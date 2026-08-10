from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import m073_domain
from mira_core.skills import (
    SkillCapsule, SkillDemonstration, SkillInductionError, TeacherCallTrap,
    apply_skill_capsule, induce_skill_capsule,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M073" / "PROTOCOL.json"
TRAINING = ROOT / "experiments" / "M073" / "TRAINING_TASKS.json"


def _fixture_repair(task: m073_domain.RepairTask, *, guard_style: bool = False) -> str:
    head, return_line = task.source.rsplit("    return ", 1)
    expression = return_line.strip()
    if guard_style:
        return (
            head
            + f"    if {task.denominator_name} == 0:\n"
            + "        return 0\n"
            + f"    return {expression}\n"
        )
    return (
        head
        + f"    return {expression} if {task.denominator_name} != 0 else 0\n"
    )


def _fixture_demonstrations(*, guard_style: bool = False) -> list[SkillDemonstration]:
    tasks = [
        m073_domain.generate_division_repair_task(seed, split="fixture")
        for seed in (1, 2, 5, 8)
    ]
    return [
        SkillDemonstration(task.task_id, task.source, _fixture_repair(task, guard_style=guard_style))
        for task in tasks
    ]


def test_m073_protocol_precedes_teacher_capsule_and_holdout() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["schema"] == "m073-skill-appropriation-protocol-v1"
    assert protocol["status"] == (
        "protocol_frozen_before_capsule_implementation_teacher_demonstrations_or_holdout_materialization"
    )
    assert protocol["teacher_demonstrations_exist"] is False
    assert protocol["capsule_exists"] is False
    assert protocol["holdout_materialized"] is False
    assert protocol["scientific_result_exists"] is False
    assert protocol["teacher_removal_boundary"]["model_calls_during_holdout"] == 0
    assert protocol["preregistered_positive_threshold"]["complete_lineage_holdouts_passed"] == 12


def test_scientific_training_tasks_match_frozen_seeds_before_teacher() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    artifact = json.loads(TRAINING.read_text(encoding="utf-8"))
    assert artifact["protocol_commit"] == "78d53d733bdf77eab773414e8d273ed70e31391d"
    assert artifact["task_count"] == 4
    assert artifact["teacher_demonstrations_exist"] is False
    assert artifact["capsule_exists"] is False
    assert artifact["holdout_materialized"] is False
    assert artifact["scientific_result_exists"] is False
    expected_seeds = protocol["task_family"]["training_seeds"]
    assert expected_seeds == [3, 7, 11, 19]
    for seed, record in zip(expected_seeds, artifact["tasks"], strict=True):
        task = m073_domain.generate_division_repair_task(seed, split="training")
        assert record["seed"] == seed
        assert record["task_id"] == task.task_id
        assert record["function_name"] == task.function_name
        assert record["source"] == task.source
        assert record["source_sha256"] == m073_domain.source_sha256(task.source)
    digest_value = dict(artifact)
    expected_digest = digest_value.pop("training_materialization_sha256")
    observed = hashlib.sha256(json.dumps(
        digest_value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    assert observed == expected_digest == (
        "f64c8c1d57e9298811da68bbc9313e537611a217924c835c96611f780a06741d"
    )


def test_lineage_skill_core_contains_no_m073_task_oracle() -> None:
    source = (ROOT / "mira_core" / "skills.py").read_text(encoding="utf-8")
    assert "m073_domain" not in source
    assert "generate_division_repair_task" not in source
    assert "repair_passes" not in source
    assert "EVALUATION_CASES" not in source
    assert "expected_division_repair" not in source


def test_generic_capsule_is_induced_from_four_alpha_distinct_fixture_repairs() -> None:
    capsule = induce_skill_capsule(_fixture_demonstrations(), skill_id="fixture-skill")
    assert capsule.provenance == "induced_from_external_demonstrations"
    assert capsule.source_pattern == "__MIRA_SLOT_0__ / __MIRA_SLOT_1__"
    assert capsule.target_template == (
        "__MIRA_SLOT_0__ / __MIRA_SLOT_1__ if __MIRA_SLOT_1__ != 0 else 0"
    )
    restored = SkillCapsule.from_dict(capsule.to_dict())
    assert restored == capsule
    assert len(capsule.capsule_sha256) == 64
    assert len(capsule.training_evidence_sha256) == 64
    assert len(capsule.induction_trace_sha256) == 64


def test_guard_style_teacher_demonstrations_are_normalized_without_copying_syntax() -> None:
    capsule = induce_skill_capsule(_fixture_demonstrations(guard_style=True))
    assert capsule.source_pattern == "__MIRA_SLOT_0__ / __MIRA_SLOT_1__"
    assert "__MIRA_SLOT_1__ == 0" in capsule.target_template
    task = m073_domain.generate_division_repair_task(89, split="fixture")
    rewritten = apply_skill_capsule(capsule, task.source)
    assert m073_domain.repair_passes(task, rewritten)


def test_fixture_capsule_applies_without_teacher_to_identifier_novel_tasks() -> None:
    capsule = induce_skill_capsule(_fixture_demonstrations())
    tasks = [
        m073_domain.generate_division_repair_task(seed, split="fixture")
        for seed in (21, 34, 55)
    ]
    trap = TeacherCallTrap()
    passed = 0
    for task in tasks:
        rewritten = apply_skill_capsule(capsule, task.source)
        passed += int(m073_domain.repair_passes(task, rewritten))
        assert task.numerator_name in rewritten
        assert task.denominator_name in rewritten
    assert passed == 3
    assert trap.calls == 0


def test_teacher_call_trap_fails_closed_when_invoked() -> None:
    trap = TeacherCallTrap()
    with pytest.raises(RuntimeError, match="forbidden"):
        trap.complete("anything")
    assert trap.calls == 1


def test_inconsistent_teacher_repairs_produce_no_capsule() -> None:
    demonstrations = _fixture_demonstrations()
    corrupted = demonstrations[-1].repaired.replace("else 0", "else 1")
    demonstrations[-1] = SkillDemonstration(
        demonstrations[-1].task_id, demonstrations[-1].source, corrupted,
    )
    with pytest.raises(SkillInductionError, match="one unique generalized rewrite"):
        induce_skill_capsule(demonstrations)


def test_teacher_cannot_change_signature_or_unrelated_assignments() -> None:
    demonstrations = _fixture_demonstrations()
    bad_signature = demonstrations[0].repaired.replace("def ratio_", "def altered_")
    broken = list(demonstrations)
    broken[0] = SkillDemonstration(
        demonstrations[0].task_id, demonstrations[0].source, bad_signature,
    )
    with pytest.raises(SkillInductionError, match="function name"):
        induce_skill_capsule(broken)

    changed_marker = demonstrations[0].repaired.replace(" = 1\n", " = 99\n", 1)
    broken = list(demonstrations)
    broken[0] = SkillDemonstration(
        demonstrations[0].task_id, demonstrations[0].source, changed_marker,
    )
    with pytest.raises(SkillInductionError, match="outside the terminal return region"):
        induce_skill_capsule(broken)


def test_unchanged_holdout_source_fails_zero_denominator_contract() -> None:
    task = m073_domain.generate_division_repair_task(999, split="fixture")
    assert m073_domain.repair_passes(task, task.source) is False
