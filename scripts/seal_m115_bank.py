"""Seal the one materialized M115 response without exposing carrier content.

This is a custody operation, not a scientific reader. It validates the frozen spec and delivery
ledger, encrypts the complete preserved generation response with GnuPG/AES256, publishes only
hashes and custody metadata, removes the plaintext response, then re-validates the sealed state.

The passphrase is read from `M115_BANK_SEAL_PASSPHRASE` and is never written, printed or passed on
the command line. The operator must keep that passphrase offline until the tested system is frozen
and a later reveal is explicitly authorized.
"""

from __future__ import annotations

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

from metamorphosis import m115_carrier_bank as bank  # noqa: E402
from metamorphosis import m115_delivery as delivery  # noqa: E402
from metamorphosis import m115_sealing as sealing  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

RESPONSE_PATH = ROOT / sealing.GENERATION_RESPONSE_PATH
SEALED_PATH = ROOT / bank.SEALED_BANK_PATH
COMMITMENT_PATH = ROOT / bank.BANK_COMMITMENT_PATH
SPEC_PATH = ROOT / bank.GENERATOR_SPEC_PATH
LEDGER_PATH = ROOT / bank.DELIVERY_LEDGER_PATH


class SealCommandError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SealCommandError("cannot read %s: %s" % (path.relative_to(ROOT), exc))
    if not isinstance(value, dict):
        raise SealCommandError("%s is not a JSON object" % path.relative_to(ROOT))
    return value


def _preflight(passphrase: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not passphrase:
        raise SealCommandError("M115_BANK_SEAL_PASSPHRASE is missing")
    if shutil.which("gpg") is None:
        raise SealCommandError("gpg is unavailable")
    if not SPEC_PATH.is_file() or not LEDGER_PATH.is_file():
        raise SealCommandError("frozen spec and delivery ledger are required before sealing")
    if not RESPONSE_PATH.is_file():
        raise SealCommandError("GENERATION_RESPONSE.json is missing; there is nothing to seal")
    if SEALED_PATH.exists() or COMMITMENT_PATH.exists():
        raise SealCommandError("a sealed bank or public commitment already exists; sealing is single-use")

    spec = _load(SPEC_PATH)
    bank.validate_generator_spec(spec, root=ROOT)
    ledger = _load(LEDGER_PATH)
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=spec.get("spec_commitment_sha256"),
        request_body_sha256=spec.get("canonical_request_body_sha256"),
    )
    if delivery.delivery_summary(ledger).get("bank_materializations") != 1:
        raise SealCommandError("exactly one materialization is required before sealing")

    response = _load(RESPONSE_PATH)
    if response.get("schema") != "m115-generation-response-v1":
        raise SealCommandError("generation response schema drifted")
    if response.get("milestone") != bank.MILESTONE or response.get("hypothesis") != bank.HYPOTHESIS:
        raise SealCommandError("generation response belongs to another experiment")
    if response.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
        raise SealCommandError("generation response does not bind the frozen spec")
    if response.get("request_body_sha256") != spec.get("canonical_request_body_sha256"):
        raise SealCommandError("generation response does not bind the frozen request body")
    attestation = response.get("runtime_identity_attestation")
    if not isinstance(attestation, dict) or attestation.get("holds") is not True:
        raise SealCommandError("generation response lacks a passing runtime identity attestation")
    if not isinstance(response.get("body"), dict):
        raise SealCommandError("generation response carries no materialized response body")
    return spec, ledger, response


def seal() -> dict[str, Any]:
    passphrase = os.environ.get("M115_BANK_SEAL_PASSPHRASE", "")
    spec, ledger, _response = _preflight(passphrase)

    response_bytes = RESPONSE_PATH.read_bytes()
    response_sha256 = sha256_hex(response_bytes)
    temp_cipher = SEALED_PATH.with_suffix(SEALED_PATH.suffix + ".tmp")
    temp_commitment = COMMITMENT_PATH.with_suffix(COMMITMENT_PATH.suffix + ".tmp")
    temp_cipher.unlink(missing_ok=True)
    temp_commitment.unlink(missing_ok=True)

    command = [
        "gpg",
        "--batch",
        "--yes",
        "--pinentry-mode",
        "loopback",
        "--passphrase-fd",
        "0",
        "--symmetric",
        "--cipher-algo",
        "AES256",
        "--output",
        str(temp_cipher),
        str(RESPONSE_PATH),
    ]
    completed = subprocess.run(
        command,
        input=(passphrase + "\n").encode("utf-8"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    # Drop the only in-process reference as soon as gpg has consumed it.
    passphrase = ""
    if completed.returncode != 0 or not temp_cipher.is_file():
        temp_cipher.unlink(missing_ok=True)
        raise SealCommandError("gpg failed to create the sealed bank")

    ciphertext = temp_cipher.read_bytes()
    commitment = sealing.build_public_commitment(
        spec_commitment_sha256=str(spec["spec_commitment_sha256"]),
        request_body_sha256=str(spec["canonical_request_body_sha256"]),
        delivery_ledger_sha256=delivery.ledger_digest(ledger),
        generation_response_sha256=response_sha256,
        generation_response_bytes=len(response_bytes),
        ciphertext_sha256=sha256_hex(ciphertext),
        ciphertext_bytes=len(ciphertext),
        sealed_at=_now(),
    )
    temp_commitment.write_bytes(canonical_bytes(commitment) + b"\n")

    # Publish ciphertext and the digest-only commitment before removing plaintext. If the process
    # dies before the unlink, readiness remains `materialized_unsealed`; it never reports a seal.
    temp_cipher.replace(SEALED_PATH)
    temp_commitment.replace(COMMITMENT_PATH)
    RESPONSE_PATH.unlink()

    # Final fail-closed check against files on disk. The ciphertext remains recoverable with the
    # offline passphrase even if this final consistency check discovers an instrument defect.
    sealing.validate_public_commitment(_load(COMMITMENT_PATH), root=ROOT)
    state = sealing.readiness(ROOT)
    if state.get("phase") != "generated_sealed" or state.get("blockers"):
        raise SealCommandError("sealed files exist but the M115 readiness gate did not close")

    return {
        "schema": "m115-seal-operation-v1",
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "phase": state["phase"],
        "spec_commitment_sha256": commitment["spec_commitment_sha256"],
        "delivery_ledger_sha256": commitment["delivery_ledger_sha256"],
        "generation_response_sha256": commitment["generation_response_sha256"],
        "ciphertext_sha256": commitment["ciphertext_sha256"],
        "commitment_sha256": commitment["commitment_sha256"],
        "plaintext_removed": True,
        "carrier_content_was_not_printed": True,
    }


def main() -> int:
    try:
        report = seal()
    except (SealCommandError, sealing.SealingError, bank.CarrierBankError, delivery.DeliveryError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
