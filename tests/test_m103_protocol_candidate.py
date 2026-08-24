from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_m103_protocol as builder


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "experiments" / "M103" / "PROTOCOL_CANDIDATE.json"


def test_owner_review_candidate_is_exact_and_current() -> None:
    raw = CANDIDATE.read_bytes()
    candidate = json.loads(raw.decode("ascii"))
    payload = {key: value for key, value in candidate.items() if key != "candidate_digest"}
    assert candidate["candidate_digest"] == builder.digest(payload)
    assert candidate["candidate_digest"] == (
        "b44c80e52f8569f70f9d5b1ba89cb2fd42bac9a8628d83e42ae21cf4226e90f2"
    )
    assert hashlib.sha256(raw).hexdigest() == (
        "8565d330046cc2e25ec8fe6930ed6b1f62a2c32bcb17170565ebbdc04c74d659"
    )
    assert candidate["candidate_source_commit"] == (
        "b1f920b44707b5da3c90f99a6b51a9b070fbbf10"
    )
    assert candidate["canonical_run_allowed"] is False
    for key, value in builder._base().items():
        assert candidate[key] == value


def test_final_protocol_and_canonical_evidence_remain_absent() -> None:
    for name in ("PROTOCOL.json", "RESULT.json", "CHECK_REPORT.json"):
        assert not (ROOT / "experiments" / "M103" / name).exists()
