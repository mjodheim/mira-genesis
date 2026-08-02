"""M027 — hidden-blind breadth seeding before metaproductivity guidance.

M027 follows the negative M026 development result without changing either public
parent selector. It first enumerates every reachable archive state through depth three
using only public depth and expandability, then grants each policy forty further
expansions. The evaluator retains exclusive access to exact hidden rooted-clade quality.
"""

from __future__ import annotations

import random
from statistics import median
from typing import Iterable, Sequence

from .m026_metaproductivity import (
    PUBLIC_SELECTORS,
    PublicArchive,
    _Archive,
    _calibration,
    _per_mille,
    _reachable_states,
    _select_oracle_descendant,
    build_aligned_rig,
    build_mismatch_rig,
)


COVERAGE_MAX_DEPTH = 3
DEFAULT_POLICY_BUDGET = 40
DEVELOPMENT_MIN_SEEDS = 64
ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE = 0
ESTIMATOR_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_WIN_FLOOR = 40
PROTOCOL_VERSION = "M027-development-v1"
STRATEGIES = (*PUBLIC_SELECTORS, "oracle_guided")


def _next_coverage_parent(public: PublicArchive, depth: int) -> int | None:
    candidates = [node.node_id for node in public.eligible() if node.depth == depth]
    return min(candidates) if candidates else None


def run_layered_coverage(archive: _Archive) -> list[dict[str, object]]:
    """Enumerate all reachable states through depth three without quality access."""

    trace: list[dict[str, object]] = []
    for parent_depth in range(COVERAGE_MAX_DEPTH):
        while True:
            public = archive.public(len(trace))
            parent_id = _next_coverage_parent(public, parent_depth)
            if parent_id is None:
                break
            child, action_name = archive.expand(parent_id)
            trace.append(
                {
                    "phase": "coverage",
                    "step": len(trace),
                    "parent_id": parent_id,
                    "child_id": child.node_id,
                    "action": action_name,
                    "child_depth": len(child.state),
                    "child_development_successes": child.development_successes,
                }
            )
    return trace


def coverage_is_exact(archive: _Archive) -> bool:
    expected = {
        state
        for state in _reachable_states(archive.rig)
        if len(state) <= COVERAGE_MAX_DEPTH
    }
    observed = {
        record.state
        for record in archive.records
        if len(record.state) <= COVERAGE_MAX_DEPTH
    }
    return observed == expected


