"""Package one immutable segment of the independent M092 reproduction trajectory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping

from metamorphosis.m092_criterion_search import CriterionSearchState, implementation_digests
from metamorphosis.m092_independent_reproduction import (
    REPRODUCTION_SEGMENT_SCHEMA,
    TERMINAL_STATUSES,
    ReproductionError,
    verified_reproduction_resume_state,
)
from metamorphosis.m092_runtime import canonical_bytes

_SHA40 = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")
_ARTIFACT_DIGEST = re.compile(r"\A(?:sha256:)?[0-9a-f]{64}\Z")


class ReproductionSegmentError(ValueError):
    """A reproduction segment cannot be preserved."""


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReproductionSegmentError(f"{label} is not readable JSON") from error
    if not isinstance(value, dict):
        raise ReproductionSegmentError(f"{label} must be a JSON object")
    return value


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent), text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def package_reproduction_segment(
    *,
    output_state_payload: Mapping[str, object],
    requirement: Mapping[str, object],
    arming_head_sha: str,
    arming_parent_sha: str,
    source_canonical_run_id: int,
    source_canonical_artifact_id: int,
    source_canonical_artifact_digest: str,
    segment_index: int,
    reproduction_step_outcome: str,
    github_run_id: int,
    github_run_attempt: int,
    input_state_payload: Mapping[str, object] | None = None,
    previous_segment: Mapping[str, object] | None = None,
    previous_artifact_id: int | None = None,
    previous_artifact_digest: str | None = None,
) -> dict[str, object]:
    if _SHA40.fullmatch(arming_head_sha) is None or _SHA40.fullmatch(arming_parent_sha) is None:
        raise ReproductionSegmentError("reproduction arming SHAs must be full lowercase 40-hex")
    for label, value in (
        ("source canonical run id", source_canonical_run_id),
        ("source canonical artifact id", source_canonical_artifact_id),
        ("GitHub run id", github_run_id),
        ("GitHub run attempt", github_run_attempt),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ReproductionSegmentError(f"{label} must be a positive integer")
    if not isinstance(source_canonical_artifact_digest, str) or _ARTIFACT_DIGEST.fullmatch(source_canonical_artifact_digest) is None:
        raise ReproductionSegmentError("source canonical artifact digest is malformed")
    if not isinstance(segment_index, int) or isinstance(segment_index, bool) or segment_index < 0:
        raise ReproductionSegmentError("reproduction segment index must be non-negative")
    if reproduction_step_outcome not in {"success", "failure", "cancelled"}:
        raise ReproductionSegmentError("reproduction step outcome is invalid")

    try:
        output_state = CriterionSearchState.from_dict(output_state_payload)
    except ValueError as error:
        raise ReproductionSegmentError("reproduction output state failed semantic validation") from error
    fresh = CriterionSearchState.fresh(requirement)
    if output_state.theorem_digest != fresh.theorem_digest:
        raise ReproductionSegmentError("reproduction output theorem differs")
    if dict(output_state.implementation_bindings) != implementation_digests():
        raise ReproductionSegmentError("reproduction output implementation differs")

    previous_segment_digest: str | None = None
    if segment_index == 0:
        if any(value is not None for value in (
            input_state_payload, previous_segment, previous_artifact_id, previous_artifact_digest,
        )):
            raise ReproductionSegmentError("reproduction genesis unexpectedly supplies predecessor material")
        input_state = fresh
    else:
        if input_state_payload is None or previous_segment is None:
            raise ReproductionSegmentError("reproduction continuation requires predecessor state and receipt")
        if not isinstance(previous_artifact_id, int) or isinstance(previous_artifact_id, bool) or previous_artifact_id <= 0:
            raise ReproductionSegmentError("reproduction predecessor artifact id is invalid")
        if not isinstance(previous_artifact_digest, str) or _ARTIFACT_DIGEST.fullmatch(previous_artifact_digest) is None:
            raise ReproductionSegmentError("reproduction predecessor artifact digest is invalid")
        try:
            input_state = verified_reproduction_resume_state(
                input_state_payload,
                previous_segment,
                requirement,
                arming_head_sha=arming_head_sha,
                arming_parent_sha=arming_parent_sha,
                source_canonical_run_id=source_canonical_run_id,
                source_canonical_artifact_id=source_canonical_artifact_id,
                source_canonical_artifact_digest=source_canonical_artifact_digest,
                expected_segment_index=segment_index - 1,
            )
        except ReproductionError as error:
            raise ReproductionSegmentError("reproduction predecessor failed immutable validation") from error
        raw_digest = previous_segment.get("segment_digest")
        if not isinstance(raw_digest, str) or _SHA64.fullmatch(raw_digest) is None:
            raise ReproductionSegmentError("reproduction predecessor segment digest is invalid")
        previous_segment_digest = raw_digest

    if output_state.generated_programs < input_state.generated_programs:
        raise ReproductionSegmentError("reproduction program counter moved backwards")
    if output_state.certificate_policy_attempts < input_state.certificate_policy_attempts:
        raise ReproductionSegmentError("reproduction certificate counter moved backwards")
    if output_state.status == "searching" and (
        output_state.generated_programs == input_state.generated_programs
        and output_state.certificate_policy_attempts == input_state.certificate_policy_attempts
        and reproduction_step_outcome == "success"
    ):
        raise ReproductionSegmentError("successful non-terminal reproduction segment made no progress")
    if reproduction_step_outcome == "success" and output_state.status not in TERMINAL_STATUSES:
        raise ReproductionSegmentError("successful full-budget reproduction step did not terminate")

    serialized_input = input_state.to_dict()
    serialized_output = output_state.to_dict()
    if serialized_output.get("candidate_executed_for_selection") is not False:
        raise ReproductionSegmentError("reproduction output claims candidate execution")
    if serialized_output.get("qualification_loaded") is not False:
        raise ReproductionSegmentError("reproduction output claims qualification access")

    receipt: dict[str, object] = {
        "schema": REPRODUCTION_SEGMENT_SCHEMA,
        "segment_index": segment_index,
        "arming_head_sha": arming_head_sha,
        "arming_parent_sha": arming_parent_sha,
        "source_canonical_run_id": source_canonical_run_id,
        "source_canonical_artifact_id": source_canonical_artifact_id,
        "source_canonical_artifact_digest": source_canonical_artifact_digest,
        "previous_segment_digest": previous_segment_digest,
        "previous_artifact_id": previous_artifact_id,
        "previous_artifact_digest": previous_artifact_digest,
        "input_state_digest": serialized_input["state_digest"],
        "output_state_digest": serialized_output["state_digest"],
        "generated_programs_start": input_state.generated_programs,
        "generated_programs_end": output_state.generated_programs,
        "certificate_policy_attempts_start": input_state.certificate_policy_attempts,
        "certificate_policy_attempts_end": output_state.certificate_policy_attempts,
        "reproduction_step_outcome": reproduction_step_outcome,
        "reproduction_execution_step_reached": True,
        "canonical_result_content_loaded": False,
        "checkpoint_terminal": output_state.status in TERMINAL_STATUSES,
        "candidate_executed_for_selection": False,
        "qualification_loaded": False,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
    }
    receipt["segment_digest"] = _sha256(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-state", type=Path, required=True)
    parser.add_argument("--requirement", type=Path, required=True)
    parser.add_argument("--arming-head-sha", required=True)
    parser.add_argument("--arming-parent-sha", required=True)
    parser.add_argument("--source-canonical-run-id", type=int, required=True)
    parser.add_argument("--source-canonical-artifact-id", type=int, required=True)
    parser.add_argument("--source-canonical-artifact-digest", required=True)
    parser.add_argument("--segment-index", type=int, required=True)
    parser.add_argument("--reproduction-step-outcome", required=True)
    parser.add_argument("--github-run-id", type=int, required=True)
    parser.add_argument("--github-run-attempt", type=int, required=True)
    parser.add_argument("--input-state", type=Path)
    parser.add_argument("--previous-segment", type=Path)
    parser.add_argument("--previous-artifact-id", type=int)
    parser.add_argument("--previous-artifact-digest")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = package_reproduction_segment(
            output_state_payload=_read_object(args.output_state, "reproduction output state"),
            requirement=_read_object(args.requirement, "target theorem"),
            arming_head_sha=args.arming_head_sha,
            arming_parent_sha=args.arming_parent_sha,
            source_canonical_run_id=args.source_canonical_run_id,
            source_canonical_artifact_id=args.source_canonical_artifact_id,
            source_canonical_artifact_digest=args.source_canonical_artifact_digest,
            segment_index=args.segment_index,
            reproduction_step_outcome=args.reproduction_step_outcome,
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
            input_state_payload=None if args.input_state is None else _read_object(args.input_state, "reproduction predecessor state"),
            previous_segment=None if args.previous_segment is None else _read_object(args.previous_segment, "reproduction predecessor receipt"),
            previous_artifact_id=args.previous_artifact_id,
            previous_artifact_digest=args.previous_artifact_digest,
        )
    except ReproductionSegmentError as error:
        raise SystemExit(str(error)) from error
    _write_json_atomic(args.output, receipt)
    print(json.dumps({
        "segment_index": receipt["segment_index"],
        "segment_digest": receipt["segment_digest"],
        "generated_programs_start": receipt["generated_programs_start"],
        "generated_programs_end": receipt["generated_programs_end"],
        "checkpoint_terminal": receipt["checkpoint_terminal"],
        "canonical_result_content_loaded": receipt["canonical_result_content_loaded"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
