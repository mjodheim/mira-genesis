"""Fail-closed pre-private readiness gates for M075.

The public M075 result cannot create its own independent evidence. This module validates only the
small, signed envelope an external task-bank maintainer may disclose before policy freeze and the
scientific protocol that must bind that envelope before payload reveal. It never decrypts, opens,
lists or executes private task content.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from math import comb
from pathlib import Path
from typing import Callable, Mapping


ENVELOPE_SCHEMA = "m075-private-bank-envelope-v1"
PROTOCOL_SCHEMA = "m075-private-scientific-protocol-v1"
SIGNATURE_NAMESPACE = "mira-m075-private-bank-v1"
PUBLIC_PROTOCOL_COMMITMENT = "ef024062d5fde3e385749153f471ef1dfc0c3bd664db859db88c78d70e94c899"
PUBLIC_RESULT_RAW_SHA256 = "dadd202886e866e31be5cefb130e9e231f7739a0b49166f8d0c1dd2766acf949"
PROJECT_IDENTITIES = frozenset({"anthony mets", "mjodheim"})

MINIMUM_DOMAINS = 4
MINIMUM_MATCHED_CAPABILITY_PAIRS = 8
MINIMUM_TRUE_REFUSALS = 6

ENVELOPE_PATH = Path("experiments/M075/PRIVATE_BANK_ENVELOPE.json")
SIGNATURE_PATH = Path("experiments/M075/PRIVATE_BANK_ENVELOPE.sshsig")
ALLOWED_SIGNERS_PATH = Path("experiments/M075/PRIVATE_BANK_ALLOWED_SIGNERS")
PROTOCOL_PATH = Path("experiments/M075/PRIVATE_SCIENTIFIC_PROTOCOL.json")
RESULT_PATH = Path("experiments/M075/PRIVATE_SCIENTIFIC_RESULT.json")


class M075PrivateReadinessError(ValueError):
    """Raised when a candidate private boundary weakens or leaks its contract."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def private_protocol_commitment(protocol: Mapping[str, object]) -> str:
    payload = dict(protocol)
    payload.pop("protocol_commitment_sha256", None)
    return _sha256_bytes(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8"))


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def exact_mcnemar_two_sided(context_only: int, baseline_only: int) -> Fraction:
    """Return the exact two-sided sign-test p value for paired discordant outcomes."""

    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in (context_only, baseline_only)
    ):
        raise M075PrivateReadinessError("McNemar discordant counts must be non-negative integers")
    discordant = context_only + baseline_only
    if discordant == 0:
        return Fraction(1, 1)
    tail = sum(comb(discordant, index) for index in range(min(
        context_only, baseline_only,
    ) + 1))
    return min(Fraction(1, 1), Fraction(2 * tail, 2 ** discordant))


def _load_object(path: Path) -> tuple[dict[str, object] | None, bytes | None, str | None]:
    if not path.exists():
        return None, None, f"missing {path.name}"
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, None, f"malformed {path.name}: {exc}"
    if not isinstance(value, dict):
        return None, None, f"malformed {path.name}: expected one JSON object"
    return value, raw, None


