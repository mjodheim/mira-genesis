"""M115 sealing boundary between materialization and scientific use.

A model completion is not a sealed bank.  M115's delivery runner deliberately writes the
materialized response first so the physical request can be preserved, then requires a distinct
custody step before any scientific process may inspect carrier content.  This module makes that
boundary mechanical: a `generated_sealed` state requires ciphertext, a public digest commitment,
and absence of the plaintext generation response.

Nothing here decrypts or interprets carrier content.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m115_carrier_bank as bank
from metamorphosis import m115_delivery as delivery
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

COMMITMENT_SCHEMA = "m115-carrier-bank-public-commitment-v1"
GENERATION_RESPONSE_PATH = bank.EXPERIMENT_DIRECTORY / "GENERATION_RESPONSE.json"
_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")


class SealingError(RuntimeError):
    """Raised when the custody boundary cannot be established exactly."""


def _root(root: Path | None) -> Path:
    return Path.cwd().resolve() if root is None else Path(root).resolve()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SealingError("cannot read %s: %s" % (path, exc))
    if not isinstance(value, dict):
        raise SealingError("%s is not a JSON object" % path)
    return value


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def commitment_digest(commitment: Mapping[str, Any]) -> str:
    body = {key: value for key, value in commitment.items() if key != "commitment_sha256"}
    return sha256_hex(canonical_bytes(body))


def build_public_commitment(
    *,
    spec_commitment_sha256: str,
    request_body_sha256: str,
    delivery_ledger_sha256: str,
    generation_response_sha256: str,
    generation_response_bytes: int,
    ciphertext_sha256: str,
    ciphertext_bytes: int,
    sealed_at: str,
    cipher: str = "gpg-symmetric-aes256",
    key_custody: str = "offline-project-holder",
) -> dict[str, Any]:
    commitment: dict[str, Any] = {
        "schema": COMMITMENT_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "status": "sealed_unrevealed",
        "spec_commitment_sha256": spec_commitment_sha256,
        "request_body_sha256": request_body_sha256,
        "delivery_ledger_sha256": delivery_ledger_sha256,
        "generation_response_sha256": generation_response_sha256,
        "generation_response_bytes": generation_response_bytes,
        "ciphertext_sha256": ciphertext_sha256,
        "ciphertext_bytes": ciphertext_bytes,
        "cipher": cipher,
        "key_custody": key_custody,
        "sealed_at": sealed_at,
        "plaintext_response_present_in_repository": False,
        "revealed": False,
        "commitment_sha256": "",
    }
    commitment["commitment_sha256"] = commitment_digest(commitment)
    return commitment


def validate_public_commitment(
    commitment: Mapping[str, Any], *, root: Path | None = None
) -> None:
    expected = {
        "schema",
        "milestone",
        "hypothesis",
        "status",
        "spec_commitment_sha256",
        "request_body_sha256",
        "delivery_ledger_sha256",
        "generation_response_sha256",
        "generation_response_bytes",
        "ciphertext_sha256",
        "ciphertext_bytes",
        "cipher",
        "key_custody",
        "sealed_at",
        "plaintext_response_present_in_repository",
        "revealed",
        "commitment_sha256",
    }
    if not isinstance(commitment, Mapping) or set(commitment) != expected:
        raise SealingError("M115 public commitment fields differ from the closed schema")
    if commitment.get("schema") != COMMITMENT_SCHEMA:
        raise SealingError("M115 public commitment schema drifted")
    if commitment.get("milestone") != bank.MILESTONE or commitment.get("hypothesis") != bank.HYPOTHESIS:
        raise SealingError("M115 public commitment belongs to another experiment")
    if commitment.get("status") != "sealed_unrevealed" or commitment.get("revealed") is not False:
        raise SealingError("M115 public commitment is not sealed and unrevealed")
    if commitment.get("plaintext_response_present_in_repository") is not False:
        raise SealingError("M115 commitment may not claim a tracked plaintext response")
    for field in (
        "spec_commitment_sha256",
        "request_body_sha256",
        "delivery_ledger_sha256",
        "generation_response_sha256",
        "ciphertext_sha256",
        "commitment_sha256",
    ):
        if not _is_sha256(commitment.get(field)):
            raise SealingError("M115 public commitment %s is malformed" % field)
    for field in ("generation_response_bytes", "ciphertext_bytes"):
        value = commitment.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SealingError("M115 public commitment %s is malformed" % field)
    if commitment.get("cipher") != "gpg-symmetric-aes256":
        raise SealingError("M115 public commitment cipher drifted")
    if commitment.get("key_custody") != "offline-project-holder":
        raise SealingError("M115 sealing key must remain with the offline project holder")
    if not isinstance(commitment.get("sealed_at"), str) or "T" not in str(commitment.get("sealed_at")):
        raise SealingError("M115 public commitment seal timestamp is malformed")
    if commitment.get("commitment_sha256") != commitment_digest(commitment):
        raise SealingError("M115 public commitment digest drifted")

    base = _root(root)
    spec = _load(base / bank.GENERATOR_SPEC_PATH)
    ledger = _load(base / bank.DELIVERY_LEDGER_PATH)
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=spec.get("spec_commitment_sha256"),
        request_body_sha256=spec.get("canonical_request_body_sha256"),
    )
    summary = delivery.delivery_summary(ledger)
    if summary.get("bank_materializations") != 1:
        raise SealingError("M115 cannot seal without exactly one bank materialization")
    if commitment.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
        raise SealingError("M115 public commitment does not bind the frozen generator spec")
    if commitment.get("request_body_sha256") != spec.get("canonical_request_body_sha256"):
        raise SealingError("M115 public commitment does not bind the frozen request body")
    if commitment.get("delivery_ledger_sha256") != delivery.ledger_digest(ledger):
        raise SealingError("M115 public commitment does not bind the delivery ledger")

    ciphertext = base / bank.SEALED_BANK_PATH
    if not ciphertext.is_file():
        raise SealingError("M115 sealed ciphertext is missing")
    raw_ciphertext = ciphertext.read_bytes()
    if commitment.get("ciphertext_bytes") != len(raw_ciphertext):
        raise SealingError("M115 sealed ciphertext size drifted")
    if commitment.get("ciphertext_sha256") != sha256_hex(raw_ciphertext):
        raise SealingError("M115 sealed ciphertext digest drifted")
    if (base / GENERATION_RESPONSE_PATH).is_file():
        raise SealingError("M115 plaintext generation response still exists")


def readiness(root: Path | None = None) -> dict[str, Any]:
    """Return M115 readiness with the materialized/unsealed state represented explicitly."""
    base = _root(root)
    state = dict(bank.readiness(base))
    blockers = list(state.get("blockers") or [])

    ledger_path = base / bank.DELIVERY_LEDGER_PATH
    if not ledger_path.is_file():
        state["blockers"] = blockers
        return state

    try:
        spec = _load(base / bank.GENERATOR_SPEC_PATH)
        ledger = _load(ledger_path)
        delivery.validate_delivery_ledger(
            ledger,
            spec_commitment_sha256=spec.get("spec_commitment_sha256"),
            request_body_sha256=spec.get("canonical_request_body_sha256"),
        )
        materializations = delivery.delivery_summary(ledger).get("bank_materializations")
    except (SealingError, delivery.DeliveryError) as exc:
        blockers.append("sealing boundary: %s" % exc)
        state["blockers"] = blockers
        return state

    if materializations != 1:
        state["blockers"] = blockers
        return state

    state["phase"] = "materialized_unsealed"
    response_path = base / GENERATION_RESPONSE_PATH
    sealed_path = base / bank.SEALED_BANK_PATH
    commitment_path = base / bank.BANK_COMMITMENT_PATH
    if not response_path.is_file():
        blockers.append("materialized response is absent before a valid seal was established")
    if not sealed_path.is_file():
        blockers.append("missing SEALED_BANK.json.gpg")
    if not commitment_path.is_file():
        blockers.append("missing PUBLIC_BANK_COMMITMENT.json")

    if sealed_path.is_file() and commitment_path.is_file():
        try:
            validate_public_commitment(_load(commitment_path), root=base)
        except SealingError as exc:
            blockers.append("public commitment: %s" % exc)
        else:
            state["phase"] = "generated_sealed"
            blockers = [
                item
                for item in blockers
                if item not in {
                    "missing SEALED_BANK.json.gpg",
                    "missing PUBLIC_BANK_COMMITMENT.json",
                    "materialized response is absent before a valid seal was established",
                }
            ]

    state["blockers"] = sorted(set(blockers))
    return state


__all__ = [
    "COMMITMENT_SCHEMA",
    "GENERATION_RESPONSE_PATH",
    "SealingError",
    "build_public_commitment",
    "commitment_digest",
    "readiness",
    "validate_public_commitment",
]
