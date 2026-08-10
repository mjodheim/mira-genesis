from __future__ import annotations

import json

import pytest

from check_m075_development import (
    M075DevelopmentVerificationError, RECORD_PATH, verify,
)


def _record():
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_preserved_zero_token_development_record_recomputes() -> None:
    report = verify()
    assert report["verified"] is True
    assert report["scientific_result"] is False
    assert report["episode_count"] == 12
    assert report["model_tokens_spent"] == 0


def test_episode_removal_invalidates_exact_coverage() -> None:
    changed = _record()
    changed["episodes"].pop()
    with pytest.raises(M075DevelopmentVerificationError, match="exact coverage"):
        verify(changed)


def test_budget_mutation_invalidates_epistemic_state() -> None:
    changed = _record()
    changed["episodes"][0]["epistemic_states"][0][
        "remaining_steps_including_current"
    ] = 99
    with pytest.raises(M075DevelopmentVerificationError, match="budget accounting"):
        verify(changed)


def test_hidden_label_injection_invalidates_epistemic_state() -> None:
    changed = _record()
    changed["episodes"][0]["epistemic_states"][0]["solvability"] = "feasible"
    with pytest.raises(M075DevelopmentVerificationError, match="hidden field"):
        verify(changed)


def test_cross_arm_label_mutation_is_rejected() -> None:
    changed = _record()
    changed["episodes"][1]["capability_certificates"][0]["returncode"] = 127
    with pytest.raises(M075DevelopmentVerificationError, match="label drifted"):
        verify(changed)
