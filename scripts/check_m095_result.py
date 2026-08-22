"""Recompute M095's frozen conditions from the protocol, population and local evidence.

Before a run, structural conditions are computed and run-dependent conditions remain
``uncomputed``.  After a run, the checker rebuilds and reruns every qualification world and
the decisive development arms.  Recorded booleans are never accepted as their own proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from metamorphosis import m095_arms as arms  # noqa: E402
from metamorphosis import m095_chain as chain  # noqa: E402
from author_m095_qualification_pool import (  # noqa: E402
    audit as audit_pool,
    build_pool,
    build_world,
    canonical_json,
    digest,
    load_pool,
)
from run_m095_qualification import (  # noqa: E402
    _entry_record,
    file_set_digest,
    mechanism_digest,
)

EXPERIMENT = ROOT / "experiments" / "M095"
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
    *,
    detail: dict[str, object] | None = None,
) -> Condition:
    return Condition(
        identifier, name, True, not failures,
        "satisfied" if not failures else "; ".join(failures),
        detail or {},
    )


def _uncomputed(identifier: str, name: str) -> Condition:
    return Condition(
        identifier, name, False, None,
        "no armed RESULT.json exists; the condition is not inferred from development data",
    )


def load_result() -> dict[str, object] | None:
    if not RESULT_PATH.exists():
        return None
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def check_p1(protocol: dict[str, object], pool: dict[str, object]) -> Condition:
    failures = []
    if protocol.get("status") != "frozen":
        failures.append("protocol is not frozen")
    if pool.get("status") != "frozen":
        failures.append("pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        failures.append("protocol does not bind the committed pool digest")
    try:
        current, _members = mechanism_digest(protocol)
        if current != protocol.get("mechanism", {}).get("digest"):
            failures.append("mechanism files moved after freeze")
        apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
        if apparatus != protocol.get("qualification_apparatus", {}).get("digest"):
            failures.append("qualification apparatus moved after freeze")
    except Exception as error:  # noqa: BLE001 - an uncheckable binding is a failure
        failures.append(f"mechanism binding could not be checked: {error}")
    return _condition("P1", "frozen_protocol_pool_and_mechanism_are_bound", failures)


def check_p2(pool: dict[str, object]) -> Condition:
    failures = []
    generated = build_pool()
    # At freeze only the status changes from the author's draft output.  Compare everything
    # else, including every entry digest and structural axis.
    generated["status"] = pool.get("status")
    generated["pool_digest"] = pool.get("pool_digest")
    without_digest = {k: v for k, v in pool.items() if k != "pool_digest"}
    if digest(without_digest) != pool.get("pool_digest"):
        failures.append("pool digest does not match its contents")
    if {k: v for k, v in generated.items() if k != "pool_digest"} != without_digest:
        failures.append("committed population is not the authored Cartesian product")
    if len(pool.get("structures", [])) != 3 or len(pool.get("arrangements", [])) != 3:
        failures.append("population is not three structures by three arrangements")
    if len(pool.get("entries", [])) != 9:
        failures.append("population does not contain all nine entries")
    audit = audit_pool(pool)
    if not audit["passed"]:
        failures.append("one or more worlds fail the pre-run construction audit")
    if audit["chain_was_run"] is not False:
        failures.append("the preflight crossed the chain boundary")
    return _condition(
        "P2", "the_finite_structural_population_is_exhaustive_and_buildable", failures,
        detail={"entries": len(pool.get("entries", [])), "audit": audit["passed"]},
    )


def replay(pool: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m095-check-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            root = base / "population" / str(entry["id"])
            counterfactual = base / "counterfactual" / str(entry["id"])
            build_world(root, pool, entry)
            build_world(counterfactual, pool, entry)
            rows.append(_entry_record(entry, chain.run_existing(root, counterfactual)))

        def make_root(name: str) -> Path:
            return base / "development-arms" / name

        replayed_arms = {
            "arrangement": arms.run(make_root).to_dict(),
            "random_target_ceiling": arms.random_target(make_root).to_dict(),
            "more_budget_same_operations": arms.more_budget(make_root).to_dict(),
        }
    return rows, replayed_arms


def run_conditions(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object],
    replay_rows: list[dict[str, object]],
    replayed_arms: dict[str, object],
) -> list[Condition]:
    del protocol
    positives = [row for row in replay_rows if row["expected_relation"]]
    negatives = [row for row in replay_rows if not row["expected_relation"]]

    failures = [str(row["entry"]) for row in positives if not row["enabling_demonstrated"]]
    p3 = _condition(
        "P3", "every_demand_bearing_structural_world_demonstrates_enabling", failures,
        detail={"demonstrated": len(positives) - len(failures), "required": len(positives)},
    )

    failures = []
    for row in negatives:
        if row["enabling_demonstrated"]:
            failures.append(f"{row['entry']} demonstrated without a visible enabler")
        if row["world"].get("inner_call_sites") != 0:
            failures.append(f"{row['entry']} is not a measured zero-demand negative")
    p4 = _condition(
        "P4", "every_zero_inner_demand_world_remains_negative", failures,
        detail={"negative": len(negatives)},
    )

    failures = []
    unaided = 0
    descended = 0
    for row in positives:
        expected = bool(row["expected_descent"])
        actual = bool(row["descent_used"])
        if expected != actual:
            failures.append(f"{row['entry']} descent expected {expected}, measured {actual}")
        descended += int(actual and bool(row["enabling_demonstrated"]))
        unaided += int(not actual and bool(row["enabling_demonstrated"]))
    if unaided != 3 or descended != 3:
        failures.append(f"expected 3 unaided and 3 descended; measured {unaided}/{descended}")
    p5 = _condition(
        "P5", "relation_and_ranking_help_are_separate_conditions", failures,
        detail={"ranking_unaided": unaided, "failed_search_descent": descended},
    )

    failures = []
    for row in positives:
        if row["control_b_from_s0_reached"] is not False:
            failures.append(f"{row['entry']} has no negative S0 control")
        if row["a_reached"] is not True:
            failures.append(f"{row['entry']} did not reach A")
        if row["a_identified_by"] != "the_nested_operation_became_applicable":
            failures.append(f"{row['entry']} did not identify A by the reachability flip")
        if row["b_reached"] is not True or int(row["b_confirmed_by_execution"] or 0) < 1:
            failures.append(f"{row['entry']} did not execute-confirm B")
        if row["counterfactual_b_without_a_reached"] is not False:
            failures.append(f"{row['entry']} counterfactual did not remove B")
    p6 = _condition("P6", "the_causal_pillars_and_execution_confirmation_hold", failures)

    recorded = result.get("entries", [])
    recorded_by_id = {
        row.get("entry"): row for row in recorded if isinstance(row, dict)
    }
    failures = []
    if len(recorded_by_id) != len(pool["entries"]):
        failures.append("record does not contain exactly one row per population entry")
    for row in replay_rows:
        observed = recorded_by_id.get(row["entry"])
        if observed is None:
            failures.append(f"record is missing {row['entry']}")
        elif digest(observed) != digest(row):
            failures.append(f"recorded evidence for {row['entry']} differs from replay")
    p7 = _condition("P7", "preserved_entry_evidence_replays_byte_semantically", failures)

    recorded_arms = result.get("development_arms", {})
    arrangement = replayed_arms["arrangement"]
    failures = []
    if arrangement.get("outcome") != "satisfied":
        failures.append(f"arrangement arm is {arrangement.get('outcome')}")
    if arrangement.get("demonstrated") != 6:
        failures.append("arrangement arm does not demonstrate six demand-bearing points")
    if arrangement.get("demonstrated_without_descending") != 4:
        failures.append("arrangement arm does not separate the four unaided points")
    if digest(recorded_arms.get("arrangement")) != digest(arrangement):
        failures.append("recorded arrangement arm differs from replay")
    p8 = _condition("P8", "the_arrangement_domain_arm_is_a_verdict_condition", failures)

    budget = replayed_arms["more_budget_same_operations"]
    failures = []
    if budget.get("outcome") != "satisfied":
        failures.append(f"more-budget arm is {budget.get('outcome')}")
    if not budget.get("the_searcher_was_shown_alive"):
        failures.append("more-budget arm has no positive liveness control")
    if digest(recorded_arms.get("more_budget_same_operations")) != digest(budget):
        failures.append("recorded more-budget arm differs from replay")
    p9 = _condition("P9", "more_budget_over_the_same_operations_cannot_substitute_for_a", failures)

    random_arm = replayed_arms["random_target_ceiling"]
    failures = []
    if result.get("random_target_is_non_decisive") is not True:
        failures.append("random-target ceiling is presented as decisive")
    if random_arm.get("outcome") != "unrunnable":
        failures.append(f"random-target ceiling moved to {random_arm.get('outcome')}")
    if random_arm.get("rivals_that_could_touch_them") != 0:
        failures.append("random-target arm now has a causal rival and needs redesign")
    if digest(recorded_arms.get("random_target_ceiling")) != digest(random_arm):
        failures.append("recorded random-target ceiling differs from replay")
    for row in positives:
        if row["same_bound_control_to_b"] != row["same_bound_step_b"]:
            failures.append(f"{row['entry']} changed the search bound")
        if row["same_operations_offered_control"] != row["same_operations_offered_step_b"]:
            failures.append(f"{row['entry']} changed the operation count")
    p10 = _condition(
        "P10", "operation_language_and_bounds_are_fixed_and_the_ceiling_is_disclosed", failures
    )

    failures = []
    if result.get("track") != "A":
        failures.append("run is not Track A")
    if result.get("model_calls") != 0 or result.get("network_calls") != 0:
        failures.append("run used model or network calls")
    if result.get("working_tree_was_dirty_at_recording") is not False:
        failures.append("run did not start from a clean frozen commit")
    if result.get("population_is_exhaustive") is not True:
        failures.append("run does not declare exhaustive population execution")
    if result.get("pool_digest") != pool.get("pool_digest"):
        failures.append("run used another pool digest")
    expected_protocol = hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    if result.get("protocol_raw_sha256") != expected_protocol:
        failures.append("run used another protocol")
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    if result.get("prior_attempts") != withdrawn or result.get("attempt") != len(withdrawn) + 1:
        failures.append("attempt provenance does not match preserved withdrawn results")
    recomputed_result = digest({k: v for k, v in result.items() if k != "result_digest"})
    if result.get("result_digest") != recomputed_result:
        failures.append("result digest does not match its contents")
    p11 = _condition("P11", "chronology_track_a_and_no_leaked_or_rerolled_evidence", failures)
    return [p3, p4, p5, p6, p7, p8, p9, p10, p11]


def compute_report(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object] | None,
) -> dict[str, object]:
    conditions = [check_p1(protocol, pool), check_p2(pool)]
    names = [
        "every_demand_bearing_structural_world_demonstrates_enabling",
        "every_zero_inner_demand_world_remains_negative",
        "relation_and_ranking_help_are_separate_conditions",
        "the_causal_pillars_and_execution_confirmation_hold",
        "preserved_entry_evidence_replays_byte_semantically",
        "the_arrangement_domain_arm_is_a_verdict_condition",
        "more_budget_over_the_same_operations_cannot_substitute_for_a",
        "operation_language_and_bounds_are_fixed_and_the_ceiling_is_disclosed",
        "chronology_track_a_and_no_leaked_or_rerolled_evidence",
    ]
    if result is None:
        conditions += [_uncomputed(f"P{index}", name) for index, name in enumerate(names, 3)]
    else:
        replay_rows, replayed_arms = replay(pool)
        conditions += run_conditions(protocol, pool, result, replay_rows, replayed_arms)

    failed = [item.id for item in conditions if item.computed and item.passed is False]
    uncomputed = [item.id for item in conditions if not item.computed]
    verdict = "negative" if failed else ("incomplete" if uncomputed else "positive")
    report: dict[str, object] = {
        "schema": "m095-checker-v1",
        "milestone": "M095",
        "verdict": verdict,
        "verdict_rule": (
            "negative if any computed condition fails; incomplete while any condition is "
            "uncomputed; positive only when every condition is computed and true"
        ),
        "passed": sum(1 for item in conditions if item.computed and item.passed),
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
    result = load_result()
    report = compute_report(protocol, pool, result)
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
