from __future__ import annotations

import pytest

from metamorphosis.m026_metaproductivity import score_state
from metamorphosis.m029_component_probe import component_probe_is_disjoint
from metamorphosis.m031_structural_transport import (
    DEVELOPMENT_SEED_COUNT,
    DEVELOPMENT_SEED_START,
    DEVELOPMENT_SEEDS,
    SMOKE_SEED_START,
    STRATEGIES,
    build_transport_aligned_rig,
    build_transport_mismatch_rig,
    run_trial,
    summarize_runs,
    verify_transport_controls,
)


def test_primary_seed_block_is_separate_from_all_smoke_tests():
    assert DEVELOPMENT_SEED_START == 0
    assert DEVELOPMENT_SEED_COUNT == 64
    assert DEVELOPMENT_SEEDS == frozenset(range(64))
    assert DEVELOPMENT_SEEDS.isdisjoint(range(SMOKE_SEED_START, SMOKE_SEED_START + 4))


def test_transport_generator_changes_structure_on_nonprimary_seed():
    rig = build_transport_mismatch_rig(SMOKE_SEED_START)
    generic = [action for action in rig.actions if action.name.startswith("generic_")]
    assert len(generic) == 4
    assert {len(action.atoms) for action in generic} == {3}
    assert len(rig.development_cases) == 8
    assert len(rig.hidden_cases) == 8
    assert {len(case) for case in rig.development_cases} == {9}
    assert {action.prerequisite for action in generic} == {
        "scaffold_left",
        "scaffold_right",
    }
    assert set(rig.development_cases).isdisjoint(rig.hidden_cases)


def test_transport_controls_and_probe_isolation_pass_on_nonprimary_seed():
    assert all(verify_transport_controls(SMOKE_SEED_START).values())
    assert component_probe_is_disjoint(build_transport_mismatch_rig(SMOKE_SEED_START))
    aligned = build_transport_aligned_rig(SMOKE_SEED_START)
    assert component_probe_is_disjoint(aligned)
    assert len(aligned.actions) == len(build_transport_mismatch_rig(SMOKE_SEED_START).actions)


def test_aligned_generator_has_exact_quality_for_representative_states():
    rig = build_transport_aligned_rig(SMOKE_SEED_START + 1)
    states = (
        (),
        ("scaffold_left",),
        tuple(sorted(("scaffold_left", "generic_0"))),
        tuple(sorted(("scaffold_left", "scaffold_right", "generic_0", "generic_2"))),
    )
    for state in states:
        assert score_state(rig, state, "development") == score_state(rig, state, "hidden")


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("rig", ("mismatch", "aligned"))
def test_nonprimary_trial_is_deterministic_and_isolated(strategy, rig):
    first = run_trial(rig, strategy, SMOKE_SEED_START + 2, policy_budget=5)
    second = run_trial(rig, strategy, SMOKE_SEED_START + 2, policy_budget=5)
    assert first == second
    assert first["development_seed"] is False
    assert first["coverage_exact"] is True
    assert first["unique_task_evaluations"] is True
    assert first["transport_controls_pass"] is True
    assert first["component_probe_hidden_disjoint"] is True
    assert first["hidden_fields_visible_to_selector"] is False


def test_aligned_nonprimary_trial_preserves_exact_equality():
    for strategy in STRATEGIES:
        row = run_trial("aligned", strategy, SMOKE_SEED_START + 3, policy_budget=8)
        assert row["final_development_per_mille"] == row["final_hidden_per_mille"]


def test_summary_rejects_incomplete_pairs_without_touching_primary_block():
    rows = [
        run_trial(rig, strategy, SMOKE_SEED_START, policy_budget=1)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
    ]
    rows.pop()
    with pytest.raises(ValueError, match="at least one seed"):
        summarize_runs(rows)


def test_underpowered_nonprimary_summary_cannot_support_transport():
    rows = [
        run_trial(rig, strategy, seed, policy_budget=2)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
        for seed in range(SMOKE_SEED_START, SMOKE_SEED_START + 2)
    ]
    summary = summarize_runs(rows)
    assert summary["comparison_status"] == "insufficient_paired_seeds"
    assert summary["exact_development_seed_range"] is False
    assert summary["uniform_component_signal_transported"] is False
