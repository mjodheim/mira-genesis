"""The M075-B reveal gate, driven through its whole ordered chain and then attacked at each link.

The gate is fail-closed: absent, malformed and drifted are all blockers. These tests build a
complete valid chain in a temporary tree — nothing here writes into the repository — and then
break one link at a time.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.blind_bank_devkit import (
    DEVELOPMENT_PROMPT,
    development_bank,
    development_generator_spec,
)
from metamorphosis.blind_bank_isolation import (
    CONTAINER_OUTPUT_DIRECTORY,
    build_attestation,
    plan_invocation,
)
from metamorphosis.blind_bank_protocol import (
    BlindBankError,
    LEDGER_SCHEMA,
    REVEAL_SCHEMA,
    REVEAL_SIGNATURE_NAMESPACE,
    canonical_bytes,
    commitment_of,
    generator_commitment,
    sha256_hex,
    spec_commitment,
)
from metamorphosis.blind_bank_sealing import finalize_seal
from metamorphosis.m075b_blind_readiness import (
    ANALYSIS_PLAN_PATH,
    ANALYSIS_PLAN_SCHEMA,
    BANK_COMMITMENT_PATH,
    BLIND_CLAIM_BOUNDARY,
    GENERATION_LEDGER_PATH,
    GENERATOR_PROMPT_PATH,
    GENERATOR_SPEC_PATH,
    ISOLATION_ATTESTATION_PATH,
    MILESTONE,
    M075BReadinessError,
    RESULT_PATH,
    REVEAL_ALLOWED_SIGNERS_PATH,
    REVEAL_AUTHORIZATION_PATH,
    REVEAL_SIGNATURE_PATH,
    SYSTEM_PROTOCOL_PATH,
    SYSTEM_PROTOCOL_SCHEMA,
    analysis_plan_commitment,
    assess_blind_bank_readiness,
    system_protocol_commitment,
    validate_analysis_plan,
    validate_system_protocol,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SOURCE = REPOSITORY_ROOT / "docs/schemas/blind_bank_payload.schema.json"


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(document))  # type: ignore[arg-type]


def _analysis_plan(spec: dict[str, object]) -> dict[str, object]:
    plan: dict[str, object] = {
        "schema": ANALYSIS_PLAN_SCHEMA,
        "milestone": MILESTONE,
        "status": "frozen_before_generation",
        "date_frozen": "2026-08-12",
        "hypothesis_id": "H21",
        "evidence_tier": "blind_generated_sealed_bank",
        "unit": "task-instance",
        "conditions": ["baseline-structured-request", "epistemic-context-request"],
        "primary_test": "two-sided-exact-mcnemar",
        "thresholds": {
            "minimum_context_true_refusals": 6,
            "maximum_context_false_refusals": 0,
            "require_all_feasible_external_success": True,
            "require_zero_impossible_external_success": True,
            "minimum_context_only_correct_terminal_decisions": 6,
            "maximum_baseline_only_correct_terminal_decisions": 0,
            "maximum_two_sided_exact_mcnemar_p": 0.05,
            "require_zero_faulted_episodes": True,
        },
        "attainability": {
            "total_pairs": 8,
            "maximum_discordant_task_instances": 16,
            "two_sided_exact_mcnemar_p_at_threshold": "1/32",
            "computed_before_generation": True,
        },
        "non_retry": {
            "first_materialized_bank_counts": True,
            "reroll_permitted": False,
            "salt_change_permitted": False,
            "threshold_change_permitted": False,
            "negative_result_preserved": True,
            "successor_requires_new_protocol_version_and_new_bank": True,
        },
        "claim_boundary": dict(BLIND_CLAIM_BOUNDARY),
        "plan_commitment_sha256": "",
    }
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    return plan


def _system_protocol(
    *, commitment: dict[str, object], spec: dict[str, object], plan: dict[str, object],
    attestation_digest: str,
) -> dict[str, object]:
    protocol: dict[str, object] = {
        "schema": SYSTEM_PROTOCOL_SCHEMA,
        "milestone": MILESTONE,
        "status": "frozen_after_sealing_before_reveal",
        "date_frozen": "2026-08-12",
        "bank_commitment_sha256": commitment["commitment_sha256"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "isolation_attestation_sha256": attestation_digest,
        "tested_system": {
            "backend_id": "a-frozen-backend",
            "model": "a-frozen-model",
            "cli_version": "0.0.0",
            "policy_commit": "0" * 40,
            "code_sha256": {"metamorphosis/example.py": "1" * 64},
            "frozen_before_any_bank_content_was_known": True,
        },
        "budgets": {"max_agent_steps": 4, "command_timeout_seconds": 30},
        "attempt_policy": {
            "attempts_per_task_condition": 1,
            "fresh_environment_per_episode": True,
            "concurrency": 1,
            "retry_permitted": False,
            "replacement_permitted": False,
            "resume_permitted": False,
            "preserve_every_outcome": True,
        },
        "assignment_salt_commitment_sha256": "2" * 64,
        "information_boundary": {
            "task_instruction_visible_to_tested_system": True,
            "action_observations_visible_to_tested_system": True,
            "epistemic_self_evidence_visible_only_in_context_condition": True,
            "labels_certificates_evaluators_outcomes_hidden": True,
            "condition_identity_hidden": True,
            "bank_content_unavailable_before_reveal_authorization": True,
            "tested_system_unmodified_after_reveal": True,
        },
        "reproduction": {
            "cross_generator_reproduction_required_for_next_tier": True,
            "second_generator_must_differ_in_family": True,
            "second_generator_must_differ_in_runtime": True,
            "second_generator_must_use_a_separate_bank": True,
            "human_maintained_bank_still_required_for_h21_support": True,
            "first_result_preserved_regardless_of_reproduction": True,
        },
        "claim_boundary": dict(BLIND_CLAIM_BOUNDARY),
        "protocol_commitment_sha256": "",
    }
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    return protocol


class Chain:
    """A complete valid M075-B artifact chain in a temporary tree."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "repository"
        self.outside = tmp_path / "outside"
        self.root.mkdir(parents=True)
        self.outside.mkdir()

        schema_target = self.root / "docs/schemas/blind_bank_payload.schema.json"
        schema_target.parent.mkdir(parents=True)
        schema_bytes = SCHEMA_SOURCE.read_bytes()
        schema_target.write_bytes(schema_bytes)

        prompt_path = self.root / GENERATOR_PROMPT_PATH
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_bytes = DEVELOPMENT_PROMPT.encode("utf-8")
        prompt_path.write_bytes(prompt_bytes)

        self.spec = development_generator_spec(
            prompt_sha256=sha256_hex(prompt_bytes),
            schema_sha256=sha256_hex(schema_bytes),
        )
        self.plan = _analysis_plan(self.spec)
        self.payload = development_bank(self.spec, seed=0)

        request = self.outside / "request.json"
        request.write_text("{}", encoding="utf-8")
        output = self.outside / "out"
        output.mkdir()
        # The attestation must describe the run the frozen spec pinned, so the image and runtime
        # are taken from the spec rather than invented. A fixture that invented them was rejected
        # by the cross-artifact binding, which is the point of that check.
        runtime = self.spec["generator"]["runtime"]  # type: ignore[index]
        invocation = plan_invocation(
            repository_root=self.root,
            image_reference=str(runtime["image_reference"]),
            image_digest_sha256=str(runtime["image_digest_sha256"]),
            input_path=request,
            output_directory=output,
            environment={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "BLIND_BANK_INPUT": "/blind/input/request.json",
                "BLIND_BANK_OUTPUT": str(CONTAINER_OUTPUT_DIRECTORY),
            },
            command=["/usr/local/bin/emit-bank"],
        )
        canonical = canonical_bytes(self.payload)
        self.attestation = build_attestation(
            plan=invocation,
            repository_root=self.root,
            input_sha256=sha256_hex(request.read_bytes()),
            # The attested output is the payload that gets sealed. Anything else would be an
            # attestation of a run that produced a different bank.
            output_sha256=sha256_hex(canonical),
            stdout_sha256=sha256_hex(b""),
            stderr_sha256=sha256_hex(b""),
            started_at="2026-08-12T00:00:00Z",
            finished_at="2026-08-12T00:10:00Z",
            exit_status=0,
            runtime_name=str(runtime["name"]),
            runtime_version=str(runtime["version"]),
        )
        self.commitment = finalize_seal(
            payload=self.payload,
            spec=self.spec,
            generator_commitment_sha256=generator_commitment(self.spec["generator"]),
            isolation_attestation_sha256=str(self.attestation["attestation_sha256"]),
            ciphertext_sha256="3" * 64,
            cipher="age-v1-x25519",
            key_custody="external-holder",
            sealed_at="2026-08-12T00:11:00Z",
            milestone=MILESTONE,
        )
        self.ledger = {
            "schema": LEDGER_SCHEMA,
            "entries": [{
                "attempt_index": 1,
                "spec_commitment_sha256": self.spec["spec_commitment_sha256"],
                "started_at": "2026-08-12T00:00:00Z",
                "outcome": "materialized",
                "payload_sha256": self.commitment["payload_sha256"],
                "isolation_attestation_sha256": self.attestation["attestation_sha256"],
                "note": "",
            }],
        }
        self.protocol = _system_protocol(
            commitment=self.commitment, spec=self.spec, plan=self.plan,
            attestation_digest=str(self.attestation["attestation_sha256"]),
        )
        self.authorization = {
            "schema": REVEAL_SCHEMA,
            "milestone": MILESTONE,
            "bank_id": self.commitment["bank_id"],
            "bank_commitment_sha256": self.commitment["commitment_sha256"],
            "system_protocol_commitment_sha256": self.protocol["protocol_commitment_sha256"],
            "authorized_by": "an-authorizing-identity",
            "authorized_at": "2026-08-12T00:20:00Z",
            "signature_namespace": REVEAL_SIGNATURE_NAMESPACE,
            "authorizer_public_key_sha256": "4" * 64,
            "single_execution_only": True,
            "result_preserved_regardless_of_outcome": True,
        }

    def write_through(self, stage: str) -> None:
        """Write artifacts up to and including the named stage."""

        order = ["spec", "sealed", "protocol", "reveal"]
        index = order.index(stage)
        _write(self.root / GENERATOR_SPEC_PATH, self.spec)
        _write(self.root / ANALYSIS_PLAN_PATH, self.plan)
        if index >= 1:
            _write(self.root / GENERATION_LEDGER_PATH, self.ledger)
            _write(self.root / ISOLATION_ATTESTATION_PATH, self.attestation)
            _write(self.root / BANK_COMMITMENT_PATH, self.commitment)
        if index >= 2:
            _write(self.root / SYSTEM_PROTOCOL_PATH, self.protocol)
        if index >= 3:
            _write(self.root / REVEAL_AUTHORIZATION_PATH, self.authorization)
            (self.root / REVEAL_SIGNATURE_PATH).write_text("signature", encoding="utf-8")
            (self.root / REVEAL_ALLOWED_SIGNERS_PATH).write_text("signer", encoding="utf-8")

    def assess(self, *, signature_verified: bool = True) -> dict[str, object]:
        return assess_blind_bank_readiness(
            self.root,
            signature_verifier=lambda *_arguments: signature_verified,
        )


