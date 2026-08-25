"""Independent M108 checker.

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
EXPERIMENT = ROOT / "experiments" / "M108"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"

EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 17)]
EXPECTED_ATTRIBUTION_DOMAIN = [0, 2, 3]
EXPECTED_UNREACHABLE_ROWS = [1]
EXPECTED_BASE_IMAGE = 16
EXPECTED_LIFTABLE_IMAGES = 16
EXPECTED_MONOTONE_RULE_SPACE = 4
EXPECTED_ISOLATED_PROCESSES = 14
BASE_SIGNAL_WIDTH = 2
WORLD_SIGNAL_WIDTH = 3

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


def evaluate_conditions(evidence: dict[str, Any], *, replay_confirmed: bool) -> dict[str, bool]:
    """Predicate semantics. Deliberately imports nothing: no runtime, no orchestration."""
    preflight = evidence.get("input_preflight") or {}
    preflight_checks = preflight.get("checks") or {}
    machine = evidence.get("runtime") or {}
    domain = evidence.get("domain") or {}
    equivalence = evidence.get("equivalence") or {}
    s0 = evidence.get("s0") or {}
    image_s0 = evidence.get("image_s0") or {}
    image_s1 = evidence.get("image_s1") or {}
    partial = evidence.get("partial_acquisition") or {}
    producer = evidence.get("producer") or {}
    acquisition = producer.get("acquisition") or {}
    adopted = acquisition.get("adopted_rule") or {}
    control = evidence.get("monotone_control") or {}
    exclusion = evidence.get("exclusion") or {}
    structural = exclusion.get("structural") or {}
    monotone = exclusion.get("monotone") or {}
    consumer = evidence.get("consumer") or {}
    consumer_trace = consumer.get("trace") or []
    consumer_step = consumer_trace[0] if consumer_trace else {}
    construction = consumer.get("construction") or {}
    baseline_section = evidence.get("baseline") or {}
    baseline = baseline_section.get("resolution") or {}
    baseline_trace = baseline.get("trace") or []
    baseline_step = baseline_trace[0] if baseline_trace else {}
    deeper = evidence.get("baseline_deeper") or {}
    deeper_resolution = deeper.get("resolution") or {}
    ablation = evidence.get("ablation") or {}
    mutation = evidence.get("mutation") or {}
    mutation_trace = mutation.get("trace") or []
    mutation_step = mutation_trace[0] if mutation_trace else {}
    corruption = evidence.get("corruption") or {}
    rollback = evidence.get("rollback") or {}
    information = evidence.get("information_boundary") or {}
    boundary = evidence.get("process_boundary") or {}

    return {
        "P1": preflight.get("confirmed") is True
        and machine.get("implementation") == "cpython"
        and machine.get("matches_canonical") is True,
        "P2": s0.get("attribution_mode") == "hardwired_operator_axis"
        and s0.get("signal_width") == BASE_SIGNAL_WIDTH
        and preflight_checks.get("registry_is_the_declared_pair") is True
        and preflight_checks.get("m0_holds_the_m107_acquisition") is True
        and equivalence.get("confirmed") is True
        and equivalence.get("images_identical") is True
        and equivalence.get("m107_executes_m108_witnesses") is True
        and image_s0.get("size") == EXPECTED_BASE_IMAGE,
        "P3": structural.get("confirmed") is True
        and structural.get("target_in_any_liftable_image") is False
        and structural.get("depends_on_unread_signal") is True
        and structural.get("liftable_image_count") == EXPECTED_LIFTABLE_IMAGES
        and structural.get("budget_independent") is True
        and structural.get("operator_set_independent") is True,
        "P4": monotone.get("confirmed") is True
        and monotone.get("target_in_image") is False
        and monotone.get("target_is_monotone") is False
        and monotone.get("every_operator_is_monotone") is True
        and monotone.get("complete_image_is_monotone") is True
        and monotone.get("excluded_by_monotonicity_lemma") is True
        and monotone.get("budget_independent") is True,
        "P5": domain.get("rows") == EXPECTED_ATTRIBUTION_DOMAIN
        and domain.get("unreachable_rows") == EXPECTED_UNREACHABLE_ROWS
        and domain.get("census_complete") is True
        and (domain.get("unconstructible_pairs_examined") or 0) > 0
        and (domain.get("state_family_size") or 0) > 1,
        "P6": control.get("confirmed") is False
        and control.get("reason") == "no_expressible_rule_reproduces_the_blame_record"
        and control.get("consistent_rule_count") == 0
        and control.get("rule_space_size") == EXPECTED_MONOTONE_RULE_SPACE,
        "P7": partial.get("confirmed") is False
        and partial.get("reason") == "attribution_underdetermined_by_episodes"
        and (partial.get("surviving_attribution_classes") or 0) >= 2
        and partial.get("attribution_domain_covered") is False,
        "P8": acquisition.get("confirmed") is True
        and acquisition.get("surviving_attribution_classes") == 1
        and acquisition.get("rule_space_exhausted") is True
        and acquisition.get("attribution_domain_covered") is True
        and acquisition.get("every_consistent_rule_is_non_monotone") is True
        and producer.get("episode_rows") == EXPECTED_ATTRIBUTION_DOMAIN
        and preflight_checks.get("no_episode_carries_the_later_demand") is True,
        "P9": acquisition.get("registered") is True
        and isinstance(adopted.get("rule_id"), str)
        and adopted.get("rule_id", "").startswith("attribution-")
        and len(adopted.get("truth_table") or []) == 4
        and producer.get("s1_attribution_mode") == "state_held_rule",
        "P10": boundary.get("producer_pid_absent_from_later") is True
        and information.get("producer_has_demand_file") is False
        and information.get("producer_has_episodes_file") is True
        and information.get("later_stages_have_episodes_file") is False
        and information.get("later_stages_have_demand_file") is True,
        "P11": (consumer_step.get("attribution") or {}).get("component") == "signal_interface"
        and (consumer_step.get("attribution") or {}).get("mode") == "state_held_rule"
        and (consumer_step.get("extension") or {}).get("confirmed") is True
        and consumer.get("final_signal_width") == WORLD_SIGNAL_WIDTH,
        "P12": consumer.get("confirmed") is True
        and construction.get("constructible") is True
        and construction.get("executes_to_target") is True
        and image_s1.get("signal_width") == BASE_SIGNAL_WIDTH,
        "P13": baseline.get("confirmed") is False
        and baseline.get("reason") == "operator_candidate_space_exhausted"
        and (baseline_step.get("attribution") or {}).get("component") == "operator_table"
        and (baseline_step.get("attribution") or {}).get("mode") == "hardwired_operator_axis"
        and (baseline_step.get("extension") or {}).get("operator_space_exhausted") is True
        and deeper_resolution.get("confirmed") is False
        and deeper_resolution.get("reason") == "operator_candidate_space_exhausted"
        and (deeper.get("bound") or 0) > (baseline_section.get("bound") or 0)
        and baseline.get("steps") == consumer.get("steps"),
        "P14": ablation.get("confirmed") is False
        and mutation.get("confirmed") is False
        and (mutation_step.get("attribution") or {}).get("component") == "operator_table"
        and (mutation_step.get("attribution") or {}).get("mode") == "state_held_rule"
        and corruption.get("confirmed") is False
        and "mismatch" in str(corruption.get("error", "")).lower()
        and rollback.get("byte_exact") is True
        and rollback.get("s0_digest") == rollback.get("ablated_digest"),
        "P15": boundary.get("all_processes_isolated") is True
        and boundary.get("all_processes_zero_external_calls") is True
        and (boundary.get("isolated_process_count") or 0) >= EXPECTED_ISOLATED_PROCESSES,
        "P16": bool(replay_confirmed),
    }


def verify_protocol_boundary(protocol: dict[str, Any]) -> None:
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m108-protocol-v1" or protocol.get("protocol_digest") != digest(
        payload
    ):
        raise ValueError("M108 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise ValueError("M108 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise ValueError("M108 decisive predicate declaration changed")
    policy = protocol.get("canonical_result_policy") or {}
    if policy.get("canonical_attempts") != 1 or policy.get("canonical_checker_attempts") != 1:
        raise ValueError("M108 canonical attempt policy changed")
    if policy.get("preserve_first_result_even_if_negative") is not True:
        raise ValueError("M108 preservation policy changed")


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m108-result-v1" or result.get("attempt") != 1:
        raise ValueError("M108 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M108 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    verify_protocol_boundary(protocol)
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M108 result protocol binding mismatch")
    if any(
        result.get(key) != 0 for key in ("model_calls", "network_calls", "remote_execution_calls")
    ):
        raise ValueError("M108 result reports external calls")
    evidence = result.get("scientific_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("M108 scientific evidence is missing")
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M108 stable evidence digest mismatch")

    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m108_qualification as qualification

        replay_evidence = qualification.run_experiment()
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)

    conditions = evaluate_conditions(evidence, replay_confirmed=replay_equal)
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m108-check-report-v1",
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
        "predicate_semantics_source": "frozen_M108_independent_checker",
        "imports_m108_runtime_for_predicates": False,
        "protocol_boundary_confirmed": True,
    }
    report["report_digest"] = digest(report)
    return report


def _failure_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m108-check-report-v1",
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
        "schema": "m108-check-refusal-v1",
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
        print(
            json.dumps(
                _failure_report(ValueError("M108 checker report already exists")), sort_keys=True
            )
        )
        return 3
    if not RESULT_PATH.exists():
        print(
            json.dumps(
                _refusal("M108 canonical result is absent; the checker attempt is preserved"),
                sort_keys=True,
            )
        )
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
