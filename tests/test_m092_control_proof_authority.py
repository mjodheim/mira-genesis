from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from metamorphosis.m092_control_proof_authority import (
    ControlProofAuthorityError,
    EXPECTED_INVARIANT_DIGEST,
    PRE_RESULT_BLOB_BINDINGS,
    git_blob_sha1,
    verify_m092p_authority,
)


def test_m092p_authority_recomputes_exact_pre_result_sources() -> None:
    receipt = verify_m092p_authority()
    assert receipt["authority"] == "Corollary M092-P from Proposition M092-I"
    assert receipt["search_failure_is_impossibility_proof"] is False
    assert receipt["control_uses_m092p_not_search_exhaustion"] is True
    assert receipt["length_independent"] is True
    assert receipt["exact_abstraction"] is True
    assert receipt["invariant_digest"] == EXPECTED_INVARIANT_DIGEST
    assert receipt["pre_result_blob_bindings"] == PRE_RESULT_BLOB_BINDINGS
    assert receipt["observed_blob_bindings"] == PRE_RESULT_BLOB_BINDINGS
    assert receipt["soundness_mismatches"] == 0
    assert receipt["composition_mismatches"] == 0
    assert receipt["finite_parity_matches"] == 0
    assert receipt["finite_parity_enumeration_role"] == "corroboration_only"
    assert isinstance(receipt["authority_digest"], str) and len(receipt["authority_digest"]) == 64


def test_git_blob_identity_is_content_and_length_bound() -> None:
    path = Path("metamorphosis/m092_invariant.py")
    exact = path.read_bytes()
    assert git_blob_sha1(exact) == PRE_RESULT_BLOB_BINDINGS[str(path)]
    assert git_blob_sha1(exact + b"\n") != PRE_RESULT_BLOB_BINDINGS[str(path)]


def test_tampered_preserved_audit_is_refused_even_if_findings_still_look_positive(tmp_path: Path) -> None:
    for relative in PRE_RESULT_BLOB_BINDINGS:
        source = Path(relative)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    audit_path = tmp_path / "experiments/M092/DESIGN_AUDIT.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["composition"]["programs"] += 1
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ControlProofAuthorityError, match="proof source drifted"):
        verify_m092p_authority(tmp_path)


def test_authority_does_not_accept_finite_enumeration_as_theorem(tmp_path: Path) -> None:
    for relative in PRE_RESULT_BLOB_BINDINGS:
        source = Path(relative)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    # Changing only the prose role is still fatal at the byte-binding boundary; there is no route
    # by which a post-result artifact can relabel finite search as the M092-P proof.
    audit_path = tmp_path / "experiments/M092/DESIGN_AUDIT.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["parity_enumeration"]["note"] = "this finite enumeration proves impossibility"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ControlProofAuthorityError):
        verify_m092p_authority(tmp_path)
