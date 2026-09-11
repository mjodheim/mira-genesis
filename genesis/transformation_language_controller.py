"""Evidence-backed Genesis v2 transformation-language extension controller.

This is the first runtime layer above ``genesis.transformation_language``. The host supplies a
prospectively admitted lower micro-step kernel, but does not supply a winning composite operator.
The controller first requires the ordinary body-search policy to be exhausted. It then measures every
operator already held by the lineage. Only if the held transformation language has no measured reach
does it enumerate the complete bounded image of new canonical operator programs constructible from
the admitted lower steps.

Each candidate operator is judged indirectly, by what it lets the resulting search-policy descendant
construct. Generated bodies run through the existing sandbox and the unchanged trust root performs
the final parent/candidate comparison. Rejected measurements remain lineage observations. A language
extension is installed only when one candidate has a unique strict maximum among trust-root-accepted
candidates.

This closes one specific host choice: nobody passes the controller the composite operator to adopt.
It does *not* yet close Genesis v2. The lower micro-step kernel, its size bound and this controller are
still fixed DEVELOPMENT apparatus, and recursive second-generation language extension is a later
criterion.
"""
from __future__ import annotations

from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from genesis import objective_policy_controller as opc
from genesis import policies, policy_controller, policy_mutations, programs
from genesis import state as lineage_state
from genesis import transformation_language as language
from genesis.loop import evaluation_snapshot
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

LANGUAGE_TOOL_NAME = "transformation_language"
LANGUAGE_TOOL_ROLE = "lineage_transformation_language"
MEASUREMENT_SCHEMA = "genesis-transformation-language-measurement-v1"
SELECTION_SCHEMA = "genesis-transformation-language-selection-v1"
CERTIFICATE_SCHEMA = "genesis-transformation-language-extension-certificate-v1"

SEED_PROVENANCE = provenance(
    "host_written",
    produced_by="Genesis v2 transformation-language admission",
    detail="prospectively admitted bounded seed transformation language",
)


class TransformationLanguageControllerError(RuntimeError):
    """Raised when language self-extension cannot preserve its evidence or authority boundary."""


def _language_tool(genesis) -> Mapping[str, Any] | None:
    matches = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == LANGUAGE_TOOL_NAME and tool.get("role") == LANGUAGE_TOOL_ROLE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise TransformationLanguageControllerError(
            "lineage carries more than one current transformation language"
        )
    return matches[0]


def bound_language(genesis) -> dict[str, Any] | None:
    tool = _language_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping):
        raise TransformationLanguageControllerError(
            "lineage transformation-language tool carries no artifact"
        )
    try:
        return language.validate_language(artifact)
    except language.TransformationLanguageError as problem:
        raise TransformationLanguageControllerError(str(problem)) from problem


