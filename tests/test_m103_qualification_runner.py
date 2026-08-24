from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import check_m103_result as checker
from scripts import run_m103_qualification as runner


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_protocol_exists_but_canonical_evidence_is_absent() -> None:
    assert runner.PROTOCOL_PATH.exists()
    assert not runner.RESULT_PATH.exists()
    assert not runner.CHECK_PATH.exists()
    report = runner.preflight()
    assert report["pool"]["confirmed"] is True
    assert report["protocol_exists"] is True
    assert report["result_absent"] is True
    assert report["check_report_absent"] is True


def test_canonical_materialization_refuses_without_distinct_run_authorization() -> None:
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=False)
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=True)
    assert not runner.RESULT_PATH.exists()


def test_development_replay_is_stable_and_all_conditions_can_pass() -> None:
    pool = json.loads(runner.POOL_PATH.read_text(encoding="ascii"))
    first = runner.run_experiment(pool)
    second = runner.run_experiment(pool)
    first_stable = runner.stable_projection(first)
    second_stable = runner.stable_projection(second)
    assert first_stable == second_stable
    conditions = checker.evaluate_conditions(first, replay_confirmed=True)
    assert conditions == {f"P{index}": True for index in range(1, 16)}
    assert first["states"]["m102_bytes_conserved_v0_v1_v2_v3"] is True
    assert first["process_boundary"]["scientific_invocations"] >= 35


def test_result_checker_has_no_runtime_import() -> None:
    source = (ROOT / "scripts" / "check_m103_result.py").read_text(encoding="utf-8")
    assert "from metamorphosis import m103_runtime" not in source
    assert "import m103_runtime" not in source
