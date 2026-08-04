from __future__ import annotations

import json

import pytest

from metamorphosis.m038_journal import decode
from metamorphosis.m040_engine import EVENT_TYPES, run_m040_development
from metamorphosis.m040_packet import M040PacketError
from metamorphosis.m040_packet_verify import rehydrate_packet


@pytest.fixture(scope="module")
def result():
    return run_m040_development(require_replay=True)


def test_complete_lineage_migrates_and_rewrites_after_migration(result) -> None:
    assert result.trans_substrate_continuity_supported is True
    assert result.rollback_restored_exactly is True
    assert result.accepted_tool_was_pre_migration_owned is True
    assert result.replay_supported is True
    assert result.migration["exact"] is True
    assert result.arms["complete_migrated_lineage"].exact is True


def test_post_migration_controls_have_the_committed_direction(result) -> None:
    arms = result.arms
    for name in (
        "fresh_on_b",
        "unchanged_parent_migrated",
        "output_only",
        "learned_tool_ablated",
    ):
        assert arms[name].exact is False
    assert (
        arms["complete_migrated_lineage"].counters["symbolic_search_nodes"]
        < arms["learning_state_ablated"].counters["symbolic_search_nodes"]
    )
    assert result.post_migration_plasticity_supported is True
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    assert tuple(arms["complete_migrated_lineage"].accepted_tool_ids) in packet.learning_state.continuation_programs


def test_packet_requires_the_externally_committed_digest(result) -> None:
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    assert packet.sha256() == result.packet_sha256
    tampered = json.loads(result.packet_json)
    tampered["machine_id"] += "-tampered"
    raw = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    with pytest.raises(M040PacketError, match="externally committed digest"):
        rehydrate_packet(raw, expected_sha256=result.packet_sha256)


def test_packet_carries_no_post_migration_target_or_solution(result) -> None:
    assert "target_digest" not in result.packet_json
    assert result.task.digest() not in result.packet_json
    assert result.arms["complete_migrated_lineage"].accepted_candidate_id not in result.packet_json


def test_task_is_revealed_only_after_packet_commit_and_rehydration(result) -> None:
    event_types = [str(decode(record)["event_type"]) for record in result.journal_records]
    assert set(event_types).issubset(EVENT_TYPES)
    assert event_types.index("PacketCommitted") < event_types.index("PacketRehydrated")
    assert event_types.index("PacketRehydrated") < event_types.index("PostMigrationTaskRevealed")
    assert event_types[-1] == "LineageCompleted"


def test_post_migration_candidate_uses_a_transported_lineage_tool(result) -> None:
    accepted = result.arms["complete_migrated_lineage"]
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    lineage_ids = set(packet.learning_state.lineage_tool_ids)
    assert lineage_ids.intersection(accepted.accepted_tool_ids)


def test_packet_round_trip_preserves_registry_memory_and_native_body(result) -> None:
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    assert packet.to_json() == result.packet_json
    assert packet.learning_state.preferred_tool_ids
    assert packet.learning_state.lineage_tool_ids
    assert packet.tool_registry
    assert packet.opaque_body().to_json() == packet.opaque_body_json


def test_development_result_is_deterministic(result) -> None:
    assert result.digest()
    assert len(result.journal_head) == 64
    assert result.mapping()["journal_records_sha256"]
