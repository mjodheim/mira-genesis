"""Canonical DEVELOPMENT representation for evolvable cognitive machinery.

This module deliberately stops before execution, learning, mutation search or scientific selection.
It provides a content-addressed architecture genome that mutable Genesis can later manipulate while
the immutable trust root remains outside that machinery.

The representation is substrate-neutral: primitive semantics are admitted externally rather than
hard-coded here. Feedforward edges describe within-step dependencies and must be acyclic. Recurrent
edges carry state across logical steps and may close loops.

Only exact structural facts are reported. This module does not estimate FLOPs, watts, energy,
latency, parameter count or intelligence from topology.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, deque
from typing import Any, Collection, Mapping

COGNITIVE_ARCHITECTURE_SCHEMA = "genesis-cognitive-architecture-v1"
EDGE_KINDS = ("feedforward", "recurrent")


class CognitiveArchitectureError(ValueError):
    """Raised when an architecture genome is invalid or exceeds admitted bounds."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CognitiveArchitectureError(
            "cognitive architecture contains a non-canonical value"
        ) from exc


def _config(value: Any, *, path: str) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and (
            value != value or value in (float("inf"), float("-inf"))
        ):
            raise CognitiveArchitectureError("%s contains a non-finite float" % path)
        return value
    if isinstance(value, (list, tuple)):
        return [_config(item, path=path + "[]") for item in value]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value, key=str):
            text = str(key)
            if text in result:
                raise CognitiveArchitectureError(
                    "%s collapses distinct keys to %r" % (path, text)
                )
            result[text] = _config(value[key], path=path + "." + text)
        return result
    raise CognitiveArchitectureError(
        "%s contains unsupported type %s" % (path, type(value).__name__)
    )


def _name(value: Any, *, path: str) -> str:
    text = str(value)
    if not text or text != text.strip():
        raise CognitiveArchitectureError("%s must be a non-empty trimmed name" % path)
    return text


