from __future__ import annotations

from metamorphosis.m033_post_migration_plasticity import LineageVariant
from metamorphosis.m033_structural_tasks import COMBINED_CONTROL_SEED_START
from scripts.run_m033_combined_calibration import _paired_outcome, run


def _row(complete: tuple[bool, int, int], control: tuple[bool, int, int]):
    def payload(values: tuple[bool, int, int]) -> dict[str, object]:
        exact, quality, candidates = values
        return {
            "exact": exact,
            "held_out_quality_per_mille": quality,
            "total_candidate_evaluations": candidates,
        }

    return {
        "results": {
            LineageVariant.COMPLETE.value: payload(complete),
            LineageVariant.FRESH_B.value: payload(control),
        }
    }


def test_paired_outcome_prioritises_exactness_then_quality_then_cost():
    control = LineageVariant.FRESH_B
    assert _paired_outcome(_row((True, 1000, 999), (False, 1000, 1)), control) == 1
    assert _paired_outcome(_row((False, 900, 999), (False, 800, 1)), control) == 1
    assert _paired_outcome(_row((True, 1000, 10), (True, 1000, 20)), control) == 1
    assert _paired_outcome(_row((True, 1000, 20), (True, 1000, 10)), control) == -1
    assert _paired_outcome(_row((True, 1000, 10), (True, 1000, 10)), control) == 0


def test_combined_calibration_covers_all_lineages_without_primary_observation():
    payload = run(COMBINED_CONTROL_SEED_START, 4)
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
