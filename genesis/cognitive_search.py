"""DEVELOPMENT lineage-held search policy for cognitive architecture descendants.

The policy is canonical data. A fixed interpreter turns it into bounded mutation proposals against one
parent architecture. It has no evaluator access, cannot change external mutation/candidate ceilings,
and cannot declare a descendant better. Candidate records bind policy, parent, proposal and child
identities so later external evaluation can retain exact provenance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Collection, Iterable, Mapping, Sequence

from .cognitive_architecture import architecture_digest, canonical_architecture
from .cognitive_mutation import (
    CognitiveMutationError,
    MutationBounds,
    MutationRecord,
    apply_mutation_record,
)

SEARCH_POLICY_SCHEMA = "genesis-cognitive-architecture-search-policy-v1"
SEARCH_POLICY_KIND = "bounded_architecture_search"
CANDIDATE_SCHEMA = "genesis-cognitive-architecture-candidate-v1"
SUPPORTED_MUTATIONS = (
    "replace_primitive",
    "add_edge",
    "remove_edge",
    "add_node",
    "remove_node",
)


class CognitiveSearchError(RuntimeError):
    """Raised when cognitive search machinery asks outside its admitted boundary."""


@dataclass(frozen=True)
class SearchBounds:
    max_candidates: int
    max_nodes: int
    max_edges: int

    def __post_init__(self) -> None:
        if self.max_candidates < 1:
            raise CognitiveSearchError("search must admit at least one candidate")
        if self.max_nodes < 1 or self.max_edges < 0:
            raise CognitiveSearchError("search architecture bounds are invalid")

    @property
    def mutation_bounds(self) -> MutationBounds:
        return MutationBounds(max_nodes=self.max_nodes, max_edges=self.max_edges)


@dataclass(frozen=True)
class ArchitectureCandidate:
    policy_digest: str
    parent_architecture_digest: str
    child_architecture: dict[str, Any]
    mutation: MutationRecord

    @property
    def candidate_digest(self) -> str:
        return _digest(
            {
                "schema": CANDIDATE_SCHEMA,
                "policy_digest": self.policy_digest,
                "parent_architecture_digest": self.parent_architecture_digest,
                "child_architecture_digest": self.mutation.child_digest,
                "mutation_record_digest": self.mutation.record_digest,
            }
        )

    def record(self) -> dict[str, Any]:
        return {
            "schema": CANDIDATE_SCHEMA,
            "candidate_digest": self.candidate_digest,
            "policy_digest": self.policy_digest,
            "parent_architecture_digest": self.parent_architecture_digest,
            "child_architecture_digest": self.mutation.child_digest,
            "mutation_record_digest": self.mutation.record_digest,
            "proposal_digest": self.mutation.proposal_digest,
            "proposal": dict(self.mutation.proposal),
            "child_architecture": self.child_architecture,
        }


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CognitiveSearchError("search policy contains non-canonical data") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _name(value: Any, *, what: str) -> str:
    text = str(value)
    if not text or text != text.strip():
        raise CognitiveSearchError("%s must be a non-empty trimmed name" % what)
    return text


def create_policy(
    *,
    mutation_kinds: Sequence[str],
    primitive_order: Sequence[str],
    candidate_limit: int = 32,
    parent_policy_digest: str = "",
) -> dict[str, Any]:
    """Create one canonical lineage-held architecture-search policy."""
    kinds = [_name(value, what="mutation kind") for value in mutation_kinds]
    if not kinds or len(set(kinds)) != len(kinds):
        raise CognitiveSearchError("search policy needs a non-empty unique mutation order")
    unknown = [kind for kind in kinds if kind not in SUPPORTED_MUTATIONS]
    if unknown:
        raise CognitiveSearchError("search policy names unsupported mutations: %s" % sorted(unknown))

    primitives = [_name(value, what="primitive") for value in primitive_order]
    if not primitives or len(set(primitives)) != len(primitives):
        raise CognitiveSearchError("search policy needs a non-empty unique primitive order")
    if "source" in primitives:
        raise CognitiveSearchError("search policy cannot treat external source as a mutable primitive")
    if int(candidate_limit) <= 0:
        raise CognitiveSearchError("search policy candidate_limit must be positive")

    payload = {
        "schema": SEARCH_POLICY_SCHEMA,
        "kind": SEARCH_POLICY_KIND,
        "mutation_kinds": kinds,
        "primitive_order": primitives,
        "candidate_limit": int(candidate_limit),
        "parent_policy_digest": str(parent_policy_digest),
    }
    return {**payload, "policy_digest": _digest(payload)}


def validate_policy(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct a search policy and require its content identity to reproduce."""
    if not isinstance(record, Mapping):
        raise CognitiveSearchError("search policy is not a record")
    if record.get("schema") != SEARCH_POLICY_SCHEMA or record.get("kind") != SEARCH_POLICY_KIND:
        raise CognitiveSearchError("search policy uses an unrecognised schema or kind")
    rebuilt = create_policy(
        mutation_kinds=list(record.get("mutation_kinds") or []),
        primitive_order=list(record.get("primitive_order") or []),
        candidate_limit=int(record.get("candidate_limit", 0)),
        parent_policy_digest=str(record.get("parent_policy_digest") or ""),
    )
    if rebuilt != dict(record):
        raise CognitiveSearchError("search policy does not reconstruct from its own fields")
    return rebuilt


