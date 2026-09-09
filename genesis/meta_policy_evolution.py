"""Evidence-backed descendants of the lineage-held MetaPolicy.

PR #289 made policy-mutation selection order-invariant, but the MetaPolicy candidate set itself was
still terminal host-admitted data. This module adds one bounded transition above it without giving
that transition any evaluator authority.

The current MetaPolicy must first be empirically exhausted on the current search policy/objective:
every mutation it admits has been measured and the lower-level search policy is still exhausted. The
runtime then synthesises *data-only* one-extension MetaPolicy descendants from the already-admitted
policy-mutation language and the current policy's admitted operation registry. No new Python mutation
kind is generated at runtime.

Every candidate MetaPolicy descendant differs by one appended canonical PolicyMutation record and
names the current MetaPolicy through ``parent_meta_policy_digest``. The newly added mutation is
measured under one immutable task snapshot, the same current body, the same trust root and the same
evaluation contract. The runtime adopts a MetaPolicy descendant only when its newly reachable body
score is the unique strict maximum across the complete synthesised candidate set. Ties adopt nothing.

This establishes bounded *MetaPolicy descendant acquisition*. It does not establish open-ended
self-programming or counterfactual meta-machinery causality. The mutation language and operation
registry remain prospectively admitted apparatus.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from genesis import controller, meta_policy_controller as meta
from genesis import objective_policy_controller as opc, policies, policy_controller, policy_mutations
from genesis import programs, retentive_objectives as retentive
from genesis import state as lineage_state
from genesis.loop import evaluation_snapshot
from genesis.probe import resolve_registry
from genesis.sandbox import run_candidate
from genesis.trust_root import (
    BudgetExhausted,
    TrustRootError,
    artifact_digest_of,
    decide,
    digest_of,
    provenance,
    verify_verdict,
)

META_EVOLUTION_SCHEMA = "genesis-meta-policy-evolution-v1"
META_DESCENDANT_CERTIFICATE_SCHEMA = "genesis-meta-policy-descendant-certificate-v1"
MEASUREMENT_KIND = "meta_policy_extension_measurement"
UPDATE_KIND = "meta_policy_updated"


class MetaPolicyEvolutionError(RuntimeError):
    """Raised when the meta-machinery transition is not completely evidenced."""


def _spend(genesis, dimension: str) -> None:
    try:
        genesis.budget.spend(dimension)
    except (TrustRootError, BudgetExhausted) as problem:
        raise MetaPolicyEvolutionError(
            "MetaPolicy evolution needs a prospectively admitted %r budget: %s"
            % (dimension, problem)
        ) from problem


def _replace_meta_policy(genesis, descendant, *, provenance_record, observation) -> None:
    validated = meta.validate_meta_policy(descendant)
    current = meta.bound_meta_policy(genesis)
    if current is None:
        raise MetaPolicyEvolutionError("lineage lost its current MetaPolicy")
    if validated["parent_meta_policy_digest"] != current["meta_policy_digest"]:
        raise MetaPolicyEvolutionError("MetaPolicy descendant does not name the current MetaPolicy")

    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == meta.META_TOOL_NAME and tool.get("role") == meta.META_ROLE:
            if replaced:
                raise MetaPolicyEvolutionError("lineage carries duplicate MetaPolicy tools")
            tools.append(
                {
                    "name": meta.META_TOOL_NAME,
                    "role": meta.META_ROLE,
                    "artifact": validated,
                    "provenance": provenance_record,
                }
            )
            replaced = True
        else:
            tools.append(tool)
    if not replaced:
        raise MetaPolicyEvolutionError("lineage carries no MetaPolicy tool to replace")

    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [dict(observation)],
        generation=genesis.state["generation"],
    )


def _current_meta_exhausted(genesis, here, *, prior_policy, current_meta, objective) -> bool:
    if not opc.exhausted(genesis, here, prior_policy):
        return False
    evidence = controller._controller_context(genesis).evidence
    seen = meta._evaluated_mutations(
        evidence,
        objective_digest=objective["objective_digest"],
        prior_policy_digest=prior_policy["policy_digest"],
    )
    admitted = {item["mutation_digest"] for item in meta._admitted_mutations(current_meta)}
    return admitted.issubset(seen)


def synthesised_extensions(prior_policy: Mapping[str, Any], current_meta: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Canonical policy-mutation data the current MetaPolicy does not yet contain.

    Candidate data is derived from the fixed, already-admitted mutation language. New operation
    extensions come from the policy's admitted registry; they are not new executable Python kinds.
    """
    prior = policies.validate(prior_policy)
    held_meta = meta.validate_meta_policy(current_meta)
    held = {item["mutation_digest"] for item in held_meta["mutations"]}
    candidates: list[dict[str, Any]] = []

    registry = resolve_registry(prior["registry_reference"])
    for operation in sorted(str(name) for name in registry):
        if operation in prior["operation_names"]:
            continue
        mutation = policy_mutations.create("add_operation", operation=operation)
        if mutation["mutation_digest"] not in held:
            candidates.append(mutation)

    if int(prior["max_length"]) < int(prior["ceiling_length"]):
        mutation = policy_mutations.create("increase_depth")
        if mutation["mutation_digest"] not in held:
            candidates.append(mutation)

    # Candidate-limit growth is deliberately excluded from this first descendant path: unlike adding
    # an operation or one admitted depth level, it may expose only a prefix of an already-defined
    # search space. It remains available to the lower-level fixed mutation language but is not used
    # as evidence of a new MetaPolicy candidate here.
    return tuple(sorted(candidates, key=lambda item: item["mutation_digest"]))


