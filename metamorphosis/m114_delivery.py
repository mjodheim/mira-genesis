"""M114 delivery semantics: what a request is, and what a bank is.

M113 froze a generator identity, made one physical request, received HTTP 429 and materialized no
bank. H58 was never tested, because the model was never reached. That milestone is closed and is
not re-frozen.

What it demonstrated is not about the hypothesis. It is that M113's protocol used one predicate,
"one physical request", to carry two different things at once: how many times the instrument was
allowed to *reach* for the generator, and how many times the generator was allowed to *produce* a
bank. Those coincide only while the network cooperates. A capacity rejection from a shared upstream
pool consumed the second budget without ever spending the first, and the milestone ended on a fact
about queueing.

So M114 separates them, and the separation is the whole of what M114 changes:

    delivery_attempt      one physical request carrying the frozen body
    bank_materialization  a response that actually carries a model completion

A bank exists only when a completion is received. Up to three delivery attempts are permitted to
obtain at most one materialization.

**This rule was decided after M113's instrument failure, before any M114 bank existed, and with no
observation whatsoever of H58.** It was never part of M113 and must never be described as though it
had been. M113 remains an instrument failure under the protocol it actually ran.

The retry window is deliberately the narrowest one that addresses what happened, and its narrowness
is the point. A retry is permitted only where the evidence positively establishes that no generation
occurred: an explicit HTTP 429, no completion of any kind, no usable payload, no carrier, nothing
indicating the model executed. Everything else is final on its first outcome -- an invalid JSON, a
schema violation, a truncated completion, a refusal, an insufficient bank, a timeout after
transmission whose state cannot be established, a connection lost in an ambiguous state, and above
all any scientific outcome including `P22` false.

The asymmetry is the safeguard. `upstream capacity rejection before generation` may be retried under
the frozen rule; `anything that may have reached the model` never may. A protocol that retried an
ambiguous timeout would be a protocol that could quietly draw twice and keep the better draw, which
is the failure mode every part of this milestone exists to prevent.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

MILESTONE = "M114"
DELIVERY_LEDGER_SCHEMA = "m114-delivery-ledger-v1"

# Frozen delivery budget.
MAX_DELIVERY_ATTEMPTS = 3
MAX_BANK_MATERIALIZATIONS = 1
RETRY_WAIT_SECONDS = 60

# The only status that may precede another attempt.
RETRYABLE_STATUS = 429


class DeliveryError(RuntimeError):
    """Raised when a delivery record violates the frozen rule."""


# Every way an attempt can end. `capacity_rejected` is the only one a further attempt may follow.
ATTEMPT_OUTCOMES = (
    "capacity_rejected",      # explicit 429, no completion, no evidence the model executed
    "materialized",           # a response carrying a model completion
    "failed_no_completion",   # ended without a completion for a reason that is not a 429
    "failed_ambiguous",       # may have reached the model; state cannot be established
)

# Outcomes after which no further attempt may be made, whatever the budget says.
TERMINAL_OUTCOMES = ("materialized", "failed_no_completion", "failed_ambiguous")


def classify_attempt(observed: Mapping[str, Any]) -> str:
    """Decide, from what was observed, which outcome an attempt had.

    The classification is deliberately conservative in one direction only. An attempt counts as a
    capacity rejection -- the one retryable outcome -- only when *every* condition holds: the status
    is exactly 429, no completion is present, and nothing in the response indicates the model
    executed. Any doubt resolves to `failed_ambiguous`, which is terminal.

    That asymmetry is not caution for its own sake. Misclassifying a capacity rejection as ambiguous
    costs an attempt. Misclassifying an ambiguous outcome as a capacity rejection would permit a
    second draw against a model that may already have produced one, and no downstream check could
    ever recover the difference.
    """
    if observed.get("completion_present") is True:
        return "materialized"
    if observed.get("model_execution_cannot_be_excluded") is True:
        return "failed_ambiguous"
    if observed.get("status") == RETRYABLE_STATUS:
        return "capacity_rejected"
    return "failed_no_completion"


def retry_permitted(outcome: str, attempts_so_far: int) -> bool:
    """Whether the frozen rule permits another attempt after this one."""
    if outcome != "capacity_rejected":
        return False
    return attempts_so_far < MAX_DELIVERY_ATTEMPTS


def validate_delivery_ledger(
    ledger: Mapping[str, Any],
    *,
    spec_commitment_sha256: str | None = None,
    request_body_sha256: str | None = None,
) -> None:
    """Recompute every delivery rule from the record rather than trusting its summary.

    The runner writes this ledger, so nothing it asserts about itself is evidence. What is evidence
    is the sequence of attempts: their count, their request digests, their outcomes, the waits
    between them, and where the materialization sits. Every rule below is derived from that
    sequence.
    """
    if not isinstance(ledger, Mapping):
        raise DeliveryError("delivery ledger is not an object")
    if ledger.get("schema") != DELIVERY_LEDGER_SCHEMA:
        raise DeliveryError("delivery ledger schema is not the declared one")
    if ledger.get("milestone") != MILESTONE:
        raise DeliveryError("delivery ledger does not belong to this milestone")

    attempts = ledger.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise DeliveryError("a delivery ledger records at least one attempt")

    # -- budget -------------------------------------------------------------------------
    if len(attempts) > MAX_DELIVERY_ATTEMPTS:
        raise DeliveryError(
            "%d delivery attempts were made; the frozen budget is %d"
            % (len(attempts), MAX_DELIVERY_ATTEMPTS)
        )

    seen_indices = []
    materialized_at = None
    for position, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, Mapping):
            raise DeliveryError("delivery attempt %d is malformed" % position)
        for key in (
            "attempt_index", "started_at", "status", "requested_provider", "served_provider",
            "requested_model", "served_model", "response_headers", "error_body",
            "response_sha256", "request_body_sha256", "completion_present",
            "model_execution_cannot_be_excluded", "outcome", "retry_permitted_by_the_frozen_rule",
            "waited_seconds_before_this_attempt",
        ):
            if key not in attempt:
                raise DeliveryError(
                    "delivery attempt %d does not record %s; a record that omits what the rule is "
                    "computed from cannot be checked against it" % (position, key)
                )

        index = attempt["attempt_index"]
        if not isinstance(index, int) or isinstance(index, bool) or index != position:
            raise DeliveryError(
                "delivery attempts must be recorded in order, one per index; attempt at position "
                "%d claims index %r" % (position, index)
            )
        seen_indices.append(index)

        # -- the same frozen request, every time ---------------------------------------
        if request_body_sha256 is not None and attempt["request_body_sha256"] != request_body_sha256:
            raise DeliveryError(
                "delivery attempt %d sent a different request body; a retry that changes the "
                "request is a second experiment wearing the first one's name" % position
            )

        # -- no substitution -----------------------------------------------------------
        served_provider = attempt["served_provider"]
        if served_provider is not None and served_provider != attempt["requested_provider"]:
            raise DeliveryError(
                "delivery attempt %d was served by %r rather than the frozen %r"
                % (position, served_provider, attempt["requested_provider"])
            )
        served_model = attempt["served_model"]
        if served_model is not None and served_model != attempt["requested_model"]:
            raise DeliveryError(
                "delivery attempt %d was served model %r rather than the frozen %r"
                % (position, served_model, attempt["requested_model"])
            )

        # -- the outcome must be the one the evidence supports -------------------------
        if attempt["outcome"] not in ATTEMPT_OUTCOMES:
            raise DeliveryError("delivery attempt %d records an unknown outcome" % position)
        recomputed = classify_attempt(attempt)
        if recomputed != attempt["outcome"]:
            raise DeliveryError(
                "delivery attempt %d records outcome %r; the evidence it carries classifies as %r"
                % (position, attempt["outcome"], recomputed)
            )

        if attempt["outcome"] == "materialized":
            if materialized_at is not None:
                raise DeliveryError("more than one delivery attempt materialized a bank")
            materialized_at = position

        # -- nothing may follow a terminal outcome -------------------------------------
        is_last = position == len(attempts)
        if not is_last and attempt["outcome"] in TERMINAL_OUTCOMES:
            raise DeliveryError(
                "delivery attempt %d ended %r and was followed by another attempt; only a capacity "
                "rejection before any generation may be retried"
                % (position, attempt["outcome"])
            )

        expected_retry = retry_permitted(attempt["outcome"], position)
        if not is_last and not expected_retry:
            raise DeliveryError(
                "delivery attempt %d was followed by another attempt the frozen rule does not "
                "permit" % position
            )
        if attempt["retry_permitted_by_the_frozen_rule"] is not expected_retry:
            raise DeliveryError(
                "delivery attempt %d records retry permission %r; the frozen rule computes %r"
                % (position, attempt["retry_permitted_by_the_frozen_rule"], expected_retry)
            )

        # -- the wait is fixed and pre-registered --------------------------------------
        waited = attempt["waited_seconds_before_this_attempt"]
        if position == 1:
            if waited not in (0, 0.0):
                raise DeliveryError("the first delivery attempt waits for nothing")
        else:
            if not isinstance(waited, (int, float)) or waited < RETRY_WAIT_SECONDS:
                raise DeliveryError(
                    "delivery attempt %d waited %r seconds; the frozen interval is %d"
                    % (position, waited, RETRY_WAIT_SECONDS)
                )

    if seen_indices != list(range(1, len(attempts) + 1)):
        raise DeliveryError("delivery attempt indices are not the contiguous sequence from one")

    # -- at most one bank, and nothing after it ----------------------------------------
    materializations = sum(1 for a in attempts if a["outcome"] == "materialized")
    if materializations > MAX_BANK_MATERIALIZATIONS:
        raise DeliveryError(
            "%d bank materializations; at most %d is permitted"
            % (materializations, MAX_BANK_MATERIALIZATIONS)
        )
    if materialized_at is not None and materialized_at != len(attempts):
        raise DeliveryError("a delivery attempt was made after a bank had been materialized")

    declared = ledger.get("bank_materialization_index")
    if materialized_at is None:
        if declared is not None:
            raise DeliveryError("the ledger names a materialization index but none materialized")
    elif declared != materialized_at:
        raise DeliveryError(
            "the ledger names materialization index %r; the attempts place it at %d"
            % (declared, materialized_at)
        )

    if spec_commitment_sha256 is not None:
        if ledger.get("spec_commitment_sha256") != spec_commitment_sha256:
            raise DeliveryError("the delivery ledger does not bind the frozen generator spec")


def delivery_summary(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """What the checker reports, recomputed from the attempts rather than read from a field."""
    # Summarised, not validated -- and it is read on records that have already failed validation,
    # because a report that cannot describe a broken ledger is a report that goes silent exactly
    # where the reader needs it. So the shape is coerced rather than trusted: anything that is not
    # a list of objects summarises as no attempts at all, which is what `validate_delivery_ledger`
    # refuses anyway.
    raw = ledger.get("attempts") if isinstance(ledger, Mapping) else None
    attempts: Sequence[Mapping[str, Any]] = (
        [a for a in raw if isinstance(a, Mapping)] if isinstance(raw, list) else []
    )
    outcomes = [a.get("outcome") for a in attempts]
    materialized = [i for i, o in enumerate(outcomes, start=1) if o == "materialized"]
    return {
        "schema": "m114-delivery-summary-v1",
        "delivery_attempts": len(attempts),
        "delivery_budget": MAX_DELIVERY_ATTEMPTS,
        "within_budget": len(attempts) <= MAX_DELIVERY_ATTEMPTS,
        "outcomes": outcomes,
        "capacity_rejections": sum(1 for o in outcomes if o == "capacity_rejected"),
        "bank_materializations": len(materialized),
        "bank_materialization_index": materialized[0] if materialized else None,
        "every_attempt_sent_the_same_body": len(
            {a.get("request_body_sha256") for a in attempts}
        ) <= 1,
        "no_attempt_followed_a_terminal_outcome": all(
            o == "capacity_rejected" for o in outcomes[:-1]
        ),
        "no_substitution": all(
            (a.get("served_provider") in (None, a.get("requested_provider")))
            and (a.get("served_model") in (None, a.get("requested_model")))
            for a in attempts
        ),
    }


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