@pytest.fixture()
def chain(tmp_path: Path) -> Chain:
    return Chain(tmp_path)


# ---------------------------------------------------------------------------------------------
# the repository's own state
# ---------------------------------------------------------------------------------------------


def test_the_repository_has_authorized_no_reveal_and_holds_no_result() -> None:
    report = assess_blind_bank_readiness(REPOSITORY_ROOT)
    assert report["reveal_authorized"] is False
    assert report["scientific_result_exists"] is False
    assert report["ready_for_reveal"] is False
    assert report["bank_payload_accessed"] is False
    assert report["phase"] == "draft"


def test_the_report_never_claims_to_replace_the_human_maintainer() -> None:
    report = assess_blind_bank_readiness(REPOSITORY_ROOT)
    assert report["supersedes_m075_human_maintainer_requirement"] is False
    assert report["issue_112_status_changed_by_this_milestone"] is False
    boundary = report["claim_boundary"]
    assert boundary["satisfies_m075_independent_human_maintainer_requirement"] is False
    assert boundary["human_independence"] is False
    assert boundary["external_reproduction"] is False
    assert boundary["generator_training_data_independence"] is False
    assert boundary["supports_h21"] is False
    assert boundary["closes_issue_112"] is False


# ---------------------------------------------------------------------------------------------
# the ordered chain
# ---------------------------------------------------------------------------------------------


