from __future__ import annotations

import json
from pathlib import Path

import check_m071_external_result as external


ROOT = Path(__file__).resolve().parents[1]


def test_m071_passes_narrow_external_threshold_without_overclaim() -> None:
    result = json.loads(
        (ROOT / "experiments" / "M071" / "EXTERNAL_RESULT.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["status"] == "passed_falsifiable_threshold"
    assert result["claim_passed"] is True
    assert [trial["reward"] for trial in result["trials"]] == [0.0, 1.0]
    assert [trial["reward"] for trial in result["nop_trials"]] == [0.0, 0.0]
    assert all(trial["network_mode"] == "no-network" for trial in result["trials"])
    assert all(trial["agent_claimed_success"] is False for trial in result["trials"])
    assert result["controls"]["all_jobs_harbor_exceptions"] == 0
    assert result["controls"]["all_jobs_retries"] == 0
    assert result["controls"]["task_replacement_performed"] is False
    assert result["attribution"]["genesis_gate_2_evidence"] is False
    assert result["attribution"]["generality_gate_advanced"] is False
    assert result["attribution"]["governance_layer_isolating_baseline_present"] is False
    assert result["preservation"] == {
        "local_python_version": "3.14",
        "passed": 1225,
        "repository_integrity_passed": True,
        "seconds": 2257.69,
        "skipped": 2,
    }


def test_m071_memory_and_external_artifacts_verify() -> None:
    verified = external.verify_result()
    assert verified["status"] == "passed_falsifiable_threshold"
    assert verified["successes"] == 1
    assert verified["tasks"] == 2
    assert len(verified["result_sha256"]) == 64
