"""DEVELOPMENT-only bounded mutations for cognitive architecture genomes.

Mutation policy is intentionally external: this module applies one explicit proposal and validates
the resulting genome.  It does not score, select, search, or inspect frozen evaluators.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Collection, Mapping

from .cognitive_architecture import canonical_architecture


class CognitiveMutationError(ValueError):
    """Raised when a mutation proposal is malformed or outside admitted bounds."""


@dataclass(frozen=True)
class MutationBounds:
    max_nodes: int
    max_edges: int

    def __post_init__(self) -> None:
        if self.max_nodes < 1 or self.max_edges < 0:
            raise CognitiveMutationError("mutation bounds must be non-negative and admit one node")


def apply_mutation(
    architecture: Any,
    proposal: Mapping[str, Any],
    *,
    admitted_primitives: Collection[str],
    bounds: MutationBounds,
) -> dict[str, Any]:
    """Apply exactly one externally chosen structural mutation, then fail closed on validation."""
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
    kind = proposal.get("kind")
    result = deepcopy(current)

    if kind == "replace_primitive":
        _require_keys(proposal, {"kind", "node", "primitive"})
        node = _mutable_node(result, str(proposal["node"]))
        if node["id"] in result["inputs"]:
            raise CognitiveMutationError("input source primitives are immutable")
        primitive = str(proposal["primitive"])
        if primitive not in admitted:
            raise CognitiveMutationError("replacement primitive is not admitted")
        node["primitive"] = primitive
    elif kind == "replace_config":
        _require_keys(proposal, {"kind", "node", "config"})
        node = _mutable_node(result, str(proposal["node"]))
        if node["id"] in result["inputs"]:
            raise CognitiveMutationError("input source configuration is immutable")
        node["config"] = deepcopy(proposal["config"])
    elif kind in {"add_edge", "remove_edge"}:
        _require_keys(proposal, {"kind", "source", "target", "edge_kind"})
        edge = {
            "source": str(proposal["source"]),
            "target": str(proposal["target"]),
            "kind": str(proposal["edge_kind"]),
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
        return canonical_architecture(
            result,
            admitted_primitives=admitted_with_source,
            max_nodes=bounds.max_nodes,
            max_edges=bounds.max_edges,
        )
    except ValueError as exc:
        raise CognitiveMutationError("mutation does not produce an admitted architecture") from exc


def _require_keys(proposal: Mapping[str, Any], expected: set[str]) -> None:
    if set(proposal) != expected:
        raise CognitiveMutationError("mutation proposal fields do not match its kind")


def _mutable_node(architecture: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in architecture["nodes"]:
        if node["id"] == node_id:
            return node
    raise CognitiveMutationError("mutation refers to an unknown node")
