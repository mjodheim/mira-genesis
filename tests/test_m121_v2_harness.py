"""Hostile offline tests for the M121/H66 v2 apparatus.

No test draws a canonical salt, records a scientific observation or advances G7. Every test runs on
the public DEVELOPMENT fixture salt the design candidate forbids from becoming the canonical draw.

The tests are written to be able to fail. Each mechanism claim the apparatus makes is paired with a
construction in which the opposite outcome would be observable if the claim were false.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m121_long_horizon_v2 as apparatus
from metamorphosis.m121_long_horizon_v2 import (
    ACTIVE_RECORDS,
    ARMS,
    DEFERRED_SLOTS,
    DEVELOPMENT_SALT,
    FAULT_CLASSES,
    HORIZONS,
    QUARTILES,
    ApparatusError,
    Body,
    Evaluator,
    GuardViolation,
    apply_fault,
    build_schedule,
    eligible_episodes,
    is_boundary,
    run_arm,
    run_horizon,
)
from scripts import check_m121_v2_result as checker
from scripts import run_m121_v2_development as runner

EXPECTED = 4


@pytest.fixture(scope="module")
def campaign():
    return {str(h): run_horizon(DEVELOPMENT_SALT, h) for h in HORIZONS}


# ---------------------------------------------------------------------------------------------
# Schedule generator
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("horizon", HORIZONS)
def test_schedule_regenerates_byte_identically(horizon):
    first = build_schedule(DEVELOPMENT_SALT, horizon)
    second = build_schedule(DEVELOPMENT_SALT, horizon)
    assert first == second
    assert first["schedule_sha256"] == second["schedule_sha256"]


@pytest.mark.parametrize("horizon", HORIZONS)
def test_checker_reimplementation_matches_the_apparatus_generator(horizon):
    """The checker must not be able to validate a generator defect by importing it."""
    assert checker._independent_schedule(DEVELOPMENT_SALT, horizon) == build_schedule(
        DEVELOPMENT_SALT, horizon
    )["faults"]


@pytest.mark.parametrize("horizon", HORIZONS)
def test_constant_fault_budget_and_class_balance(horizon):
    faults = build_schedule(DEVELOPMENT_SALT, horizon)["faults"]
    assert len(faults) == len(QUARTILES) * len(FAULT_CLASSES)
    for quartile in QUARTILES:
        for name in FAULT_CLASSES:
            rows = [r for r in faults if r["quartile"] == quartile and r["fault_class"] == name]
            assert len(rows) == 1
    for name in FAULT_CLASSES:
        targets = [r["target"] for r in faults if r["fault_class"] == name]
        assert len(set(targets)) == len(targets), "a repeated target can mask a detection"


@pytest.mark.parametrize("horizon", HORIZONS)
def test_injection_windows_exclude_edges_and_boundaries(horizon):
    span = horizon // 4
    for quartile in QUARTILES:
        window = eligible_episodes(horizon, quartile)
        low = quartile * span
        assert all(low + 2 <= e < low + span - 2 for e in window)
        assert not any(is_boundary(e) for e in window)


def test_a_horizon_too_short_to_exclude_its_edges_is_refused():
    with pytest.raises(ApparatusError):
        eligible_episodes(20, 0)


def test_schedule_rejects_a_salt_of_the_wrong_length():
    with pytest.raises(ApparatusError):
        build_schedule(b"short", 32)


def test_schedule_rejects_an_unfrozen_horizon():
    with pytest.raises(ApparatusError):
        build_schedule(DEVELOPMENT_SALT, 64)


def test_a_different_salt_moves_the_schedule():
    other = bytes((b + 1) % 256 for b in DEVELOPMENT_SALT)
    assert build_schedule(other, 512)["faults"] != build_schedule(DEVELOPMENT_SALT, 512)["faults"]


# ---------------------------------------------------------------------------------------------
# Body semantics: the two planes must differ in access semantics, not in labelling
# ---------------------------------------------------------------------------------------------
def test_an_operational_fault_is_refused_by_the_very_next_operation():
    body = Body()
    for episode in range(8):
        body.work(episode)
    apply_fault(body, {"fault_class": "operational", "subtype": "guard_desync", "target": 5})
    with pytest.raises(GuardViolation) as raised:
        body.work(8)
    assert raised.value.index == 5


@pytest.mark.parametrize("subtype", ("deferred_value_shift", "deferred_slot_rotation"))
def test_a_quiescent_fault_is_invisible_to_guarded_work_but_breaks_the_invariant(subtype):
    body = Body()
    for episode in range(16):
        body.work(episode)
    apply_fault(body, {"fault_class": "quiescent", "subtype": subtype, "target": 3})
    assert body.violating_slots(), "the boundary invariant must see the corruption"
    for episode in range(16, 24):
        body.work(episode)  # ordinary guarded work must not raise on quiescent corruption


@pytest.mark.parametrize("subtype", ("deferred_value_shift", "deferred_slot_rotation"))
def test_an_ordinary_write_cannot_launder_a_corrupted_slot_clean(subtype):
    """The redundancy is advanced by the increment, never recomputed from the stored value."""
    body = Body()
    for episode in range(16):
        body.work(episode)
    apply_fault(body, {"fault_class": "quiescent", "subtype": subtype, "target": 0})
    assert 0 in body.violating_slots()
    for episode in range(16, 40):  # slot 0 is written repeatedly in this span
        body.work(episode)
    assert 0 in body.violating_slots(), "a later write recomputed the tag over corrupt state"


def test_a_quiescent_fault_changes_the_settlement_output():
    body = Body()
    for episode in range(16):
        body.work(episode)
    clean = body.settle()
    apply_fault(body, {"fault_class": "quiescent", "subtype": "deferred_value_shift", "target": 2})
    assert body.settle() != clean


def test_a_quarantined_record_is_skipped_rather_than_raising():
    body = Body()
    for episode in range(8):
        body.work(episode)
    apply_fault(body, {"fault_class": "operational", "subtype": "value_domain_break", "target": 0})
    with pytest.raises(GuardViolation):
        body.work(8)
    assert body.work(8, quarantined={0}) is None
    assert body.work(9, quarantined={0}) is not None


def test_apply_fault_rejects_unfrozen_subtypes():
    for fault_class in FAULT_CLASSES:
        with pytest.raises(ApparatusError):
            apply_fault(Body(), {"fault_class": fault_class, "subtype": "invented", "target": 0})


# ---------------------------------------------------------------------------------------------
# Ground-truth information boundary
# ---------------------------------------------------------------------------------------------
def test_no_lineage_visible_surface_carries_evaluator_ground_truth():
    """Enumerate every surface the lineage can read and fail to retrieve the hidden expectations."""
    horizon = 128
    evaluator = Evaluator(horizon)
    secrets = {str(value) for value in evaluator.expected.values()}
    assert secrets, "the evaluator must actually hold expectations for this to be a real test"

    schedule = build_schedule(DEVELOPMENT_SALT, horizon)
    body = Body()
    for episode in range(horizon):
        body.work(episode)
    surfaces = {
        "body_snapshot": body.snapshot(),
        "schedule": schedule,
        "arm_results": {arm: run_arm(arm, schedule) for arm in ARMS},
    }
    serialized = json.dumps(surfaces, sort_keys=True)
    leaked = sorted(value for value in secrets if value in serialized)
    assert not leaked, "evaluator ground truth is reachable from lineage-visible state: %s" % leaked


def test_the_evaluator_scores_from_its_own_record_not_from_a_self_report():
    evaluator = Evaluator(32)
    episode = max(evaluator.expected)
    assert evaluator.scores(episode, evaluator.expected[episode] + 1) is True
    assert evaluator.scores(episode, evaluator.expected[episode]) is False
    assert evaluator.scores(episode, None) is False, "a withheld output is not a divergence"


# ---------------------------------------------------------------------------------------------
# Arm dissociation
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("horizon", HORIZONS)
def test_operational_detection_is_a_positive_control_independent_of_the_monitor(campaign, horizon):
    arms = campaign[str(horizon)]["arms"]
    assert arms["full"]["operational_detections_before_harm"] == EXPECTED
    assert arms["no_constraint_monitor"]["operational_detections_before_harm"] == EXPECTED
    assert arms["no_checkpoint"]["operational_detections_before_harm"] == EXPECTED


@pytest.mark.parametrize("horizon", HORIZONS)
def test_the_monitor_is_required_for_quiescent_coverage(campaign, horizon):
    arms = campaign[str(horizon)]["arms"]
    assert arms["full"]["quiescent_detections_before_harm"] == EXPECTED
    assert arms["no_constraint_monitor"]["quiescent_detections_before_harm"] == 0
    assert arms["no_constraint_monitor"]["silent_divergent_outputs"] > 0


@pytest.mark.parametrize("horizon", HORIZONS)
def test_full_retains_its_constraints_and_emits_nothing_silently_wrong(campaign, horizon):
    full = campaign[str(horizon)]["arms"]["full"]
    assert full["residual_corruption"] == 0
    assert full["silent_divergent_outputs"] == 0
    assert full["completed_work_items"] == horizon
    assert full["recovery_successes"] == full["recovery_attempts"]


@pytest.mark.parametrize("horizon", HORIZONS)
def test_removing_checkpoints_changes_recovery_but_not_detection(campaign, horizon):
    arms = campaign[str(horizon)]["arms"]
    full, no_checkpoint = arms["full"], arms["no_checkpoint"]
    assert no_checkpoint["recovery_successes"] == 0
    assert no_checkpoint["residual_corruption"] > 0
    assert (
        no_checkpoint["operational_detections_before_harm"]
        == full["operational_detections_before_harm"]
    )
    assert (
        no_checkpoint["quiescent_detections_before_harm"]
        == full["quiescent_detections_before_harm"]
    )


@pytest.mark.parametrize("horizon", HORIZONS)
def test_the_idle_floor_completes_zero_work_and_cannot_earn_a_clean_result(campaign, horizon):
    idle = campaign[str(horizon)]["arms"]["idle_floor"]
    assert idle["completed_work_items"] == 0
    assert idle["operational_detections_before_harm"] == 0
    assert idle["quiescent_detections_before_harm"] == 0


@pytest.mark.parametrize("horizon", HORIZONS)
def test_every_arm_receives_the_same_materialized_schedule(campaign, horizon):
    record = campaign[str(horizon)]
    digests = {record["arms"][arm]["schedule_sha256"] for arm in ARMS}
    assert digests == {record["schedule"]["schedule_sha256"]}


@pytest.mark.parametrize("horizon", HORIZONS)
def test_no_arm_reaches_a_model_a_network_or_a_remote_executor(campaign, horizon):
    for arm in ARMS:
        observed = campaign[str(horizon)]["arms"][arm]
        assert observed["model_calls"] == 0
        assert observed["network_calls"] == 0
        assert observed["remote_executions"] == 0


@pytest.mark.parametrize("arm", ARMS)
def test_every_arm_replays_identically(arm):
    schedule = build_schedule(DEVELOPMENT_SALT, 128)
    assert run_arm(arm, schedule) == run_arm(arm, schedule)


def test_an_unfrozen_arm_is_refused():
    with pytest.raises(ApparatusError):
        run_arm("optimistic", build_schedule(DEVELOPMENT_SALT, 32))


# ---------------------------------------------------------------------------------------------
# Runner and checker
# ---------------------------------------------------------------------------------------------
def test_the_development_runner_declares_itself_non_canonical_and_draws_no_salt():
    record = runner.development_record()
    assert record["canonical"] is False
    assert record["canonical_salt_drawn"] is False
    assert record["is_a_scientific_observation"] is False
    assert record["advances_a_generality_gate"] is False
    assert record["salt_is_the_public_development_fixture"] is True


def test_the_runner_exposes_no_way_to_supply_a_salt():
    """A canonical draw must remain an owner action taken after the apparatus is frozen."""
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "urandom" not in source and "token_bytes" not in source
    assert "--salt" not in source


def test_the_checker_scores_the_development_record_positive_without_claiming_evidence():
    outcome = checker.classify(runner.development_record(), DEVELOPMENT_SALT)
    assert outcome["verdict"] == "positive"
    assert outcome["problems"] == []


def test_the_checker_refuses_to_score_a_canonical_record(tmp_path, capsys):
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps({"canonical": True}), encoding="utf-8")
    assert runner_exit(path) == 2
    assert "not authorized to score a canonical" in capsys.readouterr().out


def runner_exit(path: Path) -> int:
    import sys

    argv = sys.argv
    sys.argv = ["check_m121_v2_result.py", str(path)]
    try:
        return checker.main()
    finally:
        sys.argv = argv


def test_a_tampered_schedule_is_an_instrument_abort():
    record = runner.development_record()
    record["campaign"]["horizons"]["32"]["schedule"]["faults"][0]["episode"] += 1
    outcome = checker.classify(record, DEVELOPMENT_SALT)
    assert outcome["verdict"] == "instrument_abort"


def test_a_tampered_arm_metric_is_an_instrument_abort_before_it_can_look_positive():
    record = runner.development_record()
    record["campaign"]["horizons"]["32"]["arms"]["full"]["quiescent_detections_before_harm"] = 99
    outcome = checker.classify(record, DEVELOPMENT_SALT)
    assert outcome["verdict"] == "instrument_abort"


def test_a_genuine_mechanism_failure_is_scored_negative_not_aborted(monkeypatch):
    """If the monitor stopped buying quiescent coverage the verdict must be negative."""
    record = runner.development_record()
    for horizon_record in record["campaign"]["horizons"].values():
        horizon_record["arms"]["full"]["quiescent_detections_before_harm"] = 0
    monkeypatch.setattr(checker, "instrument_aborts", lambda record, salt: [])
    outcome = checker.classify(record, DEVELOPMENT_SALT)
    assert outcome["verdict"] == "negative"
    assert any("strictly more quiescent" in problem for problem in outcome["problems"])


def test_an_idle_floor_that_completed_work_aborts_the_instrument():
    record = runner.development_record()
    record["campaign"]["horizons"]["32"]["arms"]["idle_floor"]["completed_work_items"] = 1
    outcome = checker.classify(record, DEVELOPMENT_SALT)
    assert outcome["verdict"] == "instrument_abort"


def test_the_development_record_is_stable_across_runs():
    """Reproducibility is asserted over the reproducible half, and only over it.

    Wall clock, CPU seconds and peak memory differ between two runs on one host, let alone between
    hosts. Folding them into record_sha256 would make an honest rerun look like tampering, so the
    digest must cover everything except them.
    """
    first, second = runner.development_record(), runner.development_record()
    assert first["record_sha256"] == second["record_sha256"]
    assert first["campaign"] == second["campaign"]
    assert first["cost"]["deterministic"] == second["cost"]["deterministic"]
    assert first["deterministic_cost_sha256"] == second["deterministic_cost_sha256"]
    without_cost = {k: v for k, v in first.items() if k not in ("cost", "deterministic_cost_sha256")}
    assert copy.deepcopy(without_cost) == {
        k: v for k, v in second.items() if k not in ("cost", "deterministic_cost_sha256")
    }


def test_environment_costs_are_recorded_but_never_folded_into_the_digest():
    record = runner.development_record()
    environment = record["cost"]["environment_costs"]
    assert environment["reproducible"] is False
    assert environment["wall_clock_seconds"] >= 0
    assert environment["cpu_seconds_is_a_compute_proxy_not_energy"] is True
    rebuilt = {k: v for k, v in record.items() if k not in ("record_sha256", "cost", "deterministic_cost_sha256")}
    from metamorphosis.m121_long_horizon_v2 import digest_of

    assert digest_of(rebuilt) == record["record_sha256"]


def test_the_campaign_reports_every_g9_dimension_and_prices_itself_at_zero():
    report = runner.development_record()["cost"]["report"]
    assert set(report) >= {"quality", "reliability", "latency", "compute_proxy", "monetary_cost"}
    assert report["compute_proxy"]["is_energy"] is False
    # An offline run has no billable tokens, so zero is arithmetic rather than an estimate.
    assert report["monetary_cost"]["amount"] == 0.0
    assert report["monetary_cost"]["no_billable_usage"] is True


def test_a_tampered_cost_count_is_an_instrument_abort():
    record = runner.development_record()
    record["cost"]["deterministic"]["work_items"] += 1
    outcome = checker.classify(record, DEVELOPMENT_SALT)
    assert outcome["verdict"] == "instrument_abort"
    assert any("work_items" in problem for problem in outcome["problems"])


def test_a_record_without_a_cost_section_is_an_instrument_abort():
    record = runner.development_record()
    del record["cost"]
    outcome = checker.classify(record, DEVELOPMENT_SALT)
    assert outcome["verdict"] == "instrument_abort"
    assert any("no G9 cost record" in problem for problem in outcome["problems"])
