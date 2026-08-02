"""M030 — untouched-seed confirmation of M029's component-uniform diagnostic."""

from __future__ import annotations

from statistics import median
from typing import Iterable, Sequence

from .m028_adaptive_evaluation import DEFAULT_POLICY_BUDGET
from .m029_component_probe import run_trial as run_m029_trial


CONFIRMATION_SEED_START = 64
CONFIRMATION_SEED_COUNT = 64
CONFIRMATION_SEEDS = frozenset(
    range(CONFIRMATION_SEED_START, CONFIRMATION_SEED_START + CONFIRMATION_SEED_COUNT)
)
ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE = 0
ESTIMATOR_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_WIN_FLOOR = 40
PROTOCOL_VERSION = "M030-development-v1"
STRATEGIES = ("development_adaptive", "component_uniform")


def run_trial(
    rig_name: str,
    strategy: str,
    seed: int,
    *,
    policy_budget: int = DEFAULT_POLICY_BUDGET,
) -> dict[str, object]:
    if strategy not in STRATEGIES:
        raise ValueError("unknown M030 strategy")
    row = dict(
        run_m029_trial(
            rig_name,
            strategy,
            seed,
            policy_budget=policy_budget,
        )
    )
    row["confirmation_seed"] = seed in CONFIRMATION_SEEDS
    return row


def _integer_median(values: Iterable[int]) -> int:
    rows = list(values)
    return int(median(rows)) if rows else 0


