from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from metamorphosis.m092_adoption import (
    downstream_primitive_id,
    extend_language,
    extend_substrate,
    operation_key,
)
from metamorphosis.m092_adoption_checkpoint import load_frozen_base
from metamorphosis.m092_kernel import program_digest
from metamorphosis.m092_qualification_batch import QualificationBatchError, run_evolvable_qualification_batch
from metamorphosis.m092_qualification_contract import execution_contract
from metamorphosis.m092_qualification_generator import materialize_hidden_qualification
from metamorphosis.m092_runtime import canonical_bytes


PROTOCOL = Path("experiments/M092/PROTOCOL.json")
NEUTRAL_IDENTITY_PROGRAM = (
    ("SPOP", 0),
    ("SPUSH", 0),
    ("HALT",),
)


def _neutral_extended_runtime():
    base_language, base_substrate, _, _ = load_frozen_base()
    key = operation_key(NEUTRAL_IDENTITY_PROGRAM)
    primitive_id = downstream_primitive_id(NEUTRAL_IDENTITY_PROGRAM)
    receipt = {
        "program_digest": program_digest(NEUTRAL_IDENTITY_PROGRAM),
        "operation_key": key,
        "primitive_id": primitive_id,
    }
    substrate = extend_substrate(base_substrate, NEUTRAL_IDENTITY_PROGRAM, receipt=receipt)
    language = extend_language(base_language, substrate, NEUTRAL_IDENTITY_PROGRAM, receipt=receipt)
    return language, substrate, primitive_id


def _synthetic_material(language, substrate):
    return materialize_hidden_qualification(
        PROTOCOL.read_bytes(),
        extended_substrate_digest=substrate.digest(),
        extended_language_digest=language.digest(),
        adoption_committed=True,
        fresh_process_loaded=True,
    )


def _run():
    language, substrate, primitive_id = _neutral_extended_runtime()
    material = _synthetic_material(language, substrate)
    return run_evolvable_qualification_batch(
        material,
        protocol_blob=PROTOCOL.read_bytes(),
        downstream_primitive_id=primitive_id,
        language=language,
        substrate=substrate,
        qualification_contract=execution_contract(),
        reproduction_gate_open=True,
        adoption_committed=True,
        fresh_process_loaded=True,
    )


def _redigest(material: dict[str, object]) -> None:
    payload = {key: value for key, value in material.items() if key != "materialization_digest"}
    material["materialization_digest"] = hashlib.sha256(canonical_bytes(payload)).hexdigest()


def test_verified_batch_executes_exactly_twelve_and_preserves_neutral_negative() -> None:
    result = _run()
    assert result["arm"] == "evolvable_substrate"
    assert result["attempts_expected"] == 12
    assert result["attempts_executed"] == 12
    assert len(result["attempts"]) == 12
    assert [item["attempts"] for item in result["family_summaries"]] == [6, 6]
    # The neutral identity acquisition is deliberately not the target.  Hidden synthetic values are
    # all >= 3000, so no family may be rescued by the batch executor.
    assert result["complete_families"] == 0
    assert result["evolvable_passes_frozen_empirical_rule"] is False
    assert result["global_certificate_remains_separate"] is True
    assert result["final_h38_verdict_computed_here"] is False
    assert result["control_arms_executed_here"] is False
    assert isinstance(result["batch_digest"], str) and len(result["batch_digest"]) == 64


def test_batch_refuses_before_inspecting_malformed_material_when_gate_is_closed() -> None:
    language, substrate, primitive_id = _neutral_extended_runtime()
    with pytest.raises(QualificationBatchError, match="closed before independent reproduction"):
        run_evolvable_qualification_batch(
            {"not": "qualification material"},
            protocol_blob=PROTOCOL.read_bytes(),
            downstream_primitive_id=primitive_id,
            language=language,
            substrate=substrate,
            qualification_contract=execution_contract(),
            reproduction_gate_open=False,
            adoption_committed=True,
            fresh_process_loaded=True,
        )


def test_batch_rejects_reordered_material_after_outer_redigest() -> None:
    language, substrate, primitive_id = _neutral_extended_runtime()
    material = copy.deepcopy(_synthetic_material(language, substrate))
    draws = material["families"][0]["draws"]
    draws[0], draws[1] = draws[1], draws[0]
    _redigest(material)
    with pytest.raises(QualificationBatchError, match="material verification failed"):
        run_evolvable_qualification_batch(
            material,
            protocol_blob=PROTOCOL.read_bytes(),
            downstream_primitive_id=primitive_id,
            language=language,
            substrate=substrate,
            qualification_contract=execution_contract(),
            reproduction_gate_open=True,
            adoption_committed=True,
            fresh_process_loaded=True,
        )


def test_batch_binds_material_to_exact_executing_runtime() -> None:
    language, substrate, primitive_id = _neutral_extended_runtime()
    material = _synthetic_material(language, substrate)
    base_language, base_substrate, _, _ = load_frozen_base()
    with pytest.raises(QualificationBatchError, match="material verification failed"):
        run_evolvable_qualification_batch(
            material,
            protocol_blob=PROTOCOL.read_bytes(),
            downstream_primitive_id=primitive_id,
            language=base_language,
            substrate=base_substrate,
            qualification_contract=execution_contract(),
            reproduction_gate_open=True,
            adoption_committed=True,
            fresh_process_loaded=True,
        )