def _descendant(current_meta: Mapping[str, Any], added_mutation: Mapping[str, Any]) -> dict[str, Any]:
    held = meta.validate_meta_policy(current_meta)
    if int(held["max_attempts"]) != len(held["mutations"]):
        raise MetaPolicyEvolutionError(
            "MetaPolicy evolution currently requires its complete candidate set to be admitted"
        )
    mutation = policy_mutations.validate(added_mutation)
    if mutation in held["mutations"]:
        raise MetaPolicyEvolutionError("MetaPolicy extension repeats an already-held mutation")
    return meta.create_meta_policy(
        [*held["mutations"], mutation],
        max_attempts=len(held["mutations"]) + 1,
        parent_meta_policy_digest=held["meta_policy_digest"],
    )


def _new_sequences(prior_policy, candidate_policy) -> tuple[tuple[str, ...], ...]:
    old = set(policies.candidate_sequences(prior_policy))
    return tuple(
        sequence
        for sequence in policies.candidate_sequences(candidate_policy)
        if sequence not in old
    )


def _measurement_key(*, objective, prior_policy, current_meta, body_digest, mutation_digest) -> tuple[str, ...]:
    return (
        objective["objective_digest"],
        prior_policy["policy_digest"],
        current_meta["meta_policy_digest"],
        body_digest,
        mutation_digest,
    )


def _retained_measurements(genesis, *, objective, prior_policy, current_meta, body_digest) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for item in genesis.state.get("observations", []):
        if not isinstance(item, Mapping) or item.get("kind") != MEASUREMENT_KIND:
            continue
        if (
            item.get("objective_digest") != objective["objective_digest"]
            or item.get("prior_policy_digest") != prior_policy["policy_digest"]
            or item.get("parent_meta_policy_digest") != current_meta["meta_policy_digest"]
            or item.get("body_artifact_digest") != body_digest
            or item.get("evaluation_contract_digest") != genesis.evaluation_contract["contract_digest"]
        ):
            continue
        mutation_digest = str(item.get("added_mutation_digest") or "")
        if mutation_digest:
            records[mutation_digest] = dict(item)
    return records


def _retain_measurement(genesis, record: Mapping[str, Any]) -> str:
    measurement = dict(record)
    measurement["measurement_digest"] = digest_of(measurement)
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [measurement],
        generation=genesis.state["generation"],
    )
    entry = genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "meta_policy_extension_measurement",
            "measurement": measurement,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return entry["entry_digest"]


def _candidate_cost(prior_policy, mutation) -> int:
    try:
        candidate_policy = policy_mutations.apply(prior_policy, mutation)
    except policy_mutations.PolicyMutationError:
        return 0
    return len(_new_sequences(prior_policy, candidate_policy))


def _require_complete_budget(genesis, *, pending: Iterable[Mapping[str, Any]], prior_policy) -> None:
    pending = list(pending)
    required_candidates = len(pending)
    required_evaluations = sum(_candidate_cost(prior_policy, mutation) for mutation in pending)
    try:
        candidate_remaining = genesis.budget.remaining("meta_policy_candidates")
        evaluation_remaining = genesis.budget.remaining("meta_policy_evaluations")
    except TrustRootError as problem:
        raise MetaPolicyEvolutionError(
            "MetaPolicy evolution has no prospectively admitted complete-round budget"
        ) from problem
    if candidate_remaining < required_candidates:
        raise MetaPolicyEvolutionError(
            "meta_policy_candidates budget cannot measure the complete MetaPolicy round: need %d, have %d"
            % (required_candidates, candidate_remaining)
        )
    if evaluation_remaining < required_evaluations:
        raise MetaPolicyEvolutionError(
            "meta_policy_evaluations budget cannot measure the complete MetaPolicy round: need %d, have %d"
            % (required_evaluations, evaluation_remaining)
        )


