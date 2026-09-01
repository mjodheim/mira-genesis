"""Adversarial fixtures for the H63 decision rule.

Every scenario the pre-freeze review and the owner specification named as a way a weak result could
look strong. The desired outcome is not hard-coded: positive and negative fixtures are both
reachable, and several of these assert that a superficially favourable result is *rejected*.
"""

from __future__ import annotations

import pytest

from metamorphosis import m118_arms as arms
from metamorphosis import m118_endpoint as endpoint

R = endpoint.CLASS_REACHABLE
U = endpoint.CLASS_UNREACHABLE


def _measures(correct=0, calibrated=0, invented=0, false_refusal=0, unmet=0, agreement=1.0):
    return {"correct_construction": correct, "calibrated_refusal": calibrated,
            "invented_adapter": invented, "false_refusal": false_refusal,
            "unmet_construction": unmet, "attribution_agreement_rate": agreement}


# -------------------------------------------------------------------------------------------
# The primary endpoint follows the proposition
# -------------------------------------------------------------------------------------------

def test_success_is_construction_on_reachable_and_refusal_on_unreachable():
    assert endpoint.primary_success(R, {"correct_construction": True}) is True
    assert endpoint.primary_success(R, {"calibrated_refusal": True}) is False
    assert endpoint.primary_success(U, {"calibrated_refusal": True}) is True
    assert endpoint.primary_success(U, {"correct_construction": True}) is False


def test_everything_else_is_a_primary_failure():
    for score in ({"undetermined": True}, {"invented_adapter": True},
                  {"false_refusal": True}, {"unmet_construction": True}, {}):
        assert endpoint.primary_success(R, score) is False
        assert endpoint.primary_success(U, score) is False


def test_an_unknown_demand_class_fails_closed():
    with pytest.raises(endpoint.EndpointError, match="unknown demand class"):
        endpoint.primary_success("something_else", {"correct_construction": True})


# -------------------------------------------------------------------------------------------
# A single event can never carry the result
# -------------------------------------------------------------------------------------------

def test_one_discordant_pair_cannot_be_significant():
    """The old rule passed on +1. This one cannot."""
    d = [True] + [True] * 5
    f = [False] + [True] * 5
    verdict = endpoint.decide(d, f, _measures(6, 0, 0, 0, 0, 1.0), _measures(5, 0, 0, 0, 0, 1.0))
    assert verdict["contingency"]["discordant"] == 1
    assert verdict["p_value"] == 0.5
    assert verdict["statistical_criterion_holds"] is False
    # One discordant pair cannot reach significance at all, so this is underpowered rather than
    # evidence against the hypothesis. What matters here is that it is not positive.
    assert verdict["positive"] is False
    assert verdict["verdict"] == "inconclusive"


def test_significance_needs_at_least_five_discordant_pairs():
    assert endpoint.minimum_discordant_for_significance() == 5
    assert endpoint.smallest_attainable_p(4) > endpoint.ALPHA
    assert endpoint.smallest_attainable_p(5) <= endpoint.ALPHA


def test_a_nominal_positive_effect_can_still_fail_the_exact_test():
    """Three wins, one loss: a positive difference that the test rejects."""
    d = [True, True, True, False, True, True]
    f = [False, False, False, True, True, True]
    verdict = endpoint.decide(d, f, _measures(5, 0, 0, 0, 0, 1.0), _measures(3, 0, 0, 0, 0, 1.0))
    assert verdict["risk_difference"] > 0
    assert verdict["statistical_criterion_holds"] is False
    assert verdict["positive"] is False
    assert verdict["verdict"] == "inconclusive"


def test_a_significant_but_tiny_effect_fails_the_margin():
    """Significant on discordant pairs, but under the ten-point risk difference."""
    n = 200
    d = [True] * 100 + [False] * 100
    f = [True] * 100 + [False] * 100
    for i in range(100, 106):          # six clean wins, no losses
        d[i], f[i] = True, False
    verdict = endpoint.decide(d, f, _measures(106, 0, 0, 0, 0, 1.0),
                              _measures(100, 0, 0, 0, 0, 1.0))
    assert verdict["statistical_criterion_holds"] is True
    assert verdict["risk_difference"] < endpoint.MINIMUM_RISK_DIFFERENCE
    assert verdict["effect_size_criterion_holds"] is False
    assert verdict["verdict"] == "negative"