def test_the_chain_reaches_readiness_only_at_the_system_protocol_freeze(
    chain: Chain,
) -> None:
    chain.write_through("spec")
    first = chain.assess()
    assert first["phase"] == "spec_frozen"
    assert first["ready_for_reveal"] is False
    assert any("no bank has been materialized" in item for item in first["blockers"])

    chain.write_through("sealed")
    second = chain.assess()
    assert second["phase"] == "generated_sealed"
    assert second["ready_for_reveal"] is False

    chain.write_through("protocol")
    third = chain.assess()
    assert third["blockers"] == []
    assert third["phase"] == "system_protocol_frozen"
    assert third["ready_for_reveal"] is True
    assert third["reveal_authorized"] is False


def test_a_signed_authorization_moves_the_phase_and_closes_readiness(chain: Chain) -> None:
    chain.write_through("reveal")
    report = chain.assess(signature_verified=True)
    assert report["blockers"] == []
    assert report["phase"] == "reveal_authorized"
    assert report["reveal_authorized"] is True
    # Readiness is the state *before* the reveal. Once authorized it is no longer pending.
    assert report["ready_for_reveal"] is False


def test_an_unsigned_authorization_does_not_open_the_bank(chain: Chain) -> None:
    chain.write_through("reveal")
    report = chain.assess(signature_verified=False)
    assert report["reveal_authorized"] is False
    assert any("signature is not verified" in item for item in report["blockers"])


