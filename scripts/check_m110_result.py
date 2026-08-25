"""Independent M110 checker.

Evaluates P1-P24 from the canonical result and, with --replay, re-runs the experiment and compares
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
EXPERIMENT = ROOT / "experiments" / "M110"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"

EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 25)]
# The exact bytes D078 preserved. Binding them here is what makes the restored cascade a
# continuation of the frozen producer rather than an equivalent reimplementation.
PRODUCER_RESULT_BYTES = "0af98fb45a279fec9224bddbb4fa069d140cf21e94a3bb00699ba8c85e0c8009"
FEATURE_ROW_COUNT = 8
OPERATOR_TABLE = "operator_table"
SIGNAL_INTERFACE = "signal_interface"
CANDIDATE_SPACE = "candidate_space"
INSIDE_ROWS = ("7", "3")
OUTSIDE_ROW = "5"
CONSERVATION_ROW = "1"
ARM_NAMES = ("M0", "M1", "M2")

EPHEMERAL_KEYS = {
    "pid",
    "arm_pids",
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


def _worlds(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return list(evidence.get("worlds") or [])


def _row(world: dict[str, Any], key: str) -> dict[str, Any]:
    return (world.get("rows") or {}).get(key) or {}


def _every(worlds: list[dict[str, Any]], predicate) -> bool:
    return bool(worlds) and all(bool(predicate(world)) for world in worlds)


def _attribution_map_recomputes(provenance: dict[str, Any]) -> bool:
    """Recompute the cascade here, from the restored truth tables, importing nothing.

    The consumer delegates attribution to the producer module. A comparison of module names
    could never falsify that; recomputing every row from the preserved tables can.
    """
    restored = provenance.get("restored_rules") or {}
    order = provenance.get("cascade_order") or []
    recorded = provenance.get("attribution_map") or {}
    if sorted(recorded) != ["M0", "M1", "M2"] or len(order) != 2:
        return False
    cascades = {
        "M0": [],
        "M1": [restored.get(order[0])],
        "M2": [restored.get(order[0]), restored.get(order[1])],
    }
    for arm, cascade in cascades.items():
        rows = recorded.get(arm) or {}
        if sorted(int(key) for key in rows) != list(range(FEATURE_ROW_COUNT)):
            return False
        for row in range(FEATURE_ROW_COUNT):
            expected = OPERATOR_TABLE
            for rule in cascade:
                table = (rule or {}).get("truth_table") or []
                if len(table) != FEATURE_ROW_COUNT:
                    return False
                if bool(table[row]):
                    expected = rule.get("selects_component_when_true")
                    break
            if rows[str(row)] != expected:
                return False
    return True


def evaluate_conditions(evidence: dict[str, Any], *, replay_confirmed: bool) -> dict[str, bool]:
    """Predicate semantics. Deliberately imports nothing: no runtime, no orchestration."""
    preflight = evidence.get("input_preflight") or {}
    checks = preflight.get("checks") or {}
    provenance = evidence.get("provenance") or {}
    provenance_checks = provenance.get("checks") or {}
    boundary = evidence.get("boundary") or {}
    agreement = evidence.get("census_agreement") or {}
    worlds = _worlds(evidence)

    def solved(world: dict[str, Any], key: str, arm: str) -> bool:
        return bool((_row(world, key).get("solved") or {}).get(arm))

    def attributed(world: dict[str, Any], key: str, arm: str) -> Any:
        return ((_row(world, key).get("arms") or {}).get(arm) or {}).get("attributed_component")

    def truth(world: dict[str, Any], key: str) -> Any:
        return _row(world, key).get("ground_truth_component")

    return {
        # -- the boundary the result is read inside ------------------------------------------
        "P1": preflight.get("confirmed") is True
        and bool(checks)
        and all(value is True for value in checks.values()),
        "P2": provenance.get("confirmed") is True
        and provenance_checks.get("m0_state_digest_reproduced") is True
        and provenance_checks.get("m1_state_digest_reproduced") is True
        and provenance_checks.get("m2_state_digest_reproduced") is True
        and provenance_checks.get("producer_result_digest_matches") is True
        and provenance.get("producer_result_bytes_digest") == PRODUCER_RESULT_BYTES,
        "P3": boundary.get("no_capsule_held_a_producer_fixture") is True
        and checks.get("population_holds_no_census_or_label") is True
        and checks.get("no_producer_fixture_in_the_experiment_directory") is True,
        "P4": checks.get("arms_differ_only_in_the_rule_cascade") is True
        and checks.get("arms_share_one_adapter") is True
        and evidence.get("input_preflight", {}).get("arm_fields_that_differ") == ["rules"]
        and _every(
            worlds,
            lambda world: all(
                _row(world, key).get("equal_inputs_across_arms") is True
                for key in (world.get("rows") or {})
            ),
        )
        and (boundary.get("arm_capsules") or {}).get(
            "every_group_holds_one_capsule_per_arm"
        )
        is True
        and (boundary.get("arm_capsules") or {}).get(
            "every_group_shares_its_world_and_demand_bytes"
        )
        is True
        and (boundary.get("arm_capsules") or {}).get(
            "every_group_holds_distinct_state_bytes"
        )
        is True
        and (boundary.get("arm_capsules") or {}).get("capsule_member_lists_are_uniform")
        is True,
        # -- impossibility rather than an exhausted budget -----------------------------------
        "P5": _every(
            worlds,
            lambda world: ((world.get("certificates") or {}).get("fixed_point") or {}).get(
                "confirmed"
            )
            is True,
        ),
        "P6": _every(
            worlds,
            lambda world: ((world.get("certificates") or {}).get("monotone_closure") or {}).get(
                "confirmed"
            )
            is True,
        ),
        "P7": _every(
            worlds,
            lambda world: ((world.get("certificates") or {}).get("visible_function") or {}).get(
                "confirmed"
            )
            is True,
        ),
        "P8": _every(
            worlds,
            lambda world: (world.get("census") or {}).get("census_complete") is True
            and (world.get("census") or {}).get("ambiguous_rows") == [],
        ),
        # -- the geometry that makes this a different laboratory ------------------------------
        "P9": 5 in (agreement.get("rows_only_the_consumer_reaches") or [])
        and 5 in (provenance.get("producer_unreachable_rows") or []),
        "P10": agreement.get("labels_agree_on_every_shared_row") is True
        and agreement.get("consumer_label_is_world_invariant") is True,
        # -- H55-a: positive transfer inside the producer's census ----------------------------
        "P11": _every(
            worlds,
            lambda world: not solved(world, "7", "M0")
            and attributed(world, "7", "M0") == OPERATOR_TABLE
            and truth(world, "7") == SIGNAL_INTERFACE,
        ),
        "P12": _every(
            worlds,
            lambda world: solved(world, "7", "M1")
            and solved(world, "7", "M2")
            and attributed(world, "7", "M1") == SIGNAL_INTERFACE
            and attributed(world, "7", "M2") == SIGNAL_INTERFACE,
        ),
        "P13": _every(
            worlds,
            lambda world: not solved(world, "3", "M0")
            and not solved(world, "3", "M1")
            and attributed(world, "3", "M1") == OPERATOR_TABLE
            and truth(world, "3") == CANDIDATE_SPACE,
        ),
        "P14": _every(
            worlds,
            lambda world: solved(world, "3", "M2")
            and attributed(world, "3", "M2") == CANDIDATE_SPACE,
        ),
        # -- H55-b: negative transfer outside it ----------------------------------------------
        "P15": _every(
            worlds,
            lambda world: solved(world, OUTSIDE_ROW, "M0")
            and attributed(world, OUTSIDE_ROW, "M0") == OPERATOR_TABLE
            and truth(world, OUTSIDE_ROW) == OPERATOR_TABLE,
        ),
        "P16": _every(
            worlds,
            lambda world: not solved(world, OUTSIDE_ROW, "M1")
            and not solved(world, OUTSIDE_ROW, "M2")
            and attributed(world, OUTSIDE_ROW, "M1") == SIGNAL_INTERFACE
            and attributed(world, OUTSIDE_ROW, "M2") == SIGNAL_INTERFACE,
        ),
        # -- controls --------------------------------------------------------------------------
        "P17": _every(
            worlds,
            lambda world: all(
                (_row(world, key).get("deeper_bound_m0") or {}).get("confirmed") is False
                for key in INSIDE_ROWS
            ),
        ),
        "P18": _every(
            worlds, lambda world: all(solved(world, CONSERVATION_ROW, arm) for arm in ARM_NAMES)
        ),
        "P19": _every(
            worlds,
            lambda world: (world.get("ablation") or {}).get(
                "generation_two_removed_matches_m1"
            )
            is True
            and (world.get("ablation") or {}).get("generation_one_removed_matches_m0") is True
            and ((world.get("ablation") or {}).get("row_three_after_removing_generation_two") or {}).get(
                "confirmed"
            )
            is False
            and ((world.get("ablation") or {}).get("row_seven_after_removing_generation_one") or {}).get(
                "confirmed"
            )
            is False
            and ((world.get("ablation") or {}).get("row_five_after_removing_generation_one") or {}).get(
                "confirmed"
            )
            is True,
        ),
        "P20": _every(
            worlds,
            lambda world: (world.get("mutation") or {}).get("confirmed") is False
            and (world.get("corruption") or {}).get("confirmed") is False
            and (world.get("unregistered") or {}).get("confirmed") is False
            and (world.get("unregistered") or {}).get("capsule_held_the_rule_bytes") is True
            and (world.get("unregistered") or {}).get("state_held_no_rule") is True,
        ),
        "P21": _every(
            worlds, lambda world: (world.get("reach_chain") or {}).get("strict_chain") is True
        ),
        # -- instrument ------------------------------------------------------------------------
        # -- declared ceilings, measured rather than assumed --------------------------------
        "P23": _every(
            worlds,
            lambda world: ((world.get("host_shortcut") or {}).get(
                "row_three_with_a_host_widened_candidate_space"
            ) or {}).get("confirmed")
            is True
            and ((world.get("host_shortcut") or {}).get(
                "row_seven_with_a_host_widened_interface"
            ) or {}).get("confirmed")
            is True,
        ),
        "P24": _attribution_map_recomputes(provenance),
        "P22": boundary.get("all_processes_isolated") is True
        and boundary.get("all_processes_zero_external_calls") is True
        and evidence.get("runtime", {}).get("matches_canonical") is True
        and bool(replay_confirmed),
    }


def _read_canonical(path: Path, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("ascii"))
    if canonical_json(value).encode("ascii") != raw:
        raise RuntimeError("%s is not canonical" % label)
    return value


def verify_result(result: dict[str, Any]) -> dict[str, bool]:
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    evidence = result.get("scientific_evidence") or {}
    return {
        "schema_is_the_declared_one": result.get("schema") == "m110-result-v1",
        "milestone_is_m110": result.get("milestone") == "M110",
        "hypothesis_is_h55": result.get("hypothesis") == "H55",
        "attempt_is_the_first": result.get("attempt") == 1,
        "result_digest_recomputes": result.get("result_digest") == digest(payload),
        "stable_evidence_digest_recomputes": result.get("stable_evidence_digest")
        == digest(stable_projection(evidence)),
        "zero_model_calls": result.get("model_calls") == 0,
        "zero_network_calls": result.get("network_calls") == 0,
        "zero_remote_execution_calls": result.get("remote_execution_calls") == 0,
    }


def replay(evidence: dict[str, Any]) -> dict[str, Any]:
    from scripts.run_m110_qualification import run_experiment  # noqa: PLC0415

    produced = run_experiment()
    return {
        "performed": True,
        "equal": stable_projection(produced) == stable_projection(evidence),
        "replayed_stable_evidence_digest": digest(stable_projection(produced)),
        "recorded_stable_evidence_digest": digest(stable_projection(evidence)),
    }


def check(*, result_path: Path, report_path: Path | None, do_replay: bool) -> dict[str, Any]:
    result = _read_canonical(result_path, "M110 result")
    evidence = result.get("scientific_evidence") or {}
    integrity = verify_result(result)
    replay_report = (
        replay(evidence) if do_replay else {"performed": False, "equal": False}
    )
    conditions = evaluate_conditions(evidence, replay_confirmed=replay_report.get("equal"))
    missing = [name for name in EXPECTED_PREDICATES if name not in conditions]
    extra = [name for name in conditions if name not in EXPECTED_PREDICATES]
    report = {
        "schema": "m110-check-report-v1",
        "milestone": "M110",
        "hypothesis": "H55",
        "result_digest": result.get("result_digest"),
        "protocol_digest": result.get("protocol_digest"),
        "population_digest": result.get("population_digest"),
        "producer_result_digest": result.get("producer_result_digest"),
        "integrity": integrity,
        "conditions": {name: bool(conditions[name]) for name in EXPECTED_PREDICATES if name in conditions},
        "uncomputed_conditions": missing,
        "undeclared_conditions": extra,
        "true_count": sum(1 for name in EXPECTED_PREDICATES if conditions.get(name)),
        "false_count": sum(
            1 for name in EXPECTED_PREDICATES if name in conditions and not conditions[name]
        ),
        "replay": replay_report,
        "every_predicate_computed": not missing,
        "verdict": "positive"
        if not missing and all(integrity.values()) and all(conditions.values())
        else "negative",
    }
    report["report_digest"] = digest({k: v for k, v in report.items()})
    if report_path is not None:
        with report_path.open("xb") as handle:
            handle.write(canonical_json(report).encode("ascii"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default=str(RESULT_PATH))
    parser.add_argument("--report", default=None)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    arguments = parser.parse_args()
    report_path = None
    if arguments.write_report:
        report_path = Path(arguments.report) if arguments.report else REPORT_PATH
    try:
        report = check(
            result_path=Path(arguments.result),
            report_path=report_path,
            do_replay=arguments.replay,
        )
    except Exception as error:  # noqa: BLE001 - the refusal is the observation
        print(
            json.dumps(
                {
                    "schema": "m110-check-refusal-v1",
                    "failed_closed": True,
                    "error": "%s: %s" % (type(error).__name__, error),
                },
                sort_keys=True,
            )
        )
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
