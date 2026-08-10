#!/usr/bin/env python3
"""Run the committed M073 capsule on committed holdouts with the teacher absent.

This runner intentionally has no path or import for teacher responses or training tasks. The
lineage transformation sees only one serialized capsule and one held-out source at a time. The
separate evaluator-owned domain module decides success after transformation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import m073_domain
from mira_core.skills import SkillCapsule, SkillInductionError, TeacherCallTrap, apply_skill_capsule


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
CAPSULE_PATH = M073 / "SKILL_CAPSULE.json"
HOLDOUT_PATH = M073 / "HOLDOUT_TASKS.json"
OUTPUT_PATH = M073 / "HOLDOUT_LINEAGE_RESULT.json"


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _task(record: object) -> m073_domain.RepairTask:
    if not isinstance(record, dict):
        raise ValueError("M073 holdout task record is malformed")
    seed = record.get("seed")
    if not isinstance(seed, int):
        raise ValueError("M073 holdout seed is malformed")
    generated = m073_domain.generate_division_repair_task(seed, split="holdout")
    if record.get("task_id") != generated.task_id or record.get("source") != generated.source:
        raise ValueError("M073 holdout record differs from the frozen generator")
    if record.get("source_sha256") != m073_domain.source_sha256(generated.source):
        raise ValueError("M073 holdout source digest mismatch")
    return generated


def run(
    capsule_path: Path = CAPSULE_PATH, holdout_path: Path = HOLDOUT_PATH,
) -> dict[str, object]:
    capsule = SkillCapsule.from_dict(json.loads(Path(capsule_path).read_text(encoding="utf-8")))
    holdouts = json.loads(Path(holdout_path).read_text(encoding="utf-8"))
    if holdouts.get("schema") != "m073-holdout-task-materialization-v1":
        raise ValueError("unexpected M073 holdout schema")
    if holdouts.get("capsule_sha256") != capsule.capsule_sha256:
        raise ValueError("M073 holdouts were not materialized against this capsule")
    if holdouts.get("task_count") != 12:
        raise ValueError("M073 holdout count differs from preregistration")
    records = holdouts.get("tasks")
    if not isinstance(records, list) or len(records) != 12:
        raise ValueError("M073 holdout task records are incomplete")

    trap = TeacherCallTrap()
    outcomes: list[dict[str, object]] = []
    total_case_failures = 0
    for record in records:
        task = _task(record)
        rewritten: str | None = None
        rewrite_error: str | None = None
        try:
            rewritten = apply_skill_capsule(capsule, task.source)
            evidence = m073_domain.repair_case_results(task, rewritten)
        except SkillInductionError as exc:
            rewrite_error = str(exc)
            evidence = {
                "structural_error": "capsule_application_failed",
                "case_count": len(m073_domain.EVALUATION_CASES),
                "case_failures": len(m073_domain.EVALUATION_CASES),
                "passed": False,
                "cases": [],
            }
        total_case_failures += int(evidence["case_failures"])
        outcomes.append({
            "task_id": task.task_id,
            "source_sha256": m073_domain.source_sha256(task.source),
            "rewritten_sha256": (
                m073_domain.source_sha256(rewritten) if rewritten is not None else None
            ),
            "rewrite_error": rewrite_error,
            "evaluator": evidence,
            "passed": evidence["passed"],
        })

    result: dict[str, object] = {
        "schema": "m073-holdout-lineage-result-v1",
        "status": "model_removed_holdout_execution_completed",
        "capsule_sha256": capsule.capsule_sha256,
        "holdout_materialization_sha256": holdouts.get("holdout_materialization_sha256"),
        "teacher_calls": trap.calls,
        "external_model_imported_or_invoked": False,
        "network_required": False,
        "teacher_responses_read": False,
        "training_tasks_read": False,
        "holdouts_passed": sum(1 for outcome in outcomes if outcome["passed"] is True),
        "holdouts_total": len(outcomes),
        "case_failures": total_case_failures,
        "outcomes": outcomes,
        "scientific_result_exists": False,
    }
    result["lineage_result_sha256"] = _canonical_sha(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capsule", type=Path, default=CAPSULE_PATH)
    parser.add_argument("--holdouts", type=Path, default=HOLDOUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("M073 lineage holdout result already exists; refusing overwrite")
    result = run(args.capsule, args.holdouts)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "case_failures": result["case_failures"],
        "holdouts_passed": result["holdouts_passed"],
        "holdouts_total": result["holdouts_total"],
        "teacher_calls": result["teacher_calls"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
