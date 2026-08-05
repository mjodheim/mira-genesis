from __future__ import annotations

from dataclasses import replace
import inspect
import sys

import pytest

import metamorphosis.m046_search as proposal_module
from metamorphosis.m046_scalable_lineage import (
    M046_PROTOCOL,
    ScalableLineageError,
    run_m046_scalable_lineage,
)


@pytest.fixture(scope="module")
def manifest():
    value = run_m046_scalable_lineage()
    sys.__stdout__.write(f"\nM046_MANIFEST_SHA256={value.digest()}\n")
    sys.__stdout__.flush()
    return value


def test_protocol_is_one_fixed_integrated_scalable_experiment() -> None:
    assert M046_PROTOCOL.accepted_cycles == 6
    assert M046_PROTOCOL.resources.max_trace_depth == 3
    assert M046_PROTOCOL.resources.max_generated_candidates == 48
    assert M046_PROTOCOL.resources.max_observations == 128
    assert M046_PROTOCOL.terminal_required_growth == 2


def test_protocol_drift_fails_closed() -> None:
    with pytest.raises(ScalableLineageError):
        replace(M046_PROTOCOL, accepted_cycles=5)
    with pytest.raises(ScalableLineageError):
        replace(
            M046_PROTOCOL,
            resources=replace(
                M046_PROTOCOL.resources,
                max_generated_candidates=49,
            ),
        )


def test_proposal_generator_has_no_exact_target_validation_surface() -> None:
    source = inspect.getsource(proposal_module)
    assert "_evaluate_exact" not in source
    assert "exact_mealy_equivalence" not in source
    assert "validate_candidate_disposably" not in source


def test_one_lineage_completes_six_accepted_cycles(manifest) -> None:
    assert manifest.accepted_cycle_count == 6
    assert [cycle.ordinal for cycle in manifest.cycles] == [1, 2, 3, 4, 5, 6]
    assert [cycle.parent_states for cycle in manifest.cycles] == [2, 3, 4, 5, 6, 7]
    assert [cycle.adopted_states for cycle in manifest.cycles] == [3, 4, 5, 6, 7, 8]
    assert manifest.final_body_states == 8
    assert manifest.final_tool_count == 6
    assert manifest.final_learning_trace_count == 6
    assert manifest.final_journal_entries == 6


def test_hidden_task_families_require_generator_selected_transforms(manifest) -> None:
    assert [cycle.hidden_family for cycle in manifest.cycles] == [
        "split_emit_1",
        "split_emit_2",
        "split_emit_1",
        "split_emit_2",
        "split_emit_1",
        "split_emit_2",
    ]
    assert [cycle.selected_template for cycle in manifest.cycles] == [
        "split_emit_1",
        "split_emit_2",
        "split_emit_1",
        "split_emit_2",
        "split_emit_1",
        "split_emit_2",
    ]


def test_every_search_is_explicitly_non_exhaustive(manifest) -> None:
    assert manifest.all_searches_non_exhaustive is True
    assert all(
        cycle.complete_candidate_space_enumerated is False
        for cycle in manifest.cycles
    )
    assert all(
        0 < cycle.generated_candidates < cycle.candidate_space_lower_bound
        for cycle in manifest.cycles
    )
    assert all(
        cycle.exploration_fraction_ppm
        <= M046_PROTOCOL.maximum_exploration_fraction_ppm
        for cycle in manifest.cycles
    )
    assert (
        manifest.maximum_observed_exploration_fraction_ppm
        <= M046_PROTOCOL.maximum_exploration_fraction_ppm
    )


def test_time_memory_observation_and_compute_budgets_are_respected(manifest) -> None:
    budget = M046_PROTOCOL.resources
    assert manifest.all_resource_budgets_respected is True
    assert all(cycle.time_budget_respected for cycle in manifest.cycles)
    assert all(
        cycle.observations_used <= budget.max_observations
        for cycle in manifest.cycles
    )
    assert all(
        cycle.generated_candidates <= budget.max_generated_candidates
        for cycle in manifest.cycles
    )
    assert all(
        cycle.independent_validation_attempts <= budget.max_validation_attempts
        for cycle in manifest.cycles
    )
    assert all(
        cycle.working_memory_bytes <= budget.max_working_memory_bytes
        for cycle in manifest.cycles
    )
    assert manifest.final_causal_memory_bytes <= budget.max_causal_memory_bytes


def test_approximate_search_is_followed_by_two_independent_validation_layers(
    manifest,
) -> None:
    assert all(
        cycle.task_side_independent_validation for cycle in manifest.cycles
    )
    assert all(
        cycle.adoption_validator_disposable for cycle in manifest.cycles
    )
    assert all(
        cycle.independent_validation_attempts > 0
        for cycle in manifest.cycles
    )


def test_causal_memory_retains_successes_failures_and_changes_later_search(
    manifest,
) -> None:
    assert manifest.final_causal_memory_episodes == 7
    assert manifest.final_causal_failure_evidence_count > 0
    assert manifest.causal_memory_reuse_cycles >= 5
    assert all(cycle.reused_causal_memory for cycle in manifest.cycles[1:])
    assert (
        manifest.cycles[-1].causal_failure_evidence_count
        >= manifest.cycles[0].causal_failure_evidence_count
    )


def test_registered_tools_are_reused_on_later_cycles(manifest) -> None:
    assert manifest.tool_reuse_cycles >= 4
    assert any(
        cycle.reused_registered_tool_effects
        for cycle in manifest.cycles[2:]
    )


def test_every_success_creates_a_verified_combined_checkpoint(manifest) -> None:
    assert manifest.checkpoints_verified is True
    assert len(manifest.checkpoints) == 6
    assert [checkpoint.version for checkpoint in manifest.checkpoints] == [
        1, 2, 3, 4, 5, 6
    ]
    assert all(len(checkpoint.combined_digest) == 64 for checkpoint in manifest.checkpoints)


def test_forced_fault_restores_lineage_and_causal_memory_exactly(manifest) -> None:
    rollback = manifest.rollback
    assert rollback.lineage_exact_restoration is True
    assert rollback.combined_checkpoint_exact_restoration is True
    assert rollback.memory_unchanged is True
    assert rollback.attempted_version == 7
    assert rollback.restored_version == 6
    assert rollback.combined_checkpoint_before == rollback.combined_checkpoint_after


def test_insufficient_proof_terminates_without_changing_the_body(manifest) -> None:
    terminal = manifest.terminal
    assert terminal.required_growth == 2
    assert terminal.stop_action == "terminate_insufficient_evidence"
    assert terminal.explicit_insufficient_evidence_termination is True
    assert terminal.body_unchanged is True
    assert terminal.parent_snapshot_digest == terminal.final_snapshot_digest
    assert terminal.exact_rejections > 0


def test_complete_replay_is_byte_identical(manifest) -> None:
    assert manifest.replay_identical is True
    assert len(manifest.to_bytes()) > 0
    assert len(manifest.digest()) == 64


def test_claim_boundary_stays_bounded_development_and_noncanonical(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["claim_scope"] == (
        "bounded_scalable_non_exhaustive_development_lineage"
    )
    assert mapping["selected_seed"] is None
    assert mapping["canonical_workflow_authorised"] is False
    assert (
        mapping["m043_transaction_and_validator_reused_without_reimplementation"]
        is True
    )
