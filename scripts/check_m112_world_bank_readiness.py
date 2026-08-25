"""Report the M112 world-bank phase, and refuse a reveal that is not earned.

Three modes, and the third is the one CI needs:

    --report              print the phase and every blocker
    --require-ready       exit non-zero unless the whole ordered chain holds
    --assert-not-revealed exit non-zero if a result exists without an authorized reveal

The last one is the decisive step. The generic contract records why: M086-A produced a positive
verdict against a threshold that could not fail, partly because a scientific checker existed without
being decisive in CI. A green CI has to guarantee the properties the registers claim it guarantees.

This script never opens, decrypts or lists bank content, and there is no code path here that could.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse  # noqa: E402
import json  # noqa: E402

from metamorphosis import m112_world_bank as world_bank  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--assert-not-revealed", action="store_true")
    parser.add_argument("--root", default=str(_ROOT))
    arguments = parser.parse_args()

    report = world_bank.assess_world_bank_readiness(Path(arguments.root))
    print(json.dumps(report, sort_keys=True, indent=1))

    if arguments.require_ready and not report["ready_for_reveal"]:
        print("M112 reveal is not authorized", file=sys.stderr)
        return 1
    if arguments.assert_not_revealed and report["revealed"]:
        # A result may exist only if the chain that authorizes it also exists and holds.
        if not report["ready_for_reveal"]:
            print(
                "M112 carries a result without an authorized reveal", file=sys.stderr
            )
            return 1
    if not report["phase_is_declared"] or not report["evidence_tier_is_declared"]:
        print("M112 phase or evidence tier is outside the declared contract", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
