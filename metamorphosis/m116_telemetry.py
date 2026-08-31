"""Non-carrier operational telemetry for a future H61 delivery attempt.

M115 could not say why it failed. Its runner computed `finish_reason` and `usage.completion_tokens`
to decide whether model execution could be excluded, then discarded both, so the preserved record
carried a bare `invalid_json` that a truncated completion and a prose-prefixed completion would
have produced identically.

This module preserves exactly the operational metadata needed to tell those cases apart, under a
strict allowlist, and refuses to preserve anything else. The distinction it enforces is between
*operational* metadata -- how the endpoint behaved -- and *carrier* content -- what it said. The
first may be read by a human before reveal. The second may not be read by a human at all until the
tested system is frozen and the single reveal is authorized.

Nothing here parses carrier content, and nothing here decides anything: the telemetry is written,
committed and then not read again until the terminal classifier runs.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

TELEMETRY_SCHEMA = "m116-delivery-telemetry-v1"

# Every field the ledger may carry. A field absent from the endpoint's response is recorded as
# None rather than omitted, so that "the endpoint did not report it" and "we forgot to look" are
# different observations in the preserved record.
ALLOWED_FIELDS = (
    "http_status",
    "finish_reason",
    "native_finish_reason",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "response_bytes",
    "content_bytes",
    "content_present",
    "choice_count",
    "generation_id",
    "requested_model",
    "served_model",
    "requested_provider",
    "served_provider",
    "canonical_checkpoint_attested",
    "router_direct",
    "router_no_fallback",
    "router_one_endpoint",
    "router_one_attempt",
    "router_no_pipeline_intervention",
    "model_execution_evidence",
    "refusal_present",
    "response_format_enforced",
    "transport_failure_class",
    "schema",
)

# Fields whose value must be a short, structurally constrained token. Free text is where a
# provider puts an account identifier, a rate-limit message quoting a key prefix, or a fragment
# of the prompt -- so an unconstrained string is refused even when the field name is allowlisted.
_TOKEN_FIELDS = (
    "finish_reason",
    "native_finish_reason",
    "generation_id",
    "requested_model",
    "served_model",
    "requested_provider",
    "served_provider",
    "transport_failure_class",
    "schema",
)
_TOKEN_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")

_BOOLEAN_FIELDS = (
    "content_present",
    "canonical_checkpoint_attested",
    "router_direct",
    "router_no_fallback",
    "router_one_endpoint",
    "router_one_attempt",
    "router_no_pipeline_intervention",
    "model_execution_evidence",
    "refusal_present",
    "response_format_enforced",
)
_INTEGER_FIELDS = (
    "http_status",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "response_bytes",
    "content_bytes",
    "choice_count",
)

# Finish reasons that are affirmative evidence the endpoint stopped because the output budget ran
# out. `truncated_completion` may be concluded from these and from nothing else.
BUDGET_FINISH_REASONS = frozenset({"length", "max_tokens", "MAX_TOKENS", "model_length"})

# Finish reasons that are affirmative evidence the model chose to stop on its own.
COMPLETED_FINISH_REASONS = frozenset({"stop", "end_turn", "eos", "STOP"})

# Finish reasons that are affirmative evidence of a refusal or filter.
REFUSAL_FINISH_REASONS = frozenset({"content_filter", "refusal", "safety"})


class TelemetryError(RuntimeError):
    """Telemetry does not satisfy the allowlist, or carries something it must never carry."""


def _integer_or_none(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _token_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if _TOKEN_RE.match(trimmed) else None


def extract(
    *,
    status: int | None,
    body: Mapping[str, Any] | None,
    response_bytes: int | None,
    headers: Mapping[str, Any] | None = None,
    identity_attestation: Mapping[str, Any] | None = None,
    requested_model: str | None = None,
    requested_provider: str | None = None,
    transport_failure_class: str | None = None,
) -> dict[str, Any]:
    """Project an endpoint response onto the allowlist. Carrier content never survives this."""
    body = body if isinstance(body, Mapping) else {}
    headers = headers if isinstance(headers, Mapping) else {}
    attestation = identity_attestation if isinstance(identity_attestation, Mapping) else {}
    router = attestation.get("router_attestation") if isinstance(
        attestation.get("router_attestation"), Mapping
    ) else {}
    checks = router.get("checks") if isinstance(router.get("checks"), Mapping) else {}

    choices = body.get("choices")
    choices = choices if isinstance(choices, list) else []
    first = choices[0] if choices and isinstance(choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first.get("message"), Mapping) else {}
    content = message.get("content")
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    details = usage.get("completion_tokens_details")
    details = details if isinstance(details, Mapping) else {}

    finish_reason = _token_or_none(first.get("finish_reason"))
    completion_tokens = _integer_or_none(usage.get("completion_tokens"))
    execution = bool(choices) or bool(completion_tokens) or finish_reason is not None

    # A refusal is recorded only when the endpoint says so structurally -- a `refusal` field, or a
    # finish reason in the refusal set. Prose that reads like a refusal is not evidence, and is
    # never inspected here.
    refusal = message.get("refusal") is not None or (
        finish_reason is not None and finish_reason in REFUSAL_FINISH_REASONS
    )

    record = {
        "schema": TELEMETRY_SCHEMA,
        "http_status": _integer_or_none(status),
        "finish_reason": finish_reason,
        "native_finish_reason": _token_or_none(first.get("native_finish_reason")),
        "prompt_tokens": _integer_or_none(usage.get("prompt_tokens")),
        "completion_tokens": completion_tokens,
        "total_tokens": _integer_or_none(usage.get("total_tokens")),
        "reasoning_tokens": _integer_or_none(details.get("reasoning_tokens")),
        "response_bytes": _integer_or_none(response_bytes),
        "content_bytes": len(content.encode("utf-8")) if isinstance(content, str) else None,
        "content_present": isinstance(content, str) and bool(content.strip()),
        "choice_count": len(choices),
        "generation_id": _token_or_none(headers.get("x-generation-id") or body.get("id")),
        "requested_model": _token_or_none(requested_model),
        "served_model": _token_or_none(body.get("model")),
        "requested_provider": _token_or_none(requested_provider),
        "served_provider": _token_or_none(body.get("provider")),
        "canonical_checkpoint_attested": bool(checks.get("selected_checkpoint_exact")),
        "router_direct": bool(checks.get("direct_strategy")),
        "router_no_fallback": bool(checks.get("no_fallback_attested")),
        "router_one_endpoint": bool(checks.get("one_selected_endpoint")),
        "router_one_attempt": bool(checks.get("one_router_attempt")),
        "router_no_pipeline_intervention": bool(checks.get("no_pipeline_intervention")),
        "model_execution_evidence": execution,
        "refusal_present": bool(refusal),
        # Whether the endpoint structurally acknowledged the schema it was given. Absent on every
        # endpoint observed so far, so this is None rather than False until one reports it.
        "response_format_enforced": (
            bool(body["response_format_enforced"])
            if isinstance(body.get("response_format_enforced"), bool)
            else None
        ),
        "transport_failure_class": _token_or_none(transport_failure_class),
    }
    validate(record)
    return record


def validate(record: Mapping[str, Any]) -> None:
    """Fail closed on any field outside the allowlist or of the wrong shape."""
    if not isinstance(record, Mapping):
        raise TelemetryError("telemetry is not an object")
    if record.get("schema") != TELEMETRY_SCHEMA:
        raise TelemetryError("telemetry schema is not the declared one")
    unexpected = sorted(set(record) - set(ALLOWED_FIELDS))
    if unexpected:
        raise TelemetryError("telemetry carries fields outside the allowlist: %s"
                             % ", ".join(unexpected))
    missing = sorted(set(ALLOWED_FIELDS) - set(record))
    if missing:
        raise TelemetryError("telemetry omits allowlisted fields: %s" % ", ".join(missing))
    for field in _INTEGER_FIELDS:
        value = record[field]
        if value is not None and not (isinstance(value, int) and not isinstance(value, bool)):
            raise TelemetryError("telemetry field %s is not an integer or null" % field)
    for field in _BOOLEAN_FIELDS:
        if not isinstance(record[field], bool) and record[field] is not None:
            raise TelemetryError("telemetry field %s is not a boolean or null" % field)
    for field in _TOKEN_FIELDS:
        value = record[field]
        if value is None:
            continue
        if not isinstance(value, str) or not _TOKEN_RE.match(value):
            raise TelemetryError(
                "telemetry field %s is not a short constrained token; free text is refused"
                % field
            )


def assert_no_carrier_content(record: Mapping[str, Any]) -> None:
    """The read barrier.

    Telemetry may be read by a human before reveal. That is only safe while every value in it is a
    scalar the endpoint reported about its own behaviour. This refuses any nested structure, which
    is the shape carrier content would have to arrive in, and any string long enough to hold it.
    """
    validate(record)
    for field, value in record.items():
        if isinstance(value, (Mapping, list, tuple, set, bytes)):
            raise TelemetryError(
                "telemetry field %s is a container; only scalars cross the read barrier" % field
            )
        if isinstance(value, str) and len(value) > 128:
            raise TelemetryError("telemetry field %s is too long to be operational metadata"
                                 % field)


__all__ = [
    "ALLOWED_FIELDS",
    "BUDGET_FINISH_REASONS",
    "COMPLETED_FINISH_REASONS",
    "REFUSAL_FINISH_REASONS",
    "TELEMETRY_SCHEMA",
    "TelemetryError",
    "assert_no_carrier_content",
    "extract",
    "validate",
]
