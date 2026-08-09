"""Verify the portable executable identities committed by M065."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from metamorphosis.m065_qualified_completion import (
    M065_PROTOCOL,
    M065_PROTOCOL_SHA256,
    M065_TASK_BANK,
)


FROZEN_PROTOCOL_PATH = Path("experiments/M065/FROZEN_PROTOCOL.json")


class FrozenProtocolError(ValueError):
    """Raised when the committed M065 protocol differs from repository bytes."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate_frozen_protocol(path: Path = FROZEN_PROTOCOL_PATH) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrozenProtocolError("M065 frozen protocol is absent or malformed") from exc
    if not isinstance(data, Mapping) or data.get("schema") != "m065-frozen-protocol/1":
        raise FrozenProtocolError("M065 frozen protocol schema is invalid")
    if data.get("protocol") != M065_PROTOCOL:
        raise FrozenProtocolError("M065 frozen protocol mapping differs from executable protocol")
    if data.get("protocol_sha256") != M065_PROTOCOL_SHA256:
        raise FrozenProtocolError("M065 protocol digest differs from executable protocol")
    if data.get("task_bank_commitment") != M065_PROTOCOL["task_bank_commitment"]:
        raise FrozenProtocolError("M065 task-bank commitment differs from executable bank")
    if data.get("task_bank_entry_count") != len(M065_TASK_BANK):
        raise FrozenProtocolError("M065 task-bank size differs from executable bank")
    hashes = data.get("file_sha256")
    if not isinstance(hashes, Mapping) or not hashes:
        raise FrozenProtocolError("M065 frozen protocol carries no file commitments")
    for raw_path, expected in hashes.items():
        source = Path(str(raw_path))
        if not source.is_file():
            raise FrozenProtocolError(f"M065 committed source is absent: {source}")
        observed = _sha256(source)
        if observed != expected:
            raise FrozenProtocolError(
                f"M065 committed source drifted: {source} expected {expected} observed {observed}"
            )
    return dict(data)


def main() -> int:
    try:
        data = validate_frozen_protocol()
    except FrozenProtocolError as error:
        print(f"M065 frozen protocol failure: {error}")
        return 1
    print(
        json.dumps(
            {
                "schema": data["schema"],
                "protocol_sha256": data["protocol_sha256"],
                "task_bank_commitment": data["task_bank_commitment"],
                "committed_files": len(data["file_sha256"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