def test_a_reveal_before_the_system_protocol_is_refused(chain: Chain) -> None:
    chain.write_through("sealed")
    _write(chain.root / REVEAL_AUTHORIZATION_PATH, chain.authorization)
    (chain.root / REVEAL_SIGNATURE_PATH).write_text("signature", encoding="utf-8")
    (chain.root / REVEAL_ALLOWED_SIGNERS_PATH).write_text("signer", encoding="utf-8")
    report = chain.assess()
    assert report["reveal_authorized"] is False
    assert any("precedes the protocol it must bind" in item for item in report["blockers"])


def test_a_result_without_a_reveal_authorization_is_refused(chain: Chain) -> None:
    chain.write_through("protocol")
    _write(chain.root / RESULT_PATH, {"outcome": "whatever"})
    report = chain.assess()
    assert report["scientific_result_exists"] is True
    assert any(
        "without a complete, signed reveal authorization" in item
        for item in report["blockers"]
    )


def test_a_partial_reveal_stage_is_reported(chain: Chain) -> None:
    chain.write_through("protocol")
    _write(chain.root / REVEAL_AUTHORIZATION_PATH, chain.authorization)
    report = chain.assess()
    assert any("REVEAL_AUTHORIZATION.sshsig" in item for item in report["blockers"])
    assert any("REVEAL_ALLOWED_SIGNERS" in item for item in report["blockers"])


# ---------------------------------------------------------------------------------------------
# drift at each link
# ---------------------------------------------------------------------------------------------


def test_prompt_drift_after_the_freeze_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    (chain.root / GENERATOR_PROMPT_PATH).write_text(
        DEVELOPMENT_PROMPT + "Also prefer tasks the agent will handle well.\n", encoding="utf-8",
    )
    report = chain.assess()
    assert any(
        "prompt file does not match the digest" in item for item in report["blockers"]
    )
    assert report["ready_for_reveal"] is False


