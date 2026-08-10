from __future__ import annotations

from copy import deepcopy
import json

import pytest

from metamorphosis.m074_scientific_runner import protocol_commitment
from check_m074_scientific_protocol import (
    PROTOCOL_PATH, ScientificProtocolVerificationError, verify,
)


def test_frozen_scientific_protocol_and_all_code_bindings_verify() -> None:
    report = verify()
    assert report["verified"] is True
    assert report["episode_count"] == 12
    assert report["scientific_result_exists_in_protocol"] is False


def test_threshold_mutation_is_rejected_even_with_a_recomputed_commitment() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol["thresholds"]["minimum_terminal_true_refusals"] = 1
    protocol["protocol_commitment_sha256"] = protocol_commitment(protocol)
    with pytest.raises(ScientificProtocolVerificationError, match="thresholds"):
        verify(protocol, verify_files=False)


def test_episode_removal_is_rejected_even_with_a_recomputed_commitment() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed = deepcopy(protocol)
    changed["episode_order"].pop()
    changed["protocol_commitment_sha256"] = protocol_commitment(changed)
    with pytest.raises(ScientificProtocolVerificationError, match="coverage"):
        verify(changed, verify_files=False)


def test_apparatus_commit_mutation_is_rejected() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol["apparatus_commit"] = "0" * 40
    protocol["protocol_commitment_sha256"] = protocol_commitment(protocol)
    with pytest.raises(ScientificProtocolVerificationError, match="apparatus commit"):
        verify(protocol, verify_files=False)
