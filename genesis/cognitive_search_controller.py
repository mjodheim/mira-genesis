"""Host-side binding for lineage-held cognitive architecture search policy.

The mutable policy lives in Genesis lineage state as canonical data. Its fixed interpreter may only
emit one inert architecture candidate record. The host reconstructs the expected next candidate from
the held policy, parent architecture, retained candidate identities and external ceilings before
returning it. No evaluator, grader or trust-root verdict is exposed to the policy.
"""
from __future__ import annotations

from typing import Any, Collection, Mapping

from genesis import cognitive_search
from genesis import state as lineage_state
from genesis.sandbox import run_isolated_callable
from genesis.trust_root import provenance

POLICY_TOOL_NAME = "cognitive_architecture_search_policy"
POLICY_ROLE = "lineage_cognitive_architecture_search_policy"
PROPOSAL_SCHEMA = "genesis-cognitive-architecture-search-proposal-v1"


class CognitiveSearchControllerError(RuntimeError):
    """Raised when held architecture-search machinery asks beyond its authority."""


SEED_PROVENANCE = provenance(
    "host_written",
    produced_by="Genesis cognitive architecture search admission",
    detail="bounded seed architecture-search policy supplied prospectively",
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
        raise CognitiveSearchControllerError(
            "lineage carries more than one cognitive architecture-search policy"
        )
    return matches[0]


def bound_policy(genesis) -> dict[str, Any] | None:
    """Return the validated cognitive search policy held by the lineage."""
    tool = _policy_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping):
        raise CognitiveSearchControllerError(
            "lineage cognitive search-policy tool carries no artifact"
        )
    try:
        return cognitive_search.validate_policy(artifact)
    except cognitive_search.CognitiveSearchError as problem:
        raise CognitiveSearchControllerError(str(problem)) from problem


def _replace_or_add_policy(genesis, policy, *, provenance_record) -> None:
    validated = cognitive_search.validate_policy(policy)
    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == POLICY_TOOL_NAME and tool.get("role") == POLICY_ROLE:
            if replaced:
                raise CognitiveSearchControllerError(
                    "lineage carries duplicate cognitive architecture-search policy tools"
                )
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

    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )


def admit_seed_policy(genesis, policy) -> bool:
    """Admit one seed policy; silent replacement is forbidden."""
    incoming = cognitive_search.validate_policy(policy)
    if incoming["parent_policy_digest"]:
        raise CognitiveSearchControllerError(
            "a seed cognitive search policy cannot claim an unobserved parent"
        )
    current = bound_policy(genesis)
    if current is not None:
        if current != incoming:
            raise CognitiveSearchControllerError(
                "lineage already holds cognitive architecture-search policy %s"
                % current["policy_digest"]
            )
        return False

    _replace_or_add_policy(genesis, incoming, provenance_record=SEED_PROVENANCE)
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "cognitive_architecture_search_policy_admission",
            "policy_digest": incoming["policy_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return True


def propose_next(
    genesis,
    architecture: Any,
    *,
    admitted_primitives: Collection[str],
    bounds: cognitive_search.SearchBounds,
    observed_candidate_digests: Collection[str] = (),
) -> dict[str, Any]:
    """Run held search machinery in isolation and return one host-revalidated inert proposal."""
    policy = bound_policy(genesis)
    if policy is None:
        raise CognitiveSearchControllerError(
            "lineage has no cognitive architecture-search policy to run"
        )

    observed = sorted({str(value) for value in observed_candidate_digests})
    payload = {
        "architecture": architecture,
        "policy": policy,
        "admitted_primitives": sorted({str(value) for value in admitted_primitives}),
        "bounds": {
            "max_candidates": bounds.max_candidates,
            "max_nodes": bounds.max_nodes,
            "max_edges": bounds.max_edges,
        },
        "observed_candidate_digests": observed,
    }
    before_state = genesis.state["state_digest"]
    before_spent = dict(genesis.budget.spent)
    result = run_isolated_callable(
        cognitive_search.step,
        payload,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    if not result["completed"]:
        raise CognitiveSearchControllerError(
            "cognitive search policy did not run under the admitted boundary: %s"
            % (result.get("reason") or result.get("traceback") or "instrument failure")
        )
    if genesis.state["state_digest"] != before_state or dict(genesis.budget.spent) != before_spent:
        raise CognitiveSearchControllerError(
            "cognitive search proposal changed lineage state or external budget"
        )

    value = result.get("value")
    if not isinstance(value, Mapping):
        raise CognitiveSearchControllerError("isolated cognitive search returned no record")
    expected = cognitive_search.next_candidate(
        architecture,
        policy,
        admitted_primitives=admitted_primitives,
        bounds=bounds,
        observed_candidate_digests=observed,
    )

    if value.get("type") == "Stop":
        if expected is not None:
            raise CognitiveSearchControllerError(
                "held policy stopped despite an externally reconstructible candidate"
            )
        return {
            "schema": PROPOSAL_SCHEMA,
            "stopped": True,
            "reason": str(value.get("reason") or ""),
            "policy_digest": policy["policy_digest"],
            "state_digest": before_state,
        }

    if value.get("type") != "ProposeArchitectureMutation" or expected is None:
        raise CognitiveSearchControllerError(
            "held policy returned an intent outside its proposal authority"
        )
    candidate = value.get("candidate")
    if not isinstance(candidate, Mapping) or dict(candidate) != expected.record():
        raise CognitiveSearchControllerError(
            "held policy proposal does not reproduce under host-side validation"
        )
    return {
        "schema": PROPOSAL_SCHEMA,
        "stopped": False,
        "policy_digest": policy["policy_digest"],
        "state_digest": before_state,
        "candidate": expected.record(),
    }
