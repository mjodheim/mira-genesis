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
from metamorphosis.m033_evaluation import held_out_quality_per_mille
from metamorphosis.m033_post_migration_plasticity import (
    LineageVariant,
    build_fresh_b_lineage,
    build_packet_derived_lineage,
    build_unchanged_parent_lineage,
    execute_control_task,
)
from metamorphosis.m033_structural_tasks import (
    STRUCTURAL_CONTROL_SEED_START,
    generate_structural_control_task,
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


VARIANTS = (
    LineageVariant.COMPLETE,
    LineageVariant.FRESH_B,
    LineageVariant.UNCHANGED_PARENT,
    LineageVariant.LEARNED_TOOLS_ABLATED,
    LineageVariant.OUTPUT_ONLY,
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
        search_seed=337_000 + seed,
        learning_state=LEARNING_STATE,
        max_edits=2,
        beam_width=64,
    )
    if not outcome.committed or outcome.packet_json is None:
        raise RuntimeError(f"M032 structural packet failed for seed {seed}: {outcome.reason}")
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
            search_seed=338_000 + seed,
        ),
        LineageVariant.UNCHANGED_PARENT: build_unchanged_parent_lineage(
            packet_json,
            state_count=2,
            accepting_states=(False, True),
            machine=make_development_positive_machine(seed),
            search_seed=339_000 + seed,
        ),
        LineageVariant.LEARNED_TOOLS_ABLATED: build_packet_derived_lineage(
            packet_json, LineageVariant.LEARNED_TOOLS_ABLATED
        ),
        LineageVariant.OUTPUT_ONLY: build_packet_derived_lineage(
            packet_json, LineageVariant.OUTPUT_ONLY
        ),
    }


def run(seed_start: int, seed_count: int) -> dict[str, object]:
    if seed_start < STRUCTURAL_CONTROL_SEED_START:
        raise ValueError("M033 structural calibration must start at seed 2048 or above")
    if seed_count < 4 or seed_count % 4:
        raise ValueError("seed_count must be a positive multiple of four")

    rows: list[dict[str, object]] = []
    for seed in range(seed_start, seed_start + seed_count):
        record = generate_structural_control_task(seed)
        task = record.task
        packet_json = _packet(seed)
        results: dict[str, dict[str, object]] = {}
        for variant, lineage in _lineages(packet_json, seed, task).items():
            result = execute_control_task(lineage, task)
            final_dfa = compile_policy_to_dfa(
                result.final_source,
                task.function_name,
                state_count=task.state_count,
                accepting_states=task.accepting_states,
                initial_state=task.initial_state,
            )
            result_payload = json.loads(result.canonical_json())
            result_payload["held_out_quality_per_mille"] = held_out_quality_per_mille(
                final_dfa,
                task.target_dfa,
                task.held_out_words,
            )
            result_payload["cost_after_task"] = lineage.construction_cost.to_dict()
            results[variant.value] = result_payload
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

    by_template: dict[str, dict[str, object]] = {}
    for template_id in range(4):
        template_rows = [row for row in rows if row["template_id"] == template_id]
        by_template[str(template_id)] = {
            "seeds": len(template_rows),
            "complete_exact": sum(
                bool(value(row, LineageVariant.COMPLETE, "exact"))
                for row in template_rows
            ),
            "fresh_exact": sum(
                bool(value(row, LineageVariant.FRESH_B, "exact"))
                for row in template_rows
            ),
            "complete_better_than_fresh": sum(
                int(value(row, LineageVariant.COMPLETE, "candidates_evaluated"))
                < int(value(row, LineageVariant.FRESH_B, "candidates_evaluated"))
                for row in template_rows
            ),
            "complete_better_than_parent": sum(
                int(value(row, LineageVariant.COMPLETE, "candidates_evaluated"))
                < int(
                    value(
                        row,
                        LineageVariant.UNCHANGED_PARENT,
                        "candidates_evaluated",
                    )
                )
                for row in template_rows
            ),
            "complete_candidate_median": median(
                int(value(row, LineageVariant.COMPLETE, "candidates_evaluated"))
                for row in template_rows
            ),
            "fresh_candidate_median": median(
                int(value(row, LineageVariant.FRESH_B, "candidates_evaluated"))
                for row in template_rows
            ),
            "tools_ablated_candidate_median": median(
                int(
                    value(
                        row,
                        LineageVariant.LEARNED_TOOLS_ABLATED,
                        "candidates_evaluated",
                    )
                )
                for row in template_rows
            ),
        }

    summary = {
        "primary_seed_block_observed": False,
        "seed_start": seed_start,
        "seed_count": seed_count,
        "templates_covered": sorted({int(row["template_id"]) for row in rows}),
        "all_complete_exact": all(
            bool(value(row, LineageVariant.COMPLETE, "exact")) for row in rows
        ),
        "all_fresh_exact": all(
            bool(value(row, LineageVariant.FRESH_B, "exact")) for row in rows
        ),
        "all_complete_held_out_exact": all(
            int(value(row, LineageVariant.COMPLETE, "held_out_quality_per_mille"))
            == 1000
            for row in rows
        ),
        "complete_better_than_fresh": sum(
            int(value(row, LineageVariant.COMPLETE, "candidates_evaluated"))
            < int(value(row, LineageVariant.FRESH_B, "candidates_evaluated"))
            for row in rows
        ),
        "complete_better_than_parent": sum(
            int(value(row, LineageVariant.COMPLETE, "candidates_evaluated"))
            < int(
                value(row, LineageVariant.UNCHANGED_PARENT, "candidates_evaluated")
            )
            for row in rows
        ),
        "complete_better_than_tools_ablated": sum(
            int(value(row, LineageVariant.COMPLETE, "candidates_evaluated"))
            < int(
                value(
                    row,
                    LineageVariant.LEARNED_TOOLS_ABLATED,
                    "candidates_evaluated",
                )
            )
            for row in rows
        ),
        "output_only_attempts": sum(
            bool(value(row, LineageVariant.OUTPUT_ONLY, "attempted"))
            for row in rows
        ),
        "by_template": by_template,
    }

    return {
        "version": "m033-structural-calibration/1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "rows": rows,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=2048)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/M033_structural_calibration.json"),
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
