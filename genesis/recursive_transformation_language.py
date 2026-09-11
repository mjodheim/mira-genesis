"""Second-generation transformation-language extension for Genesis v2 DEVELOPMENT work.

Genesis v2's first extension search composes host-admitted primitive micro-steps. That is not enough
for recursive self-extension: a later language descendant must be able to *use an earlier acquired
operator as part of the language from which it constructs the next operator*.

This module derives that recursive lower language from lineage history rather than asking the caller
which acquired operator to reuse. Every non-invocation primitive already present in the held language
is retained, and every evidence-backed acquired operator currently held becomes one
``invoke_held_operator`` micro-step identified by its content digest. The ordinary transformation-
language controller then measures the full bounded candidate image under the unchanged trust root.

A successful recursive result is accepted here only if the winning operator actually invokes at
least one previously acquired operator. The module records the dependency and mechanically verifies
that removing the invoked predecessor makes the descendant language fail reconstruction. This is a
bounded DEVELOPMENT recursion mechanism; the fixed primitive kernel, finite operator length and
selection rule remain apparatus.
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


def _extension_certificates(genesis) -> tuple[dict[str, Any], ...]:
    values: list[dict[str, Any]] = []
    for item in genesis.state.get("observations", []):
        if not isinstance(item, Mapping) or item.get("kind") != "transformation_language_extension":
            continue
        certificate = item.get("certificate")
        if isinstance(certificate, Mapping):
            values.append(dict(certificate))
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

    source_certificates = [
        certificate
        for certificate in _extension_certificates(genesis)
        if isinstance(certificate.get("operator"), Mapping)
        and certificate["operator"].get("operator_digest") in set(invoked)
    ]
    payload = {
        "schema": RECURSION_SCHEMA,
        "recursive_extension": True,
        "prior_language_digest": held_before["language_digest"],
        "descendant_language_digest": descendant["language_digest"],
        "selected_operator_digest": winner.get("operator_digest", ""),
        "invoked_acquired_operator_digests": list(invoked),
        "source_extension_certificate_digests": sorted(
            str(item.get("certificate_digest") or "") for item in source_certificates
        ),
        "derived_step_digests": [step["step_digest"] for step in admitted_steps],
        "caller_supplied_recursive_operator": False,
        "lineage_history_derived_invocation": True,
        "dependency_ablation": {
            "established": True,
            "kind": "language_reconstruction_dependency",
            "removed_operator_digests": list(invoked),
            "descendant_reconstructs_without_predecessor": False,
            "refusal": ablation_reason,
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
