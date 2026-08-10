#!/usr/bin/env python3
"""Evaluate M073 no-capsule and exact-memorizer controls outside the lineage runner."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import m073_domain


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
TRAINING_PATH = M073 / "TRAINING_TASKS.json"
RESPONSES_PATH = M073 / "TEACHER_RESPONSES.json"
HOLDOUT_PATH = M073 / "HOLDOUT_TASKS.json"
OUTPUT_PATH = M073 / "HOLDOUT_CONTROL_RESULT.json"


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _holdout_tasks(holdouts: dict[str, object]) -> list[m073_domain.RepairTask]:
    if holdouts.get("schema") != "m073-holdout-task-materialization-v1":
        raise ValueError("unexpected M073 holdout schema")
    records = holdouts.get("tasks")
    if not isinstance(records, list) or len(records) != 12:
        raise ValueError("M073 controls require exactly twelve holdouts")
    tasks: list[m073_domain.RepairTask] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("seed"), int):
            raise ValueError("M073 holdout record is malformed")
        task = m073_domain.generate_division_repair_task(record["seed"], split="holdout")
        if record.get("source") != task.source:
            raise ValueError("M073 holdout control source differs from generator")
        tasks.append(task)
    return tasks


def _memorizer(training: dict[str, object], responses: dict[str, object]) -> dict[str, str]:
    training_records = training.get("tasks")
    response_records = responses.get("responses")
    if not isinstance(training_records, list) or not isinstance(response_records, list):
        raise ValueError("M073 control evidence is malformed")
    source_by_task = {
        record["task_id"]: record["source_sha256"]
        for record in training_records if isinstance(record, dict)
    }
    mapping: dict[str, str] = {}
    for record in response_records:
        if not isinstance(record, dict):
            raise ValueError("M073 response control record is malformed")
        task_id = record.get("task_id")
        source_sha = record.get("source_sha256")
        response = record.get("response")
        if (
            not isinstance(task_id, str) or not isinstance(source_sha, str)
            or not isinstance(response, str) or source_by_task.get(task_id) != source_sha
        ):
            raise ValueError("M073 memorizer training binding is invalid")
        mapping[source_sha] = response
    if len(mapping) != 4:
        raise ValueError("M073 memorizer requires exactly four training hashes")
    return mapping


def run(
    training_path: Path = TRAINING_PATH, responses_path: Path = RESPONSES_PATH,
    holdout_path: Path = HOLDOUT_PATH,
) -> dict[str, object]:
    training = json.loads(Path(training_path).read_text(encoding="utf-8"))
    responses = json.loads(Path(responses_path).read_text(encoding="utf-8"))
    holdouts = json.loads(Path(holdout_path).read_text(encoding="utf-8"))
    if training.get("schema") != "m073-training-task-materialization-v1":
        raise ValueError("unexpected M073 training schema")
    if responses.get("schema") != "m073-teacher-response-set-v1":
        raise ValueError("unexpected M073 response schema")
    tasks = _holdout_tasks(holdouts)
    memorized = _memorizer(training, responses)

    no_capsule_records: list[dict[str, object]] = []
    memorizer_records: list[dict[str, object]] = []
    training_hash_hits = 0
    for task in tasks:
        source_sha = m073_domain.source_sha256(task.source)
        no_capsule_passed = m073_domain.repair_passes(task, task.source)
        replay = memorized.get(source_sha)
        if replay is not None:
            training_hash_hits += 1
        memorizer_source = replay if replay is not None else task.source
        memorizer_passed = m073_domain.repair_passes(task, memorizer_source)
        no_capsule_records.append({
            "task_id": task.task_id,
            "source_sha256": source_sha,
            "passed": no_capsule_passed,
        })
        memorizer_records.append({
            "task_id": task.task_id,
            "source_sha256": source_sha,
            "exact_training_hash_hit": replay is not None,
            "passed": memorizer_passed,
        })

    result: dict[str, object] = {
        "schema": "m073-holdout-control-result-v1",
        "status": "holdout_controls_completed",
        "holdout_materialization_sha256": holdouts.get("holdout_materialization_sha256"),
        "no_capsule_holdouts_passed": sum(
            1 for record in no_capsule_records if record["passed"] is True
        ),
        "memorizer_holdouts_passed": sum(
            1 for record in memorizer_records if record["passed"] is True
        ),
        "memorizer_exact_training_hash_hits": training_hash_hits,
        "teacher_calls_during_controls": 0,
        "no_capsule_records": no_capsule_records,
        "memorizer_records": memorizer_records,
        "scientific_result_exists": False,
    }
    result["control_result_sha256"] = _canonical_sha(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training", type=Path, default=TRAINING_PATH)
    parser.add_argument("--responses", type=Path, default=RESPONSES_PATH)
    parser.add_argument("--holdouts", type=Path, default=HOLDOUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("M073 holdout control result already exists; refusing overwrite")
    result = run(args.training, args.responses, args.holdouts)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "memorizer_exact_training_hash_hits": result["memorizer_exact_training_hash_hits"],
        "memorizer_holdouts_passed": result["memorizer_holdouts_passed"],
        "no_capsule_holdouts_passed": result["no_capsule_holdouts_passed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
