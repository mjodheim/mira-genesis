"""Independent M105 predicate checker and one-replay entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M105"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"
EXPECTED_PREDICATES = [f"P{index}" for index in range(1, 17)]
EXPECTED_POOL_DIGEST = "313aec1b41a9b95d8913a3ba1e48074d3d0dbd8b17b851fbef871a527921ddb7"
EXPECTED_POOL_RAW_SHA256 = "26f0eeebd32fbb7aab9523a0c7a239f58634e8b4918013f0d4d09a3af7e62b67"
EXPECTED_M104_RAW_SHA256 = "98d61df076e6b764f6b00f27793b82ef27e20cd35049780499029dc3ed7edf77"
EXPECTED_M104_STATE_DIGEST = "a34b3b9dab99ee848a9c209a95ec9201fd7056eb99393d45d4041c885f19417a"
EXPECTED_RUNTIME = {
    "python": {"implementation": "cpython", "version_info": [3, 11, 16]},
    "sqlite": {
        "module": "sqlite3",
        "sqlite_version": "3.53.1",
        "sqlite_version_info": [3, 53, 1],
    },
}
EPHEMERAL_KEYS = {
    "pid",
    "search_path",
    "python_executable",
    "sqlite_module",
    "stderr",
    "elapsed_seconds",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def stable_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in sorted(value.items())
            if key not in EPHEMERAL_KEYS and not key.endswith(("_pid", "_pids"))
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def _runtime(process: dict[str, Any]) -> dict[str, Any]:
    value = process.get("runtime")
    return value if isinstance(value, dict) else {}


def _successful(process: dict[str, Any]) -> bool:
    return process.get("returncode") == 0 and _runtime(process).get("confirmed") is True


def _refused(process: dict[str, Any]) -> bool:
    return process.get("returncode") in {1, 3} and _runtime(process).get("confirmed") is False


def _all_hidden(section: dict[str, Any]) -> bool:
    hidden = section.get("hidden")
    return isinstance(hidden, list) and len(hidden) == 4 and all(
        item.get("matched") is True for item in hidden
    )


def evaluate_conditions(
    evidence: dict[str, Any], *, replay_confirmed: bool
) -> dict[str, bool]:
    states = evidence.get("states", {})
    w0 = states.get("W0", {}).get("state", {})
    w1 = states.get("W1", {}).get("state", {})
    w2 = states.get("W2", {}).get("state", {})
    w3 = states.get("W3", {}).get("state", {})
    feature = evidence.get("feature", {})
    json_section = evidence.get("json", {})
    sqlite_section = evidence.get("sqlite", {})
    controls = evidence.get("controls", {})
    predecessor = evidence.get("predecessor", {})
    independent = evidence.get("independent_validation", {})
    boundary = evidence.get("process_boundary", {})
    information = evidence.get("information_boundary", {})
    census = evidence.get("semantic_census", {})

    json_fresh = _runtime(json_section.get("fresh", {})).get("acquisition", {})
    sqlite_fresh = _runtime(sqlite_section.get("fresh", {})).get("acquisition", {})
    json_lineage = _runtime(json_section.get("lineage_acquisition", {})).get(
        "acquisition", {}
    )
    sqlite_lineage = _runtime(sqlite_section.get("lineage_acquisition", {})).get(
        "acquisition", {}
    )
    feature_acquisition = _runtime(feature.get("acquisition", {})).get("acquisition", {})
    built_only = _runtime(feature.get("built_only", {})).get("acquisition", {})
    structural = _runtime(predecessor.get("structural_conservation", {})).get(
        "conservation", {}
    )
    definition_validation = independent.get("definition", {})
    semantic_validation = independent.get("semantics", {})
    closure_validation = independent.get("m104_closure", {})
    definition_report = _runtime(definition_validation)
    semantic_report = _runtime(semantic_validation)
    closure_report = _runtime(closure_validation)

    w1_feature_ids = [item.get("feature_id") for item in w1.get("features", [])]
    later_feature_ids = [
        [item.get("feature_id") for item in state.get("features", [])]
        for state in (w2, w3)
    ]
    hidden_contexts = [
        item.get("context", {})
        for item in [*json_section.get("hidden", []), *sqlite_section.get("hidden", [])]
    ]
    hidden_signal_rows = {
        tuple(context.get("signals", []))
        for context in hidden_contexts
        if isinstance(context, dict)
    }

    conditions = {
        "P1": evidence.get("input_preflight", {}).get("confirmed") is True
        and evidence.get("runtime", {}).get("python_version") == "3.11.16"
        and evidence.get("runtime", {}).get("sqlite_version") == "3.53.1",
        "P2": w0.get("m104_sha256") == EXPECTED_M104_RAW_SHA256
        and w0.get("features") == []
        and w0.get("definitions") == []
        and states.get("m104_bytes_conserved") is True,
        "P3": closure_validation.get("returncode") == 0
        and closure_report.get("confirmed") is True
        and closure_report.get("complete_image_kind")
        == "finite_exact_full_context_dispatch"
        and closure_report.get("budget_independent") is True
        and all(
            item.get("fresh_context_absent") is True
            and item.get("execution_lookup_materializes") is False
            for item in closure_report.get("definitions", [])
        )
        and _refused(predecessor.get("m104_fresh_context_execution", {})),
        "P4": census.get("semantic_count") == 16
        and census.get("complete_two_input_boolean_image") is True
        and len(census.get("representatives", [])) == 16
        and semantic_validation.get("returncode") == 0
        and semantic_report.get("confirmed") is True
        and semantic_report.get("semantic_count") == 16,
        "P5": built_only.get("confirmed") is True
        and built_only.get("registered") is False
        and feature_acquisition.get("confirmed") is True
        and feature_acquisition.get("registered") is True
        and feature_acquisition.get("accepted_semantic_classes") == 1
        and feature_acquisition.get("enumerated_semantics") == 16
        and feature_acquisition.get("all_signal_pairs_observed") is True
        and feature_acquisition.get("nonce_invariance_observed") is True
        and feature.get("serialized_identity_scan", {}).get(
            "development_literals_absent"
        )
        is True
        and _runtime(feature.get("built_only", {})).get("input_raw_sha256")
        == states.get("W0", {}).get("raw_sha256")
        and _runtime(feature.get("acquisition", {})).get("input_raw_sha256")
        == states.get("W0", {}).get("raw_sha256"),
        "P6": len(w1_feature_ids) == 1
        and all(ids == w1_feature_ids for ids in later_feature_ids)
        and boundary.get("producer_pid_absent_from_later") is True,
        "P7": json_lineage.get("confirmed") is True
        and json_fresh.get("confirmed") is False
        and json_fresh.get("enumerated_feature_semantics") == 16
        and json_fresh.get("semantic_image_exhausted") is True
        and int(json_fresh.get("semantic_classes", 0)) > 1
        and _runtime(json_section.get("fresh_repeated", {})).get(
            "repeated_image_identical"
        )
        is True
        and _all_hidden(json_section),
        "P8": sqlite_lineage.get("confirmed") is True
        and sqlite_fresh.get("confirmed") is False
        and sqlite_fresh.get("enumerated_feature_semantics") == 16
        and sqlite_fresh.get("semantic_image_exhausted") is True
        and int(sqlite_fresh.get("semantic_classes", 0)) > 1
        and _runtime(sqlite_section.get("fresh_repeated", {})).get(
            "repeated_image_identical"
        )
        is True
        and sqlite_section.get("outcomes_inspected_from_real_database_state") is True
        and _all_hidden(sqlite_section),
        "P9": evidence.get("capsules", {}).get("json_lineage", {}).get(
            "source_digest"
        )
        == evidence.get("capsules", {}).get("json_fresh", {}).get("source_digest")
        and evidence.get("capsules", {}).get("sqlite_lineage", {}).get(
            "source_digest"
        )
        == evidence.get("capsules", {}).get("sqlite_fresh", {}).get("source_digest")
        and w0.get("m104_ascii") == w1.get("m104_ascii") == w2.get("m104_ascii"),
        "P10": _all_hidden(json_section)
        and _all_hidden(sqlite_section)
        and hidden_signal_rows
        == {(False, False), (False, True), (True, False), (True, True)}
        and all(isinstance(context.get("nonce"), str) for context in hidden_contexts)
        and information.get("hidden_nonces_disjoint_from_development") is True,
        "P11": _successful(controls.get("remove_before_sqlite", {}))
        and _refused(controls.get("acquire_after_removal", {}))
        and _successful(controls.get("remove_after_compile", {}))
        and _refused(controls.get("execute_after_removal", {}))
        and _successful(controls.get("mutation", {}))
        and controls.get("mutation_matches_content_addressed_preview") is True
        and _successful(controls.get("mutation_json", {}))
        and _successful(controls.get("mutation_sqlite", {}))
        and controls.get("mutation_changed_json") is True
        and controls.get("mutation_changed_sqlite") is True,
        "P12": _refused(feature.get("ambiguous_development", {}))
        and _runtime(feature.get("ambiguous_development", {})).get("input_raw_sha256")
        == states.get("W0", {}).get("raw_sha256")
        and _successful(controls.get("corrupt_write", {}))
        and _refused(controls.get("corrupt_consumer", {}))
        and _successful(controls.get("rollback_mutation", {}))
        and _successful(controls.get("rollback_corrupt", {}))
        and controls.get("rollback_mutation_exact") is True
        and controls.get("rollback_corrupt_exact") is True,
        "P13": structural.get("all_conserved") is True
        and structural.get("m104_state_digest") == EXPECTED_M104_STATE_DIGEST
        and len(predecessor.get("m104_behavioral_conservation", [])) == 8
        and all(
            _successful(item)
            for item in predecessor.get("m104_behavioral_conservation", [])
        )
        and len(predecessor.get("m100_m102_behavioral_conservation", [])) == 7
        and all(
            _successful(item.get("process", {}))
            for item in predecessor.get("m100_m102_behavioral_conservation", [])
        ),
        "P14": information.get("feature_producer_has_development") is True
        and information.get("feature_producer_has_qualification_pool") is False
        and information.get("feature_producer_has_json_or_sqlite_demand") is False
        and information.get("json_lineage_has_development") is False
        and information.get("sqlite_lineage_has_development") is False
        and information.get("qualification_records_enter_after_feature_process_returned")
        is True
        and boundary.get("all_m105_processes_isolated") is True
        and boundary.get("all_m105_processes_zero_external_calls") is True,
        "P15": definition_validation.get("returncode") == 0
        and definition_report.get("confirmed") is True
        and definition_report.get(
            "independent_of_m105_runtime_search_and_qualification"
        )
        is True
        and semantic_report.get(
            "independent_of_m105_runtime_search_and_qualification"
        )
        is True
        and closure_report.get(
            "independent_of_m103_m104_m105_runtime_search_and_qualification"
        )
        is True,
        "P16": replay_confirmed
        and states.get("m104_bytes_conserved") is True
        and evidence.get("input_preflight", {}).get("pool_digest")
        == EXPECTED_POOL_DIGEST,
    }
    return conditions


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_protocol_boundary(protocol: dict[str, Any]) -> None:
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m105-protocol-v1" or protocol.get(
        "protocol_digest"
    ) != digest(payload):
        raise ValueError("M105 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise ValueError("M105 protocol authorization status mismatch")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise ValueError("M105 decisive predicate declaration changed")
    if protocol.get("qualification_pool_digest") != EXPECTED_POOL_DIGEST or protocol.get(
        "qualification_pool_raw_sha256"
    ) != EXPECTED_POOL_RAW_SHA256:
        raise ValueError("M105 protocol pool binding mismatch")
    if protocol.get("canonical_runtime") != EXPECTED_RUNTIME:
        raise ValueError("M105 protocol runtime declaration mismatch")
    measured_runtime = {
        "python": {
            "implementation": sys.implementation.name,
            "version_info": list(sys.version_info[:3]),
        },
        "sqlite": {
            "module": "sqlite3",
            "sqlite_version": sqlite3.sqlite_version,
            "sqlite_version_info": list(sqlite3.sqlite_version_info),
        },
    }
    if measured_runtime != EXPECTED_RUNTIME:
        raise ValueError("M105 checker runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    if not isinstance(files, list) or not isinstance(members, dict):
        raise ValueError("M105 bound-file record is invalid")
    measured = {path: _sha256(ROOT / path) for path in files}
    if measured != members or digest(measured) != bound.get("digest"):
        raise ValueError("M105 bound apparatus changed")
    policy = protocol.get("canonical_result_policy", {})
    if (
        policy.get("canonical_attempts") != 1
        or policy.get("canonical_checker_attempts") != 1
        or policy.get("exclusive_create") is not True
        or policy.get("preserve_first_result_even_if_negative") is not True
    ):
        raise ValueError("M105 unique-attempt policy mismatch")


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m105-result-v1" or result.get("attempt") != 1:
        raise ValueError("M105 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M105 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    verify_protocol_boundary(protocol)
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M105 result protocol binding mismatch")
    if result.get("pool_digest") != EXPECTED_POOL_DIGEST:
        raise ValueError("M105 result pool binding mismatch")
    if _sha256(POOL_PATH) != EXPECTED_POOL_RAW_SHA256:
        raise ValueError("M105 qualification pool raw bytes changed")
    if any(result.get(key) != 0 for key in ("model_calls", "network_calls", "remote_execution_calls")):
        raise ValueError("M105 result reports external calls")
    evidence = result.get("scientific_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("M105 scientific evidence is missing")
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M105 stable evidence digest mismatch")
    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m105_qualification as qualification

        replay_evidence = qualification.run_experiment()
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)
    conditions = evaluate_conditions(evidence, replay_confirmed=replay_equal)
    if list(conditions) != EXPECTED_PREDICATES:
        raise ValueError("M105 checker predicate set changed")
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m105-check-report-v1",
        "scientific_verdict": True,
        "verdict": "positive" if not failed else "negative",
        "attempt": 1,
        "conditions": conditions,
        "passed": len(conditions) - len(failed),
        "failed": len(failed),
        "uncomputed": 0,
        "failed_predicates": failed,
        "result_digest": result["result_digest"],
        "stable_evidence_digest": measured_stable,
        "replay_performed": replay,
        "replay_equal": replay_equal,
        "replay_stable_evidence_digest": replay_digest,
        "model_calls": result.get("model_calls"),
        "network_calls": result.get("network_calls"),
        "remote_execution_calls": result.get("remote_execution_calls"),
        "predicate_semantics_source": "frozen_M105_independent_checker",
        "imports_m105_runtime_for_predicates": False,
        "protocol_boundary_confirmed": True,
    }
    report["report_digest"] = digest(report)
    return report


def _failure_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m105-check-report-v1",
        "scientific_verdict": True,
        "verdict": "negative",
        "failed_closed": True,
        "error": f"{type(error).__name__}: {error}",
        "attempt": 1,
    }
    report["report_digest"] = digest(report)
    return report


def _refusal(reason: str) -> dict[str, Any]:
    """Refuse before the canonical checker attempt without materializing a verdict."""
    report: dict[str, Any] = {
        "schema": "m105-check-refusal-v1",
        "confirmed": False,
        "failed_closed": True,
        "report_materialized": False,
        "checker_attempt_consumed": False,
        "error": reason,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="store_true")
    arguments = parser.parse_args()
    if REPORT_PATH.exists():
        print(json.dumps(_failure_report(ValueError("M105 checker report already exists")), sort_keys=True))
        return 3
    if not RESULT_PATH.exists():
        print(
            json.dumps(
                _refusal("M105 canonical result is absent; the checker attempt is preserved"),
                sort_keys=True,
            )
        )
        return 3
    try:
        result = json.loads(RESULT_PATH.read_text(encoding="ascii"))
        report = check_result(result, replay=arguments.replay)
    except Exception as error:
        report = _failure_report(error)
    with REPORT_PATH.open("xb") as handle:
        handle.write(canonical_json(report).encode("ascii"))
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("verdict") == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
