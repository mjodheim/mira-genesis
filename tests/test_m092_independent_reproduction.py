"""Pre-arm falsifiers for M092 independent reproduction."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

import metamorphosis.m092_criterion_search as criterion
import metamorphosis.m092_search_enumerator as enumerator
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_independent_reproduction import ReproductionError, validate_canonical_reference
from metamorphosis.m092_kernel import Program, program_digest
import package_m092_canonical_search as canonical_packager
import package_m092_canonical_segment as canonical_segment_packager
import package_m092_independent_reproduction as reproduction_packager
import package_m092_reproduction_segment as reproduction_segment_packager
import run_m092_independent_reproduction as reproduction_runner

HEAD = "a" * 40
PARENT = "b" * 40
SOURCE_RUN = 101
SOURCE_ARTIFACT = 202
SOURCE_DIGEST = "sha256:" + "c" * 64
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
        "schema": "m092-canonical-search-arm/1",
        "frozen_parent_sha": PARENT,
        "program_limit": 2_000_000,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "qualification_forbidden": True,
    }


def _selected_state() -> criterion.CriterionSearchState:
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


def _canonical_result(state: criterion.CriterionSearchState) -> dict[str, object]:
    segment = canonical_segment_packager.package_segment(
        output_state_payload=state.to_dict(),
        requirement=COUNTDOWN_POSTCONDITION,
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        segment_index=0,
        search_step_outcome="success",
        github_run_id=99,
        github_run_attempt=1,
    )
    return canonical_packager.package_result(
        state_payload=state.to_dict(),
        terminal_segment=segment,
        marker=_marker(),
        target_theorem=COUNTDOWN_POSTCONDITION,
        head_sha=HEAD,
        parent_sha=PARENT,
    )


def _reproduction_segment(state: criterion.CriterionSearchState) -> dict[str, object]:
    return reproduction_segment_packager.package_reproduction_segment(
        output_state_payload=state.to_dict(),
        requirement=COUNTDOWN_POSTCONDITION,
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        source_canonical_run_id=SOURCE_RUN,
        source_canonical_artifact_id=SOURCE_ARTIFACT,
        source_canonical_artifact_digest=SOURCE_DIGEST,
        segment_index=0,
        reproduction_step_outcome="success",
        github_run_id=303,
        github_run_attempt=1,
    )


def test_exact_terminal_reproduction_opens_only_the_reproduction_gate() -> None:
    state = _selected_state()
    result = reproduction_packager.package_independent_reproduction(
        reproduced_state_payload=state.to_dict(),
        terminal_reproduction_segment=_reproduction_segment(state),
        canonical_result=_canonical_result(state),
        target_theorem=COUNTDOWN_POSTCONDITION,
        marker=_marker(),
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        source_canonical_run_id=SOURCE_RUN,
        source_canonical_artifact_id=SOURCE_ARTIFACT,
        source_canonical_artifact_digest=SOURCE_DIGEST,
    )
    assert result["status"] == "independent-reproduction-match"
    assert result["state_byte_identical"] is True
    assert result["qualification_gate_open"] is True
    assert result["qualification_loaded"] is False
    assert result["candidate_executed_for_selection"] is False
    assert result["canonical_result_content_loaded_only_after_reproduction_terminal"] is True


def test_terminal_mismatch_is_preserved_and_never_opens_qualification() -> None:
    canonical_state = _selected_state()
    altered = canonical_state.to_dict()
    altered["criterion_event_chain_digest"] = "f" * 64
    payload = dict(altered)
    payload.pop("state_digest")
    altered["state_digest"] = criterion._sha256(payload)
    reproduced = criterion.CriterionSearchState.from_dict(altered)

    result = reproduction_packager.package_independent_reproduction(
        reproduced_state_payload=reproduced.to_dict(),
        terminal_reproduction_segment=_reproduction_segment(reproduced),
        canonical_result=_canonical_result(canonical_state),
        target_theorem=COUNTDOWN_POSTCONDITION,
        marker=_marker(),
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        source_canonical_run_id=SOURCE_RUN,
        source_canonical_artifact_id=SOURCE_ARTIFACT,
        source_canonical_artifact_digest=SOURCE_DIGEST,
    )
    assert result["status"] == "independent-reproduction-mismatch"
    assert result["state_byte_identical"] is False
    assert result["qualification_gate_open"] is False
    assert result["canonical_state_digest"] != result["reproduced_state_digest"]


def test_rehashed_canonical_reference_with_different_marker_is_rejected() -> None:
    state = _selected_state()
    result = _canonical_result(state)
    result["marker"] = {**_marker(), "qualification_forbidden": False}
    result["marker_digest"] = criterion._sha256(result["marker"])
    payload = dict(result)
    payload.pop("result_digest")
    result["result_digest"] = criterion._sha256(payload)

    with pytest.raises(ReproductionError, match="marker differs"):
        validate_canonical_reference(
            result,
            target_theorem=COUNTDOWN_POSTCONDITION,
            marker=_marker(),
            arming_head_sha=HEAD,
            arming_parent_sha=PARENT,
        )


def test_reproduction_segment_is_bound_to_exact_source_artifact() -> None:
    state = _selected_state()
    segment = _reproduction_segment(state)
    with pytest.raises(reproduction_packager.ReproductionPackageError, match="canonical artifact differs"):
        reproduction_packager.package_independent_reproduction(
            reproduced_state_payload=state.to_dict(),
            terminal_reproduction_segment=segment,
            canonical_result=_canonical_result(state),
            target_theorem=COUNTDOWN_POSTCONDITION,
            marker=_marker(),
            arming_head_sha=HEAD,
            arming_parent_sha=PARENT,
            source_canonical_run_id=SOURCE_RUN,
            source_canonical_artifact_id=SOURCE_ARTIFACT + 1,
            source_canonical_artifact_digest=SOURCE_DIGEST,
        )


def test_reproduction_runner_has_no_canonical_result_input_or_import() -> None:
    source = Path(reproduction_runner.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "canonical-result" not in source
    assert "package_m092_canonical_search" not in source
    assert "m092-first-canonical-search-result" not in source
    project_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(alias.name for alias in node.names if alias.name.startswith("metamorphosis"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            project_imports.add(node.module)
    assert project_imports == {
        "metamorphosis.m092_criterion_search",
        "metamorphosis.m092_independent_reproduction",
    }
    assert all("qualification" not in name for name in project_imports)
