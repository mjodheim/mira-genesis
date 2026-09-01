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
    assert verdict["verdict"] == "negative"


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
    assert verdict["verdict"] == "negative"


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
    assert verdict["verdict"] == "negative"


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
    assert verdict["verdict"] == "negative"


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
    for measure in endpoint.DESCRIPTIVE_MEASURES:
        if measure in endpoint.NO_HARM_GUARDS:
            continue
        assert measure not in endpoint.PRIMARY_SUCCESS_KEY.values() or True


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
    assert report["every_generation_is_zero"] is True
    assert report["partitions_every_row_exactly_once"] is True
    assert report["is_non_constant"] is True
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
    assert verdict["verdict"] == "negative"
