"""Adversarial tests for the M116 terminal classifier.

The defect being corrected is precise: M115 classified terminal failures by matching the text of a
Python exception, so `invalid_json` meant "the parser raised" and nothing more -- while the frozen
plan enumerated `truncated_completion` as a distinct class that no code path could ever assign.
These tests exist mainly to stop that from being true again.
"""

from __future__ import annotations

import pytest

from metamorphosis import m116_admission as admission
from metamorphosis import m116_telemetry as telemetry
from metamorphosis import m116_terminal as terminal


def _telemetry(**overrides):
    record = {
        "schema": telemetry.TELEMETRY_SCHEMA,
        "http_status": 200,
        "finish_reason": "stop",
        "native_finish_reason": None,
        "prompt_tokens": 900,
        "completion_tokens": 41203,
        "total_tokens": 42103,
        "reasoning_tokens": 0,
        "response_bytes": 197496,
        "content_bytes": 140000,
        "content_present": True,
        "choice_count": 1,
        "generation_id": "gen-abc",
        "requested_model": "deepseek/deepseek-v4-flash-0731",
        "served_model": "deepseek/deepseek-v4-flash-0731",
        "requested_provider": "Alibaba",
        "served_provider": "Alibaba",
        "canonical_checkpoint_attested": True,
        "router_direct": True,
        "router_no_fallback": True,
        "router_one_endpoint": True,
        "router_one_attempt": True,
        "router_no_pipeline_intervention": True,
        "model_execution_evidence": True,
        "refusal_present": False,
        "response_format_enforced": None,
        "transport_failure_class": None,
    }
    record.update(overrides)
    telemetry.validate(record)
    return record


def _admission(**overrides):
    record = {name: None for name in admission.ADMISSION_FIELDS}
    record.update({
        "schema": admission.ADMISSION_SCHEMA,
        "validator_version": admission.VALIDATOR_VERSION,
        "envelope_version": admission.ENVELOPE_VERSION,
        "admitted": False, "parsed": False, "schema_valid": False,
        "payload_admissible": False, "records_emitted": 0, "carriers_enveloped": 0,
        "carriers_accepted": 0, "carriers_refused": 0, "distinct_structural_signatures": 0,
        "violation_location": "", "violation_keyword": "", "failure_stage": "content_not_json",
    })
    record.update(overrides)
    return record


# ---------------------------------------------------------------------------------------------
# The M115 defect, in both directions
# ---------------------------------------------------------------------------------------------

def test_truncation_is_never_inferred_from_a_parse_failure_alone():
    """A parse failure at an unknown finish reason must fall closed, not become truncation."""
    result = terminal.classify(_telemetry(finish_reason=None), admission=_admission())
    assert result["terminal_class"] == "unclassified_terminal"
    assert result["terminal_class"] != "truncated_completion"


def test_invalid_json_at_a_completed_finish_reason_stays_invalid_json():
    result = terminal.classify(_telemetry(finish_reason="stop"), admission=_admission())
    assert result["terminal_class"] == "invalid_json"


@pytest.mark.parametrize("reason", sorted(telemetry.BUDGET_FINISH_REASONS))
def test_explicit_budget_termination_maps_to_truncated_completion(reason: str):
    """Affirmative finish-reason evidence, and only that, may conclude truncation."""
    result = terminal.classify(_telemetry(finish_reason=reason), admission=_admission())
    assert result["terminal_class"] == "truncated_completion"
    assert result["retry_permitted_by_class"] is False


def test_truncation_outranks_the_parse_failure_it_also_causes():
    """A truncated completion also fails to parse; the parse failure must not absorb it."""
    result = terminal.classify(
        _telemetry(finish_reason="length"),
        admission=_admission(parsed=False, failure_stage="content_not_json"),
    )
    assert result["terminal_class"] == "truncated_completion"


def test_every_declared_terminal_class_is_reachable_or_explicitly_not_an_observation():
    """The M115 defect was a class no code could assign. Nothing here may be unreachable."""
    reached = {
        terminal.classify(_telemetry(transport_failure_class="TimeoutError"))["terminal_class"],
        terminal.classify(_telemetry(http_status=429, content_present=False,
                                     model_execution_evidence=False, finish_reason=None,
                                     completion_tokens=None, generation_id=None))["terminal_class"],
        terminal.classify(_telemetry(http_status=503))["terminal_class"],
        terminal.classify(_telemetry(canonical_checkpoint_attested=False))["terminal_class"],
        terminal.classify(_telemetry(refusal_present=True))["terminal_class"],
        terminal.classify(_telemetry(content_present=False))["terminal_class"],
        terminal.classify(_telemetry(finish_reason="length"), admission=_admission())["terminal_class"],
        terminal.classify(_telemetry(), admission=_admission())["terminal_class"],
        terminal.classify(_telemetry(), admission=_admission(parsed=True, schema_valid=False,
                                                             failure_stage="output_schema_violation"))["terminal_class"],
        terminal.classify(_telemetry(), binding_mismatch=True)["terminal_class"],
        terminal.classify(_telemetry(finish_reason=None), admission=_admission())["terminal_class"],
    }
    assert reached == set(terminal.TERMINAL_CLASSES)


# ---------------------------------------------------------------------------------------------
# Precedence and ambiguity
# ---------------------------------------------------------------------------------------------

def test_a_binding_mismatch_outranks_every_observation():
    result = terminal.classify(_telemetry(), admission=_admission(admitted=True, parsed=True,
                                                                  schema_valid=True,
                                                                  payload_admissible=True,
                                                                  failure_stage=""),
                               binding_mismatch=True)
    assert result["terminal_class"] == "post_validation_failure"


def test_an_ambiguous_transport_outranks_a_429():
    result = terminal.classify(_telemetry(http_status=429, transport_failure_class="ConnectionReset"))
    assert result["terminal_class"] == "ambiguous_transport"
    assert result["retry_permitted_by_class"] is False


def test_a_429_carrying_execution_evidence_is_not_the_retryable_class():
    result = terminal.classify(_telemetry(http_status=429, content_present=False,
                                          model_execution_evidence=True))
    assert result["terminal_class"] != "pre_generation_429"
    assert result["retry_permitted_by_class"] is False


def test_only_the_pre_generation_429_is_retryable():
    retryable = {
        name for name in terminal.TERMINAL_CLASSES if name in terminal.RETRYABLE_CLASSES
    }
    assert retryable == {"pre_generation_429"}


def test_a_completion_without_admission_evidence_falls_closed():
    result = terminal.classify(_telemetry(), admission=None)
    assert result["terminal_class"] == "unclassified_terminal"


def test_classification_is_deterministic_and_replayable():
    record = _telemetry(finish_reason="length")
    first = terminal.classify(record, admission=_admission())
    second = terminal.classify(dict(record), admission=_admission())
    assert first == second


def test_a_schema_violation_is_not_an_invalid_json():
    result = terminal.classify(
        _telemetry(),
        admission=_admission(parsed=True, schema_valid=False,
                             failure_stage="output_schema_violation",
                             violation_location="/properties/machines/items", violation_keyword="pattern"),
    )
    assert result["terminal_class"] == "output_schema_violation"


def test_the_classifier_refuses_telemetry_it_does_not_recognize():
    with pytest.raises(telemetry.TelemetryError):
        terminal.classify({"schema": "something-else"})
