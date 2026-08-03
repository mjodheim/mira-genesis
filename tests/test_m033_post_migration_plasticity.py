from __future__ import annotations

from functools import lru_cache

import pytest

from metamorphosis.m012b_dfa import canonicalize, minimize_dfa
from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import (
    Case,
    ToolRegistry,
    VersionedCodeBody,
    apply_patch,
)
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    compile_policy_to_dfa,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_post_migration_plasticity import (
    ControlTaskFamily,
    LineageVariant,
    build_fresh_b_lineage,
    build_packet_derived_lineage,
    build_packet_derived_lineages,
    build_unchanged_parent_lineage,
    execute_control_task,
    generate_control_task,
    opaque_matches_source,
)


PRE_REWRITE_SOURCE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

PRE_REWRITE_TARGET = """\
def policy(state, symbol):
    return ((state * symbol) % 2) + 0
"""

PRE_REWRITE_DEVELOPMENT = (
    Case((0, 0), 0),
    Case((0, 1), 0),
    Case((1, 0), 0),
    Case((1, 1), 1),
)

PRE_REWRITE_REGRESSION = PRE_REWRITE_DEVELOPMENT

LEARNING_STATE = PortableLearningState(
    memory=((0, 1, 1), (1, 0, 1)),
    uncertainty=(3, 1),
    exploration_frontier=((1, 1), (0, 0)),
)


