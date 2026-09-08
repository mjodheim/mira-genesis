"""DEVELOPMENT regressions for objective-scoped repeated search-machinery evolution."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import objective_policy_controller as opc
from genesis import policies, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="objective-policy recursion fixture")


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


def _genesis(*, policy_evaluations=16):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 32,
                "policy_updates": 2,
                "policy_evaluations": policy_evaluations,
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


def _seed_policy():
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment", "square"),
        max_length=1,
        ceiling_length=3,
        max_candidates=32,
    )


def test_rejections_from_one_objective_do_not_exhaust_another_objective():
    genesis = _genesis()
    first = _world(fixtures.OBJECTIVE_ONE)
    second = _world(fixtures.OBJECTIVE_TWO)

    run = opc.run_policy(genesis, first, seed_policy=_seed_policy(), max_steps=4)
    assert [step.get("accepted") for step in run["steps"] if step["intent"] != "stop"] == [
        False,
        False,
    ]
    assert opc.exhausted(genesis, first) is True

    first_goal = opc.objective_record(genesis, first)
    second_goal = opc.objective_record(genesis, second)
    assert first_goal["objective_digest"] != second_goal["objective_digest"]
    assert opc.exhausted(genesis, second) is False


def test_policy_meta_evaluations_have_a_prospective_budget():
    genesis = _genesis(policy_evaluations=0)
    here = _world(fixtures.OBJECTIVE_ONE)
    opc.run_policy(genesis, here, seed_policy=_seed_policy(), max_steps=4)

    with pytest.raises(opc.ObjectivePolicyError, match="policy_evaluations"):
        opc.expand_policy(genesis, here)
    assert policy_controller.bound_policy(genesis)["max_length"] == 1


def test_changed_policy_can_become_exhausted_and_earn_a_second_machinery_change(tmp_path):
    """Depth-1 -> depth-2 -> body -> new objective -> depth-3 -> body, with retained capability."""
    genesis = _genesis()
    first = _world(fixtures.OBJECTIVE_ONE)
    second = _world(fixtures.OBJECTIVE_TWO)
    seed = _seed_policy()

    # Objective one: depth one has no solution.
    first_search = opc.run_policy(
        genesis,
        first,
        seed_policy=seed,
        max_steps=4,
        checkpoint_directory=tmp_path,
    )
    assert opc.exhausted(genesis, first) is True
    assert first_search["steps"][-1]["intent"] == "stop"

    # The first machinery change reaches depth two and is licensed by a measured witness.
    update_one = opc.expand_policy(genesis, first, checkpoint_directory=tmp_path)
    assert update_one["accepted"] is True
    assert update_one["candidate_policy"]["max_length"] == 2
    assert update_one["certificate"]["meta_evaluations_spent"] == 1
    first_policy_digest = update_one["candidate_policy"]["policy_digest"]

    body_one = opc.run_policy(genesis, first, max_steps=4, checkpoint_directory=tmp_path)
    accepted_one = [step for step in body_one["steps"] if step.get("accepted")]
    assert len(accepted_one) == 1
    assert accepted_one[0]["program"]["operations"] == ["increment", "increment"]
    assert isinstance(genesis.body_factory, ConfiguredBody)
    assert genesis.body_factory.configuration["operations"] == ("increment", "increment")

    # Objective two contains every old task plus one new point. The depth-two descendant therefore
    # has to retain its old reach while gaining the new one; it cannot trade the first objective away.
    second_search = opc.run_policy(
        genesis,
        second,
        max_steps=8,
        checkpoint_directory=tmp_path,
    )
    second_attempts = [
        step for step in second_search["steps"] if step["intent"] == "GenerateTransform"
    ]
    assert len(second_attempts) == 6
    assert all(step["accepted"] is False for step in second_attempts)
    assert opc.exhausted(genesis, second) is True

    # Crucial recursive property: the *already changed* depth-two policy is now the exhausted parent
    # of another evidence-backed machinery change.
    update_two = opc.expand_policy(genesis, second, checkpoint_directory=tmp_path)
    assert update_two["accepted"] is True
    assert update_two["prior_policy"]["policy_digest"] == first_policy_digest
    assert update_two["prior_policy"]["max_length"] == 2
    assert update_two["candidate_policy"]["max_length"] == 3
    assert update_two["candidate_policy"]["parent_policy_digest"] == first_policy_digest
    assert update_two["certificate"]["meta_evaluations_spent"] == 5
    assert update_two["certificate"]["resolving_program"]["operations"] == [
        "square",
        "increment",
        "increment",
    ]

    body_two = opc.run_policy(genesis, second, max_steps=7, checkpoint_directory=tmp_path)
    accepted_two = [step for step in body_two["steps"] if step.get("accepted")]
    assert len(accepted_two) == 1
    assert accepted_two[0]["program"]["operations"] == [
        "square",
        "increment",
        "increment",
    ]
    assert genesis.body_factory.configuration["operations"] == (
        "square",
        "increment",
        "increment",
    )

    updates = [
        item for item in genesis.state["observations"] if item.get("kind") == "search_policy_updated"
    ]
    assert len(updates) == 2
    assert updates[0]["causal_dependency"]["established"] is True
    assert updates[1]["causal_dependency"]["established"] is True
    assert updates[0]["objective_digest"] != updates[1]["objective_digest"]

    # The second objective retained the first two tasks, so the final accepted body is measured as a
    # strict extension rather than a score trade. It and the twice-changed policy survive process death.
    assert accepted_two[0]["reason"] == ""
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert isinstance(restored.body_factory, ConfiguredBody)
    assert restored.body_factory.configuration["operations"] == (
        "square",
        "increment",
        "increment",
    )
    assert policy_controller.bound_policy(restored)["max_length"] == 3
    assert policy_controller.bound_policy(restored)["policy_digest"] == update_two["candidate_policy"][
        "policy_digest"
    ]