def test_a_large_effect_without_statistical_support_fails():
    d = [True, True, False, False]
    f = [False, False, False, False]
    verdict = endpoint.decide(d, f, _measures(2, 0, 0, 0, 0, 1.0), _measures(0, 0, 0, 0, 0, 1.0))
    assert verdict["risk_difference"] >= endpoint.MINIMUM_RISK_DIFFERENCE
    assert verdict["statistical_criterion_holds"] is False
    assert verdict["positive"] is False
    assert verdict["verdict"] == "inconclusive"


def test_genuine_strong_paired_improvement_passes():
    d = [True] * 6
    f = [False] * 6
    verdict = endpoint.decide(d, f, _measures(3, 3, 0, 0, 0, 1.0), _measures(0, 0, 0, 0, 0, 0.5))
    assert verdict["p_value"] <= endpoint.ALPHA
    assert verdict["risk_difference"] == 1.0
    assert verdict["primary_holds"] is True
    assert verdict["verdict"] == "positive"


# -------------------------------------------------------------------------------------------
# Guards veto; they never manufacture
# -------------------------------------------------------------------------------------------

def test_a_gain_that_loses_attribution_is_rejected():
    """The exact hole in M113's no-worse guard, which omitted attribution."""
    d, f = [True] * 6, [False] * 6
    verdict = endpoint.decide(d, f, _measures(3, 3, 0, 0, 0, agreement=0.40),
                              _measures(0, 0, 0, 0, 0, agreement=0.90))
    assert verdict["primary_holds"] is True
    assert "attribution_agreement_rate" in verdict["no_harm"]["failed"]
    assert verdict["verdict"] == "negative"


def test_construction_bought_with_worse_calibrated_refusal_is_rejected():
    d, f = [True] * 6, [False] * 6
    verdict = endpoint.decide(d, f, _measures(6, 0, 0, 0, 0, 1.0), _measures(0, 4, 0, 0, 0, 1.0))
    assert verdict["primary_holds"] is True
    assert "calibrated_refusal" in verdict["no_harm"]["failed"]
    assert verdict["verdict"] == "negative"


def test_refusal_bought_with_worse_construction_is_rejected():
    d, f = [True] * 6, [False] * 6
    verdict = endpoint.decide(d, f, _measures(0, 6, 0, 0, 0, 1.0), _measures(4, 0, 0, 0, 0, 1.0))
    assert "correct_construction" in verdict["no_harm"]["failed"]
    assert verdict["verdict"] == "negative"


@pytest.mark.parametrize("worse", ["invented_adapter", "false_refusal", "unmet_construction"])
def test_each_at_most_guard_can_veto(worse):
    d, f = [True] * 6, [False] * 6
    bad = _measures(3, 3, 0, 0, 0, 1.0)
    bad[worse] = 5
    verdict = endpoint.decide(d, f, bad, _measures(0, 0, 0, 0, 0, 1.0))
    assert worse in verdict["no_harm"]["failed"]
    assert verdict["verdict"] == "negative"


def test_a_guard_cannot_turn_a_negative_primary_into_a_positive():
    """Every guard passing handsomely, primary failing: still negative."""
    d = [True, False, False, False]
    f = [False, False, False, False]
    verdict = endpoint.decide(d, f, _measures(9, 9, 0, 0, 0, 1.0), _measures(0, 0, 9, 9, 9, 0.1))
    assert verdict["no_harm"]["all_hold"] is True
    assert verdict["primary_holds"] is False
    assert verdict["positive"] is False
    assert verdict["verdict"] != "positive"


def test_a_missing_guard_measure_fails_closed():
    d, f = [True] * 6, [False] * 6
    incomplete = _measures(3, 3, 0, 0, 0, 1.0)
    del incomplete["attribution_agreement_rate"]
    verdict = endpoint.decide(d, f, incomplete, _measures(0, 0, 0, 0, 0, 1.0))
    assert verdict["no_harm"]["all_hold"] is False
    assert verdict["verdict"] == "negative"


