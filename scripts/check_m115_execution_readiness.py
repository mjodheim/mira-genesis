"""Report M115's post-seal phase without opening, decrypting or listing bank content."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_execution as execution  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-phase", choices=execution.PHASES)
    arguments = parser.parse_args()
    report = execution.readiness(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    if arguments.require_ready and not report["ready_for_reveal"]:
        return 2
    if arguments.require_phase and report["phase"] != arguments.require_phase:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
