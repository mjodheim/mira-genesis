"""Materialize the owner-authorized, single-use M115 reveal gate.

This command never decrypts the bank.  It proves that the public sealed checkpoint precedes the
committed tested-system freeze and writes the authorization record the canonical runner requires.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_carrier_bank as bank  # noqa: E402
from metamorphosis import m115_execution as execution  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes  # noqa: E402


OWNER_AUTHORIZATION = (
    "Anthony Mets's owner instruction in the Codex session on 2026-08-30: continue M115/H60 from "
    "the frozen safe stopping point, reveal only when mechanically authorized, execute P1-P22 "
    "exactly as frozen, preserve every outcome, and perform no post-hoc repair or rescue retry"
)


def main() -> int:
    path = ROOT / execution.REVEAL_AUTHORIZATION_PATH
    if path.exists():
        print("REFUSED: REVEAL_AUTHORIZATION.json already exists; authorization is single-use")
        return 1
    if (ROOT / execution.RESULT_PATH).exists():
        print("REFUSED: a result exists before reveal authorization")
        return 1
    try:
        sealed_commit = execution.commit_that_added(ROOT, bank.BANK_COMMITMENT_PATH)
        system_commit = execution.commit_that_added(ROOT, execution.SYSTEM_PROTOCOL_PATH)
        authorization = execution.build_reveal_authorization(
            root=ROOT,
            bank_commitment_published_at_commit=sealed_commit,
            system_protocol_frozen_at_commit=system_commit,
            authorized_by=OWNER_AUTHORIZATION,
        )
        execution.validate_reveal_authorization(
            authorization,
            root=ROOT,
            require_committed_authorization=False,
        )
        path.write_bytes(canonical_bytes(authorization) + b"\n")
    except execution.ExecutionError as exc:
        path.unlink(missing_ok=True)
        print("REFUSED: %s" % exc)
        return 1
    print(
        json.dumps(
            {
                "schema": "m115-reveal-authorization-operation-v1",
                "milestone": "M115",
                "hypothesis": "H60",
                "authorization_sha256": authorization["authorization_sha256"],
                "bank_commitment_published_at_commit": sealed_commit,
                "system_protocol_frozen_at_commit": system_commit,
                "reveal_attempts_permitted": 1,
            },
            indent=2,
            sort_keys=True,
        )
    )
    print("Commit this exact authorization before invoking the reveal runner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
