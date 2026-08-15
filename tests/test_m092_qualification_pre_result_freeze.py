from __future__ import annotations

from pathlib import Path


NOTE = Path("experiments/M092/QUALIFICATION_PRE_RESULT_FREEZE.md")


def test_pre_result_freeze_note_contains_no_materialized_result_artifact() -> None:
    text = NOTE.read_text(encoding="utf-8")
    assert "pre-result, non-qualifying infrastructure only" in text
    assert "acceptance order of the domain-separated counter-mode digest" in text
    assert "No second target-specific" in text or "No second target-specific" in text.replace("\n", " ")
    assert "SUBSTRATE_B.json" not in text
    assert "CANONICAL_SEARCH_RESULT.json" not in text
    assert "INDEPENDENT_REPRODUCTION_RESULT.json" not in text


def test_freeze_note_records_family_b_composition_before_hidden_draws() -> None:
    text = NOTE.read_text(encoding="utf-8")
    assert 'APPLY_UNARY(slot 0, "neg")' in text
    assert 'APPLY_UNARY(slot 0, "inc")' in text
    assert "hidden values are materialized" in text
    assert "Accepted candidates are not lexicographically re-sorted" in text
