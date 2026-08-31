"""M116 may not touch the closed M113/M114/M115 record.

M115 is terminal `instrument-aborted` with H60 untested after a completion that failed strict-JSON
admission. M116 corrects the instrument prospectively; it does not reinterpret, repair, retry or
relabel its predecessor. These tests pin that boundary against the new apparatus.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis import m116_admission as admission
from metamorphosis import m116_materialization as materialization
from metamorphosis import m116_telemetry as telemetry
from metamorphosis import m116_terminal as terminal

ROOT = Path(__file__).resolve().parents[1]
M116_MODULES = (
    "metamorphosis/m116_admission.py",
    "metamorphosis/m116_materialization.py",
    "metamorphosis/m116_schema.py",
    "metamorphosis/m116_stress_schema.py",
    "metamorphosis/m116_telemetry.py",
    "metamorphosis/m116_terminal.py",
)


def test_the_m115_result_is_unchanged_and_still_instrument_aborted():
    result = json.loads((ROOT / "experiments" / "M115" / "RESULT.json").read_text("utf-8"))
    assert result["verdict"] == "instrument-aborted"
    assert result["hypothesis"] == "H60"
    assert result["hypothesis_status"] == "untested"
    assert result["terminal_failure"] == "invalid_json"
    assert result["qualifying_carriers"] == 0
    assert all(value == "not_computed" for value in result["p1_p22"].values())


def test_no_m116_module_reads_the_sealed_m115_bank():
    for relative in M116_MODULES:
        source = (ROOT / relative).read_text("utf-8")
        assert "SEALED_BANK" not in source
        assert ".gpg" not in source
        assert "GENERATION_RESPONSE" not in source
        assert "REVEAL_AUTHORIZATION" not in source


def test_no_m116_module_writes_into_the_closed_experiment_directories():
    for relative in M116_MODULES:
        tree = ast.parse((ROOT / relative).read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("write_text", "write_bytes",
                                                                 "unlink", "replace"):
                pytest.fail("%s performs a filesystem write" % relative)


def test_the_m116_classifier_cannot_relabel_the_m115_observation():
    """M115 preserved no finish reason, so M116's classifier must refuse to reinterpret it."""
    without_finish_reason = telemetry.extract(
        status=200,
        body={"choices": [{"message": {"content": "not json"}}]},
        response_bytes=197496,
        requested_model="deepseek/deepseek-v4-flash-0731",
        requested_provider="Alibaba",
        identity_attestation={"router_attestation": {"checks": {
            "selected_checkpoint_exact": True, "direct_strategy": True,
            "no_fallback_attested": True, "one_selected_endpoint": True,
            "one_router_attempt": True, "no_pipeline_intervention": True}}},
    )
    blank = {name: None for name in admission.ADMISSION_FIELDS}
    blank.update({"schema": admission.ADMISSION_SCHEMA,
                  "validator_version": admission.VALIDATOR_VERSION,
                  "envelope_version": admission.ENVELOPE_VERSION,
                  "admitted": False, "parsed": False, "schema_valid": False,
                  "payload_admissible": False, "records_emitted": 0, "carriers_enveloped": 0,
                  "carriers_accepted": 0, "carriers_refused": 0,
                  "distinct_structural_signatures": 0, "violation_location": "",
                  "violation_keyword": "", "failure_stage": "content_not_json"})
    result = terminal.classify(without_finish_reason, admission=blank)
    assert result["terminal_class"] == "unclassified_terminal"
    assert result["terminal_class"] != "truncated_completion"


def test_m116_never_authorizes_a_second_scientific_draw():
    source = (ROOT / "metamorphosis" / "m116_materialization.py").read_text("utf-8")
    assert "first schema-valid completion wins" in source.lower()
    assert materialization.MAX_BANK_MATERIALIZATIONS == 1


def test_no_plaintext_carrier_output_is_persisted_by_the_new_apparatus():
    assert not (ROOT / "experiments" / "M115" / "GENERATION_RESPONSE.json").exists()
    assert not (ROOT / "experiments" / "M116" / "GENERATION_RESPONSE.json").exists()
    for path in (ROOT / "experiments" / "M116").iterdir():
        if path.suffix == ".json":
            body = path.read_text("utf-8")
            for token in ("machines", "surface", "ok_token"):
                assert token not in body


def test_no_h61_freeze_or_bank_exists_yet():
    directory = ROOT / "experiments" / "M116"
    for absent in ("ANALYSIS_PLAN.json", "GENERATOR_SPEC.json", "DELIVERY_LEDGER.json",
                   "SEALED_BANK.json.gpg", "PUBLIC_BANK_COMMITMENT.json", "RESULT.json",
                   "REVEAL_AUTHORIZATION.json"):
        assert not (directory / absent).exists(), "%s must not exist before freeze" % absent
