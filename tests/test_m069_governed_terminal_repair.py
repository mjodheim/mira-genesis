from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import sys

import pytest

import metamorphosis.m069_governed_terminal_repair as m069


@pytest.fixture(scope="session")
def manifest():
    return m069.run_m069_development()


def test_live_task_bank_matches_the_prepolicy_freeze() -> None:
    attestation = m069.attest_task_bank()
    assert attestation == m069.FROZEN["task_bank_attestation"]
    assert m069.FROZEN["protocol_sha256"] == (
        "2da6abe85d0830f32a67415f1e4faef3316bd1ab1cf3cb461799e3c9a85fb499"
    )
    assert attestation["task_bank_commitment"] == (
        "66b7c7ffe87ecbf5c9cc42d14850b122dd933aa6235647d8dcdf6887464061ed"
    )


def test_complete_frozen_repair_language_is_enumerated_without_duplicates(tmp_path: Path) -> None:
    _goal, source = m069.materialize_task(m069.COMPATIBLE_HANDLES[0], tmp_path)
    candidates = m069.build_repair_candidates(source)
    assert len(candidates) == len(m069.REPLACEMENTS) == 11
    assert len({candidate.digest for candidate in candidates}) == 11
    assert tuple(candidate.digest for candidate in candidates) == tuple(
        sorted(candidate.digest for candidate in candidates)
    )
    assert {candidate.replacement for candidate in candidates} == set(m069.REPLACEMENTS)


def test_uniform_policy_has_no_task_handle_or_hidden_input() -> None:
    parameters = inspect.signature(m069.M069RepairPolicy.propose).parameters
    assert tuple(parameters) == ("self", "goal", "observation", "history")
    policy_source = inspect.getsource(m069.M069RepairPolicy.propose)
    assert "handle" not in policy_source.lower()
    assert "hidden_cases" not in policy_source
    assert "HIDDEN_COMMAND_ID" in policy_source


def test_learner_does_not_import_or_read_the_frozen_evaluator_source() -> None:
    learner_source = Path(m069.__file__).read_text(encoding="utf-8")
    assert "import metamorphosis.m069_terminal_task_bank" not in learner_source
    assert "TASK_RUNTIME_PATH.read_text" not in learner_source
    assert "TASK_RUNTIME_PATH.read_bytes" not in learner_source
    assert "open(TASK_RUNTIME_PATH" not in learner_source


def test_one_unchanged_policy_repairs_every_compatible_task(manifest) -> None:
    value = manifest.to_dict()
    assert value["compatible_tasks_completed"] == value["compatible_task_count"] == 4
    assert value["same_policy_for_every_task"] is True
    assert set(value["task_results"]) == set(m069.TASK_HANDLES)
    expected_sources = {
        "workcell-13a9d2": "8e6bf3da47e4bba9db67b783c41916da0ad841a8e66899410308db3af5c29ed7",
        "workcell-4c70be": "56c8772fb806012ceffa950d7600d4f0a5602fca35a9f9b8cc30e9eabfd3b376",
        "workcell-806f41": "f9384c421f36d0153123f806be5299e29ef85713e00cc9fce660bc08511eee8e",
        "workcell-b5287f": "e87a1bd28802eda1c4a5da824d87650c10291479ea28d1ba262de237c7c760e8",
    }
    for handle, expected_digest in expected_sources.items():
        result = value["task_results"][handle]
        assert result["status"] == "completed"
        assert result["succeeded"] is True
        assert result["steps"] == 25
        assert result["candidate_count"] == 11
        assert result["public_survivor_count"] == 1
        assert result["write_actions"] == 12
        assert result["public_process_actions"] == 11
        assert result["hidden_process_actions"] == 1
        assert result["hidden_output_disclosed"] is False
        assert result["final_source_sha256"] == expected_digest


def test_incompatible_task_is_refused_before_mutation_or_process(manifest) -> None:
    value = manifest.to_dict()
    result = value["task_results"][m069.INCOMPATIBLE_HANDLE]
    assert result["status"] == "policy_refused"
    assert result["steps"] == 1
    assert result["candidate_count"] == 0
    assert result["refusal_reason"] == "repair_slot_absent"
    assert result["initial_source_sha256"] == result["final_source_sha256"]
    assert result["write_actions"] == 0
    assert result["public_process_actions"] == 0
    assert result["hidden_process_actions"] == 0
    assert value["incompatible_refusal_before_write"] is True
    assert value["incompatible_refusal_before_process"] is True


def test_every_preregistered_control_rejects(manifest) -> None:
    controls = manifest.to_dict()["controls"]
    assert set(controls) == {
        "unmodified_source_fails_public",
        "first_candidate_without_observation_fails_public",
        "write_authority_ablation_refuses",
        "underdeclared_authority_refuses_before_body",
        "path_traversal_rejected_without_outside_change",
        "unknown_command_and_dynamic_arguments_rejected",
        "parent_secret_not_inherited",
        "hidden_output_not_disclosed",
        "incompatible_task_policy_refusal_before_mutation",
        "policy_does_not_inspect_evaluator_source",
    }
    assert set(controls["unmodified_source_fails_public"]) == set(m069.COMPATIBLE_HANDLES)
    assert all(controls["unmodified_source_fails_public"].values())
    assert set(controls["first_candidate_without_observation_fails_public"]) == set(
        m069.COMPATIBLE_HANDLES
    )
    assert all(controls["first_candidate_without_observation_fails_public"].values())
    assert all(
        result is True for name, result in controls.items()
        if name not in {
            "unmodified_source_fails_public",
            "first_candidate_without_observation_fails_public",
        }
    )


def test_manifest_keeps_authority_and_claim_boundaries(manifest) -> None:
    value = manifest.to_dict()
    assert value["real_filesystem_process_body"] is True
    assert value["finite_supplied_repair_language"] is True
    assert value["evidence_memory_event_count"] == 7
    assert value["evidence_memory_digest"] == (
        "59a277880453a997c60880e8eb357ddc50fcec1185303e967793de9c80d2e086"
    )
    false_fields = (
        "open_ended_code_generation",
        "policy_has_hidden_input",
        "policy_reads_evaluator_source",
        "external_task_authorship",
        "operating_system_security_sandbox",
        "network_authority",
        "repository_write_authority",
        "credential_authority",
        "deployment_authority",
        "permission_change_authority",
        "physical_actuation_authority",
        "general_intelligence_claimed",
        "canonical",
    )
    assert all(value[field] is False for field in false_fields)
    assert manifest.digest() == "c5c807017f05788dc22d21f88192279b9f177b648403b2cc41ca149b25ff6289"


def test_manifest_is_byte_reproducible_across_processes(manifest) -> None:
    command = (
        "from metamorphosis.m069_governed_terminal_repair import run_m069_development; "
        "print(run_m069_development().to_bytes().decode())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command], check=True, capture_output=True, text=True, timeout=120,
    )
    assert json.loads(completed.stdout) == manifest.to_dict()
