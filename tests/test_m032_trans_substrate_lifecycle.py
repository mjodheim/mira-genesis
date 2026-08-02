from __future__ import annotations

from itertools import product

from metamorphosis.m013e_engine import UnknownSubstrateMigrator
from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import Case, ToolRegistry, VersionedCodeBody
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    TransSubstratePacket,
    execute_trans_substrate_lifecycle,
)


PARITY_BROKEN = """\
def policy(state, symbol):
    return (state + symbol) % 1
"""

PARITY_DEVELOPMENT = (
    Case((0, 1), 1),
    Case((1, 0), 1),
)

PARITY_REGRESSION = (
    Case((0, 0), 0),
    Case((1, 1), 0),
)


def test_rewritten_body_crosses_opaque_substrate_with_learning_state():
    body = VersionedCodeBody("policy", PARITY_BROKEN)
    registry = ToolRegistry()
    machine = make_development_positive_machine(0)
    learning_state = PortableLearningState(
        memory=((0, 1, 1), (1, 0, 1)),
        uncertainty=(3, 1),
        exploration_frontier=((1, 1), (0, 0)),
    )

    outcome = execute_trans_substrate_lifecycle(
        body,
        registry,
        PARITY_DEVELOPMENT,
        PARITY_REGRESSION,
        state_count=2,
        accepting_states=(False, True),
        machine=machine,
        search_seed=32_001,
        learning_state=learning_state,
    )

    assert outcome.committed
    assert outcome.reason == "rewrite_compiled_and_migrated_to_opaque_substrate"
    assert outcome.rewrite.adopted
    assert outcome.source_dfa is not None
    assert outcome.migration is not None
    assert outcome.migration.status == "success"
    assert outcome.migration.body is not None
    assert outcome.packet_json is not None
    assert outcome.packet_sha256 is not None
    assert body.active_source != PARITY_BROKEN
    assert len(registry.learned) == 1

    packet = TransSubstratePacket.from_json(outcome.packet_json)
    assert packet.learning_state == learning_state
    assert packet.sha256() == outcome.packet_sha256
    assert packet.rewrite_passport_sha256 == outcome.rewrite.evidence.passport_sha256

    for length in range(6):
        for word in product((0, 1), repeat=length):
            assert outcome.migration.body.accepts(machine, word) == outcome.source_dfa.accepts(
                word
            )


def test_failed_substrate_discovery_rolls_back_body_and_registry():
    body = VersionedCodeBody("policy", PARITY_BROKEN)
    registry = ToolRegistry()
    machine = make_development_positive_machine(1)

    outcome = execute_trans_substrate_lifecycle(
        body,
        registry,
        PARITY_DEVELOPMENT,
        PARITY_REGRESSION,
        state_count=2,
        accepting_states=(False, True),
        machine=machine,
        search_seed=32_002,
        migrator=UnknownSubstrateMigrator(probe_budget=1),
    )

    assert not outcome.committed
    assert outcome.reason.startswith("opaque_migration_abstained:")
    assert body.active_source == PARITY_BROKEN
    assert body.archive == []
    assert registry.learned == []
    assert outcome.packet_json is None


def test_invalid_finite_compilation_rolls_back_after_m025_adoption():
    source = """\
def policy(state, symbol):
    return state + 0
"""
    body = VersionedCodeBody("policy", source)
    registry = ToolRegistry()
    machine = make_development_positive_machine(2)

    outcome = execute_trans_substrate_lifecycle(
        body,
        registry,
        (Case((0, 0), 1),),
        (Case((0, 1), 1),),
        state_count=2,
        accepting_states=(False, True),
        machine=machine,
        search_seed=32_003,
        max_edits=1,
    )

    assert not outcome.committed
    assert outcome.reason.startswith("compiled_body_invalid:")
    assert outcome.rewrite.adopted
    assert body.active_source == source
    assert body.archive == []
    assert registry.learned == []
    assert outcome.migration is None
    assert outcome.packet_json is None
