"""Independent M111 checker.

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
EXPERIMENT = ROOT / "experiments" / "M111"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"

EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 25)]
# The bytes D078 and D079 preserved. Binding them here is what makes M111 a continuation rather than
# a rebuild that happens to behave the same way.
PRODUCER_RESULT_BYTES = "0af98fb45a279fec9224bddbb4fa069d140cf21e94a3bb00699ba8c85e0c8009"
CONSUMER_RESULT_BYTES = "163a46dadd815d98d03fede22905a181c4d406a19d391c5ee2631efc3a2488e3"
TERMINAL_STATE_DIGEST_PREFIX = "5c08fa30"
AMBIGUOUS_ROW = 3
UPPER_ROW = 7
MONOTONE_RULE_SPACE = 18
OPERATOR_TABLE = "operator_table"
SIGNAL_INTERFACE = "signal_interface"
CANDIDATE_SPACE = "candidate_space"
PROBE_ORDERS = ("candidates_first", "signals_first")
DETERMINED_FIRST = ("determined_then_A", "determined_then_B")

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
    """Only the ambiguous stratum carries arms; witness worlds contribute record, not competence."""
    return [
        item
        for item in (evidence.get("worlds") or [])
        if item.get("stratum") == "ambiguous"
    ]


def _witness(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in (evidence.get("worlds") or []) if item.get("stratum") == "witness"
    ]


def _every(worlds: list[dict[str, Any]], predicate) -> bool:
    return bool(worlds) and all(bool(predicate(world)) for world in worlds)


def _static(world: dict[str, Any], arm: str, sequence: str) -> dict[str, Any]:
    return ((world.get("static_arms") or {}).get(arm) or {}).get(sequence) or {}


def _diag(world: dict[str, Any], force: str, order: str, sequence: str) -> dict[str, Any]:
    return (
        ((world.get("diagnostic") or {}).get(force) or {}).get(order) or {}
    ).get(sequence) or {}


def _second_resolved(summary: dict[str, Any]) -> bool:
    """Did the *ambiguous* demand, which is always the second in a determined-first sequence, land?"""
    outcomes = summary.get("outcomes") or []
    return len(outcomes) == 2 and bool(outcomes[1].get("confirmed")) and bool(
        outcomes[1].get("executes_to_target")
    )


def evaluate_conditions(evidence: dict[str, Any], *, replay_confirmed: bool) -> dict[str, bool]:
    """Predicate semantics. Deliberately imports nothing: no runtime, no orchestration."""
    preflight = evidence.get("input_preflight") or {}
    checks = preflight.get("checks") or {}
    provenance = evidence.get("provenance") or {}
    provenance_checks = provenance.get("checks") or {}
    boundary = evidence.get("boundary") or {}
    expressibility = evidence.get("expressibility") or {}
    generation_three = evidence.get("generation_three") or {}
    pooled = evidence.get("pooled_record") or {}
    worlds = _worlds(evidence)

    return {
        "P1": preflight.get("confirmed") is True
        and bool(checks)
        and all(value is True for value in checks.values()),
        "P2": provenance.get("confirmed") is True
        and all(value is True for value in provenance_checks.values())
        and provenance.get("producer_result_bytes_digest") == PRODUCER_RESULT_BYTES
        and provenance.get("consumer_result_bytes_digest") == CONSUMER_RESULT_BYTES
        and str(
            (provenance.get("restored_state_digests") or {}).get("M2_terminal") or ""
        ).startswith(TERMINAL_STATE_DIGEST_PREFIX),
        "P3": boundary.get("no_capsule_held_a_producer_fixture") is True
        and checks.get("population_holds_no_census_pair_or_label") is True
        and checks.get("no_producer_fixture_in_the_experiment_directory") is True,
        "P4": checks.get("arms_share_one_adapter") is True
        and len(preflight.get("arm_adapter_digests") or []) == 1
        and checks.get("probe_budget_is_one") is True,
        # -- the exhibit: one observation, two answers ---------------------------------------
        "P5": _every(
            worlds,
            lambda world: (world.get("ambiguous_pair") or {}).get("same_feature_row") is True
            and (world.get("ambiguous_pair") or {}).get("different_components") is True
            and (world.get("ambiguous_pair") or {}).get("row") == AMBIGUOUS_ROW,
        ),
        "P6": _every(
            worlds,
            lambda world: (world.get("census") or {}).get("census_complete") is True
            and (world.get("census") or {}).get("ambiguous_rows") == [AMBIGUOUS_ROW],
        )
        and bool(_witness(evidence))
        and all(
            UPPER_ROW in ((item.get("base_survey") or {}).get("determined_rows") or [])
            for item in _witness(evidence)
        ),
        # -- the expressibility lemma ----------------------------------------------------------
        "P7": (expressibility.get("M1") or {}).get("separating_program_count") == 0
        and (expressibility.get("M1") or {}).get("closed_by_monotonicity_lemma") is True
        and (expressibility.get("M1") or {}).get("rule_space_size") == MONOTONE_RULE_SPACE,
        "P8": (expressibility.get("M2") or {}).get("rule_space_size", 0) > MONOTONE_RULE_SPACE
        and (expressibility.get("M2") or {}).get("separating_program_count", 0) > 0
        and provenance_checks.get("acquired_operator_is_non_monotone") is True,
        "P9": (expressibility.get("M2") or {}).get("non_monotone_in_monotone_space") == 0
        and (expressibility.get("M2") or {}).get("non_monotone_in_complete_space", 0) > 0,
        "P10": (evidence.get("ablated_acquisition") or {}).get("confirmed") is False
        and (generation_three.get("acquisition") or {}).get("confirmed") is True,
        "P11": pooled.get("no_episodes_fixture_in_any_capsule") is True
        and (generation_three.get("acquisition") or {}).get("labels_are_lineage_determined")
        is True
        and pooled.get("undetermined") == [AMBIGUOUS_ROW]
        and pooled.get("worlds_contributing", 0) > 1
        and generation_three.get("one_policy_for_the_whole_population") is True,
        "P12": AMBIGUOUS_ROW in (generation_three.get("policy_fires_on") or [])
        and not (
            set(pooled.get("determined") or [])
            & set(generation_three.get("policy_fires_on") or [])
        ),
        "P13": _every(
            worlds,
            lambda world: (world.get("probe_rollback") or {}).get(
                "every_probe_left_the_state_unchanged"
            )
            is True
            and (world.get("probe_rollback") or {}).get("no_probe_is_an_adoption") is True,
        ),
        # -- every static arm fails at least one ------------------------------------------------
        "P14": _every(
            worlds,
            lambda world: not _second_resolved(_static(world, "M0", "determined_then_A"))
            and not _second_resolved(_static(world, "M0", "determined_then_B"))
            and not _second_resolved(_static(world, "M1", "determined_then_A"))
            and not _second_resolved(_static(world, "M1", "determined_then_B")),
        ),
        "P15": _every(
            worlds,
            lambda world: _second_resolved(_static(world, "M2", "determined_then_A"))
            and not _second_resolved(_static(world, "M2", "determined_then_B")),
        ),
        "P16": _every(
            worlds,
            lambda world: _second_resolved(_static(world, "always_signal", "determined_then_B"))
            and not _second_resolved(_static(world, "always_signal", "determined_then_A")),
        ),
        # -- the diagnostic lineage --------------------------------------------------------------
        "P17": _every(
            worlds,
            lambda world: all(
                _second_resolved(_diag(world, "policy", order, sequence))
                for order in PROBE_ORDERS
                for sequence in DETERMINED_FIRST
            ),
        ),
        "P18": _every(
            worlds,
            lambda world: all(
                not _second_resolved(_diag(world, "never", order, "determined_then_B"))
                for order in PROBE_ORDERS
            ),
        ),
        "P19": _every(
            worlds,
            lambda world: all(
                not _second_resolved(_diag(world, "always", order, "determined_then_B"))
                for order in PROBE_ORDERS
            ),
        ),
        "P20": _every(
            worlds,
            lambda world: all(
                _diag(world, "policy", order, sequence).get("starting_probe_budget")
                == _diag(world, "always", order, sequence).get("starting_probe_budget")
                and _diag(world, "policy", order, sequence).get("probes_spent", 0)
                <= _diag(world, "always", order, sequence).get("probes_spent", 0)
                for order in PROBE_ORDERS
                for sequence in DETERMINED_FIRST
            ),
        ),
        # -- causal controls ------------------------------------------------------------------
        "P21": _every(
            worlds,
            lambda world: (world.get("ablation") or {}).get("removal_returns_to_m2_byte_exactly")
            is True
            and not _second_resolved(
                (world.get("ablation") or {}).get("generation_three_removed") or {}
            ),
        ),
        "P22": _every(
            worlds,
            lambda world: not _second_resolved(world.get("mutation") or {})
            and (world.get("corruption") or {}).get("confirmed") is False,
        ),
        "P23": _every(
            worlds,
            lambda world: all(
                _second_resolved(_diag(world, "policy", order, "determined_then_A"))
                for order in PROBE_ORDERS
            )
            and all(
                (_diag(world, "policy", order, sequence).get("outcomes") or [{}])[0].get(
                    "confirmed"
                )
                is True
                for order in PROBE_ORDERS
                for sequence in DETERMINED_FIRST
            ),
        ),
        "P24": boundary.get("all_processes_isolated") is True
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
        "schema_is_the_declared_one": result.get("schema") == "m111-result-v1",
        "milestone_is_m111": result.get("milestone") == "M111",
        "hypothesis_is_h56": result.get("hypothesis") == "H56",
        "attempt_is_the_first": result.get("attempt") == 1,
        "result_digest_recomputes": result.get("result_digest") == digest(payload),
        "stable_evidence_digest_recomputes": result.get("stable_evidence_digest")
        == digest(stable_projection(evidence)),
        "zero_model_calls": result.get("model_calls") == 0,
        "zero_network_calls": result.get("network_calls") == 0,
        "zero_remote_execution_calls": result.get("remote_execution_calls") == 0,
    }


def replay(evidence: dict[str, Any]) -> dict[str, Any]:
    from scripts.run_m111_qualification import run_experiment  # noqa: PLC0415

    produced = run_experiment()
    return {
        "performed": True,
        "equal": stable_projection(produced) == stable_projection(evidence),
        "replayed_stable_evidence_digest": digest(stable_projection(produced)),
        "recorded_stable_evidence_digest": digest(stable_projection(evidence)),
    }


def check(*, result_path: Path, report_path: Path | None, do_replay: bool) -> dict[str, Any]:
    result = _read_canonical(result_path, "M111 result")
    evidence = result.get("scientific_evidence") or {}
    integrity = verify_result(result)
    replay_report = replay(evidence) if do_replay else {"performed": False, "equal": False}
    conditions = evaluate_conditions(evidence, replay_confirmed=replay_report.get("equal"))
    missing = [name for name in EXPECTED_PREDICATES if name not in conditions]
    extra = [name for name in conditions if name not in EXPECTED_PREDICATES]
    report = {
        "schema": "m111-check-report-v1",
        "milestone": "M111",
        "hypothesis": "H56",
        "result_digest": result.get("result_digest"),
        "protocol_digest": result.get("protocol_digest"),
        "population_digest": result.get("population_digest"),
        "producer_result_digest": result.get("producer_result_digest"),
        "consumer_result_digest": result.get("consumer_result_digest"),
        "integrity": integrity,
        "conditions": {
            name: bool(conditions[name]) for name in EXPECTED_PREDICATES if name in conditions
        },
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
                    "schema": "m111-check-refusal-v1",
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
