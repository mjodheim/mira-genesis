"""Advance the frozen M092 criterion search without qualification or candidate execution.

The command has no reset, skip, repair or reroll flag. A new search starts only when no input state
is supplied. Plain resumes retain the strongest M092-D rule: the complete saved prefix is replayed
from genesis and must reproduce the supplied state byte-for-byte before any new proposal is consumed.

Long-running canonical GitHub transport may instead provide the immutable predecessor segment
receipt plus the exact arming head/parent and predecessor index. In that narrow mode the workflow has
already authenticated the immutable Actions artifact id and SHA-256; the receipt is then validated
against the exact criterion checkpoint before continuation. The scientific trajectory is unchanged.

Every checkpoint is written atomically. Chunking is transport-only: each chunk calls the frozen
``advance_search`` on the current immutable state, so changing checkpoint frequency cannot change
proposal order, certificate order, selection semantics or frozen budgets.
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
from metamorphosis.m092_resume_validation import (
    ResumeValidationError,
    TERMINAL_STATUSES,
    verified_resume_state,
    verified_segment_resume_state,
)


def _install_target_neutral_path_cache() -> None:
    """Memoise deterministic symbolic paths without changing the scientific search surface.

    The policy enumerator prepares the same immutable symbolic paths once to enumerate policy
    vectors and again while constructing every certificate.  The runner may safely reuse those
    target-neutral paths within one process because programs, ghost names, symbolic states and paths
    are immutable values.  A fresh list is returned on every lookup so callers retain the historical
    container semantics.  The bounded cache affects only repeated computation, never ordering,
    budgets, theorem data, verifier feedback or qualification material.
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


def _read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def advance_with_checkpoints(
    state: CriterionSearchState,
    requirement: Mapping[str, object],
    *,
    program_limit: int,
    checkpoint_programs: int,
    output: Path,
) -> tuple[CriterionSearchState, int]:
    """Advance the exact frozen trajectory while persisting only completed program boundaries.

    The initial state is written before any new program is consumed. If execution is interrupted
    during a chunk, the output therefore remains the last fully validated checkpoint.
    """

    if not isinstance(program_limit, int) or isinstance(program_limit, bool) or program_limit < 0:
        raise ValueError("program_limit must be a non-negative integer")
    if (
        not isinstance(checkpoint_programs, int)
        or isinstance(checkpoint_programs, bool)
        or checkpoint_programs <= 0
    ):
        raise ValueError("checkpoint_programs must be a positive integer")

    _write_json_atomic(output, state.to_dict())
    remaining = program_limit
    checkpoints_written = 1
    current = state

    while remaining > 0 and current.status == "searching":
        request = min(remaining, checkpoint_programs)
        before = current.generated_programs
        current = advance_search(current, requirement, program_limit=request)
        consumed = current.generated_programs - before
        if consumed < 0 or consumed > request:
            raise RuntimeError("criterion chunk changed the generated-program count inconsistently")
        if consumed == 0 and current.status == "searching":
            raise RuntimeError("criterion chunk made no progress while search remained active")
        remaining -= consumed
        _write_json_atomic(output, current.to_dict())
        checkpoints_written += 1

    return current, checkpoints_written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirement", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--canonical-segment-record", type=Path)
    parser.add_argument("--arming-head-sha")
    parser.add_argument("--arming-parent-sha")
    parser.add_argument("--previous-segment-index", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--program-limit", type=int, required=True)
    parser.add_argument(
        "--checkpoint-programs",
        type=int,
        default=None,
        help=(
            "persist a validated state after at most this many new programs; "
            "omitting it preserves the historical one-chunk transport"
        ),
    )
    arguments = parser.parse_args()
    _install_target_neutral_path_cache()

    requirement = _read_json(arguments.requirement)
    if not isinstance(requirement, dict):
        raise SystemExit("M092 criterion requirement must be a JSON object")
    if arguments.program_limit < 0:
        raise SystemExit("--program-limit must be non-negative")
    checkpoint_programs = (
        max(1, arguments.program_limit)
        if arguments.checkpoint_programs is None
        else arguments.checkpoint_programs
    )
    if checkpoint_programs <= 0:
        raise SystemExit("--checkpoint-programs must be positive")

    segment_fields = (
        arguments.canonical_segment_record,
        arguments.arming_head_sha,
        arguments.arming_parent_sha,
        arguments.previous_segment_index,
    )
    segment_mode = any(value is not None for value in segment_fields)
    if segment_mode and not all(value is not None for value in segment_fields):
        raise SystemExit("canonical segment resume requires record, arming SHAs and predecessor index")
    if segment_mode and arguments.state is None:
        raise SystemExit("canonical segment resume requires --state")

    resume_mode = "genesis"
    if arguments.state is None:
        state = CriterionSearchState.fresh(requirement)
    else:
        if not arguments.state.is_file():
            raise SystemExit("resume state path does not exist")
        raw_state = _read_json(arguments.state)
        if not isinstance(raw_state, dict):
            raise SystemExit("resume state must be a JSON object")
        try:
            if segment_mode:
                assert arguments.canonical_segment_record is not None
                assert arguments.arming_head_sha is not None
                assert arguments.arming_parent_sha is not None
                assert arguments.previous_segment_index is not None
                if not arguments.canonical_segment_record.is_file():
                    raise SystemExit("canonical predecessor segment record path does not exist")
                raw_segment = _read_json(arguments.canonical_segment_record)
                if not isinstance(raw_segment, dict):
                    raise SystemExit("canonical predecessor segment record must be a JSON object")
                state = verified_segment_resume_state(
                    raw_state,
                    raw_segment,
                    requirement,
                    arming_head_sha=arguments.arming_head_sha,
                    arming_parent_sha=arguments.arming_parent_sha,
                    expected_segment_index=arguments.previous_segment_index,
                )
                resume_mode = "immutable_segment_chain"
            else:
                state = verified_resume_state(raw_state, requirement)
                resume_mode = "full_replay_from_genesis"
        except ResumeValidationError as error:
            raise SystemExit(str(error)) from error

    advanced, checkpoints_written = advance_with_checkpoints(
        state,
        requirement,
        program_limit=arguments.program_limit,
        checkpoint_programs=checkpoint_programs,
        output=arguments.output,
    )
    payload = advanced.to_dict()
    print(json.dumps({
        "status": payload["status"],
        "generated_programs": payload["generated_programs"],
        "certificate_policy_attempts": payload["certificate_policy_attempts"],
        "certificates_constructed": payload["certificates_constructed"],
        "surviving_candidates": payload["surviving_candidates"],
        "state_digest": payload["state_digest"],
        "candidate_executed_for_selection": payload["candidate_executed_for_selection"],
        "qualification_loaded": payload["qualification_loaded"],
        "resume_mode": resume_mode,
        "checkpoint_programs": checkpoint_programs,
        "checkpoints_written": checkpoints_written,
        "terminal": payload["status"] in TERMINAL_STATUSES,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
