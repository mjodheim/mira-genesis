"""Regressions for M078 calibrated refusal on an incompatible opaque body."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis.m078_incompatible_refusal import (
    ARMS,
    BODIES_PER_CLASS,
    COMMAND_SLOTS,
    HIDDEN_OBSERVATIONS_PER_BODY,
    REFUSED_EMPTY,
    REFUSED_UNDERDETERMINED,
    SKILLS,
    SKILL_NAMES,
    Body,
    RefusalError,
    SkillInputs,
    _fitting_commands,
    _injective_assignment,
    build_bank,
    discover,
    evaluate,
    run_arm,
    validate_hidden,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M078"
MODULE = ROOT / "metamorphosis/m078_incompatible_refusal.py"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def bank(salt: bytes) -> tuple[Body, ...]:
    return build_bank(salt)


@pytest.fixture(scope="module")
def arms(bank: tuple[Body, ...]) -> dict:
    return {arm: run_arm(bank, arm) for arm in ARMS}


def test_bank_shape_and_ordering(bank: tuple[Body, ...]) -> None:
    assert len(bank) == 2 * BODIES_PER_CLASS
    for body_class in ("compatible", "incompatible"):
        members = [body for body in bank if body.body_class == body_class]
        assert len(members) == BODIES_PER_CLASS
        commitments = [body.commitment() for body in members]
        assert commitments == sorted(commitments)


def test_bank_is_deterministic(salt: bytes, bank: tuple[Body, ...]) -> None:
    assert [b.commitment() for b in build_bank(salt)] == [b.commitment() for b in bank]


def test_bank_matches_the_bound_commitment(bank: tuple[Body, ...]) -> None:
    bound = json.loads((BASE / "BANK_COMMITMENT.json").read_text(encoding="utf-8"))
    assert [b.commitment() for b in bank] == [r["commitment"] for r in bound["bodies"]]


def test_public_input_sets_are_disjoint(bank: tuple[Body, ...]) -> None:
    """The stitched command is only constructible because these sets do not overlap."""

    for body in bank:
        seen: set[int] = set()
        for name in SKILL_NAMES:
            values = set(body.inputs.public[name])
            assert not (values & seen)
            seen |= values


def test_hidden_inputs_never_overlap_public_inputs(bank: tuple[Body, ...]) -> None:
    for body in bank:
        public = body.inputs.all_public()
        for name in SKILL_NAMES:
            assert not (set(body.inputs.hidden[name]) & public)


def test_incompatible_bodies_admit_a_public_fitting_candidate(bank: tuple[Body, ...]) -> None:
    """Refusal must require under-determination, never an empty candidate set."""

    for body in (b for b in bank if b.body_class == "incompatible"):
        viable = [
            mask for mask in range(256)
            if all(_fitting_commands(body, mask, name) for name in SKILL_NAMES)
        ]
        assert viable, "an incompatible body offered no public fit at all"


def test_incompatible_bodies_collapse_exactly_the_constructed_pair(
    bank: tuple[Body, ...],
) -> None:
    for body in (b for b in bank if b.body_class == "incompatible"):
        mask = next(
            m for m in range(256)
            if all(_fitting_commands(body, m, name) for name in SKILL_NAMES)
        )
        fits = {name: _fitting_commands(body, mask, name) for name in SKILL_NAMES}
        first, second = body.aliased_pair
        assert set(fits[first]) & set(fits[second]), "the aliased pair does not share a command"
        assert _injective_assignment(fits) is None


def test_compatible_bodies_admit_an_injective_assignment(bank: tuple[Body, ...]) -> None:
    for body in (b for b in bank if b.body_class == "compatible"):
        mask = next(
            m for m in range(256)
            if all(_fitting_commands(body, m, name) for name in SKILL_NAMES)
        )
        fits = {name: _fitting_commands(body, mask, name) for name in SKILL_NAMES}
        assert _injective_assignment(fits) is not None


def test_discoverer_adapts_every_compatible_body(arms: dict) -> None:
    record = arms["discoverer"]
    assert record["compatible_adapters"] == BODIES_PER_CLASS
    assert record["compatible_hidden_perfect"] == BODIES_PER_CLASS


def test_discoverer_never_falsely_refuses(arms: dict) -> None:
    assert arms["discoverer"]["false_refusals"] == 0


def test_discoverer_refuses_every_incompatible_body(arms: dict) -> None:
    assert arms["discoverer"]["true_refusals"] == BODIES_PER_CLASS
    assert arms["discoverer"]["invented_adapters"] == 0


def test_no_refusal_comes_from_an_empty_candidate_set(arms: dict) -> None:
    """The protocol does not count an exhausted search as a calibrated refusal."""

    assert arms["discoverer"]["empty_set_refusals"] == 0
    for record in arms["discoverer"]["records"]:
        if record["refused"]:
            assert record["refusal_kind"] == REFUSED_UNDERDETERMINED


def test_never_refuse_control_fails_hidden_validation(arms: dict) -> None:
    """This is what proves the public evidence really was insufficient."""

    record = arms["never_refuse"]
    assert record["invented_adapters"] == BODIES_PER_CLASS
    assert record["incompatible_hidden_failures"] == BODIES_PER_CLASS


def test_always_refuse_control_recovers_nothing(arms: dict) -> None:
    assert arms["always_refuse"]["adapters_recovered"] == 0


def test_verdict_is_positive(arms: dict) -> None:
    verdict = evaluate(arms)
    assert verdict.positive, verdict.reasons


def test_evaluation_rejects_a_discoverer_that_refuses_everything(arms: dict) -> None:
    degraded = {arm: dict(arms[arm]) for arm in ARMS}
    degraded["discoverer"] = dict(arms["always_refuse"])
    degraded["discoverer"]["arm"] = "discoverer"
    assert evaluate(degraded).positive is False


def test_evaluation_rejects_a_discoverer_that_never_refuses(arms: dict) -> None:
    degraded = {arm: dict(arms[arm]) for arm in ARMS}
    degraded["discoverer"] = dict(arms["never_refuse"])
    degraded["discoverer"]["arm"] = "discoverer"
    assert evaluate(degraded).positive is False


def test_discoverer_never_reads_hidden_evidence_or_body_class() -> None:
    """The M069 falsifier, checked structurally rather than by trust."""

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    function = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "discover"
    )
    attributes = {
        node.attr for node in ast.walk(function) if isinstance(node, ast.Attribute)
    }
    assert "hidden" not in attributes
    assert "body_class" not in attributes
    assert "aliased_pair" not in attributes
    assert "_operations" not in attributes


def test_body_call_is_total_and_never_raises(bank: tuple[Body, ...]) -> None:
    for body in bank:
        assert body.call(COMMAND_SLOTS + 40, 7) is None
        for command in range(COMMAND_SLOTS):
            reply = body.call(command, 3)
            assert reply is None or isinstance(reply, int)


def test_unknown_arm_and_mode_are_rejected(bank: tuple[Body, ...]) -> None:
    with pytest.raises(RefusalError):
        run_arm(bank, "hopeful")
    with pytest.raises(RefusalError):
        discover(bank[0], refusal="sometimes")


def test_empty_candidate_refusal_is_reachable_and_distinct(salt: bytes) -> None:
    """A body implementing nothing must refuse with the non-calibrated kind."""

    inputs = SkillInputs.build(salt, "compatible", 0)
    barren = Body(
        body_class="compatible", index=99, commands=(), mask=0, inputs=inputs,
        _operations={}, aliased_pair=None,
    )
    decision = discover(barren)
    assert decision.refusal == REFUSED_EMPTY


def test_hidden_validation_counts_every_observation(bank: tuple[Body, ...]) -> None:
    body = next(b for b in bank if b.body_class == "compatible")
    decision = discover(body)
    assert decision.adapter is not None
    assert validate_hidden(body, decision.adapter) == HIDDEN_OBSERVATIONS_PER_BODY


def test_skills_are_pairwise_distinguishable() -> None:
    for first in SKILL_NAMES:
        for second in SKILL_NAMES:
            if first < second:
                assert any(
                    SKILLS[first](value) != SKILLS[second](value) for value in range(60)
                )


def test_preserved_result_reproduces(arms: dict) -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    for arm in ARMS:
        assert preserved["arms"][arm]["records"] == arms[arm]["records"]
    assert preserved["verdict"] == "positive"
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["closes_generality_gate_g1"] is False
    assert boundary["establishes_general_epistemic_humility"] is False
    assert boundary["establishes_refusal_by_exhaustion_only"] is False
    assert boundary["agi_evidence"] is False
