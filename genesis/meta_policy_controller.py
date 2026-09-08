"""Evidence-backed search over *how* a lineage-held search policy should change.

The depth-expansion controller made a mutable policy persistent, but its mutation was fixed apparatus:
``max_length += 1``. This module introduces one level of bounded meta-search. A lineage-held
``MetaPolicy`` is canonical data containing candidate policy mutations. A fixed interpreter runs the
meta-policy in the isolated worker and emits one mutation record at a time. The host kernel may then
measure the resulting candidate policy, but it cannot substitute another mutation.

A policy mutation is adopted only when:

* the current search policy is already exhausted on the exact objective;
* the mutation is one allowed by ``genesis.policy_mutations`` and derives a policy whose parent is
  the currently held policy;
* the candidate policy exposes at least one program the old policy could not construct; and
* the unchanged trust root accepts one of those newly reachable programs against the current body on
  one immutable task snapshot.

Rejected mutations become retained lineage evidence, so the meta-policy skips them on its next step.
Candidate-policy meta-evaluations and mutation attempts consume prospectively admitted budgets and are
checkpointed before the next meta-policy step when persistence is requested.

The meta-policy language is deliberately bounded DEVELOPMENT apparatus. This is search over a small
set of policy edits, not unrestricted self-programming.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from genesis import controller, objective_policy_controller as opc, policies, policy_controller
from genesis import policy_mutations, programs
from genesis import retentive_objectives as retentive
from genesis import state as lineage_state
from genesis.loop import evaluation_snapshot
from genesis.sandbox import run_candidate, run_isolated_callable
from genesis.trust_root import (
    BudgetExhausted,
    TrustRootError,
    decide,
    digest_of,
    provenance,
    verify_verdict,
)

META_POLICY_SCHEMA = "genesis-policy-mutation-meta-policy-v1"
META_RUN_SCHEMA = "genesis-policy-mutation-meta-run-v1"
META_UPDATE_SCHEMA = "genesis-policy-mutation-update-v1"
META_CERTIFICATE_SCHEMA = "genesis-policy-mutation-certificate-v1"
META_TOOL_NAME = "policy_mutation_meta_policy"
META_ROLE = "lineage_policy_mutation_search"


class MetaPolicyError(RuntimeError):
    """Raised when meta-policy search cannot justify or execute a policy mutation."""


def create_meta_policy(
    mutations: Sequence[Mapping[str, Any]],
    *,
    max_attempts: int | None = None,
    parent_meta_policy_digest: str = "",
) -> dict[str, Any]:
    candidates = [policy_mutations.validate(item) for item in mutations]
    if not candidates:
        raise MetaPolicyError("meta-policy contains no candidate policy mutation")
    digests = [item["mutation_digest"] for item in candidates]
    if len(set(digests)) != len(digests):
        raise MetaPolicyError("meta-policy contains a duplicate mutation")
    limit = len(candidates) if max_attempts is None else int(max_attempts)
    if limit <= 0 or limit > len(candidates):
        raise MetaPolicyError("meta-policy max_attempts must cover a positive bounded prefix")
    payload = {
        "schema": META_POLICY_SCHEMA,
        "mutations": candidates,
        "max_attempts": limit,
        "parent_meta_policy_digest": str(parent_meta_policy_digest),
    }
    return {**payload, "meta_policy_digest": digest_of(payload)}


def validate_meta_policy(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != META_POLICY_SCHEMA:
        raise MetaPolicyError("meta-policy uses an unrecognised schema")
    rebuilt = create_meta_policy(
        list(record.get("mutations") or []),
        max_attempts=int(record.get("max_attempts", 0)),
        parent_meta_policy_digest=str(record.get("parent_meta_policy_digest") or ""),
    )
    if rebuilt != dict(record):
        raise MetaPolicyError("meta-policy does not reconstruct from its own fields")
    return rebuilt


META_SEED_PROVENANCE = provenance(
    "host_written",
    produced_by="Genesis meta-policy admission",
    detail="bounded candidate policy-mutation language admitted prospectively",
)


def _meta_tool(genesis) -> Mapping[str, Any] | None:
    matches = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == META_TOOL_NAME and tool.get("role") == META_ROLE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise MetaPolicyError("lineage carries more than one current policy-mutation meta-policy")
    return matches[0]


def bound_meta_policy(genesis) -> dict[str, Any] | None:
    tool = _meta_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping):
        raise MetaPolicyError("lineage meta-policy tool carries no artifact")
    return validate_meta_policy(artifact)


def admit_meta_policy(genesis, meta_policy: Mapping[str, Any]) -> bool:
    incoming = validate_meta_policy(meta_policy)
    current = bound_meta_policy(genesis)
    if current is not None:
        if current != incoming:
            raise MetaPolicyError(
                "lineage already holds meta-policy %s; replacing it requires its own evidence-backed "
                "meta-machinery transition" % current["meta_policy_digest"]
            )
        return False
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"]
        + [
            {
                "name": META_TOOL_NAME,
                "role": META_ROLE,
                "artifact": incoming,
                "provenance": META_SEED_PROVENANCE,
            }
        ],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "policy_mutation_meta_policy_admission",
            "meta_policy_digest": incoming["meta_policy_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return True


def _rejected_mutations(
    evidence: Iterable[Mapping[str, Any]], *, objective_digest: str, prior_policy_digest: str
) -> set[str]:
    rejected: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping) or item.get("kind") != "observation":
            continue
        record = item.get("record") or {}
        if not isinstance(record, Mapping) or record.get("kind") != "policy_mutation_rejected":
            continue
        if (
            record.get("objective_digest") == objective_digest
            and record.get("prior_policy_digest") == prior_policy_digest
        ):
            digest = str(record.get("mutation_digest") or "")
            if digest:
                rejected.add(digest)
    return rejected


def _meta_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Fixed isolated interpreter: retained evidence -> one declarative policy mutation."""
    meta = validate_meta_policy(payload.get("meta_policy") or {})
    objective = opc.validate_objective(payload.get("objective") or {})
    prior = policies.validate(payload.get("policy") or {})
    context = payload.get("context") or {}
    rejected = _rejected_mutations(
        context.get("evidence") or [],
        objective_digest=objective["objective_digest"],
        prior_policy_digest=prior["policy_digest"],
    )
    for mutation in meta["mutations"][: meta["max_attempts"]]:
        if mutation["mutation_digest"] in rejected:
            continue
        return {
            "type": "PolicyMutation",
            "meta_policy_digest": meta["meta_policy_digest"],
            "objective_digest": objective["objective_digest"],
            "prior_policy_digest": prior["policy_digest"],
            "mutation": mutation,
            "retained_mutation_rejections_skipped": len(rejected),
        }
    return {
        "type": "Stop",
        "reason": "meta-policy exhausted its admitted mutation candidates on this policy/objective",
    }


