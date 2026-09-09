"""DEVELOPMENT regressions for bounded evidence-backed MetaPolicy descendants."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import meta_policy_evolution as meta_evolution
from genesis import objective_policy_controller as opc
from genesis import policies, policy_controller, policy_mutations, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="MetaPolicy evolution fixture")
SQUARE_OBJECTIVE = (
    {"task_id": "m0", "input": 2, "expected": 4},
    {"task_id": "m1", "input": 3, "expected": 9},
)
TIE_OBJECTIVE = ({"task_id": "t0", "input": 2, "expected": 4},)


def _state():
    return st.create_state(
        body_digest=tr.artifact_digest_of(fixtures.null_body)["artifact_digest"],
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _genesis(*, meta_candidates=16, meta_evaluations=64):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 32,
                "policy_mutations": 16,
                "policy_evaluations": 64,
                "meta_policy_candidates": meta_candidates,
                "meta_policy_evaluations": meta_evaluations,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world(tasks):
    return controller.world(
        tasks=tasks,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def _seed_policy(*, ceiling=1):
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment",),
        max_length=1,
        ceiling_length=ceiling,
        max_candidates=32,
    )


def _terminal_seed_meta():
    return meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
    )


def _exhaust_body_and_meta(genesis, here, *, ceiling=1, directory=None):
    body_run = opc.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(ceiling=ceiling),
        max_steps=16,
        checkpoint_directory=directory,
    )
    generated = [step for step in body_run["steps"] if step["intent"] == "GenerateTransform"]
    assert generated
    assert all(step["accepted"] is False for step in generated)
    assert opc.exhausted(genesis, here) is True

    meta_run = meta.run_meta_policy(
        genesis,
        here,
        seed_meta_policy=_terminal_seed_meta(),
        max_steps=8,
        checkpoint_directory=directory,
    )
    mutations = [step for step in meta_run["steps"] if step.get("intent") == "PolicyMutation"]
    assert len(mutations) == 1
    assert mutations[0]["accepted"] is False
    assert meta.bound_meta_policy(genesis) == _terminal_seed_meta()
    assert policy_controller.bound_policy(genesis) == _seed_policy(ceiling=ceiling)


def test_exhausted_meta_policy_acquires_a_data_only_descendant_then_changes_lower_machinery(tmp_path):
    genesis = _genesis()
    here = _world(SQUARE_OBJECTIVE)
    _exhaust_body_and_meta(genesis, here, directory=tmp_path)
    parent_meta = meta.bound_meta_policy(genesis)
    parent_policy = policy_controller.bound_policy(genesis)

    evolution = meta_evolution.evolve_meta_policy(
        genesis,
        here,
        checkpoint_directory=tmp_path,
    )

    assert evolution["accepted"] is True
    assert evolution["selection_reason"] == "unique_strict_maximum"
    winner = evolution["winner"]
    assert winner["added_mutation"]["kind"] == "add_operation"
    assert winner["added_mutation"]["operation"] == "square"
    assert winner["selection_score"] == 2

    descendant = meta.bound_meta_policy(genesis)
    assert descendant["parent_meta_policy_digest"] == parent_meta["meta_policy_digest"]
    assert descendant["meta_policy_digest"] != parent_meta["meta_policy_digest"]
    assert {item["operation"] for item in descendant["mutations"] if item["kind"] == "add_operation"} == {
        "negate",
        "square",
    }
    certificate = evolution["certificate"]
    assert certificate["dependency"]["kind"] == "meta_policy_structural_reach_dependency"
    assert certificate["dependency"]["counterfactual_meta_machinery_ablation_established"] is False
    assert certificate["parent_meta_policy_digest"] == parent_meta["meta_policy_digest"]
    assert certificate["new_meta_policy_digest"] == descendant["meta_policy_digest"]

    # The MetaPolicy descendant is not merely a stored certificate. On the same retained objective,
    # it now exposes `add_operation(square)`, and the unchanged lower-level meta-controller adopts
    # the corresponding search-policy descendant.
    lower = meta.run_meta_policy(
        genesis,
        here,
        max_steps=8,
        checkpoint_directory=tmp_path,
    )
    accepted = [step for step in lower["steps"] if step.get("intent") == "PolicyMutation" and step.get("accepted")]
    assert len(accepted) == 1
    assert accepted[0]["mutation"]["operation"] == "square"
    changed_policy = policy_controller.bound_policy(genesis)
    assert changed_policy["parent_policy_digest"] == parent_policy["policy_digest"]
    assert changed_policy["operation_names"] == ["increment", "square"]

    # The changed policy then produces the body through the ordinary objective-scoped body path.
    body_run = opc.run_policy(
        genesis,
        here,
        max_steps=16,
        checkpoint_directory=tmp_path,
    )
    accepted_bodies = [
        step for step in body_run["steps"] if step["intent"] == "GenerateTransform" and step["accepted"]
    ]
    assert len(accepted_bodies) == 1
    assert accepted_bodies[0]["program"]["operations"] == ["square"]

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert meta.bound_meta_policy(restored) == descendant
    assert policy_controller.bound_policy(restored) == changed_policy
    assert restored.body_factory.configuration["operations"] == ("square",)


def test_meta_policy_descendant_selection_tie_adopts_nothing():
    genesis = _genesis()
    here = _world(TIE_OBJECTIVE)
    _exhaust_body_and_meta(genesis, here, ceiling=2)
    parent_meta = meta.bound_meta_policy(genesis)

    evolution = meta_evolution.evolve_meta_policy(genesis, here)

    assert evolution["accepted"] is False
    assert evolution["selection_reason"] == "ambiguous_no_strict_maximum"
    assert meta.bound_meta_policy(genesis) == parent_meta
    viable = [item for item in evolution["measurements"] if item["viable"]]
    assert len(viable) >= 2
    top = max(item["selection_score"] for item in viable)
    assert sum(1 for item in viable if item["selection_score"] == top) >= 2


def test_meta_policy_evolution_refuses_incomplete_round_before_first_measurement():
    genesis = _genesis(meta_candidates=1, meta_evaluations=64)
    here = _world(SQUARE_OBJECTIVE)
    _exhaust_body_and_meta(genesis, here)
    before = [item for item in genesis.state["observations"] if item.get("kind") == meta_evolution.MEASUREMENT_KIND]

    with pytest.raises(meta_evolution.MetaPolicyEvolutionError, match="complete MetaPolicy round"):
        meta_evolution.evolve_meta_policy(genesis, here)

    after = [item for item in genesis.state["observations"] if item.get("kind") == meta_evolution.MEASUREMENT_KIND]
    assert after == before == []
    assert genesis.budget.spent["meta_policy_candidates"] == 0
    assert genesis.budget.spent["meta_policy_evaluations"] == 0
