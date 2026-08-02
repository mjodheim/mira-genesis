from __future__ import annotations

from dataclasses import fields
import inspect
import random

import pytest

from metamorphosis.m026_metaproductivity import (
    PUBLIC_SELECTORS,
    STRATEGIES,
    PublicArchive,
    PublicNode,
    _fixed_sigmoid_weight,
    _integer_beta_order_statistic,
    build_aligned_rig,
    build_mismatch_rig,
    clade_development_counts,
    exact_clade_hidden_successes,
    run_trial,
    score_state,
    summarize_runs,
    verify_structural_controls,
)


def test_positive_control_reverses_immediate_score_and_exact_potential():
    assert all(verify_structural_controls(0).values())
    rig = build_mismatch_rig(0)

    assert score_state(rig, ("platform",), "development") == 0
    assert score_state(rig, ("shortcut_0",), "development") == 1
    assert exact_clade_hidden_successes(rig, ("platform",)) == 6
    assert exact_clade_hidden_successes(rig, ("shortcut_0",)) == 3


def test_aligned_control_has_distinct_cases_but_identical_exact_scores():
    rig = build_aligned_rig(3)
    assert rig.development_cases != rig.hidden_cases
    states = [
        (),
        ("platform",),
        ("generic_0",),
        ("generic_0", "generic_1"),
    ]
    for state in states:
        assert score_state(rig, state, "development") == score_state(
            rig, state, "hidden"
        )


def test_aligned_control_is_exhaustively_checked():
    controls = verify_structural_controls(9)
    assert controls["aligned_current_quality_is_exact"] is True


def test_rigs_are_deterministic_and_seeded():
    assert build_mismatch_rig(4) == build_mismatch_rig(4)
    assert build_mismatch_rig(4) != build_mismatch_rig(5)
    assert build_aligned_rig(4) == build_aligned_rig(4)


def test_selector_boundary_contains_no_hidden_or_exact_field():
    names = {field.name for field in fields(PublicNode)}
    assert not any("hidden" in name or "exact" in name for name in names)
    for selector in PUBLIC_SELECTORS.values():
        assert tuple(inspect.signature(selector).parameters) == ("archive", "rng")


def test_clade_counts_include_observed_descendants():
    archive = PublicArchive(
        nodes=(
            PublicNode(0, None, 0, 0, 6, (1, 2), True),
            PublicNode(1, 0, 1, 1, 6, (3,), True),
            PublicNode(2, 0, 1, 2, 6, (), True),
            PublicNode(3, 1, 2, 6, 6, (), False),
        ),
        step=3,
        budget=10,
    )

    assert clade_development_counts(archive, 0) == (9, 15)
    assert clade_development_counts(archive, 1) == (7, 5)
    assert clade_development_counts(archive, 2) == (2, 4)


def test_dgm_fixed_point_score_is_monotone_and_child_discount_is_external():
    weights = [_fixed_sigmoid_weight(value, 6) for value in range(7)]
    assert weights == sorted(weights)
    assert len(set(weights)) == len(weights)


def test_integer_beta_order_statistic_is_reproducible_and_bounded():
    first = random.Random(7)
    second = random.Random(7)
    draws = [_integer_beta_order_statistic(3, 5, first) for _ in range(20)]
    assert draws == [_integer_beta_order_statistic(3, 5, second) for _ in range(20)]
    assert all(0 <= value < 2**64 for value in draws)


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("rig", ("mismatch", "aligned"))
def test_trial_is_deterministic_complete_and_traceable(strategy, rig):
    first = run_trial(rig, strategy, 2, budget=12)
    second = run_trial(rig, strategy, 2, budget=12)

    assert first == second
    assert first["archive_nodes"] == first["expansions"] + 1
    assert first["integer_only_selection_trace"] is True
    assert first["hidden_fields_visible_to_selector"] is False


def test_aligned_trial_never_creates_a_visible_hidden_gap():
    for strategy in STRATEGIES:
        row = run_trial("aligned", strategy, 8, budget=20)
        assert row["final_development_per_mille"] == row["final_hidden_per_mille"]


def test_summary_rejects_incomplete_pairs():
    rows = [run_trial(rig, strategy, 0, budget=4) for rig in ("mismatch", "aligned") for strategy in STRATEGIES]
    rows.pop()
    with pytest.raises(ValueError, match="at least one seed"):
        summarize_runs(rows)
