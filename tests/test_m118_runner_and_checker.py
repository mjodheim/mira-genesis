"""The H63 runner measures and the checker decides, on synthetic DEVELOPMENT fixtures.

None of this touches H63 data, which does not exist. These fixtures exercise the corrected arm set
and decision rule end to end so that the first time they run on a real bank is not the first time
they run at all.
"""

from __future__ import annotations

import json

import pytest

from metamorphosis import carrier_host as host
from metamorphosis import m109_runtime as lineage
from metamorphosis import m113_carrier_devkit as devkit
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m118_arms as arms
from metamorphosis import m118_endpoint as endpoint
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from scripts import check_m118_result as checker
from scripts import run_m118_qualification as runner

NONCE = "00" * 32


def _carriers(count=4):
    found = []
    for index in range(120):
        carrier = host.validate_carrier(devkit.development_carrier("m118-fixture-%d" % index))
        if evaluator.qualification_report(carrier)["qualifies"]:
            found.append(carrier)
        if len(found) >= count:
            break
    assert len(found) == count, "the devkit did not yield enough qualifying carriers"
    return found


# A synthetic stand-in for the committed analysis plan. The runner refuses to take scientific
# parameters from its arguments, so the fixtures must supply a plan exactly as the real run will.
DEV_PLAN = {
    "plan_commitment_sha256": "d" * 64,
    "session_budget": 4000,
    "minimum_qualifying_carriers": 3,
    "minimum_distinct_qualifying_structures": 1,
}


@pytest.fixture(scope="module")
def measurements():
    return runner.measure(_carriers(), NONCE, session_budget=DEV_PLAN["session_budget"],
                          plan=DEV_PLAN)


# -------------------------------------------------------------------------------------------
# The arms are the corrected factorial set, restored from frozen bytes
# -------------------------------------------------------------------------------------------

def test_the_factorial_cells_are_present_and_correct():
    cascades = runner.restore_h63_arms()["cascades"]
    assert cascades["T0"]["rules"] == [] and not cascades["T0"]["policy"]
    assert cascades["probe_only"]["rules"] == [] and cascades["probe_only"]["policy"]
    assert cascades["M2"]["rules"] and not cascades["M2"]["policy"]
    assert cascades["M3"]["rules"] and cascades["M3"]["policy"]


def test_the_budget_control_can_actually_probe():
    """Legacy budget_plus cannot probe at any budget; the new one can."""
    cascades = runner.restore_h63_arms()["cascades"]
    assert not cascades["budget_plus"]["policy"]
    assert cascades["probe_only_budget_plus"]["policy"]
    assert arms.BUDGET_MULTIPLIER["probe_only_budget_plus"] == 4


def test_every_comparator_rule_is_well_formed_for_the_inherited_runtime():
    for rule in arms.fresh_uniform_rules():
        lineage.decode_rule(rule)


def test_the_comparator_is_not_the_constant_arm():
    report = arms.is_information_free(arms.fresh_uniform_rules())
    assert report["reaches_every_component"] is True
    assert report["unlike_t0_which_reaches_the_fallthrough_on_every_row"] is True


# -------------------------------------------------------------------------------------------
# The runner records and does not decide
# -------------------------------------------------------------------------------------------

def test_the_runner_writes_no_verdict(measurements):
    serialised = json.dumps(measurements)
    assert measurements["the_runner_records_measurements_and_decides_nothing"] is True
    for forbidden in ('"verdict": "positive"', '"verdict": "negative"',
                      '"hypothesis_status"', '"p_value"'):
        assert forbidden not in serialised, forbidden


def test_every_arm_answered_the_same_demands(measurements):
    lengths = {name: len(series)
               for name, series in measurements["paired_primary_outcomes"].items()}
    assert len(set(lengths.values())) == 1
    assert lengths["M3"] == len(measurements["demand_order"])


def test_the_demand_order_alternates_the_two_classes(measurements):
    classes = [row["demand_class"] for row in measurements["demand_order"]]
    assert set(classes) == set(evaluator.DEMAND_CLASSES)


def test_the_measurements_digest_reproduces(measurements):
    expected = sha256_hex(canonical_bytes(
        {k: v for k, v in measurements.items() if k != "measurements_sha256"}))
    assert measurements["measurements_sha256"] == expected


def test_attribution_is_recorded_for_every_arm(measurements):
    for name in arms.ARM_NAMES:
        assert "attribution_agreement_rate" in measurements["measures"][name]


# -------------------------------------------------------------------------------------------
# The checker recomputes
# -------------------------------------------------------------------------------------------

