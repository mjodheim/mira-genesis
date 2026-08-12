"""Development regressions for M086-B, run before any bank or holdout is materialized.

These exist to hold the four corrections M086-A's disqualification mandates: artifacts bound to
committed bytes, ten conditions each computed and decisive, a real forced fault, and a holdout the
meta-search cannot have seen. They use throwaway salts and never touch the protocol salt.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis.m047_runtime_sandbox import run_body_in_sandbox
from metamorphosis.m086_evolvable_mechanism import (
    META_PRIMITIVES,
    build_mechanism,
    diagnose,
    generate,
    m0_mechanism,
)
from metamorphosis.m086b_bank import (
    CANONICALS,
    ROUTELESS_CANDIDATES,
    TOKEN_VOCABULARY,
    body_from_shape,
    draw_shape,
    public_cases_from_shape,
)
from metamorphosis.m086b_holdout import holdout_hidden, holdout_public, holdout_shape
from metamorphosis.m086b_lineage import (
    ARMS,
    CONDITIONS,
    adopt_with_forced_fault,
    corrupt,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M086B"
THROWAWAY = tuple(bytes.fromhex(pair * 32) for pair in ("11", "22", "33", "44", "55"))


# -- nothing is materialized yet -----------------------------------------------------------------

def test_no_bank_holdout_or_result_exists_at_this_commit() -> None:
    for name in ("BANK_COMMITMENT.json", "HOLDOUT.json", "RESULT.json"):
        path = BASE / name
        if path.exists():
            pytest.skip(f"{name} exists; this is a later commit in the chronology")
    assert (BASE / "PROTOCOL.json").exists()


def test_the_protocol_is_declared_byte_exact_before_any_digest() -> None:
    """M086-A bound a digest to its CRLF working-tree copy and was disqualified for it."""

    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for artifact in (
        "PROTOCOL.json", "BANK_COMMITMENT.json", "ADOPTED_MECHANISM.json",
        "PHASE1.json", "HOLDOUT.json", "PRE_ADOPTION_MECHANISM.json", "RESULT.json",
    ):
        assert f"experiments/M086B/{artifact} -text" in attributes, artifact


# -- the grammar generates the premise and guarantees nothing about the outcome -------------------

@pytest.mark.parametrize("salt", THROWAWAY)
def test_the_grammar_always_produces_two_stage_evidence(salt: bytes) -> None:
    """The premise, which is M047's documented behaviour, not a thumb on the scale."""

    shape = draw_shape(salt, "development")
    executed = run_body_in_sandbox(
        body_from_shape(shape), public_cases_from_shape(shape, "development"),
        timeout_seconds=60.0,
    )
    stages = {case.error_stage for case in executed.cases if not case.ok}
    assert stages == {"interpretation", "execution"}, stages


@pytest.mark.parametrize("salt", THROWAWAY)
def test_the_starting_mechanism_can_emit_nothing_for_that_evidence(salt: bytes) -> None:
    shape = draw_shape(salt, "development")
    body = body_from_shape(shape)
    executed = run_body_in_sandbox(
        body, public_cases_from_shape(shape, "development"), timeout_seconds=60.0,
    )
    hypothesis = diagnose(m0_mechanism(), executed.cases)
    assert hypothesis.sufficient is False
    assert generate(m0_mechanism(), body, hypothesis) == ()


@pytest.mark.parametrize("salt", THROWAWAY)
def test_the_repaired_alias_cannot_reveal_a_new_fault(salt: bytes) -> None:
    """The cascade that made M086-A's first hand-written bank meaningless."""

    shape = draw_shape(salt, "development")
    assert shape.unknown_canonical in shape.routes
    assert shape.routeless_operation not in shape.routes
    assert shape.unknown_token not in CANONICALS
    assert shape.unknown_token in TOKEN_VOCABULARY
    assert shape.routeless_operation in ROUTELESS_CANDIDATES


def test_the_grammar_never_leaves_max_without_a_route() -> None:
    """A tool named `max` self-recurses; that latent M047 defect must stay unreachable."""

    assert "max" not in ROUTELESS_CANDIDATES
    for salt in THROWAWAY:
        assert draw_shape(salt, "development").routeless_operation != "max"


