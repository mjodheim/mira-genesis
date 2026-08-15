"""Pre-search falsifiers for immutable multi-run M092 canonical transport."""
from __future__ import annotations

import hashlib

import pytest

import package_m092_canonical_segment as segment_packager
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_criterion_search import CriterionSearchState, advance_search
from metamorphosis.m092_resume_validation import (
    ResumeValidationError,
    verified_segment_resume_state,
)
from metamorphosis.m092_runtime import canonical_bytes

HEAD = "a" * 40
PARENT = "b" * 40


def _rehash_segment(segment: dict[str, object]) -> dict[str, object]:
    payload = dict(segment)
    payload.pop("segment_digest", None)
    payload["segment_digest"] = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    return payload


def _first_segment() -> tuple[dict[str, object], dict[str, object]]:
    requirement = COUNTDOWN_POSTCONDITION
    initial = CriterionSearchState.fresh(requirement)
    advanced = advance_search(initial, requirement, program_limit=1)
    assert advanced.status == "searching"
    receipt = segment_packager.package_segment(
        output_state_payload=advanced.to_dict(),
        requirement=requirement,
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        segment_index=0,
        search_step_outcome="failure",
        github_run_id=100,
        github_run_attempt=1,
    )
    return advanced.to_dict(), receipt


def test_genesis_segment_can_authorize_exact_nonterminal_checkpoint() -> None:
    state, receipt = _first_segment()
    resumed = verified_segment_resume_state(
        state,
        receipt,
        COUNTDOWN_POSTCONDITION,
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        expected_segment_index=0,
    )
    assert resumed.to_dict() == state


def test_rehashed_segment_cannot_point_at_a_different_checkpoint() -> None:
    state, receipt = _first_segment()
    forged = dict(receipt)
    forged["output_state_digest"] = "c" * 64
    forged = _rehash_segment(forged)

    with pytest.raises(ResumeValidationError, match="does not bind the supplied checkpoint"):
        verified_segment_resume_state(
            state,
            forged,
            COUNTDOWN_POSTCONDITION,
            arming_head_sha=HEAD,
            arming_parent_sha=PARENT,
            expected_segment_index=0,
        )


def test_segment_cannot_move_to_a_different_arming_head() -> None:
    state, receipt = _first_segment()
    with pytest.raises(ResumeValidationError, match="arming head differs"):
        verified_segment_resume_state(
            state,
            receipt,
            COUNTDOWN_POSTCONDITION,
            arming_head_sha="d" * 40,
            arming_parent_sha=PARENT,
            expected_segment_index=0,
        )


def test_continuation_receipt_binds_predecessor_artifact_and_segment() -> None:
    first_state_payload, first_receipt = _first_segment()
    first_state = CriterionSearchState.from_dict(first_state_payload)
    second_state = advance_search(first_state, COUNTDOWN_POSTCONDITION, program_limit=1)

    second_receipt = segment_packager.package_segment(
        output_state_payload=second_state.to_dict(),
        requirement=COUNTDOWN_POSTCONDITION,
        arming_head_sha=HEAD,
        arming_parent_sha=PARENT,
        segment_index=1,
        search_step_outcome="failure",
        github_run_id=101,
        github_run_attempt=1,
        input_state_payload=first_state_payload,
        previous_segment=first_receipt,
        previous_artifact_id=12345,
        previous_artifact_digest="e" * 64,
    )

    assert second_receipt["previous_segment_digest"] == first_receipt["segment_digest"]
    assert second_receipt["previous_artifact_id"] == 12345
    assert second_receipt["previous_artifact_digest"] == "e" * 64
    assert second_receipt["input_state_digest"] == first_state_payload["state_digest"]
    assert second_receipt["output_state_digest"] == second_state.to_dict()["state_digest"]


def test_continuation_rejects_wrong_predecessor_state_even_when_self_hashed() -> None:
    first_state_payload, first_receipt = _first_segment()
    different = advance_search(
        CriterionSearchState.from_dict(first_state_payload),
        COUNTDOWN_POSTCONDITION,
        program_limit=1,
    ).to_dict()

    with pytest.raises(segment_packager.SegmentPackageError, match="predecessor failed"):
        segment_packager.package_segment(
            output_state_payload=different,
            requirement=COUNTDOWN_POSTCONDITION,
            arming_head_sha=HEAD,
            arming_parent_sha=PARENT,
            segment_index=1,
            search_step_outcome="failure",
            github_run_id=101,
            github_run_attempt=1,
            input_state_payload=different,
            previous_segment=first_receipt,
            previous_artifact_id=12345,
            previous_artifact_digest="f" * 64,
        )


def test_successful_nonterminal_segment_is_refused() -> None:
    state, _ = _first_segment()
    with pytest.raises(segment_packager.SegmentPackageError, match="did not terminate"):
        segment_packager.package_segment(
            output_state_payload=state,
            requirement=COUNTDOWN_POSTCONDITION,
            arming_head_sha=HEAD,
            arming_parent_sha=PARENT,
            segment_index=0,
            search_step_outcome="success",
            github_run_id=100,
            github_run_attempt=1,
        )
