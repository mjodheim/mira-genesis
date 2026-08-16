from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m092_adoption import sha256_bytes, validate_candidate_for_adoption
from metamorphosis.m092_certificate_generator import generate_candidate_certificates
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_control_observations import (
    ControlObservationError,
    observe_evolvable_adoption,
    observe_extension_built_but_not_registered,
    observe_substrate_registered_downstream_not_registered,
)
from metamorphosis.m092_kernel import program_digest
from metamorphosis.m092_runtime import RuntimeLanguage
from metamorphosis.m092_substrate_state import SubstrateState

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


def test_candidate_dependent_observations_refuse_before_independent_reproduction(tmp_path: Path) -> None:
    _, language, substrate, base_sha = _base()
    certificate = _certificate()

    with pytest.raises(ControlObservationError, match="independent reproduction"):
        observe_evolvable_adoption(
            reproduction_status="searching",
            program=NEUTRAL_PROGRAM,
            certificate=certificate,
            expected_postcondition=COUNTDOWN_POSTCONDITION,
            base_language=language,
            base_substrate=substrate,
            source_bundle_sha256=base_sha,
            bundle_path=tmp_path / "SUBSTRATE_B.json",
            journal_path=tmp_path / "ADOPTION_TRANSACTION.json",
        )


def test_evolvable_observation_is_derived_from_committed_reload_and_live_execution(tmp_path: Path) -> None:
    _, language, substrate, base_sha = _base()
    result = observe_evolvable_adoption(
        reproduction_status="reproduced",
        program=NEUTRAL_PROGRAM,
        certificate=_certificate(),
        expected_postcondition=COUNTDOWN_POSTCONDITION,
        base_language=language,
        base_substrate=substrate,
        source_bundle_sha256=base_sha,
        bundle_path=tmp_path / "SUBSTRATE_B.json",
        journal_path=tmp_path / "ADOPTION_TRANSACTION.json",
        probe_value=7,
    )

    assert result["arm"] == "evolvable_substrate"
    assert result["passed"] is True
    assert result["facts"] == {
        "complete_causal_chain_enabled": True,
        "qualification_scoring_allowed": True,
        "acquired_substrate_operation_registered": True,
        "downstream_primitive_registered": True,
        "downstream_primitive_references_acquired_operation": True,
    }
    assert result["metrics"]["complete_qualifying_families"] == 0
    assert result["candidate_or_hidden_value_embedded"] is False


def test_built_but_unregistered_observation_keeps_frozen_checkpoint_authoritative() -> None:
    base_bundle, language, substrate, base_sha = _base()
    certificate = _certificate()
    receipt = validate_candidate_for_adoption(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )

    result = observe_extension_built_but_not_registered(
        reproduction_status="reproduced",
        program=NEUTRAL_PROGRAM,
        certificate=certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
        base_language=language,
        base_substrate=substrate,
        source_bundle_sha256=base_sha,
        frozen_substrate_digest=str(base_bundle["expected_substrate_digest"]),
        evolvable_program_digest=program_digest(NEUTRAL_PROGRAM),
        evolvable_receipt_digest=str(receipt["receipt_digest"]),
    )

    assert result["arm"] == "extension_built_but_not_registered"
    assert result["passed"] is True
    assert result["facts"]["extended_state_built"] is True
    assert result["facts"]["executing_substrate_is_frozen_checkpoint"] is True
    assert result["facts"]["extended_substrate_becomes_execution_authority"] is False


def test_built_but_unregistered_preserves_a_causal_mismatch_as_negative_evidence() -> None:
    base_bundle, language, substrate, base_sha = _base()
    certificate = _certificate()
    receipt = validate_candidate_for_adoption(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )

    result = observe_extension_built_but_not_registered(
        reproduction_status="reproduced",
        program=NEUTRAL_PROGRAM,
        certificate=certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
        base_language=language,
        base_substrate=substrate,
        source_bundle_sha256=base_sha,
        frozen_substrate_digest=str(base_bundle["expected_substrate_digest"]),
        evolvable_program_digest="0" * 64,
        evolvable_receipt_digest=str(receipt["receipt_digest"]),
    )

    assert result["facts"]["same_accepted_program_as_evolvable"] is False
    assert result["passed"] is False


def test_substrate_only_observation_executes_acquired_program_without_registering_downstream() -> None:
    _, language, substrate, _ = _base()
    result = observe_substrate_registered_downstream_not_registered(
        reproduction_status="reproduced",
        program=NEUTRAL_PROGRAM,
        certificate=_certificate(),
        expected_postcondition=COUNTDOWN_POSTCONDITION,
        base_language=language,
        base_substrate=substrate,
        probe_value=9,
    )

    assert result["arm"] == "substrate_registered_downstream_not_registered"
    assert result["passed"] is True
    assert result["facts"] == {
        "acquired_substrate_operation_registered": True,
        "acquired_substrate_operation_executable": True,
        "downstream_primitive_built": True,
        "downstream_primitive_registered": False,
        "qualification_scoring_as_evolvable": False,
    }
