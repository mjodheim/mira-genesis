"""M028 — adaptive evaluation weighting over a breadth-seeded rewrite archive.

M027 exposed productive descendants but estimated clade quality by giving every
fully evaluated node equal weight. M028 isolates the mechanism omitted by that
construction: an HGM-inspired evaluation policy can allocate more observations to
some agents than to others. Expansion, task order, coverage and final selection stay
fixed across the two public policies.

This is a finite mechanism test, not a reproduction of HGM. In particular, the
depth-three coverage intervention makes HGM's original evaluation/expansion scheduler
inapplicable, so M028 uses a fixed common schedule and changes only the evaluation
target policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import random
from statistics import median
from typing import Callable, Iterable, Sequence

from .m017_language import Library, description_length
from .m026_metaproductivity import (
    MetaproductivityRig,
    State,
    _Archive,
    _NodeRecord,
    _integer_beta_order_statistic,
    _pairwise_concordance_per_mille,
    _per_mille,
    exact_clade_hidden_successes,
    build_aligned_rig,
    build_mismatch_rig,
)
from .m027_seeded_clade import coverage_is_exact, run_layered_coverage


DEFAULT_POLICY_BUDGET = 40
DEVELOPMENT_MIN_SEEDS = 64
INITIAL_EVALUATIONS_PER_NODE = 1
WARMUP_EVALUATIONS_PER_COVERED_NODE = 2
POST_EXPANSION_EVALUATIONS = 2
ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE = 0
ESTIMATOR_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_WIN_FLOOR = 40
PROTOCOL_VERSION = "M028-development-v1"
STRATEGIES = ("uniform_evaluation", "adaptive_evaluation")


@lru_cache(maxsize=None)
def development_outcomes(
    rig: MetaproductivityRig,
    state: State,
) -> tuple[int, ...]:
    """Return evaluator-computed outcomes for the public development cases."""

    library = Library.primitive()
    for atoms in rig.fixed_macros:
        library.add(atoms, episode=-1)
    for action_name in state:
        library.add(rig.action(action_name).atoms, episode=-1)
    return tuple(
        int(description_length(case, library) <= rig.max_symbols)
        for case in rig.development_cases
    )


@dataclass(frozen=True)
class EvaluatedPublicNode:
    """The complete information boundary visible to an M028 policy."""

    node_id: int
    parent_id: int | None
    depth: int
    evaluation_successes: int
    evaluation_failures: int
    remaining_tasks: int
    children: tuple[int, ...]
    can_expand: bool


@dataclass(frozen=True)
class EvaluatedPublicArchive:
    nodes: tuple[EvaluatedPublicNode, ...]
    step: int
    budget: int

    def evaluable(self) -> tuple[EvaluatedPublicNode, ...]:
        return tuple(node for node in self.nodes if node.remaining_tasks > 0)

    def eligible_parents(self) -> tuple[EvaluatedPublicNode, ...]:
        return tuple(node for node in self.nodes if node.can_expand)

    def clade(self, root_id: int) -> tuple[EvaluatedPublicNode, ...]:
        by_id = {node.node_id: node for node in self.nodes}
        found: list[EvaluatedPublicNode] = []
        pending = [root_id]
        while pending:
            node_id = pending.pop()
            node = by_id[node_id]
            found.append(node)
            pending.extend(reversed(node.children))
        return tuple(found)


class _EvaluationLedger:
    """Track unique development-task observations without exposing node state."""

    def __init__(self, rig: MetaproductivityRig, seed: int) -> None:
        self.rig = rig
        self.seed = seed
        self._orders: dict[int, tuple[int, ...]] = {}
        self._cursors: dict[int, int] = {}
        self._successes: dict[int, int] = {}
        self._failures: dict[int, int] = {}

    def _task_order(self, record: _NodeRecord) -> tuple[int, ...]:
        def key(task_index: int) -> str:
            payload = (
                f"m028|{self.seed}|{'/'.join(record.state)}|{task_index}"
            )
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return tuple(sorted(range(self.rig.development_total), key=key))

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
            raise ValueError("node has no unevaluated development task")
        task_index = order[cursor]
        outcome = development_outcomes(self.rig, record.state)[task_index]
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
                    remaining_tasks=(
                        self.rig.development_total - self._cursors[record.node_id]
                    ),
                    children=tuple(record.children),
                    can_expand=(
                        len(record.state) < self.rig.max_depth
                        and archive._next_unique_action(record, consume=False) is not None
                    ),
                )
            )
        return EvaluatedPublicArchive(tuple(nodes), step=step, budget=budget)

    def counts(self, node_id: int) -> tuple[int, int]:
        return self._successes[node_id], self._failures[node_id]

    def total_evaluations(self) -> int:
        return sum(self._successes.values()) + sum(self._failures.values())

    def all_tasks_unique(self) -> bool:
        return all(
            0 <= cursor <= len(self._orders[node_id])
            for node_id, cursor in self._cursors.items()
        )


def evaluated_clade_counts(
    archive: EvaluatedPublicArchive,
    root_id: int,
) -> tuple[int, int]:
    clade = archive.clade(root_id)
    return (
        sum(node.evaluation_successes for node in clade),
        sum(node.evaluation_failures for node in clade),
    )


def select_uniform_evaluation(
    archive: EvaluatedPublicArchive,
    rng: random.Random,
) -> int:
    candidates = archive.evaluable()
    if not candidates:
        raise ValueError("no node has an unevaluated task")
    return candidates[rng.randrange(len(candidates))].node_id


def select_adaptive_evaluation(
    archive: EvaluatedPublicArchive,
    rng: random.Random,
) -> int:
    """Select an agent by individual-performance Thompson sampling."""

    samples: list[tuple[int, int]] = []
    for node in archive.evaluable():
        sample = _integer_beta_order_statistic(
            1 + node.evaluation_successes,
            1 + node.evaluation_failures,
            rng,
        )
        samples.append((sample, -node.node_id))
    if not samples:
        raise ValueError("no node has an unevaluated task")
    _, negative_id = max(samples)
    return -negative_id


EvaluationSelector = Callable[[EvaluatedPublicArchive, random.Random], int]
EVALUATION_SELECTORS: dict[str, EvaluationSelector] = {
    "uniform_evaluation": select_uniform_evaluation,
    "adaptive_evaluation": select_adaptive_evaluation,
}


def select_weighted_clade_parent(
    archive: EvaluatedPublicArchive,
    rng: random.Random,
) -> int:
    """Apply one common clade Thompson policy to weighted observations."""

    samples: list[tuple[int, int]] = []
    for node in archive.eligible_parents():
        successes, failures = evaluated_clade_counts(archive, node.node_id)
        sample = _integer_beta_order_statistic(
            1 + successes,
            1 + failures,
            rng,
        )
        samples.append((sample, -node.node_id))
    if not samples:
        raise ValueError("no eligible parent")
    _, negative_id = max(samples)
    return -negative_id


def _record_evaluation(
    ledger: _EvaluationLedger,
    archive: _Archive,
    node_id: int,
    *,
    phase: str,
    step: int,
) -> dict[str, object]:
    task_index, outcome = ledger.evaluate(archive.records[node_id])
    return {
        "phase": phase,
        "step": step,
        "node_id": node_id,
        "task_index": task_index,
        "success": outcome,
    }


def _allocate_evaluations(
    archive: _Archive,
    ledger: _EvaluationLedger,
    selector: EvaluationSelector,
    rng: random.Random,
    *,
    count: int,
    phase: str,
    budget: int,
    start_step: int,
) -> list[dict[str, object]]:
    trace: list[dict[str, object]] = []
    for offset in range(count):
        public = ledger.public(
            archive,
            step=start_step + offset,
            budget=budget,
        )
        node_id = selector(public, rng)
        trace.append(
            _record_evaluation(
                ledger,
                archive,
                node_id,
                phase=phase,
                step=start_step + offset,
            )
        )
    return trace


def _clade_calibration(
    archive: _Archive,
    public: EvaluatedPublicArchive,
) -> int:
    estimates: list[int] = []
    targets: list[int] = []
    for node in public.nodes:
        successes, failures = evaluated_clade_counts(public, node.node_id)
        estimates.append(_per_mille(successes, successes + failures))
        targets.append(
            _per_mille(
                exact_clade_hidden_successes(
                    archive.rig,
                    archive.records[node.node_id].state,
                ),
                archive.rig.hidden_total,
            )
        )
    return _pairwise_concordance_per_mille(estimates, targets)


def _high_potential_observed_node(archive: _Archive, node_id: int) -> bool:
    record = archive.records[node_id]
    return (
        record.development_successes > 0
        and exact_clade_hidden_successes(archive.rig, record.state)
        == archive.rig.hidden_total
    )


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
        raise ValueError("unknown M028 strategy")
    if rig_name == "mismatch":
        rig = build_mismatch_rig(seed)
    elif rig_name == "aligned":
        rig = build_aligned_rig(seed)
    else:
        raise ValueError("unknown M028 rig")

    archive = _Archive(rig, seed, policy_budget)
    coverage_trace = run_layered_coverage(archive)
    exact_coverage = coverage_is_exact(archive)
    covered_nodes = len(archive.records)
    ledger = _EvaluationLedger(rig, seed)
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

    evaluation_selector = EVALUATION_SELECTORS[strategy]
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
        public = ledger.public(
            archive,
            step=policy_step,
            budget=policy_budget,
        )
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

    public = ledger.public(
        archive,
        step=policy_budget,
        budget=policy_budget,
    )
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

    return {
        "rig": rig.name,
        "strategy": strategy,
        "seed": seed,
        "coverage_expansions": len(coverage_trace),
        "coverage_exact": exact_coverage,
        "covered_nodes": covered_nodes,
        "policy_budget": policy_budget,
        "policy_expansions": len(policy_trace),
        "archive_nodes": len(archive.records),
        "initial_evaluations": covered_nodes * INITIAL_EVALUATIONS_PER_NODE,
        "warmup_evaluations": len(warmup_trace),
        "post_coverage_evaluations": len(evaluation_trace) - covered_nodes,
        "total_evaluations": ledger.total_evaluations(),
        "unique_task_evaluations": ledger.all_tasks_unique(),
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
    reference = seed_sets[("mismatch", "uniform_evaluation")]
    if any(seeds != reference for seeds in seed_sets.values()):
        raise ValueError("M028 runs are not paired across rigs and strategies")
    expected_rows = len(reference) * len(expected_rigs) * len(expected_strategies)
    if len(runs) != expected_rows:
        raise ValueError("M028 runs contain missing or duplicate rows")

    summary: dict[str, object] = {
        "development_only": True,
        "paired_seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "development_min_seeds": DEVELOPMENT_MIN_SEEDS,
        "common_layered_coverage": True,
        "common_task_families": True,
        "common_task_orders": True,
        "common_parent_policy": True,
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
        "primary_metric": "final hidden exact quality per mille",
    }

    metrics = (
        "coverage_expansions",
        "total_evaluations",
        "high_potential_observed_allocation_share_per_mille",
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

    adaptive_rows = {
        int(row["seed"]): row
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "adaptive_evaluation"
    }
    uniform_rows = {
        int(row["seed"]): row
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "uniform_evaluation"
    }
    policy_differences = [
        int(adaptive_rows[seed]["final_hidden_per_mille"])
        - int(uniform_rows[seed]["final_hidden_per_mille"])
        for seed in sorted(reference)
    ]
    summary["mismatch_adaptive_minus_uniform_median_per_mille"] = _integer_median(
        policy_differences
    )
    summary["mismatch_adaptive_wins"] = sum(
        value > 0 for value in policy_differences
    )
    summary["mismatch_adaptive_ties"] = sum(
        value == 0 for value in policy_differences
    )
    summary["mismatch_adaptive_losses"] = sum(
        value < 0 for value in policy_differences
    )

    adaptive_alignment = int(
        summary[
            "mismatch_adaptive_evaluation_weighted_clade_exact_cmp_concordance_per_mille_median"
        ]
    )
    uniform_alignment = int(
        summary[
            "mismatch_uniform_evaluation_weighted_clade_exact_cmp_concordance_per_mille_median"
        ]
    )
    summary["mismatch_adaptive_minus_uniform_alignment_per_mille"] = (
        adaptive_alignment - uniform_alignment
    )
    adaptive_allocation = int(
        summary[
            "mismatch_adaptive_evaluation_high_potential_observed_allocation_share_per_mille_median"
        ]
    )
    uniform_allocation = int(
        summary[
            "mismatch_uniform_evaluation_high_potential_observed_allocation_share_per_mille_median"
        ]
    )
    summary["mismatch_adaptive_minus_uniform_high_potential_allocation_per_mille"] = (
        adaptive_allocation - uniform_allocation
    )

    enough = len(reference) >= DEVELOPMENT_MIN_SEEDS
    estimator_supported = (
        enough
        and adaptive_alignment >= ESTIMATOR_ALIGNMENT_FLOOR_PER_MILLE
        and int(summary["mismatch_adaptive_minus_uniform_alignment_per_mille"])
        >= ESTIMATOR_SEPARATION_FLOOR_PER_MILLE
    )
    policy_supported = (
        enough
        and int(summary["mismatch_adaptive_minus_uniform_median_per_mille"])
        >= POLICY_SEPARATION_FLOOR_PER_MILLE
        and int(summary["mismatch_adaptive_wins"]) >= POLICY_WIN_FLOOR
    )
    aligned_exact = all(
        int(row["final_development_per_mille"])
        == int(row["final_hidden_per_mille"])
        for row in runs
        if row["rig"] == "aligned"
    )
    summary["enough_seeds_for_comparison"] = enough
    summary["adaptive_estimator_alignment_supported"] = estimator_supported
    summary["adaptive_policy_advantage_supported"] = policy_supported
    summary["aligned_control_exact"] = aligned_exact
    summary["adaptive_evaluation_weighting_supported"] = (
        estimator_supported
        and policy_supported
        and aligned_exact
        and bool(summary["coverage_exact"])
        and bool(summary["unique_task_evaluations"])
        and not bool(summary["hidden_fields_visible_to_selectors"])
    )

    if not enough:
        status = "insufficient_paired_seeds"
    elif not bool(summary["coverage_exact"]):
        status = "coverage_control_failed"
    elif not aligned_exact:
        status = "aligned_control_failed"
    elif bool(summary["adaptive_evaluation_weighting_supported"]):
        status = "adaptive_evaluation_weighting_supported"
    elif estimator_supported:
        status = "estimator_alignment_without_policy_advantage"
    else:
        status = "adaptive_weighting_prediction_not_supported"
    summary["comparison_status"] = status
    return summary
