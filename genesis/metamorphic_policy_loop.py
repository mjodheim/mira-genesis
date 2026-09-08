"""Integrated bounded metamorphic loop: body search -> machinery search -> body search.

Earlier layers established the mechanisms separately:

* a lineage-held search policy can generate executable body programs;
* exhaustion can justify a search-policy change;
* a lineage-held meta-policy can search over *which structural policy mutation* has useful new reach;
* accepted bodies can be bound back to the changed machinery that produced them; and
* later objectives must retain earlier evaluated work.

What remained outside the runtime was the hand-off between the two search levels. A launcher could
run the body policy until exhaustion, then call the meta-policy controller, then call the changed body
policy. This module removes that hand sequencing. Objective arrival remains environmental input, but
within one objective the runtime alternates body search and policy-mutation search until either a body
is adopted or both search levels are exhausted.

The meta-policy still contains a bounded, host-admitted mutation menu and the mutation interpreter is
fixed apparatus. This is an integrated DEVELOPMENT mechanism, not an unbounded self-programming
claim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import controller, meta_policy_controller as meta, objective_policy_controller as opc
from genesis import policy_body_lineage, policy_controller
from genesis import retentive_objectives as retentive
from genesis.trust_root import digest_of

OBJECTIVE_RUN_SCHEMA = "genesis-metamorphic-policy-objective-v1"
CAMPAIGN_SCHEMA = "genesis-metamorphic-policy-campaign-v1"


class MetamorphicPolicyError(RuntimeError):
    """Raised when the integrated body/machinery search cannot preserve its authority boundaries."""


def _checkpoint(genesis, directory: Path | None) -> str:
    if directory is None:
        return ""
    return genesis.persist(directory)["checkpoint"]


def run_objective(
    genesis,
    here,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_rounds: int = 64,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Drive body and policy-mutation search on one retained-capability objective."""
    retentive.assert_retains_prior_work(genesis, here)
    admitted_policy = False
    admitted_meta = False
    if seed_policy is not None:
        admitted_policy = policy_controller.admit_seed_policy(genesis, seed_policy)
    if seed_meta_policy is not None:
        admitted_meta = meta.admit_meta_policy(genesis, seed_meta_policy)
    if policy_controller.bound_policy(genesis) is None:
        raise MetamorphicPolicyError("lineage has no body-search policy")
    if meta.bound_meta_policy(genesis) is None:
        raise MetamorphicPolicyError("lineage has no policy-mutation meta-policy")

    objective = opc.objective_record(genesis, here)
    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint_path is not None and (admitted_policy or admitted_meta):
        admission_checkpoint = _checkpoint(genesis, checkpoint_path)

    steps: list[dict[str, Any]] = []
    adopted = False
    for _ in range(max_rounds):
        policy = policy_controller.bound_policy(genesis)
        if policy is None:
            raise MetamorphicPolicyError("lineage lost its body-search policy")
        intent = opc._invoke_policy(genesis, policy, objective)

        if isinstance(intent, controller.GenerateTransform):
            rationale = dict(intent.rationale or {})
            if rationale.get("search_policy_digest") != policy["policy_digest"]:
                raise MetamorphicPolicyError("generated body intent names machinery not currently held")
            if rationale.get("search_objective_digest") != objective["objective_digest"]:
                raise MetamorphicPolicyError("generated body intent names another objective")
            outcome = controller._generate_transform(genesis, here, intent)
            step = {
                "intent": "GenerateTransform",
                "name": intent.name,
                "objective_digest": objective["objective_digest"],
                "policy_digest": policy["policy_digest"],
                "program": outcome["generated_program"],
                "body_artifact": outcome["generated_body_artifact"],
                "accepted": bool(outcome.get("accepted")),
                "reason": outcome.get("reason", ""),
            }
            if outcome.get("accepted"):
                link = policy_body_lineage.record_adoption(
                    genesis,
                    objective=objective,
                    policy=policy,
                    intent=intent,
                    outcome=outcome,
                )
                corpus = retentive._install_corpus(genesis, here, intent.name)
                step["policy_body_link"] = link
                step["retention_corpus_digest"] = corpus["corpus_digest"]
                adopted = True
            step["checkpoint_digest"] = _checkpoint(genesis, checkpoint_path)
            step["durable_before_next_round"] = checkpoint_path is not None
            step["state_digest"] = genesis.state["state_digest"]
            steps.append(step)
            if adopted or outcome.get("stopped"):
                break
            continue

        if intent is None or isinstance(intent, controller.Stop):
            reason = getattr(intent, "reason", "no body-policy intent")
            exhausted = str(reason).startswith("policy search exhausted for objective ")
            if not exhausted:
                steps.append(
                    {
                        "intent": "stop",
                        "reason": str(reason),
                        "objective_digest": objective["objective_digest"],
                        "policy_digest": policy["policy_digest"],
                    }
                )
                break

            # The body policy itself has established that no candidate remains in its current
            # bounded search space. That retained evidence is the precondition for invoking the
            # lineage-held meta-policy. The launcher does not choose a mutation or call a specific
            # expansion operator.
            mutation_run = meta.run_meta_policy(
                genesis,
                here,
                max_steps=max_rounds,
                checkpoint_directory=checkpoint_path,
            )
            mutation_steps = [
                step for step in mutation_run["steps"] if step.get("intent") == "PolicyMutation"
            ]
            accepted_mutations = [step for step in mutation_steps if step.get("accepted")]
            steps.append(
                {
                    "intent": "MetaPolicySearch",
                    "objective_digest": objective["objective_digest"],
                    "prior_policy_digest": policy["policy_digest"],
                    "meta_policy_digest": mutation_run["meta_policy"]["meta_policy_digest"],
                    "mutations": mutation_steps,
                    "accepted": bool(accepted_mutations),
                    "checkpoint_digest": _checkpoint(genesis, checkpoint_path),
                    "durable_before_next_round": checkpoint_path is not None,
                }
            )
            if not accepted_mutations:
                steps.append(
                    {
                        "intent": "stop",
                        "reason": "body policy exhausted and the mutation meta-policy found no "
                        "evidence-backed machinery descendant",
                        "objective_digest": objective["objective_digest"],
                        "policy_digest": policy["policy_digest"],
                    }
                )
                break
            if len(accepted_mutations) != 1:
                raise MetamorphicPolicyError("one meta-policy search adopted more than one policy")
            changed = policy_controller.bound_policy(genesis)
            if changed is None or changed["parent_policy_digest"] != policy["policy_digest"]:
                raise MetamorphicPolicyError(
                    "meta-policy search did not install a direct descendant of the exhausted policy"
                )
            # Continue in this same runtime loop. The next round asks the changed policy for the body
            # intent; the meta-evaluation witness itself is not silently installed.
            continue

        raise MetamorphicPolicyError("body policy returned an intent outside the integrated loop")

    record = {
        "schema": OBJECTIVE_RUN_SCHEMA,
        "objective": objective,
        "steps": steps,
        "body_adopted": adopted,
        "current_policy": policy_controller.bound_policy(genesis),
        "meta_policy": meta.bound_meta_policy(genesis),
        "retention_corpus": retentive.bound_corpus(genesis),
        "policy_body_links": [dict(item) for item in policy_body_lineage.links(genesis)],
        "final_generation": genesis.state["generation"],
        "final_state_digest": genesis.state["state_digest"],
        "admission_checkpoint": admission_checkpoint,
        "durable_rounds": checkpoint_path is not None,
    }
    record["run_digest"] = digest_of(record)
    return record


def run_objectives(
    genesis,
    objectives: Sequence[Any],
    *,
    seed_policy: Mapping[str, Any] | None = None,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_rounds_per_objective: int = 64,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run successive environmental objectives; all body/machinery hand-offs stay runtime-owned."""
    runs = []
    for index, here in enumerate(objectives):
        runs.append(
            run_objective(
                genesis,
                here,
                seed_policy=seed_policy if index == 0 else None,
                seed_meta_policy=seed_meta_policy if index == 0 else None,
                max_rounds=max_rounds_per_objective,
                checkpoint_directory=checkpoint_directory,
            )
        )
    record = {
        "schema": CAMPAIGN_SCHEMA,
        "objectives": runs,
        "final_policy": policy_controller.bound_policy(genesis),
        "final_meta_policy": meta.bound_meta_policy(genesis),
        "final_retention_corpus": retentive.bound_corpus(genesis),
        "policy_body_links": [dict(item) for item in policy_body_lineage.links(genesis)],
        "final_generation": genesis.state["generation"],
        "final_state_digest": genesis.state["state_digest"],
    }
    record["campaign_digest"] = digest_of(record)
    return record