def _next_generated_node_id(node_ids: Collection[str]) -> str:
    occupied = set(node_ids)
    index = 0
    while True:
        candidate = "cognitive_candidate_%d" % index
        if candidate not in occupied:
            return candidate
        index += 1


def _proposal_stream(
    architecture: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Iterable[dict[str, Any]]:
    node_ids = [node["id"] for node in architecture["nodes"]]
    inputs = set(architecture["inputs"])
    outputs = set(architecture["outputs"])
    node_by_id = {node["id"]: node for node in architecture["nodes"]}
    edge_keys = {
        (edge["source"], edge["target"], edge["kind"])
        for edge in architecture["edges"]
    }

    for kind in policy["mutation_kinds"]:
        if kind == "replace_primitive":
            for node_id in node_ids:
                if node_id in inputs:
                    continue
                current = node_by_id[node_id]["primitive"]
                for primitive in policy["primitive_order"]:
                    if primitive != current:
                        yield {
                            "kind": "replace_primitive",
                            "node": node_id,
                            "primitive": primitive,
                        }
        elif kind == "add_edge":
            for edge_kind in ("feedforward", "recurrent"):
                for source in node_ids:
                    for target in node_ids:
                        if target in inputs:
                            continue
                        if edge_kind == "feedforward" and source == target:
                            continue
                        key = (source, target, edge_kind)
                        if key in edge_keys:
                            continue
                        yield {
                            "kind": "add_edge",
                            "source": source,
                            "target": target,
                            "edge_kind": edge_kind,
                        }
        elif kind == "remove_edge":
            for edge in architecture["edges"]:
                yield {
                    "kind": "remove_edge",
                    "source": edge["source"],
                    "target": edge["target"],
                    "edge_kind": edge["kind"],
                }
        elif kind == "add_node":
            node_id = _next_generated_node_id(node_ids)
            for primitive in policy["primitive_order"]:
                yield {
                    "kind": "add_node",
                    "node": {"id": node_id, "primitive": primitive, "config": {}},
                }
        elif kind == "remove_node":
            for node_id in node_ids:
                if node_id not in inputs and node_id not in outputs:
                    yield {"kind": "remove_node", "node": node_id}
        else:  # pragma: no cover - validate_policy closes this path
            raise CognitiveSearchError("unsupported mutation kind")


def enumerate_candidates(
    architecture: Any,
    policy: Mapping[str, Any],
    *,
    admitted_primitives: Collection[str],
    bounds: SearchBounds,
) -> tuple[ArchitectureCandidate, ...]:
    """Enumerate unique structurally valid descendants in deterministic policy order."""
    held = validate_policy(policy)
    admitted = {str(name) for name in admitted_primitives}
    if "source" in admitted:
        admitted.remove("source")
    missing = [name for name in held["primitive_order"] if name not in admitted]
    if missing:
        raise CognitiveSearchError(
            "search policy names primitives outside the external admitted registry: %s"
            % sorted(missing)
        )
    if held["candidate_limit"] > bounds.max_candidates:
        raise CognitiveSearchError(
            "search policy candidate limit exceeds the external candidate ceiling"
        )

    parent = canonical_architecture(
        architecture,
        admitted_primitives=admitted | {"source"},
        max_nodes=bounds.max_nodes,
        max_edges=bounds.max_edges,
    )
    parent_digest = architecture_digest(parent)
    candidates: list[ArchitectureCandidate] = []
    child_digests: set[str] = set()
    for proposal in _proposal_stream(parent, held):
        try:
            child, mutation = apply_mutation_record(
                parent,
                proposal,
                admitted_primitives=admitted,
                bounds=bounds.mutation_bounds,
            )
        except CognitiveMutationError:
            continue
        if mutation.child_digest == parent_digest or mutation.child_digest in child_digests:
            continue
        child_digests.add(mutation.child_digest)
        candidates.append(
            ArchitectureCandidate(
                policy_digest=held["policy_digest"],
                parent_architecture_digest=parent_digest,
                child_architecture=child,
                mutation=mutation,
            )
        )
        if len(candidates) >= held["candidate_limit"]:
            break
    return tuple(candidates)


def next_candidate(
    architecture: Any,
    policy: Mapping[str, Any],
    *,
    admitted_primitives: Collection[str],
    bounds: SearchBounds,
    observed_candidate_digests: Collection[str] = (),
) -> ArchitectureCandidate | None:
    """Return the first not-yet-observed candidate; retained evidence is inert identity only."""
    observed = {str(value) for value in observed_candidate_digests}
    for candidate in enumerate_candidates(
        architecture,
        policy,
        admitted_primitives=admitted_primitives,
        bounds=bounds,
    ):
        if candidate.candidate_digest not in observed:
            return candidate
    return None


def exhausted(
    architecture: Any,
    policy: Mapping[str, Any],
    *,
    admitted_primitives: Collection[str],
    bounds: SearchBounds,
    observed_candidate_digests: Collection[str],
) -> bool:
    return (
        next_candidate(
            architecture,
            policy,
            admitted_primitives=admitted_primitives,
            bounds=bounds,
            observed_candidate_digests=observed_candidate_digests,
        )
        is None
    )


def step(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Interpret one held policy into a declarative candidate proposal, never a verdict."""
    if not isinstance(payload, Mapping):
        raise CognitiveSearchError("search step payload is not a mapping")
    raw_bounds = payload.get("bounds")
    if not isinstance(raw_bounds, Mapping):
        raise CognitiveSearchError("search step carries no external bounds")
    bounds = SearchBounds(
        max_candidates=int(raw_bounds.get("max_candidates", 0)),
        max_nodes=int(raw_bounds.get("max_nodes", 0)),
        max_edges=int(raw_bounds.get("max_edges", -1)),
    )
    candidate = next_candidate(
        payload.get("architecture"),
        payload.get("policy") or {},
        admitted_primitives=list(payload.get("admitted_primitives") or []),
        bounds=bounds,
        observed_candidate_digests=list(payload.get("observed_candidate_digests") or []),
    )
    if candidate is None:
        return {"type": "Stop", "reason": "bounded cognitive architecture search exhausted"}
    return {
        "type": "ProposeArchitectureMutation",
        "candidate": candidate.record(),
    }
