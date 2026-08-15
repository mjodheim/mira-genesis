from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path

import pytest

from metamorphosis.m092_qualification_generator import materialize_hidden_qualification
from metamorphosis.m092_qualification_material_verifier import (
    FAMILIES,
    QualificationMaterialVerificationError,
    verify_qualification_material,
)
from metamorphosis.m092_runtime import canonical_bytes


PROTOCOL = Path("experiments/M092/PROTOCOL.json")
SUBSTRATE_DIGEST = "a" * 64
LANGUAGE_DIGEST = "b" * 64


def _material():
    return materialize_hidden_qualification(
        PROTOCOL.read_bytes(),
        extended_substrate_digest=SUBSTRATE_DIGEST,
        extended_language_digest=LANGUAGE_DIGEST,
        adoption_committed=True,
        fresh_process_loaded=True,
    )


def _redigest(material: dict[str, object]) -> None:
    payload = {key: value for key, value in material.items() if key != "materialization_digest"}
    material["materialization_digest"] = hashlib.sha256(canonical_bytes(payload)).hexdigest()


def test_independent_verifier_reconstructs_all_synthetic_draws_without_fixed_values() -> None:
    material = _material()
    receipt = verify_qualification_material(
        material,
        protocol_blob=PROTOCOL.read_bytes(),
        extended_substrate_digest=SUBSTRATE_DIGEST,
        extended_language_digest=LANGUAGE_DIGEST,
    )
    assert receipt["draw_algorithm_recomputed_independently"] is True
    assert receipt["post_hoc_draw_reordering"] is False
    assert receipt["families"] == list(FAMILIES)
    assert len(receipt["worlds"]) == 12
    assert len({world["task_id"] for world in receipt["worlds"]}) == 12
    assert receipt["materialization_digest"] == material["materialization_digest"]
    assert isinstance(receipt["verification_digest"], str)
    assert len(receipt["verification_digest"]) == 64


def test_post_hoc_reordering_is_rejected_even_when_outer_digest_is_recomputed() -> None:
    material = copy.deepcopy(_material())
    draws = material["families"][0]["draws"]
    draws[0], draws[1] = draws[1], draws[0]
    _redigest(material)
    with pytest.raises(QualificationMaterialVerificationError, match="counter-mode reconstruction"):
        verify_qualification_material(
            material,
            protocol_blob=PROTOCOL.read_bytes(),
            extended_substrate_digest=SUBSTRATE_DIGEST,
            extended_language_digest=LANGUAGE_DIGEST,
        )


def test_draw_counter_tamper_is_rejected_after_outer_redigest() -> None:
    material = copy.deepcopy(_material())
    material["families"][1]["draws"][0]["draw_counter"] += 1
    _redigest(material)
    with pytest.raises(QualificationMaterialVerificationError, match="counter-mode reconstruction"):
        verify_qualification_material(
            material,
            protocol_blob=PROTOCOL.read_bytes(),
            extended_substrate_digest=SUBSTRATE_DIGEST,
            extended_language_digest=LANGUAGE_DIGEST,
        )


def test_protocol_and_runtime_bindings_are_independent_inputs() -> None:
    material = _material()
    with pytest.raises(QualificationMaterialVerificationError, match="different protocol bytes"):
        verify_qualification_material(
            material,
            protocol_blob=PROTOCOL.read_bytes() + b" ",
            extended_substrate_digest=SUBSTRATE_DIGEST,
            extended_language_digest=LANGUAGE_DIGEST,
        )
    with pytest.raises(QualificationMaterialVerificationError, match="substrate digest differs"):
        verify_qualification_material(
            material,
            protocol_blob=PROTOCOL.read_bytes(),
            extended_substrate_digest="c" * 64,
            extended_language_digest=LANGUAGE_DIGEST,
        )


def test_chronology_claim_cannot_be_flipped_and_redigested() -> None:
    material = copy.deepcopy(_material())
    material["materialized_after_adoption"] = False
    _redigest(material)
    with pytest.raises(QualificationMaterialVerificationError, match="predates adoption"):
        verify_qualification_material(
            material,
            protocol_blob=PROTOCOL.read_bytes(),
            extended_substrate_digest=SUBSTRATE_DIGEST,
            extended_language_digest=LANGUAGE_DIGEST,
        )


def test_verifier_source_does_not_import_the_generator() -> None:
    source = Path("metamorphosis/m092_qualification_material_verifier.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert "metamorphosis.m092_qualification_generator" not in imports
