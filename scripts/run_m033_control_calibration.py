from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median

from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m020_self_rewrite import Case, ToolRegistry, VersionedCodeBody
from metamorphosis.m032_trans_substrate_lifecycle import (
    PortableLearningState,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_post_migration_plasticity import (
    ControlTaskFamily,
    LineageVariant,
    build_fresh_b_lineage,
    build_packet_derived_lineage,
    build_unchanged_parent_lineage,
    execute_control_task,
    generate_control_task,
)


PRE_REWRITE_SOURCE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

PRE_REWRITE_DEVELOPMENT = (
    Case((0, 0), 0),
    Case((0, 1), 0),
    Case((1, 0), 0),
    Case((1, 1), 1),
)

LEARNING_STATE = PortableLearningState(
    memory=((0, 1, 1), (1, 0, 1)),
    uncertainty=(3, 1),
    exploration_frontier=((1, 1), (0, 0)),
)

LEARNING_VARIANTS = (
    LineageVariant.COMPLETE,
    LineageVariant.FRESH_B,
    LineageVariant.UNCHANGED_PARENT,
    LineageVariant.LEARNING_STATE_ABLATED,
    LineageVariant.LEARNED_TOOLS_ABLATED,
)


def _packet(seed: int) -> str:
    outcome = execute_trans_substrate_lifecycle(
        VersionedCodeBody("policy", PRE_REWRITE_SOURCE),
        ToolRegistry(),
        PRE_REWRITE_DEVELOPMENT,
        PRE_REWRITE_DEVELOPMENT,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(seed),
        search_seed=330_000 + seed,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    if not outcome.committed or outcome.packet_json is None:
        raise RuntimeError(f"M032 control packet failed for seed {seed}: {outcome.reason}")
    return outcome.packet_json


def _lineages(packet_json: str, seed: int, family: ControlTaskFamily):
    task = generate_control_task(seed, family)
    complete = build_packet_derived_lineage(packet_json, LineageVariant.COMPLETE)
    state_ablated = build_packet_derived_lineage(
        packet_json, LineageVariant.LEARNING_STATE_ABLATED
    )
    tools_ablated = build_packet_derived_lineage(
        packet_json, LineageVariant.LEARNED_TOOLS_ABLATED
    )
    output_only = build_packet_derived_lineage(
        packet_json, LineageVariant.OUTPUT_ONLY
    )
    fresh = build_fresh_b_lineage(
        task.baseline_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        machine=make_development_positive_machine(seed),
        search_seed=331_000 + seed,
    )
    parent = build_unchanged_parent_lineage(
        packet_json,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(seed),
        search_seed=332_000 + seed,
    )
    return task, {
        LineageVariant.COMPLETE: complete,
        LineageVariant.FRESH_B: fresh,
        LineageVariant.UNCHANGED_PARENT: parent,
        LineageVariant.OUTPUT_ONLY: output_only,
        LineageVariant.LEARNING_STATE_ABLATED: state_ablated,
        LineageVariant.LEARNED_TOOLS_ABLATED: tools_ablated,
    }


def _result_dict(result) -> dict[str, object]:
    return json.loads(result.canonical_json())


def run(seed_start: int, seed_count: int) -> dict[str, object]:
    if seed_start < 1024:
        raise ValueError("M033 calibration seeds must start at 1024 or above")
    if seed_count < 1:
        raise ValueError("seed_count must be positive")

    rows: list[dict[str, object]] = []
    for seed in range(seed_start, seed_start + seed_count):
        packet_json = _packet(seed)
        for family in ControlTaskFamily:
            task, lineages = _lineages(packet_json, seed, family)
            results = {
                variant.value: _result_dict(execute_control_task(lineage, task))
                for variant, lineage in lineages.items()
            }
            rows.append(
                {
                    "seed": seed,
                    "family": family.value,
                    "task_sha256": task.sha256(),
                    "results": results,
                }
            )

    positive = [row for row in rows if row["family"] == "positive_tool"]
    negative = [row for row in rows if row["family"] == "negative_tool"]

    def candidates(row, variant: LineageVariant) -> int:
        return int(row["results"][variant.value]["candidates_evaluated"])

    def exact(row, variant: LineageVariant) -> bool:
        return bool(row["results"][variant.value]["exact"])

    summary: dict[str, object] = {
        "primary_seed_block_observed": False,
        "all_positive_complete_exact": all(
            exact(row, LineageVariant.COMPLETE) for row in positive
        ),
        "all_positive_fresh_exact": all(
            exact(row, LineageVariant.FRESH_B) for row in positive
        ),
        "all_positive_parent_exact": all(
            exact(row, LineageVariant.UNCHANGED_PARENT) for row in positive
        ),
        "positive_complete_better_than_fresh": sum(
            candidates(row, LineageVariant.COMPLETE)
            < candidates(row, LineageVariant.FRESH_B)
            for row in positive
        ),
        "positive_complete_better_than_parent": sum(
            candidates(row, LineageVariant.COMPLETE)
            < candidates(row, LineageVariant.UNCHANGED_PARENT)
            for row in positive
        ),
        "positive_complete_candidate_median": median(
            candidates(row, LineageVariant.COMPLETE) for row in positive
        ),
        "positive_fresh_candidate_median": median(
            candidates(row, LineageVariant.FRESH_B) for row in positive
        ),
        "positive_parent_candidate_median": median(
            candidates(row, LineageVariant.UNCHANGED_PARENT) for row in positive
        ),
        "positive_state_ablated_candidate_median": median(
            candidates(row, LineageVariant.LEARNING_STATE_ABLATED)
            for row in positive
        ),
        "positive_tools_ablated_candidate_median": median(
            candidates(row, LineageVariant.LEARNED_TOOLS_ABLATED)
            for row in positive
        ),
        "negative_complete_better_than_fresh": sum(
            candidates(row, LineageVariant.COMPLETE)
            < candidates(row, LineageVariant.FRESH_B)
            for row in negative
        ),
        "negative_complete_candidate_median": median(
            candidates(row, LineageVariant.COMPLETE) for row in negative
        ),
        "negative_fresh_candidate_median": median(
            candidates(row, LineageVariant.FRESH_B) for row in negative
        ),
        "output_only_attempts": sum(
            bool(row["results"][LineageVariant.OUTPUT_ONLY.value]["attempted"])
            for row in rows
        ),
    }

    return {
        "version": "m033-control-calibration/1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "families": [family.value for family in ControlTaskFamily],
        "learning_variants": [variant.value for variant in LEARNING_VARIANTS],
        "rows": rows,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=1024)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/M033_control_calibration.json"),
    )
    args = parser.parse_args()

    payload = run(args.seed_start, args.seeds)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(raw, encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True, indent=2))
    print(f"sha256={hashlib.sha256(raw.encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
