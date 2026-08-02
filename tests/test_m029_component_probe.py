from __future__ import annotations

import pytest

from metamorphosis.m026_metaproductivity import build_aligned_rig, build_mismatch_rig
from metamorphosis.m028_adaptive_evaluation import run_trial as run_m028_trial
from metamorphosis.m029_component_probe import (
    STRATEGIES,
    component_probe_is_disjoint,
    component_probe_outcomes,
    component_probe_tasks,
    run_trial,
    summarize_runs,
    verify_component_controls,
)


@pytest.mark.parametrize("seed", range(8))
def test_component_probe_controls_pass_across_structural_seeds(seed):
    assert all(verify_component_controls(seed).values())


@pytest.mark.parametrize("builder", (build_mismatch_rig, build_aligned_rig))
def test_component_cases_are_unique_and_disjoint_from_both_sealed_suites(builder):
    rig = builder(4)
    tasks = component_probe_tasks(rig)
    cases = [task.case for task in tasks]

    assert len(cases) == len(set(cases))
    assert set(cases).isdisjoint(rig.development_cases)
    assert set(cases).isdisjoint(rig.hidden_cases)
    assert component_probe_is_disjoint(rig) is True


def test_component_probe_separates_generic_reuse_from_shortcut_memorisation():
    rig = build_mismatch_rig(0)
    generic_state = tuple(sorted(("platform", "generic_0")))
    shortcut_state = ("shortcut_0",)

    assert sum(component_probe_outcomes(rig, generic_state)) == 2
    assert sum(component_probe_outcomes(rig, shortcut_state)) == 0


def test_development_baseline_reexecutes_frozen_m028_policy():
    m028 = run_m028_trial(
        "mismatch",
        "adaptive_evaluation",
        6,
        policy_budget=5,
    )
    m029 = run_trial(
        "mismatch",
        "development_adaptive",
        6,
        policy_budget=5,
    )

    for key in (
        "coverage_trace",
        "evaluation_trace",
        "policy_trace",
        "final_state",
        "final_development_per_mille",
        "final_hidden_per_mille",
        "weighted_clade_exact_cmp_concordance_per_mille",
    ):
        assert m029[key] == m028[key]


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
    assert first["component_probe_controls_pass"] is True
    assert first["component_probe_hidden_disjoint"] is True
    assert first["integer_only_selection_trace"] is True
    assert first["hidden_fields_visible_to_selector"] is False
    assert first["total_evaluations"] == 3 * first["archive_nodes"]


@pytest.mark.parametrize(
    "strategy",
    ("component_uniform", "component_adaptive"),
)
def test_component_trials_never_repeat_a_node_task_pair(strategy):
    row = run_trial("mismatch", strategy, 5, policy_budget=10)
    tasks_by_node: dict[int, list[int]] = {}
    for event in row["evaluation_trace"]:
        tasks_by_node.setdefault(int(event["node_id"]), []).append(
            int(event["task_index"])
        )
    assert all(len(tasks) == len(set(tasks)) for tasks in tasks_by_node.values())
    assert all(len(tasks) <= 8 for tasks in tasks_by_node.values())


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
    assert summary["component_signal_supported"] is False
