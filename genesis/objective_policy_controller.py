"""Objective-scoped bounded evolution of lineage-held search machinery.

The first persistent search-policy controller retained rejected program names globally. That is enough
for one objective and wrong for continued evolution: evidence that a program failed on task family A
must not make the same policy appear exhausted on task family B. Conversely, once a descendant was
adopted for A, that acquisition must not make the policy stop forever when a new objective arrives.

This module makes the objective an authenticated value: task-set contents plus the already-admitted
evaluation contract. Candidate names are scoped by that digest, so retained rejections and
acquisitions are reusable evidence only for the objective that produced them. A policy can therefore
be exhausted, expanded, change the body, encounter a new retained-capability objective, become
exhausted again, and earn a second machinery expansion.

Policy meta-evaluation is also explicitly budgeted. Candidate executions used only to decide whether
a policy expansion has new reach are real experiments even though they do not adopt a body, so they
spend the prospectively admitted ``policy_evaluations`` budget one by one.

This is DEVELOPMENT apparatus. The policy language, one-step expansion operator and depth ceiling
remain host-admitted bounds; no scientific gate moves merely because this mechanism exists.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from genesis import controller, policies, policy_controller, programs
from genesis.loop import evaluation_snapshot, task_set_digest
from genesis.sandbox import run_candidate, run_isolated_callable
from genesis.trust_root import (
    BudgetExhausted,
    TrustRootError,
    decide,
    digest_of,
    provenance,
    verify_verdict,
)

OBJECTIVE_SCHEMA = "genesis-search-objective-v1"
RUN_SCHEMA = "genesis-objective-policy-run-v1"
UPDATE_SCHEMA = "genesis-objective-policy-update-v1"
CERTIFICATE_SCHEMA = "genesis-objective-policy-expansion-certificate-v1"


class ObjectivePolicyError(RuntimeError):
    """Raised when objective-scoped policy execution cannot justify a transition."""


def objective_record(genesis, here: controller.World) -> dict[str, Any]:
    """Identify the goal independently of task labels and independently of the current body.

    The body is deliberately not part of the objective. A successful descendant satisfies the same
    goal its parent was measured against; a later goal gets a different task-set digest. The admitted
    evaluation contract *is* part of the goal because changing the grader or decision rule changes
    what success means.
    """
    questions = evaluation_snapshot(here.tasks)
    payload = {
        "schema": OBJECTIVE_SCHEMA,
        "task_set_digest": task_set_digest(questions),
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
    }
    return {**payload, "objective_digest": digest_of(payload)}


def validate_objective(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != OBJECTIVE_SCHEMA:
        raise ObjectivePolicyError("search objective uses an unrecognised schema")
    payload = {
        "schema": OBJECTIVE_SCHEMA,
        "task_set_digest": str(record.get("task_set_digest") or ""),
        "evaluation_contract_digest": str(record.get("evaluation_contract_digest") or ""),
    }
    if not payload["task_set_digest"] or not payload["evaluation_contract_digest"]:
        raise ObjectivePolicyError("search objective is missing task or evaluation identity")
    expected = digest_of(payload)
    if record.get("objective_digest") != expected:
        raise ObjectivePolicyError("search objective does not reproduce its own digest")
    return {**payload, "objective_digest": expected}


def candidate_name(operations: Sequence[str], objective: Mapping[str, Any]) -> str:
    """Stable identity for one program *on one measured objective*."""
    goal = validate_objective(objective)
    return "policy-program:%s:%s" % (
        goal["objective_digest"],
        "+".join(str(name) for name in operations),
    )


def _scoped_names(
    evidence: Iterable[Mapping[str, Any]], objective: Mapping[str, Any]
) -> tuple[set[str], set[str]]:
    goal = validate_objective(objective)
    prefix = "policy-program:%s:" % goal["objective_digest"]
    rejected: set[str] = set()
    acquired: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        kind = item.get("kind")
        record = item.get("record") or {}
        if not isinstance(record, Mapping):
            continue
        name = str(record.get("name") or "")
        if not name.startswith(prefix):
            continue
        if kind == "observation" and record.get("kind") == "rejected_candidate":
            rejected.add(name)
        elif kind == "acquisition":
            acquired.add(name)
    return rejected, acquired


def _step(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Fixed isolated interpreter for a mutable policy and one objective-scoped evidence view."""
    policy = policies.validate(payload.get("policy") or {})
    objective = validate_objective(payload.get("objective") or {})
    context = payload.get("context") or {}
    evidence = context.get("evidence") or []
    rejected, acquired = _scoped_names(evidence, objective)
    if acquired:
        return {
            "type": "Stop",
            "reason": "this objective already has a policy-generated adopted descendant",
        }

    for operations in policies.candidate_sequences(policy):
        name = candidate_name(operations, objective)
        if name in rejected:
            continue
        return {
            "type": "GenerateTransform",
            "name": name,
            "operations": list(operations),
            "input_field": policy["input_field"],
            "depends_on": "",
            "rationale": {
                "search_policy_digest": policy["policy_digest"],
                "search_objective_digest": objective["objective_digest"],
                "search_depth": policy["max_length"],
                "retained_rejections_skipped": len(rejected),
            },
        }
    return {
        "type": "Stop",
        "reason": "policy search exhausted for objective %s at max_length=%d"
        % (objective["objective_digest"], policy["max_length"]),
    }