def _invoke_meta_policy(genesis, objective, prior) -> Mapping[str, Any]:
    meta = bound_meta_policy(genesis)
    if meta is None:
        raise MetaPolicyError("lineage has no policy-mutation meta-policy")
    result = run_isolated_callable(
        _meta_step,
        {
            "meta_policy": meta,
            "objective": opc.validate_objective(objective),
            "policy": policies.validate(prior),
            "context": controller._context_record(controller._controller_context(genesis)),
        },
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    if not result["completed"]:
        raise MetaPolicyError(
            "meta-policy did not run under the admitted boundary: %s"
            % (result.get("reason") or result.get("traceback") or "instrument failure")
        )
    value = result.get("value")
    if not isinstance(value, Mapping):
        raise MetaPolicyError("isolated meta-policy returned no mutation record")
    return dict(value)


def _new_sequences(prior, candidate) -> tuple[tuple[str, ...], ...]:
    old = set(policies.candidate_sequences(prior))
    return tuple(
        sequence for sequence in policies.candidate_sequences(candidate) if sequence not in old
    )


def _spend(genesis, dimension: str) -> None:
    try:
        genesis.budget.spend(dimension)
    except (TrustRootError, BudgetExhausted) as problem:
        raise MetaPolicyError(
            "policy-mutation search needs a prospectively admitted %r budget: %s"
            % (dimension, problem)
        ) from problem


def _retain_rejection(genesis, *, objective, prior, mutation, candidate, attempts, reason):
    observation = {
        "kind": "policy_mutation_rejected",
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "mutation_digest": mutation["mutation_digest"],
        "mutation": mutation,
        "candidate_policy_digest": "" if candidate is None else candidate["policy_digest"],
        "reason": str(reason),
        "attempts": list(attempts),
    }
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [observation],
        generation=genesis.state["generation"],
    )
    entry = genesis.journal.append(
        "diagnosis",
        genesis.state["generation"],
        {
            "proposed": False,
            "detail": "policy mutation rejected: %s" % reason,
            **observation,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return observation, entry


def _evaluate_mutation(genesis, here, *, objective, prior, meta, emitted):
    if emitted.get("type") != "PolicyMutation":
        raise MetaPolicyError("meta-policy emitted no policy mutation")
    if emitted.get("meta_policy_digest") != meta["meta_policy_digest"]:
        raise MetaPolicyError("mutation intent does not name the current meta-policy")
    if emitted.get("objective_digest") != objective["objective_digest"]:
        raise MetaPolicyError("mutation intent does not name the current objective")
    if emitted.get("prior_policy_digest") != prior["policy_digest"]:
        raise MetaPolicyError("mutation intent does not name the current search policy")
    mutation = policy_mutations.validate(emitted.get("mutation") or {})
    if mutation not in meta["mutations"][: meta["max_attempts"]]:
        raise MetaPolicyError("meta-policy emitted a mutation outside its admitted candidate set")

    _spend(genesis, "policy_mutations")
    try:
        candidate = policy_mutations.apply(prior, mutation)
    except policy_mutations.PolicyMutationError as problem:
        return {
            "accepted": False,
            "mutation": mutation,
            "candidate_policy": None,
            "attempts": [],
            "reason": str(problem),
        }
    if candidate["parent_policy_digest"] != prior["policy_digest"]:
        raise MetaPolicyError("candidate policy does not name the policy it mutated")
    differences = policy_mutations.structural_difference(prior, candidate)
    if not differences:
        return {
            "accepted": False,
            "mutation": mutation,
            "candidate_policy": candidate,
            "attempts": [],
            "reason": "policy mutation changes no search-relevant field",
        }

    sequences = _new_sequences(prior, candidate)
    if not sequences:
        return {
            "accepted": False,
            "mutation": mutation,
            "candidate_policy": candidate,
            "attempts": [],
            "reason": "mutated policy exposes no candidate the prior policy could not construct",
        }

    questions = evaluation_snapshot(here.tasks)
    parent = run_candidate(
        genesis.body_factory,
        questions,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=genesis.grade,
    )
    if not parent["completed"]:
        raise MetaPolicyError("current body could not be measured for policy-mutation evaluation")
    meta_provenance = provenance(
        "lineage_owned",
        produced_by="policy-mutation meta-policy evaluation",
        detail=mutation["mutation_digest"],
    )
    attempts: list[dict[str, Any]] = []
    witness = None
    for sequence in sequences:
        _spend(genesis, "policy_evaluations")
        generated = programs.artifact(
            registry_reference=candidate["registry_reference"],
            operations=sequence,
            input_field=candidate["input_field"],
        )
        run = run_candidate(
            generated,
            questions,
            genesis.isolation,
            admitted_isolation=genesis.admitted_isolation,
            grade=genesis.grade,
        )
        if not run["completed"]:
            attempts.append(
                {
                    "operations": list(sequence),
                    "instrument_abort": True,
                    "sandbox_digest": run["result_digest"],
                }
            )
            continue
        verdict = decide(
            parent_outcomes=parent["outcomes"],
            candidate_outcomes=run["outcomes"],
            budget=genesis.budget,
            isolation=genesis.isolation,
            admitted_isolation=genesis.admitted_isolation,
            candidate_provenance=meta_provenance,
            evaluation_contract_record=genesis.evaluation_contract,
        )
        problems = verify_verdict(verdict, admitted_source_sha256=genesis.admitted_source_sha256)
        if problems:
            raise MetaPolicyError("; ".join(problems))
        attempt = {
            "operations": list(sequence),
            "accepted": bool(verdict["accepted"]),
            "verdict_digest": verdict["verdict_digest"],
            "sandbox_digest": run["result_digest"],
        }
        attempts.append(attempt)
        if verdict["accepted"]:
            from genesis.trust_root import artifact_digest_of

            witness = {**attempt, "body_artifact": artifact_digest_of(generated)}
            break
    return {
        "accepted": witness is not None,
        "mutation": mutation,
        "candidate_policy": candidate,
        "structural_difference": differences,
        "attempts": attempts,
        "witness": witness,
        "reason": "" if witness is not None else "mutated policy produced no trust-root-accepted new candidate",
    }


def run_meta_policy(
    genesis,
    here,
    *,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_steps: int = 16,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Search policy mutations until one earns adoption or the meta-policy exhausts."""
    retentive.assert_retains_prior_work(genesis, here)
    prior = policy_controller.bound_policy(genesis)
    if prior is None:
        raise MetaPolicyError("lineage has no search policy to mutate")
    if not opc.exhausted(genesis, here, prior):
        raise MetaPolicyError("search policy is not exhausted on this objective")
    newly_admitted = False
    if seed_meta_policy is not None:
        newly_admitted = admit_meta_policy(genesis, seed_meta_policy)
    meta = bound_meta_policy(genesis)
    if meta is None:
        raise MetaPolicyError("lineage has no mutation meta-policy")
    objective = opc.objective_record(genesis, here)
    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint_path is not None and newly_admitted:
        admission_checkpoint = genesis.persist(checkpoint_path)["checkpoint"]

    steps: list[dict[str, Any]] = []
    for _ in range(max_steps):
        # The policy remains `prior` until one mutation is accepted. Rejected mutations are evidence
        # about how to change this exact policy on this exact objective.
        current = policy_controller.bound_policy(genesis)
        if current != prior:
            raise MetaPolicyError("search policy changed outside the meta-policy adoption transaction")
        emitted = _invoke_meta_policy(genesis, objective, prior)
        if emitted.get("type") == "Stop":
            steps.append({"intent": "stop", "reason": str(emitted.get("reason") or "")})
            break
        evaluation = _evaluate_mutation(
            genesis,
            here,
            objective=objective,
            prior=prior,
            meta=meta,
            emitted=emitted,
        )
        if not evaluation["accepted"]:
            observation, entry = _retain_rejection(
                genesis,
                objective=objective,
                prior=prior,
                mutation=evaluation["mutation"],
                candidate=evaluation.get("candidate_policy"),
                attempts=evaluation.get("attempts") or [],
                reason=evaluation["reason"],
            )
            checkpoint = "" if checkpoint_path is None else genesis.persist(checkpoint_path)["checkpoint"]
            steps.append(
                {
                    "intent": "PolicyMutation",
                    "accepted": False,
                    "mutation": evaluation["mutation"],
                    "candidate_policy": evaluation.get("candidate_policy"),
                    "reason": evaluation["reason"],
                    "attempts": evaluation.get("attempts") or [],
                    "observation": observation,
                    "journal_entry": entry["entry_digest"],
                    "checkpoint_digest": checkpoint,
                    "durable_before_next_meta_intent": checkpoint_path is not None,
                }
            )
            continue

        candidate = evaluation["candidate_policy"]
        witness = evaluation["witness"]
        certificate_payload = {
            "schema": META_CERTIFICATE_SCHEMA,
            "objective": objective,
            "meta_policy_digest": meta["meta_policy_digest"],
            "prior_policy_digest": prior["policy_digest"],
            "mutation": evaluation["mutation"],
            "mutation_digest": evaluation["mutation"]["mutation_digest"],
            "new_policy_digest": candidate["policy_digest"],
            "prior_policy_exhausted_on_this_objective": True,
            "structural_difference": evaluation["structural_difference"],
            "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
            "newly_reachable_attempts": evaluation["attempts"],
            "resolving_program": witness,
            "causal_dependency": {
                "established": True,
                "why": "the prior policy had no unevaluated candidate on this objective; the "
                "meta-policy-generated structural mutation exposed a descendant accepted by the "
                "unchanged trust root",
            },
        }
        certificate = {
            **certificate_payload,
            "certificate_digest": digest_of(certificate_payload),
        }
        update_provenance = provenance(
            "lineage_owned",
            produced_by="lineage policy-mutation meta-policy",
            detail=certificate["certificate_digest"],
        )
        observation = {
            "kind": "search_policy_updated",
            "update_kind": "meta_policy_generated_mutation",
            "objective_digest": objective["objective_digest"],
            "meta_policy_digest": meta["meta_policy_digest"],
            "prior_policy_digest": prior["policy_digest"],
            "new_policy_digest": candidate["policy_digest"],
            "mutation_digest": evaluation["mutation"]["mutation_digest"],
            "certificate_digest": certificate["certificate_digest"],
            "causal_dependency": certificate["causal_dependency"],
        }
        policy_controller._replace_or_add_policy(
            genesis,
            candidate,
            provenance_record=update_provenance,
            observation=observation,
        )
        entry = genesis.journal.append(
            "observation",
            genesis.state["generation"],
            {
                "arm": "meta_policy_generated_search_policy_update",
                "certificate": certificate,
                "new_state_digest": genesis.state["state_digest"],
            },
        )
        checkpoint = "" if checkpoint_path is None else genesis.persist(checkpoint_path)["checkpoint"]
        steps.append(
            {
                "intent": "PolicyMutation",
                "accepted": True,
                "mutation": evaluation["mutation"],
                "candidate_policy": candidate,
                "witness": witness,
                "certificate": certificate,
                "journal_entry": entry["entry_digest"],
                "checkpoint_digest": checkpoint,
                "durable_before_next_meta_intent": checkpoint_path is not None,
            }
        )
        break

    record = {
        "schema": META_RUN_SCHEMA,
        "objective": objective,
        "meta_policy": bound_meta_policy(genesis),
        "prior_policy_digest": prior["policy_digest"],
        "current_policy": policy_controller.bound_policy(genesis),
        "steps": steps,
        "meta_policy_admission_checkpoint": admission_checkpoint,
        "final_state_digest": genesis.state["state_digest"],
    }
    record["run_digest"] = digest_of(record)
    return record
