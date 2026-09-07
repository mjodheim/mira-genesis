#!/usr/bin/env python3
"""Report or enforce whether G9's human baseline exists.

It does not exist, and cannot be made to exist by this repository: a baseline needs people who are
not the project attempting the frozen tasks uncoached. This check refuses until they have, in the
same way M075 and M085 refuse until their independent banks arrive.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.human_baseline import assess_readiness  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-available",
        action="store_true",
        help="fail unless a committed protocol and a matching result both verify",
    )
    arguments = parser.parse_args()
    report = assess_readiness(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    if arguments.require_available and report["human_baseline_available"] is not True:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