def test_the_checker_produces_a_coherent_verdict(measurements):
    report = checker.check(measurements)
    assert report["verdict"] in ("positive", "negative", "inconclusive", "not_computed")
    assert report["primary_comparison"] == "M3 vs fresh_uniform"
    assert report["verdict_recomputed_independently"] is True


def test_the_checker_refuses_a_tampered_digest(measurements):
    tampered = dict(measurements)
    tampered["qualifying_carriers"] = 999
    with pytest.raises(checker.CheckError, match="digest does not reproduce"):
        checker.check(tampered)


def test_the_checker_refuses_t0_as_the_primary_comparator(measurements):
    swapped = dict(measurements)
    swapped["primary_fresh_arm"] = "T0"
    swapped["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in swapped.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="beating T0 is not the test"):
        checker.check(swapped)


def test_the_checker_refuses_unequal_demand_counts(measurements):
    broken = json.loads(json.dumps(measurements))
    broken["paired_primary_outcomes"]["M3"] = broken["paired_primary_outcomes"]["M3"][:-1]
    broken["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in broken.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="same number of demands"):
        checker.check(broken)


def test_the_checker_reports_t0_without_letting_it_decide(measurements):
    report = checker.check(measurements)
    assert "not evidence for H63" in report["legacy_t0_comparison_not_decisive"]["note"]
    assert "T0 is a constant function" in report["legacy_t0_comparison_not_decisive"]["note"]


def test_the_checker_recomputes_rather_than_trusting_the_runner(measurements):
    """Behavioural, not a grep: a planted verdict must not survive into the report.

    The previous version searched the checker's source for a string, which proves nothing about
    what it does with a record that carries a verdict.
    """
    planted = json.loads(json.dumps(measurements))
    planted["verdict"] = "positive"
    planted["hypothesis_status"] = "supported"
    planted["p_value"] = 0.0
    planted["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in planted.items() if k != "measurements_sha256"}))
    honest = checker.check(measurements)
    report = checker.check(planted)
    assert report["verdict"] == honest["verdict"]
    assert report["primary"]["p_value"] == honest["primary"]["p_value"]


def test_a_forged_outcome_series_is_refused(measurements):
    """Rewriting the paired outcomes without touching the per-demand record is caught.

    This test previously forged the series to force a positive verdict, which the checker accepted
    because it read the aggregate rather than recomputing it. It now recomputes from `entries`, so
    the forgery is the thing under test.
    """
    forged = json.loads(json.dumps(measurements))
    n = len(forged["paired_primary_outcomes"]["M3"])
    forged["paired_primary_outcomes"]["M3"] = [True] * n
    forged["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="recomputed primary outcomes disagree"):
        checker.check(forged)


def test_a_forged_guard_measure_is_refused(measurements):
    """The guards are evaluated on aggregates, so those aggregates must be recomputed too."""
    forged = json.loads(json.dumps(measurements))
    forged["measures"]["M3"]["correct_construction"] += 7
    forged["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="recomputed correct_construction disagrees"):
        checker.check(forged)


def test_an_attacker_chosen_comparator_seed_is_refused(measurements):
    """Freshness was recomputed from a seed the record supplied, never compared to the frozen one."""
    forged = json.loads(json.dumps(measurements))
    forged["fresh_uniform_seed"] = "attacker-chosen-seed"
    forged["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="comparator seed is not the frozen one"):
        checker.check(forged)


def test_a_bank_below_the_plans_minimum_is_refused(measurements):
    forged = json.loads(json.dumps(measurements))
    forged["minimum_qualifying_carriers"] = forged["qualifying_carriers"] + 1
    forged["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="below the minimum qualifying carriers"):
        checker.check(forged)


def test_a_failed_producer_provenance_check_is_refused(measurements):
    forged = json.loads(json.dumps(measurements))
    key = sorted(forged["provenance_checks"])[0]
    forged["provenance_checks"][key] = False
    forged["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="provenance check did not hold"):
        checker.check(forged)


def test_a_budget_not_from_the_committed_plan_is_refused(measurements):
    forged = json.loads(json.dumps(measurements))
    forged["session_budget_came_from_the_committed_plan"] = False
    forged["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "measurements_sha256"}))
    with pytest.raises(checker.CheckError, match="did not come from the committed plan"):
        checker.check(forged)


def test_the_dominance_guards_reach_the_verdict(measurements):
    """T0 and M2 must be able to veto, so the checker has to pass them to the endpoint."""
    report = checker.check(measurements)
    assert set(report["primary"]["dominance"]["guards"]) == {"T0", "M2"}
