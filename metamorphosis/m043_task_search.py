"""Target-blind constructive search and catalogue admission for M043 gate Q3."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from metamorphosis.m043_mealy import (
    MealyMachine,
    exact_mealy_equivalence,
    mealy_digest,
    minimize_mealy,
)
from metamorphosis.m043_rewrite import (
    DuplicateReachableTarget,
    RedirectTransition,
    ReplaceEmission,
    RewriteError,
    RewriteOperation,
    RewriteTrace,
    apply_rewrite,
    build_rewrite_trace,
    exact_body_digest,
    reachable_states,
    replay_rewrite_trace,
)
from metamorphosis.m043_task_model import (
    AdmittedConstructiveTask,
    CatalogueResult,
    CatalogueStatus,
    ControlArm,
    HiddenTargetEvaluator,
    OperationKind,
    PublicTaskView,
    SearchBudget,
    SearchCapabilities,
    SearchOutcome,
    SearchStatus,
    TaskQualificationError,
    control_capabilities,
    prove_structural_incapacity,
    validate_control_surfaces,
)


@dataclass(frozen=True)
class ProposedPath:
    operations: tuple[RewriteOperation, ...]
    source: str


def _primitive_operations(
    machine: MealyMachine, kind: OperationKind
) -> Iterable[RewriteOperation]:
    reachable = tuple(sorted(reachable_states(machine)))
    if kind is OperationKind.DUPLICATE:
        for state in reachable:
            for symbol in machine.input_alphabet:
                yield DuplicateReachableTarget(state, symbol)
    elif kind is OperationKind.REPLACE_EMISSION:
        for state in reachable:
            for index, symbol in enumerate(machine.input_alphabet):
                current = machine.outputs[state][index]
                for output in machine.output_alphabet:
                    if output != current:
                        yield ReplaceEmission(state, symbol, output)
    elif kind is OperationKind.REDIRECT_TRANSITION:
        for state in reachable:
            for index, symbol in enumerate(machine.input_alphabet):
                current = machine.transitions[state][index]
                for target in range(machine.n_states):
                    if target != current:
                        yield RedirectTransition(state, symbol, target)


def propose_operation_paths(
    machine: MealyMachine, capabilities: SearchCapabilities
) -> tuple[ProposedPath, ...]:
    """Generate target-blind candidate paths from the current body and capabilities."""

    paths: list[ProposedPath] = []
    if (
        capabilities.composed_split_tool
        and OperationKind.DUPLICATE in capabilities.allowed
    ):
        clone = machine.n_states
        duplicates = list(_primitive_operations(machine, OperationKind.DUPLICATE))
        edit_symbols = list(machine.input_alphabet)
        outputs = list(machine.output_alphabet)
        # Portable learning state changes only deterministic proposal order. It never
        # receives a target symbol or table and therefore cannot encode the hidden answer.
        if capabilities.learning_state_active:
            duplicates.reverse()
            edit_symbols.reverse()
            outputs.reverse()
        for duplicate in duplicates:
            for edit_symbol in edit_symbols:
                target_state = machine.transitions[duplicate.entry_state][
                    machine.input_alphabet.index(duplicate.input_symbol)
                ]
                current = machine.outputs[target_state][
                    machine.input_alphabet.index(edit_symbol)
                ]
                for output in outputs:
                    if output != current:
                        paths.append(
                            ProposedPath(
                                (
                                    duplicate,
                                    ReplaceEmission(clone, edit_symbol, output),
                                ),
                                "lineage_composed_split_tool",
                            )
                        )
    for kind in capabilities.priority:
        for operation in _primitive_operations(machine, kind):
            paths.append(ProposedPath((operation,), "q2_primitive"))
    return tuple(paths)


def blind_constructive_search(
    parent: MealyMachine,
    evaluator: HiddenTargetEvaluator,
    budget: SearchBudget,
    capabilities: SearchCapabilities,
) -> SearchOutcome:
    """Search without exposing a target table to the proposal surface."""

    exact, _ = evaluator._evaluate_exact(parent)
    if exact:
        _, trace = build_rewrite_trace(parent, ())
        return SearchOutcome(
            capabilities.arm,
            SearchStatus.FOUND,
            budget,
            1,
            0,
            0,
            trace,
            mealy_digest(parent, minimise=True),
        )

    queue = deque([(parent, tuple(), 0)])
    seen = {exact_body_digest(parent)}
    nodes_seen = 1
    paths_considered = 0
    max_depth_reached = 0
    depth_blocked = False

    while queue:
        current, operations, depth = queue.popleft()
        max_depth_reached = max(max_depth_reached, depth)
        if depth >= budget.max_depth:
            depth_blocked = True
            continue
        for path in propose_operation_paths(current, capabilities):
            paths_considered += 1
            next_depth = depth + len(path.operations)
            if next_depth > budget.max_depth:
                depth_blocked = True
                continue
            candidate = current
            try:
                for operation in path.operations:
                    candidate, _ = apply_rewrite(candidate, operation)
                    if candidate.n_states > budget.max_states:
                        raise RewriteError("candidate exceeds Q3 state cap")
            except (RewriteError, ValueError):
                continue
            identity = exact_body_digest(candidate)
            if identity in seen:
                continue
            if nodes_seen >= budget.max_nodes:
                return SearchOutcome(
                    capabilities.arm,
                    SearchStatus.NODE_BUDGET_EXHAUSTED,
                    budget,
                    nodes_seen,
                    paths_considered,
                    max_depth_reached,
                    None,
                    None,
                )
            seen.add(identity)
            nodes_seen += 1
            candidate_operations = operations + path.operations
            exact, _ = evaluator._evaluate_exact(candidate)
            if exact:
                final, trace = build_rewrite_trace(parent, candidate_operations)
                if not exact_mealy_equivalence(final, candidate)[0]:
                    raise TaskQualificationError(
                        "reconstructed Q2 trace changed the candidate"
                    )
                return SearchOutcome(
                    capabilities.arm,
                    SearchStatus.FOUND,
                    budget,
                    nodes_seen,
                    paths_considered,
                    next_depth,
                    trace,
                    mealy_digest(candidate, minimise=True),
                )
            queue.append((candidate, candidate_operations, next_depth))

    status = (
        SearchStatus.DEPTH_LIMIT_REACHED
        if depth_blocked
        else SearchStatus.EXHAUSTED
    )
    return SearchOutcome(
        capabilities.arm,
        status,
        budget,
        nodes_seen,
        paths_considered,
        max_depth_reached,
        None,
        None,
    )


@dataclass(frozen=True)
class _HistorySplitSpec:
    entry_state: int
    entry_symbol: int
    edit_symbol: int
    replacement_output: int


def _candidate_specs(parent: MealyMachine) -> Iterable[_HistorySplitSpec]:
    for entry_state in sorted(reachable_states(parent)):
        for entry_symbol in parent.input_alphabet:
            duplicate = DuplicateReachableTarget(entry_state, entry_symbol)
            try:
                grown, _ = apply_rewrite(parent, duplicate)
            except RewriteError:
                continue
            clone = grown.n_states - 1
            for edit_symbol in parent.input_alphabet:
                current = grown.outputs[clone][
                    parent.input_alphabet.index(edit_symbol)
                ]
                for output in parent.output_alphabet:
                    if output != current:
                        yield _HistorySplitSpec(
                            entry_state, entry_symbol, edit_symbol, output
                        )


def _construct_hidden_target(
    parent: MealyMachine, spec: _HistorySplitSpec
) -> MealyMachine:
    grown, _ = apply_rewrite(
        parent, DuplicateReachableTarget(spec.entry_state, spec.entry_symbol)
    )
    target, _ = apply_rewrite(
        grown,
        ReplaceEmission(
            grown.n_states - 1,
            spec.edit_symbol,
            spec.replacement_output,
        ),
    )
    return target


def _trace_exploits_new_capacity(
    parent: MealyMachine, trace: RewriteTrace
) -> bool:
    current_states = parent.n_states
    grown_states: set[int] = set()
    for step in trace.steps:
        operation = step.operation
        if isinstance(operation, DuplicateReachableTarget):
            grown_states.add(current_states)
            current_states += 1
        elif isinstance(operation, (ReplaceEmission, RedirectTransition)):
            if operation.state in grown_states:
                return True
    return False


def _task_id(
    parent: MealyMachine,
    target_commitment: str,
    ordinal: int,
    budget: SearchBudget,
) -> str:
    material = {
        "schema": "m043-q3-task-id/1",
        "parent": exact_body_digest(parent),
        "target_commitment": target_commitment,
        "ordinal": ordinal,
        "budget": budget.to_dict(),
    }
    return hashlib.sha256(
        b"m043-q3-task-id-v1\x00"
        + json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_development_catalogue(
    parent: MealyMachine,
    *,
    budget: SearchBudget = SearchBudget(),
    minimum_entries: int = 2,
    maximum_candidates: int = 64,
    observation_limit: int = 64,
) -> CatalogueResult:
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in (minimum_entries, maximum_candidates)
    ):
        raise TaskQualificationError(
            "catalogue limits must be positive integers"
        )
    if minimum_entries > maximum_candidates:
        raise TaskQualificationError(
            "minimum_entries exceeds maximum_candidates"
        )
    declared_parent = minimize_mealy(parent)
    surfaces = control_capabilities()
    validate_control_surfaces(surfaces, budget)

    entries: list[AdmittedConstructiveTask] = []
    rejections: list[str] = []
    seen_targets: set[str] = set()
    candidates_considered = 0

    for spec in _candidate_specs(declared_parent):
        if candidates_considered >= maximum_candidates:
            break
        candidates_considered += 1
        target = _construct_hidden_target(declared_parent, spec)
        commitment = mealy_digest(target, minimise=True)
        if commitment in seen_targets:
            rejections.append("duplicate_target_behaviour")
            continue
        seen_targets.add(commitment)
        try:
            incapacity = prove_structural_incapacity(declared_parent, target)
        except TaskQualificationError:
            rejections.append("parent_not_structurally_incapable")
            continue

        evaluator = HiddenTargetEvaluator(
            target, observation_limit=observation_limit
        )
        complete = blind_constructive_search(
            declared_parent,
            evaluator,
            budget,
            surfaces[ControlArm.COMPLETE],
        )
        if not complete.exact or complete.trace is None:
            rejections.append(
                f"constructive_search_{complete.status.value}"
            )
            continue
        replayed = replay_rewrite_trace(declared_parent, complete.trace)
        if not exact_mealy_equivalence(replayed, target)[0]:
            rejections.append("constructive_trace_replay_not_exact")
            continue
        if not _trace_exploits_new_capacity(
            declared_parent, complete.trace
        ):
            rejections.append("trace_does_not_exploit_new_capacity")
            continue

        controls: list[SearchOutcome] = []
        for arm in (
            ControlArm.FRESH,
            ControlArm.UNCHANGED_PARENT,
            ControlArm.OUTPUT_ONLY,
            ControlArm.LEARNING_STATE_ABLATED,
            ControlArm.TOOL_ABLATED,
        ):
            control_evaluator = HiddenTargetEvaluator(
                target, observation_limit=observation_limit
            )
            controls.append(
                blind_constructive_search(
                    declared_parent,
                    control_evaluator,
                    budget,
                    surfaces[arm],
                )
            )
        if any(control.budget != budget for control in controls):
            raise TaskQualificationError(
                "a Q3 control did not receive the shared budget"
            )

        task_id = _task_id(
            declared_parent, commitment, len(entries), budget
        )
        public = PublicTaskView(
            schema="m043-q3-public-task/1",
            task_id=task_id,
            parent_exact_digest=exact_body_digest(declared_parent),
            target_commitment=commitment,
            input_alphabet=declared_parent.input_alphabet,
            output_alphabet=declared_parent.output_alphabet,
            observation_limit=observation_limit,
            search_budget=budget,
        )
        entries.append(
            AdmittedConstructiveTask(
                public=public,
                incapacity=incapacity,
                constructive_outcome=complete,
                controls=tuple(controls),
                target_minimal_states=minimize_mealy(target).n_states,
                evaluator=evaluator,
            )
        )
        if len(entries) >= minimum_entries:
            break

    status = (
        CatalogueStatus.QUALIFIED
        if len(entries) >= minimum_entries
        else CatalogueStatus.INSUFFICIENT
    )
    return CatalogueResult(
        status=status,
        entries=tuple(entries),
        candidates_considered=candidates_considered,
        rejection_reasons=tuple(rejections),
        minimum_entries=minimum_entries,
        maximum_candidates=maximum_candidates,
    )


Q3_DEVELOPMENT_BUDGET = SearchBudget(
    max_depth=2, max_nodes=512, max_states=4
)
Q3_DEVELOPMENT_MINIMUM_ENTRIES = 3
Q3_DEVELOPMENT_MAXIMUM_CANDIDATES = 32
Q3_DEVELOPMENT_OBSERVATION_LIMIT = 64


def q3_development_parent() -> MealyMachine:
    """Return the public, seed-free parent used only to qualify the Q3 rig."""

    return MealyMachine(
        input_alphabet=(0, 1, 2),
        output_alphabet=(0, 1, 2),
        transitions=((0, 1, 0), (0, 1, 1)),
        outputs=((0, 1, 2), (1, 0, 2)),
        initial=0,
    )


def run_q3_development_catalogue() -> CatalogueResult:
    """Build the deterministic, unselected Q3 development catalogue."""

    return build_development_catalogue(
        q3_development_parent(),
        budget=Q3_DEVELOPMENT_BUDGET,
        minimum_entries=Q3_DEVELOPMENT_MINIMUM_ENTRIES,
        maximum_candidates=Q3_DEVELOPMENT_MAXIMUM_CANDIDATES,
        observation_limit=Q3_DEVELOPMENT_OBSERVATION_LIMIT,
    )
