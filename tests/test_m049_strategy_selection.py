from __future__ import annotations

import copy

import pytest

from metamorphosis.m049_strategy_selection import (
    FROZEN_STRATEGIES,
    M049Error,
    Probe,
    independently_validate,
    run_m049_bounded_strategy_selection,
    select_strategy,
)


def test_positive_public_evidence_selects_maximum_only() -> None:
    selection = select_strategy(
        (
            Probe((2, 9, 4), 9),
            Probe((-5, -2, -8), -2),
            Probe((), 0),
        )
    )
    assert selection.status == "selected"
    assert selection.strategy is not None
    assert selection.strategy["aggregate"] == "maximum"
    assert len(selection.surviving_strategy_digests) == 1


def test_ambiguous_public_evidence_fails_closed() -> None:
    selection = select_strategy((Probe((5,), 5), Probe((), 0)))
    assert selection.status == "insufficient_evidence"
    assert selection.strategy is None
    assert len(selection.surviving_strategy_digests) == len(FROZEN_STRATEGIES)


def test_contradictory_public_evidence_fails_closed() -> None:
    selection = select_strategy((Probe((1, 2), 99),))
    assert selection.status == "insufficient_evidence"
    assert selection.surviving_strategy_digests == ()


def test_empty_public_evidence_is_rejected() -> None:
    with pytest.raises(M049Error, match="public probe"):
        select_strategy(())


def test_hidden_validator_accepts_correct_public_selection() -> None:
    selection = select_strategy((Probe((1, 8, 3), 8), Probe((-3, -1), -1)))
    verdict = independently_validate(selection, (Probe((4, 4, 2), 4),))
    assert verdict.accepted is True


def test_hidden_validator_can_reject_publicly_plausible_selection() -> None:
    selection = select_strategy((Probe((0, 0), 0), Probe((), 0)))
    assert selection.status == "insufficient_evidence"
    with pytest.raises(M049Error, match="uniquely selected"):
        independently_validate(selection, (Probe((1, 2), 2),))


def test_validator_rejects_missing_hidden_evidence() -> None:
    selection = select_strategy((Probe((1, 8, 3), 8), Probe((-3, -1), -1)))
    with pytest.raises(M049Error, match="hidden probes"):
        independently_validate(selection, ())


def test_validator_rejects_tampered_strategy_digest() -> None:
    selection = select_strategy((Probe((1, 8, 3), 8), Probe((-3, -1), -1)))
    mapping = selection.to_dict()
    assert mapping["strategy"] is not None
    tampered_strategy = copy.deepcopy(mapping["strategy"])
    tampered_strategy["aggregate"] = "minimum"
    tampered = type(selection)(
        status="selected",
        strategy=tampered_strategy,
        public_evidence_digest=selection.public_evidence_digest,
        surviving_strategy_digests=selection.surviving_strategy_digests,
    )
    with pytest.raises(M049Error, match="digest mismatch"):
        independently_validate(tampered, (Probe((1, 2), 2),))


def test_manifest_is_deterministic_and_bounded() -> None:
    first = run_m049_bounded_strategy_selection()
    second = run_m049_bounded_strategy_selection()
    assert first == second
    assert first["status"] == "passed_in_development"
    assert first["strategy_budget"] == 4
    assert first["canonical"] is False
    assert first["arbitrary_compiler_synthesis"] is False
    assert first["unknown_runtime_discovery"] is False
    assert first["repository_authority"] is False
    assert first["network_authority"] is False
    assert first["deployment_authority"] is False
    assert first["validation"]["accepted"] is True
    assert first["ambiguous"]["status"] == "insufficient_evidence"
