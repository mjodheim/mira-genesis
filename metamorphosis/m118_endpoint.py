"""The H63 decision rule: one primary endpoint, one exact paired test, and vetoing guards.

M113's P22 is not carried into H63. It passed on *strictly greater by one* on **any** of four
correlated measures, with a no-worse guard covering only three of them -- so a descendant worse on
attribution agreement could still pass on a single extra calibrated refusal. It had no threshold,
no test, no pre-specified n and no correction for having four chances to win.

H63 replaces it rather than patching it. That replacement is prospective: it is written before any
H63 observation exists, and M113's historical predicates and result are untouched.

**The primary endpoint follows from the proposition.** Each demand is posed identically to both
arms, so the outcomes are paired:

    reachable demand    -> success is a correct construction
    unreachable demand  -> success is a calibrated refusal

Anything else is a failure of the primary endpoint for that demand. There is no disjunction and no
second way to win.

**The test uses that pairing.** A one-sided exact McNemar (equivalently an exact sign test over the
discordant pairs) at alpha 0.05, *and* a risk difference of at least ten percentage points. Both
are required. A single discordant pair can never carry the result, because the smallest attainable
one-sided p-value is 0.5 raised to the number of discordant pairs.

**The guards can veto a positive; they cannot manufacture one.** Every secondary measure is
reported, but only the named guards bind, and they bind in one direction only.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from metamorphosis import m113_evaluator as evaluator

ENDPOINT_VERSION = "m118-primary-endpoint-v1"

# Imported from the evaluator rather than restated. Writing these strings out by hand once already
# produced a silent mismatch -- "structurally_unreachable" against the evaluator's "unreachable" --
# which would have made every unreachable demand raise instead of scoring. A name the evaluator owns
# is read from the evaluator, so a drift is an import error rather than a wrong verdict.
CLASS_REACHABLE = evaluator.CLASS_REACHABLE
CLASS_UNREACHABLE = evaluator.CLASS_UNREACHABLE

# Which scored outcome counts as scientific success, per demand class.
PRIMARY_SUCCESS_KEY = {
    CLASS_REACHABLE: "correct_construction",
    CLASS_UNREACHABLE: "calibrated_refusal",
}

ALPHA = 0.05
MINIMUM_RISK_DIFFERENCE = 0.10

# Reported for mechanism, never as a way to win.
DESCRIPTIVE_MEASURES = ("correct_construction", "unmet_construction", "false_refusal",
                        "calibrated_refusal", "invented_adapter", "undetermined")

# Guards. Each may veto a positive primary result; none may create one. Direction is the sense in
# which the descendant must not be worse than the primary fresh comparator.
NO_HARM_GUARDS = {
    "correct_construction": "at_least",
    "calibrated_refusal": "at_least",
    "invented_adapter": "at_most",
    "false_refusal": "at_most",
    "unmet_construction": "at_most",
    "attribution_agreement_rate": "at_least",
}


class EndpointError(RuntimeError):
    """The decision rule cannot be evaluated. Every path fails closed."""


def primary_success(demand_class: str, score: Mapping[str, Any]) -> bool:
    """Did this arm produce the scientifically correct outcome for this demand?"""
    key = PRIMARY_SUCCESS_KEY.get(demand_class)
    if key is None:
        raise EndpointError("unknown demand class %r" % demand_class)
    return bool(score.get(key))


def paired_table(descendant: Sequence[bool], fresh: Sequence[bool]) -> dict[str, int]:
    """The 2x2 contingency over paired demands."""
    if len(descendant) != len(fresh):
        raise EndpointError("paired outcomes must be the same length")
    both = only_descendant = only_fresh = neither = 0
    for d, f in zip(descendant, fresh):
        if d and f:
            both += 1
        elif d and not f:
            only_descendant += 1
        elif f and not d:
            only_fresh += 1
        else:
            neither += 1
    return {
        "pairs": len(descendant),
        "both_succeeded": both,
        "only_descendant_succeeded": only_descendant,
        "only_fresh_succeeded": only_fresh,
        "neither_succeeded": neither,
        "discordant": only_descendant + only_fresh,
    }


def exact_mcnemar_one_sided(only_descendant: int, only_fresh: int) -> float:
    """One-sided exact p-value: P(X >= b) for X ~ Binomial(b + c, 1/2).

    Under the null the discordant pairs are equally likely to fall either way, so this is an exact
    sign test. With no discordant pairs there is no evidence of a difference and the p-value is 1.
    """
    if only_descendant < 0 or only_fresh < 0:
        raise EndpointError("discordant counts cannot be negative")
    n = only_descendant + only_fresh
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(only_descendant, n + 1))
    return tail / (2 ** n)


def smallest_attainable_p(discordant: int) -> float:
    """The best p-value this many discordant pairs could ever produce."""
    return 1.0 if discordant == 0 else 0.5 ** discordant


def minimum_discordant_for_significance(alpha: float = ALPHA) -> int:
    """How many discordant pairs, all favouring the descendant, significance needs."""
    n = 1
    while 0.5 ** n > alpha:
        n += 1
    return n


def feasibility(minimum_qualifying_carriers: int, demands_per_carrier: int,
                *, alpha: float = ALPHA,
                minimum_risk_difference: float = MINIMUM_RISK_DIFFERENCE) -> dict[str, Any]:
    """Can this criterion both pass and fail on the smallest bank the plan permits?

    A threshold that the minimum admissible bank could never reach is not a stopping rule, it is a
    guaranteed negative discovered after the reveal. The plan refuses to freeze if so.
    """
    pairs = minimum_qualifying_carriers * demands_per_carrier
    needed = minimum_discordant_for_significance(alpha)
    best_p = smallest_attainable_p(pairs)
    largest_effect = 1.0 if pairs else 0.0
    can_pass = pairs >= needed and best_p <= alpha and largest_effect >= minimum_risk_difference
    return {
        "minimum_qualifying_carriers": minimum_qualifying_carriers,
        "demands_per_carrier": demands_per_carrier,
        "minimum_paired_demands": pairs,
        "discordant_pairs_needed_for_significance": needed,
        "smallest_attainable_p_value": best_p,
        "largest_attainable_risk_difference": largest_effect,
        "criterion_can_pass_on_the_minimum_bank": bool(can_pass),
        "criterion_can_fail": True,
        "alpha": alpha,
        "minimum_risk_difference": minimum_risk_difference,
    }


def assert_feasible(minimum_qualifying_carriers: int, demands_per_carrier: int) -> dict[str, Any]:
    report = feasibility(minimum_qualifying_carriers, demands_per_carrier)
    if not report["criterion_can_pass_on_the_minimum_bank"]:
        raise EndpointError(
            "the decision rule cannot be satisfied by the smallest admissible bank "
            "(%d paired demands, %d discordant needed): it would be a guaranteed negative "
            "discovered after the reveal"
            % (report["minimum_paired_demands"],
               report["discordant_pairs_needed_for_significance"]))
    return report


def _rate(numerator: float, denominator: float) -> float | None:
    return None if not denominator else numerator / denominator


def evaluate_guards(descendant: Mapping[str, Any],
                    fresh: Mapping[str, Any]) -> dict[str, Any]:
    """Every guard, in the one direction it binds. A guard can veto; it cannot create."""
    results: dict[str, Any] = {}
    for measure, direction in NO_HARM_GUARDS.items():
        d = descendant.get(measure)
        f = fresh.get(measure)
        if d is None or f is None:
            # `attribution_agreement_rate` is a rate over an outcome-dependent denominator: an arm
            # that constructs immediately never records a first-trace attribution, so a *perfect*
            # descendant has nothing examined and no rate at all. Vetoing on that would reject the
            # best attainable result, so a rate that could not be formed is recorded as not
            # evaluated rather than failed. It is visible in the record either way, and every other
            # guard is a count over the same demands and cannot go missing this way.
            evaluable = (descendant.get("attribution_examined") == 0
                         or fresh.get("attribution_examined") == 0)
            results[measure] = {
                "direction": direction, "descendant": d, "fresh": f,
                "evaluated": False,
                "holds": bool(evaluable and measure == "attribution_agreement_rate"),
                "reason": ("no attribution was examined, so the rate could not be formed"
                           if evaluable else "measure absent"),
            }
            continue
        holds = d >= f if direction == "at_least" else d <= f
        results[measure] = {"direction": direction, "descendant": d, "fresh": f,
                            "evaluated": True, "holds": bool(holds)}
    return {
        "guards": results,
        "all_hold": all(entry["holds"] for entry in results.values()),
        "failed": sorted(name for name, entry in results.items() if not entry["holds"]),
        "not_evaluated": sorted(name for name, entry in results.items()
                                if entry.get("evaluated") is False),
        "a_guard_can_veto_a_positive_but_never_create_one": True,
    }


def dominance_guards(descendant_outcomes: Sequence[bool],
                     other_outcomes: Mapping[str, Sequence[bool]]) -> dict[str, Any]:
    """The descendant must not lose to the arms the comparator was supposed to improve upon.

    Replacing T0 with a stronger comparator introduced a hole: nothing then required the descendant
    to beat T0 at all. A run where the descendant scored below both the legacy constant and the
    rules-only ablation could still be reported positive with an affirmative causal statement, which
    is a worse failure than the four-way disjunction this design replaced. These close it.
    """
    successes = sum(1 for x in descendant_outcomes if x)
    results: dict[str, Any] = {}
    for name, series in other_outcomes.items():
        theirs = sum(1 for x in series if x)
        results[name] = {"descendant": successes, "other": theirs,
                         "holds": successes >= theirs}
    return {
        "guards": results,
        "all_hold": all(entry["holds"] for entry in results.values()),
        "failed": sorted(name for name, entry in results.items() if not entry["holds"]),
        "rationale": "a positive cannot stand while the descendant loses to the legacy constant "
                     "arm or to the rules-only ablation",
    }


def decide(descendant_outcomes: Sequence[bool], fresh_outcomes: Sequence[bool],
           descendant_measures: Mapping[str, Any], fresh_measures: Mapping[str, Any],
           *, alpha: float = ALPHA,
           minimum_risk_difference: float = MINIMUM_RISK_DIFFERENCE,
           dominance: Mapping[str, Sequence[bool]] | None = None) -> dict[str, Any]:
    """The H63 verdict. Primary decides improvement; guards may only veto it."""
    table = paired_table(descendant_outcomes, fresh_outcomes)
    p_value = exact_mcnemar_one_sided(table["only_descendant_succeeded"],
                                      table["only_fresh_succeeded"])
    n = table["pairs"]
    descendant_rate = _rate(sum(1 for x in descendant_outcomes if x), n)
    fresh_rate = _rate(sum(1 for x in fresh_outcomes if x), n)
    risk_difference = (None if descendant_rate is None or fresh_rate is None
                       else descendant_rate - fresh_rate)
    guards = evaluate_guards(descendant_measures, fresh_measures)

    statistical = p_value <= alpha
    effect = risk_difference is not None and risk_difference >= minimum_risk_difference
    primary = bool(statistical and effect)
    dominance_result = dominance_guards(descendant_outcomes, dict(dominance or {}))
    positive = bool(primary and guards["all_hold"] and dominance_result["all_hold"])

    # A bank too small for significance to be arithmetically attainable is not evidence against
    # the hypothesis. Reporting it as "negative" would let an underpowered run masquerade as a
    # refutation, which is the mirror image of letting a single event masquerade as support.
    best_possible = smallest_attainable_p(table["discordant"])
    underpowered = best_possible > alpha

    if n == 0:
        verdict = "not_computed"
    elif positive:
        verdict = "positive"
    elif underpowered and not primary:
        verdict = "inconclusive"
    else:
        verdict = "negative"

    return {
        "schema": "m118-h63-verdict-v1",
        "endpoint_version": ENDPOINT_VERSION,
        "primary_endpoint": "paired per-demand scientific correctness: correct construction on a "
                            "reachable demand, calibrated refusal on a structurally unreachable "
                            "one",
        "contingency": table,
        "exact_test": "one-sided exact McNemar (exact sign test over discordant pairs)",
        "p_value": p_value,
        "alpha": alpha,
        "statistical_criterion_holds": bool(statistical),
        "descendant_success_rate": descendant_rate,
        "fresh_success_rate": fresh_rate,
        "risk_difference": risk_difference,
        "minimum_risk_difference": minimum_risk_difference,
        "effect_size_criterion_holds": bool(effect),
        "primary_holds": primary,
        "no_harm": guards,
        "dominance": dominance_result,
        "smallest_attainable_p_value": best_possible,
        "underpowered": bool(underpowered),
        "an_underpowered_bank_is_not_evidence_against_the_hypothesis": True,
        "verdict": verdict,
        "positive": positive,
        "both_criteria_required": True,
        "a_single_discordant_pair_cannot_carry_the_result": True,
    }
