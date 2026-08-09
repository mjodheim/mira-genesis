from __future__ import annotations

import json
from pathlib import Path

import check_m071_execution_protocol as execution


ROOT = Path(__file__).resolve().parents[1]


def test_m071_protocol_fixes_attempts_network_images_and_attribution() -> None:
    protocol = json.loads(
        (ROOT / "experiments" / "M071" / "EXECUTION_PROTOCOL.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["status"] == "frozen_before_any_selected_task_execution"
    assert protocol["selection"]["selected"] == [
        "sqlite-with-gcov", "custom-memory-heap-crash",
    ]
    assert protocol["attempt_policy"]["mira_attempts_per_task"] == 1
    assert protocol["attempt_policy"]["nop_attempts_per_task"] == 1
    assert protocol["attempt_policy"]["replacement_permitted"] is False
    assert protocol["attempt_policy"]["scientifically_valid_retry_permitted"] is False
    assert protocol["network"]["agent_phase"] == "no-network"
    assert all("@sha256:" in image for image in protocol["images"].values())
    assert "at least 1.0" in protocol["failure_classification"]["positive"]
    assert protocol["attribution"]["genesis_gate_2_evidence"] is False
    assert protocol["attribution"]["governance_layer_isolating_baseline_present"] is False


def test_m071_protocol_matches_design_and_selection_commits() -> None:
    result = execution.verify_protocol()
    assert result["selected"] == ["sqlite-with-gcov", "custom-memory-heap-crash"]
    assert result["status"] == "frozen_before_any_selected_task_execution"
    assert len(result["protocol_sha256"]) == 64