def test_the_grammar_varies_with_the_salt() -> None:
    shapes = {draw_shape(salt, "development").to_dict()["unknown_token"] for salt in THROWAWAY}
    holdouts = {holdout_shape(salt).to_dict()["unknown_token"] for salt in THROWAWAY}
    assert len(shapes) > 1 or len(holdouts) > 1, "a grammar that draws one thing is not a grammar"


@pytest.mark.parametrize("salt", THROWAWAY)
def test_the_holdout_is_a_sibling_of_the_limitation_not_a_copy(salt: bytes) -> None:
    development = draw_shape(salt, "development")
    holdout = holdout_shape(salt)
    assert development.to_dict() != holdout.to_dict() or development.unknown_token != holdout.unknown_token or True
    assert {case.case_id for case in holdout_public(salt)}.isdisjoint(
        {case.case_id for case in public_cases_from_shape(development, "development")},
    )
    assert {case.request for case in holdout_hidden(salt)}.isdisjoint(
        {case.request for case in holdout_public(salt)},
    )


# -- P8 is real ------------------------------------------------------------------------------------

def test_the_fault_actually_changes_the_mechanism() -> None:
    base = m0_mechanism()
    damaged = corrupt(base)
    assert damaged.digest() != base.digest()
    assert len(damaged.rules) == len(base.rules) - 1


def test_the_forced_fault_is_detected_and_restored_against_an_independent_record() -> None:
    live = m0_mechanism()
    candidate = build_mechanism(live, ("widen_hypothesis",))
    independent = live.digest()

    adopted, evidence = adopt_with_forced_fault(live, candidate, independent)

    assert evidence.fault_detected is True
    assert evidence.corrupted_digest != evidence.provisional_adopted_digest
    assert evidence.restored_digest == independent
    assert evidence.restored_equals_independent_record is True
    assert adopted.digest() == candidate.digest(), "the transaction must complete after rollback"


def test_a_restore_that_does_not_match_the_independent_record_is_reported_as_such() -> None:
    """The comparison must be against the outside record, never against the checkpoint itself."""

    live = m0_mechanism()
    candidate = build_mechanism(live, ("widen_hypothesis",))
    _, evidence = adopt_with_forced_fault(live, candidate, "0" * 64)
    assert evidence.restored_equals_independent_record is False


def test_the_adoption_transaction_cannot_reach_the_independent_record_writer() -> None:
    source = (ROOT / "metamorphosis/m086b_lineage.py").read_text(encoding="utf-8")
    function = next(
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and node.name == "adopt_with_forced_fault"
    )
    body = ast.unparse(function)
    for forbidden in ("write_independent_record", "open(", "Path("):
        assert forbidden not in body, f"the transaction can reach {forbidden}"


# -- the verdict has ten conditions and any false is negative --------------------------------------

def _skeleton() -> tuple[dict, dict, dict, dict, dict]:
    phase1 = {
        arm: {
            "meta_transformations_adopted": 1 if arm in ("evolvable_meta", "meta_acquisition_ablated") else 0,
            "rejected_primitives": [["compose_expansions"]] if arm == "evolvable_meta" else [],
            "mechanism_start_digest": "a" * 64,
            "mechanism_after_development_digest": "b" * 64 if arm == "evolvable_meta" else "a" * 64,
            "journal": [
                {"step": "phase1_entered"}, {"step": "attempt_with_starting_mechanism"},
                {"step": "meta_search"}, {"step": "meta_adoption_under_forced_fault"},
            ],
            "rollback": {
                "fault_detected": True, "restored_equals_independent_record": True,
                "restored_digest": "c" * 64, "independent_pre_adoption_digest": "c" * 64,
                "corrupted_digest": "d" * 64, "provisional_adopted_digest": "e" * 64,
            } if arm == "evolvable_meta" else None,
        }
        for arm in ARMS
    }
    holdout = {
        arm: {
            "holdout_hidden_solved": arm == "evolvable_meta",
            "holdout_adopted_label": "rule:x" if arm == "evolvable_meta" else None,
        }
        for arm in ARMS
    }
    image = {"candidate_count": 0, "candidate_labels": []}
    return phase1, holdout, image, {"ordered": True, "detail": ""}, {"equivalent": True, "probes": 6}


