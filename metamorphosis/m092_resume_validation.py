"""Resume validation for the frozen M092 criterion search.

A plain serialized criterion state is never authority: ``verified_resume_state`` retains the strong
M092-D rule and reconstructs the complete claimed prefix from genesis before accepting it.

The canonical GitHub transport also has a second, deliberately narrower resume path for long-running
execution split across immutable Actions artifacts.  ``verified_segment_resume_state`` accepts only
the exact output checkpoint recorded by one canonical segment receipt, bound to the frozen arming
head/parent, theorem and implementation.  Artifact identity and artifact SHA-256 are checked by the
workflow before this function is called; the receipt then binds that external artifact provenance to
the serialized criterion state.  This path is transport-only and may resume only a non-terminal
checkpoint.  It does not execute or inspect qualification material.
"""
from __future__ import annotations

import hashlib
import re
from typing import Mapping

from metamorphosis.m092_criterion_search import (
    CriterionSearchState,
    advance_search,
    implementation_digests,
)
from metamorphosis.m092_runtime import canonical_bytes


SEGMENT_SCHEMA = "m092-canonical-search-segment/1"
TERMINAL_STATUSES = frozenset({
    "candidate_selected",
    "program_budget_exhausted",
    "certificate_budget_exhausted",
})
_SHA40 = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")
_ARTIFACT_DIGEST = re.compile(r"\A(?:sha256:)?[0-9a-f]{64}\Z")


