"""Guard the unique marker-only M064 whole-WebAssembly canonical commit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from metamorphosis.m064_real_substrate_completion import M064_PROTOCOL
from check_m064_frozen_protocol import FrozenProtocolError, validate_frozen_protocol


ARM_PATH = Path("experiments/M064/CANONICAL_ARMED.json")
FROZEN_PROTOCOL_PATH = Path("experiments/M064/FROZEN_PROTOCOL.json")
ARM_MESSAGE = "m064(canonical): arm first immutable whole-wasm run"
ARM_SCHEMA = "m064-canonical-arm/1"
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")


class GuardError(ValueError):
    """Raised when a marker-shaped commit violates the frozen contract."""


def _posix(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_arm(
    *,
    head_sha: str,
    parent_sha: str,
    commit_message: str,
    changed_files: tuple[str, ...],
    marker_path: Path = ARM_PATH,
    frozen_protocol_path: Path = FROZEN_PROTOCOL_PATH,
) -> dict[str, object] | None:
    files = tuple(sorted(_posix(path) for path in changed_files if path))
    if files != (_posix(marker_path),):
        return None
    if commit_message.strip() != ARM_MESSAGE:
        raise GuardError("marker-only commit does not carry the exact M064 arming message")
    if not _SHA.match(head_sha) or not _SHA.match(parent_sha):
        raise GuardError("head and parent must be full lower-case forty-hex SHAs")
    if not marker_path.is_file() or not frozen_protocol_path.is_file():
        raise GuardError("M064 marker or frozen protocol is absent")
    data = json.loads(marker_path.read_text(encoding="utf-8"))
    expected = {
        "schema",
        "frozen_parent_sha",
        "protocol_sha256",
        "frozen_protocol_file_sha256",
        "task_bank_commitment",
        "first_run_only",
        "reruns_are_reproductions_only",
        "independent_reproduction_required",
    }
    if set(data) != expected or data.get("schema") != ARM_SCHEMA:
        raise GuardError("M064 marker fields do not match the closed schema")
    if data["frozen_parent_sha"] != parent_sha:
        raise GuardError("M064 marker does not name its actual immutable parent")
    if data["protocol_sha256"] != M064_PROTOCOL.digest():
        raise GuardError("M064 marker protocol digest differs from executable protocol")
    if data["task_bank_commitment"] != M064_PROTOCOL.task_bank_commitment:
        raise GuardError("M064 marker task-bank commitment differs from executable protocol")
    if not _DIGEST.match(str(data["frozen_protocol_file_sha256"])):
        raise GuardError("M064 frozen-protocol digest is malformed")
    if data["frozen_protocol_file_sha256"] != _file_sha256(frozen_protocol_path):
        raise GuardError("M064 marker does not bind the frozen protocol file bytes")
    try:
        validate_frozen_protocol(frozen_protocol_path)
    except FrozenProtocolError as exc:
        raise GuardError(f"M064 frozen protocol contents failed verification: {exc}") from exc
    if (
        data["first_run_only"] is not True
        or data["reruns_are_reproductions_only"] is not True
        or data["independent_reproduction_required"] is not True
    ):
        raise GuardError("M064 first-run and reproduction semantics are not locked")
    return data


def _write_output(path: Path | None, *, armed: bool, reason: str) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"armed={'true' if armed else 'false'}\n")
        handle.write(f"reason={reason}\n")


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
    except (GuardError, json.JSONDecodeError, OSError) as error:
        _write_output(args.github_output, armed=False, reason="invalid-arm")
        print(f"M064 canonical guard failure: {error}")
        return 1
    if marker is None:
        _write_output(args.github_output, armed=False, reason="not-arm-commit")
        print("M064 canonical block remains closed")
        return 0
    _write_output(args.github_output, armed=True, reason="valid-first-arm")
    print(json.dumps(marker, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
