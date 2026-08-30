import json

from metamorphosis import m115_identity as model_identity
from metamorphosis import m115_sealing as sealing
from metamorphosis.blind_bank_protocol import sha256_hex
from scripts import seal_m115_bank as seal_command


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _valid_response_and_ledger():
    body = {
        "model": model_identity.REQUESTED_MODEL,
        "provider": model_identity.SELECTED_PROVIDER,
        "openrouter_metadata": {
            "requested": model_identity.REQUESTED_MODEL,
            "strategy": "direct",
            "attempt": 1,
            "is_byok": False,
            "endpoints": {
                "total": 1,
                "available": [
                    {
                        "provider": model_identity.SELECTED_PROVIDER,
                        "model": model_identity.CANONICAL_CHECKPOINT,
                        "selected": True,
                    }
                ],
            },
            "attempts": [],
            "pipeline": [],
        },
        "choices": [{"message": {"content": "opaque carrier content"}}],
    }
    attestation = model_identity.attest_completion_response(body)
    attempt = {
        "attempt_index": 1,
        "started_at": "2026-08-30T08:00:00Z",
        "finished_at": "2026-08-30T08:00:02Z",
        "status": 200,
        "served_model": model_identity.REQUESTED_MODEL,
        "served_provider": model_identity.SELECTED_PROVIDER,
        "identity_attestation": attestation,
        "outcome": "materialized",
    }
    ledger = {
        "bank_materialization_index": 1,
        "attempts": [attempt],
    }
    response = {
        "delivery_attempt_index": 1,
        "delivery_attempts_made": 1,
        "status": 200,
        "served_model": model_identity.REQUESTED_MODEL,
        "served_provider": model_identity.SELECTED_PROVIDER,
        "runtime_identity_attestation": attestation,
        "started_at": attempt["started_at"],
        "finished_at": attempt["finished_at"],
        "body": body,
    }
    return response, ledger


def test_materialization_is_not_reported_as_generated_sealed(tmp_path, monkeypatch):
    experiment = tmp_path / "experiments" / "M115"
    ledger_path = experiment / "DELIVERY_LEDGER.json"
    response_path = experiment / "GENERATION_RESPONSE.json"
    _write(ledger_path, {"kind": "ledger"})
    _write(response_path, {"kind": "response"})

    monkeypatch.setattr(
        sealing.bank,
        "readiness",
        lambda _root: {
            "schema": "m115-carrier-bank-readiness-v1",
            "milestone": "M115",
            "hypothesis": "H60",
            "phase": "generated_sealed",
            "blockers": [],
            "revealed": False,
        },
    )
    monkeypatch.setattr(
        sealing,
        "_load",
        lambda path: (
            {"spec_commitment_sha256": "a" * 64, "canonical_request_body_sha256": "b" * 64}
            if path.name == "GENERATOR_SPEC.json"
            else {"kind": "ledger"}
        ),
    )
    monkeypatch.setattr(sealing.delivery, "validate_delivery_ledger", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sealing.delivery,
        "delivery_summary",
        lambda _ledger: {"bank_materializations": 1},
    )

    state = sealing.readiness(tmp_path)

    assert state["phase"] == "materialized_unsealed"
    assert "missing SEALED_BANK.json.gpg" in state["blockers"]
    assert "missing PUBLIC_BANK_COMMITMENT.json" in state["blockers"]


def test_public_commitment_binds_ciphertext_and_requires_plaintext_absence(tmp_path, monkeypatch):
    experiment = tmp_path / "experiments" / "M115"
    spec = {"spec_commitment_sha256": "a" * 64, "canonical_request_body_sha256": "b" * 64}
    ledger = {"schema": "test-ledger", "attempts": [{"attempt_index": 1}]}
    _write(experiment / "GENERATOR_SPEC.json", spec)
    _write(experiment / "DELIVERY_LEDGER.json", ledger)
    ciphertext = b"opaque encrypted bytes"
    sealed_path = experiment / "SEALED_BANK.json.gpg"
    sealed_path.write_bytes(ciphertext)

    monkeypatch.setattr(sealing.delivery, "validate_delivery_ledger", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sealing.delivery,
        "delivery_summary",
        lambda _ledger: {"bank_materializations": 1},
    )

    ledger_digest = sealing.delivery.ledger_digest(ledger)
    commitment = sealing.build_public_commitment(
        spec_commitment_sha256="a" * 64,
        request_body_sha256="b" * 64,
        delivery_ledger_sha256=ledger_digest,
        generation_response_sha256="c" * 64,
        generation_response_bytes=123,
        ciphertext_sha256=sha256_hex(ciphertext),
        ciphertext_bytes=len(ciphertext),
        sealed_at="2026-08-30T08:00:00Z",
    )

    sealing.validate_public_commitment(commitment, root=tmp_path)

    _write(experiment / "GENERATION_RESPONSE.json", {"plaintext": True})
    try:
        sealing.validate_public_commitment(commitment, root=tmp_path)
    except sealing.SealingError as exc:
        assert "plaintext generation response still exists" in str(exc)
    else:
        raise AssertionError("a plaintext response must invalidate generated_sealed custody")


def test_commitment_digest_detects_metadata_drift():
    commitment = sealing.build_public_commitment(
        spec_commitment_sha256="a" * 64,
        request_body_sha256="b" * 64,
        delivery_ledger_sha256="c" * 64,
        generation_response_sha256="d" * 64,
        generation_response_bytes=100,
        ciphertext_sha256="e" * 64,
        ciphertext_bytes=200,
        sealed_at="2026-08-30T08:00:00Z",
    )
    original = commitment["commitment_sha256"]
    commitment["ciphertext_bytes"] = 201

    assert sealing.commitment_digest(commitment) != original


def test_seal_preflight_recomputes_runtime_identity_from_current_body():
    response, ledger = _valid_response_and_ledger()
    response["body"]["provider"] = "Substituted Provider"

    try:
        seal_command._validate_response_provenance(response, ledger)
    except seal_command.SealCommandError as exc:
        assert "no longer passes runtime identity attestation" in str(exc)
    else:
        raise AssertionError("a substituted response body must be refused before sealing")


def test_seal_preflight_rejects_stale_stored_attestation():
    response, ledger = _valid_response_and_ledger()
    response["runtime_identity_attestation"] = dict(response["runtime_identity_attestation"])
    response["runtime_identity_attestation"]["holds"] = False

    try:
        seal_command._validate_response_provenance(response, ledger)
    except seal_command.SealCommandError as exc:
        assert "does not match its current body" in str(exc)
    else:
        raise AssertionError("a stale stored attestation must be refused before sealing")


def test_seal_preflight_rejects_operational_drift_from_materialized_attempt():
    response, ledger = _valid_response_and_ledger()
    response["finished_at"] = "2026-08-30T09:00:00Z"

    try:
        seal_command._validate_response_provenance(response, ledger)
    except seal_command.SealCommandError as exc:
        assert "finished_at" in str(exc)
    else:
        raise AssertionError("a response detached from the materialized attempt must be refused")
