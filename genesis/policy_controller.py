"""Host-side executor for persistent lineage-held search-policy artifacts.

This is the bounded machinery-evolution path the integrated controller was still missing. The mutable
search policy is canonical data in lineage state; a fixed interpreter runs it in the isolated worker.
The initial policy is host-admitted. A descendant policy may increase its program-depth bound by one
only when two facts are measured:

1. every program the prior policy could generate is already a retained rejection; and
2. the newly reachable shell contains a generated program the unchanged trust root accepts against
   the current body on the same task family.

The meta-evaluation runs candidate bodies but does not adopt them. If the policy update is installed,
the *new policy* must subsequently generate and pass the descendant through the ordinary controller
cycle. The update record therefore separates "the wider machinery has measured reach" from "the
lineage actually used that machinery to change its body".

The expansion operator and the maximum depth ceiling are still host apparatus. This is a bounded
empirical acquisition-machinery change, not open-ended self-programming.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from genesis import controller, policies, programs
from genesis import state as lineage_state
from genesis.sandbox import run_candidate, run_isolated_callable
from genesis.trust_root import (
    BudgetExhausted,
    TrustRootError,
    decide,
    digest_of,
    provenance,
    verify_verdict,
)

POLICY_RUN_SCHEMA = "genesis-policy-controller-run-v1"
POLICY_UPDATE_SCHEMA = "genesis-search-policy-update-v1"
POLICY_CERTIFICATE_SCHEMA = "genesis-search-policy-expansion-certificate-v1"
POLICY_TOOL_NAME = "generated_search_policy"
POLICY_ROLE = "lineage_search_policy"


class PolicyControllerError(RuntimeError):
    """Raised when policy execution or evolution asks for an unlicensed transition."""


SEED_PROVENANCE = provenance(
    "host_written",
    produced_by="Genesis search-policy admission",
    detail="bounded seed policy supplied prospectively by the DEVELOPMENT world",
)


def _policy_tool(genesis) -> Mapping[str, Any] | None:
    matches = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == POLICY_TOOL_NAME and tool.get("role") == POLICY_ROLE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise PolicyControllerError("lineage carries more than one current generated-search policy")
    return matches[0]


def bound_policy(genesis) -> dict[str, Any] | None:
    """Return the current validated policy artifact held in lineage state."""
    tool = _policy_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping):
        raise PolicyControllerError("lineage search-policy tool carries no artifact")
    try:
        return policies.validate(artifact)
    except policies.PolicyError as problem:
        raise PolicyControllerError(str(problem)) from problem


def _replace_or_add_policy(genesis, policy, *, provenance_record, observation=None) -> None:
    validated = policies.validate(policy)
    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == POLICY_TOOL_NAME and tool.get("role") == POLICY_ROLE:
            if replaced:
                raise PolicyControllerError("lineage carries duplicate generated-search policy tools")
            tools.append(
                {
                    "name": POLICY_TOOL_NAME,
                    "role": POLICY_ROLE,
                    "artifact": validated,
                    "provenance": provenance_record,
                }
            )
            replaced = True
        else:
            tools.append(tool)
    if not replaced:
        tools.append(
            {
                "name": POLICY_TOOL_NAME,
                "role": POLICY_ROLE,
                "artifact": validated,
                "provenance": provenance_record,
            }
        )

    observations = list(genesis.state.get("observations", []))
    if observation is not None:
        observations.append(dict(observation))
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=observations,
        generation=genesis.state["generation"],
    )


def admit_seed_policy(genesis, policy) -> bool:
    """Admit one bounded seed policy; replacement requires the evidence-backed update path."""
    incoming = policies.validate(policy)
    current = bound_policy(genesis)
    if current is not None:
        if current != incoming:
            raise PolicyControllerError(
                "lineage already holds search policy %s; replacing it requires an expansion "
                "certificate" % current["policy_digest"]
            )
        return False
    _replace_or_add_policy(genesis, incoming, provenance_record=SEED_PROVENANCE)
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "search_policy_admission",
            "policy_digest": incoming["policy_digest"],
            "max_length": incoming["max_length"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return True


def _context_record(genesis) -> dict[str, Any]:
    return controller._context_record(controller._controller_context(genesis))


def _invoke_policy(genesis, policy) -> Any:
    result = run_isolated_callable(
        policies.step,
        {"policy": policies.validate(policy), "context": _context_record(genesis)},
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    if not result["completed"]:
        raise PolicyControllerError(
            "search policy did not run under the admitted boundary: %s"
            % (result.get("reason") or result.get("traceback") or "instrument failure")
        )
    value = result.get("value")
    if not isinstance(value, Mapping):
        raise PolicyControllerError("isolated search policy returned no intent record")
    intent = controller._intent_from_record(value)
    if intent is not None and not isinstance(intent, (controller.GenerateTransform, controller.Stop)):
        raise PolicyControllerError("bounded search policy returned an intent outside its authority")
    return intent


def run_policy(
    genesis,
    here: controller.World,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    max_steps: int = 32,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run the current lineage-held policy until it stops, adopts a body, or reaches ``max_steps``."""
    newly_admitted = False
    if seed_policy is not None:
        newly_admitted = admit_seed_policy(genesis, seed_policy)
    policy = bound_policy(genesis)
    if policy is None:
        raise PolicyControllerError("lineage has no generated-search policy to run")

    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint_path is not None and newly_admitted:
        admission_checkpoint = genesis.persist(checkpoint_path)["checkpoint"]

    steps: list[dict[str, Any]] = []
    for _ in range(max_steps):
        policy = bound_policy(genesis)
        if policy is None:
            raise PolicyControllerError("lineage lost its generated-search policy")
        intent = _invoke_policy(genesis, policy)
        if intent is None or isinstance(intent, controller.Stop):
            steps.append(
                {
                    "intent": "stop",
                    "reason": getattr(intent, "reason", "no policy intent"),
                    "policy_digest": policy["policy_digest"],
                }
            )
            break
        outcome = controller._generate_transform(genesis, here, intent)
        step = {
            "intent": "GenerateTransform",
            "name": intent.name,
            "policy_digest": policy["policy_digest"],
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
        "schema": POLICY_RUN_SCHEMA,
        "steps": steps,
        "policy": bound_policy(genesis),
        "final_generation": genesis.state["generation"],
        "final_state_digest": genesis.state["state_digest"],
        "durable_step_persistence": checkpoint_path is not None,
        "policy_admission_checkpoint": admission_checkpoint,
    }
    record["run_digest"] = digest_of(record)
    return record


