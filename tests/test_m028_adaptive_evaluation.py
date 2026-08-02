from __future__ import annotations

import inspect

import pytest

from metamorphosis.m028_adaptive_evaluation import (
    EVALUATION_SELECTORS,
    EvaluatedPublicNode,
    STRATEGIES,
    run_trial,
    select_adaptive_evaluation,
    select_weighted_clade_parent,
    summarize_runs,
)


def test_public_node_contains_only_structural_and_observed_fields():
    assert set(EvaluatedPublicNode.__dataclass_fields__) == {
        "node_id",
        "parent_id",
        "depth",
        "evaluation_successes",
        "evaluation_failures",
        "remaining_tasks",
        "children",
        "can_expand",
    }


def test_public_policies_do_not_read_hidden_exact_state_or_actions():
    for policy in (*EVALUATION_SELECTORS.values(), select_weighted_clade_parent):
        source = inspect.getsource(policy)
        assert "hidden" not in source
        assert "exact" not in source
        assert ".state" not in source
        assert "action" not in source


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("rig", ("mismatch", "aligned"))
def test_trial_is_deterministic_complete_and_isolated(strategy, rig):
    first = run_trial(rig, strategy, 3, policy_budget=8)
    second = run_trial(rig, strategy, 3, policy_budget=8)

    assert first == second
    assert first["coverage_exact"] is True
    assert first["policy_expansions"] == 8
    assert first["archive_nodes"] == first["covered_nodes"] + 8
    assert first["unique_task_evaluations"] is True
    assert first["integer_only_selection_trace"] is True
    assert first["hidden_fields_visible_to_selector"] is False
    assert first["total_evaluations"] == 3 * first["archive_nodes"]


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_each_node_receives_only_unique_development_tasks(strategy):
    row = run_trial("mismatch", strategy, 5, policy_budget=10)
    tasks_by_node: dict[int, list[int]] = {}
    for event in row["evaluation_trace"]:
        tasks_by_node.setdefault(int(event["node_id"]), []).append(
            int(event["task_index"])
        )
    assert all(len(tasks) == len(set(tasks)) for tasks in tasks_by_node.values())
    assert all(len(tasks) <= 6 for tasks in tasks_by_node.values())


def test_adaptive_evaluation_is_not_uniform_on_the_same_seed():
    uniform = run_trial("mismatch", "uniform_evaluation", 7, policy_budget=4)
    adaptive = run_trial("mismatch", "adaptive_evaluation", 7, policy_budget=4)
    uniform_targets = [
        row["node_id"]
        for row in uniform["evaluation_trace"]
        if row["phase"] != "initial"
    ]
    adaptive_targets = [
        row["node_id"]
        for row in adaptive["evaluation_trace"]
        if row["phase"] != "initial"
    ]
    assert uniform_targets != adaptive_targets


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
    assert summary["adaptive_evaluation_weighting_supported"] is False
