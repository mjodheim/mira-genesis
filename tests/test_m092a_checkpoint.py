"""The M092-A seal is exact, pre-extension and able to fail."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from check_m092a_checkpoint import (
    DEFAULT_CHECKPOINT,
    M092ACheckpointError,
    _digest_without_self,
    verify_checkpoint,
)


def test_checkpoint_verifies_exact_pre_extension_blobs() -> None:
    report = verify_checkpoint()
    assert report["status"] == "verified"
    assert report["artifacts_verified"] >= 15
    assert report["immutable_artifacts_verified"] >= 14
    assert len(report["checkpoint_digest"]) == 64
    assert len(report["source_commit"]) == 40


def test_checkpoint_digest_detects_tampering(tmp_path: Path) -> None:
    value = json.loads(DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))
    value["chronology"]["model_calls"] = 1
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(M092ACheckpointError, match="checkpoint digest mismatch"):
        verify_checkpoint(altered)


def test_recomputed_digest_cannot_hide_a_semantic_commitment_change(tmp_path: Path) -> None:
    value = json.loads(DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))
    value["semantic_commitments"]["substrate_digest"] = "0" * 64
    value["checkpoint_digest"] = _digest_without_self(value)
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(M092ACheckpointError, match="substrate semantic digest mismatch"):
        verify_checkpoint(altered)


def test_recomputed_digest_cannot_rewrite_a_bound_blob(tmp_path: Path) -> None:
    value = json.loads(DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))
    target = "metamorphosis/m092_kernel.py"
    value["artifacts"][target]["sha256"] = "0" * 64
    value["checkpoint_digest"] = _digest_without_self(value)
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(M092ACheckpointError, match="SHA-256 mismatch"):
        verify_checkpoint(altered)


def test_recomputed_digest_cannot_drop_or_unfreeze_a_required_blob(tmp_path: Path) -> None:
    original = json.loads(DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))

    missing = copy.deepcopy(original)
    missing["artifacts"].pop("metamorphosis/m092_kernel.py")
    missing["checkpoint_digest"] = _digest_without_self(missing)
    missing_path = tmp_path / "missing.json"
    missing_path.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(M092ACheckpointError, match="artifact map differs"):
        verify_checkpoint(missing_path)

    mutable = copy.deepcopy(original)
    mutable["artifacts"]["metamorphosis/m092_kernel.py"]["immutable"] = False
    mutable["checkpoint_digest"] = _digest_without_self(mutable)
    mutable_path = tmp_path / "mutable.json"
    mutable_path.write_text(json.dumps(mutable), encoding="utf-8")
    with pytest.raises(M092ACheckpointError, match="immutability declaration differs"):
        verify_checkpoint(mutable_path)


def test_source_commit_contains_no_m092b_artifact() -> None:
    value = json.loads(DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))
    assert value["absent_at_source_commit"] == [
        "experiments/M092/PROTOCOL.json",
        "experiments/M092/QUALIFICATION.json",
        "experiments/M092/SUBSTRATE_B.json",
        "experiments/M092/VALIDATION_RECEIPT.json",
        "experiments/M092/RESULT.json",
        "experiments/M092/REGISTER_CLAIM.json",
    ]
    assert value["chronology"] == {
        "extension_search_executed_before_checkpoint": False,
        "qualification_existed_at_source_commit": False,
        "model_calls": 0,
        "network_calls": 0,
    }


def test_every_forbidden_checkpoint_claim_is_false(tmp_path: Path) -> None:
    original = json.loads(DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))
    for name in original["claim_boundary"]:
        value = copy.deepcopy(original)
        value["claim_boundary"][name] = True
        value["checkpoint_digest"] = _digest_without_self(value)
        altered = tmp_path / f"{name}.json"
        altered.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(M092ACheckpointError, match="forbidden claim"):
            verify_checkpoint(altered)
