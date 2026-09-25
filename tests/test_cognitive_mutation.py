import pytest

from genesis.cognitive_architecture import COGNITIVE_ARCHITECTURE_SCHEMA, architecture_digest
from genesis.cognitive_mutation import (
    CognitiveMutationError,
    MutationBounds,
    apply_mutation,
    apply_mutation_record,
)


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


def architecture_with_middle():
    return {
        "schema": COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": [
            {"id": "in", "primitive": "source", "config": {}},
            {"id": "mid", "primitive": "identity", "config": {}},
            {"id": "out", "primitive": "identity", "config": {}},
        ],
        "edges": [
            {"source": "in", "target": "mid", "kind": "feedforward"},
            {"source": "mid", "target": "out", "kind": "feedforward"},
        ],
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


def test_add_node_is_canonical_and_cannot_create_external_source():
    mutated = apply_mutation(
        architecture(),
        {
            "kind": "add_node",
            "node": {"id": "mid", "primitive": "identity", "config": {"label": "candidate"}},
        },
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert {"id": "mid", "primitive": "identity", "config": {"label": "candidate"}} in mutated["nodes"]

    with pytest.raises(CognitiveMutationError, match="external source"):
        apply_mutation(
            architecture(),
            {"kind": "add_node", "node": {"id": "new_input", "primitive": "source"}},
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )


def test_add_node_respects_external_node_budget():
    with pytest.raises(CognitiveMutationError, match="does not produce"):
        apply_mutation(
            architecture(),
            {"kind": "add_node", "node": {"id": "mid", "primitive": "identity"}},
            admitted_primitives=ADMITTED,
            bounds=MutationBounds(max_nodes=2, max_edges=4),
        )


def test_remove_node_removes_incident_edges_but_protects_io_nodes():
    mutated = apply_mutation(
        architecture_with_middle(),
        {"kind": "remove_node", "node": "mid"},
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert [node["id"] for node in mutated["nodes"]] == ["in", "out"]
    assert mutated["edges"] == []

    for protected in ("in", "out"):
        with pytest.raises(CognitiveMutationError, match="cannot be removed"):
            apply_mutation(
                architecture_with_middle(),
                {"kind": "remove_node", "node": protected},
                admitted_primitives=ADMITTED,
                bounds=BOUNDS,
            )


def test_mutation_record_binds_parent_proposal_and_child_deterministically():
    proposal = {"kind": "replace_primitive", "node": "out", "primitive": "sum"}
    child_a, record_a = apply_mutation_record(
        architecture(),
        proposal,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    child_b, record_b = apply_mutation_record(
        architecture(),
        proposal,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )

    assert child_a == child_b
    assert record_a == record_b
    assert record_a.parent_digest == architecture_digest(architecture())
    assert record_a.child_digest == architecture_digest(child_a)
    assert record_a.record_digest == record_b.record_digest

    _, changed = apply_mutation_record(
        architecture(),
        {"kind": "replace_config", "node": "out", "config": {"gain": 2}},
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert changed.proposal_digest != record_a.proposal_digest
    assert changed.record_digest != record_a.record_digest


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