def summarize_runs(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    expected_rigs = {"mismatch", "aligned"}
    expected_strategies = set(STRATEGIES)
    seed_sets = {
        (rig, strategy): {
            int(row["seed"])
            for row in runs
            if row["rig"] == rig and row["strategy"] == strategy
        }
        for rig in expected_rigs
        for strategy in expected_strategies
    }
    if any(not seeds for seeds in seed_sets.values()):
        raise ValueError("every rig and strategy requires at least one seed")
    reference = seed_sets[("mismatch", "development_adaptive")]
    if any(seeds != reference for seeds in seed_sets.values()):
        raise ValueError("M030 runs are not paired across rigs and strategies")
    expected_rows = len(reference) * len(expected_rigs) * len(expected_strategies)
    if len(runs) != expected_rows:
        raise ValueError("M030 runs contain missing or duplicate rows")

    exact_confirmation_range = reference == CONFIRMATION_SEEDS
    summary: dict[str, object] = {
        "development_only": True,
        "paired_seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "confirmation_seed_start": CONFIRMATION_SEED_START,
        "confirmation_seed_count": CONFIRMATION_SEED_COUNT,
        "exact_confirmation_seed_range": exact_confirmation_range,
        "frozen_m029_policy_paths": True,
        "common_layered_coverage": True,
        "common_evaluation_schedule": True,
        "common_parent_policy": True,
        "common_final_selector": True,
        "component_probe_controls_pass": all(
            bool(row["component_probe_controls_pass"]) for row in runs
        ),
        "component_probe_hidden_disjoint": all(
            bool(row["component_probe_hidden_disjoint"]) for row in runs
        ),
        "unique_task_evaluations": all(
            bool(row["unique_task_evaluations"]) for row in runs
        ),
        "integer_only_selection_traces": all(
            bool(row["integer_only_selection_trace"]) for row in runs
        ),
        "hidden_fields_visible_to_selectors": any(
            bool(row["hidden_fields_visible_to_selector"]) for row in runs
        ),
        "coverage_exact": all(bool(row["coverage_exact"]) for row in runs),
        "estimator_alignment_floor_per_mille": ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE,
        "estimator_separation_floor_per_mille": ESTIMATOR_SEPARATION_FLOOR_PER_MILLE,
        "policy_separation_floor_per_mille": POLICY_SEPARATION_FLOOR_PER_MILLE,
        "policy_win_floor": POLICY_WIN_FLOOR,
        "primary_metric": "paired final hidden exact quality per mille",
    }

    metrics = (
        "coverage_expansions",
        "total_evaluations",
        "final_development_per_mille",
        "final_hidden_per_mille",
        "best_hidden_per_mille",
        "weighted_clade_exact_cmp_concordance_per_mille",
    )
    for rig in sorted(expected_rigs):
        for strategy in STRATEGIES:
            selected = [
                row
                for row in runs
                if row["rig"] == rig and row["strategy"] == strategy
            ]
            prefix = f"{rig}_{strategy}"
            for metric in metrics:
                summary[f"{prefix}_{metric}_median"] = _integer_median(
                    int(row[metric]) for row in selected
                )

    component = {
        int(row["seed"]): row
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "component_uniform"
    }
    development = {
        int(row["seed"]): row
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "development_adaptive"
    }
    differences = [
        int(component[seed]["final_hidden_per_mille"])
        - int(development[seed]["final_hidden_per_mille"])
        for seed in sorted(reference)
    ]
    summary["mismatch_component_minus_development_median_per_mille"] = (
        _integer_median(differences)
    )
    summary["mismatch_component_wins"] = sum(value > 0 for value in differences)
    summary["mismatch_component_ties"] = sum(value == 0 for value in differences)
    summary["mismatch_component_losses"] = sum(value < 0 for value in differences)

    component_alignment = int(
        summary[
            "mismatch_component_uniform_weighted_clade_exact_cmp_concordance_per_mille_median"
        ]
    )
    development_alignment = int(
        summary[
            "mismatch_development_adaptive_weighted_clade_exact_cmp_concordance_per_mille_median"
        ]
    )
    summary["mismatch_component_minus_development_alignment_per_mille"] = (
        component_alignment - development_alignment
    )

    enough = len(reference) >= CONFIRMATION_SEED_COUNT
    estimator_supported = (
        enough
        and exact_confirmation_range
        and component_alignment >= ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE
        and int(summary["mismatch_component_minus_development_alignment_per_mille"])
        >= ESTIMATOR_SEPARATION_FLOOR_PER_MILLE
    )
    policy_supported = (
        enough
        and exact_confirmation_range
        and int(summary["mismatch_component_minus_development_median_per_mille"])
        >= POLICY_SEPARATION_FLOOR_PER_MILLE
        and int(summary["mismatch_component_wins"]) >= POLICY_WIN_FLOOR
    )
    aligned_exact = all(
        int(row["final_development_per_mille"])
        == int(row["final_hidden_per_mille"])
        for row in runs
        if row["rig"] == "aligned"
    )
    summary["enough_seeds_for_confirmation"] = enough
    summary["component_estimator_confirmation_supported"] = estimator_supported
    summary["component_policy_confirmation_supported"] = policy_supported
    summary["aligned_control_exact"] = aligned_exact
    summary["uniform_component_signal_confirmed"] = (
        estimator_supported
        and policy_supported
        and aligned_exact
        and bool(summary["coverage_exact"])
        and bool(summary["component_probe_controls_pass"])
        and bool(summary["component_probe_hidden_disjoint"])
        and bool(summary["unique_task_evaluations"])
        and not bool(summary["hidden_fields_visible_to_selectors"])
    )

    if not enough:
        status = "insufficient_paired_seeds"
    elif not exact_confirmation_range:
        status = "confirmation_seed_range_mismatch"
    elif not bool(summary["component_probe_controls_pass"]):
        status = "component_probe_control_failed"
    elif not bool(summary["coverage_exact"]):
        status = "coverage_control_failed"
    elif not aligned_exact:
        status = "aligned_control_failed"
    elif bool(summary["uniform_component_signal_confirmed"]):
        status = "uniform_component_signal_confirmed"
    elif estimator_supported:
        status = "component_estimator_without_confirmed_policy_advantage"
    else:
        status = "uniform_component_confirmation_not_supported"
    summary["comparison_status"] = status
    return summary
