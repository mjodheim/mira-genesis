import copy

import pytest

from metamorphosis.m053_endogenous_extension import (
    EXTENSION_BUDGET, META_PROGRAMS, M053Error, Probe, Registry,
    certify_founder_insufficiency, independently_validate,
    run_m053_endogenous_extension, synthesize_extension,
)

PUBLIC = (
    Probe((1, 4, 2), "sum", 1),
    Probe((5, 2, 8), "sum", 3),
    Probe((0, 3, 7), "sum", 7),
)


def test_meta_language_is_fixed_and_small():
    assert EXTENSION_BUDGET == 16
    assert len(META_PROGRAMS) == 16


def test_founder_language_is_exhaustively_insufficient():
    certificate = certify_founder_insufficiency(PUBLIC)
    assert certificate["founder_candidate_count"] == 80
    assert certificate["survivor_count"] == 0
    assert certificate["insufficient"] is True


def test_public_evidence_synthesizes_new_pair_extension():
    result = synthesize_extension(PUBLIC)
    assert result["status"] == "synthesized"
    assert result["explored_meta_programs"] == 16
    assert result["extension"]["left"] == "current"
    assert result["extension"]["operator"] == "subtract"
    assert result["extension"]["right"] == "previous"


def test_hidden_validation_accepts_and_rejects_independently():
    result = synthesize_extension(PUBLIC)
    assert independently_validate(result, (Probe((-2, 3, 1), "sum", 3),)) is True
    assert independently_validate(result, (Probe((-2, 3, 1), "sum", 4),)) is False


def test_tampered_extension_is_rejected():
    result = synthesize_extension(PUBLIC)
    tampered = copy.deepcopy(result)
    tampered["extension"]["operator"] = "add"
    with pytest.raises(M053Error, match="digest mismatch"):
        independently_validate(tampered, (Probe((1, 2), "sum", 1),))


def test_ambiguous_evidence_fails_closed_without_widening():
    result = synthesize_extension((Probe((1, 2), "sum", 1),))
    assert result["status"] == "insufficient_evidence"
    assert result["extension"] is None
    assert result["explored_meta_programs"] == 16


def test_unvalidated_extension_cannot_be_adopted_and_rollback_is_exact():
    result = synthesize_extension(PUBLIC)
    founder = Registry()
    checkpoint = founder.checkpoint()
    with pytest.raises(M053Error, match="unvalidated"):
        founder.adopt(result["extension"], False)
    adopted = founder.adopt(result["extension"], True)
    assert adopted.checkpoint() != checkpoint
    assert founder.checkpoint() == checkpoint


def test_manifest_is_deterministic_and_preserves_authority_boundaries():
    first = run_m053_endogenous_extension()
    second = run_m053_endogenous_extension()
    assert first == second
    assert first["hidden_validated"] is True
    assert first["reuse_passed"] is True
    assert first["negative_status"] == "insufficient_evidence"
    assert first["rollback_exact"] is True
    assert first["network_authority"] is False
    assert first["repository_authority"] is False
    assert first["credential_authority"] is False
    assert first["deployment_authority"] is False
    assert first["canonical"] is False
