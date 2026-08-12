"""M075-B — the fail-closed gate for one blind-generated sealed bank.

M075 is blocked on a person. `experiments/M075/PRE_PRIVATE_CAUSAL_DESIGN.md` requires an
independent human maintainer who writes a private feasible/capability-absent bank and withholds it
until the scientific protocol is frozen, and issue #112 is still looking for one. **Nothing in this
module changes that requirement, and nothing here may be reported as satisfying it.**

M075-B is a separate, explicitly weaker successor. It asks a narrower question: how much of M075's
boundary is scientific, and how much is the custody mechanism chosen in 2026?

* *Scientific and preserved here.* The bank must exist before the tested system's protocol is
  frozen; the project must commit publicly, by digest, to how it will be scored before it can see
  a task; success must be decided from terminal environment state; the bank is materialized once
  and the first result stands.
* *Custody, and replaceable.* The identity of whoever holds the payload. M075 achieves withholding
  through a person's discretion; M075-B achieves it through encryption plus a signed reveal gate.
* *Scientific and NOT replaceable.* That a mind outside the project chose the subject matter. A
  model given no project context is blind, not independent. Its checkpoint's training corpus is
  not under anyone's control here, and no human judgement outside the project was exercised.

So M075-B can produce evidence at the `blind_generated_sealed_bank` tier and can never produce
evidence at the `human_maintained_sealed_bank` tier that M075's own frozen protocol requires for
H21. The two live side by side; the weaker one does not close the stronger one.

This module never decrypts, opens, lists or executes bank content.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Callable, Mapping

from metamorphosis.blind_bank_isolation import validate_attestation
from metamorphosis.blind_bank_protocol import (
    BlindBankError,
    REVEAL_SIGNATURE_NAMESPACE,
    commitment_of,
    sealed_run_binding_problems,
    sha256_hex,
    spec_commitment,
    validate_generation_ledger,
    validate_generator_spec,
    validate_public_commitment,
    validate_reveal_authorization,
)
from metamorphosis.m075_private_readiness import exact_mcnemar_two_sided


MILESTONE = "M075B"
ANALYSIS_PLAN_SCHEMA = "mira-blind-bank-analysis-plan-v1"
SYSTEM_PROTOCOL_SCHEMA = "mira-blind-bank-system-protocol-v1"
REPORT_SCHEMA = "m075b-blind-bank-readiness-v1"

# The same shape M075 requires of a human maintainer: four materially different domains and eight
# matched pairs. A blind bank that were structurally easier would be weaker on both counts at once.
MINIMUM_DOMAINS = 4
MINIMUM_PAIRS_PER_DOMAIN = 2
MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P = Fraction(1, 20)

EXPERIMENT_DIRECTORY = Path("experiments/M075B")
GENERATOR_SPEC_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json"
GENERATOR_PROMPT_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_PROMPT.txt"
ANALYSIS_PLAN_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json"
GENERATION_LEDGER_PATH = EXPERIMENT_DIRECTORY / "GENERATION_LEDGER.json"
ISOLATION_ATTESTATION_PATH = EXPERIMENT_DIRECTORY / "ISOLATION_ATTESTATION.json"
BANK_COMMITMENT_PATH = EXPERIMENT_DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
SYSTEM_PROTOCOL_PATH = EXPERIMENT_DIRECTORY / "SYSTEM_PROTOCOL.json"
REVEAL_AUTHORIZATION_PATH = EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.json"
REVEAL_SIGNATURE_PATH = EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.sshsig"
REVEAL_ALLOWED_SIGNERS_PATH = EXPERIMENT_DIRECTORY / "REVEAL_ALLOWED_SIGNERS"
RESULT_PATH = EXPERIMENT_DIRECTORY / "RESULT.json"

# Every digest-bearing artifact this milestone will ever write, registered before any of them
# exists. See `missing_gitattributes_entries`.
DIGEST_BEARING_PATHS = (
    "experiments/M075B/GENERATOR_SPEC.json",
    "experiments/M075B/ANALYSIS_PLAN.json",
    "experiments/M075B/GENERATION_LEDGER.json",
    "experiments/M075B/ISOLATION_ATTESTATION.json",
    "experiments/M075B/PUBLIC_BANK_COMMITMENT.json",
    "experiments/M075B/SYSTEM_PROTOCOL.json",
    "experiments/M075B/REVEAL_AUTHORIZATION.json",
    "experiments/M075B/RESULT.json",
)


class M075BReadinessError(BlindBankError):
    """Raised when the M075-B boundary weakens, drifts or is crossed out of order."""


def analysis_plan_commitment(plan: Mapping[str, object]) -> str:
    return commitment_of(plan, omit="plan_commitment_sha256")


def system_protocol_commitment(protocol: Mapping[str, object]) -> str:
    return commitment_of(protocol, omit="protocol_commitment_sha256")


def validate_analysis_plan(plan: Mapping[str, object], *, spec: Mapping[str, object]) -> None:
    """Validate the scoring rule, which is frozen *before* the bank is materialized.

    The bank's size determines which p values are reachable at all, so a threshold chosen after
    seeing the bank would be fitted to it even without seeing a single task. Freezing the plan in
    the same act as the generator spec removes that degree of freedom, and the attainability check
    below removes the opposite defect: a threshold no draw could ever meet, or one no draw could
    ever miss.
    """

    expected = {
        "schema", "milestone", "status", "date_frozen", "hypothesis_id", "evidence_tier",
        "unit", "conditions", "primary_test", "thresholds", "attainability", "non_retry",
        "claim_boundary", "plan_commitment_sha256",
    }
    if not isinstance(plan, Mapping) or set(plan) != expected:
        raise M075BReadinessError("analysis plan fields differ from the closed schema")
    if plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise M075BReadinessError("analysis plan schema drifted")
    if plan.get("milestone") != MILESTONE:
        raise M075BReadinessError("analysis plan milestone drifted")
    if plan.get("status") != "frozen_before_generation":
        raise M075BReadinessError("the analysis plan must be frozen before the bank exists")
    if plan.get("hypothesis_id") != "H21":
        raise M075BReadinessError("M075-B addresses H21 and no other hypothesis")
    if plan.get("evidence_tier") != "blind_generated_sealed_bank":
        raise M075BReadinessError("analysis plan evidence tier drifted")
    if plan.get("unit") != "task-instance":
        raise M075BReadinessError("analysis plan unit drifted")
    if plan.get("conditions") != ["baseline-structured-request", "epistemic-context-request"]:
        raise M075BReadinessError("analysis plan conditions drifted")
    if plan.get("primary_test") != "two-sided-exact-mcnemar":
        raise M075BReadinessError("analysis plan primary test drifted")
    if plan.get("plan_commitment_sha256") != analysis_plan_commitment(plan):
        raise M075BReadinessError("analysis plan commitment drifted")

    thresholds = plan.get("thresholds")
    if not isinstance(thresholds, Mapping) or set(thresholds) != {
        "minimum_context_true_refusals", "maximum_context_false_refusals",
        "require_all_feasible_external_success", "require_zero_impossible_external_success",
        "minimum_context_only_correct_terminal_decisions",
        "maximum_baseline_only_correct_terminal_decisions",
        "maximum_two_sided_exact_mcnemar_p", "require_zero_faulted_episodes",
    }:
        raise M075BReadinessError("analysis plan threshold fields differ from the closed schema")
    for boolean in (
        "require_all_feasible_external_success", "require_zero_impossible_external_success",
        "require_zero_faulted_episodes",
    ):
        if thresholds.get(boolean) is not True:
            raise M075BReadinessError(f"analysis plan threshold {boolean} drifted")
    if thresholds.get("maximum_context_false_refusals") != 0:
        raise M075BReadinessError("a false refusal may never be tolerated")
    if thresholds.get("maximum_baseline_only_correct_terminal_decisions") != 0:
        raise M075BReadinessError("baseline-only correct decisions may never be tolerated")

    composition = spec.get("composition")
    if not isinstance(composition, Mapping):
        raise M075BReadinessError("the frozen spec carries no composition")
    domain_count = int(composition["domain_count"])
    pairs_per_domain = int(composition["pairs_per_domain"])
    total_pairs = domain_count * pairs_per_domain
    if domain_count < MINIMUM_DOMAINS or pairs_per_domain < MINIMUM_PAIRS_PER_DOMAIN:
        raise M075BReadinessError(
            "a blind bank must be at least as broad as the human-maintained bank it does not replace"
        )

    context_only = thresholds.get("minimum_context_only_correct_terminal_decisions")
    refusals = thresholds.get("minimum_context_true_refusals")
    if not isinstance(context_only, int) or isinstance(context_only, bool):
        raise M075BReadinessError("the discordance threshold is malformed")
    if not isinstance(refusals, int) or isinstance(refusals, bool):
        raise M075BReadinessError("the refusal threshold is malformed")
    # Reachable: the bank must be able to produce this many discordant task instances at all.
    if not 1 <= context_only <= total_pairs * 2:
        raise M075BReadinessError("the discordance threshold is unreachable in this bank size")
    # Failable: a threshold met by every possible draw is not a threshold. Requiring strictly more
    # true refusals than zero, and fewer than every impossible task, keeps both outcomes open.
    if not 1 <= refusals <= total_pairs:
        raise M075BReadinessError("the refusal threshold is vacuous or unreachable")
    maximum_p = thresholds.get("maximum_two_sided_exact_mcnemar_p")
    if not isinstance(maximum_p, (int, float)) or isinstance(maximum_p, bool):
        raise M075BReadinessError("the significance threshold is malformed")
    if Fraction(str(maximum_p)) > MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P:
        raise M075BReadinessError("the significance threshold is looser than the project standard")
    attained = exact_mcnemar_two_sided(context_only, 0)
    if attained > Fraction(str(maximum_p)):
        raise M075BReadinessError(
            f"a bank meeting the discordance threshold would still score p={attained}, "
            "so the frozen plan can never pass"
        )

    attainability = plan.get("attainability")
    if not isinstance(attainability, Mapping) or set(attainability) != {
        "total_pairs", "maximum_discordant_task_instances",
        "two_sided_exact_mcnemar_p_at_threshold", "computed_before_generation",
    }:
        raise M075BReadinessError("attainability fields differ from the closed schema")
    if attainability.get("total_pairs") != total_pairs:
        raise M075BReadinessError("recorded pair count does not match the frozen composition")
    if attainability.get("maximum_discordant_task_instances") != total_pairs * 2:
        raise M075BReadinessError("recorded discordance capacity does not reconcile")
    if Fraction(str(attainability.get("two_sided_exact_mcnemar_p_at_threshold"))) != attained:
        raise M075BReadinessError("recorded p value at threshold does not reconcile")
    if attainability.get("computed_before_generation") is not True:
        raise M075BReadinessError("attainability must be computed before the bank exists")

    if plan.get("non_retry") != {
        "first_materialized_bank_counts": True,
        "reroll_permitted": False,
        "salt_change_permitted": False,
        "threshold_change_permitted": False,
        "negative_result_preserved": True,
        "successor_requires_new_protocol_version_and_new_bank": True,
    }:
        raise M075BReadinessError("analysis plan non-retry policy drifted")
    _validate_claim_boundary(plan.get("claim_boundary"), where="analysis plan")


BLIND_CLAIM_BOUNDARY = {
    "evidence_tier": "blind_generated_sealed_bank",
    "procedural_independence": True,
    "generator_context_blindness": True,
    "generator_training_data_independence": False,
    "human_independence": False,
    "external_reproduction": False,
    "satisfies_m075_independent_human_maintainer_requirement": False,
    "supports_h21": False,
    "closes_issue_112": False,
    "agi": False,
    "genesis_gate_2": False,
    "genesis_gate_3": False,
    "mathematical_impossibility": False,
}


def _validate_claim_boundary(boundary: object, *, where: str) -> None:
    if boundary != BLIND_CLAIM_BOUNDARY:
        raise M075BReadinessError(f"{where} claim boundary drifted")


def validate_system_protocol(
    protocol: Mapping[str, object], *, commitment: Mapping[str, object],
    spec: Mapping[str, object], plan: Mapping[str, object],
    isolation_attestation_sha256: str,
) -> None:
    """Validate the tested-system freeze, which happens after sealing and before reveal."""

    expected = {
        "schema", "milestone", "status", "date_frozen", "bank_commitment_sha256",
        "spec_commitment_sha256", "analysis_plan_commitment_sha256",
        "isolation_attestation_sha256", "tested_system", "budgets", "attempt_policy",
        "assignment_salt_commitment_sha256", "information_boundary", "reproduction",
        "claim_boundary", "protocol_commitment_sha256",
    }
    if not isinstance(protocol, Mapping) or set(protocol) != expected:
        raise M075BReadinessError("system protocol fields differ from the closed schema")
    if protocol.get("schema") != SYSTEM_PROTOCOL_SCHEMA:
        raise M075BReadinessError("system protocol schema drifted")
    if protocol.get("milestone") != MILESTONE:
        raise M075BReadinessError("system protocol milestone drifted")
    if protocol.get("status") != "frozen_after_sealing_before_reveal":
        raise M075BReadinessError("the system protocol is only valid frozen before reveal")
    if protocol.get("protocol_commitment_sha256") != system_protocol_commitment(protocol):
        raise M075BReadinessError("system protocol commitment drifted")
    if protocol.get("bank_commitment_sha256") != commitment.get("commitment_sha256"):
        raise M075BReadinessError("system protocol does not bind the sealed bank commitment")
    if protocol.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
        raise M075BReadinessError("system protocol does not bind the frozen generator spec")
    if protocol.get("analysis_plan_commitment_sha256") != plan.get("plan_commitment_sha256"):
        raise M075BReadinessError("system protocol does not bind the pre-generation analysis plan")
    if protocol.get("isolation_attestation_sha256") != isolation_attestation_sha256:
        raise M075BReadinessError("system protocol does not bind the isolation attestation")

    tested = protocol.get("tested_system")
    if not isinstance(tested, Mapping) or set(tested) != {
        "backend_id", "model", "cli_version", "policy_commit", "code_sha256",
        "frozen_before_any_bank_content_was_known",
    }:
        raise M075BReadinessError("tested-system freeze fields differ from the closed schema")
    if tested.get("frozen_before_any_bank_content_was_known") is not True:
        raise M075BReadinessError("the tested system must be frozen before any content is known")
    for field in ("backend_id", "model", "cli_version"):
        if not isinstance(tested.get(field), str) or not str(tested.get(field)).strip():
            raise M075BReadinessError(f"tested-system {field} is missing")
    policy_commit = tested.get("policy_commit")
    if not isinstance(policy_commit, str) or len(policy_commit) != 40 or any(
        character not in "0123456789abcdef" for character in policy_commit
    ):
        raise M075BReadinessError("tested-system policy commit is malformed")
    code = tested.get("code_sha256")
    if not isinstance(code, Mapping) or not code:
        raise M075BReadinessError("tested-system code digests are missing")
    for path, digest in code.items():
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(
            path
        ).parts:
            raise M075BReadinessError("tested-system code path is malformed")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise M075BReadinessError("tested-system code digest is malformed")

    budgets = protocol.get("budgets")
    if not isinstance(budgets, Mapping) or not budgets:
        raise M075BReadinessError("tested-system budgets are missing")
    for name, value in budgets.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise M075BReadinessError(f"budget {name!r} is malformed")

    if protocol.get("attempt_policy") != {
        "attempts_per_task_condition": 1,
        "fresh_environment_per_episode": True,
        "concurrency": 1,
        "retry_permitted": False,
        "replacement_permitted": False,
        "resume_permitted": False,
        "preserve_every_outcome": True,
    }:
        raise M075BReadinessError("single-attempt policy drifted")
    salt = protocol.get("assignment_salt_commitment_sha256")
    if not isinstance(salt, str) or len(salt) != 64 or any(
        character not in "0123456789abcdef" for character in salt
    ):
        raise M075BReadinessError("assignment salt commitment is malformed")
    if protocol.get("information_boundary") != {
        "task_instruction_visible_to_tested_system": True,
        "action_observations_visible_to_tested_system": True,
        "epistemic_self_evidence_visible_only_in_context_condition": True,
        "labels_certificates_evaluators_outcomes_hidden": True,
        "condition_identity_hidden": True,
        "bank_content_unavailable_before_reveal_authorization": True,
        "tested_system_unmodified_after_reveal": True,
    }:
        raise M075BReadinessError("information boundary drifted")
    if protocol.get("reproduction") != {
        "cross_generator_reproduction_required_for_next_tier": True,
        "second_generator_must_differ_in_family": True,
        "second_generator_must_differ_in_runtime": True,
        "second_generator_must_use_a_separate_bank": True,
        "human_maintained_bank_still_required_for_h21_support": True,
        "first_result_preserved_regardless_of_reproduction": True,
    }:
        raise M075BReadinessError("reproduction contract drifted")
    _validate_claim_boundary(protocol.get("claim_boundary"), where="system protocol")


def _load(path: Path) -> tuple[Mapping[str, object] | None, bytes | None, str | None]:
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


def assess_blind_bank_readiness(
    root: Path,
    *,
    signature_verifier: Callable[[bytes, Path, Path, str, str], bool] | None = None,
) -> dict[str, object]:
    """Report the milestone's phase and every reason reveal is not authorized.

    Fail-closed: an absent artifact, a malformed one and a drifted one are all blockers, and the
    report says `ready_for_reveal: false` unless the entire ordered chain holds. It never opens a
    payload; there is no code path in this module that could.
    """

    resolved = root.resolve()
    blockers: list[str] = []
    phase = "draft"

    result_exists = (resolved / RESULT_PATH).exists()

    spec, _, error = _load(resolved / GENERATOR_SPEC_PATH)
    if error:
        blockers.append(error)
    if spec is not None:
        try:
            validate_generator_spec(spec)
        except BlindBankError as exc:
            blockers.append(f"generator spec: {exc}")
            spec = None
    if spec is not None:
        # Both files the spec commits to by digest are re-hashed here. A prompt edited after the
        # freeze, or an output schema quietly widened, would otherwise leave the spec commitment
        # intact while changing what the generator was actually asked for.
        for path, declared, label in (
            (
                resolved / GENERATOR_PROMPT_PATH,
                spec["prompt"]["template_sha256"],  # type: ignore[index]
                "prompt",
            ),
            (
                resolved / str(spec["output_schema"]["schema_path"]),  # type: ignore[index]
                spec["output_schema"]["schema_sha256"],  # type: ignore[index]
                "output schema",
            ),
        ):
            if not path.is_file():
                blockers.append(f"missing frozen {label} file {path.name}")
            elif sha256_hex(path.read_bytes()) != declared:
                blockers.append(
                    f"the frozen {label} file does not match the digest in the generator spec"
                )
        if spec.get("spec_commitment_sha256") != spec_commitment(spec):
            blockers.append("generator spec commitment drifted")

    plan, _, error = _load(resolved / ANALYSIS_PLAN_PATH)
    if error:
        blockers.append(error)
    if plan is not None and spec is not None:
        try:
            validate_analysis_plan(plan, spec=spec)
        except BlindBankError as exc:
            blockers.append(f"analysis plan: {exc}")
            plan = None
    elif plan is not None:
        blockers.append("analysis plan cannot be validated without a valid generator spec")
        plan = None

    if spec is not None and plan is not None and not blockers:
        phase = "spec_frozen"

    ledger, _, ledger_error = _load(resolved / GENERATION_LEDGER_PATH)
    attestation, _, attestation_error = _load(resolved / ISOLATION_ATTESTATION_PATH)
    commitment, _, commitment_error = _load(resolved / BANK_COMMITMENT_PATH)
    sealed_stage_present = any(
        (resolved / path).exists()
        for path in (GENERATION_LEDGER_PATH, ISOLATION_ATTESTATION_PATH, BANK_COMMITMENT_PATH)
    )

    if sealed_stage_present:
        for error in (ledger_error, attestation_error, commitment_error):
            if error:
                blockers.append(error)
        if ledger is not None:
            try:
                validate_generation_ledger(
                    ledger,
                    spec_commitment_sha256=(
                        str(spec["spec_commitment_sha256"]) if spec is not None else None
                    ),
                )
            except BlindBankError as exc:
                blockers.append(f"generation ledger: {exc}")
                ledger = None
        if attestation is not None:
            try:
                validate_attestation(attestation, repository_root=resolved)
            except BlindBankError as exc:
                blockers.append(f"isolation attestation: {exc}")
                attestation = None
        if commitment is not None:
            try:
                validate_public_commitment(commitment, spec=spec)
            except BlindBankError as exc:
                blockers.append(f"bank commitment: {exc}")
                commitment = None
        if commitment is not None and attestation is not None and spec is not None:
            # Each document above is valid on its own. This is the check that they describe the
            # same run: attested output against sealed payload, frozen generator identity against
            # the commitment, pinned image and runtime against what actually ran, and the ledger
            # entry against all three.
            blockers += sealed_run_binding_problems(
                spec=spec, attestation=attestation, commitment=commitment, ledger=ledger,
            )
        elif commitment is not None or attestation is not None:
            blockers.append(
                "the sealed stage is incomplete, so its artifacts cannot be bound to one run"
            )
        if phase == "spec_frozen" and not blockers:
            phase = "generated_sealed"
    elif spec is not None and plan is not None:
        blockers.append("no bank has been materialized under the frozen specification")

    protocol, _, protocol_error = _load(resolved / SYSTEM_PROTOCOL_PATH)
    if protocol_error and phase == "generated_sealed":
        blockers.append(protocol_error)
    if protocol is not None:
        if commitment is None or spec is None or plan is None or attestation is None:
            blockers.append("the system protocol precedes the artifacts it must bind")
            protocol = None
        else:
            try:
                validate_system_protocol(
                    protocol, commitment=commitment, spec=spec, plan=plan,
                    isolation_attestation_sha256=str(attestation["attestation_sha256"]),
                )
            except BlindBankError as exc:
                blockers.append(f"system protocol: {exc}")
                protocol = None
    if protocol is not None and phase == "generated_sealed" and not blockers:
        phase = "system_protocol_frozen"

    authorization, authorization_raw, authorization_error = _load(
        resolved / REVEAL_AUTHORIZATION_PATH
    )
    signature_file = resolved / REVEAL_SIGNATURE_PATH
    allowed_signers = resolved / REVEAL_ALLOWED_SIGNERS_PATH
    # Presence, not absence: an absent authorization is the normal state of this milestone and
    # must not be reported as a blocker, while a partially present one must.
    reveal_stage_present = (
        (resolved / REVEAL_AUTHORIZATION_PATH).exists()
        or signature_file.exists() or allowed_signers.exists()
    )
    signature_verified = False
    if reveal_stage_present:
        if authorization_error:
            blockers.append(authorization_error)
        if not signature_file.is_file():
            blockers.append(f"missing {REVEAL_SIGNATURE_PATH.name}")
        if not allowed_signers.is_file():
            blockers.append(f"missing {REVEAL_ALLOWED_SIGNERS_PATH.name}")
        if (
            authorization is not None and authorization_raw is not None
            and signature_file.is_file() and allowed_signers.is_file()
            and signature_verifier is not None
        ):
            identity = authorization.get("authorized_by")
            if isinstance(identity, str):
                try:
                    signature_verified = signature_verifier(
                        authorization_raw, signature_file, allowed_signers, identity,
                        REVEAL_SIGNATURE_NAMESPACE,
                    )
                except OSError:
                    signature_verified = False
        if authorization is not None:
            if commitment is None or protocol is None:
                blockers.append("a reveal authorization precedes the protocol it must bind")
            else:
                try:
                    validate_reveal_authorization(
                        authorization, commitment=commitment,
                        protocol_commitment_sha256=str(protocol["protocol_commitment_sha256"]),
                        signature_verified=signature_verified,
                    )
                except BlindBankError as exc:
                    blockers.append(f"reveal authorization: {exc}")
                else:
                    if phase == "system_protocol_frozen" and not blockers:
                        phase = "reveal_authorized"

    if result_exists:
        if phase != "reveal_authorized":
            blockers.append(
                "a result exists without a complete, signed reveal authorization preceding it"
            )
        phase = "executed"

    ready = phase == "system_protocol_frozen" and not blockers and not result_exists
    return {
        "schema": REPORT_SCHEMA,
        "milestone": MILESTONE,
        "phase": phase,
        "phases": list(
            ("draft", "spec_frozen", "generated_sealed", "system_protocol_frozen",
             "reveal_authorized", "executed")
        ),
        "ready_for_reveal": ready,
        "reveal_authorized": phase in {"reveal_authorized", "executed"},
        "scientific_result_exists": result_exists,
        "bank_payload_accessed": False,
        "blockers": blockers,
        "required_minimum_domains": MINIMUM_DOMAINS,
        "required_minimum_pairs_per_domain": MINIMUM_PAIRS_PER_DOMAIN,
        "claim_boundary": dict(BLIND_CLAIM_BOUNDARY),
        "supersedes_m075_human_maintainer_requirement": False,
        "issue_112_status_changed_by_this_milestone": False,
    }


__all__ = [
    "ANALYSIS_PLAN_PATH", "ANALYSIS_PLAN_SCHEMA", "BANK_COMMITMENT_PATH",
    "BLIND_CLAIM_BOUNDARY", "DIGEST_BEARING_PATHS", "EXPERIMENT_DIRECTORY",
    "GENERATION_LEDGER_PATH", "GENERATOR_PROMPT_PATH", "GENERATOR_SPEC_PATH",
    "ISOLATION_ATTESTATION_PATH", "MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P", "MILESTONE",
    "MINIMUM_DOMAINS", "MINIMUM_PAIRS_PER_DOMAIN", "M075BReadinessError", "REPORT_SCHEMA",
    "RESULT_PATH", "REVEAL_ALLOWED_SIGNERS_PATH", "REVEAL_AUTHORIZATION_PATH",
    "REVEAL_SIGNATURE_PATH", "SYSTEM_PROTOCOL_PATH", "SYSTEM_PROTOCOL_SCHEMA",
    "analysis_plan_commitment", "assess_blind_bank_readiness", "system_protocol_commitment",
    "validate_analysis_plan", "validate_system_protocol",
]
