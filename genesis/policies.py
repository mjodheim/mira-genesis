"""Lineage-held bounded search policies represented as canonical data.

The first generated-body work still used a host-authored Python function to decide which program to
try next. This module moves that *search machinery* into a content-addressed value. A fixed policy
interpreter is apparatus; the mutable policy is data held by the lineage.

A policy names an admitted primitive-operation registry, an ordered operation alphabet, a maximum
program length and a fixed ceiling on how far that length may ever be expanded in this bounded
DEVELOPMENT setting. ``step`` reads only inert lineage evidence and returns one declarative
``GenerateTransform``-shaped record or a stop record. It does not run candidates and cannot grade
anything.

``expand`` is the one licensed edit: increase the search depth by exactly one while every other
field stays fixed. Whether that edit may be adopted is *not* decided here; ``policy_controller``
requires an exhaustion certificate and a trust-root-judged gain before it installs the descendant.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Iterable, Mapping, Sequence

from genesis.probe import resolve_registry
from genesis.trust_root import digest_of

POLICY_SCHEMA = "genesis-generated-search-policy-v1"
POLICY_KIND = "bounded_program_search"


class PolicyError(RuntimeError):
    """Raised when a search policy is malformed or asks beyond its admitted bound."""


def _payload(
    *,
    registry_reference: str,
    operation_names: Sequence[str],
    max_length: int,
    ceiling_length: int,
    max_candidates: int,
    input_field: str,
    parent_policy_digest: str,
) -> dict[str, Any]:
    names = [str(name) for name in operation_names]
    if not registry_reference:
        raise PolicyError("search policy names no operation registry")
    if not names or len(set(names)) != len(names):
        raise PolicyError("search policy needs a non-empty unique operation alphabet")
    registry = resolve_registry(registry_reference)
    missing = [name for name in names if name not in registry]
    if missing:
        raise PolicyError(
            "search policy names operations outside the admitted registry: %s"
            % ", ".join(sorted(missing))
        )
    if int(max_length) <= 0:
        raise PolicyError("search policy max_length must be positive")
    if int(ceiling_length) < int(max_length):
        raise PolicyError("search policy ceiling is below its current depth")
    if int(max_candidates) <= 0:
        raise PolicyError("search policy max_candidates must be positive")
    if not input_field:
        raise PolicyError("search policy names no input field")
    return {
        "schema": POLICY_SCHEMA,
        "kind": POLICY_KIND,
        "registry_reference": str(registry_reference),
        "operation_names": names,
        "max_length": int(max_length),
        "ceiling_length": int(ceiling_length),
        "max_candidates": int(max_candidates),
        "input_field": str(input_field),
        "parent_policy_digest": str(parent_policy_digest),
    }


def create(
    *,
    registry_reference: str,
    operation_names: Sequence[str],
    max_length: int = 1,
    ceiling_length: int = 2,
    max_candidates: int = 64,
    input_field: str = "input",
    parent_policy_digest: str = "",
) -> dict[str, Any]:
    """Create one canonical policy artifact."""
    payload = _payload(
        registry_reference=registry_reference,
        operation_names=operation_names,
        max_length=max_length,
        ceiling_length=ceiling_length,
        max_candidates=max_candidates,
        input_field=input_field,
        parent_policy_digest=parent_policy_digest,
    )
    return {**payload, "policy_digest": digest_of(payload)}


def validate(record: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild a policy from its parts and require the digest to reproduce."""
    if not isinstance(record, Mapping):
        raise PolicyError("search policy is not a record")
    if record.get("schema") != POLICY_SCHEMA or record.get("kind") != POLICY_KIND:
        raise PolicyError("search policy uses an unrecognised schema or kind")
    rebuilt = create(
        registry_reference=str(record.get("registry_reference") or ""),
        operation_names=list(record.get("operation_names") or []),
        max_length=int(record.get("max_length", 0)),
        ceiling_length=int(record.get("ceiling_length", 0)),
        max_candidates=int(record.get("max_candidates", 0)),
        input_field=str(record.get("input_field") or ""),
        parent_policy_digest=str(record.get("parent_policy_digest") or ""),
    )
    if rebuilt != dict(record):
        raise PolicyError("search policy does not reconstruct from its own fields")
    return rebuilt


def candidate_sequences(record: Mapping[str, Any]) -> tuple[tuple[str, ...], ...]:
    """The bounded program sequence this policy can propose, in deterministic order."""
    policy = validate(record)
    names = tuple(policy["operation_names"])
    candidates: list[tuple[str, ...]] = []
    for length in range(1, policy["max_length"] + 1):
        for sequence in product(names, repeat=length):
            if len(candidates) >= policy["max_candidates"]:
                return tuple(candidates)
            candidates.append(tuple(sequence))
    return tuple(candidates)


def candidate_name(operations: Sequence[str]) -> str:
    """A name stable across policy descendants so an expanded policy does not retry old evidence."""
    return "policy-program:" + "+".join(str(name) for name in operations)


def _evidence_names(evidence: Iterable[Mapping[str, Any]]) -> tuple[set[str], set[str]]:
    rejected: set[str] = set()
    acquired: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        kind = item.get("kind")
        record = item.get("record") or {}
        if not isinstance(record, Mapping):
            continue
        name = str(record.get("name") or "")
        if not name.startswith("policy-program:"):
            continue
        if kind == "observation" and record.get("kind") == "rejected_candidate":
            rejected.add(name)
        elif kind == "acquisition":
            acquired.add(name)
    return rejected, acquired


def _latest_dependency(context: Mapping[str, Any]) -> str:
    acquisitions = list(context.get("acquisitions") or [])
    return str(acquisitions[-1]) if acquisitions else ""


def step(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Interpret one policy against inert evidence and return one declarative controller intent."""
    policy = validate(payload.get("policy") or {})
    context = payload.get("context") or {}
    evidence = context.get("evidence") or []
    rejected, acquired = _evidence_names(evidence)
    if acquired:
        return {"type": "Stop", "reason": "a policy-generated descendant was adopted"}

    dependency = _latest_dependency(context)
    for operations in candidate_sequences(policy):
        name = candidate_name(operations)
        if name in rejected:
            continue
        return {
            "type": "GenerateTransform",
            "name": name,
            "operations": list(operations),
            "input_field": policy["input_field"],
            "depends_on": dependency,
            "rationale": {
                "search_policy_digest": policy["policy_digest"],
                "search_depth": policy["max_length"],
                "retained_rejections_skipped": len(rejected),
            },
        }
    return {
        "type": "Stop",
        "reason": "policy search exhausted at max_length=%d" % policy["max_length"],
    }


def exhausted(record: Mapping[str, Any], evidence: Iterable[Mapping[str, Any]]) -> bool:
    """Whether every program this policy could propose is already a retained rejection."""
    policy = validate(record)
    rejected, acquired = _evidence_names(evidence)
    if acquired:
        return False
    return all(candidate_name(sequence) in rejected for sequence in candidate_sequences(policy))


def expand(record: Mapping[str, Any]) -> dict[str, Any]:
    """The one structural policy mutation admitted here: current search depth plus one."""
    policy = validate(record)
    if policy["max_length"] >= policy["ceiling_length"]:
        raise PolicyError("search policy is already at its admitted depth ceiling")
    return create(
        registry_reference=policy["registry_reference"],
        operation_names=policy["operation_names"],
        max_length=policy["max_length"] + 1,
        ceiling_length=policy["ceiling_length"],
        max_candidates=policy["max_candidates"],
        input_field=policy["input_field"],
        parent_policy_digest=policy["policy_digest"],
    )