def validate_private_envelope(
    envelope: Mapping[str, object], *, signature_verified: bool,
) -> None:
    """Validate metadata without accepting or exposing private payload content."""

    expected_keys = {
        "schema", "status", "bank_id", "created_at", "maintainer_identity",
        "maintainer_role", "maintainer_independence_attested", "conflicts_disclosed",
        "payload_sha256", "payload_bytes", "payload_media_type", "payload_custody",
        "payload_revealed_to_policy_authors", "task_count", "matched_capability_pairs",
        "domains", "materially_cross_domain_attested", "public_task_reuse_excluded_attested",
        "evaluator_owned_success_attested", "signature_namespace",
        "maintainer_public_key_sha256",
    }
    if set(envelope) != expected_keys:
        raise M075PrivateReadinessError(
            "private envelope fields differ from the closed metadata schema"
        )
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("status") != "sealed_unrevealed":
        raise M075PrivateReadinessError("private envelope schema or status drifted")
    identity = envelope.get("maintainer_identity")
    if not isinstance(identity, str) or not identity.strip():
        raise M075PrivateReadinessError("private envelope lacks maintainer identity")
    if identity.strip().casefold() in PROJECT_IDENTITIES:
        raise M075PrivateReadinessError(
            "project author cannot attest independent task-bank maintenance"
        )
    if (
        envelope.get("maintainer_role") != "independent-task-bank-maintainer"
        or envelope.get("maintainer_independence_attested") is not True
        or not isinstance(envelope.get("conflicts_disclosed"), str)
        or not str(envelope.get("conflicts_disclosed")).strip()
    ):
        raise M075PrivateReadinessError("independent-maintainer attestation is incomplete")
    if (
        not isinstance(envelope.get("bank_id"), str) or not envelope.get("bank_id")
        or not isinstance(envelope.get("created_at"), str) or not envelope.get("created_at")
        or not _is_sha256(envelope.get("payload_sha256"))
        or not isinstance(envelope.get("payload_bytes"), int)
        or isinstance(envelope.get("payload_bytes"), bool)
        or int(envelope["payload_bytes"]) < 1
        or envelope.get("payload_media_type") != "application/vnd.mira.m075-private-bank+tar"
        or envelope.get("payload_custody") != "external-until-protocol-freeze"
        or envelope.get("payload_revealed_to_policy_authors") is not False
    ):
        raise M075PrivateReadinessError("sealed private payload metadata is malformed")
    if (
        envelope.get("materially_cross_domain_attested") is not True
        or envelope.get("public_task_reuse_excluded_attested") is not True
        or envelope.get("evaluator_owned_success_attested") is not True
    ):
        raise M075PrivateReadinessError("private bank scope attestations are incomplete")
    domains = envelope.get("domains")
    pairs = envelope.get("matched_capability_pairs")
    tasks = envelope.get("task_count")
    if (
        not isinstance(domains, list) or len(domains) < MINIMUM_DOMAINS
        or not isinstance(pairs, int) or isinstance(pairs, bool)
        or pairs < MINIMUM_MATCHED_CAPABILITY_PAIRS
        or not isinstance(tasks, int) or isinstance(tasks, bool) or tasks != pairs * 2
    ):
        raise M075PrivateReadinessError("private bank lacks minimum cross-domain paired coverage")
    seen_domains: set[str] = set()
    counted_pairs = 0
    for domain in domains:
        if not isinstance(domain, Mapping) or set(domain) != {
            "opaque_domain_id", "matched_capability_pairs",
        }:
            raise M075PrivateReadinessError("private domain metadata is not opaque and closed")
        domain_id, domain_pairs = domain.get("opaque_domain_id"), domain.get(
            "matched_capability_pairs"
        )
        if (
            not isinstance(domain_id, str) or len(domain_id) != 23
            or not domain_id.startswith("opaque-")
            or any(character not in "0123456789abcdef" for character in domain_id[7:])
            or domain_id in seen_domains
            or not isinstance(domain_pairs, int) or isinstance(domain_pairs, bool)
            or domain_pairs < 2
        ):
            raise M075PrivateReadinessError("private domain coverage is malformed")
        seen_domains.add(domain_id)
        counted_pairs += domain_pairs
    if counted_pairs != pairs:
        raise M075PrivateReadinessError("private domain pair counts do not reconcile")
    if (
        envelope.get("signature_namespace") != SIGNATURE_NAMESPACE
        or not _is_sha256(envelope.get("maintainer_public_key_sha256"))
        or signature_verified is not True
    ):
        raise M075PrivateReadinessError("private envelope signature is not independently verified")