def _new_shell(prior, candidate) -> tuple[tuple[str, ...], ...]:
    old = set(policies.candidate_sequences(prior))
    return tuple(
        sequence for sequence in policies.candidate_sequences(candidate) if sequence not in old
    )


def expand_policy(
    genesis,
    here: controller.World,
    *,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Adopt one deeper search policy only after exhaustion and a trust-root-judged reach witness."""
    prior = bound_policy(genesis)
    if prior is None:
        raise PolicyControllerError("lineage has no search policy to expand")
    evidence = controller._controller_context(genesis).evidence
    if not policies.exhausted(prior, evidence):
        raise PolicyControllerError(
            "current search policy is not exhausted; widening machinery before measuring its limit "
            "would turn a failed guess into an acquisition claim"
        )
    try:
        genesis.budget.spend("policy_updates")
    except (TrustRootError, BudgetExhausted) as problem:
        raise PolicyControllerError(
            "policy evolution needs a prospectively admitted 'policy_updates' budget: %s" % problem
        ) from problem
    try:
        candidate_policy = policies.expand(prior)
    except policies.PolicyError as problem:
        raise PolicyControllerError(str(problem)) from problem

    parent = run_candidate(
        genesis.body_factory,
        here.tasks,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=genesis.grade,
    )
    if not parent["completed"]:
        raise PolicyControllerError("current body could not be measured for policy meta-evaluation")

    meta_provenance = provenance(
        "lineage_owned",
        produced_by="candidate search-policy meta-evaluation",
        detail=candidate_policy["policy_digest"],
    )
    attempts: list[dict[str, Any]] = []
    witness = None
    for sequence in _new_shell(prior, candidate_policy):
        generated = programs.artifact(
            registry_reference=candidate_policy["registry_reference"],
            operations=sequence,
            input_field=candidate_policy["input_field"],
        )
        run = run_candidate(
            generated,
            here.tasks,
            genesis.isolation,
            admitted_isolation=genesis.admitted_isolation,
            grade=genesis.grade,
        )
        if not run["completed"]:
            attempts.append(
                {
                    "name": policies.candidate_name(sequence),
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
            raise PolicyControllerError("; ".join(problems))
        attempt = {
            "name": policies.candidate_name(sequence),
            "operations": list(sequence),
            "accepted": verdict["accepted"],
            "verdict_digest": verdict["verdict_digest"],
            "sandbox_digest": run["result_digest"],
        }
        attempts.append(attempt)
        if verdict["accepted"]:
            witness = {**attempt, "body_artifact": generated.body_artifact() if hasattr(generated, "body_artifact") else None}
            # ConfiguredBody does not expose Proposal.body_artifact; bind it directly below.
            from genesis.trust_root import artifact_digest_of

            witness["body_artifact"] = artifact_digest_of(generated)
            break

    if witness is None:
        entry = genesis.journal.append(
            "diagnosis",
            genesis.state["generation"],
            {
                "proposed": False,
                "detail": "policy expansion measured no improving descendant in the newly reachable shell",
                "prior_policy_digest": prior["policy_digest"],
                "candidate_policy_digest": candidate_policy["policy_digest"],
                "attempts": attempts,
            },
        )
        return {
            "schema": POLICY_UPDATE_SCHEMA,
            "accepted": False,
            "reason": "new search depth produced no trust-root-accepted descendant",
            "prior_policy": prior,
            "candidate_policy": candidate_policy,
            "attempts": attempts,
            "journal_entry": entry["entry_digest"],
        }

    certificate_payload = {
        "schema": POLICY_CERTIFICATE_SCHEMA,
        "prior_policy_digest": prior["policy_digest"],
        "new_policy_digest": candidate_policy["policy_digest"],
        "prior_policy_exhausted": True,
        "single_structural_change": {
            "field": "max_length",
            "before": prior["max_length"],
            "after": candidate_policy["max_length"],
        },
        "same_operation_alphabet": prior["operation_names"] == candidate_policy["operation_names"],
        "same_evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
        "new_shell_attempts": attempts,
        "resolving_program": witness,
        "causal_dependency": {
            "established": True,
            "why": "the prior policy had no unevaluated program left, while the one-step-expanded "
            "policy can construct a descendant the unchanged trust root accepts",
        },
    }
    certificate = {
        **certificate_payload,
        "certificate_digest": digest_of(certificate_payload),
    }
    update_provenance = provenance(
        "lineage_owned",
        produced_by="lineage policy expansion",
        detail=certificate["certificate_digest"],
    )
    observation = {
        "kind": "search_policy_updated",
        "prior_policy_digest": prior["policy_digest"],
        "new_policy_digest": candidate_policy["policy_digest"],
        "certificate_digest": certificate["certificate_digest"],
        "causal_dependency": certificate["causal_dependency"],
    }
    _replace_or_add_policy(
        genesis,
        candidate_policy,
        provenance_record=update_provenance,
        observation=observation,
    )
    entry = genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "search_policy_update",
            "certificate": certificate,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    checkpoint = ""
    if checkpoint_directory is not None:
        checkpoint = genesis.persist(Path(checkpoint_directory))["checkpoint"]
    return {
        "schema": POLICY_UPDATE_SCHEMA,
        "accepted": True,
        "prior_policy": prior,
        "candidate_policy": candidate_policy,
        "certificate": certificate,
        "journal_entry": entry["entry_digest"],
        "checkpoint_digest": checkpoint,
    }
