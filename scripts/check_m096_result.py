"""Independently recompute M096's frozen conditions and paired evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from author_m096_qualification_pool import (  # noqa: E402
    audit as audit_pool,
    build_pool,
    canonical_json,
    digest,
    load_pool,
)
from run_m095_qualification import file_set_digest  # noqa: E402
from run_m096_qualification import mechanism_digest, replay_population  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M096"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"


@dataclass
class Condition:
    id: str
    name: str
    computed: bool
    passed: bool | None
    evidence: str
    detail: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "computed": self.computed,
            "passed": self.passed,
            "evidence": self.evidence,
            "detail": self.detail,
        }


def _condition(
    identifier: str,
    name: str,
    failures: list[str],
    detail: dict[str, object] | None = None,
) -> Condition:
    return Condition(
        identifier,
        name,
        True,
        not failures,
        "satisfied" if not failures else "; ".join(failures),
        detail or {},
    )


def _uncomputed(identifier: str, name: str) -> Condition:
    return Condition(
        identifier,
        name,
        False,
        None,
        "no armed RESULT.json exists; development evidence is not substituted",
    )


def load_result() -> dict[str, object] | None:
    return (
        json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if RESULT_PATH.exists()
        else None
    )


def check_p1(protocol: dict[str, object], pool: dict[str, object]) -> Condition:
    failures: list[str] = []
    if protocol.get("status") != "frozen":
        failures.append("protocol is not frozen")
    if pool.get("status") != "frozen":
        failures.append("pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        failures.append("protocol does not bind the committed pool")
    try:
        measured, _members = mechanism_digest(protocol)
        if protocol.get("mechanism", {}).get("digest") != measured:
            failures.append("mechanism files moved after freeze")
        apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
        if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
            failures.append("qualification apparatus moved after freeze")
    except Exception as error:  # noqa: BLE001
        failures.append(f"bindings could not be recomputed: {error}")
    return _condition("P1", "frozen_protocol_pool_mechanism_and_checker_are_bound", failures)


def check_p2(pool: dict[str, object]) -> Condition:
    failures: list[str] = []
    generated = build_pool(status="frozen")
    if generated != pool:
        failures.append("committed population is not the authored Cartesian product")
    if len(pool.get("structures", [])) != 4 or len(pool.get("arrangements", [])) != 3:
        failures.append("population is not four structures by three arrangements")
    if len(pool.get("entries", [])) != 12:
        failures.append("population does not contain all twelve entries")
    audit = audit_pool(pool)
    if not audit["passed"] or audit["chain_was_run"] is not False:
        failures.append("S0-only population audit failed or crossed the freeze boundary")
    return _condition(
        "P2",
        "fresh_finite_population_is_exhaustive_buildable_and_unrun_before_freeze",
        failures,
        {"entries": len(pool.get("entries", [])), "preflight_passed": audit["passed"]},
    )


def _method_keys(method_source: object) -> tuple[str, ...] | None:
    if not isinstance(method_source, str):
        return None
    try:
        function = next(
            node for node in ast.parse(method_source).body if isinstance(node, ast.FunctionDef)
        )
    except (SyntaxError, StopIteration):
        return None
    returns = [node.value for node in ast.walk(function) if isinstance(node, ast.Return)]
    if len(returns) != 1 or not isinstance(returns[0], ast.Dict):
        return None
    keys = [
        key.value
        for key in returns[0].keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    ]
    if len(keys) != len(returns[0].keys) or len(keys) != len(set(keys)):
        return None
    return tuple(sorted(keys))


def run_conditions(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object],
    replay_rows: list[dict[str, object]],
) -> list[Condition]:
    del protocol
    positives = [row for row in replay_rows if row["expected_relation"]]
    negatives = [row for row in replay_rows if not row["expected_relation"]]

    failures = [
        str(row["entry"])
        for row in positives
        if not row["contract_safe"]["enabling_demonstrated"]
    ]
    p3 = _condition(
        "P3",
        "every_demand_bearing_world_composes_under_the_exact_contract",
        failures,
        {"demonstrated": len(positives) - len(failures), "required": len(positives)},
    )

    failures = []
    for row in negatives:
        exact = row["contract_safe"]
        if exact["enabling_demonstrated"]:
            failures.append(f"{row['entry']} demonstrated without visible A demand")
        if exact["world"].get("inner_call_sites") != 0:
            failures.append(f"{row['entry']} is not a measured zero-demand negative")
    p4 = _condition("P4", "every_zero_inner_demand_world_remains_negative", failures)

    failures = []
    unaided = descended = 0
    for row in positives:
        actual = bool(row["contract_safe"]["descent_used"])
        expected = bool(row["expected_descent"])
        if actual != expected:
            failures.append(f"{row['entry']} descent expected {expected}, measured {actual}")
        unaided += int(not actual and bool(row["contract_safe"]["enabling_demonstrated"]))
        descended += int(actual and bool(row["contract_safe"]["enabling_demonstrated"]))
    if (unaided, descended) != (4, 4):
        failures.append(f"expected 4 unaided and 4 descended, measured {unaided}/{descended}")
    p5 = _condition(
        "P5",
        "ranking_unaided_and_failed_search_descent_are_both_qualified",
        failures,
        {"ranking_unaided": unaided, "failed_search_descent": descended},
    )

    failures = []
    for row in positives:
        exact = row["contract_safe"]
        if exact["control_b_from_s0_reached"] is not False:
            failures.append(f"{row['entry']} lacks a negative S0 control")
        if exact["a_reached"] is not True:
            failures.append(f"{row['entry']} did not reach A")
        if exact["a_identified_by"] != "the_nested_operation_became_applicable":
            failures.append(f"{row['entry']} did not identify A from the applicability flip")
        if exact["b_reached"] is not True or int(exact["b_confirmed_by_execution"] or 0) < 1:
            failures.append(f"{row['entry']} did not execution-confirm B")
        if exact["counterfactual_b_without_a_reached"] is not False:
            failures.append(f"{row['entry']} did not remove B in the without-A counterfactual")
    p6 = _condition("P6", "all_causal_pillars_and_execution_confirmation_hold", failures)

    failures = []
    for row in positives:
        step_a = row["contract_safe"]["chain"].get("step_a") or {}
        keys = _method_keys(step_a.get("adopted_method"))
        required = tuple(sorted(item[0] for item in step_a.get("requirement", [])))
        if keys != required:
            failures.append(f"{row['entry']} adopted A with keys {keys}, required {required}")
    p7 = _condition("P7", "every_adopted_enabler_has_an_exact_closed_output_contract", failures)

    failures = []
    partial = [row for row in positives if row["structure"] != "complete_minimal_contract"]
    complete = [row for row in positives if row["structure"] == "complete_minimal_contract"]
    for row in complete:
        if not row["legacy_subset"]["enabling_demonstrated"]:
            failures.append(f"{row['entry']} failed the paired legacy liveness control")
    for row in positives:
        if row["legacy_subset"]["world"] != row["contract_safe"]["world"]:
            failures.append(f"{row['entry']} paired arms measured different S0 worlds")
    p8 = _condition(
        "P8",
        "paired_legacy_sensitivity_arm_is_runnable_matched_and_non_decisive",
        failures,
        {
            "partial_contract_entries": len(partial),
            "partial_legacy_failures": sum(
                not bool(row["legacy_subset"]["enabling_demonstrated"])
                for row in partial
            ),
            "complete_liveness_controls": len(complete),
        },
    )

    failures = []
    recorded = {
        row.get("entry"): row
        for row in result.get("entries", [])
        if isinstance(row, dict)
    }
    if len(recorded) != len(pool["entries"]):
        failures.append("record does not contain exactly one row per frozen entry")
    for row in replay_rows:
        if row["entry"] not in recorded:
            failures.append(f"record is missing {row['entry']}")
        elif digest(recorded[row["entry"]]) != digest(row):
            failures.append(f"recorded evidence for {row['entry']} differs from replay")
    p9 = _condition("P9", "all_paired_evidence_replays_byte_semantically", failures)

    failures = []
    for row in replay_rows:
        exact = row["contract_safe"]
        legacy = row["legacy_subset"]
        if exact["same_bound_control_to_b"] != legacy["same_bound_control_to_b"]:
            failures.append(f"{row['entry']} paired control bound differs")
        if exact["same_operations_offered_control"] != legacy["same_operations_offered_control"]:
            failures.append(f"{row['entry']} paired control operation count differs")
    if result.get("track") != "A":
        failures.append("run is not Track A")
    if result.get("model_calls") != 0 or result.get("network_calls") != 0:
        failures.append("model or network calls entered qualification")
    if result.get("remote_execution") is not False:
        failures.append("qualification was not recorded as local-only")
    if result.get("working_tree_was_dirty_at_recording") is not False:
        failures.append("run did not start from a clean frozen commit")
    if result.get("population_is_exhaustive") is not True:
        failures.append("run did not execute the exhaustive population")
    if result.get("pool_digest") != pool.get("pool_digest"):
        failures.append("result used another pool")
    if result.get("protocol_raw_sha256") != hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest():
        failures.append("result used another protocol")
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    if result.get("prior_attempts") != withdrawn or result.get("attempt") != len(withdrawn) + 1:
        failures.append("attempt provenance does not match preserved prior artifacts")
    recomputed = digest({key: value for key, value in result.items() if key != "result_digest"})
    if result.get("result_digest") != recomputed:
        failures.append("result digest does not match its contents")
    p10 = _condition(
        "P10", "fixed_search_chronology_track_a_and_local_only_execution", failures
    )
    return [p3, p4, p5, p6, p7, p8, p9, p10]


def compute_report(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object] | None,
) -> dict[str, object]:
    conditions = [check_p1(protocol, pool), check_p2(pool)]
    names = [
        "every_demand_bearing_world_composes_under_the_exact_contract",
        "every_zero_inner_demand_world_remains_negative",
        "ranking_unaided_and_failed_search_descent_are_both_qualified",
        "all_causal_pillars_and_execution_confirmation_hold",
        "every_adopted_enabler_has_an_exact_closed_output_contract",
        "paired_legacy_sensitivity_arm_is_runnable_matched_and_non_decisive",
        "all_paired_evidence_replays_byte_semantically",
        "fixed_search_chronology_track_a_and_local_only_execution",
    ]
    if result is None:
        conditions.extend(
            _uncomputed(f"P{index}", name) for index, name in enumerate(names, 3)
        )
    else:
        conditions.extend(run_conditions(protocol, pool, result, replay_population(pool)))
    failed = [item.id for item in conditions if item.computed and item.passed is False]
    uncomputed = [item.id for item in conditions if not item.computed]
    verdict = "negative" if failed else ("incomplete" if uncomputed else "positive")
    report: dict[str, object] = {
        "schema": "m096-checker-v1",
        "milestone": "M096",
        "verdict": verdict,
        "verdict_rule": (
            "negative if any computed condition fails; incomplete while any condition is "
            "uncomputed; positive only when all ten conditions are computed and true"
        ),
        "passed": sum(bool(item.passed) for item in conditions if item.computed),
        "failed": len(failed),
        "uncomputed": len(uncomputed),
        "failed_conditions": failed,
        "uncomputed_conditions": uncomputed,
        "conditions": {item.id: item.to_dict() for item in conditions},
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    report = compute_report(protocol, pool, load_result())
    if not args.no_write:
        (EXPERIMENT / "CHECK_REPORT.json").write_text(
            canonical_json(report) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_result and report["verdict"] != "positive":
        return 1
    if args.strict and report["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
