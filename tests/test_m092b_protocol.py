"""M092-B is frozen as a falsifiable pre-search contract, and nothing more."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from check_m092b_protocol import (
    ARMS,
    CONDITIONS,
    DEFAULT_PROTOCOL,
    M092BProtocolError,
    verify_protocol,
)
from metamorphosis.m092_kernel import INSTRUCTION_SET


@pytest.fixture(scope="module")
def protocol() -> dict[str, object]:
    return json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))


def _write(tmp_path: Path, value: object, name: str = "protocol.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_frozen_protocol_verifies_without_search_or_qualification() -> None:
    report = verify_protocol()
    assert report == {
        "status": "verified",
        "checkpoint_digest": "d8bacb1c94dd06da8ceb5ddf2c9a94f8d2bc8c598b307ea1171e3dc7dfc86ce8",
        "arms": 11,
        "conditions": 15,
        "dependency_arrows": 6,
        "candidate_cap": 2_000_000,
        "qualification_read": False,
    }


def test_protocol_schema_is_closed(protocol: dict[str, object], tmp_path: Path) -> None:
    altered = copy.deepcopy(protocol)
    altered["post_freeze_escape_hatch"] = True
    with pytest.raises(M092BProtocolError, match="closed schema"):
        verify_protocol(_write(tmp_path, altered))


def test_arms_conditions_and_dependency_matrix_are_exact(protocol: dict[str, object]) -> None:
    assert tuple(protocol["arms"]) == ARMS
    assert set(protocol["arm_requirements"]) == set(ARMS)
    assert tuple(protocol["conditions"]) == CONDITIONS
    assert len(CONDITIONS) == len(set(CONDITIONS)) == 15
    matrix = protocol["dependency_matrix"]
    assert len(matrix) == 6
    assert {row["ablation"] for row in matrix} <= set(ARMS)


def test_checkpoint_binding_cannot_be_redirected(
    protocol: dict[str, object], tmp_path: Path,
) -> None:
    altered = copy.deepcopy(protocol)
    altered["m092a_checkpoint"]["checkpoint_commit"] = "0" * 40
    with pytest.raises(M092BProtocolError, match="exact M092-A checkpoint"):
        verify_protocol(_write(tmp_path, altered))


def test_k1_candidate_surface_is_a_complete_partition(protocol: dict[str, object]) -> None:
    kernel = protocol["k1_frozen"]
    allowed = set(kernel["candidate_allowed_opcodes"])
    forbidden = set(kernel["candidate_forbidden_opcodes"])
    assert not allowed & forbidden
    assert allowed | forbidden == set(INSTRUCTION_SET)
    assert {"ARG", "GETSLOT", "SETSLOT", "GETINPUT"} <= forbidden


def test_global_certificate_is_not_finite_testing(protocol: dict[str, object]) -> None:
    certificate = protocol["certificate_contract"]
    qualification = protocol["qualification"]
    assert certificate["candidate_supplies_certificate"] is True
    assert certificate["independent_verifier_rechecks_against_program"] is True
    assert certificate["binding"].startswith("program_digest")
    assert any("every original_x >= 0" in item for item in certificate["required_proofs"])
    assert certificate["empirical_execution_is_separate_corroboration"] is True
    assert qualification["theorem_certificate_and_empirical_fields_are_separate"] is True
    assert qualification["empirical_corroboration_domain"] == {
        "inclusive_minimum": 0,
        "inclusive_maximum": 2999,
        "role": "finite adversarial corroboration only; never the global correctness proof",
    }
    assert qualification["hidden_instances_per_family"] == 6
    assert qualification["hidden_value_domain"]["inclusive_minimum"] == 3000
    assert qualification["hidden_value_domain"]["inclusive_maximum"] == 9999


def test_search_is_bounded_and_not_the_impossibility_argument(protocol: dict[str, object]) -> None:
    search = protocol["search"]
    assert search["candidate_cap"] == 2_000_000
    assert search["candidate_program_max_length"] == 14
    assert search["candidate_literal_set"] == [-1, 0, 1]
    assert search["search_failure_is_not_an_impossibility_proof"] is True
    assert search["behaviour_deduplication_is_only_an_optimization"] is True
    assert search["no_finished_candidate_catalogue"] is True
    assert search["certificate_search_bounds"] == {
        "affine_coefficient_inclusive_maximum": 4,
        "affine_coefficient_inclusive_minimum": -4,
        "certificates_examined_per_program_maximum": 4096,
        "constraints_per_loop_maximum": 8,
        "ghost_counters_maximum": 2,
        "loop_headers_maximum": 1,
        "total_certificates_examined_maximum": 2_000_000,
    }


def test_validation_registration_and_downstream_contracts_are_closed(
    protocol: dict[str, object],
) -> None:
    validation = protocol["validation_contract"]
    assert validation["allowed_project_imports"] == [
        "metamorphosis.m092_kernel",
        "metamorphosis.m092_runtime",
    ]
    assert validation["candidate_builder_import_forbidden"] is True
    assert validation["qualification_modules_and_artifacts_forbidden"] is True
    assert validation["verifier_may_not_repair_or_complete_a_certificate"] is True
    assert len(validation["receipt_required_fields"]) == 12

    registration = protocol["registration_contract"]
    assert registration["host_function_or_side_registry_forbidden"] is True
    assert registration["program_bytes_live_inside_the_registered_operation"] is True
    assert registration["substrate_version_increment"] == 1

    downstream = protocol["downstream_language_contract"]
    assert downstream["acquired_primitive_count"] == 1
    assert downstream["body_max_length"] == 4
    assert downstream["parameter_kinds"] == ["slot", "input"]
    assert downstream["body_must_reference_the_acquired_substrate_key"] is True


def test_anti_cheating_fixtures_and_clean_restore_are_binding(protocol: dict[str, object]) -> None:
    scanner = protocol["anti_cheating"]
    assert len(scanner["deliberate_rejection_fixtures"]) == 5
    assert scanner["clean_state_restored_and_redigested_after_fixtures"] is True
    assert scanner["executable_scanner_positive_controls_required"] is True
    assert scanner["truth_table_is_not_semantic_acquisition"] is True


def test_no_result_or_generality_claim_is_precommitted(protocol: dict[str, object]) -> None:
    assert protocol["hypothesis"]["id"] == "H38"
    assert protocol["decision_slot"] == "D062"
    assert all(value is False for value in protocol["claim_boundary"].values())
    assert protocol["integrity"]["m093_not_implemented"] is True
    assert protocol["integrity"]["model_calls_during_qualification"] == 0
    assert protocol["integrity"]["network_calls_during_qualification"] == 0


def test_development_rehearsal_cannot_rehearse_the_target(protocol: dict[str, object]) -> None:
    rehearsal = protocol["development_rehearsal"]
    assert rehearsal["may_not_generate_a_target_semantics_candidate"] is True
    assert rehearsal["uses_qualification_generator"] is False
    assert rehearsal["uses_qualification_values"] is False
    assert "countdown" in rehearsal["target"]
