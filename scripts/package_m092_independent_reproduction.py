"""Package the first completed independent M092 reproduction against the canonical reference.

The workflow must call this only after the reproduction search state is already terminal.  Canonical
result content is therefore unavailable to the reproduction trajectory and is used here solely for
an exact post-hoc equality check.  A mismatch is a preserved reproduction result and never opens
qualification.
"""
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
    REPRODUCTION_RESULT_SCHEMA,
    REPRODUCTION_SEGMENT_SCHEMA,
    TERMINAL_STATUSES,
    ReproductionError,
    validate_canonical_reference,
)
from metamorphosis.m092_runtime import canonical_bytes

_SHA40 = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")
_ARTIFACT_DIGEST = re.compile(r"\A(?:sha256:)?[0-9a-f]{64}\Z")


class ReproductionPackageError(ValueError):
    """The completed reproduction cannot be preserved as a valid comparison result."""


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReproductionPackageError(f"{label} is not readable JSON") from error
    if not isinstance(value, dict):
        raise ReproductionPackageError(f"{label} must be a JSON object")
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


def _validate_terminal_reproduction_segment(
    raw: Mapping[str, object],
    *,
    reproduced_state: CriterionSearchState,
    arming_head_sha: str,
    arming_parent_sha: str,
    source_canonical_run_id: int,
    source_canonical_artifact_id: int,
    source_canonical_artifact_digest: str,
) -> dict[str, object]:
    if raw.get("schema") != REPRODUCTION_SEGMENT_SCHEMA:
        raise ReproductionPackageError("terminal reproduction segment schema differs")
    payload = dict(raw)
    supplied = payload.pop("segment_digest", None)
    if not isinstance(supplied, str) or _SHA64.fullmatch(supplied) is None or supplied != _sha256(payload):
        raise ReproductionPackageError("terminal reproduction segment digest differs")
    if raw.get("arming_head_sha") != arming_head_sha or raw.get("arming_parent_sha") != arming_parent_sha:
        raise ReproductionPackageError("terminal reproduction segment arming identity differs")
    if raw.get("source_canonical_run_id") != source_canonical_run_id:
        raise ReproductionPackageError("terminal reproduction segment canonical run differs")
    if raw.get("source_canonical_artifact_id") != source_canonical_artifact_id:
        raise ReproductionPackageError("terminal reproduction segment canonical artifact differs")
    if raw.get("source_canonical_artifact_digest") != source_canonical_artifact_digest:
        raise ReproductionPackageError("terminal reproduction segment canonical digest differs")
    index = raw.get("segment_index")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ReproductionPackageError("terminal reproduction segment index is malformed")
    if raw.get("checkpoint_terminal") is not True:
        raise ReproductionPackageError("terminal reproduction segment is not terminal")
    if raw.get("reproduction_execution_step_reached") is not True:
        raise ReproductionPackageError("terminal reproduction segment never executed reproduction")
    if raw.get("canonical_result_content_loaded") is not False:
        raise ReproductionPackageError("reproduction trajectory loaded canonical result content")
    if raw.get("qualification_loaded") is not False or raw.get("candidate_executed_for_selection") is not False:
        raise ReproductionPackageError("terminal reproduction segment crosses the pre-qualification boundary")
    serialized = reproduced_state.to_dict()
    if raw.get("output_state_digest") != serialized["state_digest"]:
        raise ReproductionPackageError("terminal reproduction segment does not bind reproduced state")
    if raw.get("generated_programs_end") != reproduced_state.generated_programs:
        raise ReproductionPackageError("terminal reproduction segment program count differs")
    if raw.get("certificate_policy_attempts_end") != reproduced_state.certificate_policy_attempts:
        raise ReproductionPackageError("terminal reproduction segment certificate count differs")
    return dict(raw)


