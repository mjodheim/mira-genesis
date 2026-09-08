"""DEVELOPMENT regressions for bounded acquisition-machinery evolution.

The search-depth ceiling and expansion operator are host apparatus. What these tests require is that
the mutable search policy itself is persistent lineage state, that it cannot widen before its current
reach is exhausted, that the wider policy is adopted only after an unchanged trust root measures a
newly reachable improving descendant, and that the changed policy then produces the next body change.
"""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import policies, policy_controller, recovery
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="policy-evolution fixture")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


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


def _genesis(*, policy_updates=2):
    return Genesis(
        state=_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(
            limits={"generations": 8, "probes": 100, "policy_updates": policy_updates}
        ),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _world():
    return controller.world(
        tasks=TASKS,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        artifacts={},
        grade=bodies.grade,
    )


def _seed_policy(*, operations=("double", "increment"), ceiling=2):
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=operations,
        max_length=1,
        ceiling_length=ceiling,
        max_candidates=64,
    )


def test_policy_cannot_expand_before_its_current_search_space_is_exhausted():
    genesis = _genesis()
    policy_controller.admit_seed_policy(genesis, _seed_policy())

    with pytest.raises(policy_controller.PolicyControllerError, match="not exhausted"):
        policy_controller.expand_policy(genesis, _world())

    assert policy_controller.bound_policy(genesis)["max_length"] == 1


def test_exhausted_seed_policy_is_expanded_only_after_a_trust_root_judged_reach_witness(tmp_path):
    genesis = _genesis()
    first = policy_controller.run_policy(
        genesis,
        _world(),
        seed_policy=_seed_policy(),
        max_steps=4,
        checkpoint_directory=tmp_path,
    )
    assert [step.get("accepted") for step in first["steps"] if step["intent"] != "stop"] == [
        False,
        False,
    ]
    assert first["steps"][-1]["reason"] == "policy search exhausted at max_length=1"
    prior = policy_controller.bound_policy(genesis)
    assert policies.exhausted(prior, controller._controller_context(genesis).evidence) is True

    update = policy_controller.expand_policy(
        genesis,
        _world(),
        checkpoint_directory=tmp_path,
    )
    assert update["accepted"] is True
    assert update["candidate_policy"]["max_length"] == 2
    assert update["certificate"]["prior_policy_exhausted"] is True
    assert update["certificate"]["single_structural_change"] == {
        "field": "max_length",
        "before": 1,
        "after": 2,
    }
    assert update["certificate"]["resolving_program"]["operations"] == [
        "double",
        "increment",
    ]
    assert update["certificate"]["causal_dependency"]["established"] is True
    assert update["checkpoint_digest"]

    held = policy_controller.bound_policy(genesis)
    assert held == update["candidate_policy"]
    tool = next(tool for tool in genesis.state["tools"] if tool.get("role") == "lineage_search_policy")
    assert tool["provenance"]["class"] == "lineage_owned"
    assert tool["provenance"]["produced_by"] == "lineage policy expansion"


def test_changed_search_machinery_produces_the_next_body_modification():
    genesis = _genesis()
    here = _world()
    policy_controller.run_policy(genesis, here, seed_policy=_seed_policy(), max_steps=4)
    policy_controller.expand_policy(genesis, here)
    generation_before = genesis.state["generation"]

    second = policy_controller.run_policy(genesis, here, max_steps=4)
    attempts = [step for step in second["steps"] if step["intent"] == "GenerateTransform"]

    # The expanded policy does not retry the retained length-one failures. It reaches the new shell,
    # rejects double->double, then constructs and adopts double->increment.
    assert [step["program"]["operations"] for step in attempts] == [
        ["double", "double"],
        ["double", "increment"],
    ]
    assert [step["accepted"] for step in attempts] == [False, True]
    assert genesis.state["generation"] == generation_before + 1
    assert genesis.state["acquisitions"][-1]["name"] == "policy-program:double+increment"
    assert isinstance(genesis.body_factory, ConfiguredBody)

    update_observation = next(
        item for item in genesis.state["observations"] if item.get("kind") == "search_policy_updated"
    )
    assert update_observation["causal_dependency"]["established"] is True


def test_policy_update_is_not_adopted_when_new_depth_has_no_improving_descendant():
    genesis = _genesis()
    here = _world()
    seed = _seed_policy(operations=("negate",), ceiling=2)
    policy_controller.run_policy(genesis, here, seed_policy=seed, max_steps=3)
    before = policy_controller.bound_policy(genesis)

    update = policy_controller.expand_policy(genesis, here)
    assert update["accepted"] is False
    assert policy_controller.bound_policy(genesis) == before
    assert not any(
        item.get("kind") == "search_policy_updated" for item in genesis.state["observations"]
    )


def test_policy_and_generated_body_survive_process_death_after_the_machinery_change(tmp_path):
    genesis = _genesis()
    here = _world()
    policy_controller.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(),
        max_steps=4,
        checkpoint_directory=tmp_path,
    )
    policy_controller.expand_policy(genesis, here, checkpoint_directory=tmp_path)
    policy_controller.run_policy(
        genesis,
        here,
        max_steps=4,
        checkpoint_directory=tmp_path,
    )
    expected_policy = policy_controller.bound_policy(genesis)
    expected_state = genesis.state["state_digest"]

    restored = recovery.restore_lineage(tmp_path, grade=bodies.grade)
    assert restored.state["state_digest"] == expected_state
    assert policy_controller.bound_policy(restored) == expected_policy
    assert policy_controller.bound_policy(restored)["max_length"] == 2
    assert isinstance(restored.body_factory, ConfiguredBody)

    after = policy_controller.run_policy(restored, here, max_steps=1)
    assert after["steps"][0]["intent"] == "stop"
    assert after["steps"][0]["reason"] == "a policy-generated descendant was adopted"


def test_policy_update_budget_is_prospective_and_cannot_be_invented_after_exhaustion():
    genesis = _genesis(policy_updates=0)
    here = _world()
    policy_controller.run_policy(genesis, here, seed_policy=_seed_policy(), max_steps=4)

    with pytest.raises(policy_controller.PolicyControllerError, match="policy_updates"):
        policy_controller.expand_policy(genesis, here)
    assert policy_controller.bound_policy(genesis)["max_length"] == 1
