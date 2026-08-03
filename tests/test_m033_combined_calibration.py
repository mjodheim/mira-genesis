from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from metamorphosis.m033_combined_evaluation import paired_outcome
from metamorphosis.m033_post_migration_plasticity import LineageVariant
from metamorphosis.m033_structural_tasks import COMBINED_CONTROL_SEED_START


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_m033_combined_calibration.py"


def _payload(exact: bool, quality: int, candidates: int) -> dict[str, object]:
    return {
        "exact": exact,
        "held_out_quality_per_mille": quality,
        "total_candidate_evaluations": candidates,
    }


def test_paired_outcome_prioritises_exactness_then_quality_then_cost():
    assert paired_outcome(_payload(True, 1000, 999), _payload(False, 1000, 1)) == 1
    assert paired_outcome(_payload(False, 900, 999), _payload(False, 800, 1)) == 1
    assert paired_outcome(_payload(True, 1000, 10), _payload(True, 1000, 20)) == 1
    assert paired_outcome(_payload(True, 1000, 20), _payload(True, 1000, 10)) == -1
    assert paired_outcome(_payload(True, 1000, 10), _payload(True, 1000, 10)) == 0


def test_combined_calibration_cli_covers_all_lineages_without_primary_observation(
    tmp_path: Path,
):
    output = tmp_path / "combined.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--seed-start",
            str(COMBINED_CONTROL_SEED_START),
            "--seeds",
            "4",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["version"] == "m033-combined-calibration/1"
    assert payload["seed_start"] == COMBINED_CONTROL_SEED_START
    assert payload["seed_count"] == 4
    assert summary["primary_seed_block_observed"] is False
    assert summary["templates_covered"] == [0, 1, 2, 3]
    assert summary["unique_task_digests"] == 4
    assert summary["output_only_attempts"] == 0

    for variant in (
        LineageVariant.COMPLETE,
        LineageVariant.FRESH_B,
        LineageVariant.UNCHANGED_PARENT,
        LineageVariant.LEARNING_STATE_ABLATED,
        LineageVariant.LEARNED_TOOLS_ABLATED,
    ):
        assert summary[f"all_{variant.value}_exact"] is True
        assert summary[f"all_{variant.value}_held_out_exact"] is True

    assert summary["fresh_b_memory_accepted"] == 0
    assert summary["learning_state_ablated_memory_accepted"] == 0
    assert summary["complete_memory_accepted"] > 0
