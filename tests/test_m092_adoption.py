from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m092_adoption import (
    AdoptionError,
    BEHAVIOUR_FAULT_PROGRAM,
    build_extended_bundle,
    commit_adoption_transaction,
    dependency_ablation,
    downstream_body,
    downstream_primitive_id,
    execute_downstream,
    load_committed_bundle,
    operation_key,
    restore_exact,
    sha256_bytes,
    validate_candidate_for_adoption,
)
from metamorphosis.m092_candidate_validation import validate_candidate_artifacts
from metamorphosis.m092_certificate_generator import generate_candidate_certificates
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_kernel import program_digest
from metamorphosis.m092_runtime import RefusalCode, RuntimeLanguage, SubstrateError
from metamorphosis.m092_substrate_state import SubstrateState, execute_from_state

BASE = Path("experiments/M092/SUBSTRATE_A.json")
NEUTRAL_PROGRAM = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _base() -> tuple[dict[str, object], RuntimeLanguage, SubstrateState, str]:
    raw = BASE.read_bytes()
    bundle = json.loads(raw)
    language = RuntimeLanguage.from_dict(bundle["language"])
    substrate = SubstrateState.from_dict(bundle["substrate"])
    assert substrate.digest() == bundle["expected_substrate_digest"]
    return bundle, language, substrate, sha256_bytes(raw)


def _certificate() -> dict[str, object]:
    return next(generate_candidate_certificates(NEUTRAL_PROGRAM, COUNTDOWN_POSTCONDITION, limit=64))


def _adopted_bundle() -> tuple[dict[str, object], dict[str, object], RuntimeLanguage, SubstrateState]:
    _, language, substrate, base_sha = _base()
    certificate = _certificate()
    receipt = validate_candidate_for_adoption(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )
    bundle = build_extended_bundle(
        language,
        substrate,
        NEUTRAL_PROGRAM,
        receipt=receipt,
        source_bundle_sha256=base_sha,
    )
    return bundle, receipt, language, substrate


def test_operation_and_downstream_ids_are_content_addressed_by_their_own_contracts() -> None:
    digest = program_digest(NEUTRAL_PROGRAM)
    assert operation_key(NEUTRAL_PROGRAM) == f"ACQUIRED_{digest}"
    primitive_id = downstream_primitive_id(NEUTRAL_PROGRAM)
    assert primitive_id.startswith("M092_USE_")
    assert len(primitive_id.removeprefix("M092_USE_")) == 64
    assert primitive_id != f"M092_USE_{digest}"


def test_adoption_recomputes_scanner_and_global_certificate() -> None:
    certificate = _certificate()
    clean = validate_candidate_artifacts(NEUTRAL_PROGRAM, certificate)
    assert clean["accepted"] is True
    receipt = validate_candidate_for_adoption(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )
    assert receipt["program_digest"] == program_digest(NEUTRAL_PROGRAM)
    assert receipt["candidate_executed_during_validation"] is False
    assert receipt["qualification_read_during_validation"] is False

    tampered = dict(certificate)
    tampered["program_digest"] = "0" * 64
    with pytest.raises((AdoptionError, ValueError)):
        validate_candidate_for_adoption(
            NEUTRAL_PROGRAM,
            tampered,
            expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_build_but_not_registered_is_inaccessible() -> None:
    bundle, _, base_language, _ = _adopted_bundle()
    substrate = SubstrateState.from_dict(bundle["substrate"])
    with pytest.raises(SubstrateError) as error:
        execute_from_state(
            ((str(bundle["primitive_id"]), (0, 0)),),
            (0,),
            base_language,
            substrate,
        )
    assert error.value.code == RefusalCode.UNDEFINED_PRIMITIVE


def test_extended_state_and_language_are_real_and_dependency_bound() -> None:
    bundle, _, _, base_substrate = _adopted_bundle()
    language = RuntimeLanguage.from_dict(bundle["language"])
    substrate = SubstrateState.from_dict(bundle["substrate"])
    key = str(bundle["operation_key"])
    primitive_id = str(bundle["primitive_id"])

    operation = substrate.operation(key)
    assert operation is not None
    assert operation.origin == "acquired"
    assert operation.program == NEUTRAL_PROGRAM
    assert substrate.substrate_version == base_substrate.substrate_version + 1
    assert substrate.permitted_capabilities == base_substrate.permitted_capabilities
    assert substrate.forbidden_capabilities == base_substrate.forbidden_capabilities
    primitive = language.definition(primitive_id)
    assert primitive is not None
    assert primitive.body == downstream_body(NEUTRAL_PROGRAM)
    assert any(step[0] == key for step in primitive.body)
    assert execute_downstream(language, substrate, primitive_id, 0)[0] == 0
    assert execute_downstream(language, substrate, primitive_id, 7)[0] == 0


def test_transaction_fresh_reload_and_journal_is_not_execution_authority(tmp_path: Path) -> None:
    bundle, _, _, _ = _adopted_bundle()
    bundle_path = tmp_path / "SUBSTRATE_B.json"
    journal_path = tmp_path / "ADOPTION_TRANSACTION.json"
    committed = commit_adoption_transaction(bundle_path, journal_path, bundle)
    assert committed["phase"] == "COMMITTED"

    language, substrate = load_committed_bundle(bundle_path, journal_path)
    assert execute_downstream(language, substrate, str(bundle["primitive_id"]), 4)[0] == 0

    bundle_path.write_text(journal_path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(AdoptionError):
        load_committed_bundle(bundle_path, journal_path)


def test_registered_dependency_ablation_removes_the_capability() -> None:
    bundle, _, _, _ = _adopted_bundle()
    language, ablated = dependency_ablation(bundle)
    with pytest.raises(SubstrateError) as error:
        execute_downstream(language, ablated, str(bundle["primitive_id"]), 0)
    assert error.value.code == RefusalCode.UNKNOWN_OPERATION


def test_fault_changes_live_behaviour_then_rollback_restores_exact_bytes(tmp_path: Path) -> None:
    bundle, _, _, _ = _adopted_bundle()
    bundle_path = tmp_path / "SUBSTRATE_B.json"
    journal_path = tmp_path / "ADOPTION_TRANSACTION.json"
    commit_adoption_transaction(bundle_path, journal_path, bundle)

    preserved = bundle_path.read_bytes()
    preserved_sha = sha256_bytes(preserved)
    language, substrate = load_committed_bundle(bundle_path, journal_path)
    primitive_id = str(bundle["primitive_id"])
    before = execute_downstream(language, substrate, primitive_id, 0)
    assert before[0] == 0

    corrupted = substrate.replacing(str(bundle["operation_key"]), BEHAVIOUR_FAULT_PROGRAM)
    faulty = dict(bundle)
    faulty["substrate"] = corrupted.to_dict()
    faulty["substrate_digest"] = corrupted.digest()
    after_fault = execute_downstream(language, corrupted, primitive_id, 0)
    assert after_fault[0] == 1
    assert after_fault != before

    bundle_path.write_text(json.dumps(faulty, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(AdoptionError):
        load_committed_bundle(bundle_path, journal_path)

    restored_sha = restore_exact(bundle_path, preserved)
    assert restored_sha == preserved_sha
    assert bundle_path.read_bytes() == preserved
    restored_language, restored_substrate = load_committed_bundle(bundle_path, journal_path)
    assert execute_downstream(restored_language, restored_substrate, primitive_id, 0) == before
