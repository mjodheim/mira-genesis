"""Protocol-exact independent validation receipt for M092 adoption.

This module is frozen before the first canonical target search.  It never imports candidate
construction, qualification, search-result, or hidden-world code.  It recomputes the structural and
anti-cheating scanner plus the independent global certificate verifier from the exact program and
certificate supplied by the selected result, then emits the closed receipt schema committed in
``experiments/M092/PROTOCOL.json``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m092_candidate_validation import validate_candidate_artifacts
from metamorphosis.m092_certificate_verifier import verify_global_certificate
from metamorphosis.m092_kernel import Program, program_digest
from metamorphosis.m092_runtime import canonical_bytes

VALIDATION_RECEIPT_SCHEMA = "m092-independent-validation-receipt-v1"


class ValidationReceiptError(ValueError):
    """The selected candidate cannot receive the protocol-required independent receipt."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _validator_blob_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def recompute_validation_receipt(
    program: Program,
    certificate: Mapping[str, object],
    *,
    expected_postcondition: Mapping[str, object],
    checkpoint_digest: str,
    support_artifacts: Sequence[object] = (),
) -> dict[str, object]:
    """Return the exact closed M092 validation receipt after full independent recomputation."""

    if not isinstance(checkpoint_digest, str) or len(checkpoint_digest) != 64:
        raise ValidationReceiptError("checkpoint digest must be canonical SHA-256")
    scan = validate_candidate_artifacts(program, certificate, support_artifacts=support_artifacts)
    if scan.get("accepted") is not True:
        raise ValidationReceiptError("candidate scanner refused independent validation")
    verification = verify_global_certificate(
        program,
        certificate,
        expected_postcondition=expected_postcondition,
    )
    exact_program_digest = program_digest(program)
    if scan.get("program_digest") != exact_program_digest:
        raise ValidationReceiptError("scanner digest differs from the exact program")
    if verification.get("program_digest") != exact_program_digest:
        raise ValidationReceiptError("global verifier digest differs from the exact program")
    certificate_digest = verification.get("certificate_digest")
    if not isinstance(certificate_digest, str) or len(certificate_digest) != 64:
        raise ValidationReceiptError("global verifier certificate digest is malformed")

    global_findings = {
        key: value
        for key, value in verification.items()
        if key not in {"frame", "certificate_digest"}
    }
    receipt: dict[str, object] = {
        "schema": VALIDATION_RECEIPT_SCHEMA,
        "checkpoint_digest": checkpoint_digest,
        "program_digest": exact_program_digest,
        "certificate_digest": certificate_digest,
        "validator_blob_sha256": _validator_blob_sha256(),
        "structural_findings": scan["structural_findings"],
        "anti_cheating_findings": scan["anti_cheating_findings"],
        "global_proof_findings": global_findings,
        "frame_findings": verification["frame"],
        "accepted": True,
        "qualification_imported": False,
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def validate_receipt_shape(receipt: Mapping[str, object]) -> None:
    expected = {
        "schema", "checkpoint_digest", "program_digest", "certificate_digest",
        "validator_blob_sha256", "structural_findings", "anti_cheating_findings",
        "global_proof_findings", "frame_findings", "accepted", "qualification_imported",
        "receipt_digest",
    }
    if set(receipt) != expected or receipt.get("schema") != VALIDATION_RECEIPT_SCHEMA:
        raise ValidationReceiptError("validation receipt fields differ from the closed protocol schema")
    payload = {key: receipt[key] for key in receipt if key != "receipt_digest"}
    if receipt.get("receipt_digest") != _digest(payload):
        raise ValidationReceiptError("validation receipt digest differs")
    if receipt.get("accepted") is not True or receipt.get("qualification_imported") is not False:
        raise ValidationReceiptError("validation receipt crosses the frozen acceptance boundary")


__all__ = [
    "VALIDATION_RECEIPT_SCHEMA", "ValidationReceiptError", "recompute_validation_receipt",
    "validate_receipt_shape",
]
