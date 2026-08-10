from __future__ import annotations

import json

import pytest

from check_m075_model_development_result import (
    M075ModelDevelopmentResultVerificationError, RESULT_PATH, verify,
)


def _result():
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_preserved_public_model_development_result_recomputes() -> None:
    report = verify()
    assert report["verified"] is True
    assert report["scientific_result"] is False
    assert report["episode_count"] == 12
    assert report["live_model_decisions"] == 43
    assert report["baseline_true_refusals"] == 0
    assert report["context_true_refusals"] == 2
    assert report["context_false_refusals"] == 0


def test_episode_removal_invalidates_exact_coverage() -> None:
    changed = _result()
    changed["episodes"].pop()
    with pytest.raises(M075ModelDevelopmentResultVerificationError, match="exact twelve"):
        verify(changed)


def test_request_digest_mutation_is_rejected() -> None:
    changed = _result()
    changed["episodes"][0]["model_decisions"][0]["request"]["input_json"] += " "
    with pytest.raises(M075ModelDevelopmentResultVerificationError, match="request digest"):
        verify(changed)


def test_hidden_label_injection_is_rejected_even_with_rehashed_request() -> None:
    changed = _result()
    decision = changed["episodes"][0]["model_decisions"][0]
    payload = json.loads(decision["request"]["input_json"])
    payload["expected_solvability"] = "feasible"
    decision["request"]["input_json"] = json.dumps(payload, sort_keys=True)
    from check_m075_model_development_result import _sha256
    decision["request_sha256"] = _sha256(decision["request"])
    with pytest.raises(M075ModelDevelopmentResultVerificationError, match="information boundary"):
        verify(changed)


def test_context_budget_mutation_is_rejected() -> None:
    changed = _result()
    episode = changed["episodes"][1]
    episode["epistemic_states"][0]["remaining_steps_including_current"] = 99
    decision = episode["model_decisions"][0]
    payload = json.loads(decision["request"]["input_json"])
    payload["epistemic_state"]["remaining_steps_including_current"] = 99
    decision["request"]["input_json"] = json.dumps(
        payload, sort_keys=True, ensure_ascii=False,
    )
    from check_m075_model_development_result import _sha256
    decision["request_sha256"] = _sha256(decision["request"])
    with pytest.raises(M075ModelDevelopmentResultVerificationError, match="budget accounting"):
        verify(changed)


def test_calibration_mutation_is_rejected() -> None:
    changed = _result()
    changed["reports"][1]["true_refusals"] = 3
    with pytest.raises(M075ModelDevelopmentResultVerificationError, match="reports"):
        verify(changed)
