from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m012b_eval_run import run
from m012b_eval_support import ROOT, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "M012b"))
    parser.add_argument("--canonical", action="store_true")
    parser.add_argument("--master-nonce")
    parser.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID", "local-development"))
    parser.add_argument("--github-run-attempt", type=int, default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")))
    parser.add_argument("--event-action", default=os.environ.get("M012B_EVENT_ACTION", "development"))
    args = parser.parse_args()
    result = run(
        git_commit=args.git_commit,
        output_dir=Path(args.output_dir),
        canonical=args.canonical,
        master_nonce_hex=args.master_nonce,
        github_run_id=args.github_run_id,
        github_run_attempt=args.github_run_attempt,
        event_action=args.event_action,
    )
    print(report(result))


if __name__ == "__main__":
    main()