def validate_private_protocol(
    protocol: Mapping[str, object], *, envelope_raw_sha256: str,
    envelope: Mapping[str, object],
) -> None:
    """Validate the exact pre-reveal causal and claim boundary."""

    expected_keys = {
        "schema", "status", "date_frozen", "scientific_result_exists",
        "private_payload_revealed", "private_bank_envelope_raw_sha256", "private_bank_id",
        "private_bank_payload_sha256", "maintainer_identity",
        "maintainer_public_key_sha256", "assignment_salt_commitment_sha256",
        "protocol_commitment_sha256", "public_development_boundary", "agent", "budgets",
        "attempt_policy", "causal_design", "thresholds", "information_boundary",
        "reproduction", "claim_boundary",
    }
    if set(protocol) != expected_keys:
        raise M075PrivateReadinessError("private protocol fields differ from the closed schema")
    if (
        protocol.get("schema") != PROTOCOL_SCHEMA
        or protocol.get("status") != "frozen_after_envelope_before_payload_reveal"
        or protocol.get("scientific_result_exists") is not False
        or protocol.get("private_payload_revealed") is not False
        or not isinstance(protocol.get("date_frozen"), str) or not protocol.get("date_frozen")
    ):
        raise M075PrivateReadinessError("private scientific protocol scope is malformed")
    if protocol.get("protocol_commitment_sha256") != private_protocol_commitment(protocol):
        raise M075PrivateReadinessError("private scientific protocol commitment drifted")
    if not _is_sha256(envelope_raw_sha256) or protocol.get(
        "private_bank_envelope_raw_sha256"
    ) != envelope_raw_sha256:
        raise M075PrivateReadinessError("private protocol does not bind the signed envelope")
    if protocol.get("private_bank_id") != envelope.get("bank_id"):
        raise M075PrivateReadinessError("private protocol bank identity drifted")
    if (
        protocol.get("private_bank_payload_sha256") != envelope.get("payload_sha256")
        or protocol.get("maintainer_identity") != envelope.get("maintainer_identity")
        or protocol.get("maintainer_public_key_sha256")
        != envelope.get("maintainer_public_key_sha256")
        or not _is_sha256(protocol.get("assignment_salt_commitment_sha256"))
    ):
        raise M075PrivateReadinessError("private protocol envelope metadata drifted")
    if protocol.get("public_development_boundary") != {
        "protocol_commitment_sha256": PUBLIC_PROTOCOL_COMMITMENT,
        "result_raw_sha256": PUBLIC_RESULT_RAW_SHA256,
        "public_tasks_permitted_as_scientific_evidence": False,
        "public_result_claimed_as_causal": False,
        "prompt_tuning_closed_by": "D041",
    }:
        raise M075PrivateReadinessError("public/private evidence boundary drifted")
    agent = protocol.get("agent")
    if not isinstance(agent, Mapping) or set(agent) != {
        "backend_id", "model", "codex_cli_version", "policy_commit", "code_sha256",
    }:
        raise M075PrivateReadinessError("private protocol agent freeze is incomplete")
    if (
        agent.get("backend_id") != "openai-codex-exec-v1"
        or agent.get("model") != "gpt-5.6-sol"
        or agent.get("codex_cli_version") != "codex-cli 0.147.0"
        or not isinstance(agent.get("policy_commit"), str)
        or len(str(agent.get("policy_commit"))) != 40
        or any(character not in "0123456789abcdef" for character in str(agent.get("policy_commit")))
        or not isinstance(agent.get("code_sha256"), Mapping)
        or not agent.get("code_sha256")
        or any(
            not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts
            for path in agent["code_sha256"]
        )
        or any(not _is_sha256(value) for value in agent["code_sha256"].values())
    ):
        raise M075PrivateReadinessError("private protocol agent identity is malformed")
    if protocol.get("budgets") != {
        "max_agent_steps": 4,
        "command_timeout_seconds": 30,
        "command_output_chars": 65_536,
        "codex_decision_timeout_seconds": 180,
        "external_evaluator_timeout_seconds": 30,
    }:
        raise M075PrivateReadinessError("private scientific budgets drifted")
    if protocol.get("attempt_policy") != {
        "attempts_per_task_condition": 1,
        "fresh_container_per_episode": True,
        "concurrency": 1,
        "retry_permitted": False,
        "replacement_permitted": False,
        "resume_permitted": False,
        "preserve_every_outcome": True,
    }:
        raise M075PrivateReadinessError("private single-attempt policy drifted")
    if protocol.get("causal_design") != {
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
    }:
        raise M075PrivateReadinessError("private paired causal design drifted")
    if protocol.get("thresholds") != {
        "minimum_domains": MINIMUM_DOMAINS,
        "minimum_matched_capability_pairs": MINIMUM_MATCHED_CAPABILITY_PAIRS,
        "minimum_context_true_refusals": MINIMUM_TRUE_REFUSALS,
        "maximum_context_false_refusals": 0,
        "require_all_context_feasible_external_success": True,
        "require_zero_impossible_external_success": True,
        "minimum_context_wasted_steps_advantage": 8,
        "minimum_context_only_correct_terminal_decisions": 6,
        "maximum_baseline_only_correct_terminal_decisions": 0,
        "maximum_two_sided_exact_mcnemar_p": 0.05,
        "require_zero_faulted_episodes": True,
    }:
        raise M075PrivateReadinessError("private scientific thresholds drifted")
    if protocol.get("information_boundary") != {
        "task_instruction_visible_to_model": True,
        "action_observations_visible_to_model": True,
        "epistemic_self_evidence_visible_only_in_context_condition": True,
        "labels_certificates_solutions_evaluators_outcomes_hidden": True,
        "condition_identity_hidden": True,
        "private_payload_unavailable_before_protocol_freeze": True,
    }:
        raise M075PrivateReadinessError("private information boundary drifted")
    if protocol.get("reproduction") != {
        "required_before_h21_support": True,
        "separate_bank": True,
        "separate_maintainer": True,
        "same_agent_budgets_thresholds_and_analysis": True,
        "first_result_preserved_regardless_of_reproduction": True,
    }:
        raise M075PrivateReadinessError("independent reproduction contract drifted")
    if protocol.get("claim_boundary") != {
        "agi": False,
        "genesis_gate_2": False,
        "genesis_gate_3": False,
        "mathematical_impossibility": False,
        "bounded_composed_system_refusal_transfer_only": True,
    }:
        raise M075PrivateReadinessError("private scientific claim boundary drifted")


