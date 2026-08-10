#!/usr/bin/env python3
"""Induce and preserve the M073 skill capsule from frozen teacher responses.

This program is committed before scientific teacher execution. It validates every teacher repair
against the evaluator-owned training contract, proves that one deterministically corrupted
teacher set induces no capsule, and writes the one generalized capsule. It never reads or
materializes holdout content.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Mapping

import m073_domain
from mira_core.skills import SkillDemonstration, SkillInductionError, induce_skill_capsule


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
TRAINING_PATH = M073 / "TRAINING_TASKS.json"
RESPONSES_PATH = M073 / "TEACHER_RESPONSES.json"
CAPSULE_PATH = M073 / "SKILL_CAPSULE.json"
INDUCTION_PATH = M073 / "CAPSULE_INDUCTION.json"


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _load_json(path: Path, schema: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema") != schema:
        raise ValueError(f"unexpected M073 schema in {path.name}")
    return value


def _tasks(training: Mapping[str, object]) -> dict[str, m073_domain.RepairTask]:
    records = training.get("tasks")
    if not isinstance(records, list) or len(records) != 4:
        raise ValueError("M073 training artifact does not contain exactly four tasks")
    result: dict[str, m073_domain.RepairTask] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("M073 training task record is malformed")
        seed = record.get("seed")
        if not isinstance(seed, int):
            raise ValueError("M073 training task seed is malformed")
        task = m073_domain.generate_division_repair_task(seed, split="training")
        if record.get("task_id") != task.task_id or record.get("source") != task.source:
            raise ValueError("M073 training task no longer matches its frozen generator")
        if record.get("source_sha256") != m073_domain.source_sha256(task.source):
            raise ValueError("M073 training source digest mismatch")
        result[task.task_id] = task
    return result


def _validated_demonstrations(
    training: Mapping[str, object], responses: Mapping[str, object],
) -> tuple[list[SkillDemonstration], list[dict[str, object]]]:
    tasks = _tasks(training)
    response_records = responses.get("responses")
    if responses.get("status") != "four_frozen_teacher_calls_completed":
        raise ValueError("M073 teacher response phase is incomplete")
    if responses.get("model") != "gpt-5.6-sol" or responses.get("call_count") != 4:
        raise ValueError("M073 teacher identity or call count differs from the frozen protocol")
    if responses.get("scientific_retries") != 0:
        raise ValueError("M073 teacher response set contains a retry")
    if not isinstance(response_records, list) or len(response_records) != 4:
        raise ValueError("M073 teacher response set does not contain four records")
    demonstrations: list[SkillDemonstration] = []
    audit: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in response_records:
        if not isinstance(record, dict):
            raise ValueError("M073 teacher response record is malformed")
        task_id = record.get("task_id")
        response = record.get("response")
        if not isinstance(task_id, str) or task_id not in tasks or task_id in seen:
            raise ValueError("M073 teacher response task binding is invalid")
        if not isinstance(response, str):
            raise ValueError("M073 teacher response body is absent")
        task = tasks[task_id]
        response_sha = m073_domain.source_sha256(response)
        if record.get("source_sha256") != m073_domain.source_sha256(task.source):
            raise ValueError("M073 teacher response is bound to the wrong source")
        if record.get("response_sha256") != response_sha:
            raise ValueError("M073 teacher response digest mismatch")
        passed = m073_domain.repair_passes(task, response)
        if not passed:
            raise SkillInductionError(f"teacher repair failed training evaluator: {task_id}")
        seen.add(task_id)
        demonstrations.append(SkillDemonstration(task_id, task.source, response))
        audit.append({
            "task_id": task_id,
            "source_sha256": m073_domain.source_sha256(task.source),
            "response_sha256": response_sha,
            "training_evaluator_passed": True,
        })
    if set(tasks) != seen:
        raise ValueError("M073 teacher response set is incomplete")
    return demonstrations, audit


def _corrupt_response(source: str) -> str:
    """Change one numeric constant in the learned return region without reading a hidden oracle."""

    tree = ast.parse(source)
    constants = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ]
    # Prefer a terminal zero constant if present; otherwise change the last numeric literal.
    target = next((node for node in reversed(constants) if node.value == 0), None)
    if target is None and constants:
        target = constants[-1]
    if target is None:
        raise SkillInductionError("teacher response contains no corruptible numeric terminal value")
    target.value = 1 if target.value == 0 else target.value + 1
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


def induce(
    training_path: Path = TRAINING_PATH, responses_path: Path = RESPONSES_PATH,
) -> tuple[dict[str, object], dict[str, object]]:
    training = _load_json(training_path, "m073-training-task-materialization-v1")
    responses = _load_json(responses_path, "m073-teacher-response-set-v1")
    if responses.get("holdout_materialized") is not False:
        raise ValueError("M073 teacher responses improperly contain holdout state")
    demonstrations, audit = _validated_demonstrations(training, responses)
    capsule = induce_skill_capsule(demonstrations)

    corrupted = list(demonstrations)
    last = corrupted[-1]
    corrupted[-1] = SkillDemonstration(
        last.task_id, last.source, _corrupt_response(last.repaired),
    )
    corrupted_capsules_induced = 0
    try:
        induce_skill_capsule(corrupted, skill_id="m073-corrupted-control")
    except SkillInductionError:
        pass
    else:
        corrupted_capsules_induced = 1
        raise SkillInductionError("corrupted teacher control unexpectedly induced a capsule")

    capsule_value = capsule.to_dict()
    induction = {
        "schema": "m073-capsule-induction-v1",
        "status": "capsule_induced_before_holdout_materialization",
        "protocol_commit": "78d53d733bdf77eab773414e8d273ed70e31391d",
        "training_tasks_commit": "898380d86aef7f67e39367c06e0ebe498395d33b",
        "teacher_request_commit": "521895af33e30320c06437d4d9fbd83dee581a47",
        "teacher_valid_repairs": len(audit),
        "training_audit": audit,
        "unique_capsules_induced": 1,
        "corrupted_teacher_capsules_induced": corrupted_capsules_induced,
        "capsule_sha256": capsule.capsule_sha256,
        "teacher_response_set_sha256": _canonical_sha(responses),
        "holdout_materialized": False,
        "holdout_model_calls": 0,
        "scientific_result_exists": False,
    }
    return capsule_value, induction


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training", type=Path, default=TRAINING_PATH)
    parser.add_argument("--responses", type=Path, default=RESPONSES_PATH)
    parser.add_argument("--capsule-output", type=Path, default=CAPSULE_PATH)
    parser.add_argument("--induction-output", type=Path, default=INDUCTION_PATH)
    args = parser.parse_args()
    for output in (args.capsule_output, args.induction_output):
        if output.exists():
            raise SystemExit(f"M073 output already exists; refusing overwrite: {output}")
    capsule, induction = induce(args.training, args.responses)
    args.capsule_output.write_text(
        json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    args.induction_output.write_text(
        json.dumps(induction, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "capsule_sha256": induction["capsule_sha256"],
        "corrupted_teacher_capsules_induced": induction["corrupted_teacher_capsules_induced"],
        "teacher_valid_repairs": induction["teacher_valid_repairs"],
        "unique_capsules_induced": induction["unique_capsules_induced"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
