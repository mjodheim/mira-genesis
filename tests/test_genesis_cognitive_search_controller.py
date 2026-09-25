"""DEVELOPMENT regressions for persistent lineage-held cognitive architecture search."""
from __future__ import annotations

import pytest

from genesis import cognitive_architecture as ca
from genesis import cognitive_search as cs
from genesis import cognitive_search_controller as csc
from genesis import development_bodies as bodies
from genesis import recovery
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="cognitive-search fixture")


def _state():
    return st.create_state(
        body_digest="seed",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            },
            {
                "name": "signal_interface",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            },
        ],
        vocabulary=[
            {"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None},
            {"name": "resolvable_by_signal_interface", "origin": "seed", "certificate": None},
        ],
    )


def _genesis():
    return Genesis(
        state=_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


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


def _policy(*, primitives=("identity", "sum", "state_cell")):
    return cs.create_policy(
        mutation_kinds=("replace_primitive", "remove_edge", "add_edge"),
        primitive_order=primitives,
        candidate_limit=6,
    )


BOUNDS = cs.SearchBounds(max_candidates=8, max_nodes=6, max_edges=10)
ADMITTED = {"identity", "sum", "state_cell", "threshold_router"}


def test_seed_policy_is_canonical_lineage_state_and_cannot_be_silently_replaced():
    genesis = _genesis()
    policy = _policy()

    assert csc.admit_seed_policy(genesis, policy) is True
    assert csc.bound_policy(genesis) == policy
    tool = next(
        tool for tool in genesis.state["tools"]
        if tool.get("role") == csc.POLICY_ROLE
    )
    assert tool["artifact"]["policy_digest"] == policy["policy_digest"]
    assert tool["provenance"]["class"] == "host_written"

    assert csc.admit_seed_policy(genesis, policy) is False
    with pytest.raises(csc.CognitiveSearchControllerError, match="already holds"):
        csc.admit_seed_policy(
            genesis,
            cs.create_policy(
                mutation_kinds=("remove_edge",),
                primitive_order=("identity",),
                candidate_limit=2,
            ),
        )


def test_proposal_is_revalidated_and_cannot_spend_budget_or_mutate_lineage_state():
    genesis = _genesis()
    policy = _policy()
    csc.admit_seed_policy(genesis, policy)
    state_before = genesis.state["state_digest"]
    spent_before = dict(genesis.budget.spent)

    result = csc.propose_next(
        genesis,
        _architecture(),
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )

    assert result["stopped"] is False
    assert result["policy_digest"] == policy["policy_digest"]
    assert result["state_digest"] == state_before
    assert genesis.state["state_digest"] == state_before
    assert dict(genesis.budget.spent) == spent_before

    expected = cs.next_candidate(
        _architecture(),
        policy,
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    assert expected is not None
    assert result["candidate"] == expected.record()


def test_retained_candidate_identity_moves_held_policy_to_next_proposal():
    genesis = _genesis()
    policy = _policy()
    csc.admit_seed_policy(genesis, policy)
    first = csc.propose_next(
        genesis,
        _architecture(),
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
    )
    second = csc.propose_next(
        genesis,
        _architecture(),
        admitted_primitives=ADMITTED,
        bounds=BOUNDS,
        observed_candidate_digests=(first["candidate"]["candidate_digest"],),
    )

    assert second["stopped"] is False
    assert second["candidate"]["candidate_digest"] != first["candidate"]["candidate_digest"]


def test_seed_policy_survives_checkpoint_restore(tmp_path):
    genesis = _genesis()
    policy = _policy()
    csc.admit_seed_policy(genesis, policy)
    expected_state = genesis.state["state_digest"]
    genesis.persist(tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=bodies.grade)
    assert restored.state["state_digest"] == expected_state
    assert csc.bound_policy(restored) == policy


def test_seed_policy_cannot_fake_a_parent_lineage():
    genesis = _genesis()
    fake_descendant = cs.create_policy(
        mutation_kinds=("replace_primitive",),
        primitive_order=("identity", "sum"),
        candidate_limit=2,
        parent_policy_digest="unobserved-parent",
    )
    with pytest.raises(csc.CognitiveSearchControllerError, match="unobserved parent"):
        csc.admit_seed_policy(genesis, fake_descendant)
