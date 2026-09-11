"""Regression for the canonical bounded DEVELOPMENT metamorphosis reproducer."""
from __future__ import annotations

import json

from genesis import program_forms
from genesis import trust_root as tr
from scripts import run_genesis_metamorphosis_reproduction as reproduce


def test_canonical_reproducer_crosses_fresh_interpreters_and_emits_self_checking_report(tmp_path):
    output = tmp_path / "canonical-reproduction"
    report = reproduce.run_reproduction(output)

    assert report["classification"] == "DEVELOPMENT_REPRODUCTION"
    assert report["passed"] is True
    assert report["fresh_interpreter_boundaries"] == 2
    assert all(report["checks"].values())
    assert report["evidence"]["final_body"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert report["evidence"]["final_body"]["operations"] == ["square", "square"]
    assert report["evidence"]["causal_dependency"]["established"] is True
    assert report["evidence"]["causal_dependency"]["newly_solved_lost_without_acquisition"] == ["m1"]
    assert report["evidence"]["metamorphosis"]["succeeded"] is True

    stored = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert stored == report
    digest_payload = {
        key: value for key, value in stored.items() if key != "reproduction_digest"
    }
    assert stored["reproduction_digest"] == tr.digest_of(digest_payload)

    for phase in (1, 2, 3):
        phase_record = json.loads(
            (output / f"phase-{phase}.json").read_text(encoding="utf-8")
        )
        assert phase_record["schema"] == reproduce.SCHEMA
        assert phase_record["phase"] == phase


def test_canonical_reproducer_refuses_to_mix_with_existing_output(tmp_path):
    output = tmp_path / "not-empty"
    output.mkdir()
    (output / "foreign.txt").write_text("do not overwrite", encoding="utf-8")

    try:
        reproduce.run_reproduction(output)
    except RuntimeError as error:
        assert "output directory must be empty" in str(error)
    else:  # pragma: no cover
        raise AssertionError("reproducer overwrote a non-empty output directory")
