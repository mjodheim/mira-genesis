from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import run_m103_qualification as runner


ROOT = Path(__file__).resolve().parents[1]


RESULT_RAW_SHA256 = "6d89f26f994124ef7207ed1c580a7a72cd468a83d3f8787c1085a5b8e062ff26"
RESULT_DIGEST = "d2ace036a29d18be95f2fc5e0eee1285193cf96e8a7d7feebde46f61f96b0a81"
STABLE_EVIDENCE_DIGEST = "6a11fff9b3a4b3a00deee5150fe8884094a3baf09ac307b495a02ccb74617a97"


def test_frozen_protocol_and_negative_canonical_evidence_are_preserved() -> None:
    assert runner.PROTOCOL_PATH.exists()
    assert runner.RESULT_PATH.exists()
    assert not runner.CHECK_PATH.exists()
    result_bytes = runner.RESULT_PATH.read_bytes()
    result = json.loads(result_bytes.decode("ascii"))
    assert hashlib.sha256(result_bytes).hexdigest() == RESULT_RAW_SHA256
    assert result["result_digest"] == RESULT_DIGEST
    assert result["stable_evidence_digest"] == STABLE_EVIDENCE_DIGEST
    failure = json.loads((runner.EXPERIMENT / "CHECKER_FAILURE.json").read_text(encoding="ascii"))
    assert failure["scientific_verdict"] == "negative"
    assert failure["process_exit_code"] == 3
    assert failure["check_report_materialized"] is False


def test_canonical_materialization_refuses_without_distinct_run_authorization() -> None:
    before = runner.RESULT_PATH.read_bytes()
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=False)
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=True)
    assert runner.RESULT_PATH.read_bytes() == before


def test_result_checker_has_no_runtime_import() -> None:
    source = (ROOT / "scripts" / "check_m103_result.py").read_text(encoding="utf-8")
    assert "from metamorphosis import m103_runtime" not in source
    assert "import m103_runtime" not in source
