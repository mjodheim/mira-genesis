"""Independent pre-qualification reproduction boundary for M092.

The canonical search result is reference evidence, never a search input.  Reproduction advances the
same frozen criterion engine from genesis using its own immutable segment chain.  Canonical result
content is validated and compared only after the reproduction trajectory has reached a terminal
state.  No function in this module imports qualification material or executes a selected candidate.
"""
from __future__ import annotations

import hashlib
import re
from typing import Mapping

from metamorphosis.m092_criterion_search import (
    PROGRAM_CAP,
    CriterionSearchState,
    implementation_digests,
)
from metamorphosis.m092_runtime import canonical_bytes

CANONICAL_RESULT_SCHEMA = "m092-canonical-criterion-search-result/2"
CANONICAL_SEGMENT_SCHEMA = "m092-canonical-search-segment/1"
ARM_SCHEMA = "m092-canonical-search-arm/1"
REPRODUCTION_SEGMENT_SCHEMA = "m092-independent-reproduction-segment/1"
REPRODUCTION_RESULT_SCHEMA = "m092-independent-reproduction-result/1"
TERMINAL_STATUSES = frozenset({
    "candidate_selected",
    "program_budget_exhausted",
    "certificate_budget_exhausted",
})
_SHA40 = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")
_ARTIFACT_DIGEST = re.compile(r"\A(?:sha256:)?[0-9a-f]{64}\Z")


