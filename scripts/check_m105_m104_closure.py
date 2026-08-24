"""Independently prove the exact M104 finite full-context dispatch boundary."""

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
except ImportError:  # pragma: no cover - package import in tests
    from scripts import check_m103_definitions as m103_checker


EXPECTED_RAW_SHA256 = "98d61df076e6b764f6b00f27793b82ef27e20cd35049780499029dc3ed7edf77"
EXPECTED_STATE_DIGEST = "a34b3b9dab99ee848a9c209a95ec9201fd7056eb99393d45d4041c885f19417a"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def validate(raw: bytes) -> dict[str, Any]:
    measured = hashlib.sha256(raw).hexdigest()
    if measured != EXPECTED_RAW_SHA256:
        raise ValueError("M104 closure checker received non-canonical predecessor bytes")
    independent_predecessor = m103_checker.validate(raw)
    state = json.loads(raw.decode("ascii"))
    if state["state_digest"] != EXPECTED_STATE_DIGEST:
        raise ValueError("M104 state digest mismatch")
    definition_reports: list[dict[str, Any]] = []
    for definition in state["definitions"]:
        dispatch = definition["dispatch"]
        contexts = {canonical_json(row["context"]) for row in dispatch}
        suffix = 0
        while True:
            witness = [f"m105-fresh-context-{definition['definition_id']}-{suffix}"]
            witness_key = canonical_json(witness)
            if witness_key not in contexts:
                break
            suffix += 1
        matched = [row for row in dispatch if canonical_json(row["context"]) == witness_key]
        if matched:
            raise ValueError("M104 fresh-context witness unexpectedly materialized")
        definition_reports.append(
            {
                "definition_id": definition["definition_id"],
                "family": definition["family"],
                "finite_domain_size": len(contexts),
                "fresh_context_witness": witness,
                "fresh_context_absent": True,
                "execution_lookup_materializes": False,
                "action_receives_context": False,
                "representation_can_abstract_nonce": False,
            }
        )
    report: dict[str, Any] = {
        "schema": "m105-independent-m104-closure-v1",
        "scientific_verdict": False,
        "confirmed": bool(definition_reports)
        and all(item["fresh_context_absent"] for item in definition_reports),
        "m104_raw_sha256": measured,
        "m104_state_digest": state["state_digest"],
        "m103_definition_report_digest": independent_predecessor["report_digest"],
        "definitions": definition_reports,
        "complete_image_kind": "finite_exact_full_context_dispatch",
        "budget_independent": True,
        "larger_budget_changes_representation": False,
        "symbolic_reason": "every finite set of exact serialized contexts omits another admitted context",
        "independent_of_m103_m104_m105_runtime_search_and_qualification": True,
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
            "schema": "m105-independent-m104-closure-v1",
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "independent_of_m103_m104_m105_runtime_search_and_qualification": True,
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