# -------------------------------------------------------------------------------------------
# There is exactly one way to win
# -------------------------------------------------------------------------------------------

def test_no_descriptive_measure_is_a_way_to_win():
    """This test previously ended in `or True` and asserted nothing at all.

    The real property: improving a descriptive measure that is neither the primary endpoint nor a
    guard must not change the verdict.
    """
    d, f = [True, False, False, False], [False, False, False, False]
    base = _measures(1, 0, 0, 0, 0, 1.0)
    plain = endpoint.decide(d, f, base, _measures(0, 0, 0, 0, 0, 1.0))
    for measure in endpoint.DESCRIPTIVE_MEASURES:
        if measure in endpoint.NO_HARM_GUARDS:
            continue
        flattered = dict(base, **{measure: 9999})
        assert endpoint.decide(d, f, flattered, _measures(0, 0, 0, 0, 0, 1.0))["verdict"] \
            == plain["verdict"], measure


def test_the_verdict_requires_both_criteria():
    assert endpoint.decide([True] * 6, [False] * 6,
                           _measures(3, 3, 0, 0, 0, 1.0),
                           _measures(0, 0, 0, 0, 0, 1.0))["both_criteria_required"] is True


def test_no_paired_demands_is_not_computed_rather_than_negative():
    verdict = endpoint.decide([], [], _measures(), _measures())
    assert verdict["verdict"] == "not_computed"
    assert verdict["p_value"] == 1.0


# -------------------------------------------------------------------------------------------
# Feasibility is proven before the freeze, not discovered after the reveal
# -------------------------------------------------------------------------------------------

def test_the_criterion_can_pass_and_fail_on_the_smallest_admissible_bank():
    report = endpoint.assert_feasible(3, 2)
    assert report["minimum_paired_demands"] == 6
    assert report["criterion_can_pass_on_the_minimum_bank"] is True
    assert report["criterion_can_fail"] is True


def test_a_plan_whose_minimum_bank_could_never_reach_significance_refuses_to_freeze():
    with pytest.raises(endpoint.EndpointError, match="guaranteed negative"):
        endpoint.assert_feasible(2, 2)          # 4 paired demands, 5 discordant needed


# -------------------------------------------------------------------------------------------
# The exact test itself
# -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("b,c,expected", [
    (0, 0, 1.0), (5, 0, 0.03125), (6, 0, 0.015625), (0, 5, 1.0), (3, 3, 0.65625),
])
def test_exact_one_sided_p_values(b, c, expected):
    assert endpoint.exact_mcnemar_one_sided(b, c) == pytest.approx(expected)


def test_the_test_is_one_sided_in_the_descendants_favour():
    assert endpoint.exact_mcnemar_one_sided(6, 0) < endpoint.exact_mcnemar_one_sided(0, 6)


def test_negative_counts_fail_closed():
    with pytest.raises(endpoint.EndpointError):
        endpoint.exact_mcnemar_one_sided(-1, 2)


# -------------------------------------------------------------------------------------------
# fresh_uniform is information-free, and beating T0 is not enough
# -------------------------------------------------------------------------------------------

def test_the_fresh_comparator_is_information_free_and_non_constant():
    report = arms.is_information_free(arms.fresh_uniform_rules())
    assert report["carries_no_acquired_rule"] is True
    assert report["every_rule_is_seed_derived"] is True
    assert report["no_row_is_claimed_twice"] is True
    assert report["effective_assignment_is_total"] is True
    assert report["is_non_constant"] is True
    assert report["reaches_every_component"] is True
    assert len(report["components_named"]) == 3


def test_the_fresh_comparator_is_deterministic_and_replayable():
    assert arms.fresh_uniform_rules() == arms.fresh_uniform_rules()
    assert arms.fresh_uniform_assignment("other-seed") != arms.fresh_uniform_assignment()