def _evaluate_extension(
    genesis,
    *,
    objective,
    prior_policy,
    current_meta,
    mutation,
    questions,
    parent,
    body_digest,
) -> dict[str, Any]:
    mutation = policy_mutations.validate(mutation)
    _spend(genesis, "meta_policy_candidates")
    descendant_meta = _descendant(current_meta, mutation)

    try:
        candidate_policy = policy_mutations.apply(prior_policy, mutation)
    except policy_mutations.PolicyMutationError as problem:
        return {
            "kind": MEASUREMENT_KIND,
            "objective_digest": objective["objective_digest"],
            "prior_policy_digest": prior_policy["policy_digest"],
            "parent_meta_policy_digest": current_meta["meta_policy_digest"],
            "candidate_meta_policy": descendant_meta,
            "candidate_meta_policy_digest": descendant_meta["meta_policy_digest"],
            "added_mutation": mutation,
            "added_mutation_digest": mutation["mutation_digest"],
            "body_artifact_digest": body_digest,
            "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
            "candidate_policy": None,
            "attempts": [],
            "viable": False,
            "selection_score": -1,
            "reason": str(problem),
        }

    sequences = _new_sequences(prior_policy, candidate_policy)
    attempts: list[dict[str, Any]] = []
    accepted_attempts: list[dict[str, Any]] = []
    meta_provenance = provenance(
        "lineage_owned",
        produced_by="candidate MetaPolicy descendant evaluation",
        detail=descendant_meta["meta_policy_digest"],
    )
    for sequence in sequences:
        _spend(genesis, "meta_policy_evaluations")
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
            raise MetaPolicyEvolutionError("; ".join(problems))
        attempt = {
            "operations": list(sequence),
            "accepted": bool(verdict["accepted"]),
            "candidate_solved_count": int(verdict["candidate"]["counts"]["solved"]),
            "verdict_digest": verdict["verdict_digest"],
            "sandbox_digest": run["result_digest"],
            "body_artifact": artifact_digest_of(generated),
        }
        attempts.append(attempt)
        if verdict["accepted"]:
            accepted_attempts.append(attempt)

    if accepted_attempts:
        selection_score = max(item["candidate_solved_count"] for item in accepted_attempts)
        top = [item for item in accepted_attempts if item["candidate_solved_count"] == selection_score]
        # Digest order is only a representative-record convention. It does not choose the
        # MetaPolicy descendant: every tied program contributes the same extension score.
        witness = sorted(top, key=lambda item: item["body_artifact"]["artifact_digest"])[0]
        viable = True
        reason = ""
    else:
        selection_score = -1
        witness = None
        viable = False
        reason = "MetaPolicy extension exposed no trust-root-accepted new body"

    return {
        "kind": MEASUREMENT_KIND,
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior_policy["policy_digest"],
        "parent_meta_policy_digest": current_meta["meta_policy_digest"],
        "candidate_meta_policy": descendant_meta,
        "candidate_meta_policy_digest": descendant_meta["meta_policy_digest"],
        "added_mutation": mutation,
        "added_mutation_digest": mutation["mutation_digest"],
        "body_artifact_digest": body_digest,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
        "candidate_policy": candidate_policy,
        "attempts": attempts,
        "witness": witness,
        "viable": viable,
        "selection_score": selection_score,
        "measure": "trust_root_candidate_solved_count",
        "reason": reason,
    }


