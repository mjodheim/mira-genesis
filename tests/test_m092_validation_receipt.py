from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis.m092_adoption_checkpoint import load_frozen_base
from metamorphosis.m092_certificate_generator import generate_candidate_certificates
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_validation_receipt import (
    VALIDATION_RECEIPT_SCHEMA,
    ValidationReceiptError,
    recompute_validation_receipt,
    validate_receipt_shape,
)

NEUTRAL_PROGRAM = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _receipt() -> dict[str, object]:
    _, _, _, checkpoint = load_frozen_base()
    certificate = next(
        generate_candidate_certificates(NEUTRAL_PROGRAM, COUNTDOWN_POSTCONDITION, limit=64)
    )
    receipt = recompute_validation_receipt(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
        checkpoint_digest=str(checkpoint["checkpoint_digest"]),
    )
    return receipt


def test_receipt_matches_closed_protocol_schema() -> None:
    receipt = _receipt()
    assert receipt["schema"] == VALIDATION_RECEIPT_SCHEMA
    assert set(receipt) == {
        "schema", "checkpoint_digest", "program_digest", "certificate_digest",
        "validator_blob_sha256", "structural_findings", "anti_cheating_findings",
        "global_proof_findings", "frame_findings", "accepted", "qualification_imported",
        "receipt_digest",
    }
    assert receipt["accepted"] is True
    assert receipt["qualification_imported"] is False
    validate_receipt_shape(receipt)


def test_checkpoint_digest_is_required_and_bound() -> None:
    certificate = next(
        generate_candidate_certificates(NEUTRAL_PROGRAM, COUNTDOWN_POSTCONDITION, limit=64)
    )
    with pytest.raises(ValidationReceiptError):
        recompute_validation_receipt(
            NEUTRAL_PROGRAM,
            certificate,
            expected_postcondition=COUNTDOWN_POSTCONDITION,
            checkpoint_digest="bad",
        )


def test_rehashed_lie_still_fails_closed_shape_validation() -> None:
    receipt = _receipt()
    altered = copy.deepcopy(receipt)
    altered["qualification_imported"] = True
    payload = {key: altered[key] for key in altered if key != "receipt_digest"}
    from metamorphosis.m092_runtime import canonical_bytes
    import hashlib
    altered["receipt_digest"] = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    with pytest.raises(ValidationReceiptError):
        validate_receipt_shape(altered)


def test_certificate_tamper_is_refused_by_recomputation() -> None:
    _, _, _, checkpoint = load_frozen_base()
    certificate = next(
        generate_candidate_certificates(NEUTRAL_PROGRAM, COUNTDOWN_POSTCONDITION, limit=64)
    )
    tampered = copy.deepcopy(certificate)
    tampered["program_digest"] = "0" * 64
    with pytest.raises(Exception):
        recompute_validation_receipt(
            NEUTRAL_PROGRAM,
            tampered,
            expected_postcondition=COUNTDOWN_POSTCONDITION,
            checkpoint_digest=str(checkpoint["checkpoint_digest"]),
        )


def test_validator_module_does_not_import_search_builder_or_qualification() -> None:
    text = Path("metamorphosis/m092_validation_receipt.py").read_text(encoding="utf-8")
    for forbidden in (
        "m092_certificate_generator", "m092_certificate_policy_search", "m092_criterion_search",
        "m092_qualification_generator", "m092_qualification",
    ):
        assert forbidden not in text
