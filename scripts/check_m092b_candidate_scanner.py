"""Run the frozen M092-B anti-cheating positive controls without search or qualification."""
from __future__ import annotations

import json

from metamorphosis.m092_candidate_validation import run_anti_cheating_selftest


def main() -> int:
    report = run_anti_cheating_selftest()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_five_rejected"] and report["clean_state_restored"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
