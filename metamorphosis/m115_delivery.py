"""M115 delivery semantics are M114's, imported rather than copied.

M115 changes model-identity attestation and the provider route.  It does *not* change what a
physical attempt, a materialization, a retryable capacity rejection or a terminal outcome means.
This wrapper changes only the milestone/schema labels, then delegates every rule to M114.
"""

from __future__ import annotations

from typing import Any, Mapping

from metamorphosis import m114_delivery as predecessor
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

MILESTONE = "M115"
DELIVERY_LEDGER_SCHEMA = "m115-delivery-ledger-v1"
MAX_DELIVERY_ATTEMPTS = predecessor.MAX_DELIVERY_ATTEMPTS
MAX_BANK_MATERIALIZATIONS = predecessor.MAX_BANK_MATERIALIZATIONS
RETRY_WAIT_SECONDS = predecessor.RETRY_WAIT_SECONDS
RETRYABLE_STATUS = predecessor.RETRYABLE_STATUS
ATTEMPT_OUTCOMES = predecessor.ATTEMPT_OUTCOMES
TERMINAL_OUTCOMES = predecessor.TERMINAL_OUTCOMES
DeliveryError = predecessor.DeliveryError

classify_attempt = predecessor.classify_attempt
retry_permitted = predecessor.retry_permitted


def validate_delivery_ledger(
    ledger: Mapping[str, Any],
    *,
    spec_commitment_sha256: str | None = None,
    request_body_sha256: str | None = None,
) -> None:
    if not isinstance(ledger, Mapping):
        raise DeliveryError("delivery ledger is not an object")
    if ledger.get("schema") != DELIVERY_LEDGER_SCHEMA:
        raise DeliveryError("delivery ledger schema is not the declared M115 one")
    if ledger.get("milestone") != MILESTONE:
        raise DeliveryError("delivery ledger does not belong to M115")
    inherited = dict(ledger)
    inherited["schema"] = predecessor.DELIVERY_LEDGER_SCHEMA
    inherited["milestone"] = predecessor.MILESTONE
    predecessor.validate_delivery_ledger(
        inherited,
        spec_commitment_sha256=spec_commitment_sha256,
        request_body_sha256=request_body_sha256,
    )


def delivery_summary(ledger: Mapping[str, Any]) -> dict[str, Any]:
    inherited = dict(ledger) if isinstance(ledger, Mapping) else {}
    inherited["schema"] = predecessor.DELIVERY_LEDGER_SCHEMA
    inherited["milestone"] = predecessor.MILESTONE
    summary = dict(predecessor.delivery_summary(inherited))
    summary["schema"] = "m115-delivery-summary-v1"
    summary["semantics_inherited_unchanged_from"] = "M114"
    return summary


def ledger_digest(ledger: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_bytes({k: v for k, v in ledger.items() if k != "ledger_sha256"}))


__all__ = [
    "ATTEMPT_OUTCOMES",
    "DELIVERY_LEDGER_SCHEMA",
    "DeliveryError",
    "MAX_BANK_MATERIALIZATIONS",
    "MAX_DELIVERY_ATTEMPTS",
    "MILESTONE",
    "RETRYABLE_STATUS",
    "RETRY_WAIT_SECONDS",
    "TERMINAL_OUTCOMES",
    "classify_attempt",
    "delivery_summary",
    "ledger_digest",
    "retry_permitted",
    "validate_delivery_ledger",
]
