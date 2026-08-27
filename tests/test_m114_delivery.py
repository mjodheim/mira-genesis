"""M114's delivery rule, attacked at every point it could be bent.

M113 used one predicate for two things: how often the instrument could reach for the generator, and
how often the generator could produce a bank. M114 separates them. These tests exist because a
separation that is only written down is a separation until someone writes a ledger that ignores it.

Every test below is an attempt to obtain a second draw at the model, or to hide one that happened.
"""

from __future__ import annotations

import json

import pytest

from metamorphosis import m114_delivery as delivery


def _attempt(index, outcome, **overrides):
    """One well-formed attempt record, which each test then bends in exactly one place."""
    base = {
        "attempt_index": index,
        "started_at": "2026-08-27T09:00:%02dZ" % index,
        "status": 429 if outcome == "capacity_rejected" else 200,
        "requested_provider": "Morph",
        "served_provider": None if outcome == "capacity_rejected" else "Morph",
        "requested_model": "deepseek/deepseek-v4-flash-0731",
        "served_model": None if outcome == "capacity_rejected" else "deepseek/deepseek-v4-flash-0731",
        "response_headers": {"server": "cloudflare"},
        "error_body": {"error": {"code": 429}} if outcome == "capacity_rejected" else None,
        "response_sha256": "%064d" % index,
        "request_body_sha256": "a" * 64,
        "completion_present": outcome == "materialized",
        "model_execution_cannot_be_excluded": outcome == "failed_ambiguous",
        "outcome": outcome,
        "retry_permitted_by_the_frozen_rule": delivery.retry_permitted(outcome, index),
        "waited_seconds_before_this_attempt": 0 if index == 1 else 60,
    }
    base.update(overrides)
    return base


def _ledger(*attempts, **overrides):
    materialized = [
        i for i, a in enumerate(attempts, start=1) if a.get("outcome") == "materialized"
    ]
    base = {
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": "M114",
        "spec_commitment_sha256": "c" * 64,
        "attempts": list(attempts),
        "bank_materialization_index": materialized[0] if materialized else None,
    }
    base.update(overrides)
    return base


def _validate(ledger):
    delivery.validate_delivery_ledger(ledger, request_body_sha256="a" * 64)


# ------------------------------------------------------------------ what the rule permits


def test_one_capacity_rejection_then_a_materialization_is_the_shape_this_milestone_exists_for():
    """Exactly M113's failure, survived."""
    _validate(_ledger(_attempt(1, "capacity_rejected"), _attempt(2, "materialized")))


def test_three_capacity_rejections_exhaust_the_budget_without_a_bank():
    ledger = _ledger(
        _attempt(1, "capacity_rejected"),
        _attempt(2, "capacity_rejected"),
        _attempt(3, "capacity_rejected"),
    )
    _validate(ledger)
    summary = delivery.delivery_summary(ledger)
    assert summary["delivery_attempts"] == 3
    assert summary["bank_materializations"] == 0
    assert summary["bank_materialization_index"] is None


def test_a_first_attempt_that_materializes_needs_no_second():
    _validate(_ledger(_attempt(1, "materialized")))


# ------------------------------------------------------- attempts to obtain a second draw


def test_a_fourth_delivery_attempt_is_refused():
    with pytest.raises(delivery.DeliveryError, match="frozen budget"):
        _validate(_ledger(*[_attempt(i, "capacity_rejected") for i in range(1, 5)]))


@pytest.mark.parametrize("terminal", ["failed_no_completion", "failed_ambiguous", "materialized"])
def test_nothing_may_follow_a_terminal_outcome(terminal):
    """The asymmetry that is the whole safeguard.

    A capacity rejection establishes that no generation occurred. Every other ending either
    produced a completion or cannot exclude one, and retrying those would be drawing twice against
    the same model and keeping whichever draw came out better.
    """
    with pytest.raises(delivery.DeliveryError):
        _validate(_ledger(_attempt(1, terminal), _attempt(2, "materialized")))


def test_an_ambiguous_timeout_may_never_be_retried():
    """A request that was transmitted and then lost cannot prove the model did not run."""
    ambiguous = _attempt(1, "failed_ambiguous", status=None,
                         model_execution_cannot_be_excluded=True)
    assert delivery.classify_attempt(ambiguous) == "failed_ambiguous"
    assert delivery.retry_permitted("failed_ambiguous", 1) is False
    with pytest.raises(delivery.DeliveryError):
        _validate(_ledger(ambiguous, _attempt(2, "materialized")))


def test_a_429_that_nonetheless_carried_a_completion_is_not_a_capacity_rejection():
    """Classification is driven by the evidence, not by the status line alone."""
    contradictory = _attempt(1, "capacity_rejected", completion_present=True)
    assert delivery.classify_attempt(contradictory) == "materialized"
    with pytest.raises(delivery.DeliveryError, match="classifies as"):
        _validate(_ledger(contradictory, _attempt(2, "materialized")))


def test_a_truncated_or_invalid_completion_is_final_on_its_first_outcome():
    """Truncation, invalid JSON and a schema violation all mean the model ran. One draw only."""
    produced = _attempt(1, "materialized", completion_present=True)
    assert delivery.classify_attempt(produced) == "materialized"
    with pytest.raises(delivery.DeliveryError):
        _validate(_ledger(produced, _attempt(2, "materialized")))


def test_two_materializations_are_refused():
    with pytest.raises(delivery.DeliveryError):
        _validate(_ledger(_attempt(1, "materialized"), _attempt(2, "materialized")))


