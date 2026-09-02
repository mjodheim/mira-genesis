#!/usr/bin/env python3
"""Seal the one materialized H64 response without exposing carrier content.

Custody, not science. This validates the frozen spec, the delivery ledger and the admission record,
encrypts the preserved response with GnuPG/AES256, publishes hashes and custody metadata only, then
removes the plaintext. Nothing here parses a carrier, counts a demand or reads a completion.

The passphrase is read from `M119_BANK_SEAL_PASSPHRASE`, is never written, printed or passed on the
command line, and is dropped from this process the moment gpg has consumed it. Keep it offline until
the tested system is frozen and a reveal is explicitly authorized.

Order matters: ciphertext and commitment are published *before* the plaintext is removed. If the
process dies in between, the state is an unsealed materialization, which is recoverable. The reverse
order could destroy the one bank.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m114_delivery as delivery  # noqa: E402
from metamorphosis import m119_bank as bank  # noqa: E402
from metamorphosis import m119_chronology as chronology  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

COMMITMENT_SCHEMA = "m119-public-bank-commitment-v1"

EXPERIMENT = ROOT / chronology.DIRECTORY
RESPONSE_PATH = EXPERIMENT / "GENERATION_RESPONSE.json"
ADMISSION_PATH = EXPERIMENT / "ADMISSION.json"
SEALED_PATH = ROOT / chronology.SEALED_BANK
COMMITMENT_PATH = ROOT / chronology.PUBLIC_BANK_COMMITMENT
SPEC_PATH = ROOT / chronology.GENERATOR_SPEC
PLAN_PATH = ROOT / chronology.ANALYSIS_PLAN
LEDGER_PATH = ROOT / chronology.DELIVERY_LEDGER
SECRET_VARIABLE = "M119_BANK_SEAL_PASSPHRASE"


class SealError(RuntimeError):
    """The seal cannot be taken honestly. Every path fails closed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SealError("cannot read %s: %s" % (path.name, exc))
    if not isinstance(value, dict):
        raise SealError("%s is not a JSON object" % path.name)
    return value


def _validate_ledger(ledger: Mapping[str, Any], *, request_body_sha256: str) -> None:
    if ledger.get("schema") != "m119-delivery-ledger-v1" or ledger.get("milestone") != "M119":
        raise delivery.DeliveryError("the delivery ledger is not the M119 one")
    inherited = dict(ledger)
    inherited["schema"] = delivery.DELIVERY_LEDGER_SCHEMA
    inherited["milestone"] = delivery.MILESTONE
    delivery.validate_delivery_ledger(inherited, request_body_sha256=request_body_sha256)


def _preflight(passphrase: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not passphrase:
        raise SealError("%s is missing" % SECRET_VARIABLE)
    if shutil.which("gpg") is None:
        raise SealError("gpg is unavailable")
    if SEALED_PATH.exists() or COMMITMENT_PATH.exists():
        raise SealError("a sealed bank or public commitment already exists; sealing is single-use")
    if not RESPONSE_PATH.is_file():
        raise SealError("there is no generation response to seal")

    chronology.assert_frozen_system_unchanged(ROOT, phase="sealing")
    plan = _load(PLAN_PATH)
    bank.validate_analysis_plan(plan, ROOT)
    spec = _load(SPEC_PATH)
    bank.validate_generator_spec(spec, plan, ROOT)

    ledger = _load(LEDGER_PATH)
    _validate_ledger(ledger, request_body_sha256=spec["canonical_request_body_sha256"])
    materialized = [a for a in ledger["attempts"] if a.get("outcome") == "materialized"]
    if len(materialized) != 1:
        raise SealError("exactly one materialization is required before sealing")

    admitted = _load(ADMISSION_PATH)
    if admitted.get("admitted") is not True:
        raise SealError("the completion was not admitted; there is no bank to seal")
    if admitted.get("spec_commitment_sha256") != spec["spec_commitment_sha256"]:
        raise SealError("the admission record binds a different frozen spec")

    response = _load(RESPONSE_PATH)
    if response.get("schema") != "m119-generation-response-v1":
        raise SealError("the generation response schema drifted")
    if response.get("spec_commitment_sha256") != spec["spec_commitment_sha256"]:
        raise SealError("the generation response does not bind the frozen spec")
    if response.get("request_body_sha256") != spec["canonical_request_body_sha256"]:
        raise SealError("the generation response does not bind the frozen request body")
    if response.get("delivery_attempt_index") != materialized[0]["attempt_index"]:
        raise SealError("the generation response is not the materialized delivery attempt")
    return spec, ledger, admitted


def seal() -> dict[str, Any]:
    passphrase = os.environ.get(SECRET_VARIABLE, "")
    spec, ledger, admitted = _preflight(passphrase)

    response_bytes = RESPONSE_PATH.read_bytes()
    temp_cipher = SEALED_PATH.with_suffix(SEALED_PATH.suffix + ".tmp")
    temp_commitment = COMMITMENT_PATH.with_suffix(COMMITMENT_PATH.suffix + ".tmp")
    temp_cipher.unlink(missing_ok=True)
    temp_commitment.unlink(missing_ok=True)

    completed = subprocess.run(
        ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase-fd", "0",
         "--symmetric", "--cipher-algo", "AES256", "--output", str(temp_cipher),
         str(RESPONSE_PATH)],
        input=(passphrase + "\n").encode("utf-8"),
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    passphrase = ""  # dropped as soon as gpg has consumed it
    if completed.returncode != 0 or not temp_cipher.is_file():
        temp_cipher.unlink(missing_ok=True)
        raise SealError("gpg failed to create the sealed bank")

    ciphertext = temp_cipher.read_bytes()
    commitment = {
        "schema": COMMITMENT_SCHEMA, "milestone": "M119", "hypothesis": "H64",
        "sealed_at": _now(),
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "analysis_plan_commitment_sha256": spec["analysis_plan_commitment_sha256"],
        "request_body_sha256": spec["canonical_request_body_sha256"],
        "delivery_ledger_sha256": sha256_hex(canonical_bytes(ledger)),
        "admission_sha256": sha256_hex(canonical_bytes(admitted)),
        "generation_response_sha256": sha256_hex(response_bytes),
        "generation_response_bytes": len(response_bytes),
        "ciphertext_sha256": sha256_hex(ciphertext),
        "ciphertext_bytes": len(ciphertext),
        "cipher": "gpg symmetric AES256",
        "no_carrier_content_is_published_here": True,
        "commitment_sha256": "",
    }
    commitment["commitment_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in commitment.items() if k != "commitment_sha256"}))
    temp_commitment.write_bytes(canonical_bytes(commitment) + b"\n")

    temp_cipher.replace(SEALED_PATH)
    temp_commitment.replace(COMMITMENT_PATH)
    RESPONSE_PATH.unlink()

    published = _load(COMMITMENT_PATH)
    if sha256_hex(SEALED_PATH.read_bytes()) != published["ciphertext_sha256"]:
        raise SealError("the published ciphertext digest does not match the sealed file")
    if RESPONSE_PATH.exists():
        raise SealError("the plaintext response survived sealing")
    return {
        "schema": "m119-seal-operation-v1", "milestone": "M119", "hypothesis": "H64",
        "ciphertext_sha256": published["ciphertext_sha256"],
        "commitment_sha256": published["commitment_sha256"],
        "plaintext_removed": True,
        "carrier_content_was_not_printed": True,
    }


def main() -> int:
    try:
        report = seal()
    except (SealError, bank.BankError, delivery.DeliveryError,
            chronology.ChronologyError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