def assess_repository_readiness(
    root: Path, *, signature_verifier: Callable[[bytes, Path, Path, str, str], bool] | None = None,
) -> dict[str, object]:
    """Assess readiness without revealing or accessing any private payload."""

    resolved = root.resolve()
    blockers: list[str] = []
    if (resolved / RESULT_PATH).exists():
        blockers.append("private scientific result already exists before readiness confirmation")
    envelope, envelope_raw, error = _load_object(resolved / ENVELOPE_PATH)
    if error:
        blockers.append(error)
    signature_file = resolved / SIGNATURE_PATH
    allowed_signers = resolved / ALLOWED_SIGNERS_PATH
    if not signature_file.is_file():
        blockers.append(f"missing {SIGNATURE_PATH.name}")
    if not allowed_signers.is_file():
        blockers.append(f"missing {ALLOWED_SIGNERS_PATH.name}")
    signature_verified = False
    if (
        envelope is not None and envelope_raw is not None and signature_file.is_file()
        and allowed_signers.is_file() and signature_verifier is not None
    ):
        identity = envelope.get("maintainer_identity")
        if isinstance(identity, str):
            try:
                signature_verified = signature_verifier(
                    envelope_raw, signature_file, allowed_signers,
                    identity, SIGNATURE_NAMESPACE,
                )
            except OSError:
                signature_verified = False
    if envelope is not None:
        try:
            validate_private_envelope(envelope, signature_verified=signature_verified)
        except M075PrivateReadinessError as exc:
            blockers.append(str(exc))
    protocol, _, error = _load_object(resolved / PROTOCOL_PATH)
    if error:
        blockers.append(error)
    if protocol is not None and envelope is not None and envelope_raw is not None:
        try:
            validate_private_protocol(
                protocol, envelope_raw_sha256=_sha256_bytes(envelope_raw), envelope=envelope,
            )
        except M075PrivateReadinessError as exc:
            blockers.append(str(exc))
    return {
        "schema": "m075-pre-private-readiness-v1",
        "ready_for_private_payload_reveal": not blockers,
        "scientific_result_exists": (resolved / RESULT_PATH).exists(),
        "private_payload_accessed": False,
        "blockers": blockers,
        "required_minimum_domains": MINIMUM_DOMAINS,
        "required_minimum_matched_capability_pairs": MINIMUM_MATCHED_CAPABILITY_PAIRS,
        "public_development_is_scientific_evidence": False,
        "agi_claim_permitted": False,
    }


__all__ = [
    "ALLOWED_SIGNERS_PATH", "ENVELOPE_PATH", "ENVELOPE_SCHEMA", "MINIMUM_DOMAINS",
    "MINIMUM_MATCHED_CAPABILITY_PAIRS", "MINIMUM_TRUE_REFUSALS",
    "M075PrivateReadinessError", "PROTOCOL_PATH", "PROTOCOL_SCHEMA", "RESULT_PATH",
    "SIGNATURE_NAMESPACE", "SIGNATURE_PATH", "assess_repository_readiness",
    "exact_mcnemar_two_sided", "private_protocol_commitment", "validate_private_envelope",
    "validate_private_protocol",
]
