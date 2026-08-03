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
    compile_policy_to_dfa,
    execute_trans_substrate_lifecycle,
)
from metamorphosis.m033_combined_evaluation import paired_outcome
from metamorphosis.m033_evaluation import held_out_quality_per_mille
from metamorphosis.m033_memory_controls import execute_memory_guided_task
from metamorphosis.m033_post_migration_plasticity import (
    LineageVariant,
    build_fresh_b_lineage,
    build_packet_derived_lineage,
    build_unchanged_parent_lineage,
    execute_control_task,
)
from metamorphosis.m033_structural_tasks import (
    COMBINED_CONTROL_SEED_START,
    STRUCTURAL_TEMPLATE_COUNT,
    generate_combined_control_task,
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

ALL_VARIANTS = LEARNING_VARIANTS + (LineageVariant.OUTPUT_ONLY,)


def _packet(seed: int) -> str:
    outcome = execute_trans_substrate_lifecycle(
        VersionedCodeBody("policy", PRE_REWRITE_SOURCE),
        ToolRegistry(),
        PRE_REWRITE_DEVELOPMENT,
        PRE_REWRITE_DEVELOPMENT,
        state_count=2,
        accepting_states=(False, True),
        machine=make_development_positive_machine(seed),
        search_seed=340_000 + seed,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    if not outcome.committed or outcome.packet_json is None:
        raise RuntimeError(f"M032 combined packet failed for seed {seed}: {outcome.reason}")
    return outcome.packet_json


def _lineages(packet_json: str, seed: int, task):
    return {
        LineageVariant.COMPLETE: build_packet_derived_lineage(
            packet_json, LineageVariant.COMPLETE
        ),
        LineageVariant.FRESH_B: build_fresh_b_lineage(
            task.baseline_source,
            task.function_name,
            state_count=task.state_count,
            accepting_states=task.accepting_states,
            machine=make_development_positive_machine(seed),
            search_seed=341_000 + seed,
        ),
        LineageVariant.UNCHANGED_PARENT: build_unchanged_parent_lineage(
            packet_json,
            state_count=2,
            accepting_states=(False, True),
            machine=make_development_positive_machine(seed),
            search_seed=342_000 + seed,
        ),
        LineageVariant.LEARNING_STATE_ABLATED: build_packet_derived_lineage(
            packet_json, LineageVariant.LEARNING_STATE_ABLATED
        ),
        LineageVariant.LEARNED_TOOLS_ABLATED: build_packet_derived_lineage(
            packet_json, LineageVariant.LEARNED_TOOLS_ABLATED
        ),
        LineageVariant.OUTPUT_ONLY: build_packet_derived_lineage(
            packet_json, LineageVariant.OUTPUT_ONLY
        ),
    }


def _execute(lineage, task) -> dict[str, object]:
    if lineage.variant is LineageVariant.OUTPUT_ONLY:
        result = execute_control_task(lineage, task)
        payload = json.loads(result.canonical_json())
        payload["total_candidate_evaluations"] = result.candidates_evaluated
        payload["memory_decision"] = None
    else:
        result = execute_memory_guided_task(lineage, task)
        payload = json.loads(result.canonical_json())
        payload["candidates_evaluated"] = result.total_candidate_evaluations

    final_dfa = compile_policy_to_dfa(
        str(payload["final_source"]),
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        initial_state=task.initial_state,
    )
    payload["held_out_quality_per_mille"] = held_out_quality_per_mille(
        final_dfa,
        task.target_dfa,
        task.held_out_words,
    )
    payload["cost_after_task"] = lineage.construction_cost.to_dict()
    return payload


def _paired_outcome(
    row: dict[str, object],
    control: LineageVariant,
) -> int:
    results = row["results"]
    return paired_outcome(
        results[LineageVariant.COMPLETE.value],
        results[control.value],
    )


def run(seed_start: int, seed_count: int) -> dict[str, object]:
    if seed_start < COMBINED_CONTROL_SEED_START:
        raise ValueError("M033 combined calibration must start at seed 3072 or above")
    if seed_start % STRUCTURAL_TEMPLATE_COUNT:
        raise ValueError("seed_start must align to the four-template cycle")
    if seed_count < STRUCTURAL_TEMPLATE_COUNT or seed_count % STRUCTURAL_TEMPLATE_COUNT:
        raise ValueError("seed_count must be a positive multiple of four")

    rows: list[dict[str, object]] = []
    for seed in range(seed_start, seed_start + seed_count):
        record = generate_combined_control_task(seed)
        task = record.task
        packet_json = _packet(seed)
        lineages = _lineages(packet_json, seed, task)
        results = {
            variant.value: _execute(lineages[variant], task)
            for variant in ALL_VARIANTS
        }
        rows.append(
            {
                "seed": seed,
                "template_id": record.template_id,
                "task_sha256": record.sha256(),
                "results": results,
            }
        )

    def value(row, variant: LineageVariant, key: str):
        return row["results"][variant.value][key]

    def outcome_counts(control: LineageVariant) -> dict[str, int]:
        outcomes = [_paired_outcome(row, control) for row in rows]
        return {
            "wins": outcomes.count(1),
            "ties": outcomes.count(0),
            "losses": outcomes.count(-1),
        }

    by_template: dict[str, dict[str, object]] = {}
    for template_id in range(STRUCTURAL_TEMPLATE_COUNT):
        template_rows = [row for row in rows if row["template_id"] == template_id]
        template_summary: dict[str, object] = {
            "seeds": len(template_rows),
        }
        for variant in LEARNING_VARIANTS:
            template_summary[f"{variant.value}_exact"] = sum(
                bool(value(row, variant, "exact")) for row in template_rows
            )
            template_summary[f"{variant.value}_candidate_median"] = median(
                int(value(row, variant, "total_candidate_evaluations"))
                for row in template_rows
            )
            template_summary[f"{variant.value}_memory_accepted"] = sum(
                bool(value(row, variant, "memory_decision")["accepted"])
                for row in template_rows
            )
        for control in LEARNING_VARIANTS[1:]:
            outcomes = [_paired_outcome(row, control) for row in template_rows]
            template_summary[f"complete_vs_{control.value}"] = {
                "wins": outcomes.count(1),
                "ties": outcomes.count(0),
                "losses": outcomes.count(-1),
            }
        by_template[str(template_id)] = template_summary

    summary: dict[str, object] = {
        "primary_seed_block_observed": False,
        "seed_start": seed_start,
        "seed_count": seed_count,
        "templates_covered": sorted({int(row["template_id"]) for row in rows}),
        "unique_task_digests": len({str(row["task_sha256"]) for row in rows}),
        "output_only_attempts": sum(
            bool(value(row, LineageVariant.OUTPUT_ONLY, "attempted")) for row in rows
        ),
        "by_template": by_template,
    }
    for variant in LEARNING_VARIANTS:
        summary[f"all_{variant.value}_exact"] = all(
            bool(value(row, variant, "exact")) for row in rows
        )
        summary[f"all_{variant.value}_held_out_exact"] = all(
            int(value(row, variant, "held_out_quality_per_mille")) == 1000
            for row in rows
        )
        summary[f"{variant.value}_candidate_median"] = median(
            int(value(row, variant, "total_candidate_evaluations")) for row in rows
        )
        summary[f"{variant.value}_memory_accepted"] = sum(
            bool(value(row, variant, "memory_decision")["accepted"])
            for row in rows
        )
    for control in LEARNING_VARIANTS[1:]:
        summary[f"complete_vs_{control.value}"] = outcome_counts(control)

    return {
        "version": "m033-combined-calibration/1",
        "cost_units_are_separate": True,
        "seed_start": seed_start,
        "seed_count": seed_count,
        "rows": rows,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=COMBINED_CONTROL_SEED_START)
    parser.add_argument("--seeds", type=int, default=32)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/M033_combined_calibration.json"),
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
