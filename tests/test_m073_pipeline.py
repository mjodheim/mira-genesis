from __future__ import annotations

import json
from pathlib import Path
import subprocess

import assemble_m073_result as result_assembler
import induce_m073_capsule as capsule_induction
import m073_domain
import materialize_m073_holdouts as holdout_materializer
import run_m073_holdout_controls as holdout_controls
import run_m073_holdout_lineage as holdout_lineage
from mira_core.skills import SkillCapsule, SkillDemonstration, induce_skill_capsule


ROOT = Path(__file__).resolve().parents[1]
M073 = ROOT / "experiments" / "M073"
PROTOCOL = M073 / "PROTOCOL.json"
TRAINING = M073 / "TRAINING_TASKS.json"


def _repair(task: m073_domain.RepairTask) -> str:
    head, return_line = task.source.rsplit("    return ", 1)
    expression = return_line.strip()
    return (
        head
        + f"    return {expression} if {task.denominator_name} != 0 else 0\n"
    )


def _fake_teacher_responses(path: Path) -> Path:
    training = json.loads(TRAINING.read_text(encoding="utf-8"))
    records = []
    for call_index, task_record in enumerate(training["tasks"], start=1):
        task = m073_domain.generate_division_repair_task(
            task_record["seed"], split="training",
        )
        response = _repair(task)
        records.append({
            "call_index": call_index,
            "task_id": task.task_id,
            "source_sha256": m073_domain.source_sha256(task.source),
            "prompt_sha256": "fixture-prompt-" + str(call_index),
            "response": response,
            "response_sha256": m073_domain.source_sha256(response),
        })
    value = {
        "schema": "m073-teacher-response-set-v1",
        "status": "four_frozen_teacher_calls_completed",
        "request_set_commit": "fixture",
        "model": "gpt-5.6-sol",
        "call_count": 4,
        "scientific_retries": 0,
        "neutral_workspace": True,
        "repository_context_visible_to_teacher": False,
        "skill_induction_implementation_visible_to_teacher": False,
        "holdout_content_visible_to_teacher": False,
        "responses": records,
        "capsule_exists": False,
        "holdout_materialized": False,
        "scientific_result_exists": False,
    }
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_precommitted_pipeline_dry_run_reaches_exact_registered_threshold(
    tmp_path: Path, monkeypatch,
) -> None:
    responses_path = _fake_teacher_responses(tmp_path / "responses.json")
    capsule_value, induction = capsule_induction.induce(TRAINING, responses_path)
    assert induction["teacher_valid_repairs"] == 4
    assert induction["unique_capsules_induced"] == 1
    assert induction["corrupted_teacher_capsules_induced"] == 0

    capsule_path = tmp_path / "capsule.json"
    capsule_path.write_text(json.dumps(capsule_value), encoding="utf-8")
    monkeypatch.setattr(
        holdout_materializer,
        "committed_capsule_boundary",
        lambda capsule_path, root: {
            "capsule_commit": "fixture-committed-before-holdout",
            "capsule_blob": "a" * 40,
            "capsule_sha256": capsule_value["capsule_sha256"],
        },
    )
    holdouts = holdout_materializer.materialize(PROTOCOL, capsule_path, root=ROOT)
    assert holdouts["task_count"] == 12
    holdout_path = tmp_path / "holdouts.json"
    holdout_path.write_text(json.dumps(holdouts), encoding="utf-8")

    lineage = holdout_lineage.run(capsule_path, holdout_path)
    assert lineage["teacher_calls"] == 0
    assert lineage["holdouts_passed"] == 12
    assert lineage["case_failures"] == 0
    lineage_path = tmp_path / "lineage.json"
    lineage_path.write_text(json.dumps(lineage), encoding="utf-8")

    controls = holdout_controls.run(TRAINING, responses_path, holdout_path)
    assert controls["no_capsule_holdouts_passed"] == 0
    assert controls["memorizer_holdouts_passed"] == 0
    assert controls["memorizer_exact_training_hash_hits"] == 0
    control_path = tmp_path / "controls.json"
    control_path.write_text(json.dumps(controls), encoding="utf-8")

    induction_path = tmp_path / "induction.json"
    induction_path.write_text(json.dumps(induction), encoding="utf-8")
    result = result_assembler.assemble(
        PROTOCOL, induction_path, holdout_path, lineage_path, control_path,
    )
    assert result["claim_passed"] is True
    assert result["status"] == "passed_preregistered_threshold"
    assert result["observed"] == {
        "teacher_valid_repairs": 4,
        "unique_capsules_induced": 1,
        "complete_lineage_holdouts_passed": 12,
        "complete_lineage_holdouts_total": 12,
        "complete_lineage_case_failures": 0,
        "no_capsule_holdouts_passed": 0,
        "memorizer_holdouts_passed": 0,
        "corrupted_teacher_capsules_induced": 0,
        "holdout_model_calls": 0,
        "capsule_committed_before_holdout_materialization": True,
    }


def test_lineage_holdout_runner_cannot_read_teacher_or_training_artifacts() -> None:
    source = (ROOT / "scripts" / "run_m073_holdout_lineage.py").read_text(encoding="utf-8")
    assert "TEACHER_RESPONSES.json" not in source
    assert "TRAINING_TASKS.json" not in source
    assert "run_m073_teacher" not in source
    assert "CodexExecBackend" not in source
    assert "find_codex_executable" not in source


def test_capsule_commit_boundary_detects_uncommitted_byte_drift(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    demonstrations = []
    for seed in (1, 2, 5, 8):
        task = m073_domain.generate_division_repair_task(seed, split="fixture")
        demonstrations.append(SkillDemonstration(task.task_id, task.source, _repair(task)))
    capsule = induce_skill_capsule(demonstrations)
    capsule_path = repo / "experiments" / "M073" / "SKILL_CAPSULE.json"
    capsule_path.parent.mkdir(parents=True)
    capsule_path.write_text(json.dumps(capsule.to_dict()), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run([
        "git", "-c", "user.name=Mira test", "-c", "user.email=mira@example.invalid",
        "commit", "--quiet", "-m", "capsule",
    ], cwd=repo, check=True)
    boundary = holdout_materializer.committed_capsule_boundary(capsule_path, root=repo)
    assert boundary["capsule_sha256"] == capsule.capsule_sha256
    assert len(boundary["capsule_commit"]) == 40
    assert len(boundary["capsule_blob"]) == 40

    value = json.loads(capsule_path.read_text(encoding="utf-8"))
    value["skill_id"] = "tampered"
    capsule_path.write_text(json.dumps(value), encoding="utf-8")
    try:
        holdout_materializer.committed_capsule_boundary(capsule_path, root=repo)
    except ValueError as exc:
        assert "differs from the committed capsule" in str(exc)
    else:
        raise AssertionError("uncommitted M073 capsule drift was not detected")


def test_serialized_capsule_contains_no_teacher_output_lookup_or_evaluator() -> None:
    demonstrations = []
    for seed in (1, 2, 5, 8):
        task = m073_domain.generate_division_repair_task(seed, split="fixture")
        demonstrations.append(SkillDemonstration(task.task_id, task.source, _repair(task)))
    capsule = induce_skill_capsule(demonstrations)
    encoded = json.dumps(capsule.to_dict(), sort_keys=True)
    assert "ratio_" not in encoded
    assert "value_" not in encoded
    assert "scale_" not in encoded
    assert "teacher response" not in encoded.lower()
    assert "m073_domain" not in encoded
    assert SkillCapsule.from_dict(capsule.to_dict()) == capsule
