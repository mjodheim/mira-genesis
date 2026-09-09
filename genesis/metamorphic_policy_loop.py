"""Integrated bounded metamorphic loop across body, policy and MetaPolicy search.

The runtime owns the hand-offs between three held levels:

* a lineage-held search policy generates executable body programs;
* a lineage-held MetaPolicy searches over structural search-policy mutations; and
* after both of those spaces are empirically exhausted, the lineage may acquire an evidence-backed
  MetaPolicy descendant through the crash-consistent bounded evolution path.

Objective arrival remains environmental input. Within one objective the launcher does not choose a
body transform, a policy mutation, or a MetaPolicy extension: the runtime alternates the held levels
until it either adopts a body or exhausts the admitted machinery.

MetaPolicy evolution is available only on the checkpointed path, because its physical candidate
budget must be durably reserved before execution. The mutation language, operation registry, trust
root, evaluator and synthesis operator remain fixed apparatus. This is a DEVELOPMENT mechanism, not
an open-ended self-programming or generality claim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import controller, meta_policy_controller as meta, objective_policy_controller as opc
from genesis import durable_meta_policy_evolution as durable_meta
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
    """Drive body, policy-mutation and bounded MetaPolicy-descendant search on one objective."""
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

            # The body policy has established exhaustion of its current bounded search space. First
            # ask the held MetaPolicy to search its admitted lower-level mutation set.
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
            if accepted_mutations:
                if len(accepted_mutations) != 1:
                    raise MetamorphicPolicyError("one meta-policy search adopted more than one policy")
                changed = policy_controller.bound_policy(genesis)
                if changed is None or changed["parent_policy_digest"] != policy["policy_digest"]:
                    raise MetamorphicPolicyError(
                        "meta-policy search did not install a direct descendant of the exhausted policy"
                    )
                # The next round asks the changed policy for the body intent. The meta-evaluation
                # witness itself is never silently installed.
                continue

            # Both the body policy and the currently held MetaPolicy are exhausted. Previously the
            # runtime stopped here and a launcher had to call `evolve_meta_policy` manually. On the
            # checkpointed path, make that hand-off runtime-owned and crash-consistent as well.
            if checkpoint_path is None:
                steps.append(
                    {
                        "intent": "stop",
                        "reason": "body policy and MetaPolicy exhausted; deeper MetaPolicy evolution "
                        "requires checkpoint_directory for non-redrawable budget accounting",
                        "objective_digest": objective["objective_digest"],
                        "policy_digest": policy["policy_digest"],
                    }
                )
                break

            # Deeper machinery search itself must have been prospectively budgeted. Older callers
            # admitted only body/policy dimensions; giving those lineages new meta-level allowance
            # merely because this runtime learned a new feature would widen their experiment after
            # the fact. Preserve the old terminal behaviour instead.
            required_meta_budget = ("meta_policy_candidates", "meta_policy_evaluations")
            missing_meta_budget = [
                name for name in required_meta_budget if name not in genesis.budget.limits
            ]
            if missing_meta_budget:
                steps.append(
                    {
                        "intent": "stop",
                        "reason": "body policy and MetaPolicy exhausted; deeper MetaPolicy evolution "
                        "was not prospectively admitted (missing budget: %s)"
                        % ", ".join(missing_meta_budget),
                        "objective_digest": objective["objective_digest"],
                        "policy_digest": policy["policy_digest"],
                    }
                )
                break

            parent_meta = meta.bound_meta_policy(genesis)
            if parent_meta is None:
                raise MetamorphicPolicyError("lineage lost its MetaPolicy before descendant search")
            try:
                meta_evolution = durable_meta.evolve_meta_policy(
                    genesis,
                    here,
                    checkpoint_directory=checkpoint_path,
                )
            except durable_meta.DurableMetaPolicyEvolutionError as problem:
                raise MetamorphicPolicyError(str(problem)) from problem

            descendant_meta = meta.bound_meta_policy(genesis)
            steps.append(
                {
                    "intent": "MetaPolicyEvolution",
                    "objective_digest": objective["objective_digest"],
                    "prior_policy_digest": policy["policy_digest"],
                    "parent_meta_policy_digest": parent_meta["meta_policy_digest"],
                    "new_meta_policy_digest": descendant_meta["meta_policy_digest"]
                    if descendant_meta is not None
                    else "",
                    "accepted": bool(meta_evolution.get("accepted")),
                    "selection_reason": meta_evolution.get("selection_reason", ""),
                    "durable_budget_round_digest": meta_evolution.get(
                        "durable_budget_round_digest", ""
                    ),
                    "checkpoint_digest": _checkpoint(genesis, checkpoint_path),
                    "durable_before_next_round": True,
                }
            )
            if not meta_evolution.get("accepted"):
                steps.append(
                    {
                        "intent": "stop",
                        "reason": "body policy and held MetaPolicy were exhausted and no unique "
                        "evidence-backed MetaPolicy descendant was available",
                        "objective_digest": objective["objective_digest"],
                        "policy_digest": policy["policy_digest"],
                    }
                )
                break
            if descendant_meta is None or descendant_meta["parent_meta_policy_digest"] != parent_meta[
                "meta_policy_digest"
            ]:
                raise MetamorphicPolicyError(
                    "MetaPolicy evolution did not install a direct descendant of the exhausted MetaPolicy"
                )
            # Continue in the same runtime loop. The descendant MetaPolicy must now earn a lower-level
            # policy change through the ordinary #289 controller before any body can be adopted.
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
