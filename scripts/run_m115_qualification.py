"""Execute or independently replay the single authorized M115/H60 qualification.

The ciphertext is decrypted to process memory only.  Its exact plaintext digest is verified before
JSON parsing, the materialized runtime identity is recomputed, and the carrier payload is handed to
M113's unchanged scientific runner under its live network guard.  No decrypted response or bank is
ever written as an intermediate file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m113_carrier_bank as scientific_bank  # noqa: E402
from metamorphosis import m113_evaluator as evaluator  # noqa: E402
from metamorphosis import m115_carrier_bank as bank  # noqa: E402
from metamorphosis import m115_delivery as delivery  # noqa: E402
from metamorphosis import m115_execution as execution  # noqa: E402
from metamorphosis import m115_identity as identity  # noqa: E402
from metamorphosis import m115_sealing as sealing  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts.run_m113_qualification import canonical_json, digest, run_bank  # noqa: E402


RESULT_PATH = ROOT / execution.RESULT_PATH
PLAN_PATH = ROOT / bank.ANALYSIS_PLAN_PATH
SPEC_PATH = ROOT / bank.GENERATOR_SPEC_PATH
LEDGER_PATH = ROOT / bank.DELIVERY_LEDGER_PATH
COMMITMENT_PATH = ROOT / bank.BANK_COMMITMENT_PATH
SEALED_PATH = ROOT / bank.SEALED_BANK_PATH
PROTOCOL_PATH = ROOT / execution.SYSTEM_PROTOCOL_PATH
AUTHORIZATION_PATH = ROOT / execution.REVEAL_AUTHORIZATION_PATH
PASSPHRASE_VARIABLE = "M115_BANK_SEAL_PASSPHRASE"


class QualificationError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise QualificationError("cannot read %s: %s" % (path.relative_to(ROOT), exc))
    if not isinstance(value, dict):
        raise QualificationError("%s is not a JSON object" % path.relative_to(ROOT))
    return value


def _delivery_ledger() -> dict[str, Any]:
    ledger = _load(LEDGER_PATH)
    spec = _load(SPEC_PATH)
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=spec.get("spec_commitment_sha256"),
        request_body_sha256=spec.get("canonical_request_body_sha256"),
    )
    return ledger


def bank_delivery() -> dict[str, Any]:
    ledger = _delivery_ledger()
    summary = delivery.delivery_summary(ledger)
    summary["ledger_sha256"] = delivery.ledger_digest(ledger)
    summary["ledger_violates_the_frozen_rule"] = None
    return summary


def physical_delivery_attempts() -> int:
    return len(_delivery_ledger()["attempts"])


def bank_materializations() -> int:
    return int(bank_delivery()["bank_materializations"])


def model_execution_evidence() -> list[dict[str, Any]]:
    return [
        {
            "attempt_index": attempt.get("attempt_index"),
            "status": attempt.get("status"),
            "completion_present": attempt.get("completion_present"),
            "model_execution_cannot_be_excluded": attempt.get(
                "model_execution_cannot_be_excluded"
            ),
            "outcome": attempt.get("outcome"),
            "response_sha256": attempt.get("response_sha256"),
            "identity_attestation_holds": (
                (attempt.get("identity_attestation") or {}).get("holds")
            ),
        }
        for attempt in _delivery_ledger()["attempts"]
        if isinstance(attempt, Mapping)
    ]


def frozen_instrument() -> dict[str, Any]:
    spec = _load(SPEC_PATH)
    generator = spec.get("generator_identity") or {}
    return {
        "spec_commitment_sha256": spec.get("spec_commitment_sha256"),
        "canonical_request_body_sha256": spec.get("canonical_request_body_sha256"),
        "model": generator.get("model"),
        "canonical_checkpoint": generator.get("canonical_checkpoint"),
        "identity_semantics": generator.get("identity_semantics"),
        "provider": generator.get("provider"),
        "routing": spec.get("routing"),
    }


def _decrypt_generation_response() -> bytes:
    passphrase = os.environ.get(PASSPHRASE_VARIABLE, "")
    if not passphrase:
        raise QualificationError("%s is unavailable" % PASSPHRASE_VARIABLE)
    if shutil.which("gpg") is None:
        raise QualificationError("gpg is unavailable")
    completed = subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase-fd",
            "0",
            "--decrypt",
            str(SEALED_PATH),
        ],
        input=(passphrase + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    passphrase = ""
    if completed.returncode != 0 or not completed.stdout:
        raise QualificationError("gpg failed to decrypt the sealed M115 response")
    commitment = _load(COMMITMENT_PATH)
    if len(completed.stdout) != commitment.get("generation_response_bytes"):
        raise QualificationError("decrypted generation-response size differs from its commitment")
    if sha256_hex(completed.stdout) != commitment.get("generation_response_sha256"):
        raise QualificationError("decrypted generation-response digest differs from its commitment")
    return completed.stdout


def _materialized_attempt(ledger: Mapping[str, Any]) -> Mapping[str, Any]:
    attempts = ledger.get("attempts")
    materialized = [
        attempt
        for attempt in attempts or []
        if isinstance(attempt, Mapping) and attempt.get("outcome") == "materialized"
    ]
    if len(materialized) != 1:
        raise QualificationError("exactly one materialized attempt is required")
    if ledger.get("bank_materialization_index") != materialized[0].get("attempt_index"):
        raise QualificationError("the ledger materialization index drifted")
    return materialized[0]


def _parse_committed_response(raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        response = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise QualificationError("the committed generation response is not JSON") from exc
    if not isinstance(response, dict) or response.get("schema") != "m115-generation-response-v1":
        raise QualificationError("the committed generation response schema drifted")
    if response.get("milestone") != bank.MILESTONE or response.get("hypothesis") != bank.HYPOTHESIS:
        raise QualificationError("the committed generation response belongs to another experiment")

    spec = _load(SPEC_PATH)
    ledger = _delivery_ledger()
    attempt = _materialized_attempt(ledger)
    expected = {
        "spec_commitment_sha256": spec.get("spec_commitment_sha256"),
        "request_body_sha256": spec.get("canonical_request_body_sha256"),
        "delivery_attempt_index": attempt.get("attempt_index"),
        "delivery_attempts_made": len(ledger["attempts"]),
        "status": attempt.get("status"),
        "served_model": attempt.get("served_model"),
        "served_provider": attempt.get("served_provider"),
        "started_at": attempt.get("started_at"),
        "finished_at": attempt.get("finished_at"),
    }
    drifted = sorted(key for key, value in expected.items() if response.get(key) != value)
    if drifted:
        raise QualificationError("generation response provenance drifted: %s" % ", ".join(drifted))
    body = response.get("body")
    if not isinstance(body, dict):
        raise QualificationError("the committed response carries no body")
    attestation = identity.attest_completion_response(body)
    if attestation.get("holds") is not True:
        raise QualificationError("runtime identity no longer attests the canonical checkpoint")
    if response.get("runtime_identity_attestation") != attestation:
        raise QualificationError("response identity attestation does not match its current body")
    if attempt.get("identity_attestation") != attestation:
        raise QualificationError("response identity attestation does not match the delivery ledger")
    return response, attestation


def _extract_payload(response: Mapping[str, Any]) -> dict[str, Any]:
    body = response.get("body")
    choices = body.get("choices") if isinstance(body, Mapping) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], Mapping):
        raise QualificationError("the committed response does not carry exactly one choice")
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, Mapping) else None
    if not isinstance(content, str) or not content.strip():
        raise QualificationError("the committed response carries no completion content")
    try:
        payload = json.loads(content)
    except ValueError as exc:
        raise QualificationError("the materialized completion is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise QualificationError("the materialized completion is not a JSON object")
    return payload


def _canonical_result() -> dict[str, Any]:
    plan = _load(PLAN_PATH)
    bank.validate_analysis_plan(plan, root=ROOT)
    protocol = _load(PROTOCOL_PATH)
    execution.validate_system_protocol(protocol, root=ROOT)
    authorization = _load(AUTHORIZATION_PATH)
    execution.validate_reveal_authorization(authorization, root=ROOT)
    commitment = _load(COMMITMENT_PATH)
    sealing.validate_public_commitment(commitment, root=ROOT)

    raw = _decrypt_generation_response()
    response, attestation = _parse_committed_response(raw)
    payload = _extract_payload(response)
    acceptance = scientific_bank.validate_carrier_bank_payload(payload)
    carriers = acceptance["carriers"]
    result = run_bank(
        carriers,
        payload["bank_nonce"],
        requested_carrier_count=int(plan["requested_carrier_count"]),
        minimum_qualifying=int(plan["minimum_qualifying_carriers"]),
        minimum_distinct_structures=int(plan["minimum_distinct_qualifying_structures"]),
        session_budget=int(plan["session_budget"]),
    )

    # The inherited runner sees only schema-valid carriers.  Restore the complete frozen
    # records -> carriers -> schema-valid cardinality chain from the acceptance report.
    result["cardinality"] = evaluator.cardinality_report(
        requested_carrier_count=int(plan["requested_carrier_count"]),
        records_emitted=int(acceptance["records_emitted"]),
        carriers_enveloped=int(acceptance["carriers_enveloped"]),
        schema_valid_carriers=int(acceptance["schema_valid_carriers"]),
        qualifying_carriers=int(result["qualifying_carriers"]),
        minimum_qualifying=int(plan["minimum_qualifying_carriers"]),
        distinct_qualifying_structures=int(
            result["structural_distinctness"]["distinct_qualifying_structures"]
        ),
        minimum_distinct_structures=int(plan["minimum_distinct_qualifying_structures"]),
    )

    public_acceptance = {key: value for key, value in acceptance.items() if key != "carriers"}
    ledger = _delivery_ledger()
    result.update(
        {
            "schema": "m115-result-v1",
            "milestone": bank.MILESTONE,
            "hypothesis": bank.HYPOTHESIS,
            "filiation": dict(bank.PLAN_FILIATION),
            "development": False,
            "is_a_canonical_attempt": True,
            "plan_commitment_sha256": plan["plan_commitment_sha256"],
            "spec_commitment_sha256": protocol["spec_commitment_sha256"],
            "system_protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
            "reveal_authorization_sha256": authorization["authorization_sha256"],
            "bank_commitment_sha256": commitment["commitment_sha256"],
            "ciphertext_sha256": commitment["ciphertext_sha256"],
            "generation_response_sha256": commitment["generation_response_sha256"],
            "runtime_identity_attestation": attestation,
            "bank_acceptance": public_acceptance,
            "physical_delivery_attempts": physical_delivery_attempts(),
            "bank_materializations": bank_materializations(),
            "model_execution_evidence": model_execution_evidence(),
            "delivery_ledger": ledger,
            "frozen_instrument": frozen_instrument(),
            "bank_delivery": bank_delivery(),
            "decryption_custody": {
                "plaintext_generation_response_written_to_disk": False,
                "decrypted_in_process_memory_only": True,
                "carrier_content_printed_by_runner": False,
            },
        }
    )
    result["result_digest"] = digest({key: value for key, value in result.items() if key != "result_digest"})
    # Release large plaintext references before the only repository write.
    del payload
    del response
    del raw
    return result


def _print_summary(result: Mapping[str, Any], *, replay: bool) -> None:
    cardinality = result.get("cardinality") or {}
    print("M115 canonical %s complete" % ("replay" if replay else "qualification"))
    print("result digest: %s" % result.get("result_digest"))
    print("physical delivery attempts: %s" % result.get("physical_delivery_attempts"))
    print("bank materializations: %s" % result.get("bank_materializations"))
    print("records emitted: %s" % cardinality.get("records_emitted"))
    print("schema-valid carriers: %s" % cardinality.get("schema_valid_carriers"))
    print("qualifying carriers: %s" % cardinality.get("qualifying_carriers"))
    print("distinct qualifying structures: %s" % cardinality.get("distinct_qualifying_structures"))
    print("carrier content printed: false")


def execute() -> int:
    if RESULT_PATH.exists():
        raise QualificationError("RESULT.json already exists; the canonical attempt is single-use")
    state = execution.readiness(ROOT)
    if not state.get("ready_for_reveal"):
        raise QualificationError("the mechanical reveal gate is not ready: %s" % "; ".join(state["blockers"]))
    result = _canonical_result()
    temporary = RESULT_PATH.with_suffix(RESULT_PATH.suffix + ".tmp")
    temporary.write_bytes((canonical_json(result) + "\n").encode("ascii"))
    temporary.replace(RESULT_PATH)
    _print_summary(result, replay=False)
    return 0


def replay() -> int:
    if not RESULT_PATH.is_file():
        raise QualificationError("RESULT.json does not exist; there is nothing to replay")
    state = execution.readiness(ROOT)
    if state.get("phase") != "executed" or state.get("blockers"):
        raise QualificationError("the preserved reveal chain is not executable")
    preserved = _load(RESULT_PATH)
    recomputed = _canonical_result()
    if canonical_bytes(preserved) != canonical_bytes(recomputed):
        raise QualificationError("independent replay differs from the preserved canonical result")
    _print_summary(recomputed, replay=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--replay", action="store_true")
    arguments = parser.parse_args()
    try:
        return execute() if arguments.execute else replay()
    except (
        QualificationError,
        execution.ExecutionError,
        sealing.SealingError,
        bank.CarrierBankError,
        delivery.DeliveryError,
        scientific_bank.CarrierBankError,
    ) as exc:
        print("REFUSED: %s" % exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