def _invoke_policy(genesis, policy, objective) -> Any:
    result = run_isolated_callable(
        _step,
        {
            "policy": policies.validate(policy),
            "objective": validate_objective(objective),
            "context": controller._context_record(controller._controller_context(genesis)),
        },
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    if not result["completed"]:
        raise ObjectivePolicyError(
            "objective-scoped search policy did not run under the admitted boundary: %s"
            % (result.get("reason") or result.get("traceback") or "instrument failure")
        )
    value = result.get("value")
    if not isinstance(value, Mapping):
        raise ObjectivePolicyError("isolated objective policy returned no intent record")
    intent = controller._intent_from_record(value)
    if intent is not None and not isinstance(intent, (controller.GenerateTransform, controller.Stop)):
        raise ObjectivePolicyError("objective policy returned an intent outside its authority")
    return intent


def exhausted(genesis, here: controller.World, policy: Mapping[str, Any] | None = None) -> bool:
    """Whether this policy's complete bounded candidate set is rejected on *this* objective."""
    held = policies.validate(policy or policy_controller.bound_policy(genesis) or {})
    objective = objective_record(genesis, here)
    rejected, acquired = _scoped_names(controller._controller_context(genesis).evidence, objective)
    if acquired:
        return False
    return all(candidate_name(sequence, objective) in rejected for sequence in policies.candidate_sequences(held))


def run_policy(
    genesis,
    here: controller.World,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    max_steps: int = 32,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run the held machinery against one objective, retaining every rejected hypothesis."""
    newly_admitted = False
    if seed_policy is not None:
        newly_admitted = policy_controller.admit_seed_policy(genesis, seed_policy)
    policy = policy_controller.bound_policy(genesis)
    if policy is None:
        raise ObjectivePolicyError("lineage has no generated-search policy to run")

    objective = objective_record(genesis, here)
    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint_path is not None and newly_admitted:
        admission_checkpoint = genesis.persist(checkpoint_path)["checkpoint"]

    steps: list[dict[str, Any]] = []
    for _ in range(max_steps):
        policy = policy_controller.bound_policy(genesis)
        if policy is None:
            raise ObjectivePolicyError("lineage lost its generated-search policy")
        intent = _invoke_policy(genesis, policy, objective)
        if intent is None or isinstance(intent, controller.Stop):
            steps.append(
                {
                    "intent": "stop",
                    "reason": getattr(intent, "reason", "no policy intent"),
                    "policy_digest": policy["policy_digest"],
                    "objective_digest": objective["objective_digest"],
                }
            )
            break
        outcome = controller._generate_transform(genesis, here, intent)
        step = {
            "intent": "GenerateTransform",
            "name": intent.name,
            "policy_digest": policy["policy_digest"],
            "objective_digest": objective["objective_digest"],
            "program": outcome["generated_program"],
            "body_artifact": outcome["generated_body_artifact"],
            "accepted": bool(outcome.get("accepted")),
            "reason": outcome.get("reason", ""),
            "state_digest": genesis.state["state_digest"],
        }
        if checkpoint_path is not None:
            step["checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]
            step["durable_before_next_policy_step"] = True
        else:
            step["durable_before_next_policy_step"] = False
        steps.append(step)
        if outcome.get("stopped"):
            break

    record = {
        "schema": RUN_SCHEMA,
        "objective": objective,
        "steps": steps,
        "policy": policy_controller.bound_policy(genesis),
        "final_generation": genesis.state["generation"],
        "final_state_digest": genesis.state["state_digest"],
        "durable_step_persistence": checkpoint_path is not None,
        "policy_admission_checkpoint": admission_checkpoint,
    }
    record["run_digest"] = digest_of(record)
    return record


def _new_shell(prior, candidate) -> tuple[tuple[str, ...], ...]:
    old = set(policies.candidate_sequences(prior))
    return tuple(sequence for sequence in policies.candidate_sequences(candidate) if sequence not in old)


def _spend_meta_evaluation(genesis) -> None:
    try:
        genesis.budget.spend("policy_evaluations")
    except (TrustRootError, BudgetExhausted) as problem:
        raise ObjectivePolicyError(
            "policy expansion meta-evaluation needs a prospectively admitted "
            "'policy_evaluations' budget: %s" % problem
        ) from problem


def expand_policy(
    genesis,
    here: controller.World,
    *,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Increase policy depth by one after scoped exhaustion and measured new reach."""
    prior = policy_controller.bound_policy(genesis)
    if prior is None:
        raise ObjectivePolicyError("lineage has no search policy to expand")
    objective = objective_record(genesis, here)
    if not exhausted(genesis, here, prior):
        raise ObjectivePolicyError(
            "current search policy is not exhausted on this objective; evidence from another task "
            "family cannot license machinery growth here"
        )
    try:
        genesis.budget.spend("policy_updates")
    except (TrustRootError, BudgetExhausted) as problem:
        raise ObjectivePolicyError(
            "policy evolution needs a prospectively admitted 'policy_updates' budget: %s" % problem
        ) from problem
    try:
        candidate_policy = policies.expand(prior)
    except policies.PolicyError as problem:
        raise ObjectivePolicyError(str(problem)) from problem

    # One immutable question snapshot for the parent and every meta-evaluation candidate.
    questions = evaluation_snapshot(here.tasks)
    parent = run_candidate(
        genesis.body_factory,
        questions,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=genesis.grade,
    )
    if not parent["completed"]:
        raise ObjectivePolicyError("current body could not be measured for policy meta-evaluation")

    meta_provenance = provenance(
        "lineage_owned",
        produced_by="objective-scoped candidate-policy meta-evaluation",
        detail=candidate_policy["policy_digest"],
    )
    attempts: list[dict[str, Any]] = []
    witness = None
    for sequence in _new_shell(prior, candidate_policy):
        _spend_meta_evaluation(genesis)
        generated = programs.artifact(
            registry_reference=candidate_policy["registry_reference"],
            operations=sequence,
            input_field=candidate_policy["input_field"],
        )
        run = run_candidate(
            generated,
            questions,
            genesis.isolation,
            admitted_isolation=genesis.admitted_isolation,
            grade=genesis.grade,
        )
        name = candidate_name(sequence, objective)
        if not run["completed"]:
            attempts.append(
                {
                    "name": name,
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
            raise ObjectivePolicyError("; ".join(problems))
        attempt = {
            "name": name,
            "operations": list(sequence),
            "accepted": verdict["accepted"],
            "verdict_digest": verdict["verdict_digest"],
            "sandbox_digest": run["result_digest"],
        }
        attempts.append(attempt)
        if verdict["accepted"]:
            from genesis.trust_root import artifact_digest_of

            witness = {**attempt, "body_artifact": artifact_digest_of(generated)}
            break

    if witness is None:
        entry = genesis.journal.append(
            "diagnosis",
            genesis.state["generation"],
            {
                "proposed": False,
                "detail": "policy expansion measured no improving descendant in the new shell",
                "objective_digest": objective["objective_digest"],
                "prior_policy_digest": prior["policy_digest"],
                "candidate_policy_digest": candidate_policy["policy_digest"],
                "attempts": attempts,
            },
        )
        return {
            "schema": UPDATE_SCHEMA,
            "accepted": False,
            "reason": "new search depth produced no trust-root-accepted descendant",
            "objective": objective,
            "prior_policy": prior,
            "candidate_policy": candidate_policy,
            "attempts": attempts,
            "journal_entry": entry["entry_digest"],
        }

    certificate_payload = {
        "schema": CERTIFICATE_SCHEMA,
        "objective": objective,
        "prior_policy_digest": prior["policy_digest"],
        "new_policy_digest": candidate_policy["policy_digest"],
        "prior_policy_exhausted_on_this_objective": True,
        "single_structural_change": {
            "field": "max_length",
            "before": prior["max_length"],
            "after": candidate_policy["max_length"],
        },
        "same_operation_alphabet": prior["operation_names"] == candidate_policy["operation_names"],
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
        "meta_evaluations_spent": len(attempts),
        "new_shell_attempts": attempts,
        "resolving_program": witness,
        "causal_dependency": {
            "established": True,
            "why": "the prior policy had no unevaluated candidate on this objective, while the "
            "one-step-expanded policy reaches a descendant the unchanged trust root accepts",
        },
    }
    certificate = {**certificate_payload, "certificate_digest": digest_of(certificate_payload)}
    update_provenance = provenance(
        "lineage_owned",
        produced_by="objective-scoped lineage policy expansion",
        detail=certificate["certificate_digest"],
    )
    observation = {
        "kind": "search_policy_updated",
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "new_policy_digest": candidate_policy["policy_digest"],
        "certificate_digest": certificate["certificate_digest"],
        "causal_dependency": certificate["causal_dependency"],
    }
    policy_controller._replace_or_add_policy(
        genesis,
        candidate_policy,
        provenance_record=update_provenance,
        observation=observation,
    )
    entry = genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "objective_scoped_search_policy_update",
            "certificate": certificate,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    checkpoint = ""
    if checkpoint_directory is not None:
        checkpoint = genesis.persist(Path(checkpoint_directory))["checkpoint"]
    return {
        "schema": UPDATE_SCHEMA,
        "accepted": True,
        "objective": objective,
        "prior_policy": prior,
        "candidate_policy": candidate_policy,
        "certificate": certificate,
        "journal_entry": entry["entry_digest"],
        "checkpoint_digest": checkpoint,
    }
