"""M033 functional controls for transported memory.

The primary task block remains unopened.  A memory row encodes one bounded rewrite
operation.  The first decodable row is attempted as the lineage's first exploration
action; it is retained only when public development evidence strictly improves.
Relevant, permuted and empty states can therefore be compared without a hidden oracle.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .m012b_dfa import canonicalize, minimize_dfa
from .m020_self_rewrite import (
    PatchOperation,
    SelfRewriteEngine,
    VersionedCodeBody,
    apply_patch,
    evaluate_source,
)
from .m032_trans_substrate_lifecycle import PortableLearningState, compile_policy_to_dfa
from .m033_post_migration_plasticity import (
    ControlTask,
    DeterministicCost,
    PostMigrationLineage,
    TaskAnchor,
    lineage_start_source,
)


_BINARY_CODES = {
    0: "add",
    1: "mul",
    2: "sub",
    3: "floordiv",
    4: "mod",
}


@dataclass(frozen=True)
class MemoryExplorationDecision:
    attempted: bool
    accepted: bool
    operation: PatchOperation | None
    baseline_passed: int
    hinted_passed: int
    candidate_evaluations: int
    selected_source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "accepted": self.accepted,
            "operation": list(self.operation.key()) if self.operation else None,
            "baseline_passed": self.baseline_passed,
            "hinted_passed": self.hinted_passed,
            "candidate_evaluations": self.candidate_evaluations,
            "selected_source": self.selected_source,
        }


@dataclass(frozen=True)
class MemoryControlResult:
    variant: str
    task_sha256: str
    exact: bool
    quality_per_mille: int
    total_candidate_evaluations: int
    rewrite_candidate_evaluations: int
    memory_decision: MemoryExplorationDecision
    final_source: str
    learned_tool_name: str | None
    lineage_snapshot_sha256: str

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-memory-control-result/1",
                "variant": self.variant,
                "task_sha256": self.task_sha256,
                "exact": self.exact,
                "quality_per_mille": self.quality_per_mille,
                "total_candidate_evaluations": self.total_candidate_evaluations,
                "rewrite_candidate_evaluations": self.rewrite_candidate_evaluations,
                "memory_decision": self.memory_decision.to_dict(),
                "final_source": self.final_source,
                "learned_tool_name": self.learned_tool_name,
                "lineage_snapshot_sha256": self.lineage_snapshot_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _decode_memory_row(row: tuple[int, ...]) -> PatchOperation | None:
    if len(row) != 3:
        return None
    kind, index, value = row
    if index < 0:
        return None
    if kind == 0:
        return PatchOperation("constant", index, value)
    if kind == 1 and value in _BINARY_CODES:
        return PatchOperation("binary_operator", index, _BINARY_CODES[value])
    return None


def choose_memory_exploration(
    lineage: PostMigrationLineage,
    task: ControlTask,
    anchor: TaskAnchor = TaskAnchor.TASK_BASELINE,
) -> MemoryExplorationDecision:
    """Attempt the first decodable memory operation using development evidence only."""

    start_source = lineage_start_source(lineage, task, anchor)
    baseline = evaluate_source(
        start_source,
        task.function_name,
        task.development_cases,
    )
    operation = next(
        (
            decoded
            for row in lineage.learning_state.memory
            if (decoded := _decode_memory_row(row)) is not None
        ),
        None,
    )
    if operation is None:
        return MemoryExplorationDecision(
            attempted=False,
            accepted=False,
            operation=None,
            baseline_passed=baseline.passed,
            hinted_passed=baseline.passed,
            candidate_evaluations=0,
            selected_source=start_source,
        )

    try:
        hinted_source = apply_patch(start_source, (operation,))
        hinted = evaluate_source(
            hinted_source,
            task.function_name,
            task.development_cases,
        )
    except (SyntaxError, TypeError, ValueError):
        return MemoryExplorationDecision(
            attempted=True,
            accepted=False,
            operation=operation,
            baseline_passed=baseline.passed,
            hinted_passed=baseline.passed,
            candidate_evaluations=1,
            selected_source=start_source,
        )

    accepted = hinted.passed > baseline.passed
    return MemoryExplorationDecision(
        attempted=True,
        accepted=accepted,
        operation=operation,
        baseline_passed=baseline.passed,
        hinted_passed=hinted.passed,
        candidate_evaluations=1,
        selected_source=hinted_source if accepted else start_source,
    )


def execute_memory_guided_task(
    lineage: PostMigrationLineage,
    task: ControlTask,
    *,
    beam_width: int = 64,
    anchor: TaskAnchor = TaskAnchor.TASK_BASELINE,
) -> MemoryControlResult:
    """Run the bounded control task after one memory-directed exploration decision."""

    if not lineage.can_rewrite or not lineage.can_update_learning_state:
        raise ValueError("memory control requires a learning-capable lineage")

    decision = choose_memory_exploration(lineage, task, anchor)
    remaining_edits = task.max_edits - int(decision.accepted)
    if remaining_edits < 1:
        remaining_edits = 1

    task_body = VersionedCodeBody(task.function_name, decision.selected_source)
    rewrite = SelfRewriteEngine(
        lineage.registry,
        max_edits=remaining_edits,
        beam_width=beam_width,
    ).improve(
        decision.selected_source,
        task.function_name,
        task.development_cases,
    )
    task_body.adopt(rewrite)
    final_dfa = compile_policy_to_dfa(
        task_body.active_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        initial_state=task.initial_state,
    )
    exact = canonicalize(minimize_dfa(final_dfa)) == canonicalize(
        minimize_dfa(task.target_dfa)
    )
    passed = rewrite.selected.development.passed
    total_evaluations = (
        decision.candidate_evaluations + rewrite.candidates_evaluated
    )

    lineage.learning_state = PortableLearningState(
        memory=lineage.learning_state.memory
        + ((task.seed, passed, len(task.development_cases)),),
        uncertainty=lineage.learning_state.uncertainty
        + (len(task.development_cases) - passed,),
        exploration_frontier=lineage.learning_state.exploration_frontier
        + ((total_evaluations, int(exact)),),
    )
    lineage.construction_cost = lineage.construction_cost.plus(
        DeterministicCost(rewrite_candidate_evaluations=total_evaluations)
    )

    return MemoryControlResult(
        variant=lineage.variant.value,
        task_sha256=task.sha256(),
        exact=exact,
        quality_per_mille=(1000 * passed) // len(task.development_cases),
        total_candidate_evaluations=total_evaluations,
        rewrite_candidate_evaluations=rewrite.candidates_evaluated,
        memory_decision=decision,
        final_source=task_body.active_source,
        learned_tool_name=rewrite.learned_tool,
        lineage_snapshot_sha256=lineage.snapshot_sha256(),
    )
