#!/usr/bin/env python3
"""Record the owner's single authorization to open the sealed H65 bank.

This computes no measure, reads no carrier and scores nothing. It writes one record saying that the
tested system was frozen and committed before the seal was broken, that the pre-seal adequacy gate
cleared this bank, and that the reveal that follows is the only one.

Two refusals, and the second is M119's lesson:

* the freeze must be committed at HEAD and still match the working tree, so an authorization cannot
  be the moment at which the tested system is quietly different from the one that was frozen;
* the committed pre-seal adequacy record must say the bank is adequate. M119's reveal was spent on
  a bank that could not be tested. A reveal is single-use, and an authorization that cannot see
  whether the bank is testable is an authorization to spend it blind.
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

from metamorphosis import m120_adequacy as adequacy  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

AUTHORIZATION_PATH = ROOT / chronology.REVEAL_AUTHORIZATION
COMMITMENT_PATH = ROOT / chronology.PUBLIC_BANK_COMMITMENT
ADEQUACY_PATH = ROOT / chronology.ADEQUACY
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

    gate = json.loads(ADEQUACY_PATH.read_text(encoding="utf-8"))
    adequacy.validate_record(gate)
    if sha256_hex(canonical_bytes(gate)) != commitment.get("preseal_adequacy_sha256"):
        raise AuthorizationError(
            "the committed adequacy record is not the one the seal published")
    if gate.get("adequate") is not True:
        raise AuthorizationError(
            "the pre-seal adequacy gate did not clear this bank (%s); the one reveal is not spent "
            "on a bank the frozen plan cannot be run on, and the bank is not filtered, repaired, "
            "resampled or regenerated" % "; ".join(gate.get("shortfalls") or ["no reason given"]))

    record = {
        "schema": "m120-reveal-authorization-v1", "milestone": "M120", "hypothesis": "H65",
        "authorized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authorized_by": authorized_by,
        "ciphertext_sha256": ciphertext_sha256,
        "commitment_sha256": commitment["commitment_sha256"],
        "freeze_commitment_sha256": permission["freeze_commitment_sha256"],
        "preseal_adequacy_sha256": commitment["preseal_adequacy_sha256"],
        "preseal_adequacy_cleared_this_bank": True,
        "qualifying_carriers_at_the_gate": gate["qualifying_carriers"],
        "distinct_qualifying_structures_at_the_gate": gate["distinct_qualifying_structures"],
        "paired_demands_at_the_gate": gate["paired_demands_available"],
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
    except (AuthorizationError, adequacy.AdequacyError, chronology.ChronologyError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps({k: v for k, v in record.items() if k != "schema"},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
