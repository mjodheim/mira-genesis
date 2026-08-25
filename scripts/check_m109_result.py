"""Independent M109 checker.

Evaluates P1-P18 from the canonical result and, with --replay, re-runs the experiment and compares
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
EXPERIMENT = ROOT / "experiments" / "M109"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"

EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 19)]
EXPECTED_DOMAIN_ROWS = [1, 2, 3, 6, 7]
EXPECTED_UNREACHABLE_ROWS = [0, 4, 5]
EXPECTED_STATE_FAMILY = 84
EXPECTED_WORLD_FUNCTIONS = 256
EXPECTED_BASE_IMAGE = 4
EXPECTED_ISOLATED_PROCESSES = 21
BASE_SIGNAL_WIDTH = 2
WORLD_SIGNAL_WIDTH = 3
OPERATOR_TABLE = "operator_table"
SIGNAL_INTERFACE = "signal_interface"
CANDIDATE_SPACE = "candidate_space"

EPHEMERAL_KEYS = {
    # M098 was negative because its frozen stable projection retained consumer PIDs. The derived
    # booleans carry the claim; the raw identifiers are pure process accident and must never enter a
    # replayed projection.
    "pid",
    "producer_pids",
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


def _first_step(resolution: Any) -> dict[str, Any]:
    trace = (resolution or {}).get("trace") or []
    return trace[0] if trace else {}


def evaluate_conditions(evidence: dict[str, Any], *, replay_confirmed: bool) -> dict[str, bool]:
    """Predicate semantics. Deliberately imports nothing: no runtime, no orchestration."""
    preflight = evidence.get("input_preflight") or {}
    checks = preflight.get("checks") or {}
    machine = evidence.get("runtime") or {}
    domain = evidence.get("domain") or {}
    closure = evidence.get("closure") or {}
    m0 = evidence.get("m0") or {}
    image_m0 = evidence.get("image_m0") or {}
    baseline_section = evidence.get("baseline") or {}
    baseline = baseline_section.get("resolution") or {}
    deeper_section = evidence.get("baseline_deeper") or {}
    deeper = deeper_section.get("resolution") or {}
    gen1 = evidence.get("generation_one") or {}
    acq1 = gen1.get("acquisition") or {}
    episode1 = gen1.get("episode") or {}
    stage1 = evidence.get("stage_one_resolution") or {}
    stage2_before = evidence.get("stage_two_before_generation_two") or {}
    gen2 = evidence.get("generation_two") or {}
    acq2 = gen2.get("acquisition") or {}
    episode2 = gen2.get("episode") or {}
    stage2 = evidence.get("stage_two_resolution") or {}
    handed = evidence.get("handed_counterfactual") or {}
    conflated = evidence.get("conflated_record") or {}
    exhausted = evidence.get("exhausted_record") or {}
    ablation = evidence.get("ablation") or {}
    mutation = evidence.get("mutation") or {}
    corruption = evidence.get("corruption") or {}
    rollback = evidence.get("rollback") or {}
    reach = evidence.get("reach_improve") or {}
    chain = evidence.get("reach_chain") or {}
    curriculum = evidence.get("curriculum_boundary") or {}
    provenance = evidence.get("trial_provenance") or {}
    boundary = evidence.get("process_boundary") or {}

    return {
        "P1": preflight.get("confirmed") is True
        and machine.get("implementation") == "cpython"
        and machine.get("matches_canonical") is True,
        "P2": checks.get("registry_is_the_declared_triple") is True
        and checks.get("base_operators_are_the_monotone_fragment") is True
        and checks.get("base_candidate_space_is_monotone") is True
        and checks.get("base_holds_no_rule") is True
        and m0.get("generations") == 0
        and m0.get("signal_width") == BASE_SIGNAL_WIDTH
        and image_m0.get("size") == EXPECTED_BASE_IMAGE,
        "P3": closure.get("confirmed") is True
        and closure.get("closed_by_monotonicity_lemma") is True
        and closure.get("budget_independent") is True
        and closure.get("every_candidate_is_monotone") is True
        and closure.get("everything_reachable_is_monotone") is True,
        "P4": checks.get("stage_one_needs_the_unread_signal") is True
        and checks.get("stage_one_is_monotone") is True
        and checks.get("stage_two_is_non_monotone") is True
        and checks.get("stages_are_distinct") is True,
        "P5": baseline.get("confirmed") is False
        and baseline.get("reason") == "candidate_space_exhausted_for_this_demand"
        and (_first_step(baseline).get("attribution") or {}).get("component") == OPERATOR_TABLE
        and (_first_step(baseline).get("attribution") or {}).get("mode") == "hardwired_operator_axis"
        and ((_first_step(baseline).get("features") or {}).get("values") or [None, None, None])[2]
        is True,
        "P6": provenance.get("labels_are_lineage_determined") is True
        and episode1.get("usable") is True
        and episode2.get("usable") is True
        and (episode1.get("trial") or {}).get("label_source") == "lineage_component_trial"
        and (episode2.get("trial") or {}).get("label_source") == "lineage_component_trial"
        and checks.get("no_episode_fixture_exists") is True,
        "P7": provenance.get("no_trial_at_resolution_time") is True
        and baseline.get("trials_performed") == 0
        and stage1.get("trials_performed") == 0
        and stage2.get("trials_performed") == 0,
        "P8": conflated.get("confirmed") is False
        and conflated.get("reason") == "uncovered_episodes_name_more_than_one_component"
        and exhausted.get("confirmed") is False
        and exhausted.get("reason") == "no_uncovered_component_to_attribute"
        and acq1.get("adoption_is_conservative") is True,
        "P9": acq1.get("confirmed") is True
        and acq1.get("selected_component") == SIGNAL_INTERFACE
        and acq1.get("surviving_rule_classes") == 1
        and acq1.get("rule_space_exhausted") is True
        and gen1.get("generations") == 1
        and str((acq1.get("adopted_rule") or {}).get("rule_id", "")).startswith("rule-"),
        "P10": boundary.get("producer_pids_absent_from_later") is True
        and curriculum.get("producer_capsules_hold_no_demand") is True
        and curriculum.get("stage_one_capsules_hold_only_the_first_demand") is True
        and curriculum.get("stage_two_capsules_hold_only_the_second_demand") is True,
        "P11": stage1.get("confirmed") is True
        and (_first_step(stage1).get("attribution") or {}).get("component") == SIGNAL_INTERFACE
        and stage1.get("final_signal_width") == WORLD_SIGNAL_WIDTH
        and (stage1.get("construction") or {}).get("executes_to_target") is True
        and deeper.get("confirmed") is False
        and (deeper_section.get("bound") or 0) > (baseline_section.get("bound") or 0),
        "P12": stage2_before.get("confirmed") is False
        and (_first_step(stage2_before).get("attribution") or {}).get("mode")
        == "hardwired_operator_axis"
        and checks.get("stages_are_ordered") is True,
        "P13": acq2.get("confirmed") is True
        and acq2.get("selected_component") == CANDIDATE_SPACE
        and acq2.get("surviving_rule_classes") == 1
        and gen2.get("generations") == 2
        and (acq2.get("adopted_rule") or {}).get("generation") == 2
        and (acq2.get("adopted_rule") or {}).get("rule_id")
        != (acq1.get("adopted_rule") or {}).get("rule_id")
        and stage2.get("confirmed") is True
        and (_first_step(stage2).get("attribution") or {}).get("component") == CANDIDATE_SPACE
        and stage2.get("final_candidate_space") == "complete"
        and (stage2.get("construction") or {}).get("executes_to_target") is True,
        "P14": chain.get("strict_chain") is True
        and chain.get("m0_strictly_inside_m1") is True
        and chain.get("m1_strictly_inside_m2") is True
        and (reach.get("m0") or {}).get("axes") == [OPERATOR_TABLE]
        and sorted((reach.get("m1") or {}).get("axes") or []) == [OPERATOR_TABLE, SIGNAL_INTERFACE]
        and sorted((reach.get("m2") or {}).get("axes") or [])
        == [CANDIDATE_SPACE, OPERATOR_TABLE, SIGNAL_INTERFACE],
        "P15": ablation.get("confirmed") is False
        and rollback.get("ablated_matches_state_before_generation_two") is True
        and rollback.get("ablated_generation_count") == 1
        and mutation.get("confirmed") is False
        and corruption.get("confirmed") is False
        and "mismatch" in str(corruption.get("error", "")).lower(),
        "P16": boundary.get("all_processes_isolated") is True
        and boundary.get("all_processes_zero_external_calls") is True
        and (boundary.get("isolated_process_count") or 0) >= EXPECTED_ISOLATED_PROCESSES,
        "P17": isinstance(handed.get("confirmed"), bool)
        and isinstance(handed.get("reason"), str)
        and domain.get("rows") == EXPECTED_DOMAIN_ROWS
        and domain.get("unreachable_rows") == EXPECTED_UNREACHABLE_ROWS
        and domain.get("ambiguous_rows") == []
        and domain.get("census_complete") is True
        and domain.get("state_family_size") == EXPECTED_STATE_FAMILY
        and domain.get("world_function_count") == EXPECTED_WORLD_FUNCTIONS,
        "P18": bool(replay_confirmed),
    }


def verify_protocol_boundary(protocol: dict[str, Any]) -> None:
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m109-protocol-v1" or protocol.get("protocol_digest") != digest(
        payload
    ):
        raise ValueError("M109 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise ValueError("M109 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise ValueError("M109 decisive predicate declaration changed")
    policy = protocol.get("canonical_result_policy") or {}
    if policy.get("canonical_attempts") != 1 or policy.get("canonical_checker_attempts") != 1:
        raise ValueError("M109 canonical attempt policy changed")
    if policy.get("preserve_first_result_even_if_negative") is not True:
        raise ValueError("M109 preservation policy changed")


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m109-result-v1" or result.get("attempt") != 1:
        raise ValueError("M109 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M109 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    verify_protocol_boundary(protocol)
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M109 result protocol binding mismatch")
    if any(
        result.get(key) != 0 for key in ("model_calls", "network_calls", "remote_execution_calls")
    ):
        raise ValueError("M109 result reports external calls")
    evidence = result.get("scientific_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("M109 scientific evidence is missing")
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M109 stable evidence digest mismatch")

    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m109_qualification as qualification

        replay_evidence = qualification.run_experiment()
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)

    conditions = evaluate_conditions(evidence, replay_confirmed=replay_equal)
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m109-check-report-v1",
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
        "handed_counterfactual_outcome": (evidence.get("handed_counterfactual") or {}).get("reason"),
        "model_calls": result.get("model_calls"),
        "network_calls": result.get("network_calls"),
        "remote_execution_calls": result.get("remote_execution_calls"),
        "predicate_semantics_source": "frozen_M109_independent_checker",
        "imports_m109_runtime_for_predicates": False,
        "protocol_boundary_confirmed": True,
    }
    report["report_digest"] = digest(report)
    return report


def _failure_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m109-check-report-v1",
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
        "schema": "m109-check-refusal-v1",
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
                _failure_report(ValueError("M109 checker report already exists")), sort_keys=True
            )
        )
        return 3
    if not RESULT_PATH.exists():
        print(
            json.dumps(
                _refusal("M109 canonical result is absent; the checker attempt is preserved"),
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