class ResumeValidationError(ValueError):
    """A supplied criterion state is not an authorized deterministic search prefix."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def verified_resume_state(
    raw_state: Mapping[str, object],
    requirement: Mapping[str, object],
) -> CriterionSearchState:
    """Validate internal integrity and replay the complete claimed prefix from genesis."""

    supplied = CriterionSearchState.from_dict(raw_state)
    replayed = advance_search(
        CriterionSearchState.fresh(requirement),
        requirement,
        program_limit=supplied.generated_programs,
    )
    if replayed.to_dict() != supplied.to_dict():
        raise ResumeValidationError(
            "resume state does not match deterministic replay from the frozen M092 criterion genesis"
        )
    return supplied


def _validated_segment_record(
    raw_segment: Mapping[str, object],
    *,
    arming_head_sha: str,
    arming_parent_sha: str,
    expected_segment_index: int,
) -> dict[str, object]:
    expected_fields = {
        "schema",
        "segment_index",
        "arming_head_sha",
        "arming_parent_sha",
        "previous_segment_digest",
        "previous_artifact_id",
        "previous_artifact_digest",
        "input_state_digest",
        "output_state_digest",
        "generated_programs_start",
        "generated_programs_end",
        "certificate_policy_attempts_start",
        "certificate_policy_attempts_end",
        "search_step_outcome",
        "target_search_execution_step_reached",
        "checkpoint_terminal",
        "candidate_executed_for_selection",
        "qualification_loaded",
        "github_run_id",
        "github_run_attempt",
        "segment_digest",
    }
    if set(raw_segment) != expected_fields or raw_segment.get("schema") != SEGMENT_SCHEMA:
        raise ResumeValidationError("canonical segment schema or fields differ")
    if _SHA40.fullmatch(arming_head_sha) is None or _SHA40.fullmatch(arming_parent_sha) is None:
        raise ResumeValidationError("expected canonical arming SHAs are malformed")
    if raw_segment.get("arming_head_sha") != arming_head_sha:
        raise ResumeValidationError("canonical segment arming head differs")
    if raw_segment.get("arming_parent_sha") != arming_parent_sha:
        raise ResumeValidationError("canonical segment arming parent differs")
    if (
        not isinstance(expected_segment_index, int)
        or isinstance(expected_segment_index, bool)
        or expected_segment_index < 0
        or raw_segment.get("segment_index") != expected_segment_index
    ):
        raise ResumeValidationError("canonical segment index differs")

    payload = dict(raw_segment)
    supplied_digest = payload.pop("segment_digest")
    if not isinstance(supplied_digest, str) or supplied_digest != _sha256(payload):
        raise ResumeValidationError("canonical segment digest differs")

    integer_fields = (
        "generated_programs_start",
        "generated_programs_end",
        "certificate_policy_attempts_start",
        "certificate_policy_attempts_end",
        "github_run_id",
        "github_run_attempt",
    )
    integers: dict[str, int] = {}
    for field in integer_fields:
        value = raw_segment.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ResumeValidationError(f"canonical segment {field} is malformed")
        integers[field] = value
    if integers["github_run_id"] == 0 or integers["github_run_attempt"] == 0:
        raise ResumeValidationError("canonical segment GitHub run identity is malformed")
    if integers["generated_programs_end"] < integers["generated_programs_start"]:
        raise ResumeValidationError("canonical segment program counter moved backwards")
    if integers["certificate_policy_attempts_end"] < integers["certificate_policy_attempts_start"]:
        raise ResumeValidationError("canonical segment certificate counter moved backwards")

    for field in ("input_state_digest", "output_state_digest"):
        if not isinstance(raw_segment.get(field), str) or _SHA64.fullmatch(str(raw_segment[field])) is None:
            raise ResumeValidationError(f"canonical segment {field} is malformed")
    if raw_segment.get("search_step_outcome") not in {"success", "failure", "cancelled"}:
        raise ResumeValidationError("canonical segment search outcome is malformed")
    if raw_segment.get("target_search_execution_step_reached") is not True:
        raise ResumeValidationError("canonical segment did not reach target-search execution")
    if raw_segment.get("candidate_executed_for_selection") is not False:
        raise ResumeValidationError("canonical segment claims candidate execution for selection")
    if raw_segment.get("qualification_loaded") is not False:
        raise ResumeValidationError("canonical segment claims qualification access")
    if not isinstance(raw_segment.get("checkpoint_terminal"), bool):
        raise ResumeValidationError("canonical segment terminal flag is malformed")

    previous_segment_digest = raw_segment.get("previous_segment_digest")
    previous_artifact_id = raw_segment.get("previous_artifact_id")
    previous_artifact_digest = raw_segment.get("previous_artifact_digest")
    if expected_segment_index == 0:
        if any(value is not None for value in (
            previous_segment_digest, previous_artifact_id, previous_artifact_digest,
        )):
            raise ResumeValidationError("genesis segment unexpectedly names a predecessor")
        if integers["generated_programs_start"] != 0 or integers["certificate_policy_attempts_start"] != 0:
            raise ResumeValidationError("genesis segment does not start from zero counters")
    else:
        if not isinstance(previous_segment_digest, str) or _SHA64.fullmatch(previous_segment_digest) is None:
            raise ResumeValidationError("continuation segment predecessor digest is malformed")
        if not isinstance(previous_artifact_id, int) or isinstance(previous_artifact_id, bool) or previous_artifact_id <= 0:
            raise ResumeValidationError("continuation segment predecessor artifact id is malformed")
        if not isinstance(previous_artifact_digest, str) or _ARTIFACT_DIGEST.fullmatch(previous_artifact_digest) is None:
            raise ResumeValidationError("continuation segment predecessor artifact digest is malformed")

    return dict(raw_segment)


def verified_segment_resume_state(
    raw_state: Mapping[str, object],
    raw_segment: Mapping[str, object],
    requirement: Mapping[str, object],
    *,
    arming_head_sha: str,
    arming_parent_sha: str,
    expected_segment_index: int,
) -> CriterionSearchState:
    """Accept one immutable canonical segment output as the next transport checkpoint.

    This intentionally does not replay the full historical prefix.  The workflow must first verify
    the predecessor artifact id, immutable artifact digest, workflow run and exact arming head.  The
    segment receipt then cryptographically binds that externally authenticated artifact to this
    exact criterion state.  A separate deterministic reproduction remains required before a
    terminal target-search result can support later qualification.
    """

    segment = _validated_segment_record(
        raw_segment,
        arming_head_sha=arming_head_sha,
        arming_parent_sha=arming_parent_sha,
        expected_segment_index=expected_segment_index,
    )
    try:
        state = CriterionSearchState.from_dict(raw_state)
    except ValueError as error:
        raise ResumeValidationError("canonical segment checkpoint failed semantic validation") from error

    fresh = CriterionSearchState.fresh(requirement)
    if state.theorem_digest != fresh.theorem_digest:
        raise ResumeValidationError("canonical segment checkpoint theorem differs")
    if dict(state.implementation_bindings) != implementation_digests():
        raise ResumeValidationError("canonical segment checkpoint implementation differs")
    serialized = state.to_dict()
    if segment["output_state_digest"] != serialized["state_digest"]:
        raise ResumeValidationError("canonical segment does not bind the supplied checkpoint")
    if segment["generated_programs_end"] != state.generated_programs:
        raise ResumeValidationError("canonical segment program count differs from checkpoint")
    if segment["certificate_policy_attempts_end"] != state.certificate_policy_attempts:
        raise ResumeValidationError("canonical segment certificate count differs from checkpoint")
    terminal = state.status in TERMINAL_STATUSES
    if segment["checkpoint_terminal"] is not terminal:
        raise ResumeValidationError("canonical segment terminal flag differs from checkpoint")
    if terminal:
        raise ResumeValidationError("terminal canonical segment cannot be resumed")
    if serialized.get("candidate_executed_for_selection") is not False:
        raise ResumeValidationError("canonical checkpoint claims candidate execution for selection")
    if serialized.get("qualification_loaded") is not False:
        raise ResumeValidationError("canonical checkpoint claims qualification access")
    return state


__all__ = [
    "ResumeValidationError",
    "SEGMENT_SCHEMA",
    "TERMINAL_STATUSES",
    "verified_resume_state",
    "verified_segment_resume_state",
]
