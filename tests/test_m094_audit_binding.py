"""Amendment A3: the protocol's design-audit digest must name something that exists.

`design_audit.audit_digest` recorded a value from two commits before the freeze and matched no
committed artifact — not the document's bytes, not the report's bytes, not the report's own
recorded digest. Nothing noticed, because nothing compared them: the checker declared
`DESIGN_AUDIT_MD` and never used it, and no condition read the audit at all.

So the tests that matter here are not "is the number right today". They are "does the check
exist, and can it fail". A binding nothing can break is the state this amendment came from.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_m094_result as checker  # noqa: E402
from check_m094_result import (  # noqa: E402,F401
    REPLAYABLE_AUDIT_SECTIONS,
    SNAPSHOT_AUDIT_SECTIONS,
    check_design_audit_binding,
)

EXPERIMENT = REPO_ROOT / "experiments" / "M094"


@pytest.fixture
def protocol() -> dict:
    return json.loads((EXPERIMENT / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture
def audit() -> dict:
    return json.loads((EXPERIMENT / "DESIGN_AUDIT.json").read_text(encoding="utf-8"))


# ── the binding holds ─────────────────────────────────────────────────


def test_the_binding_resolves(protocol: dict) -> None:
    assert check_design_audit_binding(protocol) == []


def test_the_committed_audit_digests_to_its_own_recorded_value(audit: dict) -> None:
    recomputed = checker._digest({k: v for k, v in audit.items() if k != "digest"})
    assert audit["digest"] == recomputed


def test_the_protocol_names_the_committed_audit(protocol: dict, audit: dict) -> None:
    assert protocol["design_audit"]["audit_digest"] == audit["digest"]


def test_the_superseded_digest_is_preserved_not_overwritten(protocol: dict) -> None:
    """The value that named nothing is kept, so the chronology survives the correction."""

    design_audit = protocol["design_audit"]
    assert design_audit["superseded_audit_digest_see_amendment_a3"].startswith("d41ea1ea")
    assert design_audit["superseded_audit_digest_see_amendment_a3"] != design_audit["audit_digest"]


# ── and it can fail ───────────────────────────────────────────────────


def test_a_protocol_naming_the_wrong_audit_fails(protocol: dict) -> None:
    tampered = json.loads(json.dumps(protocol))
    tampered["design_audit"]["audit_digest"] = "0" * 64
    failures = check_design_audit_binding(tampered)
    assert failures
    assert any("audit_digest is not the committed audit" in item for item in failures)


def test_a_self_inconsistent_audit_fails(
    protocol: dict, audit: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corrupted = json.loads(json.dumps(audit))
    corrupted["milestone"] = "M999"  # contents change, recorded digest does not
    path = tmp_path / "DESIGN_AUDIT.json"
    path.write_text(json.dumps(corrupted), encoding="utf-8")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", path)

    failures = check_design_audit_binding(protocol)
    assert any("does not digest to its own recorded value" in item for item in failures)


def test_a_missing_audit_fails(
    protocol: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", tmp_path / "absent.json")
    assert check_design_audit_binding(protocol) == [
        "the design audit the protocol names does not exist"
    ]


def test_moved_evidence_for_a_recorded_defect_fails(
    protocol: dict, audit: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The condition that matters most: a preserved measurement that stops reproducing.

    The inherited implementation is kept precisely so the recorded defects stay supported. If
    one of those sub-reports drifts, the record is no longer evidence of anything.
    """

    tampered = json.loads(json.dumps(audit))
    tampered["indicator_discrimination"] = {"missing_query_method": {"components_matched": 99}}
    tampered["digest"] = checker._digest(
        {k: v for k, v in tampered.items() if k != "digest"}
    )
    path = tmp_path / "DESIGN_AUDIT.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", path)

    named = json.loads(json.dumps(protocol))
    named["design_audit"]["audit_digest"] = tampered["digest"]

    failures = check_design_audit_binding(named)
    assert any("no longer reproduces" in item for item in failures)


def test_p12_fails_when_the_binding_fails(
    protocol: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The binding must reach the verdict, not just exist as a helper."""

    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", tmp_path / "absent.json")
    condition = checker.check_p12(protocol)
    assert condition.computed is True
    assert condition.passed is False


# ── what is replayed, and what is deliberately not ────────────────────


def test_every_replayable_section_reproduces_today(audit: dict) -> None:
    import audit_m094_design as instrument

    replays = {
        "indicator_discrimination": instrument.indicator_discrimination,
        "capability_presence_blindness": instrument.capability_presence_blindness,
        "selection_determinism": instrument.selection_determinism,
        "template_authorship": instrument.template_authorship,
    }
    for section in REPLAYABLE_AUDIT_SECTIONS:
        assert checker._digest(audit[section]) == checker._digest(replays[section]()), section


def test_the_snapshot_section_is_disclosed_rather_than_replayed(protocol: dict) -> None:
    """The audit mixes a historical measurement with a live one, and says so.

    `corrected_measure_threshold_sensitivity` measures the *current* measure, so it moved when
    the diagnosis's detail encoding changed at 96c8a3a — before the freeze, and the report was
    never re-derived. Preserved with that disclosure rather than regenerated, because
    regenerating it today would describe the post-A2 code and replace a disclosed staleness
    with an undisclosed one.
    """

    amendment = next(item for item in protocol["amendments"] if item["id"] == "A3")
    split = amendment["what_is_replayable_and_what_is_a_snapshot"]
    assert set(split["replayed_and_checked"]) == set(REPLAYABLE_AUDIT_SECTIONS)
    assert set(split["preserved_not_replayed"]) == set(SNAPSHOT_AUDIT_SECTIONS)
    assert "fields_read 5" in amendment["a_second_staleness_found_while_fixing_the_first"]


def test_the_two_section_sets_do_not_overlap(audit: dict) -> None:
    assert not set(REPLAYABLE_AUDIT_SECTIONS) & set(SNAPSHOT_AUDIT_SECTIONS)
    for section in REPLAYABLE_AUDIT_SECTIONS + SNAPSHOT_AUDIT_SECTIONS:
        assert section in audit, section
