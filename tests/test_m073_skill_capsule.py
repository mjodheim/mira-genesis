from __future__ import annotations

import json
from pathlib import Path

import pytest

from mira_core.skills import (
    SkillCapsule, SkillDemonstration, SkillInductionError, TeacherCallTrap,
    apply_skill_capsule, evaluate_capsule_on_tasks, expected_division_repair,
    generate_division_repair_task, induce_skill_capsule, repair_passes,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M073" / "PROTOCOL.json"


def _fixture_demonstrations() -> list[SkillDemonstration]:
    tasks = [generate_division_repair_task(seed, split="fixture") for seed in (1, 2, 5, 8)]
    return [
        SkillDemonstration(task.task_id, task.source, expected_division_repair(task))
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


def test_generic_capsule_is_induced_from_four_alpha_distinct_fixture_repairs() -> None:
    capsule = induce_skill_capsule(_fixture_demonstrations(), skill_id="fixture-skill")
    assert capsule.provenance == "induced_from_external_demonstrations"
    assert capsule.source_pattern == "__MIRA_SLOT_0__ / __MIRA_SLOT_1__"
    assert capsule.target_template == (
        "__MIRA_SLOT_0__ / __MIRA_SLOT_1__ if __MIRA_SLOT_1__ != 0 else 0"
    )
    encoded = capsule.to_dict()
    restored = SkillCapsule.from_dict(encoded)
    assert restored == capsule
    assert len(capsule.capsule_sha256) == 64
    assert len(capsule.training_evidence_sha256) == 64
    assert len(capsule.induction_trace_sha256) == 64


def test_fixture_capsule_applies_without_teacher_to_identifier_novel_tasks() -> None:
    capsule = induce_skill_capsule(_fixture_demonstrations())
    tasks = [generate_division_repair_task(seed, split="fixture") for seed in (21, 34, 55)]
    trap = TeacherCallTrap()
    result = evaluate_capsule_on_tasks(capsule, tasks, teacher_trap=trap)
    assert result["passed"] == 3
    assert result["total"] == 3
    assert result["teacher_calls"] == 0
    assert trap.calls == 0
    for task in tasks:
        rewritten = apply_skill_capsule(capsule, task.source)
        assert repair_passes(task, rewritten)
        assert task.numerator_name in rewritten
        assert task.denominator_name in rewritten


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
    with pytest.raises(SkillInductionError, match="outside the return expression"):
        induce_skill_capsule(broken)


def test_unchanged_holdout_source_fails_zero_denominator_contract() -> None:
    task = generate_division_repair_task(999, split="fixture")
    assert repair_passes(task, task.source) is False
