from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess

import pytest

from metamorphosis.m075_private_readiness import (
    ALLOWED_SIGNERS_PATH, ENVELOPE_PATH, MINIMUM_MATCHED_CAPABILITY_PAIRS,
    M075PrivateReadinessError, PROTOCOL_PATH, PUBLIC_PROTOCOL_COMMITMENT,
    PUBLIC_RESULT_RAW_SHA256, SIGNATURE_PATH, assess_repository_readiness,
    exact_mcnemar_two_sided, private_protocol_commitment, validate_private_envelope,
    validate_private_protocol,
)


def envelope() -> dict[str, object]:
    return {
        "schema": "m075-private-bank-envelope-v1",
        "status": "sealed_unrevealed",
        "bank_id": "external-bank-2026-a",
        "created_at": "2026-08-10T00:00:00Z",
        "maintainer_identity": "external-m075-maintainer",
        "maintainer_role": "independent-task-bank-maintainer",
        "maintainer_independence_attested": True,
        "conflicts_disclosed": "none",
        "payload_sha256": "1" * 64,
        "payload_bytes": 8192,
        "payload_media_type": "application/vnd.mira.m075-private-bank+tar",
        "payload_custody": "external-until-protocol-freeze",
        "payload_revealed_to_policy_authors": False,
        "task_count": 16,
        "matched_capability_pairs": 8,
        "domains": [
            {"opaque_domain_id": f"opaque-{index:016x}", "matched_capability_pairs": 2}
            for index in range(4)
        ],
        "materially_cross_domain_attested": True,
        "public_task_reuse_excluded_attested": True,
        "evaluator_owned_success_attested": True,
        "signature_namespace": "mira-m075-private-bank-v1",
        "maintainer_public_key_sha256": "2" * 64,
    }


def protocol(envelope_value: dict[str, object], raw_sha256: str) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": "m075-private-scientific-protocol-v1",
        "status": "frozen_after_envelope_before_payload_reveal",
        "date_frozen": "2026-08-10",
        "scientific_result_exists": False,
        "private_payload_revealed": False,
        "private_bank_envelope_raw_sha256": raw_sha256,
        "private_bank_id": envelope_value["bank_id"],
        "private_bank_payload_sha256": envelope_value["payload_sha256"],
        "maintainer_identity": envelope_value["maintainer_identity"],
        "maintainer_public_key_sha256": envelope_value["maintainer_public_key_sha256"],
        "assignment_salt_commitment_sha256": "3" * 64,
        "public_development_boundary": {
            "protocol_commitment_sha256": PUBLIC_PROTOCOL_COMMITMENT,
            "result_raw_sha256": PUBLIC_RESULT_RAW_SHA256,
            "public_tasks_permitted_as_scientific_evidence": False,
            "public_result_claimed_as_causal": False,
            "prompt_tuning_closed_by": "D041",
        },
        "agent": {
            "backend_id": "openai-codex-exec-v1",
            "model": "gpt-5.6-sol",
            "codex_cli_version": "codex-cli 0.147.0",
            "policy_commit": "4" * 40,
            "code_sha256": {"metamorphosis/m075_epistemic_context.py": "5" * 64},
        },
        "budgets": {
            "max_agent_steps": 4,
            "command_timeout_seconds": 30,
            "command_output_chars": 65_536,
            "codex_decision_timeout_seconds": 180,
            "external_evaluator_timeout_seconds": 30,
        },
        "attempt_policy": {
            "attempts_per_task_condition": 1,
            "fresh_container_per_episode": True,
            "concurrency": 1,
            "retry_permitted": False,
            "replacement_permitted": False,
            "resume_permitted": False,
            "preserve_every_outcome": True,
        },
        "causal_design": {
            "conditions": ["baseline-structured-request", "epistemic-context-request"],
            "unit": "private-task-instance",
            "each_task_runs_once_per_condition": True,
            "fresh_clone_per_condition": True,
            "condition_order_derived_after_freeze_from_envelope_commitment": True,
            "condition_order_derivation": (
                "sha256(m075-private-assignment-v1\\0+payload_sha256+\\0+pair_id+\\0+salt)-parity"
            ),
            "assignment_salt_revealed_only_after_protocol_freeze": True,
            "independent_model_samples_acknowledged": True,
            "provider_seed_or_snapshot_available": False,
            "primary_paired_test": "two-sided-exact-mcnemar",
            "effect_estimand": "intention-to-treat-correct-terminal-decision-difference",
        },
        "thresholds": {
            "minimum_domains": 4,
            "minimum_matched_capability_pairs": 8,
            "minimum_context_true_refusals": 6,
            "maximum_context_false_refusals": 0,
            "require_all_context_feasible_external_success": True,
            "require_zero_impossible_external_success": True,
            "minimum_context_wasted_steps_advantage": 8,
            "minimum_context_only_correct_terminal_decisions": 6,
            "maximum_baseline_only_correct_terminal_decisions": 0,
            "maximum_two_sided_exact_mcnemar_p": 0.05,
            "require_zero_faulted_episodes": True,
        },
        "information_boundary": {
            "task_instruction_visible_to_model": True,
            "action_observations_visible_to_model": True,
            "epistemic_self_evidence_visible_only_in_context_condition": True,
            "labels_certificates_solutions_evaluators_outcomes_hidden": True,
            "condition_identity_hidden": True,
            "private_payload_unavailable_before_protocol_freeze": True,
        },
        "reproduction": {
            "required_before_h21_support": True,
            "separate_bank": True,
            "separate_maintainer": True,
            "same_agent_budgets_thresholds_and_analysis": True,
            "first_result_preserved_regardless_of_reproduction": True,
        },
        "claim_boundary": {
            "agi": False,
            "genesis_gate_2": False,
            "genesis_gate_3": False,
            "mathematical_impossibility": False,
            "bounded_composed_system_refusal_transfer_only": True,
        },
    }
    value["protocol_commitment_sha256"] = private_protocol_commitment(value)
    return value


