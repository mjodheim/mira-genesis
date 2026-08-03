from __future__ import annotations

from functools import lru_cache

from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import Case, ToolRegistry, VersionedCodeBody
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_memory_controls import (
    choose_memory_exploration,
    execute_memory_guided_task,
)
from metamorphosis.m033_post_migration_plasticity import (
    ControlTaskFamily,
    LineageVariant,
    build_packet_derived_lineage,
    generate_control_task,
)


PRE_REWRITE_SOURCE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

PRE_REWRITE_DEVELOPMENT = (
    Case((0, 0), 0),
    Case((0, 1), 0),
    Case((1, 0), 0),
    Case((1, 1), 1),
)

RELEVANT_STATE = PortableLearningState(
    memory=((0, 1, 1), (1, 0, 1)),
    uncertainty=(3, 1),
    exploration_frontier=((1, 1), (0, 0)),
)

PERMUTED_STATE = PortableLearningState(
    memory=tuple(reversed(RELEVANT_STATE.memory)),
    uncertainty=RELEVANT_STATE.uncertainty,
    exploration_frontier=RELEVANT_STATE.exploration_frontier,
)


@lru_cache(maxsize=1)
def _packet() -> str:
    outcome = execute_trans_substrate_lifecycle(
        VersionedCodeBody("policy", PRE_REWRITE_SOURCE),
        ToolRegistry(),
        PRE_REWRITE_DEVELOPMENT,
        PRE_REWRITE_DEVELOPMENT,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(33),
        search_seed=333_001,
        learning_state=RELEVANT_STATE,
        max_edits=2,
        beam_width=64,
    )
    assert outcome.committed and outcome.packet_json is not None
    return outcome.packet_json


def _lineage(state: PortableLearningState):
    lineage = build_packet_derived_lineage(_packet(), LineageVariant.COMPLETE)
    lineage.learning_state = state
    return lineage


def test_relevant_memory_changes_the_pre_written_exploration_decision():
    task = generate_control_task(1032, ControlTaskFamily.POSITIVE_TOOL)
    relevant = _lineage(RELEVANT_STATE)
    permuted = _lineage(PERMUTED_STATE)
    empty = _lineage(PortableLearningState())

    relevant_decision = choose_memory_exploration(relevant, task)
    permuted_decision = choose_memory_exploration(permuted, task)
    empty_decision = choose_memory_exploration(empty, task)

    assert relevant_decision.attempted
    assert relevant_decision.accepted
    assert relevant_decision.operation is not None
    assert relevant_decision.operation.key() == ("constant", 1, 1)
    assert relevant_decision.hinted_passed > relevant_decision.baseline_passed

    assert permuted_decision.attempted
    assert not permuted_decision.accepted
    assert permuted_decision.operation is not None
    assert permuted_decision.operation.key() == ("binary_operator", 0, "mul")

    assert not empty_decision.attempted
    assert not empty_decision.accepted
    assert empty_decision.operation is None


def test_relevant_memory_reduces_search_against_permuted_and_empty_controls():
    task = generate_control_task(1033, ControlTaskFamily.POSITIVE_TOOL)
    relevant_result = execute_memory_guided_task(_lineage(RELEVANT_STATE), task)
    permuted_result = execute_memory_guided_task(_lineage(PERMUTED_STATE), task)
    empty_result = execute_memory_guided_task(
        _lineage(PortableLearningState()), task
    )

    assert relevant_result.exact
    assert permuted_result.exact
    assert empty_result.exact
    assert relevant_result.memory_decision.accepted
    assert not permuted_result.memory_decision.accepted
    assert not empty_result.memory_decision.attempted
    assert (
        relevant_result.total_candidate_evaluations
        < permuted_result.total_candidate_evaluations
    )
    assert (
        relevant_result.total_candidate_evaluations
        < empty_result.total_candidate_evaluations
    )


def test_memory_control_is_byte_deterministic_from_identical_inputs():
    task = generate_control_task(1034, ControlTaskFamily.POSITIVE_TOOL)
    first = execute_memory_guided_task(_lineage(RELEVANT_STATE), task)
    second = execute_memory_guided_task(_lineage(RELEVANT_STATE), task)

    assert first.canonical_json() == second.canonical_json()
    assert first.sha256() == second.sha256()