class ReproductionError(ValueError):
    """Reproduction provenance or deterministic equality failed closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _positive_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReproductionError(f"{label} must be a positive integer")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReproductionError(f"{label} must be a non-negative integer")
    return value


def _validate_artifact_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _ARTIFACT_DIGEST.fullmatch(value) is None:
        raise ReproductionError(f"{label} is not a SHA-256 artifact digest")
    return value


def _validate_terminal_canonical_segment(
    raw: Mapping[str, object],
    *,
    state: CriterionSearchState,
    arming_head_sha: str,
    arming_parent_sha: str,
) -> dict[str, object]:
    expected = {
        "schema", "segment_index", "arming_head_sha", "arming_parent_sha",
        "previous_segment_digest", "previous_artifact_id", "previous_artifact_digest",
        "input_state_digest", "output_state_digest", "generated_programs_start",
        "generated_programs_end", "certificate_policy_attempts_start",
        "certificate_policy_attempts_end", "search_step_outcome",
        "target_search_execution_step_reached", "checkpoint_terminal",
        "candidate_executed_for_selection", "qualification_loaded", "github_run_id",
        "github_run_attempt", "segment_digest",
    }
    if set(raw) != expected or raw.get("schema") != CANONICAL_SEGMENT_SCHEMA:
        raise ReproductionError("canonical terminal segment schema or fields differ")
    if raw.get("arming_head_sha") != arming_head_sha or raw.get("arming_parent_sha") != arming_parent_sha:
        raise ReproductionError("canonical terminal segment arming identity differs")
    payload = dict(raw)
    supplied = payload.pop("segment_digest", None)
    if not isinstance(supplied, str) or _SHA64.fullmatch(supplied) is None or supplied != _sha256(payload):
        raise ReproductionError("canonical terminal segment digest differs")
    index = _nonnegative_integer(raw.get("segment_index"), "canonical terminal segment index")
    _positive_integer(raw.get("github_run_id"), "canonical terminal segment run id")
    _positive_integer(raw.get("github_run_attempt"), "canonical terminal segment run attempt")
    if raw.get("checkpoint_terminal") is not True:
        raise ReproductionError("canonical terminal segment is not terminal")
    if raw.get("target_search_execution_step_reached") is not True:
        raise ReproductionError("canonical terminal segment never reached target search")
    if raw.get("candidate_executed_for_selection") is not False or raw.get("qualification_loaded") is not False:
        raise ReproductionError("canonical terminal segment crosses the selection boundary")
    serialized = state.to_dict()
    if raw.get("output_state_digest") != serialized["state_digest"]:
        raise ReproductionError("canonical terminal segment does not bind its search state")
    if raw.get("generated_programs_end") != state.generated_programs:
        raise ReproductionError("canonical terminal segment program count differs")
    if raw.get("certificate_policy_attempts_end") != state.certificate_policy_attempts:
        raise ReproductionError("canonical terminal segment certificate count differs")
    if state.status not in TERMINAL_STATUSES:
        raise ReproductionError("canonical reference state is not terminal")
    result = dict(raw)
    result["segment_index"] = index
    return result


def validate_canonical_reference(
    raw: Mapping[str, object],
    *,
    target_theorem: Mapping[str, object],
    marker: Mapping[str, object],
    arming_head_sha: str,
    arming_parent_sha: str,
) -> CriterionSearchState:
    """Validate canonical result content only after reproduction itself is terminal."""

    expected = {
        "schema", "status", "arming_head_sha", "frozen_parent_sha",
        "canonical_search_attempt", "canonical_transport_mode", "transport_segments",
        "terminal_segment_index", "terminal_segment_digest", "terminal_segment",
        "first_run_only", "reruns_are_reproductions_only", "qualification_forbidden",
        "independent_reproduction_required", "qualification_may_begin_before_reproduction",
        "target_search_executed", "qualification_loaded", "candidate_executed_for_selection",
        "program_limit_requested", "terminal_search_status", "candidate_selected",
        "generated_programs", "certificate_policy_attempts", "certificates_constructed",
        "surviving_candidates", "marker_digest", "marker", "search_state", "result_digest",
    }
    if set(raw) != expected or raw.get("schema") != CANONICAL_RESULT_SCHEMA:
        raise ReproductionError("canonical reference result schema or fields differ")
    payload = dict(raw)
    supplied_result_digest = payload.pop("result_digest", None)
    if (
        not isinstance(supplied_result_digest, str)
        or _SHA64.fullmatch(supplied_result_digest) is None
        or supplied_result_digest != _sha256(payload)
    ):
        raise ReproductionError("canonical reference result digest differs")
    if _SHA40.fullmatch(arming_head_sha) is None or _SHA40.fullmatch(arming_parent_sha) is None:
        raise ReproductionError("expected canonical arming SHAs are malformed")
    if raw.get("arming_head_sha") != arming_head_sha or raw.get("frozen_parent_sha") != arming_parent_sha:
        raise ReproductionError("canonical reference arming identity differs")
    if raw.get("status") != "first-canonical-criterion-search-result":
        raise ReproductionError("canonical reference status differs")
    if raw.get("canonical_search_attempt") != 1:
        raise ReproductionError("canonical reference is not the first search attempt")
    if raw.get("canonical_transport_mode") != "immutable-artifact-segment-chain":
        raise ReproductionError("canonical reference transport mode differs")
    if raw.get("program_limit_requested") != PROGRAM_CAP:
        raise ReproductionError("canonical reference program budget differs")
    required_true = (
        "first_run_only", "reruns_are_reproductions_only", "qualification_forbidden",
        "independent_reproduction_required", "target_search_executed",
    )
    if any(raw.get(field) is not True for field in required_true):
        raise ReproductionError("canonical reference first-run/reproduction flags differ")
    if raw.get("qualification_may_begin_before_reproduction") is not False:
        raise ReproductionError("canonical reference permits qualification before reproduction")
    if raw.get("qualification_loaded") is not False or raw.get("candidate_executed_for_selection") is not False:
        raise ReproductionError("canonical reference crosses the pre-qualification boundary")
    if dict(raw.get("marker") or {}) != dict(marker) or raw.get("marker_digest") != _sha256(marker):
        raise ReproductionError("canonical reference marker differs from the frozen arming marker")
    if marker.get("schema") != ARM_SCHEMA or marker.get("frozen_parent_sha") != arming_parent_sha:
        raise ReproductionError("frozen arming marker identity differs")
    if marker.get("program_limit") != PROGRAM_CAP:
        raise ReproductionError("frozen arming marker program budget differs")
    for field in ("first_run_only", "reruns_are_reproductions_only", "qualification_forbidden"):
        if marker.get(field) is not True:
            raise ReproductionError(f"frozen arming marker {field} differs")

    state_payload = raw.get("search_state")
    if not isinstance(state_payload, Mapping):
        raise ReproductionError("canonical reference search state is missing")
    try:
        state = CriterionSearchState.from_dict(state_payload)
    except ValueError as error:
        raise ReproductionError("canonical reference search state failed semantic validation") from error
    if state.status not in TERMINAL_STATUSES:
        raise ReproductionError("canonical reference search state is not terminal")
    if state.theorem_digest != _sha256(target_theorem):
        raise ReproductionError("canonical reference theorem differs")
    if dict(state.implementation_bindings) != implementation_digests():
        raise ReproductionError("canonical reference selection implementation differs")
    if raw.get("terminal_search_status") != state.status:
        raise ReproductionError("canonical reference terminal status differs from its state")
    if raw.get("candidate_selected") is not (state.status == "candidate_selected"):
        raise ReproductionError("canonical reference candidate flag differs")
    for field, actual in (
        ("generated_programs", state.generated_programs),
        ("certificate_policy_attempts", state.certificate_policy_attempts),
        ("certificates_constructed", state.certificates_constructed),
        ("surviving_candidates", state.surviving_candidates),
    ):
        if raw.get(field) != actual:
            raise ReproductionError(f"canonical reference {field} differs from its state")

    terminal_raw = raw.get("terminal_segment")
    if not isinstance(terminal_raw, Mapping):
        raise ReproductionError("canonical reference terminal segment is missing")
    terminal = _validate_terminal_canonical_segment(
        terminal_raw,
        state=state,
        arming_head_sha=arming_head_sha,
        arming_parent_sha=arming_parent_sha,
    )
    terminal_index = int(terminal["segment_index"])
    if raw.get("terminal_segment_index") != terminal_index:
        raise ReproductionError("canonical reference terminal segment index differs")
    if raw.get("transport_segments") != terminal_index + 1:
        raise ReproductionError("canonical reference transport segment count differs")
    if raw.get("terminal_segment_digest") != terminal.get("segment_digest"):
        raise ReproductionError("canonical reference terminal segment digest differs")
    return state


def _validate_reproduction_segment(
    raw: Mapping[str, object],
    *,
    arming_head_sha: str,
    arming_parent_sha: str,
    source_canonical_run_id: int,
    source_canonical_artifact_id: int,
    source_canonical_artifact_digest: str,
    expected_segment_index: int,
) -> dict[str, object]:
    expected = {
        "schema", "segment_index", "arming_head_sha", "arming_parent_sha",
        "source_canonical_run_id", "source_canonical_artifact_id",
        "source_canonical_artifact_digest", "previous_segment_digest",
        "previous_artifact_id", "previous_artifact_digest", "input_state_digest",
        "output_state_digest", "generated_programs_start", "generated_programs_end",
        "certificate_policy_attempts_start", "certificate_policy_attempts_end",
        "reproduction_step_outcome", "reproduction_execution_step_reached",
        "canonical_result_content_loaded", "checkpoint_terminal",
        "candidate_executed_for_selection", "qualification_loaded", "github_run_id",
        "github_run_attempt", "segment_digest",
    }
    if set(raw) != expected or raw.get("schema") != REPRODUCTION_SEGMENT_SCHEMA:
        raise ReproductionError("reproduction segment schema or fields differ")
    if raw.get("arming_head_sha") != arming_head_sha or raw.get("arming_parent_sha") != arming_parent_sha:
        raise ReproductionError("reproduction segment arming identity differs")
    if raw.get("source_canonical_run_id") != source_canonical_run_id:
        raise ReproductionError("reproduction segment canonical run identity differs")
    if raw.get("source_canonical_artifact_id") != source_canonical_artifact_id:
        raise ReproductionError("reproduction segment canonical artifact identity differs")
    if raw.get("source_canonical_artifact_digest") != source_canonical_artifact_digest:
        raise ReproductionError("reproduction segment canonical artifact digest differs")
    if raw.get("segment_index") != expected_segment_index:
        raise ReproductionError("reproduction segment index differs")
    payload = dict(raw)
    supplied = payload.pop("segment_digest", None)
    if not isinstance(supplied, str) or _SHA64.fullmatch(supplied) is None or supplied != _sha256(payload):
        raise ReproductionError("reproduction segment digest differs")
    for field in (
        "generated_programs_start", "generated_programs_end",
        "certificate_policy_attempts_start", "certificate_policy_attempts_end",
    ):
        _nonnegative_integer(raw.get(field), f"reproduction segment {field}")
    _positive_integer(raw.get("github_run_id"), "reproduction segment run id")
    _positive_integer(raw.get("github_run_attempt"), "reproduction segment run attempt")
    if int(raw["generated_programs_end"]) < int(raw["generated_programs_start"]):
        raise ReproductionError("reproduction segment program counter moved backwards")
    if int(raw["certificate_policy_attempts_end"]) < int(raw["certificate_policy_attempts_start"]):
        raise ReproductionError("reproduction segment certificate counter moved backwards")
    for field in ("input_state_digest", "output_state_digest"):
        if not isinstance(raw.get(field), str) or _SHA64.fullmatch(str(raw[field])) is None:
            raise ReproductionError(f"reproduction segment {field} is malformed")
    if raw.get("reproduction_step_outcome") not in {"success", "failure", "cancelled"}:
        raise ReproductionError("reproduction step outcome is malformed")
    if raw.get("reproduction_execution_step_reached") is not True:
        raise ReproductionError("reproduction segment never reached reproduction execution")
    if raw.get("canonical_result_content_loaded") is not False:
        raise ReproductionError("reproduction trajectory loaded canonical result content")
    if raw.get("candidate_executed_for_selection") is not False or raw.get("qualification_loaded") is not False:
        raise ReproductionError("reproduction segment crosses the pre-qualification boundary")
    if not isinstance(raw.get("checkpoint_terminal"), bool):
        raise ReproductionError("reproduction segment terminal flag is malformed")
    if expected_segment_index == 0:
        if any(raw.get(field) is not None for field in (
            "previous_segment_digest", "previous_artifact_id", "previous_artifact_digest",
        )):
            raise ReproductionError("reproduction genesis segment unexpectedly names a predecessor")
        if raw.get("generated_programs_start") != 0 or raw.get("certificate_policy_attempts_start") != 0:
            raise ReproductionError("reproduction genesis segment does not start at zero")
    else:
        if not isinstance(raw.get("previous_segment_digest"), str) or _SHA64.fullmatch(str(raw["previous_segment_digest"])) is None:
            raise ReproductionError("reproduction predecessor segment digest is malformed")
        _positive_integer(raw.get("previous_artifact_id"), "reproduction predecessor artifact id")
        _validate_artifact_digest(raw.get("previous_artifact_digest"), "reproduction predecessor artifact digest")
    return dict(raw)


def verified_reproduction_resume_state(
    raw_state: Mapping[str, object],
    raw_segment: Mapping[str, object],
    requirement: Mapping[str, object],
    *,
    arming_head_sha: str,
    arming_parent_sha: str,
    source_canonical_run_id: int,
    source_canonical_artifact_id: int,
    source_canonical_artifact_digest: str,
    expected_segment_index: int,
) -> CriterionSearchState:
    """Resume only the exact non-terminal checkpoint in the independent reproduction chain."""

    segment = _validate_reproduction_segment(
        raw_segment,
        arming_head_sha=arming_head_sha,
        arming_parent_sha=arming_parent_sha,
        source_canonical_run_id=source_canonical_run_id,
        source_canonical_artifact_id=source_canonical_artifact_id,
        source_canonical_artifact_digest=source_canonical_artifact_digest,
        expected_segment_index=expected_segment_index,
    )
    try:
        state = CriterionSearchState.from_dict(raw_state)
    except ValueError as error:
        raise ReproductionError("reproduction checkpoint failed semantic validation") from error
    fresh = CriterionSearchState.fresh(requirement)
    if state.theorem_digest != fresh.theorem_digest:
        raise ReproductionError("reproduction checkpoint theorem differs")
    if dict(state.implementation_bindings) != implementation_digests():
        raise ReproductionError("reproduction checkpoint implementation differs")
    serialized = state.to_dict()
    if segment.get("output_state_digest") != serialized["state_digest"]:
        raise ReproductionError("reproduction segment does not bind its checkpoint")
    if segment.get("generated_programs_end") != state.generated_programs:
        raise ReproductionError("reproduction segment program count differs from checkpoint")
    if segment.get("certificate_policy_attempts_end") != state.certificate_policy_attempts:
        raise ReproductionError("reproduction segment certificate count differs from checkpoint")
    terminal = state.status in TERMINAL_STATUSES
    if segment.get("checkpoint_terminal") is not terminal:
        raise ReproductionError("reproduction segment terminal flag differs from checkpoint")
    if terminal:
        raise ReproductionError("terminal reproduction segment cannot be resumed")
    return state


__all__ = [
    "CANONICAL_RESULT_SCHEMA",
    "REPRODUCTION_RESULT_SCHEMA",
    "REPRODUCTION_SEGMENT_SCHEMA",
    "ReproductionError",
    "TERMINAL_STATUSES",
    "validate_canonical_reference",
    "verified_reproduction_resume_state",
]
