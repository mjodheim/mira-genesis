"""DEVELOPMENT regressions for continuous runtime-owned policy evolution."""
from __future__ import annotations

import pytest

from genesis import autonomous_policy_loop as auto
from genesis import controller
from genesis import development_bodies as bodies
from genesis import policies, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="autonomous-policy-loop fixture")


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


def _genesis(*, policy_updates=2):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 40,
                "policy_updates": policy_updates,
                "policy_evaluations": 16,
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


def _seed_policy(*, ceiling=3, operations=("increment", "square")):
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=operations,
        max_length=1,
        ceiling_length=ceiling,
        max_candidates=32,
    )


def test_one_runtime_campaign_sequences_two_policy_updates_and_two_body_changes(tmp_path):
    genesis = _genesis()
    campaign = auto.run_objectives(
        genesis,
        [_world(fixtures.OBJECTIVE_ONE), _world(fixtures.OBJECTIVE_TWO)],
        seed_policy=_seed_policy(),
        max_steps_per_objective=32,
        checkpoint_directory=tmp_path,
    )

    steps = [step for run in campaign["objectives"] for step in run["steps"]]
    expansions = [step for step in steps if step["intent"] == auto.EXPANSION_REQUEST]
    accepted_bodies = [
        step
        for step in steps
        if step["intent"] == "GenerateTransform" and step.get("accepted")
    ]

    # No launcher alternates run/expand calls: one campaign call reached both evidence-backed
    # machinery changes because the isolated policy requested them after its own search exhausted.
    assert len(expansions) == 2
    assert [step["requested_max_length"] for step in expansions] == [2, 3]
    assert all(step["accepted"] is True for step in expansions)
    assert [step["program"]["operations"] for step in accepted_bodies] == [
        ["increment", "increment"],
        ["square", "increment", "increment"],
    ]
    assert expansions[0]["objective_digest"] != expansions[1]["objective_digest"]
    assert expansions[1]["prior_policy_digest"] == expansions[0]["update"]["candidate_policy"][
        "policy_digest"
    ]

    assert isinstance(genesis.body_factory, ConfiguredBody)
    assert genesis.body_factory.configuration["operations"] == (
        "square",
        "increment",
        "increment",
    )
    assert policy_controller.bound_policy(genesis)["max_length"] == 3
    assert len(retentive.bound_corpus(genesis)["question_digests"]) == 3
    assert all(
        step.get("durable_before_next_intent") is True
        for step in accepted_bodies
    )

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert restored.body_factory.configuration["operations"] == (
        "square",
        "increment",
        "increment",
    )
    assert policy_controller.bound_policy(restored)["max_length"] == 3
    assert len(retentive.bound_corpus(restored)["question_digests"]) == 3

    # The runtime-owned loop cannot evade cross-objective retention after restart either.
    with pytest.raises(retentive.RetentionObjectiveError, match="retained"):
        auto.run_objective(restored, _world(fixtures.OBJECTIVE_ONE), max_steps=1)


def test_policy_at_its_admitted_ceiling_stops_instead_of_inventing_more_machinery():
    genesis = _genesis(policy_updates=0)
    run = auto.run_objective(
        genesis,
        _world(fixtures.OBJECTIVE_ONE),
        seed_policy=_seed_policy(ceiling=1, operations=("increment", "square")),
        max_steps=6,
    )

    assert [step["intent"] for step in run["steps"]][-1] == "stop"
    assert run["steps"][-1]["reason"] == "policy search exhausted at its admitted depth ceiling"
    assert not any(step["intent"] == auto.EXPANSION_REQUEST for step in run["steps"])
    assert policy_controller.bound_policy(genesis)["max_length"] == 1


def test_exhaustion_request_cannot_expand_without_a_prospective_update_budget():
    genesis = _genesis(policy_updates=0)
    with pytest.raises(Exception, match="policy_updates"):
        auto.run_objective(
            genesis,
            _world(fixtures.OBJECTIVE_ONE),
            seed_policy=_seed_policy(),
            max_steps=6,
        )
    assert policy_controller.bound_policy(genesis)["max_length"] == 1
