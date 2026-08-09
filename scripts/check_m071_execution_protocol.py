#!/usr/bin/env python3
"""Verify repository-local invariants of the frozen M071 execution protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from check_m071_agent_design_freeze import verify_freeze


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "experiments" / "M071" / "EXECUTION_PROTOCOL.json"
SELECTION_PATH = ROOT / "experiments" / "M071" / "TASK_SELECTION.json"


def _git_object_exists(identifier: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{identifier}^{{object}}"],
        cwd=ROOT, capture_output=True, check=False,
    )
    return completed.returncode == 0


def verify_protocol() -> dict[str, object]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    freeze = verify_freeze()
    if protocol["status"] != "frozen_before_any_selected_task_execution":
        raise ValueError("M071 protocol is not in its pre-execution state")
    if protocol["agent"]["design_commit"] != freeze["exact_agent_design_commit"]:
        raise ValueError("M071 protocol design commit differs from freeze")
    if protocol["agent"]["bridge_commit"] != freeze["exact_harbor_bridge_commit"]:
        raise ValueError("M071 protocol bridge commit differs from freeze")
    if protocol["agent"]["design_commitment_sha256"] != freeze["design_commitment_sha256"]:
        raise ValueError("M071 protocol design commitment differs from freeze")
    selected = [entry[1] for entry in selection["selected"]]
    if protocol["selection"]["selected"] != selected:
        raise ValueError("M071 execution pair differs from bound selection")
    if protocol["selection"]["eligible_inventory_sha256"] != selection["inventory_sha256"]:
        raise ValueError("M071 execution inventory differs from selection")
    if protocol["network"]["agent_phase"] != "no-network":
        raise ValueError("M071 agent network is not denied")
    if protocol["attempt_policy"]["replacement_permitted"] is not False:
        raise ValueError("M071 protocol permits task replacement")
    if protocol["attempt_policy"]["scientifically_valid_retry_permitted"] is not False:
        raise ValueError("M071 protocol permits a scientific retry")
    for key in ("design_commit", "bridge_commit", "design_freeze_commit"):
        if not _git_object_exists(protocol["agent"][key]):
            raise ValueError(f"M071 lacks Git object {key}")
    for key in ("rule_commit", "binding_commit"):
        if not _git_object_exists(protocol["selection"][key]):
            raise ValueError(f"M071 lacks Git object {key}")
    canonical = json.dumps(protocol, sort_keys=True, separators=(",", ":"))
    return {
        "protocol_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "selected": selected,
        "status": protocol["status"],
    }


def main() -> None:
    print(json.dumps(verify_protocol(), sort_keys=True))


if __name__ == "__main__":
    main()
