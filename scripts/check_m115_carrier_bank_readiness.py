"""Report whether M115/H60 may advance from its current lifecycle phase.

This checker is intentionally useful before freeze: candidate-only apparatus should report blockers
rather than being mistaken for an experiment already in progress. It also makes the M115 carrier
contract a real repository entry point, so orphan detection can enforce that the module remains
wired into operations.

A materialized completion is deliberately represented as `materialized_unsealed` until ciphertext
and its public commitment exist and the plaintext generation response has been removed. Scientific
code must never confuse successful delivery with established custody.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_sealing as sealing  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-phase",
        choices=("draft", "spec_frozen", "materialized_unsealed", "generated_sealed"),
        default=None,
        help="optional exact lifecycle phase required by the caller",
    )
    parser.add_argument(
        "--assert-not-revealed",
        action="store_true",
        help="fail if a reveal authorization already exists",
    )
    args = parser.parse_args()

    try:
        state = sealing.readiness(ROOT)
    except Exception as exc:  # fail closed while preserving a concise public diagnostic
        print("FAIL — M115 readiness could not be established: %s" % type(exc).__name__)
        return 1

    print(json.dumps(state, indent=2, sort_keys=True))
    ok = True
    if args.require_phase is not None and state.get("phase") != args.require_phase:
        print("FAIL — expected phase %s, observed %s" % (args.require_phase, state.get("phase")))
        ok = False
    if args.assert_not_revealed and state.get("revealed") is not False:
        print("FAIL — the M115 bank is already revealed")
        ok = False

    # In candidate/draft phase, missing frozen plan/spec are expected blockers. A plain invocation
    # reports them without failing; callers that need a gate use --require-phase. A caller may also
    # inspect `materialized_unsealed`, but that phase necessarily carries custody blockers and is
    # never an authorization to start scientific work.
    if args.require_phase is not None and state.get("blockers"):
        print("FAIL — M115 readiness blockers remain")
        for blocker in state["blockers"]:
            print("  - %s" % blocker)
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