@lru_cache(maxsize=1)
def _packet() -> str:
    outcome = execute_trans_substrate_lifecycle(
        VersionedCodeBody("policy", PRE_REWRITE_SOURCE),
        ToolRegistry(),
        PRE_REWRITE_DEVELOPMENT,
        PRE_REWRITE_REGRESSION,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(0),
        search_seed=33_001,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    assert outcome.committed and outcome.packet_json is not None
    return outcome.packet_json


def _same_minimal_dfa(left, right) -> bool:
    return canonicalize(minimize_dfa(left)) == canonicalize(minimize_dfa(right))


def test_packet_derived_lineages_differ_only_at_declared_surfaces():
    lineages = build_packet_derived_lineages(_packet())
    complete = lineages[LineageVariant.COMPLETE]
    output_only = lineages[LineageVariant.OUTPUT_ONLY]
    state_ablated = lineages[LineageVariant.LEARNING_STATE_ABLATED]
    tools_ablated = lineages[LineageVariant.LEARNED_TOOLS_ABLATED]

    assert set(lineages) == {
        LineageVariant.COMPLETE,
        LineageVariant.OUTPUT_ONLY,
        LineageVariant.LEARNING_STATE_ABLATED,
        LineageVariant.LEARNED_TOOLS_ABLATED,
    }
    assert {lineage.source_packet_sha256 for lineage in lineages.values()} == {
        complete.source_packet_sha256
    }
    assert all(
        lineage.body.active_source == complete.body.active_source
        for lineage in lineages.values()
    )
    assert all(
        lineage.body.archive == complete.body.archive
        for lineage in lineages.values()
    )
    assert all(
        lineage.source_dfa == complete.source_dfa for lineage in lineages.values()
    )
    assert all(
        lineage.opaque_body == complete.opaque_body for lineage in lineages.values()
    )

    assert complete.learning_state == LEARNING_STATE
    assert output_only.learning_state == LEARNING_STATE
    assert tools_ablated.learning_state == LEARNING_STATE
    assert state_ablated.learning_state == PortableLearningState()

    assert len(complete.registry.learned) == 1
    assert len(complete.registry.learned[0].operations) == 2
    assert len(output_only.registry.learned) == 1
    assert len(state_ablated.registry.learned) == 1
    assert tools_ablated.registry.learned == []

    assert complete.can_rewrite and complete.can_update_learning_state
    assert state_ablated.can_rewrite and state_ablated.can_update_learning_state
    assert tools_ablated.can_rewrite and tools_ablated.can_update_learning_state
    assert not output_only.can_rewrite
    assert not output_only.can_update_learning_state


def test_lineage_rehydrations_share_no_mutable_body_or_registry_state():
    lineages = build_packet_derived_lineages(_packet())
    complete = lineages[LineageVariant.COMPLETE]
    output_only = lineages[LineageVariant.OUTPUT_ONLY]

    complete.body.archive.append("mutation sentinel")
    complete.body.adopted_digests.append("digest sentinel")
    complete.registry.learned.clear()

    assert "mutation sentinel" not in output_only.body.archive
    assert "digest sentinel" not in output_only.body.adopted_digests
    assert len(output_only.registry.learned) == 1


def test_same_variant_rehydrates_byte_identically():
    packet = _packet()
    first = build_packet_derived_lineage(packet, LineageVariant.COMPLETE)
    second = build_packet_derived_lineage(packet, LineageVariant.COMPLETE)

    assert first.canonical_snapshot() == second.canonical_snapshot()
    assert first.snapshot_sha256() == second.snapshot_sha256()


def test_unchanged_parent_reconstructs_pre_adoption_state_and_migrates_exactly():
    machine = make_development_positive_machine(2)
    lineage = build_unchanged_parent_lineage(
        _packet(),
        state_count=2,
        accepting_states=(False, True),
        machine=machine,
        search_seed=33_002,
    )

    assert lineage.variant is LineageVariant.UNCHANGED_PARENT
    assert lineage.body.active_source == PRE_REWRITE_SOURCE
    assert lineage.body.archive == []
    assert len(lineage.body.adopted_digests) == 1
    assert lineage.registry.learned == []
    assert lineage.learning_state == LEARNING_STATE
    assert lineage.source_packet_sha256 is not None
    assert lineage.construction_cost.packet_validations == 1
    assert lineage.construction_cost.substrate_probes > 0
    assert opaque_matches_source(lineage, machine)


def test_fresh_b_begins_after_reveal_without_migrated_state_or_tools():
    task = generate_control_task(1024, ControlTaskFamily.POSITIVE_TOOL)
    machine = make_development_positive_machine(3)
    lineage = build_fresh_b_lineage(
        task.baseline_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        machine=machine,
        search_seed=33_003,
    )

    assert lineage.variant is LineageVariant.FRESH_B
    assert lineage.origin_checkpoint == "created_on_b_after_task_reveal"
    assert lineage.source_packet_sha256 is None
    assert lineage.learning_state == PortableLearningState()
    assert lineage.registry.learned == []
    assert lineage.body.archive == []
    assert lineage.construction_cost.packet_validations == 0
    assert lineage.construction_cost.substrate_probes > 0
    assert opaque_matches_source(lineage, machine)


def test_control_task_generator_rejects_primary_seeds_and_is_deterministic():
    with pytest.raises(ValueError, match="at least 1024"):
        generate_control_task(63, ControlTaskFamily.POSITIVE_TOOL)

    first = generate_control_task(1025, ControlTaskFamily.POSITIVE_TOOL)
    second = generate_control_task(1025, ControlTaskFamily.POSITIVE_TOOL)
    other = generate_control_task(1026, ControlTaskFamily.POSITIVE_TOOL)

    assert first.canonical_json() == second.canonical_json()
    assert first.sha256() == second.sha256()
    assert first.sha256() != other.sha256()
    assert len(first.held_out_words) == 8


def test_positive_tool_control_requires_transport_plus_a_new_operation():
    task = generate_control_task(1027, ControlTaskFamily.POSITIVE_TOOL)
    complete = build_packet_derived_lineage(_packet(), LineageVariant.COMPLETE)
    learned = complete.registry.learned[0]
    replayed_source = apply_patch(task.baseline_source, learned.operations)
    replayed_dfa = compile_policy_to_dfa(
        replayed_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
    )

    assert not _same_minimal_dfa(replayed_dfa, task.target_dfa)

    fresh = build_fresh_b_lineage(
        task.baseline_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        machine=make_development_positive_machine(4),
        search_seed=33_004,
    )
    complete_result = execute_control_task(complete, task)
    fresh_result = execute_control_task(fresh, task)

    assert complete_result.exact
    assert fresh_result.exact
    assert complete_result.adopted and fresh_result.adopted
    assert complete_result.candidates_evaluated < fresh_result.candidates_evaluated
    assert complete_result.learned_tool_name is not None
    assert complete.learning_state.memory[-1][0] == task.seed


def test_irrelevant_transport_does_not_improve_negative_tool_control():
    task = generate_control_task(1028, ControlTaskFamily.NEGATIVE_TOOL)
    complete = build_packet_derived_lineage(_packet(), LineageVariant.COMPLETE)
    fresh = build_fresh_b_lineage(
        task.baseline_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        machine=make_development_positive_machine(5),
        search_seed=33_005,
    )

    complete_result = execute_control_task(complete, task)
    fresh_result = execute_control_task(fresh, task)

    assert complete_result.exact and fresh_result.exact
    assert complete_result.candidates_evaluated >= fresh_result.candidates_evaluated


def test_output_only_control_is_immutable_when_task_is_revealed():
    lineage = build_packet_derived_lineage(_packet(), LineageVariant.OUTPUT_ONLY)
    task = generate_control_task(1029, ControlTaskFamily.POSITIVE_TOOL)
    before = lineage.canonical_snapshot()

    result = execute_control_task(lineage, task)

    assert not result.attempted
    assert not result.adopted
    assert not result.exact
    assert lineage.canonical_snapshot() == before
