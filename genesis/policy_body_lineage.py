"""Persistent evidence that a lineage-held policy produced an adopted body.

A policy update certificate can show that widening or structurally mutating search machinery exposes a
descendant the prior policy could not reach. A later body adoption is a separate event. Without an
explicit link between them, the lineage history contains two true facts but not the stronger fact the
metamorphosis target cares about: **the changed machinery produced the next accepted modification**.

This module binds those events after the ordinary trust-root adoption succeeds. It records the exact
objective, exact current policy artifact, exact generated body artifact and ordinary verdict digest.
When the candidate is the resolving program named by the evidence-backed update that installed the
current policy, the record also carries that update certificate as the structural reason the candidate
was newly reachable.

The record is lineage state, not a controller-run summary, so it survives process death and can be
used by later descendants or audits without trusting the launcher that happened to drive the run.
"""
from __future__ import annotations

from typing import Any, Mapping

from genesis import objective_policy_controller as opc
from genesis import policies
from genesis import state as lineage_state
from genesis.trust_root import digest_of, provenance

LINK_SCHEMA = "genesis-policy-generated-body-link-v1"
UPDATE_ARMS = (
    "objective_scoped_search_policy_update",
    "meta_policy_generated_search_policy_update",
    # Genesis v2: an acquired transformation-language operator constructs the search-policy
    # descendant, after which the ordinary policy/body path must still earn the body adoption.
    "transformation_language_generated_search_policy_update",
)


class PolicyBodyLinkError(RuntimeError):
    """Raised when an accepted body cannot be bound to the policy intent that produced it."""


def _witness_names_candidate(witness: Mapping[str, Any], candidate_name: str) -> bool:
    """Accept either an explicit scoped candidate name or the canonical operation suffix."""
    if witness.get("name") == candidate_name:
        return True
    operations = witness.get("operations")
    if not isinstance(operations, list) or not operations:
        return False
    # Objective-scoped names end in the generated operation composition. Meta-policy evaluation
    # records the inert operation sequence rather than duplicating the scoped name.
    suffix = "+".join(str(name) for name in operations)
    return candidate_name.endswith(":" + suffix)


def _matching_update(genesis, *, policy_digest: str, objective_digest: str, candidate_name: str):
    """Find the latest update certificate that made this exact candidate newly reachable."""
    for entry in reversed(genesis.journal.of_kind("observation")):
        payload = entry.get("payload") or {}
        if payload.get("arm") not in UPDATE_ARMS:
            continue
        certificate = payload.get("certificate") or {}
        if not isinstance(certificate, Mapping):
            continue
        objective = certificate.get("objective") or {}
        witness = certificate.get("resolving_program") or {}
        if (
            certificate.get("new_policy_digest") == policy_digest
            and isinstance(objective, Mapping)
            and objective.get("objective_digest") == objective_digest
            and isinstance(witness, Mapping)
            and _witness_names_candidate(witness, candidate_name)
        ):
            return dict(certificate)
    return None


def record_adoption(
    genesis,
    *,
    objective: Mapping[str, Any],
    policy: Mapping[str, Any],
    intent,
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist one accepted policy-generated body and, when established, its machinery dependency."""
    if not outcome.get("accepted"):
        raise PolicyBodyLinkError("policy/body link may only be recorded after an accepted verdict")
    goal = opc.validate_objective(objective)
    held_policy = policies.validate(policy)

    rationale = dict(getattr(intent, "rationale", {}) or {})
    if rationale.get("search_policy_digest") != held_policy["policy_digest"]:
        raise PolicyBodyLinkError(
            "generated-body intent does not name the exact policy that was current when it ran"
        )
    if rationale.get("search_objective_digest") != goal["objective_digest"]:
        raise PolicyBodyLinkError(
            "generated-body intent does not name the exact objective it was evaluated on"
        )

    verdict = outcome.get("verdict") or {}
    verdict_digest = str(verdict.get("verdict_digest") or "")
    if not verdict_digest:
        raise PolicyBodyLinkError("accepted generated body carries no ordinary trust-root verdict")
    candidate_name = str(getattr(intent, "name", "") or "")
    acquisition = next(
        (
            item
            for item in reversed(genesis.state.get("acquisitions", []))
            if item.get("name") == candidate_name
            and item.get("verdict_digest") == verdict_digest
        ),
        None,
    )
    if not isinstance(acquisition, Mapping):
        raise PolicyBodyLinkError(
            "accepted generated body is not present in the lineage acquisition history under its verdict"
        )

    body_artifact = outcome.get("generated_body_artifact")
    if not isinstance(body_artifact, Mapping) or not body_artifact.get("artifact_digest"):
        raise PolicyBodyLinkError("accepted generated body carries no executable artifact identity")

    update = _matching_update(
        genesis,
        policy_digest=held_policy["policy_digest"],
        objective_digest=goal["objective_digest"],
        candidate_name=candidate_name,
    )
    machinery_dependency = {
        "established": update is not None,
        "policy_digest": held_policy["policy_digest"],
        "objective_digest": goal["objective_digest"],
        "update_certificate_digest": ""
        if update is None
        else str(update.get("certificate_digest") or ""),
        "why": (
            "the evidence-backed policy update names this accepted candidate as the newly reachable "
            "resolving program"
            if update is not None
            else "this body was generated by the held policy, but no preceding policy-update "
            "certificate establishes that this exact candidate required a machinery change"
        ),
    }
    payload = {
        "schema": LINK_SCHEMA,
        "kind": "policy_generated_body_adopted",
        "generation": int(genesis.state["generation"]),
        "candidate_name": candidate_name,
        "objective": goal,
        "policy": held_policy,
        "generated_program": dict(outcome.get("generated_program") or {}),
        "body_artifact": dict(body_artifact),
        "verdict_digest": verdict_digest,
        "machinery_dependency": machinery_dependency,
    }
    link = {**payload, "link_digest": digest_of(payload)}

    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [link],
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "policy_generated_body_adoption",
            "link": link,
            "new_state_digest": genesis.state["state_digest"],
            "provenance": provenance(
                "lineage_owned",
                produced_by="policy evolution controller",
                detail=verdict_digest,
            ),
        },
    )
    return link


def links(genesis) -> tuple[Mapping[str, Any], ...]:
    """Return policy/body link records retained in lineage observations for inspection."""
    return tuple(
        item
        for item in genesis.state.get("observations", [])
        if item.get("schema") == LINK_SCHEMA and item.get("kind") == "policy_generated_body_adopted"
    )
