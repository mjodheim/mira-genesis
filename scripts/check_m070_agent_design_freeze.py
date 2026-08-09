"""Verify that the M070 agent design predates and survives external task selection."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = ROOT / "experiments" / "M070" / "AGENT_DESIGN_FREEZE.json"


def _git(*args: str, root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout).strip())
    return completed.stdout.strip()


def verify_freeze(path: Path = DEFAULT_FREEZE, *, root: Path = ROOT) -> Mapping[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != "m070-agent-design-freeze-v1":
        raise ValueError("unexpected M070 design-freeze schema")
    commit = value.get("exact_agent_design_commit")
    blobs = value.get("blobs")
    if not isinstance(commit, str) or not isinstance(blobs, dict) or not blobs:
        raise ValueError("M070 design freeze lacks its commit or blob map")
    _git("cat-file", "-e", f"{commit}^{{commit}}", root=root)
    _git("merge-base", "--is-ancestor", commit, "HEAD", root=root)
    for relative, expected in sorted(blobs.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("M070 design freeze contains an invalid blob entry")
        observed = _git("rev-parse", f"{commit}:{relative}", root=root)
        if observed != expected:
            raise ValueError(f"frozen M070 design blob mismatch for {relative}")
    commitment_value = {
        "exact_agent_design_commit": commit,
        "m070_pretarget_protocol_version": value.get("m070_pretarget_protocol_version"),
        "blobs": blobs,
    }
    observed_commitment = hashlib.sha256(json.dumps(
        commitment_value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if observed_commitment != value.get("design_commitment_sha256"):
        raise ValueError("M070 agent-design commitment mismatch")
    if any(value.get(field) is not False for field in (
        "benchmark_revision_pinned", "benchmark_task_identifier_selected",
        "benchmark_task_content_inspected", "benchmark_task_executed",
        "scientific_result_exists",
    )):
        raise ValueError("M070 pre-target freeze improperly contains a target or result")
    return {
        "status": value["status"],
        "exact_agent_design_commit": commit,
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
