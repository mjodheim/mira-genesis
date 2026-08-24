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
        "0a74e8f2f3238b6d7a613a60e5cc0f353a94010eba9d6b78e2ba3a693d279523"
    )
    assert hashlib.sha256(raw).hexdigest() == (
        "424903d3aace9fc47005261e51b9ac90bc8b172e36bb38a65edec76268cca6b0"
    )
    assert candidate["candidate_source_commit"] == (
        "48be7c06a42edaec1d33f8a46a3407dbc3a098c2"
    )
    assert candidate["canonical_run_allowed"] is False
    for key, value in builder._base().items():
        assert candidate[key] == value


def test_final_protocol_and_canonical_evidence_remain_absent() -> None:
    for name in ("PROTOCOL.json", "RESULT.json", "CHECK_REPORT.json"):
        assert not (ROOT / "experiments" / "M103" / name).exists()
