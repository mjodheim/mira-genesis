"""Independently validate M103 state, constructor and consumer definitions.

This checker imports neither the M103 nor M102 implementation module.  It
recomputes every M103 content address and delegates only the embedded predecessor
to the already independent M102 definition checker.  It does not inspect
qualification data and cannot issue a scientific verdict.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from scripts import check_m102_definitions as m102_checker
except ImportError:  # pragma: no cover - direct copied-capsule execution
    import check_m102_definitions as m102_checker  # type: ignore[no-redef]


STATE_SCHEMA = "m103-lineage-state-v1"
CONSTRUCTOR_SCHEMA = "m103-hypothesis-constructor-v1"
ACTION_SCHEMA = "m103-action-v1"
DEFINITION_SCHEMA = "m103-consumer-definition-v1"
REPORT_SCHEMA = "m103-definition-validation-v1"

S0_ORIGIN = "m103-inherited-s0"
S_PRIME_ORIGIN = "m103-acquired-s-prime"
REQUIRED_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
}
FEATURE_TOKENS = {
    "ALLOW_EMPTY_LINEAR",
    "EMIT_GUARDED",
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "REVERSE_ACTION_ORDER",
    "SORT_ACTION_IDS",
    "SYNTHESIZE_PARTITIONS",
}
SUPPORTED_FAMILIES = {"development_record", "configuration", "filesystem"}
FORBIDDEN_S_PRIME_SUBSTRINGS = (
    "configparser",
    "configuration",
    "filesystem",
    "file",
    "path",
    "section",
    "ini",
    "development_record",
    "solution",
    "target",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _validate_constructor(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "constructor_id", "origin", "features"},
        "M103 constructor",
    )
    if item["schema"] != CONSTRUCTOR_SCHEMA or item["origin"] not in {
        S0_ORIGIN,
        S_PRIME_ORIGIN,
    }:
        raise ValueError("M103 constructor schema/origin mismatch")
    if not isinstance(item["features"], list) or item["features"] != sorted(
        set(item["features"])
    ):
        raise ValueError("M103 constructor features are not canonical")
    if len(item["features"]) > 4 or any(
        feature not in FEATURE_TOKENS for feature in item["features"]
    ):
        raise ValueError("M103 constructor feature set is invalid")
    if item["origin"] == S0_ORIGIN and item["features"]:
        raise ValueError("M103 S0 unexpectedly has features")
    if item["origin"] == S_PRIME_ORIGIN:
        lowered = canonical_json(item).lower()
        if any(term in lowered for term in FORBIDDEN_S_PRIME_SUBSTRINGS):
            raise ValueError("M103 S-prime contains consumer-specific identity")
    payload = {
        "schema": CONSTRUCTOR_SCHEMA,
        "origin": item["origin"],
        "features": item["features"],
    }
    prefix = "constructor-s0" if item["origin"] == S0_ORIGIN else "constructor-s-prime"
    expected_id = f"{prefix}-{digest(payload)[:16]}"
    if item["constructor_id"] != expected_id:
        raise ValueError("M103 constructor content address mismatch")
    return item, {
        "constructor_id": expected_id,
        "origin": item["origin"],
        "features": item["features"],
        "required_feature_set_complete": REQUIRED_FEATURES.issubset(item["features"]),
        "generic_identity_scan_passed": True,
    }


def _validate_action(raw: Any) -> dict[str, Any]:
    item = _closed(copy.deepcopy(raw), {"schema", "action_id", "descriptor"}, "M103 action")
    if item["schema"] != ACTION_SCHEMA or not isinstance(item["descriptor"], dict):
        raise ValueError("M103 action is invalid")
    payload = {"schema": ACTION_SCHEMA, "descriptor": item["descriptor"]}
    if item["action_id"] != f"action-{digest(payload)[:16]}":
        raise ValueError("M103 action content address mismatch")
    return item


def _validate_definition(raw: Any, current_constructor_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    item = _closed(
        copy.deepcopy(raw),
        {
            "schema",
            "definition_id",
            "family",
            "acquired_by",
            "actions",
            "dispatch",
        },
        "M103 definition",
    )
    if item["schema"] != DEFINITION_SCHEMA or item["family"] not in SUPPORTED_FAMILIES:
        raise ValueError("M103 definition schema/family mismatch")
    if not isinstance(item["acquired_by"], str) or not item["acquired_by"]:
        raise ValueError("M103 definition acquisition provenance is invalid")
    if not isinstance(item["actions"], list) or not item["actions"]:
        raise ValueError("M103 definition actions are missing")
    actions = [_validate_action(action) for action in item["actions"]]
    action_ids = {action["action_id"] for action in actions}
    if len(action_ids) != len(actions):
        raise ValueError("M103 definition contains duplicate actions")
    if not isinstance(item["dispatch"], list) or not item["dispatch"]:
        raise ValueError("M103 definition dispatch is missing")
    contexts: set[str] = set()
    bodies: list[list[str]] = []
    for raw_row in item["dispatch"]:
        row = _closed(copy.deepcopy(raw_row), {"context", "body"}, "M103 dispatch row")
        if not isinstance(row["context"], list) or not row["context"]:
            raise ValueError("M103 dispatch context is invalid")
        key = canonical_json(row["context"])
        if key in contexts:
            raise ValueError("M103 dispatch context is duplicated")
        contexts.add(key)
        if not isinstance(row["body"], list) or not 1 <= len(row["body"]) <= 3:
            raise ValueError("M103 dispatch body is invalid")
        if any(action_id not in action_ids for action_id in row["body"]):
            raise ValueError("M103 dispatch references an absent action")
        bodies.append(list(row["body"]))
    payload = {key: value for key, value in item.items() if key != "definition_id"}
    if item["definition_id"] != f"consumer-{digest(payload)[:16]}":
        raise ValueError("M103 definition content address mismatch")
    return item, {
        "definition_id": item["definition_id"],
        "family": item["family"],
        "acquired_by": item["acquired_by"],
        "acquired_by_current_constructor": item["acquired_by"] == current_constructor_id,
        "dispatch_contexts": len(contexts),
        "distinct_bodies": len({canonical_json(body) for body in bodies}),
        "context_conditioned": len(contexts) > 1 and len({canonical_json(body) for body in bodies}) > 1,
        "content_address_valid": True,
    }


def validate(
    raw: bytes,
    *,
    expected_m102_sha256: str | None = None,
    expected_m102_state_digest: str | None = None,
    expected_m101_sha256: str | None = None,
    expected_m100_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        state = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"M103 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(state).encode("ascii") != raw:
        raise ValueError("M103 state bytes are not canonical JSON")
    state = _closed(
        state,
        {
            "schema",
            "m102_sha256",
            "m102_ascii",
            "constructor",
            "definitions",
            "state_digest",
        },
        "M103 state",
    )
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    if state["schema"] != STATE_SCHEMA or state["state_digest"] != digest(payload):
        raise ValueError("M103 state schema or digest mismatch")
    if not isinstance(state["m102_ascii"], str) or not isinstance(state["m102_sha256"], str):
        raise ValueError("M103 predecessor binding is invalid")
    predecessor_raw = state["m102_ascii"].encode("ascii")
    measured_m102 = hashlib.sha256(predecessor_raw).hexdigest()
    if measured_m102 != state["m102_sha256"]:
        raise ValueError("M103 predecessor bytes changed")
    if expected_m102_sha256 is not None and measured_m102 != expected_m102_sha256:
        raise ValueError("M102 predecessor differs from the independently expected digest")
    predecessor = m102_checker.validate(
        predecessor_raw,
        expected_m101_sha256=expected_m101_sha256,
        expected_m100_sha256=expected_m100_sha256,
    )
    if expected_m102_state_digest is not None and predecessor["state_digest"] != expected_m102_state_digest:
        raise ValueError("embedded M102 state digest differs from expected U2")
    if predecessor["policy"]["origin"] != "m102-acquired-policy" or predecessor[
        "c_definition"
    ] is None:
        raise ValueError("embedded predecessor is not positive M102 U2 shape")

    constructor, constructor_report = _validate_constructor(state["constructor"])
    if not isinstance(state["definitions"], list):
        raise ValueError("M103 definitions are invalid")
    definitions: list[dict[str, Any]] = []
    definition_reports: list[dict[str, Any]] = []
    for raw_definition in state["definitions"]:
        definition, report = _validate_definition(
            raw_definition, str(constructor["constructor_id"])
        )
        definitions.append(definition)
        definition_reports.append(report)
    ids = [item["definition_id"] for item in definitions]
    if len(ids) != len(set(ids)):
        raise ValueError("M103 state contains duplicate definitions")

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "scientific_verdict": False,
        "confirmed": True,
        "state_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state["state_digest"],
        "m102_sha256": measured_m102,
        "m102_state_digest": predecessor["state_digest"],
        "m102_report_digest": predecessor["report_digest"],
        "constructor": constructor_report,
        "definition_count": len(definitions),
        "definitions": definition_reports,
        "independent_of_m103_runtime_search_and_qualification": True,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--expected-m102-sha256")
    parser.add_argument("--expected-m102-state-digest")
    parser.add_argument("--expected-m101-sha256")
    parser.add_argument("--expected-m100-sha256")
    arguments = parser.parse_args()
    try:
        report = validate(
            Path(arguments.state).read_bytes(),
            expected_m102_sha256=arguments.expected_m102_sha256,
            expected_m102_state_digest=arguments.expected_m102_state_digest,
            expected_m101_sha256=arguments.expected_m101_sha256,
            expected_m100_sha256=arguments.expected_m100_sha256,
        )
    except Exception as error:
        report = {
            "schema": REPORT_SCHEMA,
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "independent_of_m103_runtime_search_and_qualification": True,
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
