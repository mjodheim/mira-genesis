"""M031 — transport component guidance to a distinct compositional generator.

M029 and M030 used pairs of length-two components behind one platform action. M031
keeps their public evaluation and parent-selection rules but replaces that generator
with length-three components, cyclic/permuted triads and two independent scaffolds.
"""

from __future__ import annotations

from functools import lru_cache
from statistics import median
import random
from typing import Iterable, Sequence

from .m026_metaproductivity import (
    MetaproductivityRig,
    RewriteAction,
    _Archive,
    _per_mille,
    _reachable_states,
    exact_clade_hidden_successes,
    score_state,
)
from .m027_seeded_clade import coverage_is_exact, run_layered_coverage
from .m028_adaptive_evaluation import (
    DEFAULT_POLICY_BUDGET,
    INITIAL_EVALUATIONS_PER_NODE,
    POST_EXPANSION_EVALUATIONS,
    WARMUP_EVALUATIONS_PER_COVERED_NODE,
    _EvaluationLedger,
    _allocate_evaluations,
    _clade_calibration,
    _record_evaluation,
    select_adaptive_evaluation,
    select_uniform_evaluation,
    select_weighted_clade_parent,
)
from .m029_component_probe import (
    _ComponentProbeLedger,
    component_probe_is_disjoint,
    component_probe_outcomes,
    component_probe_tasks,
)
from .structural import Atom, all_atoms


DEVELOPMENT_SEED_START = 0
DEVELOPMENT_SEED_COUNT = 64
DEVELOPMENT_SEEDS = frozenset(
    range(DEVELOPMENT_SEED_START, DEVELOPMENT_SEED_START + DEVELOPMENT_SEED_COUNT)
)
SMOKE_SEED_START = 64
ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE = 0
ESTIMATOR_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_WIN_FLOOR = 40
PROTOCOL_VERSION = "M031-development-v1"
TASK_GENERATOR = "split-scaffold-cyclic-triads-v1"
STRATEGIES = ("development_adaptive", "component_uniform")


def _shuffled_atoms(seed: int, salt: int) -> list[Atom]:
    atoms = list(all_atoms())
    random.Random(seed * 65_537 + salt).shuffle(atoms)
    return atoms


def _triads(
    generic: tuple[tuple[Atom, ...], ...],
    *,
    hidden: bool,
) -> tuple[tuple[Atom, ...], ...]:
    cases: list[tuple[Atom, ...]] = []
    for index in range(4):
        for third_offset in (2, 3):
            order = (
                (index, (index + third_offset) % 4, (index + 1) % 4)
                if hidden
                else (index, (index + 1) % 4, (index + third_offset) % 4)
            )
            cases.append(tuple(atom for part in order for atom in generic[part]))
    return tuple(cases)


def build_transport_mismatch_rig(seed: int) -> MetaproductivityRig:
    """Build the split-scaffold cyclic-triad performance/potential reversal."""

    atoms = _shuffled_atoms(seed, 31_001)
    generic = tuple(tuple(atoms[index : index + 3]) for index in range(0, 12, 3))
    development = _triads(generic, hidden=False)
    hidden = _triads(generic, hidden=True)
    actions: list[RewriteAction] = [
        RewriteAction("scaffold_left", tuple(atoms[12:14])),
        RewriteAction("scaffold_right", tuple(atoms[14:16])),
    ]
    actions.extend(
        RewriteAction(
            f"generic_{index}",
            motif,
            "scaffold_left" if index < 2 else "scaffold_right",
        )
        for index, motif in enumerate(generic)
    )
    actions.extend(
        RewriteAction(f"shortcut_{index}", case)
        for index, case in enumerate(development)
    )
    return MetaproductivityRig(
        name="mismatch",
        development_cases=development,
        hidden_cases=hidden,
        fixed_macros=(),
        actions=tuple(actions),
        max_symbols=5,
        max_depth=5,
    )


def build_transport_aligned_rig(seed: int) -> MetaproductivityRig:
    """Build a distinct-task control with identical visible and hidden quality."""

    atoms = _shuffled_atoms(seed, 31_002)
    generic = tuple(tuple(atoms[index : index + 3]) for index in range(0, 12, 3))
    development_context = tuple(atoms[12:14])
    hidden_context = tuple(atoms[14:16])
    triads = _triads(generic, hidden=False)
    development = tuple(development_context + case for case in triads)
    hidden = tuple(hidden_context + case for case in triads)
    actions = (
        RewriteAction("scaffold_left", tuple(atoms[16:18])),
        RewriteAction("scaffold_right", tuple(atoms[18:20])),
    ) + tuple(
        RewriteAction(
            f"generic_{index}",
            motif,
            "scaffold_left" if index < 2 else "scaffold_right",
        )
        for index, motif in enumerate(generic)
    ) + tuple(
        RewriteAction(f"decoy_{index}", tuple(atoms[20 + 2 * index : 22 + 2 * index]))
        for index in range(8)
    )
    return MetaproductivityRig(
        name="aligned",
        development_cases=development,
        hidden_cases=hidden,
        fixed_macros=(development_context, hidden_context),
        actions=actions,
        max_symbols=6,
        max_depth=5,
    )