def run_trial(
    rig_name: str,
    strategy: str,
    seed: int,
    *,
    policy_budget: int = DEFAULT_POLICY_BUDGET,
) -> dict[str, object]:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if type(policy_budget) is not int or policy_budget < 1:
        raise ValueError("policy_budget must be a positive integer")
    if strategy not in STRATEGIES:
        raise ValueError("unknown M027 strategy")
    if rig_name == "mismatch":
        rig = build_mismatch_rig(seed)
    elif rig_name == "aligned":
        rig = build_aligned_rig(seed)
    else:
        raise ValueError("unknown M027 rig")

    archive = _Archive(rig, seed, policy_budget)
    coverage_trace = run_layered_coverage(archive)
    exact_coverage = coverage_is_exact(archive)
    coverage_best_hidden = max(record.hidden_successes for record in archive.records)
    rng = random.Random(seed * 104_729 + 27)
    policy_trace: list[dict[str, object]] = []

    for policy_step in range(policy_budget):
        public = archive.public(len(coverage_trace) + policy_step)
        if not public.eligible():
            break
        if strategy == "oracle_guided":
            parent_id = _select_oracle_descendant(archive, public)
        else:
            parent_id = PUBLIC_SELECTORS[strategy](public, rng)
        child, action_name = archive.expand(parent_id)
        policy_trace.append(
            {
                "phase": "policy",
                "step": policy_step,
                "parent_id": parent_id,
                "child_id": child.node_id,
                "action": action_name,
                "child_development_successes": child.development_successes,
            }
        )

    public = archive.public(len(coverage_trace) + len(policy_trace))
    final = min(
        archive.records,
        key=lambda record: (-record.development_successes, record.node_id),
    )
    best_hidden = max(
        archive.records,
        key=lambda record: (record.hidden_successes, -record.node_id),
    )
    immediate_calibration, clade_calibration = _calibration(archive, public)

    return {
        "rig": rig.name,
        "strategy": strategy,
        "seed": seed,
        "coverage_max_depth": COVERAGE_MAX_DEPTH,
        "coverage_expansions": len(coverage_trace),
        "coverage_exact": exact_coverage,
        "coverage_best_hidden_per_mille": _per_mille(
            coverage_best_hidden,
            rig.hidden_total,
        ),
        "policy_budget": policy_budget,
        "policy_expansions": len(policy_trace),
        "total_expansions": len(coverage_trace) + len(policy_trace),
        "archive_nodes": len(archive.records),
        "final_node_id": final.node_id,
        "final_state": list(final.state),
        "final_development_per_mille": _per_mille(
            final.development_successes,
            rig.development_total,
        ),
        "final_hidden_per_mille": _per_mille(
            final.hidden_successes,
            rig.hidden_total,
        ),
        "best_hidden_per_mille": _per_mille(
            best_hidden.hidden_successes,
            rig.hidden_total,
        ),
        "immediate_exact_cmp_concordance_per_mille": immediate_calibration,
        "clade_exact_cmp_concordance_per_mille": clade_calibration,
        "integer_only_selection_trace": True,
        "hidden_fields_visible_to_selector": False,
        "coverage_trace": coverage_trace,
        "policy_trace": policy_trace,
    }


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
    reference = seed_sets[("mismatch", "dgm_immediate")]
    if any(seeds != reference for seeds in seed_sets.values()):
        raise ValueError("M027 runs are not paired across rigs and strategies")
    expected_rows = len(reference) * len(expected_rigs) * len(expected_strategies)
    if len(runs) != expected_rows:
        raise ValueError("M027 runs contain missing or duplicate rows")

    summary: dict[str, object] = {
        "development_only": True,
        "paired_seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "development_min_seeds": DEVELOPMENT_MIN_SEEDS,
        "coverage_max_depth": COVERAGE_MAX_DEPTH,
        "common_layered_coverage": True,
        "common_task_families": True,
        "common_expansion_orders": True,
        "integer_only_selection_traces": all(
            bool(row["integer_only_selection_trace"]) for row in runs
        ),
        "hidden_fields_visible_to_selectors": any(
            bool(row["hidden_fields_visible_to_selector"]) for row in runs
        ),
        "coverage_exact": all(bool(row["coverage_exact"]) for row in runs),
        "mismatch_coverage_exposes_hidden_signal": all(
            int(row["coverage_best_hidden_per_mille"]) >= 166
            for row in runs
            if row["rig"] == "mismatch"
        ),
        "estimator_alignment_floor_per_mille": ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE,
        "estimator_separation_floor_per_mille": ESTIMATOR_SEPARATION_FLOOR_PER_MILLE,
        "policy_separation_floor_per_mille": POLICY_SEPARATION_FLOOR_PER_MILLE,
        "policy_win_floor": POLICY_WIN_FLOOR,
        "primary_metric": "final hidden exact quality per mille",
    }

    metrics = (
        "coverage_expansions",
        "coverage_best_hidden_per_mille",
        "final_development_per_mille",
        "final_hidden_per_mille",
        "best_hidden_per_mille",
        "immediate_exact_cmp_concordance_per_mille",
        "clade_exact_cmp_concordance_per_mille",
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

    hgm_rows = {
        int(row["seed"]): row
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "hgm_clade"
    }
    dgm_rows = {
        int(row["seed"]): row
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "dgm_immediate"
    }
    policy_differences = [
        int(hgm_rows[seed]["final_hidden_per_mille"])
        - int(dgm_rows[seed]["final_hidden_per_mille"])
        for seed in sorted(reference)
    ]
    summary["mismatch_hgm_minus_dgm_median_per_mille"] = _integer_median(
        policy_differences
    )
    summary["mismatch_hgm_wins"] = sum(value > 0 for value in policy_differences)
    summary["mismatch_hgm_ties"] = sum(value == 0 for value in policy_differences)
    summary["mismatch_hgm_losses"] = sum(value < 0 for value in policy_differences)

    hgm_immediate_alignment = int(
        summary[
            "mismatch_hgm_clade_immediate_exact_cmp_concordance_per_mille_median"
        ]
    )
    hgm_clade_alignment = int(
        summary["mismatch_hgm_clade_clade_exact_cmp_concordance_per_mille_median"]
    )
    summary["mismatch_clade_minus_immediate_alignment_per_mille"] = (
        hgm_clade_alignment - hgm_immediate_alignment
    )

    enough = len(reference) >= DEVELOPMENT_MIN_SEEDS
    estimator_supported = (
        enough
        and hgm_clade_alignment >= ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE
        and int(summary["mismatch_clade_minus_immediate_alignment_per_mille"])
        >= ESTIMATOR_SEPARATION_FLOOR_PER_MILLE
    )
    policy_supported = (
        enough
        and int(summary["mismatch_hgm_minus_dgm_median_per_mille"])
        >= POLICY_SEPARATION_FLOOR_PER_MILLE
        and int(summary["mismatch_hgm_wins"]) >= POLICY_WIN_FLOOR
    )
    aligned_exact = all(
        int(row["final_development_per_mille"])
        == int(row["final_hidden_per_mille"])
        for row in runs
        if row["rig"] == "aligned"
    )
    summary["enough_seeds_for_comparison"] = enough
    summary["estimator_alignment_supported"] = estimator_supported
    summary["hgm_policy_advantage_supported"] = policy_supported
    summary["aligned_control_exact"] = aligned_exact
    summary["seeded_clade_guidance_supported"] = (
        estimator_supported
        and policy_supported
        and aligned_exact
        and bool(summary["coverage_exact"])
        and bool(summary["mismatch_coverage_exposes_hidden_signal"])
        and not bool(summary["hidden_fields_visible_to_selectors"])
    )

    if not enough:
        status = "insufficient_paired_seeds"
    elif not bool(summary["coverage_exact"]):
        status = "coverage_control_failed"
    elif not aligned_exact:
        status = "aligned_control_failed"
    elif bool(summary["seeded_clade_guidance_supported"]):
        status = "seeded_clade_guidance_supported"
    elif estimator_supported:
        status = "estimator_alignment_without_policy_advantage"
    else:
        status = "seeded_clade_prediction_not_supported"
    summary["comparison_status"] = status
    return summary
