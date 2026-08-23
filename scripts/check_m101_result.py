"""Independently recompute M101's frozen fifteen-condition verdict."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M101"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"

from audit_m101_boundaries import audit as audit_boundaries
from author_m101_qualification_pool import (
    audit as audit_pool,
    build_pool,
    canonical_json,
    digest,
    load_pool,
)
from check_m101_definitions import validate as validate_definitions
from run_m101_qualification import (
    CAPSULE_SOURCES,
    capsule_binding,
    file_set_digest,
    m100_s3_bytes,
    require_frozen,
    run_experiment,
)

CHECKER_EPHEMERAL_KEYS = {"pid", "process_pids", "search_path"}


def checker_stable_projection(value: Any) -> Any:
    """Independent implementation of the frozen recursive ephemera projection."""
    if isinstance(value, dict):
        return {
            key: checker_stable_projection(item)
            for key, item in value.items()
            if key not in CHECKER_EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [checker_stable_projection(item) for item in value]
    return value


@dataclass(frozen=True)
class Condition:
    identifier: str
    name: str
    computed: bool
    passed: bool | None
    failures: list[str]
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "computed": self.computed,
            "passed": self.passed,
            "failures": self.failures,
            "evidence": self.evidence,
        }


def _condition(
    identifier: str, name: str, failures: list[str], evidence: dict[str, Any] | None = None
) -> Condition:
    return Condition(identifier, name, True, not failures, failures, evidence or {})


def _uncomputed(identifier: str, name: str) -> Condition:
    return Condition(identifier, name, False, None, [], {})


def _success(row: dict[str, Any]) -> bool:
    return row.get("returncode") == 0 and row.get("runtime", {}).get("confirmed") is True


def _failure(row: dict[str, Any]) -> bool:
    return row.get("returncode") != 0 and row.get("runtime", {}).get("confirmed") is False


def check_p1(protocol: dict[str, Any], pool: dict[str, Any]) -> Condition:
    failures: list[str] = []
    try:
        require_frozen(protocol, pool)
    except Exception as error:
        failures.append(str(error))
    if protocol.get("pre_registration", {}).get("raw_sha256") != hashlib.sha256(
        (EXPERIMENT / "PRE_REGISTRATION.md").read_bytes()
    ).hexdigest():
        failures.append("pre-registration digest moved")
    expected_m100 = json.loads((ROOT / "experiments/M100/RESULT.json").read_text(encoding="utf-8"))
    predecessor = protocol.get("predecessor", {})
    if predecessor.get("result_digest") != expected_m100.get("result_digest"):
        failures.append("M100 result digest is not bound")
    if predecessor.get("stable_evidence_digest") != expected_m100.get("stable_evidence_digest"):
        failures.append("M100 stable evidence digest is not bound")
    if not audit_boundaries()["passed"]:
        failures.append("adversarial source-boundary audit fails")
    return _condition(
        "P1",
        "frozen_preregistration_predecessor_mechanism_pool_capsule_checker_and_projection_bindings",
        failures,
    )


def check_p2(pool: dict[str, Any]) -> Condition:
    failures: list[str] = []
    if pool != build_pool(status="frozen"):
        failures.append("committed pool differs from the authored frozen population")
    audit = audit_pool(pool)
    if not audit["passed"] or audit["entries_checked"] != 15:
        failures.append("source-only population preflight fails")
    forbidden = (
        "acquisition_was_run", "registration_was_run", "baseline_was_run", "transfer_was_run",
        "execution_was_run", "fault_was_injected", "rollback_was_run",
    )
    if any(audit.get(key) is not False for key in forbidden):
        failures.append("population crossed the scientific mechanism before freeze")
    return _condition(
        "P2", "complete_fifteen_world_population_is_valid_fresh_and_unexecuted_before_final_freeze",
        failures, {"entries": audit["entries_checked"], "source_only": audit["source_only"]},
    )


def check_p3(evidence: dict[str, Any], pool: dict[str, Any]) -> Condition:
    failures: list[str] = []
    producer = next(entry["world"] for entry in pool["entries"] if entry["world"]["role"] == "producer_trigger")
    acquisition = evidence.get("state_chronology", {}).get("acquire_and_register_a", {}).get("runtime", {}).get("acquisition", {})
    expected_ids = [case["case_id"] for case in producer["public_cases"]]
    if acquisition.get("public_case_ids") != expected_ids:
        failures.append("A acquisition did not receive exactly the producer public cases")
    if any(case["case_id"] in canonical_json(acquisition) for case in producer["hidden_cases"]):
        failures.append("producer hidden case identifiers leaked into A acquisition evidence")
    capsule = evidence.get("capsules", {}).get("acquisition", {})
    if capsule.get("members") != ["m101_runtime.py", "run.py"]:
        failures.append("A acquisition capsule census changed")
    return _condition("P3", "A_acquisition_receives_only_allowed_public_text_demand_and_generic_substrate_state", failures)


def check_p4(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    baselines = evidence.get("fresh_baselines", [])
    for row in baselines:
        baseline = row.get("fresh", {}).get("runtime", {}).get("execution", {})
        if baseline.get("structural_max_atomic_effects") != 1:
            failures.append(f"{row.get('entry')} baseline can exceed one atomic effect")
        if baseline.get("more_budget_same_language_can_exceed_one_effect") is not False:
            failures.append(f"{row.get('entry')} more-budget closure is not false")
    if not evidence.get("boundary_audit", {}).get("checks", {}).get(
        "baseline_language_is_exactly_one_atomic_application"
    ):
        failures.append("source audit does not prove one-atomic baseline semantics")
    if not evidence.get("boundary_audit", {}).get("checks", {}).get(
        "host_pipeline_shortcut_is_absent"
    ):
        failures.append("source audit does not exclude the v3 host-pipeline shortcut")
    return _condition("P4", "T0_structural_closure_proves_two_ordered_effects_unreachable_without_language_change", failures)


def _state_from_acquisition(evidence: dict[str, Any], key: str) -> dict[str, Any]:
    return evidence["state_chronology"][key]["runtime"]["acquisition"]["next_state"]


def check_p5(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    acquisition = evidence.get("state_chronology", {}).get("acquire_and_register_a", {}).get("runtime", {}).get("acquisition", {})
    adopted = acquisition.get("adopted", {})
    if acquisition.get("confirmed") is not True or acquisition.get("assembled", 0) <= 0:
        failures.append("A was not exhaustively assembled")
    if (
        acquisition.get("shortest_accepted_length") != 4
        or not isinstance(adopted.get("body"), list)
        or len(adopted["body"]) != 4
    ):
        failures.append("A is not the shortest generic two-stage body")
    validation = evidence.get("definition_validation", {}).get("T1", {})
    if not _success(validation):
        failures.append("independent T1 definition validation failed")
    else:
        state = _state_from_acquisition(evidence, "acquire_and_register_a")
        raw = canonical_json(state).encode("ascii")
        expected_m100 = m100_s3_bytes()[1]
        try:
            report = validate_definitions(raw, expected_m100_sha256=expected_m100)
            if sorted(report["definitions"][0]["symbolic_trace"]) != [0, 1]:
                failures.append("independent A trace changed")
        except Exception as error:
            failures.append(f"independent A recomputation failed: {error}")
    return _condition("P5", "A_is_exhaustively_assembled_carrier_neutral_independently_validated_and_not_a_finished_primitive", failures)


def check_p6(evidence: dict[str, Any]) -> Condition:
    chronology = evidence.get("state_chronology", {})
    failures: list[str] = []
    if chronology.get("t0_unchanged_after_a_build") is not True:
        failures.append("unregistered A changed T0 bytes")
    built = chronology.get("a_built_not_registered", {}).get("runtime", {}).get("acquisition", {})
    registered = chronology.get("acquire_and_register_a", {}).get("runtime", {}).get("acquisition", {})
    if built.get("adopted") != registered.get("adopted") or built.get("registered") is not False:
        failures.append("built and registered A candidates differ")
    states = evidence.get("states", {})
    if [states.get(name, {}).get("definition_count") for name in ("T0", "T1")] != [0, 1]:
        failures.append("T0 to T1 registration census is not 0 to 1")
    return _condition("P6", "registration_not_construction_is_the_causal_T0_to_T1_state_change", failures)


def check_p7(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    holdouts = [row for row in evidence.get("a_reuse", []) if row.get("role") != "producer_trigger"]
    baselines = evidence.get("fresh_baselines", [])
    if len(holdouts) != 8 or not all(_success(row.get("fresh", {})) for row in holdouts):
        failures.append("retained A did not solve all eight transfer holdouts")
    if len(baselines) != 8 or any(
        row.get("fresh", {}).get("runtime", {}).get("execution", {}).get("reachable") is not False
        for row in baselines
    ):
        failures.append("fresh baseline did not score zero of eight")
    return _condition("P7", "A_survives_producer_death_and_transfers_to_all_eight_holdouts_while_baseline_scores_zero", failures)


def check_p8(evidence: dict[str, Any]) -> Condition:
    parity = evidence.get("baseline_parity", {})
    failures: list[str] = []
    if parity.get("only_permitted_causal_difference") is not True:
        failures.append("baseline and retained arms differ outside registered A/state digest")
    if parity.get("arm_difference", {}).get("differing_state_keys") != [
        "definitions", "state_digest"
    ]:
        failures.append("baseline/retained state diff is not exactly A plus its digest")
    if any(
        row.get("candidate_budget_equal") is not True
        or row.get("same_executor_capsule") is not True
        or row.get("same_action") is not True
        or row.get("same_world_payload_digest") is not True
        or row.get("public_case_ids_equal") is not True
        or row.get("hidden_case_ids_equal") is not True
        or row.get("baseline_structural_max_atomic_effects") != 1
        for row in parity.get("rows", [])
    ):
        failures.append("matched-budget structural closure changed")
    return _condition("P8", "more_budget_over_unchanged_T0_cannot_substitute_for_A", failures)


def check_p9(evidence: dict[str, Any]) -> Condition:
    chronology = evidence.get("state_chronology", {})
    failures: list[str] = []
    if not _failure(chronology.get("b_absent_without_a", {})):
        failures.append("B was available without A")
    built = chronology.get("b_built_not_registered", {}).get("runtime", {}).get("acquisition", {})
    acquired = chronology.get("acquire_and_register_b", {}).get("runtime", {}).get("acquisition", {})
    if built.get("confirmed") is not True or built.get("registered") is not False:
        failures.append("unregistered B construction failed")
    if acquired.get("confirmed") is not True or acquired.get("registered") is not True:
        failures.append("B did not acquire and register from T1")
    if chronology.get("t1_unchanged_after_b_build") is not True:
        failures.append("unregistered B changed T1")
    controls = evidence.get("dependency_controls", {})
    expected_b_worlds = len(evidence.get("b_reuse", []))
    if controls.get("ablate_b_equals_t1") is not True or any(
        not _failure(row) for row in controls.get("ablate_b", [])
    ) or not expected_b_worlds or len(controls.get("ablate_b", [])) != expected_b_worlds:
        failures.append("fresh T1 consumers did not keep B absent across all B worlds")
    return _condition("P9", "later_python_syntax_target_is_demand_derived_and_B_is_acquired_only_with_registered_A", failures)


def check_p10(evidence: dict[str, Any]) -> Condition:
    failures: list[str] = []
    state = _state_from_acquisition(evidence, "acquire_and_register_b")
    a, b = state["definitions"]
    if b.get("dependencies") != [a.get("definition_id")] or not any(
        str(token).startswith(f"CALL:{a.get('definition_id')}:") for token in b.get("body", [])
    ):
        failures.append("B lost its live content-addressed A reference")
    validation = evidence.get("definition_validation", {}).get("T2", {})
    if not _success(validation):
        failures.append("independent T2 definition validation failed")
    else:
        try:
            report = validate_definitions(
                canonical_json(state).encode("ascii"),
                expected_m100_sha256=m100_s3_bytes()[1],
            )
            b_report = report["definitions"][1]
            if (
                sorted(b_report["symbolic_trace"]) != [0, 1, 2]
                or b_report["live_a_calls"] != 1
                or b_report["direct_applications"] != 1
            ):
                failures.append("independent B trace or live-call structure changed")
        except Exception as error:
            failures.append(f"independent B recomputation failed: {error}")
    controls = evidence.get("dependency_controls", {})
    if not controls.get("fault_breaks_all_b_worlds") or any(
        not _failure(row) for row in controls.get("fault_breaks_all_b_worlds", [])
    ):
        failures.append("semantic A mutation did not break every B world")
    if not _failure(controls.get("ablate_a", {})):
        failures.append("A ablation did not break B fail-closed")
    return _condition("P10", "B_retains_live_A_dependency_and_semantic_mutation_or_ablation_breaks_it", failures)


def check_p11(evidence: dict[str, Any]) -> Condition:
    states = evidence.get("states", {})
    failures: list[str] = []
    if [states.get(name, {}).get("definition_count") for name in ("T0", "T1", "T2")] != [0, 1, 2]:
        failures.append("T0/T1/T2 definition census changed")
    if states.get("m100_bytes_conserved") is not True or states.get("t1_prefix_conserved_in_t2") is not True:
        failures.append("M100 or A bytes were not conserved")
    rows = evidence.get("m100_conservation", [])
    if len(rows) != 3 or not all(_success(row.get("fresh", {})) for row in rows):
        failures.append("fresh M100 A/B/C execution did not survive T2")
    if sorted(row.get("operation_index") for row in rows) != [0, 1, 2]:
        failures.append("M100 conservation operation census changed")
    return _condition("P11", "M100_predecessor_and_A_are_conserved_through_T2_and_execute_fresh", failures)


def check_p12(evidence: dict[str, Any]) -> Condition:
    process = evidence.get("process_boundary", {})
    failures: list[str] = []
    for key in (
        "pid_records_present", "all_invocation_ordinals_unique_and_contiguous",
        "synchronous_process_exit_before_next_launch", "fresh_subprocess_launch_source_audited",
        "all_invocations_isolated", "no_project_modules_imported",
        "repository_absent_from_search_paths",
    ):
        if process.get(key) is not True:
            failures.append(f"process-boundary fact failed: {key}")
    if process.get("fresh_process_invocations") != 44:
        failures.append("complete frozen chronology is not exactly 44 isolated invocations")
    if process.get("invocation_ordinals") != list(range(1, 45)):
        failures.append("frozen process chronology ordinals are not exactly 1 through 44")
    capsules = evidence.get("capsules", {})
    if capsules.get("execution", {}).get("members") != ["m101_executor.py", "run.py"]:
        failures.append("execution-only capsule census changed")
    return _condition("P12", "all_scientific_steps_cross_hard_isolated_process_boundaries", failures)


def check_p13(evidence: dict[str, Any]) -> Condition:
    controls = evidence.get("dependency_controls", {})
    failures: list[str] = []
    if not _failure(controls.get("ablate_a", {})):
        failures.append("A ablation did not fail closed")
    expected_b_worlds = len(evidence.get("b_reuse", []))
    if (
        controls.get("ablate_b_equals_t1") is not True
        or not expected_b_worlds
        or len(controls.get("ablate_b", [])) != expected_b_worlds
    ):
        failures.append("B ablation did not restore the exact T1 control state")
    elif any(not _failure(row) for row in controls["ablate_b"]):
        failures.append("B ablation did not fail closed across every B world")
    if not _success(controls.get("a_survives_b_ablation", {})):
        failures.append("B ablation damaged unrelated A")
    if not _failure(controls.get("corrupt_state", {})):
        failures.append("state corruption did not fail closed")
    if not evidence.get("boundary_audit", {}).get("passed"):
        failures.append("hidden host shortcut source audit failed")
    return _condition("P13", "A_B_ablation_state_corruption_and_hidden_host_shortcuts_fail_closed", failures)


def check_p14(evidence: dict[str, Any]) -> Condition:
    rollback = evidence.get("rollback", {})
    failures: list[str] = []
    if rollback.get("fault_differs_from_accepted") is not True:
        failures.append("live semantic fault did not change state bytes")
    if rollback.get("restored_bytes_equal") is not True:
        failures.append("rollback was not byte exact")
    if rollback.get("restored_raw_sha256") != rollback.get("accepted_raw_sha256"):
        failures.append("rollback hash differs from accepted T2")
    if not _success(rollback.get("restore_process", {})) or not _success(rollback.get("after_restore", {})):
        failures.append("fresh rollback process did not restore B behaviour")
    return _condition("P14", "live_semantic_fault_suppresses_B_and_byte_exact_rollback_restores_it", failures)


def check_p15(
    protocol: dict[str, Any], pool: dict[str, Any], result: dict[str, Any], replay: dict[str, Any]
) -> Condition:
    failures: list[str] = []
    if digest(checker_stable_projection(replay)) != result.get("stable_evidence_digest"):
        failures.append("stable clean replay changed retained scientific evidence")
    if digest(checker_stable_projection(result.get("scientific_evidence", {}))) != result.get(
        "stable_evidence_digest"
    ):
        failures.append("recorded stable evidence digest mismatch")
    if any(result.get(key) != expected for key, expected in (
        ("model_calls", 0), ("network_calls", 0), ("remote_execution", False),
        ("working_tree_was_dirty_at_recording", False), ("attempt", 1), ("prior_attempts", []),
    )):
        failures.append("Track-A/local/first-attempt provenance changed")
    if result.get("result_digest") != digest(
        {key: value for key, value in result.items() if key != "result_digest"}
    ):
        failures.append("result digest mismatch")
    for section, result_key in (
        ("mechanism", "mechanism_digest"),
        ("qualification_apparatus", "qualification_apparatus_digest"),
        ("checker", "checker_digest"),
    ):
        measured, _members = file_set_digest(protocol[section]["files"])
        if result.get(result_key) != measured:
            failures.append(f"result does not bind frozen {section}")
    return _condition("P15", "stable_clean_replay_track_A_local_first_attempt_and_no_overwrite", failures)


CONDITION_NAMES = [
    "A_acquisition_receives_only_allowed_public_text_demand_and_generic_substrate_state",
    "T0_structural_closure_proves_two_ordered_effects_unreachable_without_language_change",
    "A_is_exhaustively_assembled_carrier_neutral_independently_validated_and_not_a_finished_primitive",
    "registration_not_construction_is_the_causal_T0_to_T1_state_change",
    "A_survives_producer_death_and_transfers_to_all_eight_holdouts_while_baseline_scores_zero",
    "more_budget_over_unchanged_T0_cannot_substitute_for_A",
    "later_python_syntax_target_is_demand_derived_and_B_is_acquired_only_with_registered_A",
    "B_retains_live_A_dependency_and_semantic_mutation_or_ablation_breaks_it",
    "M100_predecessor_and_A_are_conserved_through_T2_and_execute_fresh",
    "all_scientific_steps_cross_hard_isolated_process_boundaries",
    "A_B_ablation_state_corruption_and_hidden_host_shortcuts_fail_closed",
    "live_semantic_fault_suppresses_B_and_byte_exact_rollback_restores_it",
    "stable_clean_replay_track_A_local_first_attempt_and_no_overwrite",
]


def run_result_conditions(
    protocol: dict[str, Any], pool: dict[str, Any], result: dict[str, Any], replay: dict[str, Any]
) -> list[Condition]:
    evidence = result["scientific_evidence"]
    return [
        check_p3(evidence, pool), check_p4(evidence), check_p5(evidence), check_p6(evidence),
        check_p7(evidence), check_p8(evidence), check_p9(evidence), check_p10(evidence),
        check_p11(evidence), check_p12(evidence), check_p13(evidence), check_p14(evidence),
        check_p15(protocol, pool, result, replay),
    ]


def compute_report(
    protocol: dict[str, Any], pool: dict[str, Any], result: dict[str, Any] | None
) -> dict[str, Any]:
    conditions = [check_p1(protocol, pool), check_p2(pool)]
    if result is None:
        conditions.extend(
            _uncomputed(f"P{index}", name) for index, name in enumerate(CONDITION_NAMES, start=3)
        )
    else:
        replay = run_experiment(pool, allow_frozen=True)
        conditions.extend(run_result_conditions(protocol, pool, result, replay))
    failed = [item.identifier for item in conditions if item.computed and item.passed is False]
    uncomputed = [item.identifier for item in conditions if not item.computed]
    verdict = "negative" if failed else ("incomplete" if uncomputed else "positive")
    report: dict[str, Any] = {
        "schema": "m101-checker-v1",
        "milestone": "M101",
        "verdict": verdict,
        "passed": sum(item.passed is True for item in conditions),
        "failed": len(failed),
        "uncomputed": len(uncomputed),
        "failed_conditions": failed,
        "uncomputed_conditions": uncomputed,
        "conditions": {item.identifier: item.as_dict() for item in conditions},
        "verdict_rule": "positive only when all fifteen frozen conditions are computed and true",
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    arguments = parser.parse_args()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8")) if RESULT_PATH.exists() else None
    report = compute_report(protocol, pool, result)
    if not arguments.no_write:
        (EXPERIMENT / "CHECK_REPORT.json").write_text(
            canonical_json(report) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    if arguments.require_result and report["verdict"] != "positive":
        return 1
    if arguments.strict and report["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
