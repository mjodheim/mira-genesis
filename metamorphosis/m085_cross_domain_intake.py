"""Fail-closed intake for M085's externally maintained cross-domain task bank.

G4 asks whether knowledge acquired in one domain improves held-out performance in another, against a
fresh agent with the same tools, compute and observation budget. M084 already has that shape —
lineage against fresh organism at matched budget — and fails G4 on two counts: its four stages are
one carrier family over three substrates, and its ablation cost only efficiency.

This module supplies the boundary that fixes the first count. The domains must be written and held by
someone outside the project, and the held-out target must be drawn **after** the scientific protocol
is frozen, so the project cannot choose the domain its organism happens to suit.

M075 built the same kind of boundary for a different question. Its validator hard-codes refusal
thresholds, the `gpt-5.6-sol` agent identity and a `bounded_composed_system_refusal_transfer_only`
claim, so a G4 protocol cannot pass it. This is a separate instrument at the same standard, not a
loosening of that one — and `exact_mcnemar_two_sided` is imported from it rather than restated.

Nothing here signs anything, and nothing here opens, lists, extracts or transports task content.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping

from metamorphosis.m075_private_readiness import (
    PROJECT_IDENTITIES,
    exact_mcnemar_two_sided,
)


ENVELOPE_SCHEMA = "m085-cross-domain-bank-envelope-v1"
PROTOCOL_SCHEMA = "m085-cross-domain-scientific-protocol-v1"
SIGNATURE_NAMESPACE = "mira-m085-cross-domain-bank-v1"
ADAPTER_CONTRACT_VERSION = "m085-domain-adapter-v1"
PAYLOAD_MEDIA_TYPE = "application/vnd.mira.m085-cross-domain-bank+tar"

# Three domains rather than two: with three, the held-out target drawn after freeze cannot be
# guessed at better than one in three, and two source domains show the acquisition is not a quirk
# of a single one.
MINIMUM_DOMAINS = 3
MINIMUM_TASKS_PER_DOMAIN = 8

# The category the whole experiment turns on. M084's ablation cost no correctness because every trap
# had an alternative and the budget was generous; a G4 claim resting on step counts would be weak.
# A correctness-critical task is one where an action is accepted without effect, a later step is only
# valid if that action took effect, and committing on the false premise reaches a terminal state the
# task budget cannot undo. An organism that trusts what an action reported gets these wrong, and
# cannot tell that it did.
MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN = 6

# Six discordant tasks in one direction give an exact two-sided McNemar p of 2/2**6 = 0.03125. Five
# would give 0.0625 and could not clear the 0.05 the protocol freezes, so the threshold and the
# minimum bank size are chosen together rather than independently.
MINIMUM_TRANSFERRED_ONLY_CORRECT = 6
MAXIMUM_FRESH_ONLY_CORRECT = 0
MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P = 0.05

ENVELOPE_PATH = Path("experiments/M085/CROSS_DOMAIN_BANK_ENVELOPE.json")
SIGNATURE_PATH = Path("experiments/M085/CROSS_DOMAIN_BANK_ENVELOPE.sshsig")
ALLOWED_SIGNERS_PATH = Path("experiments/M085/CROSS_DOMAIN_BANK_ALLOWED_SIGNERS")
PROTOCOL_PATH = Path("experiments/M085/CROSS_DOMAIN_SCIENTIFIC_PROTOCOL.json")
RESULT_PATH = Path("experiments/M085/CROSS_DOMAIN_SCIENTIFIC_RESULT.json")

ARMS = ("transferred_lineage", "fresh_agent", "acquisition_ablated")


class M085IntakeError(ValueError):
    """Raised when a candidate bank envelope or scientific protocol weakens its contract."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def scientific_protocol_commitment(protocol: Mapping[str, object]) -> str:
    payload = dict(protocol)
    payload.pop("protocol_commitment_sha256", None)
    return _sha256_bytes(_canonical(payload))


