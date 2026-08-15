"""Package the first M092 canonical criterion-search state with immutable run metadata.

This script does not execute, repair, qualify or register a candidate.  It validates the exact
terminal search state emitted by the frozen criterion runner and wraps it with the arming commit,
parent and marker needed to preserve first-run provenance as one immutable CI artifact.
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
from metamorphosis.m092_runtime import canonical_bytes

RESULT_SCHEMA = "m092-canonical-criterion-search-result/1"
ARM_SCHEMA = "m092-canonical-search-arm/1"
PROGRAM_LIMIT = 2_000_000
TERMINAL_STATUSES = {
    "candidate_selected",
    "program_budget_exhausted",
    "certificate_budget_exhausted",
}
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")


class PackageError(ValueError):
    """A canonical search output cannot be preserved as the first immutable result."""


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


def package_result(
    *,
    state_payload: Mapping[str, object],
    marker: Mapping[str, object],
    target_theorem: Mapping[str, object],
    head_sha: str,
    parent_sha: str,
) -> dict[str, object]:
    if _SHA.fullmatch(head_sha) is None or _SHA.fullmatch(parent_sha) is None:
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

    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "status": "first-canonical-criterion-search-result",
        "arming_head_sha": head_sha,
        "frozen_parent_sha": parent_sha,
        "canonical_search_attempt": 1,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "qualification_forbidden": True,
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
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--target-theorem", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        packaged = package_result(
            state_payload=_read_object(args.state, "canonical search state"),
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
        "result_digest": packaged["result_digest"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
