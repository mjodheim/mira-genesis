"""M117 closes as instrument development. Its hypothesis was never tested.

Five apparatus revisions occurred inside M117 and some followed real endpoint observations, so the
route selection cannot be claimed to have been prospective from the milestone's start. The result is
a DEVELOPMENT calibration finding and nothing more: it advances no generality gate, and the
scientific work moves to M118/H63 behind a fixed, already-calibrated route.

These tests hold the record to that boundary.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _flat(path: Path) -> str:
    """Markdown wraps lines; assertions about prose must not depend on where."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
M117 = ROOT / "experiments" / "M117"
OUTCOME = M117 / "STAGE1_OUTCOME.md"
CALIBRATION_ROUTE = {
    "model": "deepseek/deepseek-v4-flash-0731",
    "provider": "OpenInference",
    "canonical_checkpoint": "deepseek/deepseek-v4-flash-20260731",
}


def _report():
    return json.loads((M117 / "STAGE1_ROUTE_QUALIFICATION.json").read_text(encoding="utf-8"))


# -------------------------------------------------------------------------------------------
# H62 was never tested
# -------------------------------------------------------------------------------------------

def test_h62_was_never_frozen_and_no_bank_exists():
    report = _report()
    assert report["h62_frozen"] is False
    assert report["h62_bank_exists"] is False
    for absent in ("ANALYSIS_PLAN.json", "GENERATOR_SPEC.json", "SEALED_BANK.json.gpg",
                   "RESULT.json", "CARRIER_BANK.json"):
        assert not (M117 / absent).exists(), absent


def test_no_qualifying_scientific_invocation_was_ever_made():
    report = _report()
    assert report["qualifying_calls"] == 0
    assert report["is_a_qualifying_call"] is False
    assert report["qualifying_input_was_sent"] is False
    assert report["development"] is True


def test_the_outcome_states_the_hypothesis_is_untested():
    text = _flat(OUTCOME)
    assert "untested" in text
    assert "instrument-development completed" in text
    assert "G1–G10" in text and "unchanged" in text


# -------------------------------------------------------------------------------------------
# The observed result, preserved exactly
# -------------------------------------------------------------------------------------------

def test_attempt_05_is_preserved_exactly_as_observed():
    report = _report()
    assert report["candidates_probed"] == 16
    assert report["requests_spent"] == 144
    assert report["global_request_ceiling"] == 160
    selection = report["selection"]
    assert selection["route_selected"] is True
    assert selection["selected"]["model"] == CALIBRATION_ROUTE["model"]
    assert selection["selected"]["provider"] == CALIBRATION_ROUTE["provider"]
    assert selection["selected"]["canonical_checkpoint"] == CALIBRATION_ROUTE["canonical_checkpoint"]


def test_exactly_one_candidate_qualified_at_the_earliest_qualifying_position():
    ledger = json.loads(
        (M117 / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    probed = [p for p in ledger["profiles"] if not p.get("skipped")]
    qualifying = [p["order"] for p in probed if (p.get("qualification") or {}).get("qualifies")]
    assert len(qualifying) == 1
    assert qualifying[0] == _report()["selection"]["selected"]["order"]


def test_all_twelve_clauses_passed_for_the_selected_route():
    ledger = json.loads(
        (M117 / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    order = _report()["selection"]["selected"]["order"]
    profile = next(p for p in ledger["profiles"] if p.get("order") == order)
    checks = profile["qualification"]["checks"]
    assert len(checks) == 12
    assert all(checks.values())
    assert profile["qualification"]["failed_checks"] == []


def test_the_stress_observation_is_preserved():
    ledger = json.loads(
        (M117 / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    order = _report()["selection"]["selected"]["order"]
    stress = next(p for p in ledger["profiles"] if p.get("order") == order)["token_capacity_stress"]
    assert stress["http_status"] == 200
    assert stress["finish_reason"] == "stop"
    assert stress["completion_tokens"] == 68368
    assert stress["schema_conforms"] is True
    assert stress["raw_completion_persisted"] is False


# -------------------------------------------------------------------------------------------
# The revision history is disclosed, not buried
# -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("directory", [
    "ATTEMPT_01_INSTRUMENT_ABORT", "ATTEMPT_02_INSTRUMENT_ABORT",
    "ATTEMPT_03_INSTRUMENT_ABORT", "ATTEMPT_04_SUPERSEDED_BEFORE_PROBING",
])
def test_every_superseded_attempt_is_preserved_with_its_own_record(directory):
    path = M117 / directory
    assert path.is_dir(), directory
    assert (path / "README.md").is_file(), directory


def test_the_outcome_discloses_that_revisions_followed_observations():
    text = _flat(OUTCOME)
    assert "five apparatus revisions" in text.lower()
    assert "followed real endpoint observations" in text
    assert "not claim that its route-selection process was prospectively clean" in text


def test_the_result_is_characterised_as_calibration_not_science():
    text = _flat(OUTCOME)
    assert "DEVELOPMENT calibration result" in text
    assert "not** evidence for the Genesis scientific proposition" in text
    assert "advances **no** generality gate" in text


# -------------------------------------------------------------------------------------------
# The instrument findings survive as findings
# -------------------------------------------------------------------------------------------

def test_all_seven_instrument_findings_are_recorded():
    text = OUTCOME.read_text(encoding="utf-8")  # section split needs real newlines
    section = text[text.index("## Instrument findings preserved"):text.index("## Corrigenda")]
    for n in range(1, 8):
        assert re.search(r"^%d\.\s" % n, section, re.M), "finding %d missing" % n
    assert "9 of 9\n   feature classes unenforced" in section or "9 of 9" in section
    assert "all nine" in section
    assert "68,368" in section


def test_the_provider_claim_is_marked_suggestive_not_causal():
    text = _flat(OUTCOME)
    assert "suggestive instrument evidence, not a causal scientific conclusion" in text
    assert "not** a prospectively randomized within-run comparison" in text


def test_no_cause_is_invented_for_the_run_to_run_instability():
    text = OUTCOME.read_text(encoding="utf-8")
    section = text[text.index("6. **Run-to-run instability"):text.index("7. **The reasoning")]
    assert "No cause is claimed" in section
    assert "nothing here establishes that as the explanation" in section


def test_both_corrigenda_are_explicit():
    text = OUTCOME.read_text(encoding="utf-8")
    flat = _flat(OUTCOME)
    section = flat[flat.index("## Corrigenda"):]
    assert "refuted" in section
    assert "It never observed them" in section
    assert "corrected explicitly rather than quietly amended" in flat
