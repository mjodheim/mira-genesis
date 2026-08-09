"""Verify the historical M071 agent and bridge before external task selection."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = ROOT / "experiments" / "M071" / "AGENT_DESIGN_FREEZE.json"


def _git(*args: str, root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout).strip())
    return completed.stdout.strip()


def verify_freeze(path: Path = DEFAULT_FREEZE, *, root: Path = ROOT) -> Mapping[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != "m071-agent-design-freeze-v1":
        raise ValueError("unexpected M071 design-freeze schema")
    design = value.get("exact_agent_design_commit")
    bridge = value.get("exact_harbor_bridge_commit")
    blobs = value.get("blobs")
    if not isinstance(design, str) or not isinstance(bridge, str):
        raise ValueError("M071 design freeze lacks exact commits")
    if not isinstance(blobs, dict) or not blobs:
        raise ValueError("M071 design freeze lacks its blob map")
    for commit in (design, bridge):
        _git("cat-file", "-e", f"{commit}^{{commit}}", root=root)
        _git("merge-base", "--is-ancestor", commit, "HEAD", root=root)
    observed_commits: set[str] = set()
    for relative, record in sorted(blobs.items()):
        if not isinstance(relative, str) or not isinstance(record, dict):
            raise ValueError("M071 design freeze contains an invalid blob entry")
        commit = record.get("commit")
        expected = record.get("blob")
        if commit not in {design, bridge} or not isinstance(expected, str):
            raise ValueError(f"invalid M071 commit/blob binding for {relative}")
        observed = _git("rev-parse", f"{commit}:{relative}", root=root)
        if observed != expected:
            raise ValueError(f"frozen M071 blob mismatch for {relative}")
        observed_commits.add(commit)
    if observed_commits != {design, bridge}:
        raise ValueError("M071 blob map does not cover both frozen commits")
    commitment_value = {
        "exact_agent_design_commit": design,
        "exact_harbor_bridge_commit": bridge,
        "m071_pretarget_protocol_version": value.get("m071_pretarget_protocol_version"),
        "blobs": blobs,
    }
    observed_commitment = hashlib.sha256(json.dumps(
        commitment_value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if observed_commitment != value.get("design_commitment_sha256"):
        raise ValueError("M071 agent-design commitment mismatch")
    if any(value.get(field) is not False for field in (
        "benchmark_revision_pinned", "benchmark_task_identifier_selected",
        "benchmark_task_content_inspected", "benchmark_task_executed",
        "scientific_result_exists",
    )):
        raise ValueError("M071 pre-target freeze improperly contains a target or result")
    return {
        "status": value["status"],
        "exact_agent_design_commit": design,
        "exact_harbor_bridge_commit": bridge,
        "design_commitment_sha256": observed_commitment,
        "frozen_blob_count": len(blobs),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    args = parser.parse_args()
    print(json.dumps(verify_freeze(args.freeze), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
