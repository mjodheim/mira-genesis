from __future__ import annotations

from dataclasses import replace

import pytest

from metamorphosis.m051_variable_composition import (
    COMPOSITION_BUDGET,
    FROZEN_CANDIDATES,
    MAX_TRANSFORM_DEPTH,
    M051Error,
    Probe,
    independently_validate,
    run_m051_bounded_variable_composition,
    search,
)


PUBLIC = (
    Probe((-1, 1, -1, 2), 3),
    Probe((-2, -2, 3), 5),
    Probe((), 0),
)


def test_budget_and_depth_are_frozen() -> None:
    assert MAX_TRANSFORM_DEPTH == 2
    assert COMPOSITION_BUDGET == 80
    assert len(FROZEN_CANDIDATES) == 80


def test_unique_variable_length_composition_is_found() -> None:
    result = search(PUBLIC)
    assert result.status == "composed"
    assert result.candidate is not None
    assert result.candidate["transforms"] == ["absolute", "unique"]
    assert result.candidate["reduction"] == "sum"
    assert result.candidate["empty_policy"] == "zero"


def test_ambiguous_evidence_fails_closed() -> None:
    result = search((Probe((5,), 5), Probe((), 0)))
    assert result.status == "insufficient_evidence"
    assert result.candidate is None
    assert len(result.surviving_digests) > 1


def test_contradictory_evidence_fails_closed() -> None:
    result = search((Probe((1, 2), 3), Probe((1, 2), 99)))
    assert result.status == "insufficient_evidence"
    assert result.surviving_digests == ()


def test_hidden_validation_is_independent() -> None:
    result = search(PUBLIC)
    assert independently_validate(result, (Probe((-5, 5, 2), 7),)) is True
    assert independently_validate(result, (Probe((-5, 5, 2), 99),)) is False


def test_tampered_candidate_is_rejected() -> None:
    result = search(PUBLIC)
    assert result.candidate is not None
    tampered = dict(result.candidate)
    tampered["reduction"] = "maximum"
    with pytest.raises(M051Error, match="digest mismatch"):
        independently_validate(replace(result, candidate=tampered), (Probe((1,), 1),))


def test_empty_public_or_hidden_evidence_is_rejected() -> None:
    with pytest.raises(M051Error, match="public probe"):
        search(())
    with pytest.raises(M051Error, match="hidden probes"):
        independently_validate(search(PUBLIC), ())


def test_manifest_is_deterministic_and_bounded() -> None:
    first = run_m051_bounded_variable_composition()
    second = run_m051_bounded_variable_composition()
    assert first == second
    assert first["status"] == "passed_in_development"
    assert first["composition_budget"] == 80
    assert first["max_transform_depth"] == 2
    assert first["arbitrary_code_generation"] is False
    assert first["unknown_runtime_discovery"] is False
    assert first["network_authority"] is False
    assert first["repository_authority"] is False
    assert first["credential_authority"] is False
    assert first["deployment_authority"] is False
    assert first["canonical"] is False