def test_the_fresh_comparator_is_balanced():
    counts = sorted(arms.is_information_free(arms.fresh_uniform_rules())
                    ["rows_per_component"].values())
    assert max(counts) - min(counts) <= 1


def test_the_primary_comparison_is_not_t0():
    assert arms.PRIMARY_FRESH_ARM == "fresh_uniform"
    assert arms.LEGACY_FRESH_ARM == "T0"
    assert arms.DESCENDANT_ARM == "M3"


def test_beating_t0_but_losing_to_fresh_uniform_is_negative():
    """T0 is a constant; the primary comparison must be against the real comparator."""
    descendant = [True, True, True, False, False, False]
    fresh_uniform = [True, True, True, True, True, True]
    verdict = endpoint.decide(descendant, fresh_uniform,
                              _measures(3, 0, 0, 0, 0, 1.0), _measures(6, 0, 0, 0, 0, 1.0))
    assert verdict["positive"] is False
    assert verdict["risk_difference"] < 0


def test_the_endpoint_covers_exactly_the_evaluators_demand_classes():
    """This is the test that would have caught the class-name mismatch.

    The endpoint once spelled the unreachable class "structurally_unreachable" while the evaluator
    calls it "unreachable". Every unreachable demand would have raised mid-run, and the fixtures
    above did not notice because they used the endpoint's own constant.
    """
    from metamorphosis import m113_evaluator as ev
    assert set(endpoint.PRIMARY_SUCCESS_KEY) == set(ev.DEMAND_CLASSES)
    assert endpoint.CLASS_REACHABLE is ev.CLASS_REACHABLE
    assert endpoint.CLASS_UNREACHABLE is ev.CLASS_UNREACHABLE
    for demand_class in ev.DEMAND_CLASSES:
        endpoint.primary_success(demand_class, {})


# -------------------------------------------------------------------------------------------
# The preregistration states the rule it will be judged by
# -------------------------------------------------------------------------------------------

def test_the_preregistration_states_the_decision_rule():
    import re
    from pathlib import Path
    text = re.sub(r"\s+", " ", (Path(__file__).resolve().parents[1] / "experiments" / "M118"
                                / "PREREGISTRATION.md").read_text(encoding="utf-8"))
    for required in (
        "M113's P22 is not carried into H63",
        "There is no disjunction and no second way to win",
        "One-sided exact McNemar",
        "Risk difference ≥ 10 percentage points",
        "refuses to freeze",
        "attribution_agreement_rate",
        "primary comparison is `M3` vs `fresh_uniform`",
        "constant function",
        "is withdrawn",
        "H63 is negative",
        "no qualifying scientific test",
        "conditional on this serving route",
    ):
        assert required in text, required


def test_the_preregistration_matches_the_implemented_thresholds():
    import re
    from pathlib import Path
    text = re.sub(r"\s+", " ", (Path(__file__).resolve().parents[1] / "experiments" / "M118"
                                / "PREREGISTRATION.md").read_text(encoding="utf-8"))
    assert "α = 0.05" in text and endpoint.ALPHA == 0.05
    assert "10 percentage points" in text and endpoint.MINIMUM_RISK_DIFFERENCE == 0.10
    assert "at least five" in text
    assert endpoint.minimum_discordant_for_significance() == 5
    assert "0.0156" in text
    assert round(endpoint.smallest_attainable_p(6), 4) == 0.0156


# -------------------------------------------------------------------------------------------
# Dominance: a positive cannot stand while the descendant loses to the arms it must improve on
# -------------------------------------------------------------------------------------------

def test_a_positive_cannot_stand_while_the_descendant_loses_to_the_constant_arm():
    """The hole opened by replacing T0 with a stronger comparator, now closed."""
    verdict = endpoint.decide(
        [True] * 8 + [False] * 4, [False] * 12,
        _measures(8, 0, 0, 0, 0, 1.0), _measures(0, 0, 0, 0, 0, 0.0),
        dominance={"T0": [True] * 12, "M2": [True] * 12})
    assert verdict["primary_holds"] is True
    assert verdict["dominance"]["failed"] == ["M2", "T0"]
    assert verdict["verdict"] == "negative"


