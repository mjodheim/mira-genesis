"""Second-generation transformation-language extension for Genesis v2 DEVELOPMENT work.

Genesis v2's first extension search composes host-admitted primitive micro-steps. That is not enough
for recursive self-extension: a later language descendant must be able to *use an earlier acquired
operator as part of the language from which it constructs the next operator*.

This module derives that recursive lower language from lineage history rather than asking the caller
which acquired operator to reuse. Every non-invocation primitive already present in the held language
is retained, and every evidence-backed acquired operator currently held becomes one
``invoke_held_operator`` micro-step identified by its content digest. An operator counts as acquired
only when its extension certificate reproduces, names the unchanged trust/evaluation identities, and
has the matching append-only journal acquisition. The ordinary transformation-language controller
then measures the full bounded candidate image under the unchanged trust root.

A successful recursive result is accepted here only if the winning operator actually invokes at
least one previously acquired operator. The module records two complementary dependency checks:
removing the invoked predecessor makes the descendant language fail reconstruction, and the same
complete measured round shows that the recursive winner has strictly greater accepted reach than the
full counterfactual image without that predecessor — including the predecessor itself as a possible
reacquisition after ablation. This is a bounded DEVELOPMENT recursion mechanism; the fixed primitive
kernel, finite operator length and selection rule remain apparatus.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from genesis import state as lineage_state
from genesis import transformation_language as language
from genesis import transformation_language_controller as controller
from genesis.trust_root import digest_of

RECURSION_SCHEMA = "genesis-recursive-transformation-language-extension-v1"


class RecursiveTransformationLanguageError(RuntimeError):
    """Raised when a claimed recursive language extension does not depend on acquired language."""


def _journal_backs_extension(genesis, certificate: Mapping[str, Any]) -> bool:
    """Whether one exact hash-chained acquisition entry binds this extension certificate."""
    operator = certificate.get("operator")
    if not isinstance(operator, Mapping):
        return False
    try:
        validated = language.validate_operator(operator)
    except language.TransformationLanguageError:
        return False
    matches = []
    for entry in genesis.journal.of_kind("acquisition"):
        payload = entry.get("payload") or {}
        if not isinstance(payload, Mapping):
            continue
        if (
            payload.get("role") == controller.LANGUAGE_TOOL_ROLE
            and payload.get("certificate_digest") == certificate.get("certificate_digest")
            and payload.get("parent_language_digest") == certificate.get("prior_language_digest")
            and payload.get("new_language_digest") == certificate.get("descendant_language_digest")
            and payload.get("operator_digest") == validated["operator_digest"]
        ):
            matches.append(entry)
    return len(matches) == 1


def _validated_extension_certificate(
    genesis, certificate: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Accept only a self-reproducing extension certificate backed by the immutable authority line."""
    if not isinstance(certificate, Mapping):
        return None
    value = dict(certificate)
    if value.get("schema") != controller.CERTIFICATE_SCHEMA:
        return None
    recorded_digest = str(value.get("certificate_digest") or "")
    if not recorded_digest:
        return None
    payload = {key: item for key, item in value.items() if key != "certificate_digest"}
    if recorded_digest != digest_of(payload):
        return None
    if value.get("trust_root_source_sha256") != genesis.admitted_source_sha256:
        return None
    if value.get("evaluation_contract_digest") != genesis.evaluation_contract["contract_digest"]:
        return None
    if not str(value.get("prior_language_digest") or ""):
        return None
    if not str(value.get("descendant_language_digest") or ""):
        return None
    try:
        language.validate_operator(value.get("operator") or {})
    except language.TransformationLanguageError:
        return None
    if not _journal_backs_extension(genesis, value):
        return None
    return value


def _extension_certificates(genesis) -> tuple[dict[str, Any], ...]:
    values: list[dict[str, Any]] = []
    for item in genesis.state.get("observations", []):
        if not isinstance(item, Mapping) or item.get("kind") != "transformation_language_extension":
            continue
        validated = _validated_extension_certificate(genesis, item.get("certificate"))
        if validated is not None:
            values.append(validated)
    return tuple(values)


