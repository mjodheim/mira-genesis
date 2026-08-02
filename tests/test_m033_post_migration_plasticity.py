from __future__ import annotations

from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import Case, ToolRegistry, VersionedCodeBody
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_post_migration_plasticity import (
    LineageVariant,
    build_packet_derived_lineage,
    build_packet_derived_lineages,
)


PARITY_BROKEN = """\
def policy(state, symbol):
    return (state + symbol) % 1
"""

PARITY_DEVELOPMENT = (
    Case((0, 0), 0),
    Case((0, 1), 1),
    Case((1, 0), 1),
    Case((1, 1), 0),
)

PARITY_REGRESSION = (
    Case((0, 0), 0),
    Case((1, 1), 0),
)

LEARNING_STATE = PortableLearningState(
    memory=((0, 1, 1), (1, 0, 1)),
    uncertainty=(3, 1),
    exploration_frontier=((1, 1), (0, 0)),
)


def _packet() -> str:
    outcome = execute_trans_substrate_lifecycle(
        VersionedCodeBody("policy", PARITY_BROKEN),
        ToolRegistry(),
        PARITY_DEVELOPMENT,
        PARITY_REGRESSION,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(0),
        search_seed=33_001,
        learning_state=LEARNING_STATE,
    )
    assert outcome.committed and outcome.packet_json is not None
    return outcome.packet_json


def test_packet_derived_lineages_differ_only_at_declared_surfaces():
    lineages = build_packet_derived_lineages(_packet())
    complete = lineages[LineageVariant.COMPLETE]
    output_only = lineages[LineageVariant.OUTPUT_ONLY]
    state_ablated = lineages[LineageVariant.LEARNING_STATE_ABLATED]
    tools_ablated = lineages[LineageVariant.LEARNED_TOOLS_ABLATED]

    assert {lineage.source_packet_sha256 for lineage in lineages.values()} == {
        complete.source_packet_sha256
    }
    assert all(lineage.body.active_source == complete.body.active_source for lineage in lineages.values())
    assert all(lineage.body.archive == complete.body.archive for lineage in lineages.values())
    assert all(lineage.source_dfa == complete.source_dfa for lineage in lineages.values())
    assert all(lineage.opaque_body == complete.opaque_body for lineage in lineages.values())

    assert complete.learning_state == LEARNING_STATE
    assert output_only.learning_state == LEARNING_STATE
    assert tools_ablated.learning_state == LEARNING_STATE
    assert state_ablated.learning_state == PortableLearningState()

    assert len(complete.registry.learned) == 1
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


def test_output_only_snapshot_is_stable_without_learning_actions():
    lineage = build_packet_derived_lineage(_packet(), LineageVariant.OUTPUT_ONLY)
    before = lineage.snapshot_sha256()

    assert not lineage.can_rewrite
    assert not lineage.can_update_learning_state
    assert lineage.snapshot_sha256() == before
