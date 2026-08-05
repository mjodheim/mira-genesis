from __future__ import annotations

import inspect

import pytest

from metamorphosis.m043_mealy import (
    MealyMachine,
    exact_mealy_equivalence,
    minimize_mealy,
)
from metamorphosis.m043_rewrite import (
    DuplicateReachableTarget,
    ReplaceEmission,
    replay_rewrite_trace,
)
from metamorphosis.m043_tasks import (
    ControlArm,
    HiddenTargetEvaluator,
    SearchBudget,
    SearchCapabilities,
    SearchStatus,
    TaskQualificationError,
    blind_constructive_search,
    control_capabilities,
    propose_operation_paths,
    prove_structural_incapacity,
    validate_control_surfaces,
)


def parent() -> MealyMachine:
    return MealyMachine(
        input_alphabet=(0, 1, 2),
        output_alphabet=(0, 1, 2),
        transitions=((0, 1, 0), (0, 1, 1)),
        outputs=((0, 1, 2), (1, 0, 2)),
        initial=0,
    )


def known_target() -> MealyMachine:
    from metamorphosis.m043_rewrite import apply_rewrite

    grown, _ = apply_rewrite(parent(), DuplicateReachableTarget(0, 0))
    target, _ = apply_rewrite(grown, ReplaceEmission(2, 0, 1))
    return target


def budget() -> SearchBudget:
    return SearchBudget(max_depth=2, max_nodes=512, max_states=4)


def test_structural_incapacity_is_an_exact_minimal_state_theorem() -> None:
    certificate = prove_structural_incapacity(parent(), known_target())

    assert certificate.parent_physical_states == 2
    assert certificate.parent_minimal_states == 2
    assert certificate.target_minimal_states == 3
    assert certificate.required_growth == 1
    assert minimize_mealy(known_target()).n_states > parent().n_states


def test_certificate_rejects_a_target_expressible_at_parent_capacity() -> None:
    with pytest.raises(TaskQualificationError, match="does not exceed"):
        prove_structural_incapacity(parent(), parent())


def test_certificate_rejects_nonminimal_declared_parent() -> None:
    nonminimal = MealyMachine(
        (0, 1, 2),
        (0, 1, 2),
        ((0, 1, 0), (0, 1, 1), (2, 2, 2)),
        ((0, 1, 2), (1, 0, 2), (0, 0, 0)),
        0,
    )
    with pytest.raises(
        TaskQualificationError, match="canonical, reachable and minimal"
    ):
        prove_structural_incapacity(nonminimal, known_target())


def test_operation_proposals_are_target_blind_by_signature_and_source() -> None:
    signature = inspect.signature(propose_operation_paths)
    source = inspect.getsource(propose_operation_paths)

    assert tuple(signature.parameters) == ("machine", "capabilities")
    assert "target" not in signature.parameters
    assert "evaluator" not in signature.parameters
    assert "exact_mealy_equivalence" not in source


def test_composed_tool_enumerates_generic_two_step_q2_paths() -> None:
    paths = propose_operation_paths(
        parent(), control_capabilities()[ControlArm.COMPLETE]
    )

    tool_paths = [
        path for path in paths if path.source == "lineage_composed_split_tool"
    ]
    assert tool_paths
    assert all(len(path.operations) == 2 for path in tool_paths)
    assert all(
        isinstance(path.operations[0], DuplicateReachableTarget)
        for path in tool_paths
    )
    assert all(
        isinstance(path.operations[1], ReplaceEmission)
        for path in tool_paths
    )


def test_all_six_control_surfaces_are_distinct_and_share_one_budget() -> None:
    surfaces = control_capabilities()
    shared = budget()

    validate_control_surfaces(surfaces, shared)

    assert set(surfaces) == set(ControlArm)
    assert len({surface.causal_surface() for surface in surfaces.values()}) == 6
    assert surfaces[ControlArm.COMPLETE].composed_split_tool
    assert not surfaces[ControlArm.TOOL_ABLATED].composed_split_tool
    assert (
        surfaces[ControlArm.COMPLETE].priority
        != surfaces[ControlArm.LEARNING_STATE_ABLATED].priority
    )
    complete_paths = propose_operation_paths(
        parent(), surfaces[ControlArm.COMPLETE]
    )
    ablated_paths = propose_operation_paths(
        parent(), surfaces[ControlArm.LEARNING_STATE_ABLATED]
    )
    assert complete_paths[:8] != ablated_paths[:8]


def test_collapsed_control_surfaces_fail_closed() -> None:
    surfaces = control_capabilities()
    surfaces[ControlArm.FRESH] = SearchCapabilities(
        ControlArm.FRESH,
        surfaces[ControlArm.COMPLETE].allowed,
        surfaces[ControlArm.COMPLETE].priority,
        True,
        True,
    )
    with pytest.raises(TaskQualificationError, match="collapse"):
        validate_control_surfaces(surfaces, budget())


def test_complete_blind_search_finds_and_replays_exact_target() -> None:
    evaluator = HiddenTargetEvaluator(known_target())
    result = blind_constructive_search(
        parent(),
        evaluator,
        budget(),
        control_capabilities()[ControlArm.COMPLETE],
    )

    assert result.status is SearchStatus.FOUND
    assert result.trace is not None
    replayed = replay_rewrite_trace(parent(), result.trace)
    assert exact_mealy_equivalence(replayed, known_target()) == (True, None)
    assert len(result.trace.steps) == 2


def test_unchanged_and_output_only_controls_cannot_cross_state_bound() -> None:
    surfaces = control_capabilities()
    unchanged = blind_constructive_search(
        parent(),
        HiddenTargetEvaluator(known_target()),
        budget(),
        surfaces[ControlArm.UNCHANGED_PARENT],
    )
    output_only = blind_constructive_search(
        parent(),
        HiddenTargetEvaluator(known_target()),
        budget(),
        surfaces[ControlArm.OUTPUT_ONLY],
    )

    assert not unchanged.exact
    assert unchanged.status is SearchStatus.EXHAUSTED
    assert not output_only.exact
    assert output_only.status is SearchStatus.DEPTH_LIMIT_REACHED


def test_node_budget_exhaustion_is_explicit_and_deterministic() -> None:
    tiny = SearchBudget(max_depth=2, max_nodes=1, max_states=4)
    first = blind_constructive_search(
        parent(),
        HiddenTargetEvaluator(known_target()),
        tiny,
        control_capabilities()[ControlArm.COMPLETE],
    )
    second = blind_constructive_search(
        parent(),
        HiddenTargetEvaluator(known_target()),
        tiny,
        control_capabilities()[ControlArm.COMPLETE],
    )

    assert first == second
    assert first.status is SearchStatus.NODE_BUDGET_EXHAUSTED
    assert first.nodes_seen == 1


def test_depth_limit_is_explicit() -> None:
    shallow = SearchBudget(max_depth=1, max_nodes=512, max_states=4)
    result = blind_constructive_search(
        parent(),
        HiddenTargetEvaluator(known_target()),
        shallow,
        control_capabilities()[ControlArm.COMPLETE],
    )

    assert not result.exact
    assert result.status is SearchStatus.DEPTH_LIMIT_REACHED
