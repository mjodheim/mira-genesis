"""Canonical subprocess-level regression for the Genesis v2 Open Metamorphosis reproducer."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_canonical_open_metamorphosis_reproducer_crosses_two_fresh_process_boundaries(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "open-metamorphosis"
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "run_genesis_open_metamorphosis_reproduction.py"),
            "--output-dir",
            str(output),
        ],
        cwd=root,
        check=True,
    )

    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["classification"] == "DEVELOPMENT_OPEN_METAMORPHOSIS_REPRODUCTION"
    assert report["passed"] is True
    assert report["fresh_interpreter_boundaries"] == 2
    assert report["checks"] and all(report["checks"].values())
    assert report["reproduction_digest"]

    phase1 = json.loads((output / "phase-1.json").read_text(encoding="utf-8"))
    phase2 = json.loads((output / "phase-2.json").read_text(encoding="utf-8"))
    phase3 = json.loads((output / "phase-3.json").read_text(encoding="utf-8"))
    assert phase1["phase"] == 1
    assert phase2["phase"] == 2
    assert phase3["phase"] == 3
    assert phase2["before"]["state_digest"] == phase1["after"]["state_digest"]
    assert phase3["before"]["state_digest"] == phase2["after"]["state_digest"]
    assert phase3["after"]["state_digest"] == phase3["before"]["state_digest"]