def _replace_language(genesis, value, *, provenance_record) -> None:
    validated = language.validate_language(value)
    tools: list[Mapping[str, Any]] = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == LANGUAGE_TOOL_NAME and tool.get("role") == LANGUAGE_TOOL_ROLE:
            if replaced:
                raise TransformationLanguageControllerError(
                    "lineage carries duplicate transformation-language tools"
                )
            tools.append(
                {
                    "name": LANGUAGE_TOOL_NAME,
                    "role": LANGUAGE_TOOL_ROLE,
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
                "name": LANGUAGE_TOOL_NAME,
                "role": LANGUAGE_TOOL_ROLE,
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


def admit_seed_language(genesis, seed: Mapping[str, Any]) -> bool:
    incoming = language.validate_language(seed)
    current = bound_language(genesis)
    if current is not None:
        if current != incoming:
            raise TransformationLanguageControllerError(
                "lineage already holds a different transformation language; replacement requires "
                "evidence-backed language extension"
            )
        return False
    _replace_language(genesis, incoming, provenance_record=SEED_PROVENANCE)
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "transformation_language_admission",
            "language_digest": incoming["language_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return True


def _candidate_program_signature(steps: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(language.validate_step(item)["step_digest"] for item in steps)


def candidate_operator_image(
    held_language: Mapping[str, Any], admitted_steps: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], ...]:
    """Enumerate the complete canonical operator image admitted for one extension round.

    The lower language defines operators as canonically ordered micro-step multisets. Therefore
    combinations-with-replacement is complete for this admitted representation and does not create
    duplicate candidates from permutations of independent edits.
    """
    held = language.validate_language(held_language)
    steps = sorted(
        (language.validate_step(item) for item in admitted_steps),
        key=language.step_sort_key,
    )
    if not steps:
        raise TransformationLanguageControllerError("language extension has no admitted micro-step")
    if len({item["step_digest"] for item in steps}) != len(steps):
        raise TransformationLanguageControllerError(
            "language extension micro-step kernel contains a duplicate"
        )

    existing = {
        _candidate_program_signature(operator["steps"])
        for operator in held["operators"]
    }
    candidates: list[dict[str, Any]] = []
    for length in range(1, int(held["max_operator_steps"]) + 1):
        for combination in combinations_with_replacement(steps, length):
            signature = _candidate_program_signature(combination)
            if signature in existing:
                continue
            program_digest = digest_of({"step_digests": list(signature)})
            operator = language.create_operator(
                "derived-" + program_digest[:16],
                list(combination),
            )
            candidates.append(operator)
    candidates.sort(key=lambda item: item["operator_digest"])
    return tuple(candidates)


def _new_sequences(prior, candidate) -> tuple[tuple[str, ...], ...]:
    old = set(policies.candidate_sequences(prior))
    return tuple(
        sequence for sequence in policies.candidate_sequences(candidate) if sequence not in old
    )


def _spend(genesis, dimension: str) -> None:
    try:
        genesis.budget.spend(dimension)
    except (TrustRootError, BudgetExhausted) as problem:
        raise TransformationLanguageControllerError(
            "transformation-language search needs prospectively admitted %r budget: %s"
            % (dimension, problem)
        ) from problem


def _round_requirements(prior, held, operators: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    body_evaluations = 0
    for operator in operators:
        try:
            temporary = (
                held
                if any(
                    item["operator_digest"] == operator["operator_digest"]
                    for item in held["operators"]
                )
                else language.extend_language(held, operator)
            )
            candidate = language.apply_operator(prior, temporary, operator["name"])
        except language.TransformationLanguageError:
            continue
        body_evaluations += len(_new_sequences(prior, candidate))
    return len(operators), body_evaluations


def _require_round_budget(genesis, prior, held, operators) -> None:
    operator_need, body_need = _round_requirements(prior, held, operators)
    try:
        operator_have = genesis.budget.remaining("language_operator_evaluations")
        body_have = genesis.budget.remaining("language_body_evaluations")
    except TrustRootError as problem:
        raise TransformationLanguageControllerError(
            "transformation-language selection has no prospectively admitted budget"
        ) from problem
    if operator_have < operator_need:
        raise TransformationLanguageControllerError(
            "language_operator_evaluations budget cannot measure the complete round: need %d, have %d"
            % (operator_need, operator_have)
        )
    if body_have < body_need:
        raise TransformationLanguageControllerError(
            "language_body_evaluations budget cannot measure the complete round: need %d, have %d"
            % (body_need, body_have)
        )


def _evaluate_operator(genesis, *, here, prior, held, operator, parent, questions, phase):
    operator = language.validate_operator(operator)
    _spend(genesis, "language_operator_evaluations")
    already_held = any(
        item["operator_digest"] == operator["operator_digest"] for item in held["operators"]
    )
    candidate_language = held if already_held else language.extend_language(held, operator)
    try:
        candidate_policy = language.apply_operator(prior, candidate_language, operator["name"])
    except language.TransformationLanguageError as problem:
        return {
            "schema": MEASUREMENT_SCHEMA,
            "phase": phase,
            "operator": operator,
            "candidate_language_digest": candidate_language["language_digest"],
            "candidate_policy": None,
            "structural_difference": [],
            "attempts": [],
            "accepted": False,
            "selection_score": -1,
            "witness": None,
            "reason": str(problem),
        }

    differences = policy_mutations.structural_difference(prior, candidate_policy)
    sequences = _new_sequences(prior, candidate_policy)
    attempts: list[dict[str, Any]] = []
    viable: list[dict[str, Any]] = []
    candidate_provenance = provenance(
        "lineage_owned",
        produced_by="Genesis v2 transformation-language evaluation",
        detail=operator["operator_digest"],
    )
    for sequence in sequences:
        _spend(genesis, "language_body_evaluations")
        generated = programs.artifact(
            registry_reference=candidate_policy["registry_reference"],
            operations=sequence,
            input_field=candidate_policy["input_field"],
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
            candidate_provenance=candidate_provenance,
            evaluation_contract_record=genesis.evaluation_contract,
        )
        problems = verify_verdict(verdict, admitted_source_sha256=genesis.admitted_source_sha256)
        if problems:
            raise TransformationLanguageControllerError("; ".join(problems))
        score = int(verdict["candidate"]["counts"]["solved"])
        attempt = {
            "operations": list(sequence),
            "accepted": bool(verdict["accepted"]),
            "selection_score": score,
            "verdict_digest": verdict["verdict_digest"],
            "sandbox_digest": run["result_digest"],
            "body_artifact": body_artifact,
        }
        attempts.append(attempt)
        if verdict["accepted"]:
            viable.append(attempt)

    if viable:
        best_score = max(item["selection_score"] for item in viable)
        best = [item for item in viable if item["selection_score"] == best_score]
        witness = min(best, key=lambda item: item["body_artifact"]["artifact_digest"])
        accepted = True
        reason = ""
    else:
        best_score = -1
        witness = None
        accepted = False
        reason = "transformation operator produced no trust-root-accepted newly reachable body"

    record = {
        "schema": MEASUREMENT_SCHEMA,
        "phase": phase,
        "operator": operator,
        "candidate_language_digest": candidate_language["language_digest"],
        "candidate_policy": candidate_policy,
        "structural_difference": differences,
        "attempts": attempts,
        "accepted": accepted,
        "selection_score": best_score,
        "witness": witness,
        "reason": reason,
    }
    record["measurement_digest"] = digest_of(record)
    return record


def _retain_measurement(genesis, measurement: Mapping[str, Any], checkpoint: Path | None) -> str:
    record = dict(measurement)
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [record],
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation" if record.get("accepted") else "diagnosis",
        genesis.state["generation"],
        {
            "arm": "transformation_language_measurement",
            "measurement_digest": record.get("measurement_digest", ""),
            "operator_digest": record["operator"]["operator_digest"],
            "accepted": bool(record.get("accepted")),
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    if checkpoint is None:
        return ""
    return genesis.persist(checkpoint)["checkpoint"]


def _measure_round(genesis, *, here, prior, held, operators, parent, questions, phase, checkpoint):
    _require_round_budget(genesis, prior, held, operators)
    records = []
    for operator in operators:
        measurement = _evaluate_operator(
            genesis,
            here=here,
            prior=prior,
            held=held,
            operator=operator,
            parent=parent,
            questions=questions,
            phase=phase,
        )
        measurement["checkpoint_digest"] = _retain_measurement(genesis, measurement, checkpoint)
        records.append(measurement)
    return records


def run_extension_search(
    genesis,
    here,
    *,
    admitted_steps: Sequence[Mapping[str, Any]],
    seed_language: Mapping[str, Any] | None = None,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Measure held language reach, then search its complete bounded lower-language extension image."""
    prior = policy_controller.bound_policy(genesis)
    if prior is None:
        raise TransformationLanguageControllerError(
            "lineage has no generated search policy whose transformation language can evolve"
        )
    if not opc.exhausted(genesis, here, prior):
        raise TransformationLanguageControllerError(
            "body-search policy is not exhausted; use currently held search machinery before "
            "extending its transformation language"
        )
    admitted = False
    if seed_language is not None:
        admitted = admit_seed_language(genesis, seed_language)
    held = bound_language(genesis)
    if held is None:
        raise TransformationLanguageControllerError("lineage has no transformation language")

    checkpoint = Path(checkpoint_directory) if checkpoint_directory is not None else None
    admission_checkpoint = ""
    if checkpoint is not None and admitted:
        admission_checkpoint = genesis.persist(checkpoint)["checkpoint"]

    questions = evaluation_snapshot(here.tasks)
    parent = run_candidate(
        genesis.body_factory,
        questions,
        genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
        grade=genesis.grade,
    )
    if not parent["completed"]:
        raise TransformationLanguageControllerError(
            "current body could not be measured for transformation-language search"
        )

    held_measurements = _measure_round(
        genesis,
        here=here,
        prior=prior,
        held=held,
        operators=tuple(held["operators"]),
        parent=parent,
        questions=questions,
        phase="held_language",
        checkpoint=checkpoint,
    )
    held_viable = [item for item in held_measurements if item["accepted"]]
    if held_viable:
        result = {
            "status": "held_language_has_measured_reach",
            "prior_language_digest": held["language_digest"],
            "held_measurements": held_measurements,
            "candidate_image": [],
            "candidate_measurements": [],
            "language_changed": False,
            "selection": None,
            "certificate": None,
            "admission_checkpoint": admission_checkpoint,
        }
        result["run_digest"] = digest_of(result)
        return result

    candidates = candidate_operator_image(held, admitted_steps)
    if not candidates:
        raise TransformationLanguageControllerError(
            "complete lower-language image contains no operator outside the held language"
        )
    candidate_measurements = _measure_round(
        genesis,
        here=here,
        prior=prior,
        held=held,
        operators=candidates,
        parent=parent,
        questions=questions,
        phase="candidate_extension",
        checkpoint=checkpoint,
    )
    viable = [item for item in candidate_measurements if item["accepted"]]
    best_score = max((int(item["selection_score"]) for item in viable), default=-1)
    winners = [item for item in viable if int(item["selection_score"]) == best_score]
    if not winners:
        status = "complete_image_exhausted_no_extension"
        winner = None
    elif len(winners) != 1:
        status = "ambiguous_no_unique_strict_maximum"
        winner = None
    else:
        status = "unique_strict_maximum"
        winner = winners[0]

    selection = {
        "schema": SELECTION_SCHEMA,
        "prior_language_digest": held["language_digest"],
        "prior_policy_digest": prior["policy_digest"],
        "candidate_operator_digests": [item["operator_digest"] for item in candidates],
        "viable": [
            {
                "operator_digest": item["operator"]["operator_digest"],
                "measurement_digest": item["measurement_digest"],
                "selection_score": int(item["selection_score"]),
            }
            for item in viable
        ],
        "selection_rule": "unique_strict_maximum_trust_root_solved_count_v1",
        "status": status,
        "winner_operator_digest": "" if winner is None else winner["operator"]["operator_digest"],
    }
    selection["selection_digest"] = digest_of(selection)

    certificate = None
    if winner is not None:
        descendant = language.extend_language(held, winner["operator"])
        if descendant["parent_language_digest"] != held["language_digest"]:
            raise TransformationLanguageControllerError(
                "selected language descendant does not name the held language as parent"
            )
        certificate = {
            "schema": CERTIFICATE_SCHEMA,
            "prior_language_digest": held["language_digest"],
            "descendant_language_digest": descendant["language_digest"],
            "operator": winner["operator"],
            "operator_program_digest": language.operator_program_digest(winner["operator"]),
            "prior_policy_digest": prior["policy_digest"],
            "candidate_policy_digest": winner["candidate_policy"]["policy_digest"],
            "structural_difference": list(winner["structural_difference"]),
            "witness": winner["witness"],
            "held_language_exhausted": True,
            "complete_candidate_image": [item["operator_digest"] for item in candidates],
            "selection_digest": selection["selection_digest"],
            "trust_root_source_sha256": genesis.admitted_source_sha256,
            "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
        }
        certificate["certificate_digest"] = digest_of(certificate)
        _replace_language(
            genesis,
            descendant,
            provenance_record=provenance(
                "lineage_owned",
                produced_by="Genesis v2 transformation-language extension search",
                detail=certificate["certificate_digest"],
            ),
        )
        genesis.state = lineage_state.create_state(
            body_digest=genesis.state["body_digest"],
            components=genesis.state["components"],
            vocabulary=genesis.state["vocabulary"],
            tools=genesis.state["tools"],
            acquisitions=genesis.state["acquisitions"],
            observations=genesis.state["observations"] + [
                {
                    "kind": "transformation_language_extension",
                    "certificate": certificate,
                }
            ],
            generation=genesis.state["generation"],
        )
        genesis.journal.append(
            "acquisition",
            genesis.state["generation"],
            {
                "name": "transformation-language:" + descendant["language_digest"][:16],
                "role": LANGUAGE_TOOL_ROLE,
                "certificate_digest": certificate["certificate_digest"],
                "parent_language_digest": held["language_digest"],
                "new_language_digest": descendant["language_digest"],
                "operator_digest": winner["operator"]["operator_digest"],
                "new_state_digest": genesis.state["state_digest"],
            },
        )
        if checkpoint is not None:
            genesis.persist(checkpoint)

    result = {
        "status": status,
        "prior_language_digest": held["language_digest"],
        "held_measurements": held_measurements,
        "candidate_image": list(candidates),
        "candidate_measurements": candidate_measurements,
        "language_changed": winner is not None,
        "selection": selection,
        "certificate": certificate,
        "current_language": bound_language(genesis),
        "admission_checkpoint": admission_checkpoint,
    }
    result["run_digest"] = digest_of(result)
    return result