def held_out_domain_index(payload_sha256: str, assignment_salt: str, domain_count: int) -> int:
    """Draw the held-out target domain from the sealed payload digest and a post-freeze salt.

    The project publishes the derivation before it knows the salt, and the maintainer releases the
    salt only after the protocol is frozen. Choosing the target after seeing the domains would let
    the project pick the one its organism happens to suit, which is the whole failure this prevents.
    """

    if not _is_sha256(payload_sha256):
        raise M085IntakeError("payload digest is not a sha256 hex string")
    if not isinstance(assignment_salt, str) or not assignment_salt:
        raise M085IntakeError("assignment salt is missing")
    if not isinstance(domain_count, int) or isinstance(domain_count, bool) or domain_count < 2:
        raise M085IntakeError("domain count must be an integer of at least two")
    digest = hashlib.sha256(
        b"m085-target-assignment-v1\0"
        + payload_sha256.encode("ascii") + b"\0"
        + assignment_salt.encode("utf-8"),
    ).digest()
    return int.from_bytes(digest[:8], "big") % domain_count


def validate_bank_envelope(envelope: Mapping[str, object], *, signature_verified: bool) -> None:
    """Validate metadata only. No task content is accepted, requested or exposed."""

    expected_keys = {
        "schema", "status", "bank_id", "created_at", "maintainer_identity", "maintainer_role",
        "maintainer_independence_attested", "conflicts_disclosed", "payload_sha256",
        "payload_bytes", "payload_media_type", "payload_custody",
        "payload_revealed_to_policy_authors", "adapter_contract_version", "domain_count",
        "task_count", "domains", "materially_distinct_domains_attested",
        "correctness_critical_definition_accepted", "evaluator_owned_success_attested",
        "public_task_reuse_excluded_attested", "signature_namespace",
        "maintainer_public_key_sha256",
    }
    if set(envelope) != expected_keys:
        raise M085IntakeError("bank envelope fields differ from the closed metadata schema")
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("status") != "sealed_unrevealed":
        raise M085IntakeError("bank envelope schema or status drifted")

    identity = envelope.get("maintainer_identity")
    if not isinstance(identity, str) or not identity.strip():
        raise M085IntakeError("bank envelope lacks maintainer identity")
    if identity.strip().casefold() in PROJECT_IDENTITIES:
        raise M085IntakeError("project author cannot attest independent task-bank maintenance")
    if (
        envelope.get("maintainer_role") != "independent-task-bank-maintainer"
        or envelope.get("maintainer_independence_attested") is not True
        or not isinstance(envelope.get("conflicts_disclosed"), str)
        or not str(envelope.get("conflicts_disclosed")).strip()
    ):
        raise M085IntakeError("independent-maintainer attestation is incomplete")

    if (
        not isinstance(envelope.get("bank_id"), str) or not envelope.get("bank_id")
        or not isinstance(envelope.get("created_at"), str) or not envelope.get("created_at")
        or not _is_sha256(envelope.get("payload_sha256"))
        or not isinstance(envelope.get("payload_bytes"), int)
        or isinstance(envelope.get("payload_bytes"), bool)
        or int(envelope["payload_bytes"]) < 1
        or envelope.get("payload_media_type") != PAYLOAD_MEDIA_TYPE
        or envelope.get("payload_custody") != "external-until-protocol-freeze"
        or envelope.get("payload_revealed_to_policy_authors") is not False
        or envelope.get("adapter_contract_version") != ADAPTER_CONTRACT_VERSION
    ):
        raise M085IntakeError("sealed payload metadata is malformed")

    if (
        envelope.get("materially_distinct_domains_attested") is not True
        or envelope.get("correctness_critical_definition_accepted") is not True
        or envelope.get("evaluator_owned_success_attested") is not True
        or envelope.get("public_task_reuse_excluded_attested") is not True
    ):
        raise M085IntakeError("bank scope attestations are incomplete")

    domains = envelope.get("domains")
    domain_count = envelope.get("domain_count")
    task_count = envelope.get("task_count")
    if (
        not isinstance(domains, list) or len(domains) < MINIMUM_DOMAINS
        or not isinstance(domain_count, int) or isinstance(domain_count, bool)
        or domain_count != len(domains)
    ):
        raise M085IntakeError("bank does not declare at least three coherent domains")

    seen_ids: set[str] = set()
    seen_statements: set[str] = set()
    counted_tasks = 0
    for domain in domains:
        if not isinstance(domain, Mapping) or set(domain) != {
            "opaque_domain_id", "task_count", "correctness_critical_tasks",
            "material_difference_statement_sha256",
        }:
            raise M085IntakeError("domain metadata is not opaque and closed")
        domain_id = domain.get("opaque_domain_id")
        tasks = domain.get("task_count")
        critical = domain.get("correctness_critical_tasks")
        statement = domain.get("material_difference_statement_sha256")
        if (
            not isinstance(domain_id, str) or len(domain_id) != 23
            or not domain_id.startswith("opaque-")
            or any(character not in "0123456789abcdef" for character in domain_id[7:])
            or domain_id in seen_ids
        ):
            raise M085IntakeError("domain identifier is malformed or repeated")
        if (
            not isinstance(tasks, int) or isinstance(tasks, bool)
            or tasks < MINIMUM_TASKS_PER_DOMAIN
            or not isinstance(critical, int) or isinstance(critical, bool)
            or critical < MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN
            or critical > tasks
        ):
            raise M085IntakeError("domain lacks the minimum correctness-critical coverage")
        # Distinct digests prove the maintainer wrote a different justification for each domain
        # without revealing any of them. After payload release the statements are checked against
        # these digests, so the attestation is falsifiable rather than a promise.
        if not _is_sha256(statement) or statement in seen_statements:
            raise M085IntakeError(
                "each domain needs its own material-difference statement digest"
            )
        seen_ids.add(domain_id)
        seen_statements.add(str(statement))
        counted_tasks += tasks

    if not isinstance(task_count, int) or isinstance(task_count, bool) or task_count != counted_tasks:
        raise M085IntakeError("declared task count does not reconcile with the domains")

    if (
        envelope.get("signature_namespace") != SIGNATURE_NAMESPACE
        or not _is_sha256(envelope.get("maintainer_public_key_sha256"))
        or signature_verified is not True
    ):
        raise M085IntakeError("bank envelope signature is not independently verified")


