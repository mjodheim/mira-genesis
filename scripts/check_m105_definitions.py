"""Independently validate M105 state, feature, and consumer definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import check_m103_definitions as m103_checker
    import check_m105_semantics as semantic_checker
except ImportError:  # pragma: no cover - package import in tests
    from scripts import check_m103_definitions as m103_checker
    from scripts import check_m105_semantics as semantic_checker


EXPECTED_M104_RAW_SHA256 = "98d61df076e6b764f6b00f27793b82ef27e20cd35049780499029dc3ed7edf77"
EXPECTED_M104_STATE_DIGEST = "a34b3b9dab99ee848a9c209a95ec9201fd7056eb99393d45d4041c885f19417a"
EXPECTED_M104_CONSTRUCTOR_ID = "constructor-s-prime-44b6c4c7f1bbe12c"
EXPECTED_M104_DEFINITION_IDS = (
    "consumer-a3fc0657cb475d16",
    "consumer-a687ff8014d8b314",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _feature(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    item = _closed(
        raw, {"schema", "feature_id", "body", "truth_table"}, "M105 feature"
    )
    # Feature validation uses the independent interpreter directly.  The
    # canonical census itself is checked separately by check_m105_semantics.
    body, nodes = semantic_checker._expression(item["body"])
    table = tuple(semantic_checker._execute(body, row) for row in semantic_checker.ROWS)
    payload = {
        "schema": "m105-constructor-feature-v1",
        "body": item["body"],
        "truth_table": list(table),
    }
    if item["schema"] != payload["schema"] or item["truth_table"] != list(table):
        raise ValueError("M105 feature semantics mismatch")
    if item["feature_id"] != f"feature-{digest(payload)[:16]}":
        raise ValueError("M105 feature content address mismatch")
    return item, {
        "feature_id": item["feature_id"],
        "truth_table": list(table),
        "nodes": nodes,
        "content_address_valid": True,
    }


def _action(raw: Any) -> dict[str, Any]:
    item = _closed(raw, {"schema", "action_id", "descriptor"}, "M105 action")
    payload = {"schema": "m105-action-v1", "descriptor": item["descriptor"]}
    if item["schema"] != payload["schema"] or item["action_id"] != f"action-{digest(payload)[:16]}":
        raise ValueError("M105 action content address mismatch")
    return item


def _definition(raw: Any, feature_ids: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    item = _closed(
        raw,
        {"schema", "definition_id", "family", "feature_id", "actions", "branches"},
        "M105 definition",
    )
    if item["schema"] != "m105-consumer-definition-v1" or item["family"] not in {
        "json_document",
        "sqlite",
    }:
        raise ValueError("M105 definition schema/family mismatch")
    if item["feature_id"] not in feature_ids:
        raise ValueError("M105 live feature dependency is missing")
    actions = [_action(action) for action in item["actions"]]
    action_ids = {action["action_id"] for action in actions}
    branches = _closed(item["branches"], {"false", "true"}, "M105 branches")
    for body in branches.values():
        if not isinstance(body, list) or not 1 <= len(body) <= 2:
            raise ValueError("M105 definition branch is invalid")
        if any(action_id not in action_ids for action_id in body):
            raise ValueError("M105 definition branch action is absent")
    payload = {key: value for key, value in item.items() if key != "definition_id"}
    if item["definition_id"] != f"consumer-{digest(payload)[:16]}":
        raise ValueError("M105 definition content address mismatch")
    return item, {
        "definition_id": item["definition_id"],
        "family": item["family"],
        "feature_id": item["feature_id"],
        "content_address_valid": True,
        "live_dependency_valid": True,
    }


def validate(raw: bytes) -> dict[str, Any]:
    try:
        state = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"M105 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(state).encode("ascii") != raw:
        raise ValueError("M105 state bytes are not canonical JSON")
    state = _closed(
        state,
        {"schema", "m104_sha256", "m104_ascii", "features", "definitions", "state_digest"},
        "M105 state",
    )
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    if state["schema"] != "m105-lineage-state-v1" or state["state_digest"] != digest(payload):
        raise ValueError("M105 state schema or digest mismatch")
    predecessor_raw = state["m104_ascii"].encode("ascii")
    measured_m104 = hashlib.sha256(predecessor_raw).hexdigest()
    if measured_m104 != state["m104_sha256"] or measured_m104 != EXPECTED_M104_RAW_SHA256:
        raise ValueError("M105 exact M104 predecessor bytes changed")
    predecessor_report = m103_checker.validate(predecessor_raw)
    predecessor = json.loads(predecessor_raw.decode("ascii"))
    if predecessor["state_digest"] != EXPECTED_M104_STATE_DIGEST:
        raise ValueError("M105 predecessor state digest mismatch")
    if predecessor["constructor"]["constructor_id"] != EXPECTED_M104_CONSTRUCTOR_ID:
        raise ValueError("M105 predecessor constructor mismatch")
    if tuple(item["definition_id"] for item in predecessor["definitions"]) != EXPECTED_M104_DEFINITION_IDS:
        raise ValueError("M105 predecessor definitions mismatch")
    if not isinstance(state["features"], list) or len(state["features"]) > 1:
        raise ValueError("M105 feature registry is invalid")
    features_and_reports = [_feature(feature) for feature in state["features"]]
    features = [item[0] for item in features_and_reports]
    feature_reports = [item[1] for item in features_and_reports]
    feature_ids = {feature["feature_id"] for feature in features}
    if not isinstance(state["definitions"], list):
        raise ValueError("M105 definitions are invalid")
    definitions_and_reports = [
        _definition(definition, feature_ids) for definition in state["definitions"]
    ]
    definitions = [item[0] for item in definitions_and_reports]
    definition_reports = [item[1] for item in definitions_and_reports]
    definition_ids = [definition["definition_id"] for definition in definitions]
    families = [definition["family"] for definition in definitions]
    if len(definition_ids) != len(set(definition_ids)) or len(families) != len(set(families)):
        raise ValueError("M105 definitions are duplicated")
    report: dict[str, Any] = {
        "schema": "m105-definition-validation-v1",
        "scientific_verdict": False,
        "confirmed": True,
        "state_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state["state_digest"],
        "m104_sha256": measured_m104,
        "m104_report_digest": predecessor_report["report_digest"],
        "features": feature_reports,
        "definitions": definition_reports,
        "independent_of_m105_runtime_search_and_qualification": True,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    arguments = parser.parse_args()
    try:
        report = validate(Path(arguments.state).read_bytes())
    except Exception as error:
        report = {
            "schema": "m105-definition-validation-v1",
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "independent_of_m105_runtime_search_and_qualification": True,
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
