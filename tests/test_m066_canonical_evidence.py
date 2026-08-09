from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from check_m066_canonical_result import (
    AUDIT_PATH,
    REPRODUCTION_PATH,
    RESULT_PATH,
    SEAL_PATH,
    CanonicalEvidenceError,
    validate_canonical_evidence,
)


def test_preserved_m066_canonical_evidence_is_exact_and_complete() -> None:
    value = validate_canonical_evidence()
    assert value["status"] == "canonical-positive-closed"
    assert value["selected_bank_index"] == 0
    assert value["exact_bytes_reproduced"] is True
    assert value["all_ten_audited_gates_true"] is True


def test_canonical_evidence_verifier_rejects_raw_byte_drift(tmp_path: Path) -> None:
    for relative in (RESULT_PATH, REPRODUCTION_PATH, SEAL_PATH, AUDIT_PATH):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)
    result = tmp_path / RESULT_PATH
    result.write_bytes(result.read_bytes() + b" ")
    with pytest.raises(CanonicalEvidenceError, match="bytes drifted"):
        validate_canonical_evidence(tmp_path)