def _feedforward_order(node_ids: Collection[str], edges: list[dict[str, str]]) -> list[str]:
    outgoing = {node_id: [] for node_id in node_ids}
    indegree = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        if edge["kind"] != "feedforward":
            continue
        outgoing[edge["source"]].append(edge["target"])
        indegree[edge["target"]] += 1

    ready = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    order: list[str] = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for target in sorted(outgoing[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)

    if len(order) != len(node_ids):
        raise CognitiveArchitectureError(
            "feedforward edges contain a cycle; use recurrent edges for cross-step state"
        )
    return order


def canonical_architecture(
    architecture: Any,
    *,
    admitted_primitives: Collection[str] | None = None,
    max_nodes: int | None = None,
    max_edges: int | None = None,
) -> dict[str, Any]:
    """Validate and return the unique canonical form of one architecture genome."""
    if not isinstance(architecture, Mapping):
        raise CognitiveArchitectureError("architecture must be a mapping")

    allowed = {"schema", "nodes", "edges", "inputs", "outputs"}
    missing = allowed - set(architecture)
    extra = set(architecture) - allowed
    if missing:
        raise CognitiveArchitectureError("architecture is missing %s" % sorted(missing))
    if extra:
        raise CognitiveArchitectureError("architecture has unknown fields %s" % sorted(extra))
    if architecture["schema"] != COGNITIVE_ARCHITECTURE_SCHEMA:
        raise CognitiveArchitectureError("architecture uses an unrecognized schema")

    raw_nodes = architecture["nodes"]
    raw_edges = architecture["edges"]
    raw_inputs = architecture["inputs"]
    raw_outputs = architecture["outputs"]
    if not isinstance(raw_nodes, (list, tuple)) or not raw_nodes:
        raise CognitiveArchitectureError("architecture must contain at least one node")
    if not isinstance(raw_edges, (list, tuple)):
        raise CognitiveArchitectureError("architecture edges must be a sequence")
    if not isinstance(raw_inputs, (list, tuple)) or not raw_inputs:
        raise CognitiveArchitectureError("architecture must declare an input node")
    if not isinstance(raw_outputs, (list, tuple)) or not raw_outputs:
        raise CognitiveArchitectureError("architecture must declare an output node")

    nodes: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_nodes):
        if not isinstance(raw, Mapping):
            raise CognitiveArchitectureError("nodes[%d] must be a mapping" % index)
        if set(raw) - {"id", "primitive", "config"}:
            raise CognitiveArchitectureError("nodes[%d] has unknown fields" % index)
        if "id" not in raw or "primitive" not in raw:
            raise CognitiveArchitectureError("nodes[%d] is incomplete" % index)
        nodes.append(
            {
                "id": _name(raw["id"], path="nodes[%d].id" % index),
                "primitive": _name(
                    raw["primitive"], path="nodes[%d].primitive" % index
                ),
                "config": _config(
                    raw.get("config", {}), path="nodes[%d].config" % index
                ),
            }
        )

    edges: list[dict[str, str]] = []
    for index, raw in enumerate(raw_edges):
        if not isinstance(raw, Mapping):
            raise CognitiveArchitectureError("edges[%d] must be a mapping" % index)
        if set(raw) != {"source", "target", "kind"}:
            raise CognitiveArchitectureError("edges[%d] must declare source, target and kind" % index)
        kind = str(raw["kind"])
        if kind not in EDGE_KINDS:
            raise CognitiveArchitectureError("edges[%d] has an unknown kind" % index)
        edges.append(
            {
                "source": _name(raw["source"], path="edges[%d].source" % index),
                "target": _name(raw["target"], path="edges[%d].target" % index),
                "kind": kind,
            }
        )

    if max_nodes is not None and len(nodes) > int(max_nodes):
        raise CognitiveArchitectureError("architecture exceeds admitted node maximum")
    if max_edges is not None and len(edges) > int(max_edges):
        raise CognitiveArchitectureError("architecture exceeds admitted edge maximum")

    node_ids = [node["id"] for node in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise CognitiveArchitectureError("architecture contains duplicate node identifiers")
    known = set(node_ids)

    if admitted_primitives is not None:
        admitted = {str(name) for name in admitted_primitives}
        unknown = sorted({node["primitive"] for node in nodes} - admitted)
        if unknown:
            raise CognitiveArchitectureError(
                "architecture uses primitives outside the admitted registry: %s" % unknown
            )

    seen_edges: set[tuple[str, str, str]] = set()
    for edge in edges:
        if edge["source"] not in known or edge["target"] not in known:
            raise CognitiveArchitectureError(
                "edge %s -> %s refers to a missing node"
                % (edge["source"], edge["target"])
            )
        key = (edge["source"], edge["target"], edge["kind"])
        if key in seen_edges:
            raise CognitiveArchitectureError("architecture contains duplicate edge %r" % (key,))
        seen_edges.add(key)

    inputs = [_name(value, path="inputs[]") for value in raw_inputs]
    outputs = [_name(value, path="outputs[]") for value in raw_outputs]
    if len(set(inputs)) != len(inputs) or len(set(outputs)) != len(outputs):
        raise CognitiveArchitectureError("architecture contains duplicate input/output identifiers")
    missing_io = sorted((set(inputs) | set(outputs)) - known)
    if missing_io:
        raise CognitiveArchitectureError(
            "architecture input/output refers to missing nodes: %s" % missing_io
        )

    _feedforward_order(known, edges)
    return {
        "schema": COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": sorted(nodes, key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: (edge["kind"], edge["source"], edge["target"])),
        "inputs": sorted(inputs),
        "outputs": sorted(outputs),
    }


def architecture_digest(architecture: Any, **validation: Any) -> str:
    """Return the SHA-256 identity of the complete validated genome."""
    canonical = canonical_architecture(architecture, **validation)
    return hashlib.sha256(_canonical_bytes(canonical)).hexdigest()


def structural_profile(architecture: Any, **validation: Any) -> dict[str, Any]:
    """Return exact topology facts without inventing compute or energy measurements."""
    canonical = canonical_architecture(architecture, **validation)
    nodes = canonical["nodes"]
    edges = canonical["edges"]
    feedforward = [edge for edge in edges if edge["kind"] == "feedforward"]
    recurrent = [edge for edge in edges if edge["kind"] == "recurrent"]

    order = _feedforward_order({node["id"] for node in nodes}, edges)
    incoming: dict[str, list[str]] = {node["id"]: [] for node in nodes}
    for edge in feedforward:
        incoming[edge["target"]].append(edge["source"])
    depth: dict[str, int] = {}
    for node_id in order:
        parents = incoming[node_id]
        depth[node_id] = 0 if not parents else 1 + max(depth[parent] for parent in parents)

    counts = Counter(node["primitive"] for node in nodes)
    return {
        "architecture_digest": hashlib.sha256(_canonical_bytes(canonical)).hexdigest(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "feedforward_edge_count": len(feedforward),
        "recurrent_edge_count": len(recurrent),
        "max_feedforward_depth": max(depth.values(), default=0),
        "primitive_counts": dict(sorted(counts.items())),
        "compute_estimate": None,
        "energy_estimate": None,
        "measurement_note": (
            "topology only; compute and energy require execution-side measurement"
        ),
    }
