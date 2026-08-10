from __future__ import annotations

import json
from pathlib import Path

import check_m073_result as result_check


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "experiments" / "M073" / "RESULT.json"


def test_m073_preserved_result_is_positive_without_overclaim() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "passed_preregistered_threshold"
    assert result["claim_passed"] is True
    assert result["observed"] == {
        "capsule_committed_before_holdout_materialization": True,
        "complete_lineage_case_failures": 0,
        "complete_lineage_holdouts_passed": 12,
        "complete_lineage_holdouts_total": 12,
        "corrupted_teacher_capsules_induced": 0,
        "holdout_model_calls": 0,
        "memorizer_holdouts_passed": 0,
        "no_capsule_holdouts_passed": 0,
        "teacher_valid_repairs": 4,
        "unique_capsules_induced": 1,
    }
    assert result["capsule_sha256"] == (
        "444a8a548d6955ac85795fe9d4fd18d4a0a0aa6d731a94dbd3a4ca0f560f8620"
    )
    assert result["result_sha256"] == (
        "edaf03b4cf922890d010ecdd838de67c9569342b27a6848fae34ab430db03a2e"
    )
    assert result["attribution"]["holdout_transformations_are_model_free"] is True
    assert result["attribution"]["teacher_is_external_and_not_lineage_owned"] is True
    for field in (
        "agi_claim", "general_software_engineering_claim", "genesis_gate_2_or_3_completed",
        "safe_deployment_claim",
    ):
        assert result["attribution"][field] is False


def test_m073_result_recomputes_from_preserved_phase_artifacts() -> None:
    assert result_check.verify_result() == {
        "status": "passed_preregistered_threshold",
        "claim_passed": True,
        "teacher_valid_repairs": 4,
        "holdouts_passed": 12,
        "holdouts_total": 12,
        "holdout_case_failures": 0,
        "holdout_model_calls": 0,
        "no_capsule_holdouts_passed": 0,
        "memorizer_holdouts_passed": 0,
        "capsule_sha256": (
            "444a8a548d6955ac85795fe9d4fd18d4a0a0aa6d731a94dbd3a4ca0f560f8620"
        ),
        "result_sha256": (
            "edaf03b4cf922890d010ecdd838de67c9569342b27a6848fae34ab430db03a2e"
        ),
    }
