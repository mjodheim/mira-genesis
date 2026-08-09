#!/usr/bin/env python3
"""Verify the repository-local invariants of the frozen M070 execution protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "experiments" / "M070" / "EXECUTION_PROTOCOL.json"
DESIGN_PATH = ROOT / "experiments" / "M070" / "AGENT_DESIGN_FREEZE.json"
SELECTION_PATH = ROOT / "experiments" / "M070" / "TASK_SELECTION.json"


def _git_object_exists(identifier: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{identifier}^{{object}}"],
        cwd=ROOT, capture_output=True, check=False,
    )
    return completed.returncode == 0


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

    assert protocol["status"] == "frozen_before_selected_task_execution"
    assert protocol["agent"]["design_commit"] == design["exact_agent_design_commit"]
    assert (
        protocol["agent"]["design_commitment_sha256"]
        == design["design_commitment_sha256"]
    )
    selected = [entry[1] for entry in selection["selected"]]
    assert protocol["selection"]["selected"] == selected
    assert protocol["selection"]["inventory_sha256"] == selection["inventory_sha256"]
    assert protocol["network"]["agent_phase"] == "no-network"
    assert protocol["attempt_policy"]["replacement_permitted"] is False
    assert protocol["attempt_policy"]["mira_attempts_per_task"] == 1
    assert protocol["required_positive_controls"]["agent_claimed_success"] is False
    for key in ("design_commit", "bridge_commit"):
        assert _git_object_exists(protocol["agent"][key]), key
    for key in ("rule_commit", "binding_commit"):
        assert _git_object_exists(protocol["selection"][key]), key

    canonical = json.dumps(protocol, sort_keys=True, separators=(",", ":"))
    print(json.dumps({
        "protocol_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "selected": selected,
        "status": protocol["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
