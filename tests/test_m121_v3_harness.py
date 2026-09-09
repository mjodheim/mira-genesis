"""Tests for the M121/H66 v3 apparatus.

The load-bearing test in this file is not that the apparatus is correct. It is that the apparatus
**can fail**: v2 passed 76 tests while being unable to return a negative, so a suite that only
checks intended behaviour is exactly the reassurance that misled it.
"""
from __future__ import annotations

import hashlib
import math

import pytest

from metamorphosis.m121_long_horizon_v2 import ApparatusError
from metamorphosis.m121_long_horizon_v3 import (
    ARMS,
    BOUNDARY_PERIOD,
    DEFERRED_SLOTS,
    DEVELOPMENT_SALT,
    HORIZONS,
    MONITOR_SLOTS_PER_BOUNDARY,
    SETTLEMENT_PERIOD,
    arm_capabilities,
    assert_schedule_taxonomy,
    build_schedule,
    eligible_episodes,
    is_boundary,
    is_settlement,
    monitor_window,
    run_arm,
    run_horizon,
)

#: Development salts. None of these is or may become the canonical draw.
SALTS = [hashlib.sha256(b"m121-v3-dev-%d" % index).digest() for index in range(40)]


def _campaign(salt):
    return {h: run_horizon(salt, h) for h in HORIZONS}


# -- the point of v3 ---------------------------------------------------------------------------

def test_the_verdict_bearing_metrics_actually_vary_across_salts():
    """v2's defect, asserted against directly: a constant metric decides nothing."""
    observed = {name: set() for name in (
        "quiescent_detections_before_harm",
        "residual_corruption",
        "unrecovered_silent_divergent_outputs",
    )}
    for salt in SALTS:
        for horizon in HORIZONS:
            full = run_horizon(salt, horizon)["arms"]["full"]
            for name in observed:
                observed[name].add(full[name])
    for name, values in observed.items():
        assert len(values) > 1, "%s is constant across salts; the salt decides nothing" % name


def test_the_apparatus_can_return_a_negative_on_some_salt():
    """At least one development salt must violate a clause the checker would treat as negative."""
    def violates(record):
        full = record["arms"]["full"]
        monitor = record["arms"]["no_constraint_monitor"]
        return (
            full["quiescent_detections_before_harm"]
            <= monitor["quiescent_detections_before_harm"]
            or full["residual_corruption"] != 0
            or full["unrecovered_silent_divergent_outputs"] != 0
        )

    assert any(
        violates(run_horizon(salt, horizon)) for salt in SALTS for horizon in HORIZONS
    ), "no development salt produces a negative; the apparatus cannot fail"


def test_the_horizon_changes_coverage_instead_of_being_decorative():
    """v2 produced identical numbers at every horizon, so it tested nothing about horizon."""
    per_horizon = {
        horizon: [
            run_horizon(salt, horizon)["arms"]["full"]["quiescent_detections_before_harm"]
            for salt in SALTS
        ]
        for horizon in HORIZONS
    }
    shortest = sum(per_horizon[HORIZONS[0]]) / len(SALTS)
    longest = sum(per_horizon[HORIZONS[-1]]) / len(SALTS)
    assert longest > shortest, "coverage does not improve with horizon"


# -- controls must stay robust; that is what makes them controls --------------------------------

@pytest.mark.parametrize("arm", ("full", "no_constraint_monitor", "no_checkpoint", "random_audit"))
def test_operational_detection_is_a_robust_positive_control(arm):
    for salt in SALTS[:10]:
        for horizon in HORIZONS:
            observed = run_horizon(salt, horizon)["arms"][arm]
            assert observed["operational_detections_before_harm"] == 4


def test_the_checkpoint_ablation_loses_repair_and_only_repair():
    for salt in SALTS[:10]:
        for horizon in HORIZONS:
            arm = run_horizon(salt, horizon)["arms"]["no_checkpoint"]
            assert arm["recovery_successes"] == 0
            assert arm["residual_corruption"] > 0


def test_the_monitor_ablation_never_sees_the_quiescent_plane():
    for salt in SALTS[:10]:
        for horizon in HORIZONS:
            arm = run_horizon(salt, horizon)["arms"]["no_constraint_monitor"]
            assert arm["quiescent_detections_before_harm"] == 0


def test_the_idle_floor_completes_nothing():
    for horizon in HORIZONS:
        assert run_horizon(DEVELOPMENT_SALT, horizon)["arms"]["idle_floor"][
            "completed_work_items"
        ] == 0


# -- the cadence and the budget are what create the variance ------------------------------------

