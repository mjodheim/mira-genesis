"""Tests for preserving the first M092 canonical search without qualifying its candidate."""
from __future__ import annotations

import pytest

import metamorphosis.m092_criterion_search as criterion
import metamorphosis.m092_search_enumerator as enumerator
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_kernel import Program, program_digest
import package_m092_canonical_search as packager

HEAD = "a" * 40
PARENT = "b" * 40
COUNTDOWN_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _marker() -> dict[str, object]:
    return {
        "schema": packager.ARM_SCHEMA,
        "frozen_parent_sha": PARENT,
        "program_limit": packager.PROGRAM_LIMIT,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "qualification_forbidden": True,
    }


def _selected_neutral_state() -> criterion.CriterionSearchState:
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
    record = enumerator.EnumerationRecord(
        ordinal=1,
        program=COUNTDOWN_PROGRAM,
        program_digest=program_digest(COUNTDOWN_PROGRAM),
        program_length=len(COUNTDOWN_PROGRAM),
        loop_headers=headers,
        structurally_valid=not refusals,
        structural_refusals=refusals,
        cursor=cursor,
    )
    state, _ = criterion._process_record(
        criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION),
        enumerator.EnumerationAudit(),
        record,
        COUNTDOWN_POSTCONDITION,
    )
    assert state.status == "candidate_selected"
    return state


def _package(state: criterion.CriterionSearchState, *, theorem: dict[str, object] | None = None,
             marker: dict[str, object] | None = None) -> dict[str, object]:
    return packager.package_result(
        state_payload=state.to_dict(),
        marker=marker or _marker(),
        target_theorem=theorem or COUNTDOWN_POSTCONDITION,
        head_sha=HEAD,
        parent_sha=PARENT,
    )


def test_terminal_selected_state_is_packaged_without_qualification() -> None:
    result = _package(_selected_neutral_state())

    assert result["status"] == "first-canonical-criterion-search-result"
    assert result["terminal_search_status"] == "candidate_selected"
    assert result["candidate_selected"] is True
    assert result["target_search_executed"] is True
    assert result["qualification_loaded"] is False
    assert result["candidate_executed_for_selection"] is False
    assert result["program_limit_requested"] == packager.PROGRAM_LIMIT
    assert result["canonical_search_attempt"] == 1
    assert isinstance(result["result_digest"], str) and len(result["result_digest"]) == 64


def test_nonterminal_state_cannot_be_preserved_as_first_result() -> None:
    state = criterion.CriterionSearchState.fresh(COUNTDOWN_POSTCONDITION)
    with pytest.raises(packager.PackageError, match="did not terminate"):
        _package(state)


def test_result_must_match_the_exact_target_theorem() -> None:
    different = {
        "schema": "m092-affine-postcondition-v1",
        "witnesses": [],
        "constraints": [{"relation": "eq", "coefficients": {"y": 1}, "constant": -1}],
    }
    with pytest.raises(packager.PackageError, match="different target theorem"):
        _package(_selected_neutral_state(), theorem=different)


def test_result_must_bind_current_selection_implementation() -> None:
    value = _selected_neutral_state().to_dict()
    bindings = dict(value["implementation_bindings"])  # type: ignore[arg-type]
    bindings["criterion_search"] = "0" * 64
    value["implementation_bindings"] = bindings
    payload = dict(value)
    payload.pop("state_digest", None)
    value["state_digest"] = criterion._sha256(payload)

    with pytest.raises(packager.PackageError, match="different selection code"):
        packager.package_result(
            state_payload=value,
            marker=_marker(),
            target_theorem=COUNTDOWN_POSTCONDITION,
            head_sha=HEAD,
            parent_sha=PARENT,
        )


def test_marker_cannot_change_full_search_budget() -> None:
    marker = _marker()
    marker["program_limit"] = packager.PROGRAM_LIMIT - 1
    with pytest.raises(packager.PackageError, match="full search budget"):
        _package(_selected_neutral_state(), marker=marker)


def test_marker_parent_and_first_run_flags_are_decisive() -> None:
    marker = _marker()
    marker["frozen_parent_sha"] = "c" * 40
    with pytest.raises(packager.PackageError, match="parent differs"):
        _package(_selected_neutral_state(), marker=marker)

    marker = _marker()
    marker["qualification_forbidden"] = False
    with pytest.raises(packager.PackageError, match="qualification_forbidden"):
        _package(_selected_neutral_state(), marker=marker)
