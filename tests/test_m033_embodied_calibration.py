"""Gate 8 requires four distinct controls. The task-baseline anchor collapses two.

These tests pin the defect and its repair. Under `TASK_BASELINE` the migrated body is
never read, so the unchanged parent and the learned-tool ablation start a post-migration
task from the same source. Under `LINEAGE_BODY` they separate.
"""

from __future__ import annotations

import pytest

from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import Case, ToolRegistry, VersionedCodeBody
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_memory_controls import execute_memory_guided_task
from metamorphosis.m033_post_migration_plasticity import (
    LineageVariant,
    TaskAnchor,
    build_fresh_b_lineage,
    build_packet_derived_lineage,
    build_unchanged_parent_lineage,
    lineage_start_source,
)
from metamorphosis.m033_structural_tasks import (
    COMBINED_CONTROL_SEED_START,
    EMBODIED_CONTROL_SEED_START,
    generate_combined_control_task,
    generate_embodied_control_task,
)

SEED = EMBODIED_CONTROL_SEED_START

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

LEARNING_STATE = PortableLearningState(
    memory=((0, 1, 1), (1, 0, 1)),
    uncertainty=(3, 1),
    exploration_frontier=((1, 1), (0, 0)),
)


def _packet(seed: int = SEED) -> str:
    outcome = execute_trans_substrate_lifecycle(
        VersionedCodeBody("policy", PRE_REWRITE_SOURCE),
        ToolRegistry(),
        PRE_REWRITE_DEVELOPMENT,
        PRE_REWRITE_DEVELOPMENT,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(seed),
        search_seed=340_000 + seed,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    assert outcome.committed and outcome.packet_json is not None
    return outcome.packet_json


def _parent(packet: str, seed: int = SEED):
    return build_unchanged_parent_lineage(
        packet,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(seed),
        search_seed=342_000 + seed,
    )


def test_embodied_generator_rejects_all_earlier_blocks():
    with pytest.raises(ValueError, match="at least 4096"):
        generate_embodied_control_task(EMBODIED_CONTROL_SEED_START - 1)
    with pytest.raises(ValueError, match="3072 through 4095"):
        generate_combined_control_task(EMBODIED_CONTROL_SEED_START)
    with pytest.raises(ValueError, match="3072 through 4095"):
        generate_combined_control_task(COMBINED_CONTROL_SEED_START - 1)


def test_embodied_block_is_deterministic_and_structurally_complete():
    records = [
        generate_embodied_control_task(EMBODIED_CONTROL_SEED_START + offset)
        for offset in range(4)
    ]
    assert {record.template_id for record in records} == {0, 1, 2, 3}
    assert len({record.sha256() for record in records}) == 4
    assert all(
        '"version":"m033-embodied-control-task/1"' in record.canonical_json()
        for record in records
    )
    assert all(
        record.canonical_json()
        == generate_embodied_control_task(
            EMBODIED_CONTROL_SEED_START + offset
        ).canonical_json()
        for offset, record in enumerate(records)
    )


def test_task_baseline_anchor_collapses_parent_onto_the_tool_ablation():
    """The recorded defect: two Gate 8 controls become one experiment."""

    packet = _packet()
    task = generate_embodied_control_task(SEED).task
    parent = _parent(packet)
    tool_ablated = build_packet_derived_lineage(
        packet, LineageVariant.LEARNED_TOOLS_ABLATED
    )

    # Their bodies genuinely differ...
    assert parent.body.active_source != tool_ablated.body.active_source
    # ...but neither the tool registry nor the learning state does...
    assert [tool.name for tool in parent.registry.learned] == []
    assert [tool.name for tool in tool_ablated.registry.learned] == []
    assert parent.learning_state == tool_ablated.learning_state
    # ...so under the task-baseline anchor they start from an identical source.
    assert lineage_start_source(
        parent, task, TaskAnchor.TASK_BASELINE
    ) == lineage_start_source(tool_ablated, task, TaskAnchor.TASK_BASELINE)


def test_lineage_body_anchor_separates_the_two_controls():
    packet = _packet()
    task = generate_embodied_control_task(SEED).task
    parent = _parent(packet)
    tool_ablated = build_packet_derived_lineage(
        packet, LineageVariant.LEARNED_TOOLS_ABLATED
    )

    assert lineage_start_source(
        parent, task, TaskAnchor.LINEAGE_BODY
    ) != lineage_start_source(tool_ablated, task, TaskAnchor.LINEAGE_BODY)
    assert (
        lineage_start_source(parent, task, TaskAnchor.LINEAGE_BODY)
        == parent.body.active_source
    )


def test_task_baseline_anchor_remains_the_default():
    """Recorded control blocks must stay byte-reproducible."""

    packet = _packet()
    task = generate_embodied_control_task(SEED).task
    complete = build_packet_derived_lineage(packet, LineageVariant.COMPLETE)

    assert lineage_start_source(
        complete, task, TaskAnchor.TASK_BASELINE
    ) == task.baseline_source
    default = execute_memory_guided_task(
        build_packet_derived_lineage(packet, LineageVariant.COMPLETE), task
    )
    explicit = execute_memory_guided_task(
        build_packet_derived_lineage(packet, LineageVariant.COMPLETE),
        task,
        anchor=TaskAnchor.TASK_BASELINE,
    )
    assert default.canonical_json() == explicit.canonical_json()


def test_embodied_anchor_makes_the_migrated_body_pay_off():
    packet = _packet()
    task = generate_embodied_control_task(SEED).task

    complete = execute_memory_guided_task(
        build_packet_derived_lineage(packet, LineageVariant.COMPLETE),
        task,
        anchor=TaskAnchor.LINEAGE_BODY,
    )
    parent = execute_memory_guided_task(
        _parent(packet), task, anchor=TaskAnchor.LINEAGE_BODY
    )
    fresh = execute_memory_guided_task(
        build_fresh_b_lineage(
            task.baseline_source,
            task.function_name,
            state_count=task.state_count,
            accepting_states=task.accepting_states,
            machine=make_development_positive_machine(SEED),
            search_seed=341_000 + SEED,
        ),
        task,
        anchor=TaskAnchor.LINEAGE_BODY,
    )

    assert complete.exact and parent.exact and fresh.exact
    assert complete.total_candidate_evaluations < parent.total_candidate_evaluations
    assert complete.total_candidate_evaluations < fresh.total_candidate_evaluations
