"""Adversarial tests for M116 machine-only pre-seal admission and the one-shot rule.

These tests construct synthetic completions locally. They make no network call, send no qualifying
input, create no bank and never read an M115 sealed artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m116_admission as admission
from metamorphosis import m116_materialization as materialization
from metamorphosis import m116_telemetry as telemetry
from metamorphosis.blind_bank_protocol import sha256_hex

ROOT = Path(__file__).resolve().parents[1]
NONCE = "a" * 64


def _schema():
    return json.loads((ROOT / "experiments" / "M115" / "OUTPUT_SCHEMA.json").read_text("utf-8"))


def _machine(index: int) -> dict:
    return {
        "surface": {"kind": ["json_object", "text_line", "packed_digits", "json_array"][index % 4],
                    "ok_token": "ok%d" % (index % 90), "error_token": "er%d" % (index % 90),
                    "field_separator": [" ", ":", ",", ";", "|"][index % 5],
                    "pair_separator": ["=", "-", "/"][index % 3],
                    "action_key": "act_%d" % (index % 90),
                    "argument_key": "arg_%d" % (index % 90),
                    "status_key": "st_%d" % (index % 90)},
        "cells": [{"name": "c%d" % (index % 90), "size": 2 + (index % 3)}],
        "initial": [0],
        "visible": [True],
        "errors": ["e%d" % (index % 90)],
        "actions": [
            {"name": "a%d" % (index % 90), "arity": 0, "arg_size": 0, "guard": [],
             "effect": [{"cell": 0, "mode": "set", "operand": 1}], "error": "e%d" % (index % 90)},
            {"name": "b%d" % (index % 90), "arity": 0, "arg_size": 0, "guard": [],
             "effect": [{"cell": 0, "mode": "add", "operand": 1}], "error": "e%d" % (index % 90)},
        ],
    }


def _response(content: str) -> bytes:
    return json.dumps({
        "body": {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
    }).encode("utf-8")


def _valid_completion(count: int = 24) -> str:
    return json.dumps({"machines": [_machine(i) for i in range(count)]})


def _evaluate(content: str):
    return admission.evaluate(_response(content), output_schema=_schema(), bank_nonce=NONCE)


# ---------------------------------------------------------------------------------------------
# The envelope, and the defect it corrects
# ---------------------------------------------------------------------------------------------

def test_a_well_formed_completion_is_admitted_end_to_end():
    """The frozen generator emits `machines`; the frozen host wants an enveloped payload.

    Before M116 nothing joined those two, so a perfect completion would still have been refused.
    """
    record = _evaluate(_valid_completion())
    admission.validate_record(record)
    assert record["admitted"] is True
    assert record["parsed"] is True and record["schema_valid"] is True
    assert record["payload_admissible"] is True
    assert record["carriers_accepted"] == 24
    assert record["carriers_refused"] == 0
    assert record["failure_stage"] == ""


def test_the_envelope_is_positional_and_adds_nothing():
    completion = json.loads(_valid_completion(3))
    payload = admission.envelope_payload(completion, NONCE)
    for index, machine in enumerate(completion["machines"]):
        entry = dict(payload["carriers"][index])
        entry.pop("carrier_ref")
        assert entry == machine


def test_the_envelope_cannot_rescue_a_malformed_machine():
    completion = json.loads(_valid_completion(3))
    completion["machines"][1] = {"surface": {}}
    payload = admission.envelope_payload(completion, NONCE)
    assert len(payload["carriers"]) == 3
    # The broken machine is enveloped and then refused downstream -- counted, never corrected.
    assert "cells" not in payload["carriers"][1]


# ---------------------------------------------------------------------------------------------
# Purity: the validator may not transform anything
# ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "content",
    [
        '```json\n{"machines":[]}\n```',
        'Here is the JSON you asked for:\n{"machines":[]}',
        '{"machines":[',
        '{"machines":[]}trailing',
        "{'machines': []}",
    ],
)
def test_admission_never_repairs_fences_prose_or_truncation(content: str):
    record = _evaluate(content)
    assert record["admitted"] is False
    assert record["parsed"] is False
    assert record["failure_stage"] == "content_not_json"


def test_admission_does_not_transform_the_completion_bytes():
    content = _valid_completion(2)
    raw = _response(content)
    before = sha256_hex(raw)
    record = admission.evaluate(raw, output_schema=_schema(), bank_nonce=NONCE)
    assert sha256_hex(raw) == before
    assert record["raw_response_sha256"] == before
    assert record["carrier_completion_sha256"] == sha256_hex(content.encode("utf-8"))


def test_successful_admission_binds_the_exact_bytes_before_sealing():
    content = _valid_completion(4)
    record = admission.evaluate(_response(content), output_schema=_schema(), bank_nonce=NONCE)
    assert record["carrier_completion_sha256"] == sha256_hex(content.encode("utf-8"))
    assert record["payload_sha256"] is not None
    assert record["output_schema_sha256"] is not None
    assert record["bank_nonce_sha256"] == sha256_hex(NONCE.encode("ascii"))


def test_the_admission_record_carries_no_carrier_content():
    record = _evaluate(_valid_completion())
    serialized = json.dumps(record, sort_keys=True)
    for token in ("machines", "surface", "ok_token", "json_object", "act_0"):
        assert token not in serialized


def test_a_schema_violation_names_a_location_never_a_value():
    completion = json.loads(_valid_completion(2))
    completion["machines"][0]["surface"]["ok_token"] = "NOT A TOKEN"
    record = _evaluate(json.dumps(completion))
    assert record["schema_valid"] is False
    assert record["violation_keyword"] == "pattern"
    assert "NOT A TOKEN" not in json.dumps(record)
    assert record["violation_location"].endswith("ok_token")


# ---------------------------------------------------------------------------------------------
# Binding between pre-seal and post-reveal
# ---------------------------------------------------------------------------------------------

def test_pre_and_post_seal_records_must_agree():
    content = _valid_completion(3)
    preseal = admission.evaluate(_response(content), output_schema=_schema(), bank_nonce=NONCE)
    postreveal = admission.evaluate(_response(content), output_schema=_schema(), bank_nonce=NONCE)
    holds, differing = admission.binding_matches(preseal, postreveal)
    assert holds is True and differing == []


def test_a_substituted_completion_breaks_the_binding():
    preseal = admission.evaluate(_response(_valid_completion(3)), output_schema=_schema(),
                                 bank_nonce=NONCE)
    postreveal = admission.evaluate(_response(_valid_completion(4)), output_schema=_schema(),
                                    bank_nonce=NONCE)
    holds, differing = admission.binding_matches(preseal, postreveal)
    assert holds is False
    assert "carrier_completion_sha256" in differing


def test_the_record_allowlist_is_enforced():
    record = _evaluate(_valid_completion(2))
    record["recovered_carrier"] = {"machines": []}
    with pytest.raises(admission.AdmissionError, match="outside the allowlist"):
        admission.validate_record(record)


def test_admission_refuses_an_uncommitted_nonce():
    with pytest.raises(admission.AdmissionError):
        admission.evaluate(_response("{}"), output_schema=_schema(), bank_nonce="short")


# ---------------------------------------------------------------------------------------------
# The one-shot rule
# ---------------------------------------------------------------------------------------------

def _executed_telemetry(**overrides):
    record = telemetry.extract(
        status=200,
        body={"choices": [{"finish_reason": overrides.pop("finish_reason", "stop"),
                           "message": {"content": overrides.pop("content", "x")}}],
              "usage": {"completion_tokens": 41203,
                        "completion_tokens_details": {"reasoning_tokens": 0}},
              "model": "deepseek/deepseek-v4-flash-0731", "provider": "Alibaba"},
        response_bytes=1000,
        headers={"x-generation-id": "gen-abc"},
        identity_attestation={"router_attestation": {"checks": {
            "selected_checkpoint_exact": True, "direct_strategy": True,
            "no_fallback_attested": True, "one_selected_endpoint": True,
            "one_router_attempt": True, "no_pipeline_intervention": True}}},
        requested_model="deepseek/deepseek-v4-flash-0731", requested_provider="Alibaba",
    )
    record.update(overrides)
    return record


def test_a_failed_admission_consumes_the_opportunity_and_forbids_a_redraw():
    record = _executed_telemetry()
    failed = _evaluate('{"machines":[')
    decision = materialization.decide(record, failed)
    assert decision["scientific_opportunity_consumed"] is True
    assert decision["physical_retry_permitted"] is False
    assert decision["content_dependent_redraw_permitted"] is False
    assert decision["repair_permitted"] is False
    assert decision["selection_among_completions_permitted"] is False
    assert decision["bank_materialized"] is False
    assert decision["may_seal"] is False
    assert decision["verdict"] == "instrument-aborted"
    assert decision["hypothesis_status"] == "untested"
    materialization.assert_no_redraw_after(decision)


def test_a_schema_failure_can_never_trigger_a_retry():
    completion = json.loads(_valid_completion(2))
    completion["machines"][0]["surface"]["kind"] = "not_a_kind"
    decision = materialization.decide(_executed_telemetry(),
                                      _evaluate(json.dumps(completion)))
    assert decision["terminal_class"] == "output_schema_violation"
    assert decision["physical_retry_permitted"] is False


def test_a_truncated_completion_can_never_trigger_a_retry():
    decision = materialization.decide(_executed_telemetry(finish_reason="length"),
                                      _evaluate('{"machines":['))
    assert decision["terminal_class"] == "truncated_completion"
    assert decision["physical_retry_permitted"] is False


def test_a_successful_admission_authorizes_exactly_one_seal():
    decision = materialization.decide(_executed_telemetry(), _evaluate(_valid_completion()))
    assert decision["bank_materialized"] is True
    assert decision["may_seal"] is True
    assert decision["scientific_opportunity_consumed"] is True
    assert decision["physical_retry_permitted"] is False
    assert materialization.MAX_BANK_MATERIALIZATIONS == 1


def test_only_a_pre_generation_429_without_execution_evidence_may_retry():
    clean = telemetry.extract(status=429, body={}, response_bytes=120,
                              requested_model="deepseek/deepseek-v4-flash-0731",
                              requested_provider="Alibaba")
    decision = materialization.decide(clean, None)
    assert decision["terminal_class"] == "pre_generation_429"
    assert decision["scientific_opportunity_consumed"] is False
    assert decision["physical_retry_permitted"] is True

    dirty = telemetry.extract(status=429,
                              body={"usage": {"completion_tokens": 12}},
                              response_bytes=120,
                              headers={"x-generation-id": "gen-xyz"},
                              requested_model="deepseek/deepseek-v4-flash-0731",
                              requested_provider="Alibaba")
    spent = materialization.decide(dirty, None)
    assert spent["scientific_opportunity_consumed"] is True
    assert spent["physical_retry_permitted"] is False
