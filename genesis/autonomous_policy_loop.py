"""Continuous objective-policy evolution without host sequencing of expansion calls.

The objective-scoped and retentive controllers establish the right evidence boundaries, but a driver
still had to alternate these calls by hand:

    run policy -> notice exhaustion -> expand policy -> run policy again

That is the same architectural smell the integrated Genesis controller was built to remove. This
module keeps objective arrival external (the environment is allowed to present work) while moving the
within-objective sequencing into one runtime loop. The isolated policy interpreter emits either a
generated-body intent, a request to expand its own bounded search machinery after measured exhaustion,
or a stop. The host kernel validates and performs the effect; lineage-owned policy code never receives
runtime authority.

The expansion operator remains the bounded one-step operator admitted by ``genesis.policies``. What
changes here is *who decides when to invoke it*: retained evidence interpreted through the current
lineage-held policy, not the launcher.

Every accepted policy-generated body is additionally bound back to the exact policy/objective that
produced its intent. If it is the resolving program named by the evidence-backed update that installed
that policy, the persistent link records that machinery dependency. Failed or interrupted machinery
updates are checkpointed too when a checkpoint directory exists: an experiment that spent budget or
produced a negative diagnosis is history even when it did not produce a descendant.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import controller, objective_policy_controller as opc, policies, policy_controller
from genesis import policy_body_lineage
from genesis import retentive_objectives as retentive
from genesis.sandbox import run_isolated_callable
from genesis.trust_root import digest_of

RUN_SCHEMA = "genesis-autonomous-policy-objective-v1"
CAMPAIGN_SCHEMA = "genesis-autonomous-policy-campaign-v1"
EXPANSION_REQUEST = "RequestPolicyExpansion"


class AutonomousPolicyError(RuntimeError):
    """Raised when the continuous policy loop cannot justify or execute its next effect."""


def _adaptive_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Interpret policy evidence and turn exhaustion into a declarative self-update request."""
    policy = policies.validate(payload.get("policy") or {})
    objective = opc.validate_objective(payload.get("objective") or {})
    ordinary = opc._step(payload)
    if ordinary.get("type") != "Stop":
        return ordinary

    reason = str(ordinary.get("reason") or "")
    exhausted_here = reason.startswith("policy search exhausted for objective ")
    if exhausted_here and policy["max_length"] < policy["ceiling_length"]:
        return {
            "type": EXPANSION_REQUEST,
            "objective_digest": objective["objective_digest"],
            "policy_digest": policy["policy_digest"],
            "current_max_length": policy["max_length"],
            "requested_max_length": policy["max_length"] + 1,
            "reason": "the current policy has no unevaluated candidate left on this objective",
        }
    if exhausted_here:
        return {
            "type": "Stop",
            "reason": "policy search exhausted at its admitted depth ceiling",
        }
    return ordinary