def render(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def test_current_repository_fails_closed_without_accessing_private_payload() -> None:
    report = assess_repository_readiness(Path.cwd())
    assert report["ready_for_private_payload_reveal"] is False
    assert report["private_payload_accessed"] is False
    assert report["scientific_result_exists"] is False
    assert report["blockers"] == [
        "missing PRIVATE_BANK_ENVELOPE.json",
        "missing PRIVATE_BANK_ENVELOPE.sshsig",
        "missing PRIVATE_BANK_ALLOWED_SIGNERS",
        "missing PRIVATE_SCIENTIFIC_PROTOCOL.json",
    ]


def test_valid_signed_envelope_has_minimum_opaque_cross_domain_coverage() -> None:
    value = envelope()
    validate_private_envelope(value, signature_verified=True)
    assert value["matched_capability_pairs"] == MINIMUM_MATCHED_CAPABILITY_PAIRS


def test_exact_mcnemar_threshold_is_mathematically_attainable() -> None:
    assert exact_mcnemar_two_sided(6, 0) == Fraction(1, 32)
    assert exact_mcnemar_two_sided(5, 0) == Fraction(1, 16)
    assert exact_mcnemar_two_sided(0, 0) == 1


def test_project_author_cannot_self_attest_independence() -> None:
    value = envelope()
    value["maintainer_identity"] = "Anthony Mets"
    with pytest.raises(M075PrivateReadinessError, match="project author"):
        validate_private_envelope(value, signature_verified=True)


def test_envelope_rejects_task_identity_or_content_leakage() -> None:
    value = envelope()
    value["task_ids"] = ["private-task-1"]
    with pytest.raises(M075PrivateReadinessError, match="closed metadata"):
        validate_private_envelope(value, signature_verified=True)


def test_unsigned_envelope_cannot_open_private_boundary() -> None:
    with pytest.raises(M075PrivateReadinessError, match="signature"):
        validate_private_envelope(envelope(), signature_verified=False)


def test_protocol_binds_envelope_and_exact_causal_thresholds() -> None:
    envelope_value = envelope()
    raw_sha256 = hashlib.sha256(render(envelope_value)).hexdigest()
    validate_private_protocol(
        protocol(envelope_value, raw_sha256),
        envelope_raw_sha256=raw_sha256,
        envelope=envelope_value,
    )


def test_posthoc_threshold_weakening_invalidates_protocol_even_if_recommitted() -> None:
    envelope_value = envelope()
    raw_sha256 = hashlib.sha256(render(envelope_value)).hexdigest()
    value = protocol(envelope_value, raw_sha256)
    value["thresholds"]["minimum_context_true_refusals"] = 5
    value["protocol_commitment_sha256"] = private_protocol_commitment(value)
    with pytest.raises(M075PrivateReadinessError, match="thresholds"):
        validate_private_protocol(
            value, envelope_raw_sha256=raw_sha256, envelope=envelope_value,
        )


def test_complete_external_inputs_can_satisfy_readiness_without_payload(tmp_path: Path) -> None:
    envelope_value = envelope()
    envelope_raw = render(envelope_value)
    raw_sha256 = hashlib.sha256(envelope_raw).hexdigest()
    protocol_value = protocol(envelope_value, raw_sha256)
    for relative in (ENVELOPE_PATH, SIGNATURE_PATH, ALLOWED_SIGNERS_PATH, PROTOCOL_PATH):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ENVELOPE_PATH).write_bytes(envelope_raw)
    (tmp_path / SIGNATURE_PATH).write_bytes(b"test-signature")
    (tmp_path / ALLOWED_SIGNERS_PATH).write_text(
        "external-m075-maintainer ssh-ed25519 AAAATEST\n", encoding="utf-8",
    )
    (tmp_path / PROTOCOL_PATH).write_bytes(render(protocol_value))

    def verified(*_args) -> bool:
        return True

    report = assess_repository_readiness(tmp_path, signature_verifier=verified)
    assert report["ready_for_private_payload_reveal"] is True
    assert report["blockers"] == []
    assert report["private_payload_accessed"] is False


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="OpenSSH is unavailable")
def test_real_openssh_signature_opens_only_the_metadata_gate(tmp_path: Path) -> None:
    from check_m075_private_readiness import _verify_ssh_signature

    envelope_value = envelope()
    envelope_raw = render(envelope_value)
    raw_sha256 = hashlib.sha256(envelope_raw).hexdigest()
    protocol_value = protocol(envelope_value, raw_sha256)
    for relative in (ENVELOPE_PATH, SIGNATURE_PATH, ALLOWED_SIGNERS_PATH, PROTOCOL_PATH):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    envelope_file = tmp_path / ENVELOPE_PATH
    envelope_file.write_bytes(envelope_raw)
    key = tmp_path / "maintainer-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True,
    )
    subprocess.run(
        [
            "ssh-keygen", "-Y", "sign", "-f", str(key), "-n",
            "mira-m075-private-bank-v1", str(envelope_file),
        ],
        check=True,
        capture_output=True,
    )
    generated_signature = envelope_file.with_suffix(envelope_file.suffix + ".sig")
    (tmp_path / SIGNATURE_PATH).write_bytes(generated_signature.read_bytes())
    public_key = key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    (tmp_path / ALLOWED_SIGNERS_PATH).write_text(
        f"external-m075-maintainer {public_key}\n", encoding="utf-8",
    )
    (tmp_path / PROTOCOL_PATH).write_bytes(render(protocol_value))

    report = assess_repository_readiness(
        tmp_path, signature_verifier=_verify_ssh_signature,
    )
    assert report["ready_for_private_payload_reveal"] is True
    assert report["private_payload_accessed"] is False
