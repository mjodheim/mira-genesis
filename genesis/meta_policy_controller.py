"""Evidence-backed search over *how* a lineage-held search policy should change.

A MetaPolicy is a bounded lineage-held set of candidate policy mutations. The important distinction is
that admission of a mutation into that set is not a choice of winner. Every still-unmeasured admitted
mutation is evaluated against the same objective, body, evaluator contract and task snapshot. The
runtime adopts a policy mutation only when the unchanged trust-root measure gives it a **unique strict
maximum** among the viable mutations. If two mutations tie under the admitted measure, neither is
adopted: there is evidence that both help, but no evidence that chooses between them.

This closes the host-order failure where reversing an authored mutation menu changed the adopted
policy. Measurement results are persisted before the next mutation is evaluated, so a process death
cannot erase a viable/rejected mutation experiment or refund its budget. The bounded mutation
language and the MetaPolicy candidate set remain DEVELOPMENT apparatus; this module does not claim
that the MetaPolicy itself is yet self-generated.
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
    artifact_digest_of,
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
        raise MetaPolicyError("meta-policy max_attempts must cover a positive bounded subset")
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


def _admitted_mutations(meta: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Choose a bounded subset without making authored list order part of subset membership.

    With the default limit the whole set is kept in authored order for readable records. If a smaller
    bound is prospectively admitted, membership is chosen by canonical mutation digest rather than by
    an authored prefix. Evaluation order may still differ in logs; adoption cannot depend on it.
    """
    validated = validate_meta_policy(meta)
    mutations = list(validated["mutations"])
    limit = int(validated["max_attempts"])
    if limit == len(mutations):
        return tuple(mutations)
    chosen = {
        item["mutation_digest"]
        for item in sorted(mutations, key=lambda item: item["mutation_digest"])[:limit]
    }
    return tuple(item for item in mutations if item["mutation_digest"] in chosen)


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


def _evaluated_mutations(
    evidence: Iterable[Mapping[str, Any]], *, objective_digest: str, prior_policy_digest: str
) -> set[str]:
    seen: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping) or item.get("kind") != "observation":
            continue
        record = item.get("record") or {}
        if not isinstance(record, Mapping):
            continue
        if record.get("kind") not in {"policy_mutation_rejected", "policy_mutation_viable"}:
            continue
        if (
            record.get("objective_digest") == objective_digest
            and record.get("prior_policy_digest") == prior_policy_digest
        ):
            mutation_digest = str(record.get("mutation_digest") or "")
            if mutation_digest:
                seen.add(mutation_digest)
    return seen


