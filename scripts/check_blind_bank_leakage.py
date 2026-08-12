"""Refuse a working tree that carries sealed-bank plaintext, a key, or an unprotected digest.

This runs over the Git index rather than the filesystem alone. A payload sitting untracked in the
checkout is a mistake; a payload that is tracked is a disclosure, and the two deserve different
verdicts. Both are reported, and only the second is fatal by default.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.blind_bank_sealing import (  # noqa: E402
    missing_gitattributes_entries,
    missing_gitignore_entries,
    scan_tree_for_leaks,
)
from metamorphosis.m075b_blind_readiness import DIGEST_BEARING_PATHS  # noqa: E402


def tracked_paths() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT, capture_output=True, check=True, text=True,
    )
    return [entry for entry in completed.stdout.split("\0") if entry]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-untracked", action="store_true",
        help="also scan files that are present but not tracked by Git",
    )
    arguments = parser.parse_args()

    fatal: list[str] = []
    advisory: list[str] = []

    try:
        tracked = tracked_paths()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("git is unavailable; scanning the working tree instead", file=sys.stderr)
        tracked = None

    fatal += scan_tree_for_leaks(ROOT, tracked_paths=tracked)
    if arguments.include_untracked:
        advisory += [
            problem for problem in scan_tree_for_leaks(ROOT) if problem not in fatal
        ]

    missing_ignores = missing_gitignore_entries(ROOT)
    if missing_ignores:
        fatal.append(
            ".gitignore does not exclude sealed-bank material: " + ", ".join(missing_ignores)
        )
    missing_attributes = missing_gitattributes_entries(ROOT, DIGEST_BEARING_PATHS)
    if missing_attributes:
        fatal.append(
            ".gitattributes does not protect digest-bearing artifacts from end-of-line "
            "conversion: " + ", ".join(missing_attributes)
        )

    for problem in advisory:
        print(f"advisory: {problem}")
    for problem in fatal:
        print(f"blocking: {problem}", file=sys.stderr)
    if fatal:
        return 2
    print("no sealed-bank plaintext, key or unprotected digest-bearing artifact is tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
