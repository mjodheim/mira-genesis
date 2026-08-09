"""Verify every executable identity committed by M064's frozen protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from metamorphosis.m064_real_substrate_completion import M064_PROTOCOL, M064_TASK_BANK


FROZEN_PROTOCOL_PATH = Path("experiments/M064/FROZEN_PROTOCOL.json")


class FrozenProtocolError(ValueError):
    """Raised when the committed protocol differs from repository bytes."""


def _sha256(path: Path) -> str:
    # Git stores these committed text sources with LF endings, while a Windows
    # checkout may materialise CRLF.  Commitments therefore bind the canonical
    # Git text bytes rather than one checkout platform's representation.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate_frozen_protocol(path: Path = FROZEN_PROTOCOL_PATH) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrozenProtocolError("frozen protocol is absent or malformed") from exc
    if not isinstance(data, Mapping) or data.get("schema") != "m064-frozen-protocol/1":
        raise FrozenProtocolError("frozen protocol schema is invalid")
    if data.get("protocol") != M064_PROTOCOL.to_dict():
        raise FrozenProtocolError("frozen protocol mapping differs from executable protocol")
    if data.get("protocol_sha256") != M064_PROTOCOL.digest():
        raise FrozenProtocolError("frozen protocol digest differs from executable protocol")
    if data.get("task_bank_commitment") != M064_PROTOCOL.task_bank_commitment:
        raise FrozenProtocolError("frozen task-bank commitment differs from executable bank")
    if data.get("task_bank_entry_count") != len(M064_TASK_BANK):
        raise FrozenProtocolError("frozen task-bank size differs from executable bank")
    file_hashes = data.get("file_sha256")
    if not isinstance(file_hashes, Mapping) or not file_hashes:
        raise FrozenProtocolError("frozen protocol carries no file commitments")
    for raw_path, expected in file_hashes.items():
        source = Path(str(raw_path))
        if not source.is_file():
            raise FrozenProtocolError(f"committed source is absent: {source}")
        observed = _sha256(source)
        if observed != expected:
            raise FrozenProtocolError(
                f"committed source drifted: {source} expected {expected} observed {observed}"
            )
    return dict(data)


def main() -> int:
    try:
        data = validate_frozen_protocol()
    except FrozenProtocolError as error:
        print(f"M064 frozen protocol failure: {error}")
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