def validate_scientific_protocol(
    protocol: Mapping[str, object], *, envelope_raw_sha256: str, envelope: Mapping[str, object],
) -> None:
    """Validate the exact pre-reveal causal and claim boundary for the G4 attempt."""

    expected_keys = {
        "schema", "status", "date_frozen", "scientific_result_exists", "payload_revealed",
        "bank_envelope_raw_sha256", "bank_id", "bank_payload_sha256", "maintainer_identity",
        "maintainer_public_key_sha256", "assignment_salt_commitment_sha256",
        "protocol_commitment_sha256", "parent_result", "organism", "budgets", "attempt_policy",
        "causal_design", "thresholds", "information_boundary", "reproduction", "claim_boundary",
    }
    if set(protocol) != expected_keys:
        raise M085IntakeError("scientific protocol fields differ from the closed schema")
    if (
        protocol.get("schema") != PROTOCOL_SCHEMA
        or protocol.get("status") != "frozen_after_envelope_before_payload_reveal"
        or protocol.get("scientific_result_exists") is not False
        or protocol.get("payload_revealed") is not False
        or not isinstance(protocol.get("date_frozen"), str) or not protocol.get("date_frozen")
    ):
        raise M085IntakeError("scientific protocol scope is malformed")
    if protocol.get("protocol_commitment_sha256") != scientific_protocol_commitment(protocol):
        raise M085IntakeError("scientific protocol commitment drifted")

    if not _is_sha256(envelope_raw_sha256) or protocol.get(
        "bank_envelope_raw_sha256"
    ) != envelope_raw_sha256:
        raise M085IntakeError("scientific protocol does not bind the signed envelope")
    if (
        protocol.get("bank_id") != envelope.get("bank_id")
        or protocol.get("bank_payload_sha256") != envelope.get("payload_sha256")
        or protocol.get("maintainer_identity") != envelope.get("maintainer_identity")
        or protocol.get("maintainer_public_key_sha256")
        != envelope.get("maintainer_public_key_sha256")
        or not _is_sha256(protocol.get("assignment_salt_commitment_sha256"))
    ):
        raise M085IntakeError("scientific protocol envelope metadata drifted")

    organism = protocol.get("organism")
    if not isinstance(organism, Mapping) or set(organism) != {
        "lineage_module", "adapter_contract_version", "policy_commit", "code_sha256",
    }:
        raise M085IntakeError("organism freeze is incomplete")
    if (
        organism.get("adapter_contract_version") != ADAPTER_CONTRACT_VERSION
        or not isinstance(organism.get("policy_commit"), str)
        or len(str(organism.get("policy_commit"))) != 40
        or any(c not in "0123456789abcdef" for c in str(organism.get("policy_commit")))
        or not isinstance(organism.get("code_sha256"), Mapping)
        or not organism.get("code_sha256")
        or any(
            not isinstance(path, str) or not path or Path(path).is_absolute()
            or ".." in Path(path).parts
            for path in organism["code_sha256"]
        )
        or any(not _is_sha256(value) for value in organism["code_sha256"].values())
    ):
        raise M085IntakeError("organism identity is malformed")

    if protocol.get("causal_design") != {
        "arms": list(ARMS),
        "unit": "held-out-target-domain-task",
        "each_task_runs_once_per_arm": True,
        "matched_budget_across_arms": True,
        "held_out_target_drawn_after_freeze": True,
        "held_out_target_derivation": (
            "sha256(m085-target-assignment-v1\\0+payload_sha256+\\0+salt) mod domain_count"
        ),
        "assignment_salt_revealed_only_after_protocol_freeze": True,
        "source_domains_are_every_domain_except_the_target": True,
        "acquisition_ablated_must_match_fresh_agent": True,
        "primary_outcome": "evaluator-owned-correct-terminal-state-in-the-held-out-domain",
        "primary_paired_test": "two-sided-exact-mcnemar",
        "cost_metrics_reported_but_not_decisive": True,
    }:
        raise M085IntakeError("paired causal design drifted")

    if protocol.get("thresholds") != {
        "minimum_domains": MINIMUM_DOMAINS,
        "minimum_tasks_per_domain": MINIMUM_TASKS_PER_DOMAIN,
        "minimum_correctness_critical_tasks_per_domain": (
            MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN
        ),
        "minimum_transferred_only_correct": MINIMUM_TRANSFERRED_ONLY_CORRECT,
        "maximum_fresh_only_correct": MAXIMUM_FRESH_ONLY_CORRECT,
        "maximum_two_sided_exact_mcnemar_p": MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P,
        "require_zero_faulted_episodes": True,
        "require_evaluator_owned_success": True,
        "require_acquisition_ablated_to_match_fresh_agent": True,
    }:
        raise M085IntakeError("scientific thresholds drifted")

    if protocol.get("information_boundary") != {
        "goal_and_affordances_visible_to_organism": True,
        "observations_visible_to_organism": True,
        "domain_identity_hidden_from_the_organism": True,
        "evaluator_solutions_and_labels_hidden": True,
        "payload_unavailable_before_protocol_freeze": True,
        "target_domain_unknown_before_protocol_freeze": True,
    }:
        raise M085IntakeError("information boundary drifted")

    if protocol.get("reproduction") != {
        "required_before_g4_advance": True,
        "separate_bank": True,
        "separate_maintainer": True,
        "same_organism_budgets_thresholds_and_analysis": True,
        "first_result_preserved_regardless_of_reproduction": True,
    }:
        raise M085IntakeError("independent reproduction contract drifted")

    if protocol.get("claim_boundary") != {
        "agi": False,
        "genesis_gate_2": False,
        "genesis_gate_3": False,
        "general_autonomy": False,
        "open_ended_evolution": False,
        "closes_generality_gate_g4": False,
        "bounded_cross_domain_transfer_of_one_acquired_policy_only": True,
    }:
        raise M085IntakeError("scientific claim boundary drifted")

    if protocol.get("parent_result") != "M084":
        raise M085IntakeError("scientific protocol does not name its parent result")
    if not isinstance(protocol.get("budgets"), Mapping) or not protocol["budgets"]:
        raise M085IntakeError("budgets are missing")
    if not isinstance(protocol.get("attempt_policy"), Mapping) or protocol["attempt_policy"] != {
        "attempts_per_task_arm": 1,
        "fresh_environment_per_task": True,
        "retry_permitted": False,
        "replacement_permitted": False,
        "resume_permitted": False,
        "preserve_every_outcome": True,
    }:
        raise M085IntakeError("single-attempt policy drifted")


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


