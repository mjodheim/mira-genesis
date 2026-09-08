"""Apply an evidence-selected policy mutation and let the changed policy produce the body.

``meta_policy_controller`` stops after it adopts search machinery: its witness is evidence that the
candidate policy has new reach, not permission to install the witness body. This helper performs the
separate next step. The newly installed policy runs through its isolated interpreter, emits the body
intent itself, and the ordinary controller/trust root decides the body. A successful body is then
bound back to the meta-policy-generated update certificate and advances the cross-objective retention
corpus.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from genesis import controller, meta_policy_controller as meta, objective_policy_controller as opc
from genesis import policy_body_lineage, policy_controller
from genesis import retentive_objectives as retentive
from genesis.trust_root import digest_of

APPLICATION_SCHEMA = "genesis-meta-policy-application-v1"


class MetaPolicyApplicationError(RuntimeError):
    """Raised when changed machinery cannot be cleanly separated from the body adoption it enables."""


def evolve_and_apply(
    genesis,
    here,
    *,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_meta_steps: int = 16,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Search a policy mutation, adopt only that policy, then let it propose the body normally."""
    prior = policy_controller.bound_policy(genesis)
    if prior is None:
        raise MetaPolicyApplicationError("lineage has no search policy to evolve")
    objective = opc.objective_record(genesis, here)
    policy_run = meta.run_meta_policy(
        genesis,
        here,
        seed_meta_policy=seed_meta_policy,
        max_steps=max_meta_steps,
        checkpoint_directory=checkpoint_directory,
    )
    current = policy_controller.bound_policy(genesis)
    accepted_updates = [step for step in policy_run["steps"] if step.get("accepted")]
    if not accepted_updates:
        record = {
            "schema": APPLICATION_SCHEMA,
            "objective": objective,
            "policy_update": policy_run,
            "body_attempt": None,
            "policy_changed": current != prior,
            "body_adopted": False,
            "final_state_digest": genesis.state["state_digest"],
        }
        record["application_digest"] = digest_of(record)
        return record
    if len(accepted_updates) != 1:
        raise MetaPolicyApplicationError("one meta-policy run adopted more than one search policy")
    if current is None or current["parent_policy_digest"] != prior["policy_digest"]:
        raise MetaPolicyApplicationError("accepted policy mutation did not install a direct descendant")

    # The objective is part of the policy interpreter input. Omitting it here would let application
    # accidentally run changed machinery without the same goal/evaluation identity that licensed it.
    intent = opc._invoke_policy(genesis, current, objective)
    if not isinstance(intent, controller.GenerateTransform):
        raise MetaPolicyApplicationError(
            "changed policy did not produce the newly reachable body intent after its adoption"
        )
    rationale = dict(intent.rationale or {})
    if rationale.get("search_policy_digest") != current["policy_digest"]:
        raise MetaPolicyApplicationError("body intent names a policy other than the changed machinery")
    if rationale.get("search_objective_digest") != objective["objective_digest"]:
        raise MetaPolicyApplicationError("body intent names another objective")

    outcome = controller._generate_transform(genesis, here, intent)
    attempt = {
        "name": intent.name,
        "program": outcome["generated_program"],
        "body_artifact": outcome["generated_body_artifact"],
        "accepted": bool(outcome.get("accepted")),
        "reason": outcome.get("reason", ""),
        "policy_digest": current["policy_digest"],
        "objective_digest": objective["objective_digest"],
    }
    if outcome.get("accepted"):
        link = policy_body_lineage.record_adoption(
            genesis,
            objective=objective,
            policy=current,
            intent=intent,
            outcome=outcome,
        )
        corpus = retentive._install_corpus(genesis, here, intent.name)
        attempt["policy_body_link"] = link
        attempt["retention_corpus_digest"] = corpus["corpus_digest"]
    checkpoint = ""
    if checkpoint_directory is not None:
        checkpoint = genesis.persist(Path(checkpoint_directory))["checkpoint"]
    attempt["checkpoint_digest"] = checkpoint
    attempt["durable_before_return"] = checkpoint_directory is not None

    record = {
        "schema": APPLICATION_SCHEMA,
        "objective": objective,
        "policy_update": policy_run,
        "body_attempt": attempt,
        "policy_changed": current != prior,
        "body_adopted": bool(outcome.get("accepted")),
        "final_state_digest": genesis.state["state_digest"],
    }
    record["application_digest"] = digest_of(record)
    return record
