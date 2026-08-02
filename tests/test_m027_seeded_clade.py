from __future__ import annotations

import inspect

import pytest

from metamorphosis.m026_metaproductivity import _Archive, build_aligned_rig, build_mismatch_rig
from metamorphosis.m027_seeded_clade import (
    STRATEGIES,
    coverage_is_exact,
    run_layered_coverage,
    run_trial,
    summarize_runs,
)


@pytest.mark.parametrize(
    ("builder", "expected_expansions"),
    ((build_mismatch_rig, 97), (build_aligned_rig, 63)),
)
def test_layered_coverage_is_exhaustive_through_depth_three(
    builder,
    expected_expansions,
):
    archive = _Archive(builder(0), seed=0, budget=40)
    trace = run_layered_coverage(archive)

    assert len(trace) == expected_expansions
    assert coverage_is_exact(archive) is True
    assert max(len(record.state) for record in archive.records) == 3


def test_layered_coverage_uses_no_hidden_or_exact_measure():
    source = inspect.getsource(run_layered_coverage)
    assert "hidden" not in source
    assert "exact" not in source


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("rig", ("mismatch", "aligned"))
def test_trial_is_deterministic_complete_and_isolated(strategy, rig):
    first = run_trial(rig, strategy, 3, policy_budget=8)
    second = run_trial(rig, strategy, 3, policy_budget=8)

    assert first == second
    assert first["coverage_exact"] is True
    assert first["policy_expansions"] == 8
    assert first["archive_nodes"] == first["total_expansions"] + 1
    assert first["integer_only_selection_trace"] is True
    assert first["hidden_fields_visible_to_selector"] is False


def test_mismatch_coverage_exposes_a_hidden_signal_before_guidance():
    for strategy in STRATEGIES:
        row = run_trial("mismatch", strategy, 5, policy_budget=1)
        assert row["coverage_best_hidden_per_mille"] >= 166


def test_aligned_trial_preserves_exact_visible_hidden_equality():
    for strategy in STRATEGIES:
        row = run_trial("aligned", strategy, 8, policy_budget=12)
        assert row["final_development_per_mille"] == row["final_hidden_per_mille"]


def test_summary_rejects_incomplete_pairs():
    rows = [
        run_trial(rig, strategy, 0, policy_budget=1)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
    ]
    rows.pop()
    with pytest.raises(ValueError, match="at least one seed"):
        summarize_runs(rows)


def test_underpowered_summary_cannot_support_prediction():
    rows = [
        run_trial(rig, strategy, seed, policy_budget=2)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
        for seed in range(2)
    ]
    summary = summarize_runs(rows)
    assert summary["comparison_status"] == "insufficient_paired_seeds"
    assert summary["seeded_clade_guidance_supported"] is False
