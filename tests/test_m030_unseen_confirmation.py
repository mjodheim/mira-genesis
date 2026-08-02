from __future__ import annotations

import pytest

from metamorphosis.m029_component_probe import run_trial as run_m029_trial
from metamorphosis.m030_unseen_confirmation import (
    CONFIRMATION_SEED_COUNT,
    CONFIRMATION_SEED_START,
    CONFIRMATION_SEEDS,
    STRATEGIES,
    run_trial,
    summarize_runs,
)


def test_confirmation_seed_block_is_exact_and_separate_from_smoke_seeds():
    assert CONFIRMATION_SEED_START == 64
    assert CONFIRMATION_SEED_COUNT == 64
    assert CONFIRMATION_SEEDS == frozenset(range(64, 128))
    assert CONFIRMATION_SEEDS.isdisjoint(range(128, 132))


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("rig", ("mismatch", "aligned"))
def test_wrapper_reexecutes_frozen_m029_paths_on_nonconfirmation_seed(strategy, rig):
    m029 = run_m029_trial(rig, strategy, 128, policy_budget=5)
    m030 = run_trial(rig, strategy, 128, policy_budget=5)

    assert m030["confirmation_seed"] is False
    for key in (
        "coverage_trace",
        "evaluation_trace",
        "policy_trace",
        "final_state",
        "final_development_per_mille",
        "final_hidden_per_mille",
        "weighted_clade_exact_cmp_concordance_per_mille",
    ):
        assert m030[key] == m029[key]


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("rig", ("mismatch", "aligned"))
def test_nonconfirmation_smoke_trial_is_deterministic_and_isolated(strategy, rig):
    first = run_trial(rig, strategy, 129, policy_budget=8)
    second = run_trial(rig, strategy, 129, policy_budget=8)

    assert first == second
    assert first["confirmation_seed"] is False
    assert first["coverage_exact"] is True
    assert first["unique_task_evaluations"] is True
    assert first["component_probe_controls_pass"] is True
    assert first["component_probe_hidden_disjoint"] is True
    assert first["hidden_fields_visible_to_selector"] is False


def test_aligned_nonconfirmation_trial_preserves_exact_equality():
    for strategy in STRATEGIES:
        row = run_trial("aligned", strategy, 130, policy_budget=12)
        assert row["final_development_per_mille"] == row["final_hidden_per_mille"]


def test_summary_rejects_incomplete_pairs_without_touching_confirmation_block():
    rows = [
        run_trial(rig, strategy, 128, policy_budget=1)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
    ]
    rows.pop()
    with pytest.raises(ValueError, match="at least one seed"):
        summarize_runs(rows)


def test_underpowered_nonconfirmation_summary_cannot_support_confirmation():
    rows = [
        run_trial(rig, strategy, seed, policy_budget=2)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
        for seed in range(128, 130)
    ]
    summary = summarize_runs(rows)
    assert summary["comparison_status"] == "insufficient_paired_seeds"
    assert summary["exact_confirmation_seed_range"] is False
    assert summary["uniform_component_signal_confirmed"] is False
