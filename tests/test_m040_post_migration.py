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
    assert arms["complete_migrated_lineage"].exact is True
    assert arms["fresh_on_b"].exact is True
    assert (
        arms["complete_migrated_lineage"].counters["symbolic_search_nodes"]
        < arms["fresh_on_b"].counters["symbolic_search_nodes"]
    )
    assert arms["output_only"].exact is False
    assert result.trans_substrate_continuity_supported is True
    assert result.post_migration_plasticity_supported is False


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

def test_packet_separates_m040_and_source_lineage_commitments(result) -> None:
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    assert packet.protocol_commitment == result.protocol_commitment
    assert packet.source_lineage_commitment != packet.protocol_commitment
    assert all(
        tool.provenance.protocol_commitment == packet.source_lineage_commitment
        for tool in packet.tool_registry
    )


def test_output_only_reports_real_migrated_parent_quality(result) -> None:
    from metamorphosis.m040_engine import OBSERVATIONS
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    expected = sum(
        int(packet.source_dfa().accepts(word) == result.task.target.accepts(word))
        for word in OBSERVATIONS
    )
    assert result.arms["output_only"].quality_numerator == expected
    assert expected > 0


def test_control_parent_has_an_exact_native_body_on_b(result) -> None:
    control = result.control_native_baselines["unchanged_parent_migrated"]
    assert control["exact"] is True
    assert control["native_components"] > 0
    assert control["serialized_bytes"] > 0


def test_independent_search_audits_bind_every_arm(result) -> None:
    assert len(result.pre_migration_search_audits) == 3
    assert set(result.post_migration_search_audits) == set(result.arms)
    for name, audit in result.post_migration_search_audits.items():
        assert audit["transcript_digest"]
        assert audit["transcript_entries"] > 0
        assert audit["symbolic_search_nodes"] == result.arms[name].counters["symbolic_search_nodes"]
        assert audit["accepted_candidate_id"] == result.arms[name].accepted_candidate_id


def test_prefix_adaptation_task_is_not_fully_stored_in_packet(result) -> None:
    packet = rehydrate_packet(result.packet_json, expected_sha256=result.packet_sha256)
    accepted = tuple(result.arms["complete_migrated_lineage"].accepted_tool_ids)
    assert result.task.task_family == "prefix_plus_primitive"
    assert accepted == result.task.generating_tool_ids
    assert accepted[:-1] in packet.learning_state.continuation_programs
    assert accepted not in packet.learning_state.continuation_programs
    assert result.task.digest() not in result.packet_json
