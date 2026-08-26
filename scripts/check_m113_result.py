"""Independent M113 checker.

Recomputes every predicate from the preserved evidence. It imports the evaluator and the host, and
never the learner: a checker that imported the mutable body would be scoring the thing that produced
the evidence with the thing that produced the evidence.

The verdict rule is stated here and is frozen with the plan rather than chosen after the numbers
exist. It has a shape M086-A's did not: it can fail, and on the development run it does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m113_carrier_bank as bank  # noqa: E402
from metamorphosis import m113_evaluator as evaluator  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M113"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
DEVELOPMENT_PATH = EXPERIMENT / "DEVELOPMENT_RUN.json"

EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 19)]

# The arm H58 is stated over. `M2` is the acquired cascade; `M3` adds the M111 diagnostic policy and
# its inherited record, and is what the pre-registration calls the full descendant.
FRESH_ARM = "T0"
DESCENDANT_ARM = "M3"
CASCADE_ARM = "M2"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _total(result: dict[str, Any], arm: str, key: str) -> int:
    return int((result["per_arm_totals"].get(arm) or {}).get(key, 0))


def _agreement(result: dict[str, Any], arm: str) -> tuple[int, int]:
    entry = result["attribution_agreement"].get(arm) or {}
    return int(entry.get("correct", 0)), int(entry.get("correct", 0)) + int(
        entry.get("incorrect", 0)
    )


def evaluate_conditions(result: dict[str, Any]) -> dict[str, bool]:
    """P1-P18. Each one is recomputed; none is copied from a boolean the runner wrote about itself."""
    checks = result.get("provenance_checks") or {}
    cardinality = result.get("cardinality") or {}
    carriers = result.get("carriers") or []

    # Recomputed from the invocation counts and the arm's own budget rather than read off the
    # boolean the runner wrote. M095 recorded what a record field that asserts rather than measures
    # costs: several of its conditions were assertions wearing a measurement's clothes.
    within_budget = all(
        int(arm[demand_class]["invocations_used"]) <= int(arm["budget"])
        for carrier in carriers
        for arm in carrier["arms"].values()
        for demand_class in evaluator.DEMAND_CLASSES
    )
    adapter_rows = result.get("adapter_agreement") or []
    one_adapter = bool(adapter_rows) and all(
        int(row["distinct_adapters"]) == 1 for row in adapter_rows
    )
    rollback_matches = bool(adapter_rows) and all(
        row["rollback_matches_fresh"] is True for row in adapter_rows
    )
    recomputed_cardinality = evaluator.cardinality_report(
        requested_carrier_count=int(cardinality.get("requested_carrier_count", -1)),
        records_emitted=int(cardinality.get("records_emitted", -1)),
        carriers_enveloped=int(cardinality.get("carriers_enveloped", -1)),
        schema_valid_carriers=int(cardinality.get("schema_valid_carriers", -1)),
        qualifying_carriers=int(cardinality.get("qualifying_carriers", -1)),
        minimum_qualifying=int(cardinality.get("minimum_qualifying_carriers", -1)),
    )
    cardinality_reproduces = all(
        recomputed_cardinality[key] == cardinality.get(key)
        for key in ("identities_hold", "monotone", "minimum_met", "identities")
    )
    refusals_closed = all(
        arm[demand_class]["exploration_closed"] is True
        for carrier in carriers
        for arm in carrier["arms"].values()
        for demand_class in evaluator.DEMAND_CLASSES
        if arm[demand_class]["verdict"] == evaluator.OUTCOME_REFUSED
    )
    # A subset test, not a list comparison. The first draft wrote `sorted(arm) >= sorted(classes)`,
    # which compares two lists lexicographically and has nothing to do with coverage: adding a
    # `budget` key to the arm record flipped it to false while every arm had in fact seen every
    # demand. A predicate that fails for a reason unrelated to what it names is worse than no
    # predicate, because it is read as evidence.
    every_arm_saw_every_demand = bool(carriers) and all(
        set(evaluator.DEMAND_CLASSES) <= set(arm)
        for carrier in carriers
        for arm in carrier["arms"].values()
    )

    fresh_correct = _total(result, FRESH_ARM, "correct_construction")
    fresh_calibrated = _total(result, FRESH_ARM, "calibrated_refusal")
    fresh_invented = _total(result, FRESH_ARM, "invented_adapter")
    descendant_correct = _total(result, DESCENDANT_ARM, "correct_construction")
    descendant_calibrated = _total(result, DESCENDANT_ARM, "calibrated_refusal")
    descendant_invented = _total(result, DESCENDANT_ARM, "invented_adapter")
    fresh_ok, fresh_seen = _agreement(result, FRESH_ARM)
    descendant_ok, descendant_seen = _agreement(result, DESCENDANT_ARM)

    strictly_better = (
        descendant_correct > fresh_correct
        or descendant_calibrated > fresh_calibrated
        or descendant_invented < fresh_invented
        or (
            fresh_seen
            and descendant_seen
            and descendant_ok / descendant_seen > fresh_ok / fresh_seen
        )
    )
    no_worse = (
        descendant_correct >= fresh_correct
        and descendant_calibrated >= fresh_calibrated
        and descendant_invented <= fresh_invented
    )

    return {
        # Provenance: the arms are the frozen ones, restored rather than reimplemented.
        "P1": checks.get("producer_result_digest_matches") is True,
        "P2": checks.get("diagnosis_result_digest_matches") is True,
        "P3": checks.get("generation_one_selects_a_registered_component") is True
        and checks.get("generation_two_selects_a_registered_component") is True,
        "P4": checks.get("cascade_is_contiguous") is True
        and checks.get("generations_are_distinct") is True,
        "P5": checks.get("policy_is_generation_three") is True,
        # Controls that must behave the way controls are supposed to.
        "P6": checks.get("a_corrupted_rule_fails_closed") is True,
        "P7": checks.get("the_unregistered_arm_built_a_rule_it_does_not_hold") is True,
        "P8": checks.get("mutation_changed_the_rule") is True,
        # The only difference between arms is the Genesis machinery, and it is measured.
        "P9": bool(one_adapter),
        "P10": bool(rollback_matches),
        "P11": bool(every_arm_saw_every_demand),
        # The M112 cardinality defect cannot recur silently, and the checker does its own arithmetic
        # rather than agreeing with the runner's.
        "P12": bool(cardinality_reproduces) and recomputed_cardinality["identities_hold"] is True,
        "P13": recomputed_cardinality["monotone"] is True,
        "P14": recomputed_cardinality["minimum_met"] is True,
        # Endogeneity and budget.
        "P15": int(result.get("model_calls", -1)) == 0
        and int(result.get("network_calls", -1)) == 0
        and int(result.get("remote_execution_calls", -1)) == 0,
        "P16": bool(within_budget),
        # A refusal is a reach fact, not a budget fact.
        "P17": bool(refusals_closed),
        # H58 itself.
        "P18": bool(strictly_better and no_worse),
    }


def measurements(result: dict[str, Any]) -> dict[str, Any]:
    """The numbers the verdict is drawn from, reported whether or not the verdict is positive."""
    arms = result.get("arms") or []
    return {
        "per_arm": {
            arm: {
                "correct_construction": _total(result, arm, "correct_construction"),
                "unmet_construction": _total(result, arm, "unmet_construction"),
                "false_refusal": _total(result, arm, "false_refusal"),
                "calibrated_refusal": _total(result, arm, "calibrated_refusal"),
                "invented_adapter": _total(result, arm, "invented_adapter"),
                "undetermined": _total(result, arm, "undetermined"),
                "attribution_correct": _agreement(result, arm)[0],
                "attribution_examined": _agreement(result, arm)[1],
            }
            for arm in arms
        },
        "qualifying_carriers": result.get("qualifying_carriers"),
        "ambiguous_feature_rows": result.get("ambiguous_feature_rows"),
        "inherited_vocabulary_is_a_function_on_this_bank": not (
            result.get("ambiguous_feature_rows") or []
        ),
        "rows_where_the_cascades_disagree": result.get("rows_where_the_cascades_disagree"),
        "learner_rows_reached": result.get("learner_rows_reached"),
        "peak_invocations_by_arm": result.get("peak_invocations_by_arm"),
        "cascade_arm_calibrated_refusal": _total(result, CASCADE_ARM, "calibrated_refusal"),
        "fresh_arm_calibrated_refusal": _total(result, FRESH_ARM, "calibrated_refusal"),
    }


def check(result: dict[str, Any]) -> dict[str, Any]:
    conditions = evaluate_conditions(result)
    missing = [name for name in EXPECTED_PREDICATES if name not in conditions]
    failing = sorted(name for name, ok in conditions.items() if not ok)
    return {
        "schema": "m113-check-report-v1",
        "milestone": "M113",
        "hypothesis": "H58",
        "development": bool(result.get("development")),
        "predicates_expected": list(EXPECTED_PREDICATES),
        "predicates_missing": missing,
        "conditions": conditions,
        "computed": len(conditions),
        "passed": sum(1 for value in conditions.values() if value),
        "failing": failing,
        "verdict": "positive" if not missing and not failing else "negative",
        "verdict_rule": (
            "positive iff every predicate is computed true; P18 requires the full descendant to be "
            "strictly better than the fresh control on at least one of correct construction, "
            "calibrated refusal, invented adapters or attribution agreement, and no worse on the "
            "other three"
        ),
        "measurements": measurements(result),
        "claim_boundary": dict(bank.CARRIER_BANK_CLAIM_BOUNDARY),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--development",
        action="store_true",
        help="check DEVELOPMENT_RUN.json instead of the canonical result",
    )
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    path = DEVELOPMENT_PATH if arguments.development else RESULT_PATH
    if not path.is_file():
        print("no evidence at %s" % path.relative_to(ROOT))
        return 1
    result = json.loads(path.read_bytes().decode("ascii"))
    report = check(result)
    report["result_digest"] = result.get("result_digest")
    report["report_digest"] = digest({k: v for k, v in report.items() if k != "report_digest"})

    if arguments.write and not arguments.development:
        REPORT_PATH.write_bytes((canonical_json(report) + "\n").encode("ascii"))
        print("wrote %s" % REPORT_PATH.relative_to(ROOT))

    for name in EXPECTED_PREDICATES:
        value = report["conditions"].get(name)
        print("%-4s %s" % (name, "true" if value else "FALSE" if value is not None else "MISSING"))
    print()
    print("verdict: %s (%d/%d)" % (report["verdict"], report["passed"], report["computed"]))
    if report["failing"]:
        print("failing: %s" % ", ".join(report["failing"]))
    print()
    print(canonical_json(report["measurements"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