def test_dominance_holds_when_the_descendant_leads_everything():
    verdict = endpoint.decide(
        [True] * 6, [False] * 6, _measures(3, 3, 0, 0, 0, 1.0), _measures(0, 0, 0, 0, 0, 1.0),
        dominance={"T0": [False] * 6, "M2": [True, False, False, False, False, False]})
    assert verdict["dominance"]["all_hold"] is True
    assert verdict["verdict"] == "positive"


def test_dominance_cannot_create_a_positive():
    verdict = endpoint.decide(
        [True, False, False, False], [False, False, False, False],
        _measures(1, 0, 0, 0, 0, 1.0), _measures(0, 0, 0, 0, 0, 1.0),
        dominance={"T0": [False] * 4, "M2": [False] * 4})
    assert verdict["dominance"]["all_hold"] is True
    assert verdict["verdict"] != "positive"


# -------------------------------------------------------------------------------------------
# An underpowered bank is not a refutation
# -------------------------------------------------------------------------------------------

def test_a_bank_too_small_for_significance_is_inconclusive_not_negative():
    verdict = endpoint.decide([True, True, True, False], [False] * 4,
                              _measures(3, 0, 0, 0, 0, 1.0), _measures(0, 0, 0, 0, 0, 1.0))
    assert verdict["smallest_attainable_p_value"] > endpoint.ALPHA
    assert verdict["underpowered"] is True
    assert verdict["verdict"] == "inconclusive"


def test_a_powered_bank_that_fails_is_still_negative():
    verdict = endpoint.decide([True] * 3 + [False] * 3, [False] * 3 + [True] * 3,
                              _measures(3, 0, 0, 0, 0, 1.0), _measures(3, 0, 0, 0, 0, 1.0))
    assert verdict["underpowered"] is False
    assert verdict["verdict"] == "negative"


def test_an_unformable_attribution_rate_does_not_veto_a_perfect_descendant():
    base = {"correct_construction": 6, "calibrated_refusal": 6, "invented_adapter": 0,
            "false_refusal": 0, "unmet_construction": 0}
    perfect = dict(base, attribution_agreement_rate=None, attribution_examined=0)
    fresh = dict(base, correct_construction=0, calibrated_refusal=0,
                 attribution_agreement_rate=0.5, attribution_examined=4)
    verdict = endpoint.decide([True] * 6, [False] * 6, perfect, fresh,
                              dominance={"T0": [False] * 6, "M2": [False] * 6})
    assert "attribution_agreement_rate" in verdict["no_harm"]["not_evaluated"]
    assert verdict["no_harm"]["failed"] == []
    assert verdict["verdict"] == "positive"


def test_a_genuinely_missing_count_measure_still_fails_closed():
    incomplete = _measures(3, 3, 0, 0, 0, 1.0)
    del incomplete["correct_construction"]
    verdict = endpoint.decide([True] * 6, [False] * 6, incomplete, _measures(0, 0, 0, 0, 0, 1.0))
    assert "correct_construction" in verdict["no_harm"]["failed"]
    assert verdict["verdict"] != "positive"


# -------------------------------------------------------------------------------------------
# The comparator space is symmetric and balanced
# -------------------------------------------------------------------------------------------

def test_the_assignment_space_is_balanced_and_no_component_is_short_changed():
    import collections
    space = arms.achievable_assignments()
    shapes = {tuple(sorted(collections.Counter(a).values())) for a in space}
    assert shapes == {(2, 3, 3)}
    short = collections.Counter(
        min(collections.Counter(a), key=lambda c: collections.Counter(a)[c]) for a in space)
    assert len(set(short.values())) == 1, "a component is short-changed more often than others"


def test_the_seed_permutes_which_component_is_short_changed():
    """Dealing over a fixed component order short-changed candidate_space in 400 of 400 seeds."""
    import collections
    short = collections.Counter()
    for index in range(120):
        assignment = arms.fresh_uniform_assignment("sensitivity-%d" % index)
        counts = collections.Counter(assignment)
        short[min(counts, key=lambda c: counts[c])] += 1
    assert len(short) == 3, "the seed never varies which component is short-changed"