def test_output_schema_drift_after_the_freeze_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    schema_path = chain.root / "docs/schemas/blind_bank_payload.schema.json"
    schema_path.write_text(schema_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report = chain.assess()
    assert any(
        "output schema file does not match the digest" in item for item in report["blockers"]
    )


def test_spec_drift_after_the_freeze_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    drifted = dict(chain.spec)
    drifted["date_frozen"] = "2026-09-01"
    _write(chain.root / GENERATOR_SPEC_PATH, drifted)
    report = chain.assess()
    assert any("commitment drifted" in item for item in report["blockers"])


def test_a_commitment_not_binding_the_isolation_attestation_is_detected(
    chain: Chain,
) -> None:
    chain.write_through("protocol")
    other = finalize_seal(
        payload=chain.payload,
        spec=chain.spec,
        generator_commitment_sha256=generator_commitment(chain.spec["generator"]),
        isolation_attestation_sha256="9" * 64,
        ciphertext_sha256="3" * 64,
        cipher="age-v1-x25519",
        key_custody="external-holder",
        sealed_at="2026-08-12T00:11:00Z",
        milestone=MILESTONE,
    )
    _write(chain.root / BANK_COMMITMENT_PATH, other)
    report = chain.assess()
    assert any(
        "does not bind the isolation attestation" in item for item in report["blockers"]
    )


def test_a_ledger_and_commitment_disagreeing_on_the_payload_is_detected(
    chain: Chain,
) -> None:
    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    ledger["entries"][0]["payload_sha256"] = "7" * 64
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("disagree on the sealed payload" in item for item in report["blockers"])


def test_a_second_materialization_under_one_frozen_spec_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    second = json.loads(json.dumps(ledger["entries"][0]))
    second["attempt_index"] = 2
    second["payload_sha256"] = "8" * 64
    ledger["entries"].append(second)
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("one frozen spec admits one" in item for item in report["blockers"])
    assert report["ready_for_reveal"] is False


def test_an_isolation_attestation_mounting_the_repository_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    attestation = json.loads(json.dumps(chain.attestation))
    attestation["argv"] = attestation["argv"] + [
        "--mount", f"type=bind,source={chain.root},target=/repo,readonly",
    ]
    _write(chain.root / ISOLATION_ATTESTATION_PATH, attestation)
    report = chain.assess()
    assert any("isolation attestation" in item for item in report["blockers"])


# --- P1-1: the four sealed-stage artifacts must describe one run -------------------------------


def test_an_attestation_from_one_run_with_a_payload_from_another_is_detected(
    chain: Chain,
) -> None:
    """Attestation A + payload B, with the ledger made to agree with B.

    Each document is individually well formed, so nothing but the cross-binding catches it.
    """

    chain.write_through("protocol")
    other = development_bank(chain.spec, seed=9)
    other_digest = sha256_hex(canonical_bytes(other))
    commitment = finalize_seal(
        payload=other,
        spec=chain.spec,
        generator_commitment_sha256=generator_commitment(chain.spec["generator"]),
        isolation_attestation_sha256=str(chain.attestation["attestation_sha256"]),
        ciphertext_sha256="3" * 64,
        cipher="age-v1-x25519",
        key_custody="external-holder",
        sealed_at="2026-08-12T00:11:00Z",
        milestone=MILESTONE,
    )
    ledger = json.loads(json.dumps(chain.ledger))
    ledger["entries"][0]["payload_sha256"] = other_digest
    _write(chain.root / BANK_COMMITMENT_PATH, commitment)
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any(
        "attested generator output is not the payload" in item for item in report["blockers"]
    )
    assert report["ready_for_reveal"] is False
    assert report["phase"] == "spec_frozen"


def test_a_commitment_naming_another_generator_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    commitment = json.loads(json.dumps(chain.commitment))
    commitment["generator_commitment_sha256"] = "9" * 64
    commitment["commitment_sha256"] = commitment_of(commitment, omit="commitment_sha256")
    _write(chain.root / BANK_COMMITMENT_PATH, commitment)
    report = chain.assess()
    assert any(
        "different generator from the frozen" in item for item in report["blockers"]
    )
    assert report["ready_for_reveal"] is False


def test_an_attestation_recording_a_different_image_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    attestation = json.loads(json.dumps(chain.attestation))
    attestation["image_digest_sha256"] = "7" * 64
    attestation["attestation_sha256"] = sha256_hex(canonical_bytes({
        key: value for key, value in attestation.items() if key != "attestation_sha256"
    }))
    _write(chain.root / ISOLATION_ATTESTATION_PATH, attestation)
    report = chain.assess()
    assert any("image digest differs" in item for item in report["blockers"])
    assert report["ready_for_reveal"] is False


def test_an_attestation_recording_a_different_runtime_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    attestation = json.loads(json.dumps(chain.attestation))
    attestation["runtime_name"] = "another-runtime"
    attestation["attestation_sha256"] = sha256_hex(canonical_bytes({
        key: value for key, value in attestation.items() if key != "attestation_sha256"
    }))
    _write(chain.root / ISOLATION_ATTESTATION_PATH, attestation)
    report = chain.assess()
    assert any("runtime name differs" in item for item in report["blockers"])


def test_a_payload_digest_changed_after_sealing_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    commitment = json.loads(json.dumps(chain.commitment))
    commitment["payload_sha256"] = "8" * 64
    commitment["commitment_sha256"] = commitment_of(commitment, omit="commitment_sha256")
    _write(chain.root / BANK_COMMITMENT_PATH, commitment)
    report = chain.assess()
    assert any(
        "attested generator output is not the payload" in item for item in report["blockers"]
    )


# --- P1-2: the ledger must belong to the frozen spec -------------------------------------------


def test_a_materialization_for_another_spec_does_not_satisfy_this_milestone(
    chain: Chain,
) -> None:
    """One `materialized` entry belonging to a different experiment used to pass the gate."""

    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    ledger["entries"][0]["spec_commitment_sha256"] = "b" * 64
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("another frozen spec" in item for item in report["blockers"])
    assert report["ready_for_reveal"] is False


def test_a_foreign_materialization_mixed_into_the_ledger_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    foreign = json.loads(json.dumps(ledger["entries"][0]))
    foreign["attempt_index"] = 2
    foreign["spec_commitment_sha256"] = "b" * 64
    foreign["payload_sha256"] = "c" * 64
    ledger["entries"].append(foreign)
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("another frozen spec" in item for item in report["blockers"])


def test_the_right_payload_under_the_wrong_spec_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    ledger["entries"][0]["spec_commitment_sha256"] = "b" * 64  # payload digest left correct
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("another frozen spec" in item for item in report["blockers"])


def test_the_right_spec_with_the_wrong_payload_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    ledger["entries"][0]["payload_sha256"] = "c" * 64
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("disagree on the sealed payload" in item for item in report["blockers"])


def test_a_ledger_with_no_materialization_for_this_spec_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    ledger = json.loads(json.dumps(chain.ledger))
    ledger["entries"][0]["outcome"] = "failed_structural_validation"
    ledger["entries"][0]["payload_sha256"] = None
    ledger["entries"][0]["isolation_attestation_sha256"] = None
    _write(chain.root / GENERATION_LEDGER_PATH, ledger)
    report = chain.assess()
    assert any("materialized 0 banks" in item for item in report["blockers"])
    assert report["ready_for_reveal"] is False


def test_a_system_protocol_not_binding_the_analysis_plan_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    protocol = json.loads(json.dumps(chain.protocol))
    protocol["analysis_plan_commitment_sha256"] = "6" * 64
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    _write(chain.root / SYSTEM_PROTOCOL_PATH, protocol)
    report = chain.assess()
    assert any("pre-generation analysis plan" in item for item in report["blockers"])


def test_a_system_protocol_admitting_a_post_reveal_edit_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    protocol = json.loads(json.dumps(chain.protocol))
    protocol["information_boundary"]["tested_system_unmodified_after_reveal"] = False
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    _write(chain.root / SYSTEM_PROTOCOL_PATH, protocol)
    report = chain.assess()
    assert any("information boundary drifted" in item for item in report["blockers"])


def test_a_system_protocol_dropping_the_human_maintainer_requirement_is_detected(
    chain: Chain,
) -> None:
    chain.write_through("protocol")
    protocol = json.loads(json.dumps(chain.protocol))
    protocol["reproduction"]["human_maintained_bank_still_required_for_h21_support"] = False
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    _write(chain.root / SYSTEM_PROTOCOL_PATH, protocol)
    report = chain.assess()
    assert any("reproduction contract drifted" in item for item in report["blockers"])


def test_a_system_protocol_permitting_a_retry_is_detected(chain: Chain) -> None:
    chain.write_through("protocol")
    protocol = json.loads(json.dumps(chain.protocol))
    protocol["attempt_policy"]["retry_permitted"] = True
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    _write(chain.root / SYSTEM_PROTOCOL_PATH, protocol)
    report = chain.assess()
    assert any("single-attempt policy drifted" in item for item in report["blockers"])


# ---------------------------------------------------------------------------------------------
# the analysis plan, frozen before the bank exists
# ---------------------------------------------------------------------------------------------


def test_the_analysis_plan_validates(chain: Chain) -> None:
    validate_analysis_plan(chain.plan, spec=chain.spec)


def test_a_threshold_no_draw_could_ever_meet_is_refused(chain: Chain) -> None:
    # Four discordant instances give an exact two-sided p of 2/16 = 0.125, above the 0.05 the
    # plan freezes. A plan that could never pass is as useless as one that could never fail.
    plan = json.loads(json.dumps(chain.plan))
    plan["thresholds"]["minimum_context_only_correct_terminal_decisions"] = 4
    plan["attainability"]["two_sided_exact_mcnemar_p_at_threshold"] = "1/8"
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="can never pass"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_vacuous_refusal_threshold_is_refused(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["thresholds"]["minimum_context_true_refusals"] = 0
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="vacuous or unreachable"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_threshold_beyond_the_bank_size_is_refused(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["thresholds"]["minimum_context_true_refusals"] = 99
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="vacuous or unreachable"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_looser_significance_threshold_is_refused(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["thresholds"]["maximum_two_sided_exact_mcnemar_p"] = 0.2
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="looser than the project standard"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_plan_tolerating_a_false_refusal_is_refused(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["thresholds"]["maximum_context_false_refusals"] = 1
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="false refusal may never be tolerated"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_plan_frozen_after_generation_is_refused(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["status"] = "frozen_after_generation"
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="before the bank exists"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_plan_permitting_a_reroll_is_refused(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["non_retry"]["reroll_permitted"] = True
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="non-retry policy drifted"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_a_bank_narrower_than_the_human_maintained_minimum_is_refused(
    chain: Chain,
) -> None:
    narrow = development_generator_spec(domain_count=2, pairs_per_domain=2)
    plan = json.loads(json.dumps(chain.plan))
    plan["attainability"]["total_pairs"] = 4
    plan["attainability"]["maximum_discordant_task_instances"] = 8
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="at least as broad"):
        validate_analysis_plan(plan, spec=narrow)


def test_the_analysis_plan_claim_boundary_cannot_be_widened(chain: Chain) -> None:
    plan = json.loads(json.dumps(chain.plan))
    plan["claim_boundary"]["supports_h21"] = True
    plan["plan_commitment_sha256"] = analysis_plan_commitment(plan)
    with pytest.raises(M075BReadinessError, match="claim boundary drifted"):
        validate_analysis_plan(plan, spec=chain.spec)


def test_the_system_protocol_claim_boundary_cannot_be_widened(chain: Chain) -> None:
    protocol = json.loads(json.dumps(chain.protocol))
    protocol["claim_boundary"]["external_reproduction"] = True
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    with pytest.raises(BlindBankError, match="claim boundary drifted"):
        validate_system_protocol(
            protocol, commitment=chain.commitment, spec=chain.spec, plan=chain.plan,
            isolation_attestation_sha256=str(chain.attestation["attestation_sha256"]),
        )


def test_a_tested_system_frozen_after_content_was_known_is_refused(chain: Chain) -> None:
    protocol = json.loads(json.dumps(chain.protocol))
    protocol["tested_system"]["frozen_before_any_bank_content_was_known"] = False
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    with pytest.raises(BlindBankError, match="before any content is known"):
        validate_system_protocol(
            protocol, commitment=chain.commitment, spec=chain.spec, plan=chain.plan,
            isolation_attestation_sha256=str(chain.attestation["attestation_sha256"]),
        )


# ---------------------------------------------------------------------------------------------
# the gate never opens a payload
# ---------------------------------------------------------------------------------------------


def test_the_gate_reports_no_payload_access_at_every_stage(chain: Chain) -> None:
    for stage in ("spec", "sealed", "protocol", "reveal"):
        chain.write_through(stage)
        assert chain.assess()["bank_payload_accessed"] is False


def test_the_readiness_module_never_imports_a_decryption_path() -> None:
    import ast

    source = (REPOSITORY_ROOT / "metamorphosis/m075b_blind_readiness.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not (imported & {"subprocess", "socket", "cryptography", "nacl", "gnupg"})