def acquired_operator_digests(genesis, held_language: Mapping[str, Any]) -> tuple[str, ...]:
    """Operators proved to have entered through the evidence-backed extension controller."""
    held = language.validate_language(held_language)
    held_digests = {item["operator_digest"] for item in held["operators"]}
    acquired = []
    for certificate in _extension_certificates(genesis):
        descendant_digest = str(certificate.get("descendant_language_digest") or "")
        operator = certificate.get("operator")
        if not isinstance(operator, Mapping):
            continue
        try:
            validated = language.validate_operator(operator)
        except language.TransformationLanguageError:
            continue
        if descendant_digest and validated["operator_digest"] in held_digests:
            acquired.append(validated["operator_digest"])
    return tuple(sorted(set(acquired)))


def derived_recursive_steps(genesis) -> tuple[dict[str, Any], ...]:
    """Derive the complete admitted lower-step set from current language and acquisition history."""
    held = controller.bound_language(genesis)
    if held is None:
        raise RecursiveTransformationLanguageError("lineage has no transformation language")

    steps: dict[str, dict[str, Any]] = {}
    for operator in held["operators"]:
        for raw_step in operator["steps"]:
            step = language.validate_step(raw_step)
            # Invocation edges are regenerated from evidence-backed acquisitions below. Carrying an
            # invocation merely because an operator text contains one would let an unverified edge
            # bootstrap itself.
            if step["kind"] == "invoke_held_operator":
                continue
            steps[step["step_digest"]] = step

    for operator_digest in acquired_operator_digests(genesis, held):
        step = language.create_step(
            "invoke_held_operator",
            operator_digest=operator_digest,
        )
        steps[step["step_digest"]] = step

    if not steps:
        raise RecursiveTransformationLanguageError(
            "current lineage history yields no recursive transformation primitives"
        )
    return tuple(sorted(steps.values(), key=language.step_sort_key))


def _invoked_acquired_digests(genesis, held_before, operator) -> tuple[str, ...]:
    acquired = set(acquired_operator_digests(genesis, held_before))
    invoked = {
        step["operator_digest"]
        for step in language.validate_operator(operator)["steps"]
        if step["kind"] == "invoke_held_operator"
        and step["operator_digest"] in acquired
    }
    return tuple(sorted(invoked))


def _ablation_refuses_descendant(descendant, *, removed_digests: tuple[str, ...]) -> tuple[bool, str]:
    """Remove invoked predecessor operators and require the recursive language to become invalid."""
    kept = [
        item
        for item in language.validate_language(descendant)["operators"]
        if item["operator_digest"] not in set(removed_digests)
    ]
    try:
        language.create_language(
            kept,
            max_operator_steps=int(descendant["max_operator_steps"]),
            parent_language_digest=str(descendant.get("parent_language_digest") or ""),
        )
    except language.TransformationLanguageError as problem:
        return True, str(problem)
    return False, "descendant language still reconstructs after acquired predecessor removal"


def _operator_invokes_any(operator: Mapping[str, Any], digests: tuple[str, ...]) -> bool:
    targets = set(digests)
    return any(
        step["kind"] == "invoke_held_operator" and step["operator_digest"] in targets
        for step in language.validate_operator(operator)["steps"]
    )


def _validated_measurements(raw_records, *, what: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in raw_records:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("operator"), Mapping):
            raise RecursiveTransformationLanguageError(
                "%s carries no operator identity" % what
            )
        record = dict(raw)
        record["operator"] = language.validate_operator(record["operator"])
        records.append(record)
    digests = [item["operator"]["operator_digest"] for item in records]
    if len(set(digests)) != len(digests):
        raise RecursiveTransformationLanguageError("%s measured an operator more than once" % what)
    return records


