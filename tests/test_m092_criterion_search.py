"""Neutral pre-search tests for the M092 criterion-selection instrument."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import metamorphosis.m092_criterion_search as criterion
import metamorphosis.m092_search_enumerator as enumerator
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_kernel import Program, program_digest


COUNTDOWN_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _synthetic_countdown_record() -> enumerator.EnumerationRecord:
    headers, refusals = enumerator._classify(COUNTDOWN_PROGRAM)
    plan = {item.program_length: item for item in enumerator.search_layer_plan()}
    cursor = enumerator.EnumerationCursor.make(
        seed=enumerator.SEARCH_SEED,
        program_length=len(COUNTDOWN_PROGRAM),
        decision_path=(0,) * (len(COUNTDOWN_PROGRAM) - 2),
        generated_programs=1,
        emitted_in_length=1,
        layer_quota=plan[len(COUNTDOWN_PROGRAM)].quota,
    )
    return enumerator.EnumerationRecord(
        ordinal=1,
        program=COUNTDOWN_PROGRAM,
        program_digest=program_digest(COUNTDOWN_PROGRAM),
        program_length=len(COUNTDOWN_PROGRAM),
        loop_headers=headers,
        structurally_valid=not refusals,
        structural_refusals=refusals,
        cursor=cursor,
    )


def _selected_neutral_state() -> criterion.CriterionSearchState:
    state = criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION)
    selected, _ = criterion._process_record(
        state,
        enumerator.EnumerationAudit(),
        _synthetic_countdown_record(),
        COUNTDOWN_POSTCONDITION,
    )
    return selected


def _refresh_state_digest(value: dict[str, object]) -> None:
    payload = dict(value)
    payload.pop("state_digest", None)
    value["state_digest"] = criterion._sha256(payload)


def test_first_accepted_neutral_candidate_is_selected_without_execution() -> None:
    selected = _selected_neutral_state()

    assert selected.status == "candidate_selected"
    assert selected.surviving_candidates == 1
    assert selected.selected is not None
    assert selected.selected["program_ordinal"] == 1
    assert selected.selected["program_digest"] == program_digest(COUNTDOWN_PROGRAM)
    serialized = selected.to_dict()
    assert serialized["candidate_executed_for_selection"] is False
    assert serialized["qualification_loaded"] is False
    assert serialized["verifier_feedback_used_for_repair"] is False


def test_selected_state_is_terminal_for_future_advance_calls() -> None:
    selected = _selected_neutral_state()
    advanced = criterion.advance_search(
        selected,
        COUNTDOWN_POSTCONDITION,
        program_limit=100,
    )
    assert advanced.to_dict() == selected.to_dict()


def test_resume_matches_uninterrupted_real_enumerator_prefix() -> None:
    uninterrupted = criterion.advance_search(
        criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION),
        COUNTDOWN_POSTCONDITION,
        program_limit=2,
    )

    first = criterion.advance_search(
        criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION),
        COUNTDOWN_POSTCONDITION,
        program_limit=1,
    )
    restored = criterion.CriterionSearchState.from_dict(json.loads(json.dumps(
        first.to_dict(), sort_keys=True, separators=(",", ":"),
    )))
    resumed = criterion.advance_search(
        restored,
        COUNTDOWN_POSTCONDITION,
        program_limit=1,
    )

    assert resumed.to_dict() == uninterrupted.to_dict()


def test_resume_refuses_a_different_theorem() -> None:
    state = criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION)
    different_neutral_theorem = {
        "schema": "m092-affine-postcondition-v1",
        "witnesses": [],
        "constraints": [
            {"relation": "eq", "coefficients": {"y": 1}, "constant": -1},
        ],
    }
    with pytest.raises(criterion.CriterionSearchError, match="theorem differs"):
        criterion.advance_search(state, different_neutral_theorem, program_limit=1)


def test_state_digest_detects_counter_tampering() -> None:
    value = criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION).to_dict()
    value["generated_programs"] = 1
    with pytest.raises(criterion.CriterionSearchError, match="state digest differs"):
        criterion.CriterionSearchState.from_dict(value)


def test_semantic_validation_rejects_rehashed_selected_program_tampering() -> None:
    value = _selected_neutral_state().to_dict()
    selected = dict(value["selected"])  # type: ignore[arg-type]
    selected["program_digest"] = "0" * 64
    value["selected"] = selected
    _refresh_state_digest(value)

    with pytest.raises(criterion.CriterionSearchError, match="program digest differs"):
        criterion.CriterionSearchState.from_dict(value)


def test_semantic_validation_rejects_rehashed_false_terminal_status() -> None:
    value = criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION).to_dict()
    value["status"] = "program_budget_exhausted"
    _refresh_state_digest(value)

    with pytest.raises(criterion.CriterionSearchError, match="terminal status differs"):
        criterion.CriterionSearchState.from_dict(value)


def test_criterion_instrument_has_no_qualification_import_edge() -> None:
    tree = ast.parse(Path(criterion.__file__).read_text(encoding="utf-8"))
    project_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(
                alias.name for alias in node.names if alias.name.startswith("metamorphosis")
            )
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            project_imports.add(node.module)

    assert all("qualification" not in name.lower() for name in project_imports)
    assert all("world" not in name.lower() for name in project_imports)
    assert all("materialize" not in name.lower() for name in project_imports)