def assess_readiness(
    root: Path, *, signature_verifier: Callable[[bytes, Path, Path, str, str], bool] | None = None,
) -> dict[str, object]:
    """Assess readiness without revealing or accessing any task content."""

    resolved = root.resolve()
    blockers: list[str] = []
    if (resolved / RESULT_PATH).exists():
        blockers.append("a scientific result already exists before readiness confirmation")

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
                    envelope_raw, signature_file, allowed_signers, identity, SIGNATURE_NAMESPACE,
                )
            except OSError:
                signature_verified = False
    if envelope is not None:
        try:
            validate_bank_envelope(envelope, signature_verified=signature_verified)
        except M085IntakeError as exc:
            blockers.append(str(exc))

    protocol, _, error = _load_object(resolved / PROTOCOL_PATH)
    if error:
        blockers.append(error)
    if protocol is not None and envelope is not None and envelope_raw is not None:
        try:
            validate_scientific_protocol(
                protocol, envelope_raw_sha256=_sha256_bytes(envelope_raw), envelope=envelope,
            )
        except M085IntakeError as exc:
            blockers.append(str(exc))

    return {
        "schema": "m085-cross-domain-readiness-v1",
        "ready_for_payload_reveal": not blockers,
        "scientific_result_exists": (resolved / RESULT_PATH).exists(),
        "payload_accessed": False,
        "target_domain_drawn": False,
        "blockers": blockers,
        "required_minimum_domains": MINIMUM_DOMAINS,
        "required_minimum_tasks_per_domain": MINIMUM_TASKS_PER_DOMAIN,
        "required_minimum_correctness_critical_tasks_per_domain": (
            MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN
        ),
        "authored_domains_permitted_as_g4_evidence": False,
        "g4_advance_permitted_without_reproduction": False,
        "agi_claim_permitted": False,
    }


__all__ = [
    "ADAPTER_CONTRACT_VERSION", "ALLOWED_SIGNERS_PATH", "ARMS", "ENVELOPE_PATH", "ENVELOPE_SCHEMA",
    "MAXIMUM_FRESH_ONLY_CORRECT", "MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P",
    "MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN", "MINIMUM_DOMAINS",
    "MINIMUM_TASKS_PER_DOMAIN", "MINIMUM_TRANSFERRED_ONLY_CORRECT", "M085IntakeError",
    "PAYLOAD_MEDIA_TYPE", "PROTOCOL_PATH", "PROTOCOL_SCHEMA", "RESULT_PATH", "SIGNATURE_NAMESPACE",
    "SIGNATURE_PATH", "assess_readiness", "exact_mcnemar_two_sided", "held_out_domain_index",
    "scientific_protocol_commitment", "validate_bank_envelope", "validate_scientific_protocol",
]
