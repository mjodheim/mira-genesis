"""Freeze M115's tested system after sealing and before reveal."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_execution as execution  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes  # noqa: E402


def main() -> int:
    path = ROOT / execution.SYSTEM_PROTOCOL_PATH
    if path.exists():
        print("REFUSED: SYSTEM_PROTOCOL.json already exists; the system freeze is single-use")
        return 1
    try:
        protocol = execution.build_system_protocol(ROOT)
        path.write_bytes(canonical_bytes(protocol) + b"\n")
        execution.validate_system_protocol(protocol, root=ROOT)
    except execution.ExecutionError as exc:
        path.unlink(missing_ok=True)
        print("REFUSED: %s" % exc)
        return 1
    print(
        json.dumps(
            {
                "schema": "m115-system-freeze-operation-v1",
                "milestone": "M115",
                "hypothesis": "H60",
                "phase": "system_protocol_frozen",
                "protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
                "bank_commitment_sha256": protocol["bank_commitment_sha256"],
                "bank_content_known_at_freeze": False,
                "tested_system_members": len(protocol["tested_system_digests"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print("Commit this exact protocol before creating reveal authorization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