def test_a_non_429_failure_may_not_be_retried():
    server_error = _attempt(1, "failed_no_completion", status=503,
                            error_body={"error": {"code": 503}})
    assert delivery.classify_attempt(server_error) == "failed_no_completion"
    with pytest.raises(delivery.DeliveryError):
        _validate(_ledger(server_error, _attempt(2, "materialized")))


# --------------------------------------------------------- attempts to hide what happened


def test_a_retry_that_changed_the_request_is_a_second_experiment():
    with pytest.raises(delivery.DeliveryError, match="different request body"):
        _validate(_ledger(
            _attempt(1, "capacity_rejected"),
            _attempt(2, "materialized", request_body_sha256="b" * 64),
        ))


def test_a_mislabelled_outcome_is_recomputed_from_its_own_evidence():
    """The runner writes this ledger, so nothing it says about itself is evidence."""
    lying = _attempt(1, "capacity_rejected", status=503, error_body={"error": {"code": 503}})
    with pytest.raises(delivery.DeliveryError, match="classifies as"):
        _validate(_ledger(lying, _attempt(2, "materialized")))


def test_a_forged_retry_permission_is_refused():
    forged = _attempt(1, "failed_ambiguous", retry_permitted_by_the_frozen_rule=True)
    with pytest.raises(delivery.DeliveryError):
        _validate(_ledger(forged, _attempt(2, "materialized")))


def test_a_declared_materialization_index_must_match_the_attempts():
    with pytest.raises(delivery.DeliveryError, match="names a materialization index"):
        _validate(_ledger(_attempt(1, "capacity_rejected"), bank_materialization_index=1))
    with pytest.raises(delivery.DeliveryError, match="place it at"):
        _validate(_ledger(
            _attempt(1, "capacity_rejected"), _attempt(2, "materialized"),
            bank_materialization_index=1,
        ))


def test_out_of_order_or_duplicated_attempt_indices_are_refused():
    with pytest.raises(delivery.DeliveryError, match="in order"):
        _validate(_ledger(_attempt(2, "capacity_rejected"), _attempt(1, "materialized")))
    with pytest.raises(delivery.DeliveryError, match="in order"):
        _validate(_ledger(_attempt(1, "capacity_rejected"), _attempt(1, "materialized")))


def test_an_attempt_that_omits_what_the_rule_is_computed_from_is_refused():
    for missing in ("completion_present", "model_execution_cannot_be_excluded", "outcome",
                    "request_body_sha256", "waited_seconds_before_this_attempt", "status"):
        attempt = _attempt(1, "materialized")
        attempt.pop(missing)
        with pytest.raises(delivery.DeliveryError, match="does not record"):
            _validate(_ledger(attempt))


# ------------------------------------------------------------------ substitution and waits


def test_a_provider_or_model_substitution_is_refused():
    with pytest.raises(delivery.DeliveryError, match="rather than the frozen"):
        _validate(_ledger(_attempt(1, "materialized", served_provider="Together")))
    with pytest.raises(delivery.DeliveryError, match="rather than the frozen"):
        _validate(_ledger(_attempt(1, "materialized", served_model="deepseek/deepseek-v3")))


def test_the_wait_between_attempts_is_the_pre_registered_one():
    with pytest.raises(delivery.DeliveryError, match="frozen interval"):
        _validate(_ledger(
            _attempt(1, "capacity_rejected"),
            _attempt(2, "materialized", waited_seconds_before_this_attempt=5),
        ))
    with pytest.raises(delivery.DeliveryError, match="waits for nothing"):
        _validate(_ledger(_attempt(1, "materialized", waited_seconds_before_this_attempt=60)))


def test_the_ledger_must_bind_the_frozen_spec():
    ledger = _ledger(_attempt(1, "materialized"), spec_commitment_sha256="d" * 64)
    with pytest.raises(delivery.DeliveryError, match="does not bind"):
        delivery.validate_delivery_ledger(
            ledger, spec_commitment_sha256="c" * 64, request_body_sha256="a" * 64
        )


def test_the_summary_is_recomputed_and_not_read_from_a_field():
    ledger = _ledger(_attempt(1, "capacity_rejected"), _attempt(2, "materialized"))
    ledger["delivery_attempts"] = 99          # a field the summary must ignore
    ledger["bank_materializations"] = 99
    summary = delivery.delivery_summary(ledger)
    assert summary["delivery_attempts"] == 2
    assert summary["bank_materializations"] == 1
    assert summary["every_attempt_sent_the_same_body"] is True
    assert summary["no_attempt_followed_a_terminal_outcome"] is True
    assert summary["no_substitution"] is True


def test_the_summary_describes_a_broken_ledger_instead_of_raising():
    """The summary is read on records that failed validation, so it may not fail on their shape.

    A phase machine that crashed while describing why a reveal is refused would take the refusal
    down with it, and the operator would see a traceback where a blocker belonged.
    """
    for broken in (
        {"schema": delivery.DELIVERY_LEDGER_SCHEMA, "attempts": {"1": {}}},
        {"schema": delivery.DELIVERY_LEDGER_SCHEMA, "attempts": ["not an attempt"]},
        {"schema": delivery.DELIVERY_LEDGER_SCHEMA, "attempts": None},
        {"schema": delivery.DELIVERY_LEDGER_SCHEMA},
    ):
        summary = delivery.delivery_summary(broken)
        assert summary["delivery_attempts"] == 0
        assert summary["bank_materializations"] == 0
        with pytest.raises(delivery.DeliveryError):
            delivery.validate_delivery_ledger(broken)
