"""Run the M022 positive and negative development controls.

This is not a selection-measure comparison and not a canonical evaluation. It answers a
more basic question first: does the repeated-motif audit actually separate an organism
whose language grows during the sequence from an otherwise capable organism that never
absorbs what it finds?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from metamorphosis.m017_engine import OpenSearchOrganism, SelfExtendingOrganism
from metamorphosis.m022_adaptation_stress import (
    audit_summary,
    build_repeated_motif_sequence,
    compare_adaptive_to_frozen,
)

ROOT = Path(__file__).resolve().parents[1]
POSITIVE_MIN_LATE_COST_RATIO_PER_MILLE = 1_500
MIN_COMMON_LATE_PAIRS = 3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "M022_adaptation_smoke.json",
    )
    arguments = parser.parse_args()

    staged = build_repeated_motif_sequence(
        arguments.seed,
        motif_count=3,
        repetitions=4,
        candidate_episodes=30,
    )

    positive = compare_adaptive_to_frozen(
        SelfExtendingOrganism(
            max_symbols=3,
            search_budget=200_000,
            threshold=2,
        ),
        staged,
        late_round_start=2,
        search_budget=200_000,
    )
    negative = compare_adaptive_to_frozen(
        OpenSearchOrganism(max_symbols=3, search_budget=200_000),
        staged,
        late_round_start=2,
        search_budget=200_000,
    )

    positive_summary = audit_summary(positive)
    negative_summary = audit_summary(negative)
    gates = {
        "positive_common_late_pairs": (
            positive.common_late_pairs >= MIN_COMMON_LATE_PAIRS
        ),
        "positive_adaptive_late_not_worse": positive.adaptive_late_not_worse,
        "positive_cost_separation": (
            positive.late_cost_ratio_per_mille
            >= POSITIVE_MIN_LATE_COST_RATIO_PER_MILLE
        ),
        "positive_language_growth": (
            int(positive_summary["macros_after_sequence"]) > 0
        ),
        "negative_solve_counts_equal": (
            negative.adaptive_solved == negative.frozen_solved
        ),
        "negative_cost_ratio_exact": negative.late_cost_ratio_per_mille == 1_000,
        "negative_no_language_growth": (
            int(negative_summary["macros_after_sequence"]) == 0
        ),
    }

    payload = {
        "development_only": True,
        "seed": arguments.seed,
        "sequence_length": len(staged),
        "motif_count": 3,
        "repetitions": 4,
        "late_round_start": 2,
        "positive_min_late_cost_ratio_per_mille": (
            POSITIVE_MIN_LATE_COST_RATIO_PER_MILLE
        ),
        "positive_control": positive_summary,
        "negative_control": negative_summary,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))

    failed = [name for name, passed in gates.items() if not passed]
    if failed:
        raise SystemExit("M022 smoke failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
