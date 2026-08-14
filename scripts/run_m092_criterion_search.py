"""Advance the frozen M092 criterion search without qualification or candidate execution.

The command has no reset, skip, repair or reroll flag.  A new search starts only when no input state
is supplied; a resumed search must validate its theorem, source bindings, cursor and state digest.
Every invocation writes one complete state atomically, making chunked execution the same scientific
trajectory rather than a sequence of fresh searches.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from metamorphosis.m092_criterion_search import CriterionSearchState, advance_search


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirement", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--program-limit", type=int, required=True)
    arguments = parser.parse_args()

    requirement = _read_json(arguments.requirement)
    if not isinstance(requirement, dict):
        raise SystemExit("M092 criterion requirement must be a JSON object")
    if arguments.program_limit < 0:
        raise SystemExit("--program-limit must be non-negative")

    if arguments.state is None:
        state = CriterionSearchState.fresh(requirement)
    else:
        if not arguments.state.is_file():
            raise SystemExit("resume state path does not exist")
        raw_state = _read_json(arguments.state)
        if not isinstance(raw_state, dict):
            raise SystemExit("resume state must be a JSON object")
        state = CriterionSearchState.from_dict(raw_state)

    advanced = advance_search(
        state,
        requirement,
        program_limit=arguments.program_limit,
    )
    payload = advanced.to_dict()
    _write_json_atomic(arguments.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "generated_programs": payload["generated_programs"],
        "certificate_policy_attempts": payload["certificate_policy_attempts"],
        "certificates_constructed": payload["certificates_constructed"],
        "surviving_candidates": payload["surviving_candidates"],
        "state_digest": payload["state_digest"],
        "candidate_executed_for_selection": payload["candidate_executed_for_selection"],
        "qualification_loaded": payload["qualification_loaded"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
