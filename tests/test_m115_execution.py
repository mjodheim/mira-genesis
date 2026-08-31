"""M115's post-seal phase machine without revealing the materialized carrier bank."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m115_carrier_bank as bank
from metamorphosis import m115_execution as execution
from metamorphosis.blind_bank_protocol import canonical_bytes
from scripts import check_m114_result as predecessor_checker
from scripts import check_m115_result as checker
from scripts import run_m115_qualification as runner


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / bank.EXPERIMENT_DIRECTORY


def _load(name: str) -> dict:
    return json.loads((EXPERIMENT / name).read_text(encoding="utf-8"))


def _system_protocol() -> dict:
    path = ROOT / execution.SYSTEM_PROTOCOL_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else execution.build_system_protocol(ROOT)


def _frozen_system_commit() -> str:
    return _load("REVEAL_AUTHORIZATION.json")["system_protocol_frozen_at_commit"]


def test_the_tested_system_freeze_is_complete_and_valid() -> None:
    protocol = _system_protocol()
    execution.validate_system_protocol(
        protocol,
        root=ROOT,
        tested_system_commit=_frozen_system_commit(),
    )
    assert protocol["bank_content_known_at_freeze"] is False
    assert protocol["predicate_contract"]["retains_m114_computations"] == [
        "P%d" % index for index in range(1, 23)
    ]
    assert protocol["predicate_contract"]["newly_versioned_for_m115"] == []
    assert set(protocol["tested_system_digests"]) == set(execution.TESTED_SYSTEM_PATHS)


def test_the_tested_system_freeze_detects_one_changed_digest() -> None:
    protocol = copy.deepcopy(_system_protocol())
    first = execution.TESTED_SYSTEM_PATHS[0]
    protocol["tested_system_digests"][first] = "0" * 64
    protocol["protocol_commitment_sha256"] = execution.system_protocol_commitment(protocol)
    with pytest.raises(execution.ExecutionError, match="tested system changed"):
        execution.validate_system_protocol(
            protocol,
            root=ROOT,
            tested_system_commit=_frozen_system_commit(),
        )


def test_readiness_never_skips_a_phase() -> None:
    report = execution.readiness(ROOT)
    assert report["phase"] in execution.PHASES
    assert report["ready_for_reveal"] is (report["phase"] == "reveal_authorized" and not report["blockers"])
    if report["phase"] == "generated_sealed":
        assert "missing SYSTEM_PROTOCOL.json" in report["blockers"]


def test_the_committed_response_parser_recomputes_identity_without_carrier_inspection() -> None:
    ledger = _load("DELIVERY_LEDGER.json")
    attempt = ledger["attempts"][ledger["bank_materialization_index"] - 1]
    attestation = attempt["identity_attestation"]
    body = {
        "model": attempt["served_model"],
        "provider": attempt["served_provider"],
        "openrouter_metadata": attestation["safe_router_metadata"],
        "choices": [{"message": {"content": "{}"}}],
    }
    response = {
        "schema": "m115-generation-response-v1",
        "milestone": "M115",
        "hypothesis": "H60",
        "spec_commitment_sha256": ledger["spec_commitment_sha256"],
        "delivery_attempt_index": attempt["attempt_index"],
        "delivery_attempts_made": len(ledger["attempts"]),
        "request_body_sha256": ledger["request_body_sha256"],
        "status": attempt["status"],
        "served_model": attempt["served_model"],
        "served_provider": attempt["served_provider"],
        "runtime_identity_attestation": attestation,
        "started_at": attempt["started_at"],
        "finished_at": attempt["finished_at"],
        "body": body,
    }
    parsed, recomputed = runner._parse_committed_response(canonical_bytes(response))
    assert parsed == response
    assert recomputed == attestation
    assert recomputed["holds"] is True


def test_m115_reuses_every_m114_predicate_computation() -> None:
    result = json.loads((ROOT / "experiments/M114/DEVELOPMENT_RUN.json").read_text(encoding="ascii"))
    predecessor_report = predecessor_checker.check(copy.deepcopy(result))

    ledger = _load("DELIVERY_LEDGER.json")
    attempt = ledger["attempts"][ledger["bank_materialization_index"] - 1]
    spec = _load("GENERATOR_SPEC.json")
    result.update(
        {
            "delivery_ledger": ledger,
            "physical_delivery_attempts": len(ledger["attempts"]),
            "bank_materializations": 1,
            "runtime_identity_attestation": attempt["identity_attestation"],
            "frozen_instrument": {
                "spec_commitment_sha256": spec["spec_commitment_sha256"],
                "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
                "model": spec["generator_identity"]["model"],
                "canonical_checkpoint": spec["generator_identity"]["canonical_checkpoint"],
                "identity_semantics": spec["generator_identity"]["identity_semantics"],
                "provider": spec["generator_identity"]["provider"],
                "routing": spec["routing"],
            },
        }
    )
    report = checker.check(result)
    assert report["conditions"] == predecessor_report["conditions"]
    assert report["predicate_provenance"]["newly_versioned_for_m115"] == []
    assert report["runtime_identity"]["holds"] is True
