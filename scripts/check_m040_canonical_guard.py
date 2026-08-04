from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED_MESSAGE = "m040(canonical): arm first immutable run"
EXPECTED_FILE = "experiments/M040/CANONICAL_ARMED.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()

    armed = (
        len(args.head_sha) == 40
        and len(args.parent_sha) == 40
        and args.head_sha != args.parent_sha
        and args.commit_message.strip() == EXPECTED_MESSAGE
        and args.changed_file == [EXPECTED_FILE]
    )
    args.github_output.write_text(
        f"armed={'true' if armed else 'false'}\n",
        encoding="utf-8",
    )
    if args.commit_message.strip() == EXPECTED_MESSAGE and not armed:
        raise SystemExit("canonical arming message used outside an exact marker-only commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