def package_independent_reproduction(
    *,
    reproduced_state_payload: Mapping[str, object],
    terminal_reproduction_segment: Mapping[str, object],
    canonical_result: Mapping[str, object],
    target_theorem: Mapping[str, object],
    marker: Mapping[str, object],
    arming_head_sha: str,
    arming_parent_sha: str,
    source_canonical_run_id: int,
    source_canonical_artifact_id: int,
    source_canonical_artifact_digest: str,
) -> dict[str, object]:
    if _SHA40.fullmatch(arming_head_sha) is None or _SHA40.fullmatch(arming_parent_sha) is None:
        raise ReproductionPackageError("reproduction arming SHAs are malformed")
    for label, value in (
        ("source canonical run id", source_canonical_run_id),
        ("source canonical artifact id", source_canonical_artifact_id),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ReproductionPackageError(f"{label} must be a positive integer")
    if not isinstance(source_canonical_artifact_digest, str) or _ARTIFACT_DIGEST.fullmatch(source_canonical_artifact_digest) is None:
        raise ReproductionPackageError("source canonical artifact digest is malformed")

    try:
        reproduced = CriterionSearchState.from_dict(reproduced_state_payload)
    except ValueError as error:
        raise ReproductionPackageError("reproduced state failed semantic validation") from error
    if reproduced.status not in TERMINAL_STATUSES:
        raise ReproductionPackageError("independent reproduction is not terminal")
    if reproduced.theorem_digest != _sha256(target_theorem):
        raise ReproductionPackageError("reproduction theorem differs")
    if dict(reproduced.implementation_bindings) != implementation_digests():
        raise ReproductionPackageError("reproduction selection implementation differs")
    serialized_reproduction = reproduced.to_dict()
    if serialized_reproduction.get("qualification_loaded") is not False:
        raise ReproductionPackageError("reproduction state claims qualification access")
    if serialized_reproduction.get("candidate_executed_for_selection") is not False:
        raise ReproductionPackageError("reproduction state claims candidate execution")

    try:
        canonical_state = validate_canonical_reference(
            canonical_result,
            target_theorem=target_theorem,
            marker=marker,
            arming_head_sha=arming_head_sha,
            arming_parent_sha=arming_parent_sha,
        )
    except ReproductionError as error:
        raise ReproductionPackageError("canonical reference failed independent validation") from error

    segment = _validate_terminal_reproduction_segment(
        terminal_reproduction_segment,
        reproduced_state=reproduced,
        arming_head_sha=arming_head_sha,
        arming_parent_sha=arming_parent_sha,
        source_canonical_run_id=source_canonical_run_id,
        source_canonical_artifact_id=source_canonical_artifact_id,
        source_canonical_artifact_digest=source_canonical_artifact_digest,
    )
    byte_identical = serialized_reproduction == canonical_state.to_dict()
    canonical_result_digest = canonical_result.get("result_digest")
    if not isinstance(canonical_result_digest, str) or _SHA64.fullmatch(canonical_result_digest) is None:
        raise ReproductionPackageError("canonical reference result digest is malformed")

    result: dict[str, object] = {
        "schema": REPRODUCTION_RESULT_SCHEMA,
        "status": "independent-reproduction-match" if byte_identical else "independent-reproduction-mismatch",
        "arming_head_sha": arming_head_sha,
        "arming_parent_sha": arming_parent_sha,
        "source_canonical_run_id": source_canonical_run_id,
        "source_canonical_artifact_id": source_canonical_artifact_id,
        "source_canonical_artifact_digest": source_canonical_artifact_digest,
        "source_canonical_result_digest": canonical_result_digest,
        "terminal_reproduction_segment_index": segment["segment_index"],
        "terminal_reproduction_segment_digest": segment["segment_digest"],
        "canonical_result_content_loaded_only_after_reproduction_terminal": True,
        "reproduction_from_genesis": True,
        "reproduction_only": True,
        "target_search_rerolled": False,
        "qualification_loaded": False,
        "candidate_executed_for_selection": False,
        "canonical_terminal_status": canonical_state.status,
        "reproduced_terminal_status": reproduced.status,
        "canonical_state_digest": canonical_state.to_dict()["state_digest"],
        "reproduced_state_digest": serialized_reproduction["state_digest"],
        "state_byte_identical": byte_identical,
        "qualification_gate_open": byte_identical,
        "reproduced_search_state": serialized_reproduction,
    }
    result["result_digest"] = _sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reproduced-state", type=Path, required=True)
    parser.add_argument("--terminal-reproduction-segment", type=Path, required=True)
    parser.add_argument("--canonical-result", type=Path, required=True)
    parser.add_argument("--target-theorem", type=Path, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--arming-head-sha", required=True)
    parser.add_argument("--arming-parent-sha", required=True)
    parser.add_argument("--source-canonical-run-id", type=int, required=True)
    parser.add_argument("--source-canonical-artifact-id", type=int, required=True)
    parser.add_argument("--source-canonical-artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = package_independent_reproduction(
            reproduced_state_payload=_read_object(args.reproduced_state, "reproduced search state"),
            terminal_reproduction_segment=_read_object(args.terminal_reproduction_segment, "terminal reproduction segment"),
            canonical_result=_read_object(args.canonical_result, "canonical result"),
            target_theorem=_read_object(args.target_theorem, "target theorem"),
            marker=_read_object(args.marker, "arming marker"),
            arming_head_sha=args.arming_head_sha,
            arming_parent_sha=args.arming_parent_sha,
            source_canonical_run_id=args.source_canonical_run_id,
            source_canonical_artifact_id=args.source_canonical_artifact_id,
            source_canonical_artifact_digest=args.source_canonical_artifact_digest,
        )
    except ReproductionPackageError as error:
        raise SystemExit(str(error)) from error
    _write_json_atomic(args.output, result)
    print(json.dumps({
        "status": result["status"],
        "state_byte_identical": result["state_byte_identical"],
        "qualification_gate_open": result["qualification_gate_open"],
        "source_canonical_result_digest": result["source_canonical_result_digest"],
        "reproduced_state_digest": result["reproduced_state_digest"],
        "result_digest": result["result_digest"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
