import pytest

from genesis.cognitive_architecture import COGNITIVE_ARCHITECTURE_SCHEMA
from genesis.cognitive_mutation import CognitiveMutationError, MutationBounds, apply_mutation


def architecture():
    return {
        "schema": COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": [
            {"id": "in", "primitive": "source", "config": {}},
            {"id": "out", "primitive": "identity", "config": {}},
        ],
        "edges": [{"source": "in", "target": "out", "kind": "feedforward"}],
        "inputs": ["in"],
        "outputs": ["out"],
    }


BOUNDS = MutationBounds(max_nodes=4, max_edges=4)
ADMITTED = {"identity", "sum", "state_cell"}


def test_replace_primitive_is_explicit_and_canonical():
    mutated = apply_mutation(
        architecture(),
        {"kind": "replace_primitive", "node": "out", "primitive": "sum"},
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert next(node for node in mutated["nodes"] if node["id"] == "out")["primitive"] == "sum"


def test_source_primitive_cannot_be_mutated():
    with pytest.raises(CognitiveMutationError, match="source primitives are immutable"):
        apply_mutation(
            architecture(),
            {"kind": "replace_primitive", "node": "in", "primitive": "sum"},
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )


def test_unadmitted_primitive_fails_closed():
    with pytest.raises(CognitiveMutationError, match="not admitted"):
        apply_mutation(
            architecture(),
            {"kind": "replace_primitive", "node": "out", "primitive": "mystery"},
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )


def test_feedforward_cycle_proposal_fails_closed():
    with pytest.raises(CognitiveMutationError, match="does not produce"):
        apply_mutation(
            architecture(),
            {"kind": "add_edge", "source": "out", "target": "in", "edge_kind": "feedforward"},
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )


def test_recurrent_edge_may_close_cross_step_loop():
    mutated = apply_mutation(
        architecture(),
        {"kind": "add_edge", "source": "out", "target": "out", "edge_kind": "recurrent"},
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert {"source": "out", "target": "out", "kind": "recurrent"} in mutated["edges"]


def test_edge_budget_is_enforced_after_mutation():
    with pytest.raises(CognitiveMutationError, match="does not produce"):
        apply_mutation(
            architecture(),
            {"kind": "add_edge", "source": "out", "target": "out", "edge_kind": "recurrent"},
            admitted_primitives=ADMITTED,
            bounds=MutationBounds(max_nodes=2, max_edges=1),
        )


def test_remove_absent_edge_and_extra_fields_fail_closed():
    with pytest.raises(CognitiveMutationError, match="absent edge"):
        apply_mutation(
            architecture(),
            {"kind": "remove_edge", "source": "out", "target": "in", "edge_kind": "recurrent"},
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )
    with pytest.raises(CognitiveMutationError, match="fields"):
        apply_mutation(
            architecture(),
            {"kind": "replace_config", "node": "out", "config": {}, "score": 1},
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )
