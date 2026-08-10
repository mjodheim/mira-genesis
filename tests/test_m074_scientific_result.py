from __future__ import annotations

from copy import deepcopy
import json

import pytest

from check_m074_scientific_result import (
    RESULT_PATH, ScientificResultVerificationError, verify,
)


def _result():
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_preserved_negative_scientific_result_recomputes() -> None:
    report = verify()
    assert report["verified"] is True
    assert report["classification"] == "negative"
    assert report["episode_count"] == 12
    assert report["live_model_decisions"] == 24
    assert report["paired_replay_decisions"] == 24


def test_one_removed_episode_invalidates_exact_coverage() -> None:
    changed = _result()
    changed["episodes"].pop()
    with pytest.raises(ScientificResultVerificationError, match="twelve-episode coverage"):
        verify(changed)


def test_one_mutated_raw_response_invalidates_its_digest() -> None:
    changed = _result()
    changed["episodes"][0]["model_decisions"][0]["response"]["script"] = "true"
    with pytest.raises(ScientificResultVerificationError, match="response digest"):
        verify(changed)


def test_one_mutated_replay_binding_invalidates_the_pair() -> None:
    changed = _result()
    changed["episodes"][1]["model_decisions"][0]["source_decision_index"] = 2
    with pytest.raises(ScientificResultVerificationError, match="paired decision prefix"):
        verify(changed)


def test_one_mutated_external_outcome_invalidates_the_evaluator_record() -> None:
    changed = deepcopy(_result())
    changed["episodes"][0]["external_success"] = False
    with pytest.raises(ScientificResultVerificationError, match="external evaluation"):
        verify(changed)