def _rig(rig_name: str, seed: int) -> MetaproductivityRig:
    if rig_name == "mismatch":
        return build_transport_mismatch_rig(seed)
    if rig_name == "aligned":
        return build_transport_aligned_rig(seed)
    raise ValueError("unknown M031 rig")


def _generic_state(rig: MetaproductivityRig) -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                "scaffold_left",
                "scaffold_right",
                "generic_0",
                "generic_1",
                "generic_2",
            )
        )
    )


@lru_cache(maxsize=None)
def verify_transport_controls(seed: int = SMOKE_SEED_START) -> dict[str, bool]:
    mismatch = build_transport_mismatch_rig(seed)
    aligned = build_transport_aligned_rig(seed)
    generic_state = _generic_state(mismatch)
    partial_generic = tuple(sorted(("scaffold_left", "generic_0")))
    shortcut_state = ("shortcut_0",)
    generic_actions = tuple(
        action for action in mismatch.actions if action.name.startswith("generic_")
    )
    prerequisites = {action.prerequisite for action in generic_actions}
    aligned_exact = all(
        score_state(aligned, state, "development")
        == score_state(aligned, state, "hidden")
        for state in _reachable_states(aligned)
    )
    return {
        "length_three_components": {len(action.atoms) for action in generic_actions} == {3},
        "eight_triad_tasks": (
            len(mismatch.development_cases) == 8
            and len(mismatch.hidden_cases) == 8
            and {len(case) for case in mismatch.development_cases} == {9}
        ),
        "cyclic_and_permuted_suites_are_disjoint": set(mismatch.development_cases).isdisjoint(mismatch.hidden_cases),
        "hidden_suite_is_not_pair_reversal": all(
            hidden != tuple(reversed(development))
            for development, hidden in zip(
                mismatch.development_cases, mismatch.hidden_cases, strict=True
            )
        ),
        "split_scaffold_topology": prerequisites == {"scaffold_left", "scaffold_right"},
        "mismatch_probe_disjoint": component_probe_is_disjoint(mismatch),
        "aligned_probe_disjoint": component_probe_is_disjoint(aligned),
        "partial_generic_beats_shortcut_on_probe": (
            sum(component_probe_outcomes(mismatch, partial_generic))
            > sum(component_probe_outcomes(mismatch, shortcut_state))
        ),
        "shortcut_passes_no_component_probe": sum(component_probe_outcomes(mismatch, shortcut_state)) == 0,
        "partial_generic_retains_higher_exact_cmp": (
            exact_clade_hidden_successes(mismatch, partial_generic)
            > exact_clade_hidden_successes(mismatch, shortcut_state)
        ),
        "complete_generic_state_solves_both_suites": (
            score_state(mismatch, generic_state, "development") == mismatch.development_total
            and score_state(mismatch, generic_state, "hidden") == mismatch.hidden_total
        ),
        "shortcut_lineage_cannot_reach_full_hidden": (
            exact_clade_hidden_successes(mismatch, shortcut_state) < mismatch.hidden_total
        ),
        "aligned_quality_is_exact": aligned_exact,
    }


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
        raise ValueError("unknown M031 strategy")

    rig = _rig(rig_name, seed)
    archive = _Archive(rig, seed, policy_budget)
    coverage_trace = run_layered_coverage(archive)
    exact_coverage = coverage_is_exact(archive)
    covered_nodes = len(archive.records)
    if strategy == "development_adaptive":
        ledger = _EvaluationLedger(rig, seed)
        evaluation_selector = select_adaptive_evaluation
        evaluation_signal = "development_performance"
    else:
        ledger = _ComponentProbeLedger(rig, seed)
        evaluation_selector = select_uniform_evaluation
        evaluation_signal = "component_transfer"

    evaluation_trace: list[dict[str, object]] = []
    for record in archive.records:
        ledger.register(record)
        for _ in range(INITIAL_EVALUATIONS_PER_NODE):
            evaluation_trace.append(
                _record_evaluation(
                    ledger,
                    archive,
                    record.node_id,
                    phase="initial",
                    step=len(evaluation_trace),
                )
            )

    evaluation_rng = random.Random(seed * 104_729 + 31_001)
    expansion_rng = random.Random(seed * 104_729 + 31_002)
    warmup_budget = WARMUP_EVALUATIONS_PER_COVERED_NODE * covered_nodes
    evaluation_trace.extend(
        _allocate_evaluations(
            archive,
            ledger,
            evaluation_selector,
            evaluation_rng,
            count=warmup_budget,
            phase="warmup",
            budget=warmup_budget + policy_budget * POST_EXPANSION_EVALUATIONS,
            start_step=len(evaluation_trace),
        )
    )

    policy_trace: list[dict[str, object]] = []
    for policy_step in range(policy_budget):
        public = ledger.public(archive, step=policy_step, budget=policy_budget)
        parent_id = select_weighted_clade_parent(public, expansion_rng)
        child, action_name = archive.expand(parent_id)
        ledger.register(child)
        child_initial = _record_evaluation(
            ledger,
            archive,
            child.node_id,
            phase="new_node",
            step=len(evaluation_trace),
        )
        evaluation_trace.append(child_initial)
        allocated = _allocate_evaluations(
            archive,
            ledger,
            evaluation_selector,
            evaluation_rng,
            count=POST_EXPANSION_EVALUATIONS,
            phase="post_expansion",
            budget=policy_budget * POST_EXPANSION_EVALUATIONS,
            start_step=len(evaluation_trace),
        )
        evaluation_trace.extend(allocated)
        policy_trace.append(
            {
                "step": policy_step,
                "parent_id": parent_id,
                "child_id": child.node_id,
                "action": action_name,
                "child_initial_task_index": child_initial["task_index"],
                "child_initial_success": child_initial["success"],
                "allocated_node_ids": [row["node_id"] for row in allocated],
            }
        )

    public = ledger.public(archive, step=policy_budget, budget=policy_budget)
    final = min(
        archive.records,
        key=lambda record: (-record.development_successes, record.node_id),
    )
    best_hidden = max(
        archive.records,
        key=lambda record: (record.hidden_successes, -record.node_id),
    )
    controls = verify_transport_controls(seed)
    return {
        "rig": rig.name,
        "strategy": strategy,
        "task_generator": TASK_GENERATOR,
        "evaluation_signal": evaluation_signal,
        "seed": seed,
        "development_seed": seed in DEVELOPMENT_SEEDS,
        "coverage_expansions": len(coverage_trace),
        "coverage_exact": exact_coverage,
        "covered_nodes": covered_nodes,
        "policy_budget": policy_budget,
        "policy_expansions": len(policy_trace),
        "archive_nodes": len(archive.records),
        "evaluation_task_count": (
            rig.development_total
            if strategy == "development_adaptive"
            else len(component_probe_tasks(rig))
        ),
        "initial_evaluations": covered_nodes * INITIAL_EVALUATIONS_PER_NODE,
        "warmup_evaluations": warmup_budget,
        "post_coverage_evaluations": len(evaluation_trace) - covered_nodes,
        "total_evaluations": ledger.total_evaluations(),
        "unique_task_evaluations": ledger.all_tasks_unique(),
        "transport_controls_pass": all(controls.values()),
        "transport_controls": controls,
        "component_probe_hidden_disjoint": component_probe_is_disjoint(rig),
        "final_node_id": final.node_id,
        "final_state": list(final.state),
        "final_development_per_mille": _per_mille(final.development_successes, rig.development_total),
        "final_hidden_per_mille": _per_mille(final.hidden_successes, rig.hidden_total),
        "final_component_probe_per_mille": _per_mille(
            sum(component_probe_outcomes(rig, final.state)),
            len(component_probe_tasks(rig)),
        ),
        "best_hidden_per_mille": _per_mille(best_hidden.hidden_successes, rig.hidden_total),
        "weighted_clade_exact_cmp_concordance_per_mille": _clade_calibration(archive, public),
        "integer_only_selection_trace": True,
        "hidden_fields_visible_to_selector": False,
        "coverage_trace": coverage_trace,
        "evaluation_trace": evaluation_trace,
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
    reference = seed_sets[("mismatch", "development_adaptive")]
    if any(seeds != reference for seeds in seed_sets.values()):
        raise ValueError("M031 runs are not paired across rigs and strategies")
    if len(runs) != len(reference) * len(expected_rigs) * len(expected_strategies):
        raise ValueError("M031 runs contain missing or duplicate rows")

    exact_development_range = reference == DEVELOPMENT_SEEDS
    summary: dict[str, object] = {
        "development_only": True,
        "paired_seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "development_seed_start": DEVELOPMENT_SEED_START,
        "development_seed_count": DEVELOPMENT_SEED_COUNT,
        "exact_development_seed_range": exact_development_range,
        "task_generator": TASK_GENERATOR,
        "structurally_distinct_generator": True,
        "common_layered_coverage": True,
        "common_evaluation_schedule": True,
        "common_parent_policy": True,
        "common_final_selector": True,
        "transport_controls_pass": all(bool(row["transport_controls_pass"]) for row in runs),
        "component_probe_hidden_disjoint": all(bool(row["component_probe_hidden_disjoint"]) for row in runs),
        "unique_task_evaluations": all(bool(row["unique_task_evaluations"]) for row in runs),
        "integer_only_selection_traces": all(bool(row["integer_only_selection_trace"]) for row in runs),
        "hidden_fields_visible_to_selectors": any(bool(row["hidden_fields_visible_to_selector"]) for row in runs),
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
        "final_component_probe_per_mille",
        "best_hidden_per_mille",
        "weighted_clade_exact_cmp_concordance_per_mille",
    )
    for rig in sorted(expected_rigs):
        for strategy in STRATEGIES:
            selected = [
                row for row in runs
                if row["rig"] == rig and row["strategy"] == strategy
            ]
            prefix = f"{rig}_{strategy}"
            for metric in metrics:
                summary[f"{prefix}_{metric}_median"] = _integer_median(
                    int(row[metric]) for row in selected
                )

    component = {
        int(row["seed"]): row for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "component_uniform"
    }
    development = {
        int(row["seed"]): row for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "development_adaptive"
    }
    differences = [
        int(component[seed]["final_hidden_per_mille"])
        - int(development[seed]["final_hidden_per_mille"])
        for seed in sorted(reference)
    ]
    summary["mismatch_component_minus_development_median_per_mille"] = _integer_median(differences)
    summary["mismatch_component_wins"] = sum(value > 0 for value in differences)
    summary["mismatch_component_ties"] = sum(value == 0 for value in differences)
    summary["mismatch_component_losses"] = sum(value < 0 for value in differences)
    component_alignment = int(summary["mismatch_component_uniform_weighted_clade_exact_cmp_concordance_per_mille_median"])
    development_alignment = int(summary["mismatch_development_adaptive_weighted_clade_exact_cmp_concordance_per_mille_median"])
    summary["mismatch_component_minus_development_alignment_per_mille"] = component_alignment - development_alignment

    enough = len(reference) >= DEVELOPMENT_SEED_COUNT
    estimator_supported = (
        enough
        and exact_development_range
        and component_alignment >= ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE
        and int(summary["mismatch_component_minus_development_alignment_per_mille"])
        >= ESTIMATOR_SEPARATION_FLOOR_PER_MILLE
    )
    policy_supported = (
        enough
        and exact_development_range
        and int(summary["mismatch_component_minus_development_median_per_mille"])
        >= POLICY_SEPARATION_FLOOR_PER_MILLE
        and int(summary["mismatch_component_wins"]) >= POLICY_WIN_FLOOR
    )
    aligned_exact = all(
        int(row["final_development_per_mille"]) == int(row["final_hidden_per_mille"])
        for row in runs if row["rig"] == "aligned"
    )
    summary["enough_seeds_for_transport"] = enough
    summary["component_estimator_transport_supported"] = estimator_supported
    summary["component_policy_transport_supported"] = policy_supported
    summary["aligned_control_exact"] = aligned_exact
    summary["uniform_component_signal_transported"] = (
        estimator_supported
        and policy_supported
        and aligned_exact
        and bool(summary["coverage_exact"])
        and bool(summary["transport_controls_pass"])
        and bool(summary["component_probe_hidden_disjoint"])
        and bool(summary["unique_task_evaluations"])
        and not bool(summary["hidden_fields_visible_to_selectors"])
    )
    if not enough:
        status = "insufficient_paired_seeds"
    elif not exact_development_range:
        status = "development_seed_range_mismatch"
    elif not bool(summary["transport_controls_pass"]):
        status = "transport_control_failed"
    elif not bool(summary["coverage_exact"]):
        status = "coverage_control_failed"
    elif not aligned_exact:
        status = "aligned_control_failed"
    elif bool(summary["uniform_component_signal_transported"]):
        status = "uniform_component_signal_transported"
    elif estimator_supported:
        status = "component_estimator_without_transport_policy_advantage"
    else:
        status = "uniform_component_transport_not_supported"
    summary["comparison_status"] = status
    return summary
