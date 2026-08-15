"""Run an independent M092 criterion reproduction without reading the canonical result content.

The canonical result is deliberately absent from this command line.  Segment zero starts from the
same frozen criterion genesis.  Continuations accept only an independently-namespaced immutable
reproduction receipt and checkpoint.  The canonical artifact identity is carried solely to prevent
mixing reproduction chains; its content is not available to the search trajectory.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping

import metamorphosis.m092_certificate_policy_search as policy_search
from metamorphosis.m092_criterion_search import CriterionSearchState, advance_search
from metamorphosis.m092_independent_reproduction import (
    ReproductionError,
    TERMINAL_STATUSES,
    verified_reproduction_resume_state,
)


def _install_target_neutral_path_cache() -> None:
    """Memoise deterministic symbolic paths without changing the scientific search surface.

    The reproduction runner uses the exact same bounded target-neutral cache as the canonical
    runner.  Only repeated symbolic-path preparation is removed; every caller receives a fresh list
    containing the same immutable paths, so proposal order, policy order, records, budgets and
    verifier inputs are unchanged.  The cache cannot read result content or qualification material.
    """

    original = policy_search._paths_for_policy
    if getattr(original, "_m092_target_neutral_cache", False):
        return

    @lru_cache(maxsize=8)
    def cached(program: tuple[tuple[object, ...], ...], ghosts: tuple[str, ...]):
        header, paths = original(program, ghosts)
        return header, tuple(paths)

    def wrapped(program, ghosts):
        header, paths = cached(program, tuple(ghosts))
        return header, list(paths)

    setattr(wrapped, "_m092_target_neutral_cache", True)
    policy_search._paths_for_policy = wrapped


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"{label} is not readable JSON") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return value


def _write_json_atomic(path: Path, value: object) -> None:
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


def advance_reproduction_with_checkpoints(
    state: CriterionSearchState,
    requirement: Mapping[str, object],
    *,
    program_limit: int,
    checkpoint_programs: int,
    output: Path,
) -> tuple[CriterionSearchState, int]:
    """Advance the frozen engine while preserving only complete program boundaries."""

    if not isinstance(program_limit, int) or isinstance(program_limit, bool) or program_limit < 0:
        raise ValueError("program_limit must be a non-negative integer")
    if (
        not isinstance(checkpoint_programs, int)
        or isinstance(checkpoint_programs, bool)
        or checkpoint_programs <= 0
    ):
        raise ValueError("checkpoint_programs must be a positive integer")

    _write_json_atomic(output, state.to_dict())
    current = state
    remaining = program_limit
    writes = 1
    while remaining > 0 and current.status == "searching":
        request = min(remaining, checkpoint_programs)
        before = current.generated_programs
        current = advance_search(current, requirement, program_limit=request)
        consumed = current.generated_programs - before
        if consumed < 0 or consumed > request:
            raise RuntimeError("reproduction chunk changed generated-program count inconsistently")
        if consumed == 0 and current.status == "searching":
            raise RuntimeError("reproduction chunk made no progress while search remained active")
        remaining -= consumed
        _write_json_atomic(output, current.to_dict())
        writes += 1
    return current, writes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirement", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--reproduction-segment-record", type=Path)
    parser.add_argument("--arming-head-sha")
    parser.add_argument("--arming-parent-sha")
    parser.add_argument("--source-canonical-run-id", type=int)
    parser.add_argument("--source-canonical-artifact-id", type=int)
    parser.add_argument("--source-canonical-artifact-digest")
    parser.add_argument("--previous-segment-index", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--program-limit", type=int, required=True)
    parser.add_argument("--checkpoint-programs", type=int, default=1)
    args = parser.parse_args()
    _install_target_neutral_path_cache()

    requirement = _read_object(args.requirement, "reproduction requirement")
    if args.program_limit < 0 or args.checkpoint_programs <= 0:
        raise SystemExit("reproduction budgets must be non-negative and checkpoints positive")

    continuation_fields = (
        args.reproduction_segment_record,
        args.arming_head_sha,
        args.arming_parent_sha,
        args.source_canonical_run_id,
        args.source_canonical_artifact_id,
        args.source_canonical_artifact_digest,
        args.previous_segment_index,
    )
    continuation = any(value is not None for value in continuation_fields)
    if continuation and not all(value is not None for value in continuation_fields):
        raise SystemExit("reproduction continuation requires complete immutable provenance")
    if continuation and args.state is None:
        raise SystemExit("reproduction continuation requires a predecessor state")

    resume_mode = "genesis"
    if args.state is None:
        if continuation:
            raise SystemExit("reproduction genesis cannot name a predecessor")
        state = CriterionSearchState.fresh(requirement)
    else:
        if not continuation:
            raise SystemExit("plain state resume is forbidden for independent reproduction")
        raw_state = _read_object(args.state, "reproduction predecessor state")
        assert args.reproduction_segment_record is not None
        assert args.arming_head_sha is not None
        assert args.arming_parent_sha is not None
        assert args.source_canonical_run_id is not None
        assert args.source_canonical_artifact_id is not None
        assert args.source_canonical_artifact_digest is not None
        assert args.previous_segment_index is not None
        raw_segment = _read_object(args.reproduction_segment_record, "reproduction predecessor receipt")
        try:
            state = verified_reproduction_resume_state(
                raw_state,
                raw_segment,
                requirement,
                arming_head_sha=args.arming_head_sha,
                arming_parent_sha=args.arming_parent_sha,
                source_canonical_run_id=args.source_canonical_run_id,
                source_canonical_artifact_id=args.source_canonical_artifact_id,
                source_canonical_artifact_digest=args.source_canonical_artifact_digest,
                expected_segment_index=args.previous_segment_index,
            )
        except ReproductionError as error:
            raise SystemExit(str(error)) from error
        resume_mode = "independent_reproduction_segment_chain"

    advanced, writes = advance_reproduction_with_checkpoints(
        state,
        requirement,
        program_limit=args.program_limit,
        checkpoint_programs=args.checkpoint_programs,
        output=args.output,
    )
    payload = advanced.to_dict()
    print(json.dumps({
        "status": payload["status"],
        "generated_programs": payload["generated_programs"],
        "certificate_policy_attempts": payload["certificate_policy_attempts"],
        "state_digest": payload["state_digest"],
        "canonical_result_content_loaded": False,
        "candidate_executed_for_selection": payload["candidate_executed_for_selection"],
        "qualification_loaded": payload["qualification_loaded"],
        "resume_mode": resume_mode,
        "checkpoints_written": writes,
        "terminal": payload["status"] in TERMINAL_STATUSES,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
