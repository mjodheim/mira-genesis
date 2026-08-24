from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_m103_protocol as builder


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "experiments" / "M103" / "PROTOCOL_CANDIDATE.json"
PROTOCOL = ROOT / "experiments" / "M103" / "PROTOCOL.json"


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


def test_final_protocol_is_exact_but_canonical_evidence_remains_absent() -> None:
    raw = PROTOCOL.read_bytes()
    protocol = json.loads(raw.decode("ascii"))
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    assert protocol["protocol_digest"] == builder.digest(payload)
    assert protocol["protocol_digest"] == (
        "cb21a4fa29d9895e477d12f6710eaa4f7c70dfca2e740812fe6846c4ff530de9"
    )
    assert hashlib.sha256(raw).hexdigest() == (
        "97c4aaf6aecfbf36903819043fa10d946c3a1d9e9e1b6193ff3e131c4bf4291b"
    )
    assert protocol["source_commit"] == "42c7f6a6f52a9650e75cc7a8d7e5f4ece8711aff"
    assert protocol["protocol_candidate"]["candidate_digest"] == (
        "b44c80e52f8569f70f9d5b1ba89cb2fd42bac9a8628d83e42ae21cf4226e90f2"
    )
    assert protocol["owner_protocol_acceptance"]["recorded"] is True
    assert protocol["canonical_run_allowed"] is False
    assert protocol["status"] == "frozen_protocol_run_not_authorized"
    for name in ("RESULT.json", "CHECK_REPORT.json"):
        assert not (ROOT / "experiments" / "M103" / name).exists()