def _same_round_reach_dependency(
    run: Mapping[str, Any],
    *,
    winner_digest: str,
    invoked_digests: tuple[str, ...],
) -> dict[str, Any]:
    """Prove that removing the invoked predecessor reduces reach in the exact measured round.

    Structural invalidity is useful but weaker than performance evidence: a recursive operator can
    mention an acquired predecessor even when an equally good non-recursive route exists.  The
    ordinary controller measures all held operators before it measures the complete bounded outside
    image.  Under ablation the removed predecessor would cease to be held and become eligible for
    reacquisition, so its already-measured held result must also be included in the counterfactual.

    Therefore the same physical round covers the complete relevant counterfactual without redrawing:
    every non-invoking outside candidate plus the exact invoked predecessor operator(s) measured in
    the held-language phase.  The recursive winner must have strictly greater accepted reach than all
    of them under the same objective snapshot and admitted budget.
    """
    raw_image = list(run.get("candidate_image") or [])
    candidate_measurements = _validated_measurements(
        list(run.get("candidate_measurements") or []),
        what="recursive candidate round",
    )
    held_measurements = _validated_measurements(
        list(run.get("held_measurements") or []),
        what="recursive held-language round",
    )
    if not raw_image or not candidate_measurements or not held_measurements:
        raise RecursiveTransformationLanguageError(
            "recursive selection carries no complete held/candidate measurements"
        )

    image_digests = [
        language.validate_operator(item)["operator_digest"]
        for item in raw_image
    ]
    if len(set(image_digests)) != len(image_digests):
        raise RecursiveTransformationLanguageError(
            "recursive candidate image contains duplicate operator identities"
        )
    measured_digests = [item["operator"]["operator_digest"] for item in candidate_measurements]
    if set(measured_digests) != set(image_digests):
        raise RecursiveTransformationLanguageError(
            "recursive candidate measurements do not cover the complete admitted image"
        )

    winner_records = [
        item for item in candidate_measurements
        if item["operator"]["operator_digest"] == str(winner_digest)
    ]
    if len(winner_records) != 1 or not winner_records[0].get("accepted"):
        raise RecursiveTransformationLanguageError(
            "recursive winner is not a unique accepted member of its measured candidate round"
        )
    winner_score = int(winner_records[0].get("selection_score", -1))

    noninvoking_candidates = [
        item
        for item in candidate_measurements
        if not _operator_invokes_any(item["operator"], invoked_digests)
    ]
    predecessor_reacquisition = [
        item
        for item in held_measurements
        if item["operator"]["operator_digest"] in set(invoked_digests)
    ]
    reacquisition_digests = {
        item["operator"]["operator_digest"] for item in predecessor_reacquisition
    }
    if reacquisition_digests != set(invoked_digests) or len(predecessor_reacquisition) != len(
        invoked_digests
    ):
        raise RecursiveTransformationLanguageError(
            "same-round evidence does not contain exactly one held measurement for each ablated predecessor"
        )

    counterfactual_without_predecessor = [
        *noninvoking_candidates,
        *predecessor_reacquisition,
    ]
    if not counterfactual_without_predecessor:
        raise RecursiveTransformationLanguageError(
            "recursive round has no measured counterfactual independent of the invoked predecessor"
        )
    best_without = max(
        int(item.get("selection_score", -1))
        for item in counterfactual_without_predecessor
    )
    if winner_score <= best_without:
        raise RecursiveTransformationLanguageError(
            "recursive winner does not have strictly greater measured reach than the complete "
            "counterfactual without the invoked predecessor"
        )

    payload = {
        "established": True,
        "kind": "same_round_measured_reach_dependency",
        "complete_candidate_image_measured": True,
        "complete_counterfactual_without_predecessor_image_measured": True,
        "candidate_count": len(candidate_measurements),
        "noninvoking_candidate_count": len(noninvoking_candidates),
        "predecessor_reacquisition_measurement_count": len(predecessor_reacquisition),
        "independent_candidate_count": len(counterfactual_without_predecessor),
        "accepted_independent_candidate_count": sum(
            1 for item in counterfactual_without_predecessor if item.get("accepted")
        ),
        "winner_operator_digest": str(winner_digest),
        "winner_selection_score": winner_score,
        "best_selection_score_without_invoked_predecessor": best_without,
        "strict_reach_loss_without_predecessor": True,
        "invoked_predecessor_operator_digests": list(invoked_digests),
        "predecessor_reacquisition_measurement_digests": sorted(
            str(item.get("measurement_digest") or "") for item in predecessor_reacquisition
        ),
        "independent_measurement_digests": sorted(
            str(item.get("measurement_digest") or "")
            for item in counterfactual_without_predecessor
        ),
    }
    return {**payload, "evidence_digest": digest_of(payload)}


