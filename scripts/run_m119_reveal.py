#!/usr/bin/env python3
"""The one authorized reveal: decrypt the sealed H64 bank into carriers.

A reveal is a singular event, not a step that can be repeated until something reads well. It is
refused unless the tested system was frozen and committed beforehand and still matches the working
tree, unless a committed authorization exists, and unless the plaintext that comes out of the
ciphertext is exactly the plaintext the public commitment named.

The envelope from `{"machines": [...]}` to the frozen carrier payload is the same positional,
total, content-independent projection admission used before the seal: carrier *i* is machine *i*,
tagged with the opaque identifier derived from the nonce committed before generation. It adds no
information, drops none, and cannot rescue a malformed machine.

The passphrase is read from `M119_BANK_SEAL_PASSPHRASE` and never written or printed. No carrier
content is printed by this script; it reports counts and digests.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import carrier_host as host  # noqa: E402
from metamorphosis import m116_admission as admission  # noqa: E402
from metamorphosis import m119_chronology as chronology  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

EXPERIMENT = ROOT / chronology.DIRECTORY
SEALED_PATH = ROOT / chronology.SEALED_BANK
COMMITMENT_PATH = ROOT / chronology.PUBLIC_BANK_COMMITMENT
AUTHORIZATION_PATH = ROOT / chronology.REVEAL_AUTHORIZATION
NONCE_PATH = ROOT / chronology.BANK_NONCE_COMMITMENT
CARRIER_BANK_PATH = ROOT / chronology.CARRIER_BANK
REVEAL_RECORD_PATH = ROOT / chronology.REVEAL_RECORD
SECRET_VARIABLE = "M119_BANK_SEAL_PASSPHRASE"


class RevealError(RuntimeError):
    """The reveal cannot be performed honestly. Every path fails closed."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RevealError("cannot read %s: %s" % (path.name, exc))
    if not isinstance(value, dict):
        raise RevealError("%s is not a JSON object" % path.name)
    return value


def reveal() -> dict[str, Any]:
    passphrase = os.environ.get(SECRET_VARIABLE, "")
    if not passphrase:
        raise RevealError("%s is missing" % SECRET_VARIABLE)
    if shutil.which("gpg") is None:
        raise RevealError("gpg is unavailable")
    if CARRIER_BANK_PATH.exists() or REVEAL_RECORD_PATH.exists():
        raise RevealError("the bank has already been revealed; the reveal is single-use")
    for path in (SEALED_PATH, COMMITMENT_PATH, AUTHORIZATION_PATH):
        if not path.is_file():
            raise RevealError("the reveal requires %s" % path.name)

    permission = chronology.assert_frozen_system_unchanged(ROOT, phase="reveal")
    chronology.assert_committed_at_head(chronology.REVEAL_AUTHORIZATION, ROOT)
    authorization = _load(AUTHORIZATION_PATH)
    commitment = _load(COMMITMENT_PATH)
    if authorization.get("commitment_sha256") != commitment.get("commitment_sha256"):
        raise RevealError("the authorization does not bind the published commitment")
    if authorization.get("freeze_commitment_sha256") != permission["freeze_commitment_sha256"]:
        raise RevealError("the authorization was issued against a different tested-system freeze")
    ciphertext = SEALED_PATH.read_bytes()
    if sha256_hex(ciphertext) != commitment["ciphertext_sha256"]:
        raise RevealError("the sealed bank does not match its published commitment")

    completed = subprocess.run(
        ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase-fd", "0",
         "--decrypt", str(SEALED_PATH)],
        input=(passphrase + "\n").encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    passphrase = ""  # dropped as soon as gpg has consumed it
    if completed.returncode != 0:
        raise RevealError("gpg could not open the sealed bank")
    plaintext = completed.stdout
    if sha256_hex(plaintext) != commitment["generation_response_sha256"]:
        raise RevealError(
            "the plaintext recovered from the seal is not the plaintext that was sealed")

    try:
        response = json.loads(plaintext.decode("utf-8"))
        content = response["body"]["choices"][0]["message"]["content"]
        machines = json.loads(content)
    except (UnicodeDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise RevealError(
            "the sealed plaintext does not carry a completion this reveal can open (%s); the "
            "reveal stops rather than reaching into it" % type(exc).__name__)
    if not isinstance(machines, dict):
        raise RevealError("the sealed completion is not a JSON object")

    nonce_record = _load(NONCE_PATH)
    nonce = nonce_record["bank_nonce"]
    if sha256_hex(nonce.encode("ascii")) != nonce_record["bank_nonce_sha256"]:
        raise RevealError("the committed bank nonce does not match its own digest")
    payload = admission.envelope_payload(machines, nonce)
    neutrality = admission.envelope_neutrality(machines, nonce)
    if not neutrality["neutral"]:
        raise RevealError("the carrier envelope was not information-preserving")

    accepted = []
    refused = 0
    for carrier in payload["carriers"]:
        try:
            accepted.append(host.validate_carrier(carrier))
        except Exception:  # noqa: BLE001 -- a refused carrier is counted, never repaired
            refused += 1
    CARRIER_BANK_PATH.write_bytes(canonical_bytes(payload) + b"\n")

    record = {
        "schema": "m119-reveal-record-v1", "milestone": "M119", "hypothesis": "H64",
        "revealed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authorization_sha256": authorization["authorization_sha256"],
        "freeze_commitment_sha256": permission["freeze_commitment_sha256"],
        "ciphertext_sha256": commitment["ciphertext_sha256"],
        "generation_response_sha256": commitment["generation_response_sha256"],
        "bank_nonce_sha256": nonce_record["bank_nonce_sha256"],
        "carrier_bank_sha256": sha256_hex(canonical_bytes(payload)),
        "carriers_enveloped": len(payload["carriers"]),
        "carriers_accepted_by_the_frozen_host": len(accepted),
        "carriers_refused": refused,
        "distinct_structural_signatures": len({host.structural_signature(c) for c in accepted}),
        "envelope_neutrality": neutrality,
        "reveals_performed": 1,
        "no_carrier_content_is_recorded_here": True,
        "reveal_record_sha256": "",
    }
    record["reveal_record_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in record.items() if k != "reveal_record_sha256"}))
    REVEAL_RECORD_PATH.write_bytes(canonical_bytes(record) + b"\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reveal", action="store_true", required=True,
                        help="perform the single authorized reveal")
    parser.parse_args()
    try:
        record = reveal()
    except (RevealError, chronology.ChronologyError, admission.AdmissionError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps({k: v for k, v in record.items()
                      if k not in ("schema", "envelope_neutrality")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
