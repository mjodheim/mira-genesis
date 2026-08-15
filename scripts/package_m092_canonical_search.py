"""Package the terminal M092 canonical criterion-search state with immutable run metadata.

This script does not execute, repair, qualify or register a candidate.  It validates the exact
terminal search state emitted by the frozen criterion runner and binds it to the terminal immutable
transport-segment receipt plus the arming commit, parent and marker.

A terminal canonical search result is still not qualification evidence.  The package explicitly
requires a separate deterministic reproduction from genesis before any later M092 qualification may
begin; multi-run transport provenance replaces repeated full-prefix replay during execution, not the
independent reproduction obligation.
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
from metamorphosis.m092_resume_validation import SEGMENT_SCHEMA
from metamorphosis.m092_runtime import canonical_bytes

RESULT_SCHEMA = "m092-canonical-criterion-search-result/2"
ARM_SCHEMA = "m092-canonical-search-arm/1"
PROGRAM_LIMIT = 2_000_000
TERMINAL_STATUSES = {
    "candidate_selected",
    "program_budget_exhausted",
    "certificate_budget_exhausted",
}
_SHA40 = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")


class PackageError(ValueError):
    """A canonical search output cannot be preserved as the immutable terminal result."""


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackageError(f"{label} is not readable canonical JSON") from error
    if not isinstance(value, dict):
        raise PackageError(f"{label} must be a JSON object")
    return value


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
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


def _validate_terminal_segment(
    terminal_segment: Mapping[str, object],
    *,
    state: CriterionSearchState,
    head_sha: str,
    parent_sha: str,
) -> dict[str, object]:
    if terminal_segment.get("schema") != SEGMENT_SCHEMA:
        raise PackageError("terminal canonical segment schema differs")
    segment_index = terminal_segment.get("segment_index")
    if not isinstance(segment_index, int) or isinstance(segment_index, bool) or segment_index < 0:
        raise PackageError("terminal canonical segment index is malformed")
    if terminal_segment.get("arming_head_sha") != head_sha:
        raise PackageError("terminal canonical segment arming head differs")
    if terminal_segment.get("arming_parent_sha") != parent_sha:
        raise PackageError("terminal canonical segment arming parent differs")

    payload = dict(terminal_segment)
    supplied_digest = payload.pop("segment_digest", None)
    if not isinstance(supplied_digest, str) or _SHA64.fullmatch(supplied_digest) is None:
        raise PackageError("terminal canonical segment digest is malformed")
    if supplied_digest != _sha256(payload):
        raise PackageError("terminal canonical segment digest differs")
    serialized_state = state.to_dict()
    if terminal_segment.get("output_state_digest") != serialized_state.get("state_digest"):
        raise PackageError("terminal canonical segment does not bind the terminal search state")
    if terminal_segment.get("generated_programs_end") != state.generated_programs:
        raise PackageError("terminal canonical segment program count differs")
    if terminal_segment.get("certificate_policy_attempts_end") != state.certificate_policy_attempts:
        raise PackageError("terminal canonical segment certificate count differs")
    if terminal_segment.get("checkpoint_terminal") is not True:
        raise PackageError("terminal canonical segment is not marked terminal")
    if terminal_segment.get("candidate_executed_for_selection") is not False:
        raise PackageError("terminal canonical segment claims candidate execution")
    if terminal_segment.get("qualification_loaded") is not False:
        raise PackageError("terminal canonical segment claims qualification access")
    return dict(terminal_segment)


def package_result(
    *,
    state_payload: Mapping[str, object],
    terminal_segment: Mapping[str, object],
    marker: Mapping[str, object],
    target_theorem: Mapping[str, object],
    head_sha: str,
    parent_sha: str,
) -> dict[str, object]:
    if _SHA40.fullmatch(head_sha) is None or _SHA40.fullmatch(parent_sha) is None:
        raise PackageError("canonical head and parent SHAs must be full lowercase 40-hex")
    if marker.get("schema") != ARM_SCHEMA:
        raise PackageError("canonical marker schema differs")
    if marker.get("frozen_parent_sha") != parent_sha:
        raise PackageError("canonical marker parent differs from the executed parent")
    if marker.get("program_limit") != PROGRAM_LIMIT or isinstance(marker.get("program_limit"), bool):
        raise PackageError("canonical marker program limit differs from the frozen full search budget")
    for field in ("first_run_only", "reruns_are_reproductions_only", "qualification_forbidden"):
        if marker.get(field) is not True:
            raise PackageError(f"canonical marker {field} must be true")

    try:
        state = CriterionSearchState.from_dict(state_payload)
    except ValueError as error:
        raise PackageError("canonical search state failed semantic validation") from error
    if state.status not in TERMINAL_STATUSES:
        raise PackageError(f"canonical search did not terminate: {state.status}")
    if dict(state.implementation_bindings) != implementation_digests():
        raise PackageError("canonical search state was produced by different selection code")
    if state.theorem_digest != _sha256(target_theorem):
        raise PackageError("canonical search state is bound to a different target theorem")

    serialized = state.to_dict()
    if serialized.get("qualification_loaded") is not False:
        raise PackageError("canonical selection state claims qualification access")
    if serialized.get("candidate_executed_for_selection") is not False:
        raise PackageError("canonical selection state claims candidate execution")
    if serialized.get("verifier_feedback_used_for_repair") is not False:
        raise PackageError("canonical selection state claims verifier-guided repair")

    selected = serialized.get("selected")
    if (state.status == "candidate_selected") != isinstance(selected, Mapping):
        raise PackageError("canonical terminal selection status and payload differ")

    bound_segment = _validate_terminal_segment(
        terminal_segment,
        state=state,
        head_sha=head_sha,
        parent_sha=parent_sha,
    )
    segment_index = int(bound_segment["segment_index"])

    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "status": "first-canonical-criterion-search-result",
        "arming_head_sha": head_sha,
        "frozen_parent_sha": parent_sha,
        "canonical_search_attempt": 1,
        "canonical_transport_mode": "immutable-artifact-segment-chain",
        "transport_segments": segment_index + 1,
        "terminal_segment_index": segment_index,
        "terminal_segment_digest": bound_segment["segment_digest"],
        "terminal_segment": bound_segment,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "qualification_forbidden": True,
        "independent_reproduction_required": True,
        "qualification_may_begin_before_reproduction": False,
        "target_search_executed": True,
        "qualification_loaded": False,
        "candidate_executed_for_selection": False,
        "program_limit_requested": PROGRAM_LIMIT,
        "terminal_search_status": state.status,
        "candidate_selected": state.status == "candidate_selected",
        "generated_programs": state.generated_programs,
        "certificate_policy_attempts": state.certificate_policy_attempts,
        "certificates_constructed": state.certificates_constructed,
        "surviving_candidates": state.surviving_candidates,
        "marker_digest": _sha256(marker),
        "marker": dict(marker),
        "search_state": serialized,
    }
    result["result_digest"] = _sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--terminal-segment", type=Path, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--target-theorem", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        packaged = package_result(
            state_payload=_read_object(args.state, "canonical search state"),
            terminal_segment=_read_object(args.terminal_segment, "terminal canonical segment"),
            marker=_read_object(args.marker, "canonical arming marker"),
            target_theorem=_read_object(args.target_theorem, "target theorem"),
            head_sha=args.head_sha,
            parent_sha=args.parent_sha,
        )
    except PackageError as error:
        raise SystemExit(str(error)) from error
    _write_json_atomic(args.output, packaged)
    print(json.dumps({
        "status": packaged["status"],
        "terminal_search_status": packaged["terminal_search_status"],
        "candidate_selected": packaged["candidate_selected"],
        "transport_segments": packaged["transport_segments"],
        "terminal_segment_digest": packaged["terminal_segment_digest"],
        "independent_reproduction_required": packaged["independent_reproduction_required"],
        "result_digest": packaged["result_digest"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
