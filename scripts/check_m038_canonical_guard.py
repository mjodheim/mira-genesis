"""Guard the one M038 canonical arming commit.

The workflow may be triggered again because the marker remains in the pull-request
diff. Only a head commit that changes exactly the marker and has the exact arming
message is allowed to evaluate. Later commits report `armed=false` and do nothing.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

ARM_PATH = Path("experiments/M038/CANONICAL_ARMED.json")
ARM_MESSAGE = "m038(canonical): arm first immutable run"
ARM_SCHEMA = "m038-canonical-arm/1"
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")


class GuardError(ValueError):
    pass


def _write_output(path: Path | None, *, armed: bool, reason: str) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"armed={'true' if armed else 'false'}\n")
        handle.write(f"reason={reason}\n")


def inspect_arm(
    *,
    head_sha: str,
    parent_sha: str,
    commit_message: str,
    changed_files: tuple[str, ...],
    marker_path: Path = ARM_PATH,
) -> dict[str, object] | None:
    """Return the validated marker, or None when this is not the arming commit.

    A commit that changes files other than the marker is an ordinary later commit and
    must not re-open the block. A commit that changes exactly the marker is claiming to
    arm the run and therefore fails loudly if any field is invalid.
    """

    canonical_files = tuple(sorted(path for path in changed_files if path))
    if canonical_files != (str(marker_path).replace("\\", "/"),):
        return None

    if commit_message.strip() != ARM_MESSAGE:
        raise GuardError("the marker-only commit does not carry the exact arming message")
    if not _SHA.match(head_sha):
        raise GuardError("head SHA must be full lowercase 40-hex")
    if not _SHA.match(parent_sha):
        raise GuardError("parent SHA must be full lowercase 40-hex")
    if not marker_path.is_file():
        raise GuardError("the canonical marker is absent")

    data = json.loads(marker_path.read_text(encoding="utf-8"))
    expected_keys = {
        "schema",
        "frozen_parent_sha",
        "protocol_sha256",
        "first_run_only",
        "reruns_are_reproductions_only",
    }
    if set(data) != expected_keys:
        raise GuardError("the canonical marker fields do not match the closed schema")
    if data["schema"] != ARM_SCHEMA:
        raise GuardError("unknown canonical marker schema")
    if data["frozen_parent_sha"] != parent_sha:
        raise GuardError("the marker is not attached directly to its frozen parent")
    if not _DIGEST.match(str(data["protocol_sha256"])):
        raise GuardError("protocol SHA-256 is not canonical lowercase hexadecimal")
    if data["first_run_only"] is not True:
        raise GuardError("first_run_only must be true")
    if data["reruns_are_reproductions_only"] is not True:
        raise GuardError("reruns_are_reproductions_only must be true")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        marker = inspect_arm(
            head_sha=args.head_sha,
            parent_sha=args.parent_sha,
            commit_message=args.commit_message,
            changed_files=tuple(args.changed_file),
        )
    except (GuardError, json.JSONDecodeError) as error:
        _write_output(args.github_output, armed=False, reason="invalid-arm")
        print(f"M038 canonical guard failure: {error}")
        return 1

    if marker is None:
        _write_output(args.github_output, armed=False, reason="not-arm-commit")
        print("M038 canonical block remains closed: the head is not the marker-only arming commit")
        return 0

    _write_output(args.github_output, armed=True, reason="valid-first-arm")
    print(json.dumps(marker, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