def evolve_meta_policy(
    genesis,
    here,
    *,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Acquire one MetaPolicy descendant after current meta-search is empirically exhausted."""
    retentive.assert_retains_prior_work(genesis, here)
    prior_policy = policy_controller.bound_policy(genesis)
    current_meta = meta.bound_meta_policy(genesis)
    if prior_policy is None or current_meta is None:
        raise MetaPolicyEvolutionError("lineage must hold both search policy and MetaPolicy")
    objective = opc.objective_record(genesis, here)
    if not _current_meta_exhausted(
        genesis,
        here,
        prior_policy=prior_policy,
        current_meta=current_meta,
        objective=objective,
    ):
        raise MetaPolicyEvolutionError(
            "current MetaPolicy is not exhausted on the current policy/objective"
        )

    extensions = synthesised_extensions(prior_policy, current_meta)
    if not extensions:
        return {
            "schema": META_EVOLUTION_SCHEMA,
            "accepted": False,
            "selection_reason": "no_synthesised_meta_policy_descendant",
            "current_meta_policy": current_meta,
            "measurements": [],
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
        raise MetaPolicyEvolutionError("current body could not be measured for MetaPolicy evolution")
    body_digest = artifact_digest_of(genesis.body_factory)["artifact_digest"]

    retained = _retained_measurements(
        genesis,
        objective=objective,
        prior_policy=prior_policy,
        current_meta=current_meta,
        body_digest=body_digest,
    )
    pending = [item for item in extensions if item["mutation_digest"] not in retained]
    _require_complete_budget(genesis, pending=pending, prior_policy=prior_policy)

    checkpoint_path = Path(checkpoint_directory) if checkpoint_directory is not None else None
    for mutation in pending:
        measurement = _evaluate_extension(
            genesis,
            objective=objective,
            prior_policy=prior_policy,
            current_meta=current_meta,
            mutation=mutation,
            questions=questions,
            parent=parent,
            body_digest=body_digest,
        )
        journal_entry = _retain_measurement(genesis, measurement)
        measurement["journal_entry"] = journal_entry
        if checkpoint_path is not None:
            genesis.persist(checkpoint_path)

    retained = _retained_measurements(
        genesis,
        objective=objective,
        prior_policy=prior_policy,
        current_meta=current_meta,
        body_digest=body_digest,
    )
    required_digests = {item["mutation_digest"] for item in extensions}
    if not required_digests.issubset(retained):
        raise MetaPolicyEvolutionError("MetaPolicy selection round is incomplete")
    measurements = [retained[item["mutation_digest"]] for item in extensions]
    viable = [item for item in measurements if item.get("viable")]
    if not viable:
        selection_reason = "no_viable_meta_policy_descendant"
        winner = None
    else:
        top_score = max(int(item["selection_score"]) for item in viable)
        winners = [item for item in viable if int(item["selection_score"]) == top_score]
        if len(winners) != 1:
            selection_reason = "ambiguous_no_strict_maximum"
            winner = None
        else:
            selection_reason = "unique_strict_maximum"
            winner = winners[0]

    certificate = None
    checkpoint = ""
    if winner is not None:
        descendant = meta.validate_meta_policy(winner["candidate_meta_policy"])
        certificate_payload = {
            "schema": META_DESCENDANT_CERTIFICATE_SCHEMA,
            "objective": objective,
            "prior_policy_digest": prior_policy["policy_digest"],
            "parent_meta_policy_digest": current_meta["meta_policy_digest"],
            "new_meta_policy_digest": descendant["meta_policy_digest"],
            "added_mutation": winner["added_mutation"],
            "added_mutation_digest": winner["added_mutation_digest"],
            "current_meta_policy_exhausted": True,
            "complete_synthesised_candidate_set_measured": True,
            "selection_rule": "unique_strict_maximum",
            "selection_measure": "trust_root_candidate_solved_count",
            "selection_score": winner["selection_score"],
            "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
            "all_measurement_digests": sorted(item["measurement_digest"] for item in measurements),
            "dependency": {
                "kind": "meta_policy_structural_reach_dependency",
                "established": True,
                "counterfactual_meta_machinery_ablation_established": False,
                "why": "the exhausted parent MetaPolicy admitted no remaining policy mutation on "
                "this objective; one data-only extension had a unique strict maximum under the "
                "unchanged trust-root measure",
            },
        }
        certificate = {
            **certificate_payload,
            "certificate_digest": digest_of(certificate_payload),
        }
        provenance_record = provenance(
            "lineage_owned",
            produced_by="evidence-backed MetaPolicy evolution",
            detail=certificate["certificate_digest"],
        )
        observation = {
            "kind": UPDATE_KIND,
            "objective_digest": objective["objective_digest"],
            "prior_policy_digest": prior_policy["policy_digest"],
            "parent_meta_policy_digest": current_meta["meta_policy_digest"],
            "new_meta_policy_digest": descendant["meta_policy_digest"],
            "certificate_digest": certificate["certificate_digest"],
            "dependency": certificate["dependency"],
        }
        _replace_meta_policy(
            genesis,
            descendant,
            provenance_record=provenance_record,
            observation=observation,
        )
        genesis.journal.append(
            "observation",
            genesis.state["generation"],
            {
                "arm": "meta_policy_update",
                "certificate": certificate,
                "new_state_digest": genesis.state["state_digest"],
            },
        )
        if checkpoint_path is not None:
            checkpoint = genesis.persist(checkpoint_path)["checkpoint"]

    record = {
        "schema": META_EVOLUTION_SCHEMA,
        "accepted": winner is not None,
        "selection_reason": selection_reason,
        "objective": objective,
        "prior_policy": prior_policy,
        "parent_meta_policy": current_meta,
        "measurements": measurements,
        "winner": winner,
        "certificate": certificate,
        "current_meta_policy": meta.bound_meta_policy(genesis),
        "checkpoint_digest": checkpoint,
        "final_state_digest": genesis.state["state_digest"],
    }
    record["run_digest"] = digest_of(record)
    return record
