"""Regression for Hati hostile audit 3: authored menu order must not choose policy machinery."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import objective_policy_controller as opc
from genesis import policies, policy_controller, policy_mutations
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="Hati ordering regression")
TASKS = ({"task_id": "only", "input": 2, "expected": 4},)


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


def _genesis():
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 16,
                "policy_updates": 0,
                "policy_evaluations": 16,
                "policy_mutations": 8,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world():
    return controller.world(
        tasks=TASKS,
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
        operation_names=("increment",),
        max_length=1,
        ceiling_length=2,
        max_candidates=8,
    )


def _exhaust(genesis, here):
    run = retentive.run_policy(genesis, here, seed_policy=_seed_policy(), max_steps=4)
    attempts = [step for step in run["steps"] if step["intent"] == "GenerateTransform"]
    assert len(attempts) == 1
    assert attempts[0]["accepted"] is False
    assert opc.exhausted(genesis, here) is True


def _run(order):
    genesis = _genesis()
    here = _world()
    _exhaust(genesis, here)
    prior = policy_controller.bound_policy(genesis)
    mutations = {
        "depth": policy_mutations.create("increase_depth"),
        "square": policy_mutations.create("add_operation", operation="square"),
    }
    meta_policy = meta.create_meta_policy(tuple(mutations[name] for name in order))
    run = meta.run_meta_policy(genesis, here, seed_meta_policy=meta_policy, max_steps=8)
    return genesis, prior, run


def test_two_equally_good_mutations_do_not_let_host_menu_order_choose_the_policy():
    first, prior_a, run_a = _run(("depth", "square"))
    second, prior_b, run_b = _run(("square", "depth"))

    # Both edits are real improvements on this one-point objective:
    # increment->increment maps 2 to 4, and square maps 2 to 4. The admitted trust-root measure
    # therefore has no strict evidence for choosing one machinery descendant over the other.
    assert run_a["selection"]["status"] == "ambiguous_no_strict_maximum"
    assert run_b["selection"]["status"] == "ambiguous_no_strict_maximum"
    assert sorted(item["selection_score"] for item in run_a["selection"]["viable"]) == [1, 1]
    assert sorted(item["selection_score"] for item in run_b["selection"]["viable"]) == [1, 1]

    # Reversing authored menu order changes neither the retained search policy nor the decision.
    assert policy_controller.bound_policy(first) == prior_a
    assert policy_controller.bound_policy(second) == prior_b
    assert prior_a == prior_b
    assert not any(step.get("accepted") for step in run_a["steps"] if step.get("intent") == "PolicyMutation")
    assert not any(step.get("accepted") for step in run_b["steps"] if step.get("intent") == "PolicyMutation")


def test_unique_strict_meta_policy_winner_remains_adoptable():
    genesis = _genesis()
    here = controller.world(
        tasks=(
            {"task_id": "a", "input": 2, "expected": 4},
            {"task_id": "b", "input": 3, "expected": 9},
        ),
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )
    _exhaust(genesis, here)
    prior = policy_controller.bound_policy(genesis)
    meta_policy = meta.create_meta_policy(
        (
            policy_mutations.create("increase_depth"),
            policy_mutations.create("add_operation", operation="square"),
        )
    )
    run = meta.run_meta_policy(genesis, here, seed_meta_policy=meta_policy, max_steps=8)

    assert run["selection"]["status"] == "unique_strict_maximum"
    current = policy_controller.bound_policy(genesis)
    assert current["parent_policy_digest"] == prior["policy_digest"]
    assert current["operation_names"] == ["increment", "square"]
    accepted = [step for step in run["steps"] if step.get("accepted")]
    assert len(accepted) == 1
    assert accepted[0]["mutation"]["kind"] == "add_operation"
    assert accepted[0]["mutation"]["operation"] == "square"
    assert accepted[0]["certificate"]["selection"]["unique_strict_maximum"] is True
    assert accepted[0]["certificate"]["causal_dependency"]["kind"] == "structural_reach_dependency"
    assert accepted[0]["certificate"]["causal_dependency"]["counterfactual_machinery_ablation_established"] is False
