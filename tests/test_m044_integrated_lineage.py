from __future__ import annotations

from dataclasses import replace
import sys

import pytest

from metamorphosis.m044_integrated_lineage import (
    IntegratedLineageError,
    M044_PROTOCOL,
    run_m044_integrated_lineage,
)


@pytest.fixture(scope="module")
def manifest():
    value = run_m044_integrated_lineage()
    # Bypass pytest capture so both CI matrices expose the exact cross-version identity.
    sys.__stdout__.write(f"\nM044_MANIFEST_SHA256={value.digest()}\n")
    sys.__stdout__.flush()
    return value


def test_protocol_is_one_fixed_accelerated_experiment() -> None:
    assert M044_PROTOCOL.pre_migration_cycles == 2
    assert M044_PROTOCOL.post_migration_cycles == 1
    assert M044_PROTOCOL.maximum_states == 6
    assert M044_PROTOCOL.opaque_family == 0


def test_protocol_drift_fails_closed() -> None:
    with pytest.raises(IntegratedLineageError):
        replace(M044_PROTOCOL, pre_migration_cycles=3)
    with pytest.raises(IntegratedLineageError):
        replace(M044_PROTOCOL, maximum_states=7)


def test_one_lineage_grows_across_three_accepted_cycles(manifest) -> None:
    assert [cycle.phase for cycle in manifest.cycles] == [
        "pre_migration",
        "pre_migration",
        "post_migration",
    ]
    assert [cycle.parent_states for cycle in manifest.cycles] == [2, 3, 4]
    assert [cycle.adopted_states for cycle in manifest.cycles] == [3, 4, 5]
    assert manifest.final_body_states == 5


def test_later_cycles_reuse_an_acquired_tool_pattern(manifest) -> None:
    assert manifest.cycles[0].reused_prior_tool_pattern is False
    assert manifest.cycles[1].reused_prior_tool_pattern is True
    assert manifest.cycles[2].reused_prior_tool_pattern is True
    assert manifest.cycles[1].reused_prior_tool_trace_digest is not None
    assert manifest.cycles[2].reused_prior_tool_trace_digest is not None


def test_migration_precedes_and_feeds_post_migration_learning(manifest) -> None:
    assert manifest.post_migration_parent_from_native is True
    assert manifest.native_reconstruction_exact is True
    assert manifest.native_program_changed_after_learning is True
    assert manifest.first_native_program_digest != manifest.updated_native_program_digest
    assert manifest.first_migration_bundle_digest != manifest.updated_migration_bundle_digest


def test_complete_lineage_state_survives_into_final_native_body(manifest) -> None:
    assert manifest.final_tool_count == 3
    assert manifest.final_learning_trace_count == 3
    assert manifest.final_journal_entries == 3
    assert manifest.cycles[-1].registered_tool_count == 3
    assert manifest.cycles[-1].learning_trace_count == 3
    assert manifest.cycles[-1].journal_entries == 3


def test_forced_post_migration_fault_restores_exact_checkpoint(manifest) -> None:
    assert manifest.rollback_exact is True
    assert manifest.rollback_attempted_version == 4
    assert manifest.rollback_restored_version == 3


def test_controls_remain_observable_without_expanding_the_gate_sequence(manifest) -> None:
    assert all(cycle.tool_ablated_nodes_seen > 0 for cycle in manifest.cycles)
    assert all(cycle.learning_ablated_nodes_seen > 0 for cycle in manifest.cycles)
    assert any(cycle.control_surface_distinct for cycle in manifest.cycles)


def test_complete_replay_is_byte_identical(manifest) -> None:
    assert manifest.replay_identical is True
    assert len(manifest.to_bytes()) > 0
    assert len(manifest.digest()) == 64


def test_claim_boundary_stays_bounded_and_noncanonical(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["claim_scope"] == "bounded_integrated_development_lineage"
    assert mapping["selected_seed"] is None
    assert mapping["canonical_workflow_authorised"] is False
    assert mapping["q1_to_q5_reused_without_reimplementation"] is True
