"""Advance the frozen M092 criterion search without qualification or candidate execution.

The command has no reset, skip, repair or reroll flag. A new search starts only when no input state
is supplied. A canonical resume is stronger than a self-digest check: after schema, theorem, source
binding and state-integrity validation, the complete saved prefix is deterministically replayed from
genesis and must reproduce the supplied state byte-for-byte before any new proposal is consumed.

This makes the saved state an integrity-checked cache of an independently reproducible prefix rather
than an authority that can be re-authored and re-hashed to skip proposals. Every checkpoint is
written atomically. Chunking is transport-only: each chunk calls the frozen ``advance_search`` on the
current immutable state, so changing checkpoint frequency cannot change proposal order, certificate
order, selection semantics or frozen budgets.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping

from metamorphosis.m092_criterion_search import CriterionSearchState, advance_search
from metamorphosis.m092_resume_validation import ResumeValidationError, verified_resume_state


TERMINAL_STATUSES = frozenset({
    "candidate_selected",
    "program_budget_exhausted",
    "certificate_budget_exhausted",
})


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
    during a chunk, the output therefore remains the last fully validated checkpoint. Replaying that
    state through the canonical resume validator reconstructs its complete prefix from genesis.
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

    if arguments.state is None:
        state = CriterionSearchState.fresh(requirement)
    else:
        if not arguments.state.is_file():
            raise SystemExit("resume state path does not exist")
        raw_state = _read_json(arguments.state)
        if not isinstance(raw_state, dict):
            raise SystemExit("resume state must be a JSON object")
        try:
            state = verified_resume_state(raw_state, requirement)
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
        "resume_prefix_replayed_from_genesis": arguments.state is not None,
        "checkpoint_programs": checkpoint_programs,
        "checkpoints_written": checkpoints_written,
        "terminal": payload["status"] in TERMINAL_STATUSES,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
