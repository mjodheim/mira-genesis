from dataclasses import replace

import pytest

from metamorphosis.m051_variable_composition import FROZEN_CANDIDATES, Probe
from metamorphosis.m052_equivalence_pruning import (
    CANONICAL_REPRESENTATIVES,
    EQUIVALENCE_CLASSES,
    FINITE_DOMAIN,
    M052Error,
    behavioral_signature,
    independently_validate,
    run_m052_behavioral_equivalence_pruning,
    search_with_pruning,
)


def _positive_result():
    return search_with_pruning(
        (
            Probe((-1, 1, -1), 1),
            Probe((-2, -2, 1), 3),
            Probe((), 0),
        )
    )


def test_finite_domain_is_frozen_and_complete():
    assert len(FINITE_DOMAIN) == 156
    assert FINITE_DOMAIN[0] == ()
    assert all(len(values) <= 3 for values in FINITE_DOMAIN)


def test_behavioral_pruning_reduces_the_frozen_grammar():
    assert len(FROZEN_CANDIDATES) == 80
    assert 0 < len(CANONICAL_REPRESENTATIVES) < len(FROZEN_CANDIDATES)
    assert sum(len(members) for members in EQUIVALENCE_CLASSES.values()) == 80
    assert any(len(members) > 1 for members in EQUIVALENCE_CLASSES.values())


def test_every_class_has_one_canonical_representative():
    representative_signatures = {behavioral_signature(candidate) for candidate in CANONICAL_REPRESENTATIVES}
    assert representative_signatures == set(EQUIVALENCE_CLASSES)


def test_positive_episode_selects_one_behavioral_class():
    result = _positive_result()
    assert result.status == "composed"
    assert result.candidate is not None
    assert result.raw_candidate_count == 80
    assert result.equivalence_class_count == len(CANONICAL_REPRESENTATIVES)
    assert result.pruned_candidate_count > 0
    assert independently_validate(
        result,
        (Probe((-2, 2, 1), 3), Probe((-1, -1, 2), 3)),
    )


def test_public_ambiguity_fails_closed():
    result = search_with_pruning((Probe((1,), 1), Probe((), 0)))
    assert result.status == "insufficient_evidence"
    assert result.candidate is None
    assert len(result.surviving_class_signatures) > 1


def test_hidden_contradiction_is_preserved_as_negative_evidence():
    result = _positive_result()
    assert not independently_validate(result, (Probe((-2, 2, 1), 999),))


def test_tampered_candidate_is_rejected():
    result = _positive_result()
    assert result.candidate is not None
    tampered = dict(result.candidate)
    tampered["digest"] = "0" * 64
    with pytest.raises(M052Error, match="digest mismatch"):
        independently_validate(replace(result, candidate=tampered), (Probe((-2, 2, 1), 3),))


def test_empty_and_out_of_domain_evidence_are_rejected():
    with pytest.raises(M052Error, match="at least one public probe"):
        search_with_pruning(())
    with pytest.raises(M052Error, match="frozen finite domain"):
        search_with_pruning((Probe((3,), 3),))
    with pytest.raises(M052Error, match="hidden probes"):
        independently_validate(_positive_result(), ())


def test_manifest_is_deterministic_and_authority_bounded():
    first = run_m052_behavioral_equivalence_pruning()
    second = run_m052_behavioral_equivalence_pruning()
    assert first == second
    assert first["raw_candidate_count"] == 80
    assert first["pruned_candidate_count"] > 0
    assert first["arbitrary_code_generation"] is False
    assert first["grammar_widening"] is False
    assert first["network_authority"] is False
    assert first["repository_authority"] is False
    assert first["credential_authority"] is False
    assert first["deployment_authority"] is False
    assert first["canonical"] is False