def run_recursive_extension_search(
    genesis,
    here,
    *,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Search a second-generation language extension from primitives derived from lineage history."""
    held_before = controller.bound_language(genesis)
    if held_before is None:
        raise RecursiveTransformationLanguageError("lineage has no transformation language")
    prior_acquired = acquired_operator_digests(genesis, held_before)
    if not prior_acquired:
        raise RecursiveTransformationLanguageError(
            "recursive language search requires at least one prior endogenous language acquisition"
        )

    admitted_steps = derived_recursive_steps(genesis)
    invocation_steps = [
        step for step in admitted_steps if step["kind"] == "invoke_held_operator"
    ]
    if not invocation_steps:
        raise RecursiveTransformationLanguageError(
            "lineage history produced no acquired-operator invocation primitive"
        )

    run = controller.run_extension_search(
        genesis,
        here,
        admitted_steps=admitted_steps,
        checkpoint_directory=checkpoint_directory,
    )
    if not run.get("language_changed"):
        result = {
            "schema": RECURSION_SCHEMA,
            "recursive_extension": False,
            "reason": str(run.get("status") or "no language extension selected"),
            "held_language_digest": held_before["language_digest"],
            "prior_acquired_operator_digests": list(prior_acquired),
            "derived_step_digests": [step["step_digest"] for step in admitted_steps],
            "extension_run": run,
        }
        result["recursion_digest"] = digest_of(result)
        return result

    certificate = run.get("certificate") or {}
    winner = certificate.get("operator") or {}
    invoked = _invoked_acquired_digests(genesis, held_before, winner)
    if not invoked:
        raise RecursiveTransformationLanguageError(
            "selected language extension does not invoke any previously acquired operator; "
            "it is another first-generation extension, not recursive self-extension"
        )
    descendant = controller.bound_language(genesis)
    if descendant is None:
        raise RecursiveTransformationLanguageError("recursive extension disappeared after adoption")
    ablation_established, ablation_reason = _ablation_refuses_descendant(
        descendant,
        removed_digests=invoked,
    )
    if not ablation_established:
        raise RecursiveTransformationLanguageError(ablation_reason)

    winner_digest = str(winner.get("operator_digest") or "")
    measured_reach = _same_round_reach_dependency(
        run,
        winner_digest=winner_digest,
        invoked_digests=invoked,
    )

    source_certificates = [
        certificate
        for certificate in _extension_certificates(genesis)
        if isinstance(certificate.get("operator"), Mapping)
        and certificate["operator"].get("operator_digest") in set(invoked)
    ]
    if len(source_certificates) != len(invoked):
        raise RecursiveTransformationLanguageError(
            "recursive invocation is not backed by one validated extension certificate per predecessor"
        )
    payload = {
        "schema": RECURSION_SCHEMA,
        "recursive_extension": True,
        "prior_language_digest": held_before["language_digest"],
        "descendant_language_digest": descendant["language_digest"],
        "selected_operator_digest": winner_digest,
        "invoked_acquired_operator_digests": list(invoked),
        "source_extension_certificate_digests": sorted(
            str(item.get("certificate_digest") or "") for item in source_certificates
        ),
        "derived_step_digests": [step["step_digest"] for step in admitted_steps],
        "caller_supplied_recursive_operator": False,
        "lineage_history_derived_invocation": True,
        "journal_backed_predecessor_acquisitions": True,
        "dependency_ablation": {
            "established": True,
            "kind": "structural_and_measured_reach_dependency",
            "removed_operator_digests": list(invoked),
            "descendant_reconstructs_without_predecessor": False,
            "refusal": ablation_reason,
            "same_round_reach": measured_reach,
        },
        "extension_certificate_digest": str(certificate.get("certificate_digest") or ""),
        "trust_root_source_sha256": genesis.admitted_source_sha256,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
    }
    record = {**payload, "recursion_digest": digest_of(payload)}
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [record],
        generation=genesis.state["generation"],
    )
    entry = genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "recursive_transformation_language_extension",
            "record": record,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    checkpoint = ""
    if checkpoint_directory is not None:
        checkpoint = genesis.persist(Path(checkpoint_directory))["checkpoint"]

    result = {
        **record,
        "extension_run": run,
        "journal_entry": entry["entry_digest"],
        "checkpoint_digest": checkpoint,
    }
    return result
