"""Bounded mutations of lineage-held search policies, represented as canonical data.

The first machinery-evolution path had one hard-coded edit: ``max_length += 1``. That is enough to
show that a policy value can change, but not that the lineage can search over *how* its policy should
change. This module separates the immutable mutation interpreter from mutation data.

A mutation may currently:

* add one already-admitted primitive operation to the policy alphabet;
* increase search depth by one within the policy's prospective ceiling; or
* increase the candidate cap by a bounded positive amount.

None of those edits changes the evaluator, trust root, task identity, isolation or budget. They only
change what executable candidates the search policy can construct. The resulting policy names its
parent digest, so every accepted machinery descendant has an explicit lineage edge.

This remains a deliberately small DEVELOPMENT language. Adding a mutation kind is a host apparatus
change and creates no scientific result by itself.
"""
from __future__ import annotations

from typing import Any, Mapping

from genesis import policies
from genesis.probe import resolve_registry
from genesis.trust_root import digest_of

MUTATION_SCHEMA = "genesis-search-policy-mutation-v1"
MUTATION_KINDS = ("add_operation", "increase_depth", "increase_candidate_limit")


class PolicyMutationError(RuntimeError):
    """Raised when mutation data is malformed or asks outside the admitted policy boundary."""


def create(
    kind: str,
    *,
    operation: str = "",
    amount: int = 1,
) -> dict[str, Any]:
    kind = str(kind)
    if kind not in MUTATION_KINDS:
        raise PolicyMutationError("unrecognised policy mutation kind %r" % kind)
    operation = str(operation)
    amount = int(amount)
    if kind == "add_operation":
        if not operation:
            raise PolicyMutationError("add_operation mutation names no operation")
        if amount != 1:
            raise PolicyMutationError("add_operation does not use a numeric amount")
    else:
        if operation:
            raise PolicyMutationError("%s mutation may not carry an operation name" % kind)
        if amount <= 0:
            raise PolicyMutationError("policy mutation amount must be positive")
        if kind == "increase_depth" and amount != 1:
            raise PolicyMutationError("depth may increase by exactly one per evidence-backed update")
    payload = {
        "schema": MUTATION_SCHEMA,
        "kind": kind,
        "operation": operation,
        "amount": amount,
    }
    return {**payload, "mutation_digest": digest_of(payload)}


def validate(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != MUTATION_SCHEMA:
        raise PolicyMutationError("policy mutation uses an unrecognised schema")
    rebuilt = create(
        str(record.get("kind") or ""),
        operation=str(record.get("operation") or ""),
        amount=int(record.get("amount", 1)),
    )
    if rebuilt != dict(record):
        raise PolicyMutationError("policy mutation does not reconstruct from its own fields")
    return rebuilt


def apply(policy: Mapping[str, Any], mutation: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one bounded structural edit to a policy and return a content-addressed descendant."""
    prior = policies.validate(policy)
    edit = validate(mutation)
    operation_names = list(prior["operation_names"])
    max_length = int(prior["max_length"])
    max_candidates = int(prior["max_candidates"])

    if edit["kind"] == "add_operation":
        operation = edit["operation"]
        registry = resolve_registry(prior["registry_reference"])
        if operation not in registry:
            raise PolicyMutationError(
                "mutation asks to add operation %r outside the policy's admitted registry" % operation
            )
        if operation in operation_names:
            raise PolicyMutationError("mutation adds an operation the policy already holds")
        operation_names.append(operation)
    elif edit["kind"] == "increase_depth":
        if max_length >= int(prior["ceiling_length"]):
            raise PolicyMutationError("mutation asks beyond the policy's admitted depth ceiling")
        max_length += 1
    elif edit["kind"] == "increase_candidate_limit":
        # A candidate-limit edit cannot create an unbounded search in one step. The current cap is
        # its local scale; one mutation may at most double it.
        amount = int(edit["amount"])
        if amount > max_candidates:
            raise PolicyMutationError("candidate-limit mutation may not grow the cap by more than 2x")
        max_candidates += amount
    else:  # pragma: no cover - validate() closes this path
        raise PolicyMutationError("unsupported policy mutation")

    return policies.create(
        registry_reference=prior["registry_reference"],
        operation_names=operation_names,
        max_length=max_length,
        ceiling_length=prior["ceiling_length"],
        max_candidates=max_candidates,
        input_field=prior["input_field"],
        parent_policy_digest=prior["policy_digest"],
    )


def structural_difference(prior: Mapping[str, Any], descendant: Mapping[str, Any]) -> list[str]:
    """Fields that changed between a policy and one claimed descendant, excluding lineage identity."""
    before = policies.validate(prior)
    after = policies.validate(descendant)
    ignored = {"policy_digest", "parent_policy_digest"}
    return sorted(
        key
        for key in set(before) | set(after)
        if key not in ignored and before.get(key) != after.get(key)
    )
