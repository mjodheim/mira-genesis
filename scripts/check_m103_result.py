"""Independent M103 result predicate checker and optional frozen replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M103"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"

EPHEMERAL_KEYS = {
    "pid",
    "process_pids",
    "search_path",
    "elapsed_seconds",
    "started_at_utc",
    "python_executable",
    "configparser_module",
}
EXPECTED_PREDICATES = [f"P{index}" for index in range(1, 16)]
REQUIRED_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
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


def _confirmed(item: dict[str, Any]) -> bool:
    return item.get("returncode") == 0 and item.get("runtime", {}).get("confirmed") is True


def _refused(item: dict[str, Any]) -> bool:
    return item.get("returncode") in {1, 3} and item.get("runtime", {}).get("confirmed") is False


def _reason(item: dict[str, Any]) -> str | None:
    return item.get("runtime", {}).get("acquisition", {}).get("reason")


def _all_hidden_confirmed(items: list[dict[str, Any]]) -> bool:
    return bool(items) and all(
        _confirmed(item)
        and item["runtime"]["execution"]["passed"] == item["runtime"]["execution"]["total"]
        for item in items
    )


def _execution_all_passed(item: dict[str, Any]) -> bool:
    if not _confirmed(item):
        return False
    execution = item.get("runtime", {}).get("execution", {})
    if execution.get("confirmed") is not True:
        return False
    if "passed" in execution or "total" in execution:
        return execution.get("passed") == execution.get("total")
    return execution.get("hidden_passed") == execution.get("hidden_total")


def evaluate_conditions(evidence: dict[str, Any], *, replay_confirmed: bool = False) -> dict[str, bool]:
    states = evidence["states"]
    constructor = evidence["constructor"]
    s_acquisition = constructor["acquisition"]
    s_record = s_acquisition["runtime"]["acquisition"]
    closure = s_record["s0_closure"]
    configuration = evidence["configuration"]
    filesystem = evidence["filesystem"]
    refusal = evidence["refusal"]
    dependencies = evidence["truthful_dependency_boundary"]
    ablations = evidence["ablations"]
    rollback = evidence["rollback"]
    conservation = evidence["predecessor_conservation"]
    conservation_report = conservation.get("runtime", {}).get("conservation", {})
    behavioral_conservation = evidence["predecessor_behavioral_conservation"]
    behavioral_executions = behavioral_conservation.get("executions", [])
    definitions = evidence["definition_validation"]
    definition_report = definitions.get("runtime", {})
    process = evidence["process_boundary"]
    boundary = evidence["information_boundary"]
    parity = evidence["baseline_parity"]
    independent_closure = evidence["independent_closure"]

    conditions = {
        "P1": bool(
            states["m102_bytes_conserved_v0_v1_v2_v3"]
            and evidence["predecessor"]["u2_raw_sha256"]
            == "3bad4d5400e8d9a11b15ba596336925823ffb4064a5bbe38f93f64b7384a198d"
            and evidence["predecessor"]["u2_state_digest"]
            == "fbf7b0232aa8adf4e67513719c63f19f28c1b7e8b86437af1135ff18335d3a0e"
            and _confirmed(conservation)
            and evidence["predecessor_conservation_preflight"]["confirmed"]
            and behavioral_conservation.get("confirmed") is True
            and behavioral_conservation.get("retained_m102_raw_sha256")
            == evidence["predecessor"]["u2_raw_sha256"]
            and behavioral_conservation.get("materialized_after_e_producer_return") is True
            and behavioral_conservation.get("all_isolated") is True
            and behavioral_conservation.get("all_imported_project_modules_empty") is True
            and behavioral_conservation.get("all_external_call_counters_zero") is True
            and len(behavioral_executions) == 7
            and all(
                _execution_all_passed(item["fresh"])
                for item in behavioral_executions
            )
            and _confirmed(definitions)
            and definition_report.get("m102_state_digest")
            == evidence["predecessor"]["u2_state_digest"]
        ),
        "P2": bool(
            closure["all_hypotheses_context_invariant"]
            and closure["actions_receive_context"] is False
            and closure["demand_outside_complete_image"]
            and closure["budget_independent"]
            and closure["finite_image_size"] > 0
            and s_record["s0_attempt"]["confirmed"] is False
            and _confirmed(independent_closure["development"])
            and independent_closure["development"]["runtime"]["accepted"] == 0
            and independent_closure["development"]["runtime"]["finite_image_size"]
            == closure["finite_image_size"]
        ),
        "P3": bool(
            s_record["s0_attempt"]["assembled"] == closure["finite_image_size"]
            and s_record["s0_attempt"]["accepted"] == 0
            and s_record["confirmed"]
            and s_record["reason"] == "unique_shortest_constructor_semantic_class"
        ),
        "P4": bool(
            _confirmed(s_acquisition)
            and s_record["registered"]
            and s_record["assembled"] == 98
            and set(s_record["adopted"]["features"]) == REQUIRED_FEATURES
            and _confirmed(constructor["built_only"])
            and constructor["built_only"]["runtime"]["acquisition"]["registered"] is False
            and constructor["built_only"]["runtime"]["acquisition"]["next_state"] is None
            and constructor["v0_bytes_unchanged_by_built_only"]
            and definition_report.get("constructor", {}).get("required_feature_set_complete")
        ),
        "P5": bool(
            boundary["qualification_materialized_after_s_prime_producer_return"]
            and boundary["s_prime_producer_received_only_v0_and_development_demand"]
            and boundary["s_prime_producer_capsule_contains_pool"] is False
            and boundary["runtime_source_contains_pool_path"] is False
            and process["all_isolated"]
            and process["all_imported_project_modules_empty"]
            and behavioral_conservation["all_isolated"]
            and behavioral_conservation["all_imported_project_modules_empty"]
        ),
        "P6": bool(
            _confirmed(configuration["acquisition"])
            and _all_hidden_confirmed(configuration["hidden"])
            and _refused(configuration["fresh_s0"])
            and _refused(configuration["more_budget_s0"])
            and configuration["fresh_s0"]["runtime"]["acquisition"]["assembled"]
            == closure["finite_image_size"]
            and configuration["more_budget_s0"]["runtime"]["repetitions"] == 32
            and configuration["more_budget_s0"]["runtime"]["total_assembled"]
            == 32 * closure["finite_image_size"]
            and configuration["more_budget_s0"]["runtime"]["repeated_image_identical"]
            and _confirmed(independent_closure["configuration"])
            and independent_closure["configuration"]["runtime"]["accepted"] == 0
        ),
        "P7": bool(
            boundary["filesystem_materialized_after_d_producer_return"]
            and _confirmed(filesystem["acquisition"])
            and _all_hidden_confirmed(filesystem["hidden"])
            and _refused(filesystem["fresh_s0"])
            and states["V1"]["state"]["constructor"]
            == states["V3"]["state"]["constructor"]
            and _confirmed(independent_closure["filesystem"])
            and independent_closure["filesystem"]["runtime"]["accepted"] == 0
        ),
        "P8": bool(
            _refused(configuration["mutated_s_prime"])
            and _refused(filesystem["ablated_s_prime"])
            and _refused(filesystem["mutated_s_prime"])
            and set(filesystem["feature_ablations"]) == REQUIRED_FEATURES
            and all(
                _confirmed(control["mutation"])
                and _refused(control["acquisition"])
                for control in filesystem["feature_ablations"].values()
            )
            and _confirmed(configuration["acquisition"])
            and _confirmed(filesystem["acquisition"])
        ),
        "P9": bool(
            _refused(refusal["development_ambiguity"])
            and _reason(refusal["development_ambiguity"]) == "ambiguous_public_semantics"
            and _refused(refusal["qualification_ambiguity"])
            and _reason(refusal["qualification_ambiguity"]) == "ambiguous_public_semantics"
            and _refused(refusal["non_discriminating"])
            and _reason(refusal["non_discriminating"])
            == "inherited_constructor_has_no_observed_structural_limitation"
            and refusal["states_unchanged"]
        ),
        "P10": bool(
            definition_report.get("definition_count") == 2
            and [item["family"] for item in definition_report.get("definitions", [])]
            == ["configuration", "filesystem"]
            and _refused(ablations["d_absent_execution"])
            and _confirmed(ablations["e_after_d_ablation"])
            and _refused(ablations["e_absent_execution"])
            and _confirmed(ablations["d_after_e_ablation"])
            and all(
                conservation_report.get(key) is True
                for key in (
                    "m100_live",
                    "m101_a_live",
                    "m101_b_live",
                    "m102_k_live",
                    "m102_c_live",
                    "record_registry_live",
                )
            )
            and {item["action"] for item in behavioral_executions}
            == {
                "execute-record",
                "execute-sqlite",
                "execute-m101-a",
                "execute-m101-b",
                "execute-m100",
            }
        ),
        "P11": bool(
            dependencies["s_prime_needed_for_configuration_acquisition"]
            and dependencies["s_prime_needed_for_filesystem_acquisition"]
            and dependencies["compiled_d_executes_without_s_prime"]
            and dependencies["compiled_e_executes_without_s_prime"]
            and dependencies["runtime_dependency_claimed"] is False
            and dependencies["acquisition_dependency_claimed"] is True
            and all(
                item["acquired_by_current_constructor"]
                for item in definition_report.get("definitions", [])
            )
        ),
        "P12": bool(
            _confirmed(evidence["corruption"]["write"])
            and evidence["corruption"]["consumer"].get("returncode") == 3
            and evidence["corruption"]["consumer"].get("runtime", {}).get("failed_closed")
            and _confirmed(rollback["fault"])
            and _refused(rollback["fault_blocks_e"])
            and _confirmed(rollback["rollback"])
            and rollback["restored_v2_is_byte_exact"]
            and _confirmed(rollback["reacquire_e"])
            and rollback["reacquired_v3_is_byte_exact"]
        ),
        "P13": bool(
            parity["same_v0_predecessor"]
            and parity["same_runtime_capsule"]
            and parity["same_public_demands"]
            and parity["same_action_catalogues"]
            and parity["s0_complete_image_repeated_in_more_budget_arm"]
            and parity["more_budget_repetitions"] == 32
            and parity["more_budget_total_assembled"] == 32 * closure["finite_image_size"]
            and parity["more_budget_repeated_image_identical"]
            and parity["only_causal_difference"] == "registered S-prime bytes"
        ),
        "P14": bool(
            process["scientific_invocations"] >= 35
            and process["all_isolated"]
            and process["all_imported_project_modules_empty"]
            and behavioral_conservation["all_isolated"]
            and behavioral_conservation["all_imported_project_modules_empty"]
            and process["producer_boundaries_distinct"]
            and process["all_processes_returned"]
            and boundary["qualification_materialized_after_s_prime_producer_return"]
            and boundary["filesystem_materialized_after_d_producer_return"]
        ),
        "P15": bool(
            replay_confirmed
            and evidence["pool_preflight"]["confirmed"]
            and process["scientific_invocations"] >= 35
            and process["all_external_call_counters_zero"]
            and behavioral_conservation["all_external_call_counters_zero"]
            and all(
                capsule["contains_only_bound_members"]
                for capsule in evidence["capsules"].values()
            )
        ),
    }
    if sorted(conditions, key=lambda key: int(key[1:])) != EXPECTED_PREDICATES:
        raise ValueError("M103 checker predicate set changed")
    return conditions


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m103-result-v1" or result.get("attempt") != 1:
        raise ValueError("M103 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M103 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M103 result protocol binding mismatch")
    if result.get("pool_digest") != pool.get("pool_digest"):
        raise ValueError("M103 result pool binding mismatch")
    evidence = result["scientific_evidence"]
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M103 stable evidence digest mismatch")

    replay_evidence: dict[str, Any] | None = None
    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m103_qualification as qualification

        replay_evidence = qualification.run_experiment(pool)
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)
    conditions = evaluate_conditions(evidence, replay_confirmed=replay_equal)
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m103-check-report-v1",
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
        "independent_predicate_logic": True,
        "imports_m103_runtime": False,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default=str(RESULT_PATH))
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    try:
        result = json.loads(Path(arguments.result).read_text(encoding="ascii"))
        report = check_result(result, replay=arguments.replay)
        if arguments.write:
            if REPORT_PATH.exists():
                raise ValueError("M103 check report already exists")
            REPORT_PATH.write_bytes(canonical_json(report).encode("ascii"))
    except Exception as error:
        print(
            json.dumps(
                {
                    "schema": "m103-check-report-v1",
                    "scientific_verdict": True,
                    "verdict": "negative",
                    "failed_closed": True,
                    "error": f"{type(error).__name__}: {error}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
