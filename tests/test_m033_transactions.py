from __future__ import annotations

from functools import lru_cache

from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import Case, ToolRegistry, VersionedCodeBody
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_post_migration_plasticity import (
    ControlTaskFamily,
    LineageVariant,
    build_packet_derived_lineage,
    generate_control_task,
)
from metamorphosis.m033_transactions import execute_post_migration_transaction


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
        machine=make_development_positive_machine(34),
        search_seed=334_001,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    assert outcome.committed and outcome.packet_json is not None
    return outcome.packet_json


def _lineage():
    return build_packet_derived_lineage(_packet(), LineageVariant.COMPLETE)


def test_failed_post_migration_regression_restores_every_lineage_surface():
    lineage = _lineage()
    task = generate_control_task(1035, ControlTaskFamily.POSITIVE_TOOL)
    before = lineage.canonical_snapshot()
    before_sha256 = lineage.snapshot_sha256()

    transaction = execute_post_migration_transaction(
        lineage,
        task,
        (Case((0, 0), 2),),
        memory_guided=True,
    )

    assert not transaction.committed
    assert transaction.reason == "post_migration_regression_gate_failed"
    assert transaction.regression_passed == 0
    assert transaction.regression_total == 1
    assert transaction.lineage_before_sha256 == before_sha256
    assert transaction.lineage_after_sha256 == before_sha256
    assert lineage.canonical_snapshot() == before
    assert lineage.snapshot_sha256() == before_sha256


def test_successful_post_migration_transaction_commits_state_and_tools():
    lineage = _lineage()
    task = generate_control_task(1036, ControlTaskFamily.POSITIVE_TOOL)
    before_sha256 = lineage.snapshot_sha256()
    learned_before = len(lineage.registry.learned)

    transaction = execute_post_migration_transaction(
        lineage,
        task,
        task.development_cases,
        memory_guided=True,
    )

    assert transaction.committed
    assert transaction.reason == "post_migration_rewrite_committed"
    assert transaction.regression_passed == transaction.regression_total
    assert transaction.lineage_before_sha256 == before_sha256
    assert transaction.lineage_after_sha256 == lineage.snapshot_sha256()
    assert transaction.lineage_after_sha256 != before_sha256
    assert len(lineage.registry.learned) >= learned_before
    assert lineage.learning_state.memory[-1][0] == task.seed
    assert lineage.construction_cost.rewrite_candidate_evaluations > 0


def test_identical_transactions_are_byte_deterministic():
    task = generate_control_task(1037, ControlTaskFamily.POSITIVE_TOOL)
    first = execute_post_migration_transaction(
        _lineage(),
        task,
        task.development_cases,
        memory_guided=True,
    )
    second = execute_post_migration_transaction(
        _lineage(),
        task,
        task.development_cases,
        memory_guided=True,
    )

    assert first.canonical_json() == second.canonical_json()
