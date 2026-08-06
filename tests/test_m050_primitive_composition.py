from __future__ import annotations

from dataclasses import replace

import pytest

from metamorphosis.m050_primitive_composition import (
    COMPOSITION_BUDGET,
    FROZEN_PIPELINES,
    M050Error,
    Probe,
    compose_pipeline,
    independently_validate,
    run_m050_bounded_primitive_composition,
)


POSITIVE_PUBLIC = (Probe((1, 1, 2), 3), Probe((-2, 1), -1), Probe((), 0))


def test_budget_and_family_are_frozen() -> None:
    assert COMPOSITION_BUDGET == 24
    assert len(FROZEN_PIPELINES) == COMPOSITION_BUDGET


def test_public_evidence_composes_unique_pipeline() -> None:
    result = compose_pipeline(POSITIVE_PUBLIC)
    assert result.status == "composed"
    assert result.pipeline is not None
    names = [item["name"] for item in result.pipeline["primitives"]]
    assert names == ["unique", "sum", "zero"]
    assert result.explored_compositions == 24


def test_ambiguous_public_evidence_fails_closed() -> None:
    result = compose_pipeline((Probe((5,), 5), Probe((), 0)))
    assert result.status == "insufficient_evidence"
    assert result.pipeline is None
    assert len(result.surviving_pipeline_digests) > 1


def test_contradictory_public_evidence_fails_closed() -> None:
    result = compose_pipeline((Probe((1, 2), 3), Probe((1, 2), 99)))
    assert result.status == "insufficient_evidence"
    assert result.pipeline is None
    assert result.surviving_pipeline_digests == ()


def test_hidden_validation_accepts_independently() -> None:
    composition = compose_pipeline(POSITIVE_PUBLIC)
    verdict = independently_validate(composition, (Probe((-5, 1, -5, 2), -2),))
    assert verdict.accepted is True


def test_hidden_contradiction_is_preserved_as_rejection() -> None:
    composition = compose_pipeline(
        (Probe((1, 2, 3), 6), Probe((1, 1, 2), 4), Probe((-2, 1), -1), Probe((), 0))
    )
    verdict = independently_validate(composition, (Probe((2, 3), 4),))
    assert verdict.accepted is False


def test_tampered_pipeline_is_rejected() -> None:
    composition = compose_pipeline(POSITIVE_PUBLIC)
    assert composition.pipeline is not None
    tampered = dict(composition.pipeline)
    tampered["runtime"] = "python"
    with pytest.raises(M050Error, match="digest mismatch"):
        independently_validate(replace(composition, pipeline=tampered), (Probe((1,), 1),))


def test_empty_evidence_is_rejected() -> None:
    with pytest.raises(M050Error, match="at least one public probe"):
        compose_pipeline(())


def test_validation_requires_hidden_evidence() -> None:
    composition = compose_pipeline(POSITIVE_PUBLIC)
    with pytest.raises(M050Error, match="requires hidden probes"):
        independently_validate(composition, ())


def test_manifest_is_deterministic_and_bounded() -> None:
    first = run_m050_bounded_primitive_composition()
    second = run_m050_bounded_primitive_composition()
    assert first == second
    assert first["status"] == "passed_in_development"
    assert first["hidden_rejection"]["accepted"] is False
    assert first["composition_budget"] == 24
    assert first["arbitrary_code_generation"] is False
    assert first["unknown_runtime_discovery"] is False
    assert first["repository_authority"] is False
    assert first["network_authority"] is False
    assert first["credential_authority"] is False
    assert first["deployment_authority"] is False
    assert first["canonical"] is False
