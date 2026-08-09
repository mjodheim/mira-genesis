from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_m070_protocol_fixes_attempts_network_images_and_threshold() -> None:
    protocol = json.loads(
        (ROOT / "experiments" / "M070" / "EXECUTION_PROTOCOL.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["status"] == "frozen_before_selected_task_execution"
    assert protocol["selection"]["selected"] == [
        "rstan-to-pystan", "llm-inference-batching-scheduler",
    ]
    assert protocol["attempt_policy"]["mira_attempts_per_task"] == 1
    assert protocol["attempt_policy"]["nop_attempts_per_task"] == 1
    assert protocol["attempt_policy"]["replacement_permitted"] is False
    assert protocol["network"]["agent_phase"] == "no-network"
    assert all(
        "@sha256:" in image for image in protocol["images"].values()
    )
    assert "at least 1.0" in protocol["failure_classification"]["positive"]
    assert protocol["required_positive_controls"]["agent_claimed_success"] is False
