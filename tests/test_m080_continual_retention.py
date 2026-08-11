"""Regressions for M080 continual acquisition under interference."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis.m080_continual_retention import (
    ARMS,
    IRREGULARS_PER_SKILL,
    SKILL_COUNT,
    TABLE_SLOTS,
    ExceptionEntry,
    Lineage,
    RetentionError,
    RuleEntry,
    Skill,
    Table,
    build_bank,
    evaluate,
    evaluate_capability,
    evaluate_holdouts,
    induce,
    run_arm,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M080"
MODULE = ROOT / "metamorphosis/m080_continual_retention.py"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def bank(salt: bytes) -> tuple[Skill, ...]:
    return build_bank(salt)


@pytest.fixture(scope="module")
def arms(bank: tuple[Skill, ...]) -> dict:
    return {arm: run_arm(bank, arm) for arm in ARMS}


def test_bank_shape_and_determinism(salt: bytes, bank: tuple[Skill, ...]) -> None:
    assert len(bank) == SKILL_COUNT
    assert [s.commitment() for s in build_bank(salt)] == [s.commitment() for s in bank]


def test_bank_matches_the_bound_commitment(bank: tuple[Skill, ...]) -> None:
    bound = json.loads((BASE / "BANK_COMMITMENT.json").read_text(encoding="utf-8"))
    assert [s.commitment() for s in bank] == [r["commitment"] for r in bound["skills"]]


def test_later_skills_share_a_rule_with_an_earlier_one(bank: tuple[Skill, ...]) -> None:
    """Where positive transfer and sublinear growth come from."""

    for skill in bank[3:]:
        donor = bank[skill.shares_rule_with]
        assert (skill.slope, skill.offset) == (donor.slope, donor.offset)


def test_later_skills_genuinely_conflict_with_their_donor(bank: tuple[Skill, ...]) -> None:
    """Where the interference comes from. Without this the retention claim is empty."""

    for skill in bank[3:]:
        donor = bank[skill.shares_rule_with]
        key = skill.conflicts_on_key
        assert key is not None
        assert key in donor.irregulars
        assert donor.expected(key) != skill.expected(key)


def test_first_skills_carry_no_conflict(bank: tuple[Skill, ...]) -> None:
    for skill in bank[:3]:
        assert skill.shares_rule_with is None
        assert skill.conflicts_on_key is None


def test_every_irregular_is_visible_in_the_examples(bank: tuple[Skill, ...]) -> None:
    """Otherwise a skill is unlearnable rather than merely hard."""

    for skill in bank:
        for key in skill.irregulars:
            assert key in skill.examples


def test_induction_recovers_the_rule_and_its_exceptions(bank: tuple[Skill, ...]) -> None:
    for skill in bank:
        (slope, offset), exceptions = induce(skill)
        assert (slope, offset) == (skill.slope, skill.offset)
        for key in skill.examples:
            expected = skill.expected(key)
            derived = exceptions.get(key, (slope * key + offset) % 8)
            assert derived == expected


def test_no_skill_has_private_slots(protocol: dict) -> None:
    assert protocol["body"]["private_slots_per_skill"] == 0
    assert protocol["body"]["shared_table_slots"] == TABLE_SLOTS


def test_lineage_retains_every_earlier_capability(arms: dict) -> None:
    assert arms["lineage"]["capabilities_lost"] == 0
    assert arms["lineage"]["final_retention_failures"] == 0


def test_lineage_generalises_on_every_skill(arms: dict) -> None:
    assert arms["lineage"]["own_holdout_perfect"] == SKILL_COUNT


def test_memory_growth_is_sublinear(arms: dict) -> None:
    ceiling = SKILL_COUNT * (1 + IRREGULARS_PER_SKILL)
    assert arms["lineage"]["slots_used_final"] < ceiling


def test_positive_transfer_is_measured(arms: dict) -> None:
    assert arms["lineage"]["rules_reused"] >= 1


def test_lineage_rolls_back_exactly(arms: dict) -> None:
    assert arms["lineage"]["rollbacks"] >= 1
    assert arms["lineage"]["rollback_mismatches"] == 0


def test_no_consolidation_loses_capabilities(arms: dict) -> None:
    """Proves the interference is real rather than asserted."""

    assert arms["no_consolidation"]["capabilities_lost"] >= 1


def test_no_rollback_leaves_a_checkpoint_mismatch(arms: dict) -> None:
    assert arms["no_rollback"]["rollback_mismatches"] >= 1


def test_the_rollback_check_is_not_tautological(bank: tuple[Skill, ...], arms: dict) -> None:
    """An earlier version compared the checkpoint against its own digest and could never fail.

    A mismatch must be reachable, otherwise the check reports green regardless of behaviour.
    """

    assert arms["no_rollback"]["rollback_mismatches"] > 0
    assert arms["lineage"]["rollback_mismatches"] == 0


def test_replay_dependence_is_reported_without_a_preregistered_direction(
    arms: dict, bank: tuple[Skill, ...],
) -> None:
    """The protocol forbids requiring either outcome; it requires stating which occurred."""

    verdict = evaluate(arms, bank)
    assert verdict.replay_dependence in ("structural", "replay_dependent")
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["replay_dependence"] == verdict.replay_dependence
    # Whichever way it fell, it must not be a pass/fail condition.
    assert not any("replay" in reason for reason in verdict.reasons)


def test_retention_is_measured_over_the_full_key_set(bank: tuple[Skill, ...]) -> None:
    """Damage lands on exception keys, which the split forces into examples."""

    skill = bank[0]
    table = Table()
    table.slots[0] = RuleEntry(frozenset({0}), skill.slope, skill.offset)
    for key, output in skill.irregulars.items():
        table.slots[table.slots.index(None)] = ExceptionEntry(frozenset({0}), key, output)
    assert evaluate_capability(table, skill) == len(skill.keys)

    broken = next(iter(skill.irregulars))
    for index, slot in enumerate(table.slots):
        if isinstance(slot, ExceptionEntry) and slot.key == broken:
            table.slots[index] = None
    assert evaluate_capability(table, skill) < len(skill.keys)
    # Holdout-only scoring would have missed it, which is why retention is not scored that way.
    assert evaluate_holdouts(table, skill) == len(skill.holdouts)


def test_the_lineage_never_reads_holdouts() -> None:
    """Checked structurally, the same way M078 pins its information boundary."""

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    lineage = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "Lineage"
    )
    attributes = {n.attr for n in ast.walk(lineage) if isinstance(n, ast.Attribute)}
    assert "holdouts" not in attributes


def test_table_lookup_prefers_exceptions_over_rules() -> None:
    table = Table()
    table.slots[0] = RuleEntry(frozenset({0}), 1, 0)
    table.slots[1] = ExceptionEntry(frozenset({0}), 5, 7)
    assert table.lookup(0, 5) == 7
    assert table.lookup(0, 4) == 4
    assert table.lookup(1, 4) is None


def test_unknown_arm_is_rejected(bank: tuple[Skill, ...]) -> None:
    with pytest.raises(RetentionError):
        run_arm(bank, "hopeful")


def test_capacity_is_bounded(bank: tuple[Skill, ...], arms: dict) -> None:
    for arm in ARMS:
        assert arms[arm]["slots_used_final"] <= TABLE_SLOTS


def test_a_fresh_lineage_starts_empty() -> None:
    lineage = Lineage(consolidation=True, replay=True, rollback=True)
    assert lineage.table.used() == 0
    assert lineage.table.lookup(0, 0) is None


def test_verdict_is_positive(arms: dict, bank: tuple[Skill, ...]) -> None:
    verdict = evaluate(arms, bank)
    assert verdict.positive, verdict.reasons


def test_evaluation_rejects_a_lineage_that_forgets(arms: dict, bank: tuple[Skill, ...]) -> None:
    degraded = {arm: dict(arms[arm]) for arm in ARMS}
    degraded["lineage"] = dict(arms["no_consolidation"])
    assert evaluate(degraded, bank).positive is False


def _json_normalised(timeline: list[dict]) -> list[dict]:
    """JSON turns the integer skill indices in `earlier_holdouts` into strings on the way out."""

    return [
        {
            key: ({str(k): v for k, v in value.items()}
                  if key == "earlier_holdouts" else value)
            for key, value in row.items()
        }
        for row in timeline
    ]


def test_preserved_result_reproduces(arms: dict) -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    for arm in ARMS:
        assert preserved["arms"][arm]["timeline"] == _json_normalised(arms[arm]["timeline"])
    assert preserved["verdict"] == "positive"
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False


def test_instrument_fixes_stay_visible() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert len(preserved["instrument_fixes_before_materialization"]) == 3


def test_learning_claim_is_explicit(protocol: dict) -> None:
    claim = protocol["learning_claim"]
    assert claim["structure_modified_is_the_policy_itself"] is True
    assert claim["external_memory_consulted_alongside_a_fixed_policy"] is False
    assert claim["weight_learning_claimed"] is False


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["closes_generality_gate_g5"] is False
    assert boundary["establishes_weight_learning"] is False
    assert boundary["establishes_open_ended_skill_acquisition"] is False
    assert boundary["agi_evidence"] is False
