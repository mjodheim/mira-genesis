"""M029 — hidden-disjoint compositional probes for evaluation routing.

M028 showed that adaptive weighting cannot repair a clade estimate when the routing
signal is the same immediate-performance proxy that created the mismatch. M029 keeps
the complete M028 schedule and policies but supplies a separate public evaluation
suite that tests whether generic motifs transfer as reusable components.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import random
from statistics import median
from typing import Iterable, Sequence

from .m017_language import Library, description_length
from .m026_metaproductivity import (
    Case,
    MetaproductivityRig,
    State,
    _Archive,
    _NodeRecord,
    _per_mille,
    exact_clade_hidden_successes,
    build_aligned_rig,
    build_mismatch_rig,
)
from .m027_seeded_clade import coverage_is_exact, run_layered_coverage
from .m028_adaptive_evaluation import (
    DEFAULT_POLICY_BUDGET,
    INITIAL_EVALUATIONS_PER_NODE,
    POST_EXPANSION_EVALUATIONS,
    WARMUP_EVALUATIONS_PER_COVERED_NODE,
    EvaluatedPublicArchive,
    EvaluatedPublicNode,
    _allocate_evaluations,
    _clade_calibration,
    _high_potential_observed_node,
    _record_evaluation,
    run_trial as run_m028_trial,
    select_adaptive_evaluation,
    select_uniform_evaluation,
    select_weighted_clade_parent,
)


DEVELOPMENT_MIN_SEEDS = 64
ALLOCATION_SEPARATION_FLOOR_PER_MILLE = 167
ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE = 0
ESTIMATOR_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_WIN_FLOOR = 40
PROTOCOL_VERSION = "M029-development-v1"
STRATEGIES = (
    "development_adaptive",
    "component_uniform",
    "component_adaptive",
)


@dataclass(frozen=True)
class ComponentProbeTask:
    name: str
    case: Case
    max_symbols: int


@lru_cache(maxsize=None)
def component_probe_tasks(rig: MetaproductivityRig) -> tuple[ComponentProbeTask, ...]:
    generic_actions = tuple(
        action for action in rig.actions if action.name.startswith("generic_")
    )
    if not generic_actions:
        raise ValueError("component probes require generic rewrite actions")
    tasks: list[ComponentProbeTask] = []
    for action in generic_actions:
        tasks.append(
            ComponentProbeTask(
                name=f"{action.name}_single",
                case=action.atoms,
                max_symbols=1,
            )
        )
        tasks.append(
            ComponentProbeTask(
                name=f"{action.name}_repeat",
                case=action.atoms + action.atoms,
                max_symbols=2,
            )
        )
    return tuple(tasks)


@lru_cache(maxsize=None)
def component_probe_outcomes(
    rig: MetaproductivityRig,
    state: State,
) -> tuple[int, ...]:
    library = Library.primitive()
    for atoms in rig.fixed_macros:
        library.add(atoms, episode=-1)
    for action_name in state:
        library.add(rig.action(action_name).atoms, episode=-1)
    return tuple(
        int(description_length(task.case, library) <= task.max_symbols)
        for task in component_probe_tasks(rig)
    )


def component_probe_is_disjoint(rig: MetaproductivityRig) -> bool:
    sealed = set(rig.development_cases) | set(rig.hidden_cases)
    tasks = component_probe_tasks(rig)
    return (
        len({task.case for task in tasks}) == len(tasks)
        and all(task.case not in sealed for task in tasks)
    )


class _ComponentProbeLedger:
    """Track unique component-probe observations behind the M028 public boundary."""

    def __init__(self, rig: MetaproductivityRig, seed: int) -> None:
        self.rig = rig
        self.seed = seed
        self.tasks = component_probe_tasks(rig)
        self._orders: dict[int, tuple[int, ...]] = {}
        self._cursors: dict[int, int] = {}
        self._successes: dict[int, int] = {}
        self._failures: dict[int, int] = {}

    def _task_order(self, record: _NodeRecord) -> tuple[int, ...]:
        def key(task_index: int) -> str:
            payload = (
                f"m029|{self.seed}|{'/'.join(record.state)}|"
                f"{self.tasks[task_index].name}"
            )
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return tuple(sorted(range(len(self.tasks)), key=key))

    def register(self, record: _NodeRecord) -> None:
        if record.node_id in self._orders:
            raise ValueError("node is already registered for evaluation")
        self._orders[record.node_id] = self._task_order(record)
        self._cursors[record.node_id] = 0
        self._successes[record.node_id] = 0
        self._failures[record.node_id] = 0

    def evaluate(self, record: _NodeRecord) -> tuple[int, int]:
        if record.node_id not in self._orders:
            raise ValueError("node is not registered for evaluation")
        cursor = self._cursors[record.node_id]
        order = self._orders[record.node_id]
        if cursor >= len(order):
            raise ValueError("node has no unevaluated component task")
        task_index = order[cursor]
        outcome = component_probe_outcomes(self.rig, record.state)[task_index]
        self._cursors[record.node_id] = cursor + 1
        if outcome:
            self._successes[record.node_id] += 1
        else:
            self._failures[record.node_id] += 1
        return task_index, outcome

    def public(
        self,
        archive: _Archive,
        *,
        step: int,
        budget: int,
    ) -> EvaluatedPublicArchive:
        nodes: list[EvaluatedPublicNode] = []
        for record in archive.records:
            if record.node_id not in self._orders:
                raise ValueError("every archive node must be registered")
            nodes.append(
                EvaluatedPublicNode(
                    node_id=record.node_id,
                    parent_id=record.parent_id,
                    depth=len(record.state),
                    evaluation_successes=self._successes[record.node_id],
                    evaluation_failures=self._failures[record.node_id],
                    remaining_tasks=len(self.tasks) - self._cursors[record.node_id],
                    children=tuple(record.children),
                    can_expand=(
                        len(record.state) < self.rig.max_depth
                        and archive._next_unique_action(record, consume=False) is not None
                    ),
                )
            )
        return EvaluatedPublicArchive(tuple(nodes), step=step, budget=budget)

    def total_evaluations(self) -> int:
        return sum(self._successes.values()) + sum(self._failures.values())

    def all_tasks_unique(self) -> bool:
        return all(
            0 <= cursor <= len(self._orders[node_id])
            for node_id, cursor in self._cursors.items()
        )


def verify_component_controls(seed: int = 0) -> dict[str, bool]:
    mismatch = build_mismatch_rig(seed)
    aligned = build_aligned_rig(seed)
    generic_state = tuple(sorted(("platform", "generic_0")))
    shortcut_state = ("shortcut_0",)
    return {
        "mismatch_probe_disjoint": component_probe_is_disjoint(mismatch),
        "aligned_probe_disjoint": component_probe_is_disjoint(aligned),
        "generic_beats_shortcut_on_probe": (
            sum(component_probe_outcomes(mismatch, generic_state))
            > sum(component_probe_outcomes(mismatch, shortcut_state))
        ),
        "generic_retains_higher_exact_cmp": (
            exact_clade_hidden_successes(mismatch, generic_state)
            > exact_clade_hidden_successes(mismatch, shortcut_state)
        ),
        "shortcut_passes_no_component_probe": (
            sum(component_probe_outcomes(mismatch, shortcut_state)) == 0
        ),
    }


def _rig(rig_name: str, seed: int) -> MetaproductivityRig:
    if rig_name == "mismatch":
        return build_mismatch_rig(seed)
    if rig_name == "aligned":
        return build_aligned_rig(seed)
    raise ValueError("unknown M029 rig")


def _augment_development_baseline(
    rig_name: str,
    seed: int,
    policy_budget: int,
) -> dict[str, object]:
    row = dict(
        run_m028_trial(
            rig_name,
            "adaptive_evaluation",
            seed,
            policy_budget=policy_budget,
        )
    )
    rig = _rig(rig_name, seed)
    final_state = tuple(str(name) for name in row["final_state"])
    controls = verify_component_controls(seed)
    row.update(
        {
            "strategy": "development_adaptive",
            "evaluation_signal": "development_performance",
            "evaluation_task_count": rig.development_total,
            "final_component_probe_per_mille": _per_mille(
                sum(component_probe_outcomes(rig, final_state)),
                len(component_probe_tasks(rig)),
            ),
            "component_probe_controls_pass": all(controls.values()),
            "component_probe_hidden_disjoint": component_probe_is_disjoint(rig),
        }
    )
    return row


def _run_component_trial(
    rig_name: str,
    strategy: str,
    seed: int,
    policy_budget: int,
) -> dict[str, object]:
    rig = _rig(rig_name, seed)
    archive = _Archive(rig, seed, policy_budget)
    coverage_trace = run_layered_coverage(archive)
    exact_coverage = coverage_is_exact(archive)
    covered_nodes = len(archive.records)
    ledger = _ComponentProbeLedger(rig, seed)
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

    evaluation_selector = (
        select_uniform_evaluation
        if strategy == "component_uniform"
        else select_adaptive_evaluation
    )
    evaluation_rng = random.Random(seed * 104_729 + 28_001)
    expansion_rng = random.Random(seed * 104_729 + 28_002)
    warmup_budget = WARMUP_EVALUATIONS_PER_COVERED_NODE * covered_nodes
    warmup_trace = _allocate_evaluations(
        archive,
        ledger,
        evaluation_selector,
        evaluation_rng,
        count=warmup_budget,
        phase="warmup",
        budget=warmup_budget + policy_budget * POST_EXPANSION_EVALUATIONS,
        start_step=len(evaluation_trace),
    )
    evaluation_trace.extend(warmup_trace)

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
    allocated_rows = [
        row for row in evaluation_trace if row["phase"] != "initial"
    ]
    high_potential_allocations = sum(
        _high_potential_observed_node(archive, int(row["node_id"]))
        for row in allocated_rows
    )
    controls = verify_component_controls(seed)

    return {
        "rig": rig.name,
        "strategy": strategy,
        "evaluation_signal": "component_transfer",
        "seed": seed,
        "coverage_expansions": len(coverage_trace),
        "coverage_exact": exact_coverage,
        "covered_nodes": covered_nodes,
        "policy_budget": policy_budget,
        "policy_expansions": len(policy_trace),
        "archive_nodes": len(archive.records),
        "evaluation_task_count": len(component_probe_tasks(rig)),
        "initial_evaluations": covered_nodes * INITIAL_EVALUATIONS_PER_NODE,
        "warmup_evaluations": len(warmup_trace),
        "post_coverage_evaluations": len(evaluation_trace) - covered_nodes,
        "total_evaluations": ledger.total_evaluations(),
        "unique_task_evaluations": ledger.all_tasks_unique(),
        "component_probe_controls_pass": all(controls.values()),
        "component_probe_hidden_disjoint": component_probe_is_disjoint(rig),
        "high_potential_observed_allocation_share_per_mille": _per_mille(
            high_potential_allocations,
            len(allocated_rows),
        ),
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
        "final_component_probe_per_mille": _per_mille(
            sum(component_probe_outcomes(rig, final.state)),
            len(component_probe_tasks(rig)),
        ),
        "best_hidden_per_mille": _per_mille(
            best_hidden.hidden_successes,
            rig.hidden_total,
        ),
        "weighted_clade_exact_cmp_concordance_per_mille": _clade_calibration(
            archive,
            public,
        ),
        "integer_only_selection_trace": True,
        "hidden_fields_visible_to_selector": False,
        "coverage_trace": coverage_trace,
        "evaluation_trace": evaluation_trace,
        "policy_trace": policy_trace,
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
        raise ValueError("unknown M029 strategy")
    if strategy == "development_adaptive":
        return _augment_development_baseline(rig_name, seed, policy_budget)
    return _run_component_trial(rig_name, strategy, seed, policy_budget)


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
        raise ValueError("M029 runs are not paired across rigs and strategies")
    expected_rows = len(reference) * len(expected_rigs) * len(expected_strategies)
    if len(runs) != expected_rows:
        raise ValueError("M029 runs contain missing or duplicate rows")

    summary: dict[str, object] = {
        "development_only": True,
        "paired_seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "development_min_seeds": DEVELOPMENT_MIN_SEEDS,
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
        "allocation_separation_floor_per_mille": ALLOCATION_SEPARATION_FLOOR_PER_MILLE,
        "estimator_alignment_floor_per_mille": ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE,
        "estimator_separation_floor_per_mille": ESTIMATOR_SEPARATION_FLOOR_PER_MILLE,
        "policy_separation_floor_per_mille": POLICY_SEPARATION_FLOOR_PER_MILLE,
        "policy_win_floor": POLICY_WIN_FLOOR,
        "primary_metric": "final hidden exact quality per mille",
    }

    metrics = (
        "coverage_expansions",
        "total_evaluations",
        "high_potential_observed_allocation_share_per_mille",
        "final_development_per_mille",
        "final_hidden_per_mille",
        "final_component_probe_per_mille",
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

    by_strategy = {
        strategy: {
            int(row["seed"]): row
            for row in runs
            if row["rig"] == "mismatch" and row["strategy"] == strategy
        }
        for strategy in STRATEGIES
    }
    component = by_strategy["component_adaptive"]
    development = by_strategy["development_adaptive"]
    uniform = by_strategy["component_uniform"]
    primary_differences = [
        int(component[seed]["final_hidden_per_mille"])
        - int(development[seed]["final_hidden_per_mille"])
        for seed in sorted(reference)
    ]
    uniform_differences = [
        int(component[seed]["final_hidden_per_mille"])
        - int(uniform[seed]["final_hidden_per_mille"])
        for seed in sorted(reference)
    ]
    summary["mismatch_component_minus_development_median_per_mille"] = (
        _integer_median(primary_differences)
    )
    summary["mismatch_component_wins"] = sum(
        value > 0 for value in primary_differences
    )
    summary["mismatch_component_ties"] = sum(
        value == 0 for value in primary_differences
    )
    summary["mismatch_component_losses"] = sum(
        value < 0 for value in primary_differences
    )
    summary["mismatch_component_adaptive_minus_uniform_median_per_mille"] = (
        _integer_median(uniform_differences)
    )

    component_alignment = int(
        summary[
            "mismatch_component_adaptive_weighted_clade_exact_cmp_concordance_per_mille_median"
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
    component_allocation = int(
        summary[
            "mismatch_component_adaptive_high_potential_observed_allocation_share_per_mille_median"
        ]
    )
    development_allocation = int(
        summary[
            "mismatch_development_adaptive_high_potential_observed_allocation_share_per_mille_median"
        ]
    )
    summary["mismatch_component_minus_development_high_potential_allocation_per_mille"] = (
        component_allocation - development_allocation
    )

    enough = len(reference) >= DEVELOPMENT_MIN_SEEDS
    allocation_supported = (
        enough
        and int(
            summary[
                "mismatch_component_minus_development_high_potential_allocation_per_mille"
            ]
        )
        >= ALLOCATION_SEPARATION_FLOOR_PER_MILLE
    )
    estimator_supported = (
        enough
        and component_alignment >= ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE
        and int(summary["mismatch_component_minus_development_alignment_per_mille"])
        >= ESTIMATOR_SEPARATION_FLOOR_PER_MILLE
    )
    policy_supported = (
        enough
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
    summary["enough_seeds_for_comparison"] = enough
    summary["component_allocation_shift_supported"] = allocation_supported
    summary["component_estimator_alignment_supported"] = estimator_supported
    summary["component_policy_advantage_supported"] = policy_supported
    summary["aligned_control_exact"] = aligned_exact
    summary["component_signal_supported"] = (
        allocation_supported
        and estimator_supported
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
    elif not bool(summary["component_probe_controls_pass"]):
        status = "component_probe_control_failed"
    elif not bool(summary["coverage_exact"]):
        status = "coverage_control_failed"
    elif not aligned_exact:
        status = "aligned_control_failed"
    elif bool(summary["component_signal_supported"]):
        status = "component_signal_supported"
    elif estimator_supported:
        status = "component_estimator_without_policy_advantage"
    else:
        status = "component_signal_prediction_not_supported"
    summary["comparison_status"] = status
    return summary
