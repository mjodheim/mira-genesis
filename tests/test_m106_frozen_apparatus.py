"""M106 frozen-apparatus invariants.

Deliberately **not** a bound apparatus member. The bound list was fixed at freeze time and includes
tests/test_m106_replication.py, so any test that asserts "the bound apparatus is unchanged" would
break that very invariant by existing inside it. This file therefore lives outside the binding and
can evolve without rebinding the protocol.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import build_m106_protocol as builder
from scripts import run_m106_qualification as qualification

ROOT = Path(__file__).resolve().parents[1]


def test_the_bound_apparatus_still_matches_its_frozen_bytes() -> None:
    """A frozen apparatus must stay byte-verifiable forever.

    Recording a verdict inside a bound document would silently rebind the protocol and make the
    freeze unreproducible for anyone else. M106's result summary lives outside the bound list for
    exactly this reason, and this test is what keeps that decision honest.
    """
    if not qualification.PROTOCOL_PATH.exists():
        return
    frozen = json.loads(qualification.PROTOCOL_PATH.read_text("ascii"))["bound_files"]
    measured = builder.bound_files()
    drifted = [
        path
        for path, value in measured["member_digests"].items()
        if frozen["member_digests"].get(path) != value
    ]
    assert not drifted, drifted
    assert measured["digest"] == frozen["digest"]


def test_the_result_summary_is_outside_the_bound_apparatus() -> None:
    summary = ROOT / "experiments" / "M106" / "RESULT_SUMMARY.md"
    if not summary.exists():
        return
    assert "experiments/M106/RESULT_SUMMARY.md" not in builder.APPARATUS_FILES
    assert "VERDICT" in summary.read_text(encoding="utf-8")
