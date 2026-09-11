"""DEVELOPMENT regressions binding generated candidates to held policy registry identity."""
from __future__ import annotations

import pytest

from genesis import controller, development_bodies as bodies, objective_policy_controller as opc
from genesis import policies, policy_controller, state as st, trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="policy registry binding fixture")
TASKS = ({"task_id": "r0", "input": 1, "expected": 2},)

def grade(task, answer):
    return "solved" if answer == task["expected"] else "unsolved"

def seed_body():
    class Body:
        def attempt(self, task):
            return None
    return Body()

def genesis():
    state = st.create_state(
        body_digest=tr.artifact_digest_of(seed_body)["artifact_digest"],
        components=[{"name": "operator_table", "origin": "seed", "certificate": None, "provenance": HOST}],
        vocabulary=[{"name": "axis", "origin": "seed", "certificate": None}],
    )
    return Genesis(
        state=state, body_factory=seed_body,
        budget=tr.Budget(limits={"generations": 8}),
        isolation=tr.Isolation(), grade=grade,
    )

def seed_policy():
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY, operation_names=("increment",),
        max_length=1, ceiling_length=1, max_candidates=4,
    )

def world(registry):
    return controller.world(
        tasks=TASKS, demands={}, substrates={}, probe_registry=registry,
        component_operations={}, artifacts={}, grade=grade,
    )

def test_objective_policy_intent_carries_its_registry_and_conflicting_world_is_refused():
    g = genesis()
    policy_controller.admit_seed_policy(g, seed_policy())
    before_state = g.state["state_digest"]
    before_spent = dict(g.budget.spent)
    with pytest.raises(controller.ControllerError, match="produced under registry"):
        opc.run_policy(
            g, world("genesis.development_bodies:SUBSTRATE_OPERATIONS"), max_steps=1
        )
    assert g.state["state_digest"] == before_state
    assert dict(g.budget.spent) == before_spent

def test_policy_generated_candidate_records_the_same_registry_it_was_interpreted_under():
    g = genesis()
    run = opc.run_policy(g, world(bodies.PROBE_REGISTRY), seed_policy=seed_policy(), max_steps=1)
    step = run["steps"][0]
    assert step["program"]["registry_reference"] == bodies.PROBE_REGISTRY
    assert step["body_artifact"]["configuration"]["configuration"]["registry_reference"] == bodies.PROBE_REGISTRY

def test_manual_generate_transform_without_bound_registry_keeps_legacy_world_binding():
    g = genesis()
    intent = controller.GenerateTransform(name="legacy", operations=("increment",))
    outcome = controller._generate_transform(g, world(bodies.PROBE_REGISTRY), intent)
    assert outcome["generated_program"]["registry_reference"] == bodies.PROBE_REGISTRY

def test_generate_transform_intent_roundtrip_preserves_registry_identity():
    intent = controller.GenerateTransform(
        name="bound", operations=("increment",), registry_reference=bodies.PROBE_REGISTRY
    )
    rebuilt = controller._intent_from_record(controller._intent_record(intent))
    assert rebuilt == intent