def _meta_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Fixed isolated interpreter: retained evidence -> all still-unmeasured admitted mutations."""
    meta = validate_meta_policy(payload.get("meta_policy") or {})
    objective = opc.validate_objective(payload.get("objective") or {})
    prior = policies.validate(payload.get("policy") or {})
    context = payload.get("context") or {}
    seen = _evaluated_mutations(
        context.get("evidence") or [],
        objective_digest=objective["objective_digest"],
        prior_policy_digest=prior["policy_digest"],
    )
    pending = [
        mutation
        for mutation in _admitted_mutations(meta)
        if mutation["mutation_digest"] not in seen
    ]
    if not pending:
        return {
            "type": "Stop",
            "reason": "meta-policy has measured every admitted mutation on this policy/objective",
        }
    return {
        "type": "PolicyMutationBatch",
        "meta_policy_digest": meta["meta_policy_digest"],
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "mutations": pending,
        "retained_mutation_measurements_skipped": len(seen),
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


def _require_round_budget(genesis, *, mutation_count: int, evaluation_count: int) -> None:
    """Refuse before the round starts if every candidate cannot receive the same promised treatment."""
    try:
        mutation_remaining = genesis.budget.remaining("policy_mutations")
        evaluation_remaining = genesis.budget.remaining("policy_evaluations")
    except TrustRootError as problem:
        raise MetaPolicyError("policy-mutation selection has no prospectively admitted budget") from problem
    if mutation_remaining < mutation_count:
        raise MetaPolicyError(
            "policy_mutations budget cannot measure the complete selection round: need %d, have %d"
            % (mutation_count, mutation_remaining)
        )
    if evaluation_remaining < evaluation_count:
        raise MetaPolicyError(
            "policy_evaluations budget cannot measure the complete selection round: need %d, have %d"
            % (evaluation_count, evaluation_remaining)
        )


def _retain_rejection(genesis, *, objective, prior, meta, evaluation):
    observation = {
        "kind": "policy_mutation_rejected",
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "meta_policy_digest": meta["meta_policy_digest"],
        "mutation_digest": evaluation["mutation"]["mutation_digest"],
        "mutation": evaluation["mutation"],
        "candidate_policy_digest": ""
        if evaluation.get("candidate_policy") is None
        else evaluation["candidate_policy"]["policy_digest"],
        "reason": str(evaluation["reason"]),
        "attempts": list(evaluation.get("attempts") or []),
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
            "detail": "policy mutation rejected by measurement: %s" % evaluation["reason"],
            **observation,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return observation, entry


def _retain_viable(genesis, *, objective, prior, meta, evaluation):
    observation = {
        "kind": "policy_mutation_viable",
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "meta_policy_digest": meta["meta_policy_digest"],
        "mutation_digest": evaluation["mutation"]["mutation_digest"],
        "mutation": evaluation["mutation"],
        "candidate_policy": evaluation["candidate_policy"],
        "structural_difference": evaluation["structural_difference"],
        "attempts": list(evaluation["attempts"]),
        "witness": evaluation["witness"],
        "selection_score": int(evaluation["selection_score"]),
        "measure": "trust_root_candidate_solved_count",
    }
    observation["measurement_digest"] = digest_of(observation)
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
        "observation",
        genesis.state["generation"],
        {
            "arm": "policy_mutation_viable_measurement",
            "measurement": observation,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return observation, entry


def _viable_measurements(genesis, *, objective, prior, meta) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    allowed = {item["mutation_digest"] for item in _admitted_mutations(meta)}
    for item in genesis.state.get("observations", []):
        if not isinstance(item, Mapping) or item.get("kind") != "policy_mutation_viable":
            continue
        if (
            item.get("objective_digest") != objective["objective_digest"]
            or item.get("prior_policy_digest") != prior["policy_digest"]
            or item.get("meta_policy_digest") != meta["meta_policy_digest"]
            or item.get("mutation_digest") not in allowed
        ):
            continue
        records.append(dict(item))
    return records


def _evaluate_mutation(genesis, *, objective, prior, meta, mutation, questions, parent):
    mutation = policy_mutations.validate(mutation)
    if mutation not in _admitted_mutations(meta):
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

    meta_provenance = provenance(
        "lineage_owned",
        produced_by="policy-mutation meta-policy evaluation",
        detail=mutation["mutation_digest"],
    )
    attempts: list[dict[str, Any]] = []
    viable: list[dict[str, Any]] = []
    for sequence in sequences:
        _spend(genesis, "policy_evaluations")
        generated = programs.artifact(
            registry_reference=candidate["registry_reference"],
            operations=sequence,
            input_field=candidate["input_field"],
        )
        body_artifact = artifact_digest_of(generated)
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
                    "body_artifact": body_artifact,
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
        score = int(verdict["candidate"]["counts"]["solved"])
        attempt = {
            "operations": list(sequence),
            "accepted": bool(verdict["accepted"]),
            "selection_score": score,
            "parent_solved": int(verdict["parent"]["counts"]["solved"]),
            "candidate_solved": score,
            "verdict_digest": verdict["verdict_digest"],
            "sandbox_digest": run["result_digest"],
            "body_artifact": body_artifact,
        }
        attempts.append(attempt)
        if verdict["accepted"]:
            viable.append(attempt)

    if not viable:
        return {
            "accepted": False,
            "mutation": mutation,
            "candidate_policy": candidate,
            "structural_difference": differences,
            "attempts": attempts,
            "witness": None,
            "reason": "mutated policy produced no trust-root-accepted new candidate",
        }

    best_score = max(item["selection_score"] for item in viable)
    best = [item for item in viable if item["selection_score"] == best_score]
    # Equal-scoring programs inside one policy do not choose between policy mutations. Pick a stable
    # witness only so the certificate has one reproducible executable example.
    witness = min(best, key=lambda item: item["body_artifact"]["artifact_digest"])
    return {
        "accepted": True,
        "mutation": mutation,
        "candidate_policy": candidate,
        "structural_difference": differences,
        "attempts": attempts,
        "witness": witness,
        "selection_score": best_score,
        "reason": "",
    }


def _round_requirements(prior, mutations: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    evaluations = 0
    for mutation in mutations:
        try:
            candidate = policy_mutations.apply(prior, mutation)
        except policy_mutations.PolicyMutationError:
            continue
        evaluations += len(_new_sequences(prior, candidate))
    return len(mutations), evaluations


def _record_selection(genesis, *, objective, prior, meta, status: str, viable, winner=None):
    payload = {
        "kind": "policy_mutation_selection",
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "meta_policy_digest": meta["meta_policy_digest"],
        "status": status,
        "measure": "trust_root_candidate_solved_count",
        "viable": [
            {
                "mutation_digest": item["mutation_digest"],
                "candidate_policy_digest": item["candidate_policy"]["policy_digest"],
                "selection_score": int(item["selection_score"]),
                "measurement_digest": item.get("measurement_digest", ""),
            }
            for item in sorted(viable, key=lambda item: item["mutation_digest"])
        ],
        "winner_mutation_digest": "" if winner is None else winner["mutation_digest"],
    }
    payload["selection_digest"] = digest_of(payload)
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [payload],
        generation=genesis.state["generation"],
    )
    entry = genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "policy_mutation_selection",
            "selection": payload,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return payload, entry


def run_meta_policy(
    genesis,
    here,
    *,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_steps: int = 16,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Measure the admitted mutation set and adopt only a unique strict maximum.

    ``max_steps`` remains as a compatibility/safety argument; the scientific selection boundary is
    the MetaPolicy's prospectively admitted ``max_attempts`` set. A round is never truncated by
    authored iteration order.
    """
    if max_steps <= 0:
        raise MetaPolicyError("meta-policy run allows no work")
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

    if policy_controller.bound_policy(genesis) != prior:
        raise MetaPolicyError("search policy changed outside the meta-policy adoption transaction")

    emitted = _invoke_meta_policy(genesis, objective, prior)
    pending: list[dict[str, Any]] = []
    if emitted.get("type") == "PolicyMutationBatch":
        if emitted.get("meta_policy_digest") != meta["meta_policy_digest"]:
            raise MetaPolicyError("mutation batch does not name the current meta-policy")
        if emitted.get("objective_digest") != objective["objective_digest"]:
            raise MetaPolicyError("mutation batch does not name the current objective")
        if emitted.get("prior_policy_digest") != prior["policy_digest"]:
            raise MetaPolicyError("mutation batch does not name the current search policy")
        pending = [policy_mutations.validate(item) for item in emitted.get("mutations") or []]
        admitted = {item["mutation_digest"] for item in _admitted_mutations(meta)}
        if not pending or any(item["mutation_digest"] not in admitted for item in pending):
            raise MetaPolicyError("meta-policy emitted a malformed mutation batch")
        if len({item["mutation_digest"] for item in pending}) != len(pending):
            raise MetaPolicyError("meta-policy emitted the same mutation twice")
    elif emitted.get("type") != "Stop":
        raise MetaPolicyError("meta-policy emitted an unrecognised selection intent")

    mutation_need, evaluation_need = _round_requirements(prior, pending)
    _require_round_budget(
        genesis,
        mutation_count=mutation_need,
        evaluation_count=evaluation_need,
    )

    questions = evaluation_snapshot(here.tasks)
    parent = run_candidate(
        genesis.body_factory,
        questions,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=genesis.grade,
    )
    if not parent["completed"]:
        raise MetaPolicyError("current body could not be measured for policy-mutation selection")

    fresh: dict[str, dict[str, Any]] = {}
    measurement_checkpoints: dict[str, str] = {}
    measurement_entries: dict[str, str] = {}
    for mutation in pending:
        evaluation = _evaluate_mutation(
            genesis,
            objective=objective,
            prior=prior,
            meta=meta,
            mutation=mutation,
            questions=questions,
            parent=parent,
        )
        digest = evaluation["mutation"]["mutation_digest"]
        if evaluation["accepted"]:
            measurement, entry = _retain_viable(
                genesis,
                objective=objective,
                prior=prior,
                meta=meta,
                evaluation=evaluation,
            )
        else:
            measurement, entry = _retain_rejection(
                genesis,
                objective=objective,
                prior=prior,
                meta=meta,
                evaluation=evaluation,
            )
        fresh[digest] = {
            "evaluation": evaluation,
            "measurement": measurement,
        }
        measurement_entries[digest] = entry["entry_digest"]
        if checkpoint_path is not None:
            measurement_checkpoints[digest] = genesis.persist(checkpoint_path)["checkpoint"]
        else:
            measurement_checkpoints[digest] = ""

    viable = _viable_measurements(
        genesis,
        objective=objective,
        prior=prior,
        meta=meta,
    )
    steps: list[dict[str, Any]] = []

    # Preserve one public step per mutation measured in this invocation. Viability is not adoption.
    for mutation in pending:
        digest = mutation["mutation_digest"]
        current = fresh[digest]
        evaluation = current["evaluation"]
        if not evaluation["accepted"]:
            steps.append(
                {
                    "intent": "PolicyMutation",
                    "accepted": False,
                    "trust_root_viable": False,
                    "mutation": evaluation["mutation"],
                    "candidate_policy": evaluation.get("candidate_policy"),
                    "reason": evaluation["reason"],
                    "attempts": evaluation.get("attempts") or [],
                    "observation": current["measurement"],
                    "journal_entry": measurement_entries[digest],
                    "checkpoint_digest": measurement_checkpoints[digest],
                    "durable_before_next_meta_intent": checkpoint_path is not None,
                }
            )

    selection_status = "no_viable_mutation"
    winner = None
    top: list[dict[str, Any]] = []
    if viable:
        best_score = max(int(item["selection_score"]) for item in viable)
        top = [item for item in viable if int(item["selection_score"]) == best_score]
        if len(top) == 1:
            winner = top[0]
            selection_status = "unique_strict_maximum"
        else:
            selection_status = "ambiguous_no_strict_maximum"

    selection, selection_entry = _record_selection(
        genesis,
        objective=objective,
        prior=prior,
        meta=meta,
        status=selection_status,
        viable=viable,
        winner=winner,
    )
    selection_checkpoint = "" if checkpoint_path is None else genesis.persist(checkpoint_path)["checkpoint"]

    if winner is None:
        for measurement in viable:
            digest = measurement["mutation_digest"]
            if digest not in fresh:
                continue
            is_top = any(item["mutation_digest"] == digest for item in top)
            reason = (
                "another viable mutation has a strictly higher trust-root score"
                if not is_top and top
                else "the admitted measure gives multiple mutations the same top score; no evidence chooses between them"
            )
            steps.append(
                {
                    "intent": "PolicyMutation",
                    "accepted": False,
                    "trust_root_viable": True,
                    "mutation": measurement["mutation"],
                    "candidate_policy": measurement["candidate_policy"],
                    "witness": measurement["witness"],
                    "selection_score": measurement["selection_score"],
                    "reason": reason,
                    "observation": measurement,
                    "journal_entry": measurement_entries[digest],
                    "checkpoint_digest": selection_checkpoint,
                    "durable_before_next_meta_intent": checkpoint_path is not None,
                }
            )
    else:
        winner_digest = winner["mutation_digest"]
        # Viable but lower-scoring mutations are measured evidence, not accepted machinery.
        for measurement in viable:
            digest = measurement["mutation_digest"]
            if digest == winner_digest or digest not in fresh:
                continue
            steps.append(
                {
                    "intent": "PolicyMutation",
                    "accepted": False,
                    "trust_root_viable": True,
                    "mutation": measurement["mutation"],
                    "candidate_policy": measurement["candidate_policy"],
                    "witness": measurement["witness"],
                    "selection_score": measurement["selection_score"],
                    "reason": "a different mutation is the unique strict maximum under the admitted measure",
                    "observation": measurement,
                    "journal_entry": measurement_entries[digest],
                    "checkpoint_digest": measurement_checkpoints[digest],
                    "durable_before_next_meta_intent": checkpoint_path is not None,
                }
            )

        candidate = winner["candidate_policy"]
        witness = winner["witness"]
        certificate_payload = {
            "schema": META_CERTIFICATE_SCHEMA,
            "objective": objective,
            "meta_policy_digest": meta["meta_policy_digest"],
            "prior_policy_digest": prior["policy_digest"],
            "mutation": winner["mutation"],
            "mutation_digest": winner_digest,
            "new_policy_digest": candidate["policy_digest"],
            "prior_policy_exhausted_on_this_objective": True,
            "structural_difference": winner["structural_difference"],
            "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
            "newly_reachable_attempts": winner["attempts"],
            "resolving_program": witness,
            "selection": {
                "all_admitted_mutations_measured": True,
                "measure": "trust_root_candidate_solved_count",
                "selection_score": int(winner["selection_score"]),
                "unique_strict_maximum": True,
                "selection_digest": selection["selection_digest"],
            },
            # Keep the historical field name for compatibility, but narrow the claim explicitly.
            "causal_dependency": {
                "established": True,
                "kind": "structural_reach_dependency",
                "counterfactual_machinery_ablation_established": False,
                "why": "the prior policy was exhausted; this mutation was the unique strict maximum "
                "among all admitted measured mutations and exposed a trust-root-accepted descendant",
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
            "update_kind": "meta_policy_evidence_ranked_mutation",
            "objective_digest": objective["objective_digest"],
            "meta_policy_digest": meta["meta_policy_digest"],
            "prior_policy_digest": prior["policy_digest"],
            "new_policy_digest": candidate["policy_digest"],
            "mutation_digest": winner_digest,
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
                "trust_root_viable": True,
                "mutation": winner["mutation"],
                "candidate_policy": candidate,
                "witness": witness,
                "selection_score": winner["selection_score"],
                "certificate": certificate,
                "journal_entry": entry["entry_digest"],
                "checkpoint_digest": checkpoint,
                "durable_before_next_meta_intent": checkpoint_path is not None,
            }
        )

    if not pending and winner is None:
        steps.append({"intent": "stop", "reason": str(emitted.get("reason") or "")})

    record = {
        "schema": META_RUN_SCHEMA,
        "objective": objective,
        "meta_policy": bound_meta_policy(genesis),
        "prior_policy_digest": prior["policy_digest"],
        "current_policy": policy_controller.bound_policy(genesis),
        "steps": steps,
        "selection": selection,
        "selection_journal_entry": selection_entry["entry_digest"],
        "selection_checkpoint": selection_checkpoint,
        "meta_policy_admission_checkpoint": admission_checkpoint,
        "final_state_digest": genesis.state["state_digest"],
    }
    record["run_digest"] = digest_of(record)
    return record
