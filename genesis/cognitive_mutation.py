"""DEVELOPMENT-only bounded mutations for cognitive architecture genomes.

Mutation policy is intentionally external: this module applies one explicit proposal and validates
the resulting genome. It does not score, select, search, or inspect frozen evaluators. Mutation
records are content-addressed so later lineage-held search can prove parent -> descendant provenance.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Collection, Mapping

from .cognitive_architecture import architecture_digest, canonical_architecture


class CognitiveMutationError(ValueError):
    """Raised when a mutation proposal is malformed or outside admitted bounds."""


@dataclass(frozen=True)
class MutationBounds:
    max_nodes: int
    max_edges: int

    def __post_init__(self) -> None:
        if self.max_nodes < 1 or self.max_edges < 0:
            raise CognitiveMutationError("mutation bounds must be non-negative and admit one node")


@dataclass(frozen=True)
class MutationRecord:
    parent_digest: str
    child_digest: str
    proposal_digest: str
    proposal: dict[str, Any]

    @property
    def record_digest(self) -> str:
        return _digest(
            {
                "parent_digest": self.parent_digest,
                "child_digest": self.child_digest,
                "proposal_digest": self.proposal_digest,
            }
        )


def _canonical_value(value: Any) -> Any:
    try:
        return json.loads(
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        )
    except (TypeError, ValueError) as exc:
        raise CognitiveMutationError("mutation proposal must be canonical JSON data") from exc


def _digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def apply_mutation(
    architecture: Any,
    proposal: Mapping[str, Any],
    *,
    admitted_primitives: Collection[str],
    bounds: MutationBounds,
) -> dict[str, Any]:
    """Apply exactly one externally chosen structural mutation, then fail closed on validation."""
    child, _ = apply_mutation_record(
        architecture,
        proposal,
        admitted_primitives=admitted_primitives,
        bounds=bounds,
    )
    return child


def apply_mutation_record(
    architecture: Any,
    proposal: Mapping[str, Any],
    *,
    admitted_primitives: Collection[str],
    bounds: MutationBounds,
) -> tuple[dict[str, Any], MutationRecord]:
    """Apply one mutation and return its immutable parent/proposal/child identity record."""
    admitted = {str(name) for name in admitted_primitives}
    admitted_with_source = admitted | {"source"}
    current = canonical_architecture(
        architecture,
        admitted_primitives=admitted_with_source,
        max_nodes=bounds.max_nodes,
        max_edges=bounds.max_edges,
    )
    if not isinstance(proposal, Mapping):
        raise CognitiveMutationError("mutation proposal must be a mapping")
    canonical_proposal = _canonical_value(dict(proposal))
    kind = canonical_proposal.get("kind")
    result = deepcopy(current)

    if kind == "replace_primitive":
        _require_keys(canonical_proposal, {"kind", "node", "primitive"})
        node = _mutable_node(result, str(canonical_proposal["node"]))
        if node["id"] in result["inputs"]:
            raise CognitiveMutationError("input source primitives are immutable")
        primitive = str(canonical_proposal["primitive"])
        if primitive not in admitted:
            raise CognitiveMutationError("replacement primitive is not admitted")
        node["primitive"] = primitive
    elif kind == "replace_config":
        _require_keys(canonical_proposal, {"kind", "node", "config"})
        node = _mutable_node(result, str(canonical_proposal["node"]))
        if node["id"] in result["inputs"]:
            raise CognitiveMutationError("input source configuration is immutable")
        node["config"] = deepcopy(canonical_proposal["config"])
    elif kind == "add_node":
        _require_keys(canonical_proposal, {"kind", "node"})
        raw = canonical_proposal["node"]
        if not isinstance(raw, Mapping) or set(raw) - {"id", "primitive", "config"}:
            raise CognitiveMutationError("added node must declare only id, primitive and optional config")
        if "id" not in raw or "primitive" not in raw:
            raise CognitiveMutationError("added node is incomplete")
        if str(raw["primitive"]) == "source":
            raise CognitiveMutationError("mutation cannot create a new external source")
        if str(raw["primitive"]) not in admitted:
            raise CognitiveMutationError("added node primitive is not admitted")
        result["nodes"].append(
            {"id": str(raw["id"]), "primitive": str(raw["primitive"]), "config": deepcopy(raw.get("config", {}))}
        )
    elif kind == "remove_node":
        _require_keys(canonical_proposal, {"kind", "node"})
        node_id = str(canonical_proposal["node"])
        _mutable_node(result, node_id)
        if node_id in result["inputs"] or node_id in result["outputs"]:
            raise CognitiveMutationError("input/output nodes cannot be removed")
        result["nodes"] = [node for node in result["nodes"] if node["id"] != node_id]
        result["edges"] = [
            edge for edge in result["edges"]
            if edge["source"] != node_id and edge["target"] != node_id
        ]
    elif kind in {"add_edge", "remove_edge"}:
        _require_keys(canonical_proposal, {"kind", "source", "target", "edge_kind"})
        edge = {
            "source": str(canonical_proposal["source"]),
            "target": str(canonical_proposal["target"]),
            "kind": str(canonical_proposal["edge_kind"]),
        }
        if kind == "add_edge":
            result["edges"].append(edge)
        else:
            try:
                result["edges"].remove(edge)
            except ValueError as exc:
                raise CognitiveMutationError("cannot remove an absent edge") from exc
    else:
        raise CognitiveMutationError("unknown mutation kind")

    try:
        child = canonical_architecture(
            result,
            admitted_primitives=admitted_with_source,
            max_nodes=bounds.max_nodes,
            max_edges=bounds.max_edges,
        )
    except ValueError as exc:
        raise CognitiveMutationError("mutation does not produce an admitted architecture") from exc

    record = MutationRecord(
        parent_digest=architecture_digest(current),
        child_digest=architecture_digest(child),
        proposal_digest=_digest(canonical_proposal),
        proposal=canonical_proposal,
    )
    return child, record


def _require_keys(proposal: Mapping[str, Any], expected: set[str]) -> None:
    if set(proposal) != expected:
        raise CognitiveMutationError("mutation proposal fields do not match its kind")


def _mutable_node(architecture: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in architecture["nodes"]:
        if node["id"] == node_id:
            return node
    raise CognitiveMutationError("mutation refers to an unknown node")
