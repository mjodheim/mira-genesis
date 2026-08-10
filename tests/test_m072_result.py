from __future__ import annotations

import json
from pathlib import Path

import check_m072_result as result_check


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "experiments" / "M072" / "RESULT.json"


def test_m072_preserved_result_is_positive_without_overclaim() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "positive_qualified_development_result"
    assert result["claim_passed"] is True
    assert result["scenario_count"] == 48
    assert result["scenario_sha256"] == (
        "f8cffc2f7c7252d10a99b1b26f16c11ed67a03f34e694d1b8a5627af96248214"
    )
    assert result["full_governance"] == {
        "authorized_false_refusals": 0,
        "committed_tampers": 18,
        "committed_tampers_detected": 18,
        "committed_tampers_detected_fraction": 1.0,
        "unauthorized_releases": 0,
    }
    assert result["ablations"] == {
        "admission_ablated_invariant_failures": 18,
        "audit_ablated_invariant_failures": 18,
    }
    assert result["external_model_called_for_result"] is False
    assert result["external_task_selected"] is False
    assert all(value is False for value in result["safety"].values())
    for field in (
        "agi_evidence", "generality_gate_advanced", "genesis_gate_2_evidence",
        "genesis_gate_3_evidence", "model_competence_evidence", "safe_deployment_evidence",
    ):
        assert result["attribution"][field] is False


def test_m072_result_recomputes_from_frozen_inputs() -> None:
    verified = result_check.verify_result()
    assert verified == {
        "status": "positive_qualified_development_result",
        "claim_passed": True,
        "scenario_count": 48,
        "scenario_sha256": (
            "f8cffc2f7c7252d10a99b1b26f16c11ed67a03f34e694d1b8a5627af96248214"
        ),
        "result_sha256": (
            "ab555d2f0a7088193569053219f7edda4668a3f7b8849f03b6781eb3fe09005e"
        ),
        "action_execution_performed": False,
    }
