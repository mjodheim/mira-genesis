"""Independent M107 checker.

Evaluates P1-P16 from the canonical result and, with --replay, re-runs the experiment and compares
stable projections. One canonical checker attempt is permitted.

M103 and M105 were both lost because a frozen checker could not start: each deferred an import into
its replay branch while direct script execution puts scripts/ on sys.path rather than the repository
root. The root is bootstrapped here at import time, before anything can need it, and the replay path
is exercised as a direct script against a materialized DEVELOPMENT result before any freeze.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from typing import Any  # noqa: E402

ROOT = _ROOT
EXPERIMENT = ROOT / "experiments" / "M107"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"

EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 17)]
EXPECTED_BASE_IMAGE = 4
EXPECTED_EXTENDED_IMAGE = 16
EXPECTED_OPERATOR_SPACE = 20

EPHEMERAL_KEYS = {
    # M098 was negative because its frozen stable projection retained consumer PIDs. The derived
    # boolean producer_pid_absent_from_later is stable and carries the claim; the raw identifiers
    # are pure process accident and must never enter a replayed projection.
    "pid",
    "producer_pid",
    "later_pids",
    "search_path",
    "python_executable",
    "elapsed_seconds",
    "stderr",
    "returncode",
    "capsule_only_path",
    "python_version",
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
            if key not in EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def _constructions(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict):
        return []
    return section.get("constructions") or []


def evaluate_conditions(evidence: dict[str, Any], *, replay_confirmed: bool) -> dict[str, bool]:
    """Predicate semantics. Deliberately imports nothing: no runtime, no orchestration."""
    preflight = evidence.get("input_preflight") or {}
    s0 = evidence.get("s0") or {}
    image_s0 = ((evidence.get("image_s0") or {}).get("image") or {})
    image_s1 = ((evidence.get("image_s1") or {}).get("image") or {})
    certificates = (evidence.get("certificates") or {}).get("certificates") or []
    primary = (evidence.get("primary_only") or {}).get("acquisition") or {}
    producer = (evidence.get("producer") or {}).get("acquisition") or {}
    adopted = producer.get("adopted_operator") or {}
    consumer = _constructions(evidence.get("consumer"))
    ablation = _constructions(evidence.get("ablation"))
    mutation = _constructions(evidence.get("mutation"))
    fresh = _constructions(evidence.get("fresh"))
    fresh_deeper = _constructions(evidence.get("fresh_deeper"))
    corruption = evidence.get("corruption") or {}
    rollback = evidence.get("rollback") or {}
    boundary = evidence.get("process_boundary") or {}
    targets = [list(item) for item in evidence.get("targets") or []]

    return {
        "P1": preflight.get("confirmed") is True
        and (evidence.get("runtime") or {}).get("implementation") == "cpython",
        "P2": sorted(s0.get("operators") or []) == ["AND", "OR"]
        and image_s0.get("size") == EXPECTED_BASE_IMAGE,
        "P3": len(certificates) == 2
        and all(
            item.get("confirmed") is True
            and item.get("target_in_image") is False
            and item.get("excluded_by_monotonicity_lemma") is True
            and item.get("budget_independent") is True
            and item.get("every_operator_is_monotone") is True
            and item.get("complete_image_is_monotone") is True
            for item in certificates
        ),
        "P4": primary.get("confirmed") is False
        and primary.get("reason") == "extension_underdetermined_by_observations"
        and (primary.get("surviving_reach_classes") or 0) >= 2,
        "P5": producer.get("confirmed") is True
        and producer.get("surviving_reach_classes") == 1
        and producer.get("operator_space_size") == EXPECTED_OPERATOR_SPACE
        and producer.get("operator_space_exhausted") is True
        and producer.get("demand_count") == 2,
        "P6": producer.get("registered") is True
        and isinstance(adopted.get("operator_id"), str)
        and adopted.get("operator_id", "").startswith("operator-")
        and adopted.get("arity") in (1, 2),
        "P7": image_s1.get("size") == EXPECTED_EXTENDED_IMAGE
        and all(
            "".join("1" if bit else "0" for bit in target) in (image_s1.get("tables") or [])
            for target in targets
        ),
        "P8": boundary.get("producer_pid_absent_from_later") is True
        and (evidence.get("information_boundary") or {}).get("producer_has_targets_file") is False
        and (evidence.get("information_boundary") or {}).get("consumer_has_demand_file") is False,
        "P9": len(consumer) == 2
        and all(
            item.get("constructible") is True and item.get("executes_to_target") is True
            for item in consumer
        ),
        "P10": len(ablation) == 2
        and all(
            item.get("constructible") is False
            and item.get("image_size") == EXPECTED_BASE_IMAGE
            for item in ablation
        ),
        "P11": len(fresh) == 2
        and all(
            item.get("constructible") is False
            and item.get("image_size") == EXPECTED_BASE_IMAGE
            for item in fresh
        ),
        "P12": len(fresh_deeper) == 2
        and all(item.get("constructible") is False for item in fresh_deeper)
        and (evidence.get("fresh_deeper") or {}).get("bound", 0)
        > (evidence.get("fresh") or {}).get("bound", 0),
        "P13": len(mutation) == 2
        and all(item.get("constructible") is False for item in mutation)
        and corruption.get("confirmed") is False
        and "digest" in str(corruption.get("error", "")).lower(),
        "P14": rollback.get("byte_exact") is True
        and rollback.get("s0_digest") == rollback.get("ablated_digest"),
        "P15": boundary.get("all_processes_isolated") is True
        and boundary.get("all_processes_zero_external_calls") is True
        and (boundary.get("isolated_process_count") or 0) >= 8,
        "P16": bool(replay_confirmed),
    }


def verify_protocol_boundary(protocol: dict[str, Any]) -> None:
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m107-protocol-v1" or protocol.get("protocol_digest") != digest(payload):
        raise ValueError("M107 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise ValueError("M107 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise ValueError("M107 decisive predicate declaration changed")
    policy = protocol.get("canonical_result_policy") or {}
    if policy.get("canonical_attempts") != 1 or policy.get("canonical_checker_attempts") != 1:
        raise ValueError("M107 canonical attempt policy changed")
    if policy.get("preserve_first_result_even_if_negative") is not True:
        raise ValueError("M107 preservation policy changed")


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m107-result-v1" or result.get("attempt") != 1:
        raise ValueError("M107 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M107 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    verify_protocol_boundary(protocol)
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M107 result protocol binding mismatch")
    if any(result.get(key) != 0 for key in ("model_calls", "network_calls", "remote_execution_calls")):
        raise ValueError("M107 result reports external calls")
    evidence = result.get("scientific_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("M107 scientific evidence is missing")
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M107 stable evidence digest mismatch")

    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m107_qualification as qualification

        replay_evidence = qualification.run_experiment()
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)

    conditions = evaluate_conditions(evidence, replay_confirmed=replay_equal)
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m107-check-report-v1",
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
        "predicate_semantics_source": "frozen_M107_independent_checker",
        "imports_m107_runtime_for_predicates": False,
        "protocol_boundary_confirmed": True,
    }
    report["report_digest"] = digest(report)
    return report


def _failure_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m107-check-report-v1",
        "scientific_verdict": True,
        "verdict": "negative",
        "failed_closed": True,
        "error": "%s: %s" % (type(error).__name__, error),
        "attempt": 1,
    }
    report["report_digest"] = digest(report)
    return report


def _refusal(reason: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m107-check-refusal-v1",
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
        print(json.dumps(_failure_report(ValueError("M107 checker report already exists")), sort_keys=True))
        return 3
    if not RESULT_PATH.exists():
        print(json.dumps(_refusal("M107 canonical result is absent; the checker attempt is preserved"), sort_keys=True))
        return 3
    try:
        result = json.loads(RESULT_PATH.read_text(encoding="ascii"))
        report = check_result(result, replay=arguments.replay)
    except Exception as error:  # noqa: BLE001 - a present but broken result is a real failure
        report = _failure_report(error)
    with REPORT_PATH.open("xb") as handle:
        handle.write(canonical_json(report).encode("ascii"))
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("verdict") == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
