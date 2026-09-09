"""Regression: one runtime call owns M0 -> M1 -> P1 -> B1 hand-offs."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import metamorphic_policy_loop as runtime
from genesis import policies, policy_controller, policy_mutations, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="integrated MetaPolicy evolution fixture")
SQUARE_OBJECTIVE = (
    {"task_id": "m0", "input": 2, "expected": 4},
    {"task_id": "m1", "input": 3, "expected": 9},
)


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
                "generations": 64,
                "policy_mutations": 32,
                "policy_evaluations": 128,
                "meta_policy_candidates": 32,
                "meta_policy_evaluations": 128,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world():
    return controller.world(
        tasks=SQUARE_OBJECTIVE,
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
        ceiling_length=1,
        max_candidates=32,
    )


def _seed_meta():
    return meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
    )


def test_one_runtime_call_evolves_meta_policy_then_policy_then_body(tmp_path):
    genesis = _genesis()
    here = _world()
    seed_meta = _seed_meta()
    seed_policy = _seed_policy()

    run = runtime.run_objective(
        genesis,
        here,
        seed_policy=seed_policy,
        seed_meta_policy=seed_meta,
        max_rounds=32,
        checkpoint_directory=tmp_path,
    )

    assert run["body_adopted"] is True
    meta_steps = [step for step in run["steps"] if step["intent"] == "MetaPolicyEvolution"]
    assert len(meta_steps) == 1
    assert meta_steps[0]["accepted"] is True
    assert meta_steps[0]["selection_reason"] == "unique_strict_maximum"
    assert meta_steps[0]["parent_meta_policy_digest"] == seed_meta["meta_policy_digest"]
    assert meta_steps[0]["new_meta_policy_digest"] != seed_meta["meta_policy_digest"]
    assert meta_steps[0]["durable_budget_round_digest"]

    held_meta = meta.bound_meta_policy(genesis)
    assert held_meta["parent_meta_policy_digest"] == seed_meta["meta_policy_digest"]
    square_mutations = [
        item
        for item in held_meta["mutations"]
        if item["kind"] == "add_operation" and item.get("operation") == "square"
    ]
    assert len(square_mutations) == 1

    held_policy = policy_controller.bound_policy(genesis)
    assert held_policy["parent_policy_digest"] == seed_policy["policy_digest"]
    assert held_policy["operation_names"] == ["increment", "square"]

    accepted_body_steps = [
        step
        for step in run["steps"]
        if step["intent"] == "GenerateTransform" and step.get("accepted")
    ]
    assert len(accepted_body_steps) == 1
    assert accepted_body_steps[0]["program"]["operations"] == ["square"]
    assert genesis.body_factory.configuration["operations"] == ("square",)

    # The launcher called only run_objective. The same persistent lineage retains every machinery
    # transition and the generated body after process death.
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert meta.bound_meta_policy(restored) == held_meta
    assert policy_controller.bound_policy(restored) == held_policy
    assert restored.body_factory.configuration["operations"] == ("square",)
