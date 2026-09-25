"""DEVELOPMENT regressions for lineage-held cognitive architecture search."""
from __future__ import annotations

import pytest

from genesis import cognitive_architecture as ca
from genesis import cognitive_search as cs


ADMITTED = {"identity", "sum", "state_cell", "threshold_router"}
BOUNDS = cs.SearchBounds(max_candidates=16, max_nodes=6, max_edges=10)


def _architecture():
    return {
        "schema": ca.COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": [
            {"id": "input", "primitive": "source", "config": {}},
            {"id": "hidden", "primitive": "identity", "config": {}},
            {"id": "output", "primitive": "identity", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "hidden", "kind": "feedforward"},
            {"source": "hidden", "target": "output", "kind": "feedforward"},
        ],
        "inputs": ["input"],
        "outputs": ["output"],
    }


def _policy(*, limit=8, primitive_order=("identity", "sum", "state_cell")):
    return cs.create_policy(
        mutation_kinds=("replace_primitive", "remove_edge", "add_edge"),
        primitive_order=primitive_order,
        candidate_limit=limit,
    )


def test_search_policy_is_content_addressed_and_fails_closed_on_tampering():
    left = _policy()
    right = _policy()
    assert left == right
    assert cs.validate_policy(left) == left

    tampered = dict(left)
    tampered["candidate_limit"] += 1
    with pytest.raises(cs.CognitiveSearchError, match="does not reconstruct"):
        cs.validate_policy(tampered)


def test_candidate_enumeration_is_deterministic_unique_and_binds_lineage_identity():
    first = cs.enumerate_candidates(
        _architecture(),
        _policy(),
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    second = cs.enumerate_candidates(
        _architecture(),
        _policy(),
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )

    assert [item.candidate_digest for item in first] == [
        item.candidate_digest for item in second
    ]
    assert len({item.mutation.child_digest for item in first}) == len(first)
    assert len(first) == _policy()["candidate_limit"]

    parent_digest = ca.architecture_digest(_architecture())
    for item in first:
        record = item.record()
        assert record["policy_digest"] == _policy()["policy_digest"]
        assert record["parent_architecture_digest"] == parent_digest
        assert record["child_architecture_digest"] == ca.architecture_digest(
            record["child_architecture"]
        )
        assert record["mutation_record_digest"] == item.mutation.record_digest


def test_external_candidate_ceiling_overrules_lineage_policy():
    policy = _policy(limit=3)
    with pytest.raises(cs.CognitiveSearchError, match="external candidate ceiling"):
        cs.enumerate_candidates(
            _architecture(),
            policy,
            admitted_primitives=ADMITTED,
            bounds=cs.SearchBounds(max_candidates=2, max_nodes=6, max_edges=10),
        )


def test_policy_cannot_smuggle_a_primitive_outside_external_registry():
    policy = _policy(primitive_order=("identity", "unadmitted_machine"))
    with pytest.raises(cs.CognitiveSearchError, match="external admitted registry"):
        cs.enumerate_candidates(
            _architecture(),
            policy,
            admitted_primitives=ADMITTED,
            bounds=BOUNDS,
        )


def test_retained_candidate_identity_is_skipped_without_reading_any_score():
    policy = _policy(limit=4)
    candidates = cs.enumerate_candidates(
        _architecture(),
        policy,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    first = cs.next_candidate(
        _architecture(),
        policy,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert first is not None
    assert first.candidate_digest == candidates[0].candidate_digest

    second = cs.next_candidate(
        _architecture(),
        policy,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
        observed_candidate_digests=(first.candidate_digest,),
    )
    assert second is not None
    assert second.candidate_digest == candidates[1].candidate_digest

    observed = [candidate.candidate_digest for candidate in candidates]
    assert cs.exhausted(
        _architecture(),
        policy,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
        observed_candidate_digests=observed,
    ) is True


def test_step_returns_only_a_declarative_proposal_not_an_evaluation():
    policy = _policy(limit=2)
    result = cs.step(
        {
            "architecture": _architecture(),
            "policy": policy,
            "admitted_primitives": sorted(ADMITTED),
            "bounds": {
                "max_candidates": BOUNDS.max_candidates,
                "max_nodes": BOUNDS.max_nodes,
                "max_edges": BOUNDS.max_edges,
            },
            "observed_candidate_digests": [],
        }
    )

    assert result["type"] == "ProposeArchitectureMutation"
    candidate = result["candidate"]
    assert candidate["policy_digest"] == policy["policy_digest"]
    forbidden = {"score", "reward", "accepted", "verdict", "energy_joules"}
    assert forbidden.isdisjoint(result)
    assert forbidden.isdisjoint(candidate)


def test_add_node_uses_deterministic_generated_identity():
    policy = cs.create_policy(
        mutation_kinds=("add_node",),
        primitive_order=("identity",),
        candidate_limit=1,
    )
    candidate = cs.enumerate_candidates(
        _architecture(),
        policy,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )[0]
    node_ids = {node["id"] for node in candidate.child_architecture["nodes"]}
    assert "cognitive_candidate_0" in node_ids
