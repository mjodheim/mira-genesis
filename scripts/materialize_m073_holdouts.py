#!/usr/bin/env python3
"""Materialize M073 holdouts only after the scientific capsule is committed.

The holdout seeds were frozen in PROTOCOL.json before implementation. This script enforces the
causal ordering: a byte-identical SKILL_CAPSULE.json must already exist in Git history on the
current branch before any held-out source can be generated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import m073_domain
from mira_core.skills import SkillCapsule


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
PROTOCOL_PATH = M073 / "PROTOCOL.json"
CAPSULE_PATH = M073 / "SKILL_CAPSULE.json"
OUTPUT_PATH = M073 / "HOLDOUT_TASKS.json"


def _git(*args: str, root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout).strip())
    return completed.stdout.strip()


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def committed_capsule_boundary(
    capsule_path: Path = CAPSULE_PATH, *, root: Path = ROOT,
) -> dict[str, str]:
    capsule_path = Path(capsule_path)
    if not capsule_path.is_file():
        raise ValueError("M073 capsule does not exist; holdout materialization is forbidden")
    try:
        relative = capsule_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("M073 capsule must live inside the repository") from exc
    commit = _git("log", "-1", "--format=%H", "--", relative, root=root)
    if not commit:
        raise ValueError("M073 capsule has not been committed")
    _git("merge-base", "--is-ancestor", commit, "HEAD", root=root)
    committed_blob = _git("rev-parse", f"HEAD:{relative}", root=root)
    working_blob = _git("hash-object", f"--path={relative}", relative, root=root)
    if committed_blob != working_blob:
        raise ValueError("M073 working capsule differs from the committed capsule")
    capsule = SkillCapsule.from_dict(json.loads(capsule_path.read_text(encoding="utf-8")))
    return {
        "capsule_commit": commit,
        "capsule_blob": committed_blob,
        "capsule_sha256": capsule.capsule_sha256,
    }


def materialize(
    protocol_path: Path = PROTOCOL_PATH, capsule_path: Path = CAPSULE_PATH, *, root: Path = ROOT,
) -> dict[str, object]:
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    if protocol.get("schema") != "m073-skill-appropriation-protocol-v1":
        raise ValueError("unexpected M073 protocol schema")
    boundary = committed_capsule_boundary(capsule_path, root=root)
    task_family = protocol.get("task_family")
    if not isinstance(task_family, dict):
        raise ValueError("M073 protocol lacks task family")
    seeds = task_family.get("holdout_seeds")
    training_seeds = task_family.get("training_seeds")
    if not isinstance(seeds, list) or not all(isinstance(seed, int) for seed in seeds):
        raise ValueError("M073 holdout seeds are malformed")
    if seeds != [101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157]:
        raise ValueError("M073 holdout seeds differ from preregistration")
    if set(seeds) & set(training_seeds if isinstance(training_seeds, list) else []):
        raise ValueError("M073 holdout seeds overlap training seeds")
    tasks: list[dict[str, object]] = []
    source_hashes: set[str] = set()
    identifiers: set[str] = set()
    for seed in seeds:
        task = m073_domain.generate_division_repair_task(seed, split="holdout")
        source_sha = m073_domain.source_sha256(task.source)
        if source_sha in source_hashes or task.task_id in identifiers:
            raise ValueError("M073 holdout generator produced a duplicate")
        source_hashes.add(source_sha)
        identifiers.add(task.task_id)
        tasks.append({
            "seed": seed,
            "task_id": task.task_id,
            "function_name": task.function_name,
            "source": task.source,
            "source_sha256": source_sha,
        })
    artifact: dict[str, object] = {
        "schema": "m073-holdout-task-materialization-v1",
        "status": "holdouts_materialized_after_committed_capsule",
        "protocol_commit": "78d53d733bdf77eab773414e8d273ed70e31391d",
        **boundary,
        "task_count": len(tasks),
        "tasks": tasks,
        "teacher_model_available_to_holdout_runner": False,
        "teacher_responses_required_by_holdout_runner": False,
        "scientific_result_exists": False,
    }
    artifact["holdout_materialization_sha256"] = _canonical_sha(artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--capsule", type=Path, default=CAPSULE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("M073 holdout artifact already exists; refusing overwrite")
    artifact = materialize(args.protocol, args.capsule)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "capsule_commit": artifact["capsule_commit"],
        "holdout_materialization_sha256": artifact["holdout_materialization_sha256"],
        "task_count": artifact["task_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