def test_the_cadences_are_coprime_so_most_settlements_are_unaudited():
    assert math.gcd(BOUNDARY_PERIOD, SETTLEMENT_PERIOD) == 1
    settlements = [e for e in range(400) if is_settlement(e)]
    audited = [e for e in settlements if is_boundary(e)]
    assert 0 < len(audited) < len(settlements) / 2


def test_injection_windows_exclude_both_event_kinds():
    for horizon in HORIZONS:
        for quartile in range(4):
            window = eligible_episodes(horizon, quartile)
            assert window
            assert not any(is_boundary(e) or is_settlement(e) for e in window)


def test_the_monitor_spends_a_bounded_budget():
    for index in range(20):
        for arm in ("full", "random_audit"):
            window = monitor_window(index, arm=arm, salt=DEVELOPMENT_SALT)
            assert len(window) == MONITOR_SLOTS_PER_BOUNDARY
            assert len(set(window)) == len(window)
            assert all(0 <= slot < DEFERRED_SLOTS for slot in window)


def test_the_structured_cursor_covers_every_slot_and_ignores_arm_history():
    covered = set()
    for index in range(DEFERRED_SLOTS // MONITOR_SLOTS_PER_BOUNDARY):
        covered |= set(monitor_window(index, arm="full", salt=DEVELOPMENT_SALT))
    assert covered == set(range(DEFERRED_SLOTS))
    # A pure function of the boundary index: two monitor-carrying arms cannot diverge for a
    # scheduling reason, only for the capability an ablation removed.
    assert monitor_window(3, arm="full", salt=DEVELOPMENT_SALT) == monitor_window(
        3, arm="no_checkpoint", salt=DEVELOPMENT_SALT
    )


def test_the_matched_control_spends_the_same_budget_on_different_slots():
    differ = sum(
        monitor_window(index, arm="full", salt=DEVELOPMENT_SALT)
        != monitor_window(index, arm="random_audit", salt=DEVELOPMENT_SALT)
        for index in range(40)
    )
    assert differ > 0, "the matched control inspects the same slots and controls for nothing"


def test_the_closing_audit_repairs_without_inflating_pre_harm_coverage():
    """A fault found only at the end was not found before harm."""
    for salt in SALTS[:15]:
        for horizon in HORIZONS:
            full = run_horizon(salt, horizon)["arms"]["full"]
            assert full["quiescent_detections_before_harm"] <= full["injected_quiescent_faults"]
            assert full["closing_audit_detections"] >= 0


# -- determinism and taxonomy -------------------------------------------------------------------

@pytest.mark.parametrize("horizon", HORIZONS)
def test_the_schedule_regenerates_and_the_taxonomy_holds(horizon):
    first = build_schedule(DEVELOPMENT_SALT, horizon)
    assert first == build_schedule(DEVELOPMENT_SALT, horizon)
    assert_schedule_taxonomy(first)
    assert len(first["faults"]) == 8


@pytest.mark.parametrize("arm", ARMS)
def test_every_arm_replays_identically(arm):
    schedule = build_schedule(DEVELOPMENT_SALT, 128)
    assert run_arm(arm, schedule, DEVELOPMENT_SALT) == run_arm(arm, schedule, DEVELOPMENT_SALT)


def test_every_arm_shares_its_horizon_schedule():
    for horizon in HORIZONS:
        record = run_horizon(DEVELOPMENT_SALT, horizon)
        digests = {record["arms"][arm]["schedule_sha256"] for arm in ARMS}
        assert digests == {record["schedule"]["schedule_sha256"]}


def test_no_arm_reaches_a_model_a_network_or_a_remote_executor():
    for horizon in HORIZONS:
        for arm in ARMS:
            observed = run_horizon(DEVELOPMENT_SALT, horizon)["arms"][arm]
            assert observed["model_calls"] == 0
            assert observed["network_calls"] == 0
            assert observed["remote_executions"] == 0


def test_unfrozen_arms_horizons_and_salts_are_refused():
    with pytest.raises(ApparatusError):
        arm_capabilities("optimistic")
    with pytest.raises(ApparatusError):
        build_schedule(DEVELOPMENT_SALT, 64)
    with pytest.raises(ApparatusError):
        build_schedule(b"short", 32)


def test_v3_does_not_edit_v2():
    """v2's finding is the record of what went wrong and must survive its successor."""
    from metamorphosis import m121_long_horizon_v2 as v2

    assert v2.BOUNDARY_PERIOD == 4 and v2.SETTLEMENT_PERIOD == 8
    assert not hasattr(v2, "MONITOR_SLOTS_PER_BOUNDARY")
