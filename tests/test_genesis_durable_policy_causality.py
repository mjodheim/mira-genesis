"""DEVELOPMENT regressions for durable policy evidence and policy-to-body causal history."""
from __future__ import annotations

from genesis import autonomous_policy_loop as auto
from genesis import controller
from genesis import development_bodies as bodies
from genesis import policies, policy_body_lineage, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="durable policy causality fixture")


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


def _genesis(*, evaluations=16):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 40,
                "policy_updates": 2,
                "policy_evaluations": evaluations,
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


def _seed_policy(*, operations=("increment", "square"), ceiling=3):
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=operations,
        max_length=1,
        ceiling_length=ceiling,
        max_candidates=32,
    )


def test_two_changed_policies_are_persistently_linked_to_the_two_bodies_they_produced(tmp_path):
    genesis = _genesis()
    campaign = auto.run_objectives(
        genesis,
        [_world(fixtures.OBJECTIVE_ONE), _world(fixtures.OBJECTIVE_TWO)],
        seed_policy=_seed_policy(),
        checkpoint_directory=tmp_path,
    )

    links = list(policy_body_lineage.links(genesis))
    assert len(links) == 2
    assert [link["generated_program"]["operations"] for link in links] == [
        ["increment", "increment"],
        ["square", "increment", "increment"],
    ]
    assert all(link["machinery_dependency"]["established"] is True for link in links)
    assert all(link["machinery_dependency"]["update_certificate_digest"] for link in links)
    assert links[0]["policy"]["max_length"] == 2
    assert links[1]["policy"]["max_length"] == 3
    assert links[1]["policy"]["parent_policy_digest"] == links[0]["policy"]["policy_digest"]
    assert links[0]["objective"]["objective_digest"] != links[1]["objective"]["objective_digest"]

    accepted_steps = [
        step
        for run in campaign["objectives"]
        for step in run["steps"]
        if step["intent"] == "GenerateTransform" and step.get("accepted")
    ]
    assert [step["policy_body_link_digest"] for step in accepted_steps] == [
        links[0]["link_digest"],
        links[1]["link_digest"],
    ]
    assert all(step["machinery_dependency"]["established"] for step in accepted_steps)

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert policy_body_lineage.links(restored) == tuple(links)
    assert isinstance(restored.body_factory, ConfiguredBody)
    assert policy_controller.bound_policy(restored)["max_length"] == 3
    assert len(retentive.bound_corpus(restored)["question_digests"]) == 3


def test_negative_policy_expansion_and_its_spent_meta_evaluation_survive_process_death(tmp_path):
    genesis = _genesis()
    here = _world(fixtures.OBJECTIVE_ONE)

    # `negate` and `negate -> negate` do not solve this objective. The policy asks for the depth-two
    # expansion after depth one is exhausted, the new shell is measured, and that update is rejected.
    run = auto.run_objective(
        genesis,
        here,
        seed_policy=_seed_policy(operations=("negate",), ceiling=2),
        max_steps=8,
        checkpoint_directory=tmp_path,
    )
    expansion = next(step for step in run["steps"] if step["intent"] == auto.EXPANSION_REQUEST)
    assert expansion["accepted"] is False
    assert expansion["checkpoint_digest"]
    assert expansion["durable_before_next_intent"] is True
    assert policy_controller.bound_policy(genesis)["max_length"] == 1
    assert genesis.budget.spent["policy_updates"] == 1
    assert genesis.budget.spent["policy_evaluations"] == 1
    assert any(
        "policy expansion measured no improving descendant" in str(entry.get("payload", {}).get("detail", ""))
        for entry in genesis.journal.of_kind("diagnosis")
    )

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert policy_controller.bound_policy(restored)["max_length"] == 1
    assert restored.budget.spent["policy_updates"] == 1
    assert restored.budget.spent["policy_evaluations"] == 1
    assert restored.journal.head == genesis.journal.head
    assert any(
        "policy expansion measured no improving descendant" in str(entry.get("payload", {}).get("detail", ""))
        for entry in restored.journal.of_kind("diagnosis")
    )
