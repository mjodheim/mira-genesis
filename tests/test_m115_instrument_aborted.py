"""Pin M115's terminal strict-JSON admission failure and closed H60 record."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from metamorphosis import m115_delivery as delivery
from metamorphosis import m115_execution as execution
from metamorphosis import m115_identity as identity
from scripts.check_m113_result import digest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments/M115"

RESULT_DIGEST = "441e1206686efcea2630aa16bb0179bff09160a3254ad8e7e6836a627dcd9b94"
REPORT_DIGEST = "082cd5d4d27f2e98e8552e91f9e9ff297222c3c11480a5e479573d8d8d435d61"
BANK_COMMITMENT = "fd37a9c2691115ef3b9286ed3903236131d0b850e9c81182abb0587e7a485d90"
SYSTEM_PROTOCOL_COMMITMENT = "f98b8d5d67eea9c83984f25f9a8b51b6ef4a69f83e789e299e2c8f5af690afa1"
REVEAL_AUTHORIZATION = "25adf4b084b6aecfddb293be6eb47774aa96f882bbc0f561ec6558d00bb972f5"
RESULT_COMMIT = "9d5c295be6140a16022045ac95a6f660aaaac629"
PREDICATES = [f"P{index}" for index in range(1, 23)]


def _load(name: str) -> dict:
    return json.loads((EXPERIMENT / name).read_text(encoding="utf-8"))


def test_the_terminal_result_and_checker_report_are_digest_pinned() -> None:
    result = _load("RESULT.json")
    report = _load("CHECK_REPORT.json")

    assert result["result_digest"] == RESULT_DIGEST
    assert digest({key: value for key, value in result.items() if key != "result_digest"}) == RESULT_DIGEST
    assert report["report_digest"] == REPORT_DIGEST
    assert digest({key: value for key, value in report.items() if key != "report_digest"}) == REPORT_DIGEST
    assert report["result_digest"] == RESULT_DIGEST
    assert report["result_commit"] == RESULT_COMMIT


def test_invalid_json_ended_the_reveal_before_qualification() -> None:
    result = _load("RESULT.json")

    assert result["reveal_occurred"] is True
    assert result["reveal_legitimate"] is True
    assert result["terminal_failure"] == "invalid_json"
    assert result["carrier_payload_parsed"] is False
    assert result["qualification_started"] is False
    assert result["scientific_retry_permitted"] is False
    assert result["verdict"] == "instrument-aborted"
    assert result["hypothesis_status"] == "untested"
    assert result["insufficient_bank_verdict_not_applied_because_no_carrier_payload_existed"] is True


def test_no_carrier_or_scientific_predicate_was_computed() -> None:
    result = _load("RESULT.json")
    report = _load("CHECK_REPORT.json")

    assert result["total_carriers"] == 0
    assert result["qualifying_carriers"] == 0
    assert result["distinct_qualifying_structures"] == 0
    assert result["minimum_bank_criteria_passed"] is False
    assert result["p1_p22"] == {name: "not_computed" for name in PREDICATES}
    assert report["computed"] == 0
    assert report["passed"] == 0
    assert report["failing"] == []
    assert report["not_computed"] == PREDICATES


def test_the_single_materialization_retains_its_runtime_identity() -> None:
    ledger = _load("DELIVERY_LEDGER.json")
    spec = _load("GENERATOR_SPEC.json")
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=spec["spec_commitment_sha256"],
        request_body_sha256=spec["canonical_request_body_sha256"],
    )
    assert len(ledger["attempts"]) == 1
    assert ledger["bank_materialization_index"] == 1
    attempt = ledger["attempts"][0]
    assert attempt["outcome"] == "materialized"
    assert attempt["identity_attestation"]["holds"] is True
    assert attempt["served_model"] == identity.REQUESTED_MODEL
    assert attempt["served_provider"] == identity.SELECTED_PROVIDER
    assert attempt["identity_attestation"]["router_attestation"]["canonical_checkpoint"] == identity.CANONICAL_CHECKPOINT


def test_the_frozen_system_and_reveal_bindings_still_hold() -> None:
    protocol = _load("SYSTEM_PROTOCOL.json")
    authorization = _load("REVEAL_AUTHORIZATION.json")
    result = _load("RESULT.json")

    execution.validate_system_protocol(protocol, root=ROOT)
    execution.validate_reveal_authorization(authorization, root=ROOT)
    assert protocol["protocol_commitment_sha256"] == SYSTEM_PROTOCOL_COMMITMENT
    assert authorization["authorization_sha256"] == REVEAL_AUTHORIZATION
    assert result["system_protocol_commitment_sha256"] == SYSTEM_PROTOCOL_COMMITMENT
    assert result["bank_commitment_sha256"] == BANK_COMMITMENT
    assert result["authorization_commit"] == "5be5afa7abb9f55ec44797a7000ca4e4518776cb"
    assert result["system_protocol_frozen_at_commit"] == "1a696e17a6ae176c837ce844891e29535d145803"


def test_the_phase_machine_is_closed_and_plaintext_is_absent() -> None:
    state = execution.readiness(ROOT)
    assert state["phase"] == "executed"
    assert state["ready_for_reveal"] is False
    assert state["revealed"] is True
    assert state["blockers"] == []
    assert not (EXPERIMENT / "GENERATION_RESPONSE.json").exists()
    assert _load("RESULT.json")["custody"] == {
        "carrier_content_printed": False,
        "plaintext_generation_response_present": False,
        "plaintext_generation_response_written_by_reveal": False,
    }


def test_independent_replay_preserved_the_same_terminal_outcome() -> None:
    replay = _load("CHECK_REPORT.json")["independent_replay"]
    assert replay == {
        "carrier_content_printed": False,
        "exit_status": 1,
        "matched_terminal_outcome": True,
        "mode": "scripts/run_m115_qualification.py --replay",
        "plaintext_generation_response_written": False,
        "terminal_failure": "invalid_json",
    }


def test_a_second_canonical_attempt_is_mechanically_refused_before_decryption() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_m115_qualification.py", "--execute"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "RESULT.json already exists; the canonical attempt is single-use" in completed.stdout


def test_the_public_outcome_preserves_the_abort_without_overclaiming() -> None:
    outcome = (EXPERIMENT / "OUTCOME.md").read_text(encoding="utf-8")
    assert "instrument-aborted" in outcome
    assert "H60" in outcome and "untested" in outcome
    assert "not an insufficient-bank result" in outcome
    assert "invalid_json" in outcome
    assert "No generality or completion gate moved" in outcome