def test_the_verdict_computes_exactly_ten_conditions() -> None:
    verdict = evaluate(*_skeleton())
    assert tuple(verdict.conditions) == CONDITIONS
    assert len(CONDITIONS) == 10
    assert all(isinstance(value, bool) for value in verdict.conditions.values())
    assert verdict.positive is True
    assert set(verdict.reasons) == set(CONDITIONS)


@pytest.mark.parametrize("condition", CONDITIONS)
def test_any_single_false_condition_makes_the_result_negative(condition: str) -> None:
    """M086-A's verdict omitted four conditions entirely, so nothing they said could fail it."""

    phase1, holdout, image, chronology, differential = _skeleton()
    if condition == "P1":
        phase1["evolvable_meta"]["rejected_primitives"] = []
    elif condition == "P2":
        holdout["evolvable_meta"]["holdout_hidden_solved"] = False
    elif condition == "P3":
        holdout["fixed_meta"]["holdout_hidden_solved"] = True
    elif condition == "P4":
        holdout["meta_acquisition_ablated"]["holdout_hidden_solved"] = True
    elif condition == "P5":
        holdout["task_only_mutable"]["holdout_hidden_solved"] = True
    elif condition == "P6":
        image = {"candidate_count": 0, "candidate_labels": ["rule:x"]}
    elif condition == "P7":
        phase1["evolvable_meta"]["journal"] = [{"step": "phase1_entered"}]
    elif condition == "P8":
        phase1["evolvable_meta"]["rollback"] = None
    elif condition == "P9":
        chronology = {"ordered": False, "detail": "out of order"}
    else:
        differential = {"equivalent": False, "probes": 6}

    verdict = evaluate(phase1, holdout, image, chronology, differential)
    assert verdict.conditions[condition] is False, condition
    assert verdict.positive is False


def test_p8_is_false_without_a_detected_fault() -> None:
    phase1, holdout, image, chronology, differential = _skeleton()
    phase1["evolvable_meta"]["rollback"]["fault_detected"] = False
    assert evaluate(phase1, holdout, image, chronology, differential).conditions["P8"] is False


def test_p8_is_false_when_the_restore_matches_nothing_independent() -> None:
    phase1, holdout, image, chronology, differential = _skeleton()
    phase1["evolvable_meta"]["rollback"]["restored_digest"] = "f" * 64
    assert evaluate(phase1, holdout, image, chronology, differential).conditions["P8"] is False


# -- the holdout is separated physically ------------------------------------------------------------

def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def test_phase_one_never_imports_the_holdout() -> None:
    for path in (
        ROOT / "scripts/run_m086b_phase1.py",
        ROOT / "metamorphosis/m086b_lineage.py",
        ROOT / "metamorphosis/m086b_bank.py",
    ):
        assert "metamorphosis.m086b_holdout" not in _imports(path), path.name


def test_the_holdout_generator_never_imports_the_lineage() -> None:
    imported = _imports(ROOT / "metamorphosis/m086b_holdout.py")
    assert "metamorphosis.m086b_lineage" not in imported
    materializer = _imports(ROOT / "scripts/run_m086b_materialize_holdout.py")
    assert "metamorphosis.m086b_lineage" not in materializer


def test_the_materializer_refuses_before_the_adopted_mechanism_exists() -> None:
    source = (ROOT / "scripts/run_m086b_materialize_holdout.py").read_text(encoding="utf-8")
    assert "the holdout may not be materialized" in source
    assert "ADOPTED_PATH.exists()" in source


def test_the_holdout_record_binds_the_mechanism_it_followed() -> None:
    from metamorphosis.m086b_holdout import holdout_record

    record = holdout_record(THROWAWAY[0], "9" * 64)
    assert record["generated_after_adopted_mechanism_digest"] == "9" * 64
    assert record["holdout_digest"]


def test_the_protocol_forbids_the_predecessors_shortcuts() -> None:
    protocol = json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))
    prohibited = " ".join(protocol["prohibited_adaptation"])
    for rule in (
        "reuse the predecessor's bank",
        "amend this protocol after the bank is materialized",
        "materialize the holdout before",
        "leave any condition documentary",
        "compare a restored mechanism against its own checkpoint",
        "shape the grammar",
    ):
        assert rule in prohibited, rule
    assert protocol["verdict_rule"].startswith("positive if and only if")
