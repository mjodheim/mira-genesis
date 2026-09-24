"""DEVELOPMENT regressions for substrate-neutral cognitive architecture genomes."""
from __future__ import annotations

import pytest

from genesis import cognitive_architecture as ca


def _architecture():
    return {
        "schema": ca.COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": [
            {"id": "input", "primitive": "source", "config": {"width": 4}},
            {"id": "memory", "primitive": "state_cell", "config": {"slots": 8}},
            {"id": "output", "primitive": "sink", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "memory", "kind": "feedforward"},
            {"source": "memory", "target": "memory", "kind": "recurrent"},
            {"source": "memory", "target": "output", "kind": "feedforward"},
        ],
        "inputs": ["input"],
        "outputs": ["output"],
    }


def test_digest_is_order_independent_but_covers_configuration():
    first = _architecture()
    reordered = _architecture()
    reordered["nodes"] = list(reversed(reordered["nodes"]))
    reordered["edges"] = list(reversed(reordered["edges"]))

    assert ca.architecture_digest(first) == ca.architecture_digest(reordered)

    changed = _architecture()
    changed["nodes"][1]["config"]["slots"] = 9
    assert ca.architecture_digest(first) != ca.architecture_digest(changed)


def test_primitive_family_is_not_hard_coded_but_registry_can_fail_closed():
    architecture = _architecture()
    architecture["nodes"][1]["primitive"] = "future_unknown_machine"

    canonical = ca.canonical_architecture(architecture)
    assert "future_unknown_machine" in {
        node["primitive"] for node in canonical["nodes"]
    }

    with pytest.raises(ca.CognitiveArchitectureError, match="outside the admitted registry"):
        ca.canonical_architecture(
            architecture,
            admitted_primitives={"source", "state_cell", "sink"},
        )


def test_feedforward_cycles_are_refused_while_recurrent_cycles_are_allowed():
    ca.canonical_architecture(_architecture())

    forbidden = _architecture()
    forbidden["edges"].append(
        {"source": "output", "target": "input", "kind": "feedforward"}
    )
    with pytest.raises(ca.CognitiveArchitectureError, match="feedforward edges contain a cycle"):
        ca.canonical_architecture(forbidden)


def test_dangling_edges_duplicate_nodes_and_bounds_fail_closed():
    dangling = _architecture()
    dangling["edges"].append(
        {"source": "missing", "target": "output", "kind": "feedforward"}
    )
    with pytest.raises(ca.CognitiveArchitectureError, match="refers to a missing node"):
        ca.canonical_architecture(dangling)

    duplicate = _architecture()
    duplicate["nodes"].append(dict(duplicate["nodes"][0]))
    with pytest.raises(ca.CognitiveArchitectureError, match="duplicate node"):
        ca.canonical_architecture(duplicate)

    with pytest.raises(ca.CognitiveArchitectureError, match="admitted node maximum"):
        ca.canonical_architecture(_architecture(), max_nodes=2)


def test_structural_profile_reports_facts_without_inventing_resource_measurements():
    profile = ca.structural_profile(_architecture())

    assert profile["node_count"] == 3
    assert profile["edge_count"] == 3
    assert profile["feedforward_edge_count"] == 2
    assert profile["recurrent_edge_count"] == 1
    assert profile["max_feedforward_depth"] == 2
    assert profile["primitive_counts"] == {"sink": 1, "source": 1, "state_cell": 1}
    assert profile["compute_estimate"] is None
    assert profile["energy_estimate"] is None
