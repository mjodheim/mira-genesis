"""Verify the portable executable identities committed by M066."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from metamorphosis.m066_canonical_governance import (
    M066_PROTOCOL,
    M066_PROTOCOL_SHA256,
    M066_TASK_BANK,
)


FROZEN_PROTOCOL_PATH = Path("experiments/M066/FROZEN_PROTOCOL.json")


class FrozenProtocolError(ValueError):
    """Raised when the committed M066 protocol differs from repository bytes."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate_frozen_protocol(path: Path = FROZEN_PROTOCOL_PATH) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrozenProtocolError("M066 frozen protocol is absent or malformed") from exc
    if not isinstance(data, Mapping) or data.get("schema") != "m066-frozen-protocol/1":
        raise FrozenProtocolError("M066 frozen protocol schema is invalid")
    if data.get("protocol") != M066_PROTOCOL:
        raise FrozenProtocolError("M066 frozen protocol mapping differs from executable protocol")
    if data.get("protocol_sha256") != M066_PROTOCOL_SHA256:
        raise FrozenProtocolError("M066 protocol digest differs from executable protocol")
    if data.get("task_bank_commitment") != M066_PROTOCOL["task_bank_commitment"]:
        raise FrozenProtocolError("M066 task-bank commitment differs from executable bank")
    if data.get("task_bank_entry_count") != len(M066_TASK_BANK):
        raise FrozenProtocolError("M066 task-bank size differs from executable bank")
    canonical = data.get("canonical_execution")
    if not isinstance(canonical, Mapping):
        raise FrozenProtocolError("M066 canonical execution contract is absent")
    if canonical.get("marker_history_scope") != "first_parent_of_pushed_main_head":
        raise FrozenProtocolError("M066 marker history is not scoped to canonical first parents")
    hashes = data.get("file_sha256")
    if not isinstance(hashes, Mapping) or not hashes:
        raise FrozenProtocolError("M066 frozen protocol carries no file commitments")
    for raw_path, expected in hashes.items():
        source = Path(str(raw_path))
        if not source.is_file():
            raise FrozenProtocolError(f"M066 committed source is absent: {source}")
        observed = _sha256(source)
        if observed != expected:
            raise FrozenProtocolError(
                f"M066 committed source drifted: {source} expected {expected} observed {observed}"
            )
    return dict(data)


def main() -> int:
    try:
        data = validate_frozen_protocol()
    except FrozenProtocolError as error:
        print(f"M066 frozen protocol failure: {error}")
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
