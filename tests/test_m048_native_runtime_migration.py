from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import inspect
import sys

import pytest

import metamorphosis.m048_runtime_migration as m048
from metamorphosis.m048_runtime_migration import (
    M048_PROTOCOL,
    NativeMigrationError,
    run_m048_native_runtime_migration,
)


@pytest.fixture(scope="module")
def manifest():
    value = run_m048_native_runtime_migration()
    sys.__stdout__.write(f"\nM048_MANIFEST_SHA256={value.digest()}\n")
    sys.__stdout__.flush()
    return value


def test_protocol_fixes_one_integrated_runtime_migration() -> None:
    assert M048_PROTOCOL.source_runtime == "cpython"
    assert M048_PROTOCOL.target_runtime == "node-esm"
    assert M048_PROTOCOL.accepted_post_migration_cycles == 1
    assert M048_PROTOCOL.max_generated_candidates == 8
    assert M048_PROTOCOL.max_candidate_bytes == 131_072
    assert M048_PROTOCOL.node_timeout_seconds == 30.0


def test_protocol_drift_fails_closed() -> None:
    with pytest.raises(NativeMigrationError):
        replace(M048_PROTOCOL, target_runtime="python-wrapper")
    with pytest.raises(NativeMigrationError):
        replace(M048_PROTOCOL, accepted_post_migration_cycles=2)
    with pytest.raises(NativeMigrationError):
        replace(M048_PROTOCOL, max_generated_candidates=9)


def test_migration_continues_the_exact_qualified_m047_lineage(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["source_version"] == 6
    assert mapping["source_retained_case_count"] == 28
    assert len(mapping["source_snapshot_digest"]) == 64
    assert len(mapping["source_body_digest"]) == 64
    assert len(mapping["source_causal_memory_digest"]) == 64


def test_migrated_body_is_real_node_esm_without_python_delegation(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["migration_version"] == 7
    assert mapping["native_module_count_after_migration"] == 9
    assert mapping["semantic_delegation_to_python"] is False
    assert mapping["native_migration_all_retained_passed"] is True
    assert mapping["native_migration_worker_pid"] > 0


def test_pre_migration_skill_remains_useful_after_migration(manifest) -> None:
    assert manifest.to_dict()["pre_migration_mean_tool_reused_after_migration"] is True


def test_native_proposal_is_bounded_and_non_exhaustive(manifest) -> None:
    mapping = manifest.to_dict()
    assert 1 <= mapping["post_migration_generated_candidates"] <= 8
    assert mapping["post_migration_generated_candidates"] < mapping["post_migration_program_space_lower_bound"]
    assert mapping["post_migration_complete_space_enumerated"] is False


def test_post_migration_learning_constructs_a_native_tool(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["post_migration_selected_template"] == "native_composite_max_maximum"
    assert mapping["post_migration_changed_modules"] == [
        "interpretation",
        "selection",
        "tool_max",
    ]
    assert mapping["post_migration_validation_attempts"] >= 1
    assert mapping["post_migration_version"] == 8
    assert mapping["native_module_count_after_learning"] == 10
    assert mapping["native_regression_case_count_after_learning"] == 14
    assert mapping["post_migration_all_retained_passed"] is True


def test_migration_and_learning_have_verified_checkpoints(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["migration_checkpoint"]["version"] == 7
    assert mapping["post_migration_checkpoint"]["version"] == 8
    assert len(mapping["migration_checkpoint"]["combined_digest"]) == 64
    assert len(mapping["post_migration_checkpoint"]["combined_digest"]) == 64


def test_forced_native_fault_restores_exact_version_eight(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["forced_fault_attempted_version"] == 9
    assert mapping["forced_fault_restored_version"] == 8
    assert mapping["forced_fault_exact_restoration"] is True


def test_terminal_median_challenge_fails_closed(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["terminal_action"] == "terminate_insufficient_evidence"
    assert mapping["terminal_rejections"] >= 1
    assert mapping["terminal_body_unchanged"] is True
    assert mapping["final_native_failure_evidence_count"] >= 1


def test_migration_and_post_migration_learning_replay_exactly(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["replay_identical"] is True
    assert len(mapping["final_state_digest"]) == 64
    assert len(manifest.digest()) == 64


def test_node_runtime_exposes_separate_execute_propose_and_validate_modes() -> None:
    script = Path(m048.__file__).with_name("m048_node_runtime.mjs").read_text(encoding="utf-8")
    assert "mode==='execute'" in script
    assert "mode==='propose'" in script
    assert "mode==='validate'" in script
    assert "node:child_process" not in script
    assert "python" not in script.lower()


def test_proposal_call_does_not_receive_hidden_cases() -> None:
    source = inspect.getsource(m048._lineage._propose)
    assert "hidden_cases" not in source
    assert '"public_cases"' in source


def test_validator_does_not_own_transactional_adoption() -> None:
    script = Path(m048.__file__).with_name("m048_node_runtime.mjs").read_text(encoding="utf-8")
    validate_source = script.split("async function validate", 1)[1].split("async function main", 1)[0]
    assert "patch_registry" not in validate_source
    assert "native_journal" not in validate_source
    assert "accepted_task_ids" not in validate_source


def test_claim_boundary_remains_bounded_and_noncanonical(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["claim_scope"] == "bounded_cpython_to_node_modular_lineage_migration_with_one_post_migration_learning_cycle"
    assert mapping["canonical_workflow_authorised"] is False
    assert mapping["repository_write_authority_granted_to_lineage"] is False
