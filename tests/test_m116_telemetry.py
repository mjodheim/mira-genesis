"""Adversarial tests for the M116 non-carrier telemetry allowlist and read barrier.

Nothing here touches the network, a bank, or any M115 artifact.
"""

from __future__ import annotations

import pytest

from metamorphosis import m116_telemetry as telemetry


def _body(**overrides):
    body = {
        "choices": [{"finish_reason": "stop", "message": {"content": '{"machines":[]}'}}],
        "usage": {
            "prompt_tokens": 900,
            "completion_tokens": 41203,
            "total_tokens": 42103,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": "Alibaba",
    }
    body.update(overrides)
    return body


def _extract(**overrides):
    kwargs = {
        "status": 200,
        "body": _body(),
        "response_bytes": 197496,
        "headers": {"x-generation-id": "gen-1788105857-RrXbTGro"},
        "requested_model": "deepseek/deepseek-v4-flash-0731",
        "requested_provider": "Alibaba",
    }
    kwargs.update(overrides)
    return telemetry.extract(**kwargs)


def test_the_evidence_m115_discarded_now_survives():
    record = _extract()
    assert record["finish_reason"] == "stop"
    assert record["completion_tokens"] == 41203
    assert record["prompt_tokens"] == 900
    assert record["total_tokens"] == 42103
    assert record["reasoning_tokens"] == 0
    assert record["response_bytes"] == 197496
    assert record["generation_id"] == "gen-1788105857-RrXbTGro"
    assert record["model_execution_evidence"] is True


def test_carrier_content_never_reaches_telemetry():
    secret = '{"machines":[{"surface":{"ok_token":"tell_me"}}]}'
    record = _extract(body=_body(choices=[{"finish_reason": "stop",
                                           "message": {"content": secret}}]))
    telemetry.assert_no_carrier_content(record)
    serialized = repr(sorted(record.items()))
    assert "machines" not in serialized
    assert "tell_me" not in serialized
    # Only the *length* of the completion survives, never a byte of it.
    assert record["content_bytes"] == len(secret.encode("utf-8"))


def test_the_read_barrier_refuses_containers_and_long_strings():
    record = _extract()
    record["finish_reason"] = "x" * 200
    with pytest.raises(telemetry.TelemetryError):
        telemetry.assert_no_carrier_content(record)


def test_the_allowlist_rejects_unexpected_fields():
    record = _extract()
    record["provider_error_message"] = "rate limited for key sk-or-v1-abc"
    with pytest.raises(telemetry.TelemetryError, match="outside the allowlist"):
        telemetry.validate(record)


def test_the_allowlist_rejects_omitted_fields():
    record = _extract()
    del record["finish_reason"]
    with pytest.raises(telemetry.TelemetryError, match="omits allowlisted"):
        telemetry.validate(record)


@pytest.mark.parametrize(
    "value",
    [
        "rate limited: organization org_9f3 exceeded quota",
        "Bearer sk-or-v1-0123456789abcdef",
        "stop\nx-api-key: leaked",
        " ",
    ],
)
def test_free_text_is_refused_in_token_fields(value: str):
    record = _extract()
    record["finish_reason"] = value
    with pytest.raises(telemetry.TelemetryError, match="free text is refused"):
        telemetry.validate(record)


def test_free_text_from_the_endpoint_is_dropped_rather_than_recorded():
    # A provider that returns prose where a token belongs must produce None, not the prose.
    record = _extract(body=_body(choices=[{"finish_reason": "stopped early, quota for org_9f3",
                                           "message": {"content": "{}"}}]))
    assert record["finish_reason"] is None
    telemetry.assert_no_carrier_content(record)


def test_a_refusal_is_recorded_only_on_structural_evidence():
    prose = _extract(body=_body(choices=[{"finish_reason": "stop",
                                          "message": {"content": "I cannot help with that."}}]))
    assert prose["refusal_present"] is False

    structural = _extract(body=_body(choices=[{"finish_reason": "stop",
                                               "message": {"content": "x", "refusal": "policy"}}]))
    assert structural["refusal_present"] is True

    by_reason = _extract(body=_body(choices=[{"finish_reason": "content_filter",
                                              "message": {"content": "x"}}]))
    assert by_reason["refusal_present"] is True


def test_execution_evidence_survives_an_empty_completion():
    record = _extract(body=_body(choices=[{"finish_reason": "length", "message": {"content": ""}}]))
    assert record["content_present"] is False
    assert record["model_execution_evidence"] is True


def test_a_transport_failure_carries_no_status():
    record = _extract(status=None, body=None, response_bytes=None,
                      transport_failure_class="TimeoutError")
    assert record["http_status"] is None
    assert record["transport_failure_class"] == "TimeoutError"
    telemetry.assert_no_carrier_content(record)
