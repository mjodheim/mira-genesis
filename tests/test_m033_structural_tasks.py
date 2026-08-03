from __future__ import annotations

from functools import lru_cache

import pytest

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
from metamorphosis.m033_evaluation import exact_dfa_match
from metamorphosis.m033_post_migration_plasticity import (
    LineageVariant,
    build_fresh_b_lineage,
    build_packet_derived_lineage,
    execute_control_task,
)
from metamorphosis.m033_structural_tasks import (
    COMBINED_CONTROL_SEED_START,
    EMBODIED_CONTROL_SEED_START,
    STRUCTURAL_CONTROL_SEED_START,
    generate_combined_control_task,
    generate_structural_control_task,
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
        PRE_REWRITE_DEVELOPMENT,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(35),
        search_seed=335_001,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    assert outcome.committed and outcome.packet_json is not None
    return outcome.packet_json


def test_structural_generator_rejects_all_other_seed_blocks():
    with pytest.raises(ValueError, match="2048 through 3071"):
        generate_structural_control_task(STRUCTURAL_CONTROL_SEED_START - 1)
    with pytest.raises(ValueError, match="2048 through 3071"):
        generate_structural_control_task(COMBINED_CONTROL_SEED_START)


def test_four_templates_are_deterministic_and_distinct():
    records = [
        generate_structural_control_task(STRUCTURAL_CONTROL_SEED_START + offset)
        for offset in range(4)
    ]

    assert {record.template_id for record in records} == {0, 1, 2, 3}
    assert len({record.sha256() for record in records}) == 4
    assert all(
        record.canonical_json()
        == generate_structural_control_task(
            STRUCTURAL_CONTROL_SEED_START + offset
        ).canonical_json()
        for offset, record in enumerate(records)
    )


def test_combined_block_is_disjoint_deterministic_and_structurally_complete():
    with pytest.raises(ValueError, match="3072 through 4095"):
        generate_combined_control_task(COMBINED_CONTROL_SEED_START - 1)
    with pytest.raises(ValueError, match="3072 through 4095"):
        generate_combined_control_task(EMBODIED_CONTROL_SEED_START)

    records = [
        generate_combined_control_task(COMBINED_CONTROL_SEED_START + offset)
        for offset in range(4)
    ]
    assert {record.template_id for record in records} == {0, 1, 2, 3}
    assert len({record.sha256() for record in records}) == 4
    assert all(
        '"version":"m033-combined-control-task/1"' in record.canonical_json()
        for record in records
    )
    assert all(
        record.canonical_json()
        == generate_combined_control_task(
            COMBINED_CONTROL_SEED_START + offset
        ).canonical_json()
        for offset, record in enumerate(records)
    )


def test_transported_tool_never_encodes_a_complete_structural_answer():
    complete = build_packet_derived_lineage(_packet(), LineageVariant.COMPLETE)
    learned = complete.registry.learned[0]

    for offset in range(4):
        task = generate_structural_control_task(
            STRUCTURAL_CONTROL_SEED_START + offset
        ).task
        replayed_source = apply_patch(task.baseline_source, learned.operations)
        try:
            replayed_dfa = compile_policy_to_dfa(
                replayed_source,
                task.function_name,
                state_count=task.state_count,
                accepting_states=task.accepting_states,
            )
        except ValueError:
            continue
        assert not exact_dfa_match(replayed_dfa, task.target_dfa)


def test_complete_and_fresh_solve_every_structural_template_without_forcing_advantage():
    comparisons: list[tuple[int, int]] = []
    for offset in range(4):
        record = generate_structural_control_task(
            STRUCTURAL_CONTROL_SEED_START + offset
        )
        task = record.task
        complete = build_packet_derived_lineage(_packet(), LineageVariant.COMPLETE)
        fresh = build_fresh_b_lineage(
            task.baseline_source,
            task.function_name,
            state_count=task.state_count,
            accepting_states=task.accepting_states,
            machine=make_development_positive_machine(40 + offset),
            search_seed=336_000 + offset,
        )

        complete_result = execute_control_task(complete, task)
        fresh_result = execute_control_task(fresh, task)

        assert complete_result.exact, record.template_id
        assert fresh_result.exact, record.template_id
        assert complete_result.adopted
        assert fresh_result.adopted
        comparisons.append(
            (
                complete_result.candidates_evaluated,
                fresh_result.candidates_evaluated,
            )
        )

    assert any(complete < fresh for complete, fresh in comparisons)
    assert any(complete >= fresh for complete, fresh in comparisons)
