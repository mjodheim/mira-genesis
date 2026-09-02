#!/usr/bin/env python3
"""Record the owner's single authorization to open the sealed H64 bank.

This computes no measure, reads no carrier and scores nothing. It writes one record saying that the
tested system was frozen and committed before the seal was broken, and that the reveal that follows
is the only one.

The authorization is refused unless the freeze is committed at HEAD and still matches the working
tree, so an authorization cannot be the moment at which the tested system is quietly different from
the one that was frozen.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m119_chronology as chronology  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

AUTHORIZATION_PATH = ROOT / chronology.REVEAL_AUTHORIZATION
COMMITMENT_PATH = ROOT / chronology.PUBLIC_BANK_COMMITMENT
SEALED_PATH = ROOT / chronology.SEALED_BANK


class AuthorizationError(RuntimeError):
    """The reveal cannot be authorized. Every path fails closed."""


def authorize(*, authorized_by: str) -> dict[str, Any]:
    if AUTHORIZATION_PATH.exists():
        raise AuthorizationError("a reveal authorization already exists; it is issued once")
    if not SEALED_PATH.is_file() or not COMMITMENT_PATH.is_file():
        raise AuthorizationError("there is no sealed bank to authorize a reveal of")
    permission = chronology.assert_frozen_system_unchanged(ROOT, phase="authorization")
    commitment = json.loads(COMMITMENT_PATH.read_text(encoding="utf-8"))
    ciphertext_sha256 = sha256_hex(SEALED_PATH.read_bytes())
    if ciphertext_sha256 != commitment["ciphertext_sha256"]:
        raise AuthorizationError("the sealed bank does not match its published commitment")
    record = {
        "schema": "m119-reveal-authorization-v1", "milestone": "M119", "hypothesis": "H64",
        "authorized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authorized_by": authorized_by,
        "ciphertext_sha256": ciphertext_sha256,
        "commitment_sha256": commitment["commitment_sha256"],
        "freeze_commitment_sha256": permission["freeze_commitment_sha256"],
        "tested_system_was_frozen_and_committed_before_the_seal_was_broken": True,
        "reveals_permitted": 1,
        "this_record_computes_no_measure_and_reads_no_carrier": True,
        "authorization_sha256": "",
    }
    record["authorization_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in record.items() if k != "authorization_sha256"}))
    AUTHORIZATION_PATH.write_bytes(canonical_bytes(record) + b"\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized-by", required=True,
                        help="who authorized this single reveal")
    args = parser.parse_args()
    try:
        record = authorize(authorized_by=args.authorized_by)
    except (AuthorizationError, chronology.ChronologyError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps({k: v for k, v in record.items() if k != "schema"},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
