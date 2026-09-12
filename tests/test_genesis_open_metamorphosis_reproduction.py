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
    assert report["predecessor_reacquisition_measurement_count"] == 1
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

    # The canonical multi-process run must preserve the stronger causal result, not merely a
    # syntactic invocation edge. In phase 2 the ordinary controller first measures every held
    # operator, then the complete bounded outside image. If L1 is ablated, L1 itself becomes a
    # possible reacquisition; the counterfactual therefore includes that held measurement as well
    # as every candidate that does not invoke L1. L2 must beat the complete measured set.
    reach = phase2["recursive_result"]["dependency_ablation"]["same_round_reach"]
    assert reach["established"] is True
    assert reach["complete_candidate_image_measured"] is True
    assert reach["complete_counterfactual_without_predecessor_image_measured"] is True
    assert reach["predecessor_reacquisition_measurement_count"] == 1
    assert reach["strict_reach_loss_without_predecessor"] is True
    assert reach["noninvoking_candidate_count"] > 0
    assert reach["independent_candidate_count"] > reach["noninvoking_candidate_count"]
    assert (
        reach["winner_selection_score"]
        > reach["best_selection_score_without_invoked_predecessor"]
    )
    assert reach["evidence_digest"]
