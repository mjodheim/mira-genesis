"""M115 may relabel M114 delivery records, but may not soften their semantics."""

from __future__ import annotations

import copy

import pytest

from metamorphosis import m114_delivery, m115_delivery


def _ledger():
    return {
        "schema": m115_delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": "M115",
        "hypothesis": "H60",
        "spec_commitment_sha256": "a" * 64,
        "request_body_sha256": "b" * 64,
        "bank_materialization_index": 2,
        "attempts": [
            {
                "attempt_index": 1,
                "started_at": "2026-08-28T00:00:00Z",
                "status": 429,
                "requested_provider": "Alibaba",
                "served_provider": None,
                "requested_model": "deepseek/deepseek-v4-flash-0731",
                "served_model": None,
                "response_headers": {},
                "error_body": {"error": {"code": 429}},
                "response_sha256": "c" * 64,
                "request_body_sha256": "b" * 64,
                "completion_present": False,
                "model_execution_cannot_be_excluded": False,
                "outcome": "capacity_rejected",
                "retry_permitted_by_the_frozen_rule": True,
                "waited_seconds_before_this_attempt": 0,
            },
            {
                "attempt_index": 2,
                "started_at": "2026-08-28T00:01:00Z",
                "status": 200,
                "requested_provider": "Alibaba",
                "served_provider": "Alibaba",
                "requested_model": "deepseek/deepseek-v4-flash-0731",
                "served_model": "deepseek/deepseek-v4-flash-0731",
                "response_headers": {},
                "error_body": None,
                "response_sha256": "d" * 64,
                "request_body_sha256": "b" * 64,
                "completion_present": True,
                "model_execution_cannot_be_excluded": False,
                "outcome": "materialized",
                "retry_permitted_by_the_frozen_rule": False,
                "waited_seconds_before_this_attempt": 60,
            },
        ],
    }


def test_valid_m115_ledger_is_exactly_m114_semantics_with_new_labels():
    ledger = _ledger()
    m115_delivery.validate_delivery_ledger(
        ledger, spec_commitment_sha256="a" * 64, request_body_sha256="b" * 64
    )
    inherited = copy.deepcopy(ledger)
    inherited["schema"] = m114_delivery.DELIVERY_LEDGER_SCHEMA
    inherited["milestone"] = "M114"
    m114_delivery.validate_delivery_ledger(
        inherited, spec_commitment_sha256="a" * 64, request_body_sha256="b" * 64
    )


def test_m115_cannot_add_a_fourth_attempt():
    ledger = _ledger()
    extra = copy.deepcopy(ledger["attempts"][0])
    extra["attempt_index"] = 3
    extra["waited_seconds_before_this_attempt"] = 60
    ledger["attempts"][1]["outcome"] = "capacity_rejected"
    ledger["attempts"][1]["completion_present"] = False
    ledger["attempts"][1]["status"] = 429
    ledger["attempts"][1]["served_provider"] = None
    ledger["attempts"][1]["served_model"] = None
    ledger["attempts"][1]["retry_permitted_by_the_frozen_rule"] = True
    ledger["bank_materialization_index"] = None
    ledger["attempts"].append(extra)
    fourth = copy.deepcopy(extra)
    fourth["attempt_index"] = 4
    ledger["attempts"].append(fourth)
    with pytest.raises(m115_delivery.DeliveryError):
        m115_delivery.validate_delivery_ledger(ledger)


def test_terminal_outcome_still_cannot_be_followed():
    ledger = _ledger()
    ledger["attempts"][0]["outcome"] = "failed_ambiguous"
    ledger["attempts"][0]["model_execution_cannot_be_excluded"] = True
    ledger["attempts"][0]["retry_permitted_by_the_frozen_rule"] = False
    with pytest.raises(m115_delivery.DeliveryError, match="followed"):
        m115_delivery.validate_delivery_ledger(ledger)


def test_summary_names_inheritance_without_changing_counts():
    summary = m115_delivery.delivery_summary(_ledger())
    assert summary["schema"] == "m115-delivery-summary-v1"
    assert summary["semantics_inherited_unchanged_from"] == "M114"
    assert summary["delivery_attempts"] == 2
    assert summary["bank_materializations"] == 1