def _invoke(genesis, objective: Mapping[str, Any]) -> Any:
    policy = policy_controller.bound_policy(genesis)
    if policy is None:
        raise AutonomousPolicyError("lineage has no search policy")
    result = run_isolated_callable(
        _adaptive_step,
        {
            "policy": policy,
            "objective": opc.validate_objective(objective),
            "context": controller._context_record(controller._controller_context(genesis)),
        },
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    if not result["completed"]:
        raise AutonomousPolicyError(
            "adaptive policy interpreter did not run under the admitted boundary: %s"
            % (result.get("reason") or result.get("traceback") or "instrument failure")
        )
    value = result.get("value")
    if not isinstance(value, Mapping):
        raise AutonomousPolicyError("adaptive policy interpreter returned no intent record")
    if value.get("type") == EXPANSION_REQUEST:
        return dict(value)
    intent = controller._intent_from_record(value)
    if intent is not None and not isinstance(intent, (controller.GenerateTransform, controller.Stop)):
        raise AutonomousPolicyError("adaptive policy returned an intent outside its authority")
    return intent


def _persist_if_possible(genesis, checkpoint_path: Path | None) -> str:
    """Commit consumed budget/evidence before returning or propagating an expected refusal."""
    if checkpoint_path is None:
        return ""
    return genesis.persist(checkpoint_path)["checkpoint"]


def run_objective(
    genesis,
    here,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    max_steps: int = 64,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Search, update machinery when licensed, adopt/reject, persist, and continue until stop."""
    retentive.assert_retains_prior_work(genesis, here)
    newly_admitted = False
    if seed_policy is not None:
        newly_admitted = policy_controller.admit_seed_policy(genesis, seed_policy)
    if policy_controller.bound_policy(genesis) is None:
        raise AutonomousPolicyError("lineage has no policy to drive")

    objective = opc.objective_record(genesis, here)
    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint_path is not None and newly_admitted:
        admission_checkpoint = genesis.persist(checkpoint_path)["checkpoint"]

    steps: list[dict[str, Any]] = []
    for _ in range(max_steps):
        action = _invoke(genesis, objective)
        policy = policy_controller.bound_policy(genesis)
        if policy is None:
            raise AutonomousPolicyError("lineage lost its search policy")

        if action is None or isinstance(action, controller.Stop):
            steps.append(
                {
                    "intent": "stop",
                    "reason": getattr(action, "reason", "no policy intent"),
                    "objective_digest": objective["objective_digest"],
                    "policy_digest": policy["policy_digest"],
                }
            )
            break

        if isinstance(action, Mapping) and action.get("type") == EXPANSION_REQUEST:
            if action.get("objective_digest") != objective["objective_digest"]:
                raise AutonomousPolicyError("policy expansion request names another objective")
            if action.get("policy_digest") != policy["policy_digest"]:
                raise AutonomousPolicyError("policy expansion request names machinery not currently held")
            try:
                update = retentive.expand_policy(
                    genesis,
                    here,
                    checkpoint_directory=checkpoint_path,
                )
            except (opc.ObjectivePolicyError, retentive.RetentionObjectiveError):
                # Budget may already have been consumed before the refusal became known. Persist the
                # exact spent ledger/state before propagating; a crash must not refund an experiment.
                _persist_if_possible(genesis, checkpoint_path)
                raise
            checkpoint = str(update.get("checkpoint_digest") or "")
            if not checkpoint:
                # Negative meta-evaluation is still evidence and may have spent several candidate
                # evaluations. The lower-level update path only checkpoints a successful adoption.
                checkpoint = _persist_if_possible(genesis, checkpoint_path)
            step = {
                "intent": EXPANSION_REQUEST,
                "objective_digest": objective["objective_digest"],
                "prior_policy_digest": policy["policy_digest"],
                "requested_max_length": action["requested_max_length"],
                "accepted": bool(update.get("accepted")),
                "reason": update.get("reason", ""),
                "update": update,
                "checkpoint_digest": checkpoint,
                "durable_before_next_intent": checkpoint_path is not None,
            }
            steps.append(step)
            if not update.get("accepted"):
                steps.append(
                    {
                        "intent": "stop",
                        "reason": "requested machinery expansion produced no measured new reach",
                        "objective_digest": objective["objective_digest"],
                        "policy_digest": policy_controller.bound_policy(genesis)["policy_digest"],
                    }
                )
                break
            continue

        if not isinstance(action, controller.GenerateTransform):
            raise AutonomousPolicyError("continuous policy loop received an unknown action")

        # The inert policy record itself states which machinery and objective produced this intent.
        # Validate that claim before running it; after an acceptance the persistent link below binds
        # the same identities to the ordinary trust-root verdict and executable artifact.
        rationale = dict(action.rationale or {})
        if rationale.get("search_policy_digest") != policy["policy_digest"]:
            raise AutonomousPolicyError("generated transform does not name the exact current policy")
        if rationale.get("search_objective_digest") != objective["objective_digest"]:
            raise AutonomousPolicyError("generated transform does not name the exact current objective")

        outcome = controller._generate_transform(genesis, here, action)
        step = {
            "intent": "GenerateTransform",
            "name": action.name,
            "objective_digest": objective["objective_digest"],
            "policy_digest": policy["policy_digest"],
            "program": outcome["generated_program"],
            "body_artifact": outcome["generated_body_artifact"],
            "accepted": bool(outcome.get("accepted")),
            "reason": outcome.get("reason", ""),
            "state_digest": genesis.state["state_digest"],
        }
        if outcome.get("accepted"):
            link = policy_body_lineage.record_adoption(
                genesis,
                objective=objective,
                policy=policy,
                intent=action,
                outcome=outcome,
            )
            step["policy_body_link_digest"] = link["link_digest"]
            step["machinery_dependency"] = link["machinery_dependency"]
            corpus = retentive._install_corpus(genesis, here, action.name)
            step["retention_corpus_digest"] = corpus["corpus_digest"]
        if checkpoint_path is not None:
            step["checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]
            step["durable_before_next_intent"] = True
        else:
            step["checkpoint_digest"] = ""
            step["durable_before_next_intent"] = False
        step["state_digest"] = genesis.state["state_digest"]
        steps.append(step)
        if outcome.get("stopped"):
            break

    record = {
        "schema": RUN_SCHEMA,
        "objective": objective,
        "steps": steps,
        "policy": policy_controller.bound_policy(genesis),
        "retention_corpus": retentive.bound_corpus(genesis),
        "policy_body_links": [dict(item) for item in policy_body_lineage.links(genesis)],
        "final_generation": genesis.state["generation"],
        "final_state_digest": genesis.state["state_digest"],
        "policy_admission_checkpoint": admission_checkpoint,
        "durable_step_persistence": checkpoint_path is not None,
    }
    record["run_digest"] = digest_of(record)
    return record


def run_objectives(
    genesis,
    objectives: Sequence[Any],
    *,
    seed_policy: Mapping[str, Any] | None = None,
    max_steps_per_objective: int = 64,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run successive environment-provided objectives; all within-objective evolution is runtime-owned."""
    runs = []
    for index, here in enumerate(objectives):
        run = run_objective(
            genesis,
            here,
            seed_policy=seed_policy if index == 0 else None,
            max_steps=max_steps_per_objective,
            checkpoint_directory=checkpoint_directory,
        )
        runs.append(run)
    record = {
        "schema": CAMPAIGN_SCHEMA,
        "objectives": runs,
        "final_generation": genesis.state["generation"],
        "final_policy": policy_controller.bound_policy(genesis),
        "final_retention_corpus": retentive.bound_corpus(genesis),
        "policy_body_links": [dict(item) for item in policy_body_lineage.links(genesis)],
        "final_state_digest": genesis.state["state_digest"],
    }
    record["campaign_digest"] = digest_of(record)
    return record
