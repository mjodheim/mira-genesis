"""The H64 decision rule: one endpoint, one test, three guards, four verdicts.

Deliberately small. M118's rule grew until it could issue a positive causal claim while the
descendant was worse than the controls it was supposed to beat; this one is sized so that the whole
of it fits in a paragraph.

**Primary endpoint.** Each demand is posed identically to every arm, so outcomes are paired:

    reachable demand    -> success is a correct construction
    unreachable demand  -> success is a calibrated refusal

Anything else -- including `undetermined` -- is a primary failure for that demand. There is no
disjunction and no second way to win.

**Primary comparison.** FULL versus FRESH, one-sided exact McNemar over discordant pairs at
alpha 0.05, **and** an absolute success-rate improvement of at least ten percentage points. Both
required.

**Verdicts.** Four states, and the two failure modes are not the same statement:

    INSTRUMENT_ABORTED  the run cannot validly test H64 at all
    INCONCLUSIVE        a valid observation, but significance was not arithmetically attainable
    NEGATIVE            a valid, adequately powered test in which the criterion failed
    POSITIVE            both criteria met and every mandatory guard held

An underpowered bank is never a refutation, and an instrument failure is never a scientific result.

**Guards veto; they never create.** Three, each in one direction, and none of them can turn a failed
primary into a pass.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from metamorphosis import m113_evaluator as evaluator

ENDPOINT_VERSION = "m119-endpoint-v1"

CLASS_REACHABLE = evaluator.CLASS_REACHABLE
CLASS_UNREACHABLE = evaluator.CLASS_UNREACHABLE

PRIMARY_SUCCESS_KEY = {
    CLASS_REACHABLE: "correct_construction",
    CLASS_UNREACHABLE: "calibrated_refusal",
}

ALPHA = 0.05
MINIMUM_RISK_DIFFERENCE = 0.10

# Three, in one direction each. `attribution_agreement_rate` binds only where attribution was
# actually examined: it has an outcome-dependent denominator, so an arm that constructs immediately
# examines nothing, and vetoing on a rate that could not be formed would reject the best result.
NO_HARM_GUARDS = {
    "invented_adapter": "at_most",
    "false_refusal": "at_most",
    "attribution_agreement_rate": "at_least",
}

INSTRUMENT_ABORTED = "instrument_aborted"
INCONCLUSIVE = "inconclusive"
NEGATIVE = "negative"
POSITIVE = "positive"
VERDICTS = (INSTRUMENT_ABORTED, INCONCLUSIVE, NEGATIVE, POSITIVE)


class EndpointError(RuntimeError):
    """The rule cannot be evaluated. Every path fails closed."""


def primary_success(demand_class: str, score: Mapping[str, Any]) -> bool:
    key = PRIMARY_SUCCESS_KEY.get(demand_class)
    if key is None:
        raise EndpointError("unknown demand class %r" % demand_class)
    return bool(score.get(key))


def paired_table(descendant: Sequence[bool], fresh: Sequence[bool]) -> dict[str, int]:
    if len(descendant) != len(fresh):
        raise EndpointError("paired outcomes must be the same length")
    both = only_d = only_f = neither = 0
    for d, f in zip(descendant, fresh):
        both += bool(d and f)
        only_d += bool(d and not f)
        only_f += bool(f and not d)
        neither += bool(not d and not f)
    return {"pairs": len(descendant), "both_succeeded": both,
            "only_descendant_succeeded": only_d, "only_fresh_succeeded": only_f,
            "neither_succeeded": neither, "discordant": only_d + only_f}


def exact_mcnemar_one_sided(only_descendant: int, only_fresh: int) -> float:
    """P(X >= b) for X ~ Binomial(b + c, 1/2). An exact sign test over the discordant pairs."""
    if only_descendant < 0 or only_fresh < 0:
        raise EndpointError("discordant counts cannot be negative")
    n = only_descendant + only_fresh
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(only_descendant, n + 1)) / (2 ** n)


def smallest_attainable_p(discordant: int) -> float:
    return 1.0 if discordant == 0 else 0.5 ** discordant


def minimum_discordant_for_significance(alpha: float = ALPHA) -> int:
    n = 1
    while 0.5 ** n > alpha:
        n += 1
    return n


def required_paired_demands(alpha: float = ALPHA) -> int:
    """The fewest paired demands under which the criterion could possibly be met."""
    return minimum_discordant_for_significance(alpha)


def feasibility(minimum_qualifying_carriers: int, demands_per_carrier: int,
                *, alpha: float = ALPHA,
                minimum_risk_difference: float = MINIMUM_RISK_DIFFERENCE) -> dict[str, Any]:
    """Can the frozen criterion both pass and fail on the smallest admissible bank?"""
    pairs = minimum_qualifying_carriers * demands_per_carrier
    needed = minimum_discordant_for_significance(alpha)
    best_p = smallest_attainable_p(pairs)
    return {
        "minimum_qualifying_carriers": minimum_qualifying_carriers,
        "demands_per_carrier": demands_per_carrier,
        "minimum_paired_demands": pairs,
        "discordant_pairs_needed_for_significance": needed,
        "smallest_attainable_p_value": best_p,
        "largest_attainable_risk_difference": 1.0 if pairs else 0.0,
        "criterion_can_pass_on_the_minimum_bank": bool(
            pairs >= needed and best_p <= alpha and minimum_risk_difference <= 1.0),
        "criterion_can_fail": True,
        "alpha": alpha,
        "minimum_risk_difference": minimum_risk_difference,
    }


def assert_feasible(minimum_qualifying_carriers: int, demands_per_carrier: int) -> dict[str, Any]:
    """Refuse a plan whose smallest admissible bank could never satisfy its own criterion."""
    report = feasibility(minimum_qualifying_carriers, demands_per_carrier)
    if not report["criterion_can_pass_on_the_minimum_bank"]:
        raise EndpointError(
            "the frozen criterion cannot be satisfied by the smallest admissible bank: %d paired "
            "demands against %d discordant needed. Redesign the requested bank size before "
            "generation rather than discovering this after the reveal."
            % (report["minimum_paired_demands"],
               report["discordant_pairs_needed_for_significance"]))
    return report


def evaluate_guards(descendant: Mapping[str, Any], fresh: Mapping[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for measure, direction in NO_HARM_GUARDS.items():
        d, f = descendant.get(measure), fresh.get(measure)
        if d is None or f is None:
            unformable = (measure == "attribution_agreement_rate"
                          and (descendant.get("attribution_examined") == 0
                               or fresh.get("attribution_examined") == 0))
            results[measure] = {
                "direction": direction, "descendant": d, "fresh": f, "evaluated": False,
                "holds": bool(unformable),
                "reason": ("attribution was not examined, so the rate could not be formed"
                           if unformable else "measure absent"),
            }
            continue
        results[measure] = {"direction": direction, "descendant": d, "fresh": f,
                            "evaluated": True,
                            "holds": bool(d >= f if direction == "at_least" else d <= f)}
    return {
        "guards": results,
        "all_hold": all(entry["holds"] for entry in results.values()),
        "failed": sorted(name for name, entry in results.items() if not entry["holds"]),
        "not_evaluated": sorted(name for name, entry in results.items()
                                if entry.get("evaluated") is False),
        "a_guard_can_veto_a_positive_but_never_create_one": True,
    }


def decide(descendant_outcomes: Sequence[bool], fresh_outcomes: Sequence[bool],
           descendant_measures: Mapping[str, Any], fresh_measures: Mapping[str, Any],
           *, alpha: float = ALPHA,
           minimum_risk_difference: float = MINIMUM_RISK_DIFFERENCE,
           instrument_valid: bool = True,
           instrument_failures: Sequence[str] = ()) -> dict[str, Any]:
    """The H64 verdict."""
    table = paired_table(descendant_outcomes, fresh_outcomes)
    n = table["pairs"]
    p_value = exact_mcnemar_one_sided(table["only_descendant_succeeded"],
                                      table["only_fresh_succeeded"])
    d_rate = (sum(1 for x in descendant_outcomes if x) / n) if n else None
    f_rate = (sum(1 for x in fresh_outcomes if x) / n) if n else None
    risk_difference = None if d_rate is None or f_rate is None else d_rate - f_rate
    guards = evaluate_guards(descendant_measures, fresh_measures)

    statistical = p_value <= alpha
    effect = risk_difference is not None and risk_difference >= minimum_risk_difference
    primary = bool(statistical and effect)
    best_possible = smallest_attainable_p(table["discordant"])
    underpowered = best_possible > alpha
    positive = bool(primary and guards["all_hold"])

    if not instrument_valid or n == 0:
        verdict = INSTRUMENT_ABORTED
    elif positive:
        verdict = POSITIVE
    elif underpowered and not primary:
        verdict = INCONCLUSIVE
    else:
        verdict = NEGATIVE

    return {
        "schema": "m119-h64-verdict-v1",
        "endpoint_version": ENDPOINT_VERSION,
        "primary_endpoint": "paired per-demand scientific correctness: correct construction on a "
                            "reachable demand, calibrated refusal on an unreachable one",
        "contingency": table,
        "exact_test": "one-sided exact McNemar over discordant pairs",
        "p_value": p_value, "alpha": alpha,
        "statistical_criterion_holds": bool(statistical),
        "descendant_success_rate": d_rate, "fresh_success_rate": f_rate,
        "risk_difference": risk_difference,
        "minimum_risk_difference": minimum_risk_difference,
        "effect_size_criterion_holds": bool(effect),
        "primary_holds": primary,
        "smallest_attainable_p_value": best_possible,
        "underpowered": bool(underpowered),
        "no_harm": guards,
        "instrument_valid": bool(instrument_valid),
        "instrument_failures": list(instrument_failures),
        "verdict": verdict,
        "positive": positive,
        "an_underpowered_bank_is_not_a_refutation": True,
        "an_instrument_failure_is_not_a_scientific_result": True,
    }
