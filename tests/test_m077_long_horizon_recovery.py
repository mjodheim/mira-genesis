"""Regressions for the M077 long-horizon recovery shift, including its preserved negative."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m077_long_horizon_recovery import (
    ARMS,
    CHECKPOINT_INTERVAL,
    FAULT_KINDS,
    GENESIS_DIGEST,
    HORIZONS,
    OPERATIONAL_FAULTS,
    SILENT_FAULTS,
    SLOT_COUNT,
    Body,
    OperationalFault,
    ShiftError,
    build_schedule,
    evaluate,
    inject,
    run_arm,
    run_shift,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M077"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def arms(salt: bytes) -> dict:
    return {arm: run_arm(salt, arm) for arm in ARMS}


def test_schedule_is_deterministic(salt: bytes) -> None:
    for horizon in HORIZONS:
        assert build_schedule(salt, horizon) == build_schedule(salt, horizon)


def test_every_fault_kind_appears_at_each_horizon(salt: bytes) -> None:
    for horizon in HORIZONS:
        assert set(build_schedule(salt, horizon).values()) == set(FAULT_KINDS)


def test_schedule_matches_the_bound_commitment(salt: bytes) -> None:
    bound = json.loads((BASE / "SCHEDULE_COMMITMENT.json").read_text(encoding="utf-8"))
    for horizon in HORIZONS:
        replay = {str(k): v for k, v in build_schedule(salt, horizon).items()}
        assert replay == bound["schedules"][str(horizon)]


def test_fault_count_scales_with_horizon(salt: bytes) -> None:
    counts = [len(build_schedule(salt, horizon)) for horizon in HORIZONS]
    assert counts == [max(4, horizon // 64) for horizon in HORIZONS]


def test_full_arm_recovers_every_fault_at_every_horizon(arms: dict) -> None:
    for horizon in HORIZONS:
        row = arms["full"]["horizons"][str(horizon)]
        assert row["detections"] == row["faults_injected"]
        assert row["unrecovered_faults"] == 0
        assert row["undetected_faults"] == 0
        assert row["residual_violations"] == 0
        assert row["interventions"] == 0


def test_full_arm_retention_does_not_degrade_with_horizon(arms: dict) -> None:
    """The headline retention claim: perfect at 32 must still be perfect at 2048."""

    rates = [
        arms["full"]["horizons"][str(horizon)]["restoration_rate_on_detected"]
        for horizon in HORIZONS
    ]
    assert rates == [1.0, 1.0, 1.0, 1.0]


def test_no_checkpoint_loses_restoration_and_retains_detection(arms: dict) -> None:
    for horizon in HORIZONS:
        key = str(horizon)
        assert arms["no_checkpoint"]["horizons"][key]["restoration_rate_on_detected"] == 0.0
        assert arms["no_checkpoint"]["horizons"][key]["unrecovered_faults"] >= 1
        assert (
            arms["no_checkpoint"]["horizons"][key]["detections"]
            == arms["full"]["horizons"][key]["detections"]
        )


def test_no_constraint_monitor_retains_restoration(arms: dict) -> None:
    for horizon in HORIZONS:
        key = str(horizon)
        assert (
            arms["no_constraint_monitor"]["horizons"][key]["restoration_rate_on_detected"]
            == arms["full"]["horizons"][key]["restoration_rate_on_detected"]
        )


def test_the_refuted_half_stays_refuted(arms: dict) -> None:
    """Locks the negative: the monitor ablation does not lose detection below 2048.

    If a later change makes this pass, that is a different experiment and must be numbered
    separately rather than silently converting M077 into a positive.
    """

    undetected = [
        arms["no_constraint_monitor"]["horizons"][str(horizon)]["undetected_faults"]
        for horizon in HORIZONS
    ]
    assert undetected[:3] == [0, 0, 0]
    verdict = evaluate(arms)
    assert verdict.positive is False
    assert any("no_constraint_monitor" in reason for reason in verdict.reasons)


def test_idle_floor_completes_no_work_and_is_not_clean(arms: dict) -> None:
    for horizon in HORIZONS:
        row = arms["idle_floor"]["horizons"][str(horizon)]
        assert row["work_items_completed"] == 0
        assert row["residual_violations"] > 0


def test_operational_and_silent_faults_are_disjoint() -> None:
    assert set(OPERATIONAL_FAULTS).isdisjoint(SILENT_FAULTS)
    assert set(OPERATIONAL_FAULTS) | set(SILENT_FAULTS) == set(FAULT_KINDS)


def test_audit_catches_slot_type_corruption(salt: bytes) -> None:
    body = Body.build(salt)
    assert body.audit() == ()
    inject(body, "slot_type_corruption", salt, 0)
    assert "I1" in body.audit()


def test_audit_catches_journal_truncation(salt: bytes) -> None:
    body = Body.build(salt)
    body.apply_work(0, body.pool.slot_types[0])
    inject(body, "journal_truncation", salt, 0)
    assert "I2" in body.audit()


def test_audit_catches_capacity_overflow(salt: bytes) -> None:
    body = Body.build(salt)
    inject(body, "capacity_spike", salt, 0)
    assert "I3" in body.audit()


def test_truncated_journal_raises_operationally(salt: bytes) -> None:
    body = Body.build(salt)
    body.apply_work(0, body.pool.slot_types[0])
    inject(body, "journal_truncation", salt, 0)
    with pytest.raises(OperationalFault):
        body.apply_work(1, body.pool.slot_types[1])


def test_journal_chain_starts_at_genesis(salt: bytes) -> None:
    body = Body.build(salt)
    assert body.journal.digests[0] == GENESIS_DIGEST
    assert body.journal.chain_is_unbroken()


def test_restore_returns_the_body_to_a_clean_snapshot(salt: bytes) -> None:
    body = Body.build(salt)
    body.apply_work(0, body.pool.slot_types[0])
    checkpoint = body.snapshot()
    inject(body, "slot_type_corruption", salt, 1)
    assert body.audit()
    body.restore(checkpoint)
    assert body.audit() == ()


def test_unknown_fault_kind_is_rejected(salt: bytes) -> None:
    with pytest.raises(ShiftError):
        inject(Body.build(salt), "meltdown", salt, 0)


def test_unknown_arm_is_rejected(salt: bytes) -> None:
    with pytest.raises(ShiftError):
        run_shift(salt, 32, "wishful")


def test_replay_is_deterministic(salt: bytes) -> None:
    first = run_shift(salt, 128, "full")
    second = run_shift(salt, 128, "full")
    assert first.replay_digest == second.replay_digest


def test_checkpoint_interval_matches_the_protocol(protocol: dict) -> None:
    assert protocol["body"]["checkpoint_interval_episodes"] == CHECKPOINT_INTERVAL
    assert protocol["body"]["slots"] == SLOT_COUNT
    assert protocol["horizons"] == list(HORIZONS)


def test_preserved_result_reproduces(arms: dict) -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    for arm in ARMS:
        assert preserved["arms"][arm]["horizons"] == arms[arm]["horizons"]
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False


def test_preserved_result_records_the_negative_verdict() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["verdict"] == "negative"
    assert preserved["failed_conditions"]
    assert preserved["horizon_unit"] == "episode_count_not_human_equivalent_time"


def test_instrument_corrections_stay_visible() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert len(preserved["instrument_corrections_before_materialization"]) == 2


def test_claim_boundary_refuses_time_horizon_language(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["establishes_human_equivalent_time_horizon"] is False
    assert boundary["closes_generality_gate_g7"] is False
    assert boundary["agi_evidence"] is False
    assert "human_equivalent_task_horizons" in protocol["explicitly_not_addressed"]
