"""Counterexamples and regressions at the post-controller endogenous-search frontier.

These are DEVELOPMENT apparatus tests. They establish continuity and authority properties of the
integrated runtime; they are not scientific evidence about generality.
"""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import endogenous_frontier_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="endogenous-frontier fixture")
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
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _genesis():
    return Genesis(
        state=_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 8, "probes": 100}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _empty_world():
    # A Stop intent needs no task, artifact, demand or substrate. Keeping the world empty makes the
    # mechanism-continuity tests about identity only rather than about some other controller service.
    return controller.world(
        tasks=(),
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=bodies.grade,
    )


def _transform_world():
    return controller.world(
        tasks=TASKS,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={"regressed": "genesis.development_bodies:regressed_body"},
        grade=bodies.grade,
    )


def test_process_death_cannot_replace_the_lineage_controller_mechanism(tmp_path):
    """The body cannot be substituted after restore; acquisition machinery cannot either."""
    genesis = _genesis()
    first = controller.run(genesis, _empty_world(), fixtures.stop_as_alpha, max_steps=1)
    alpha = tr.artifact_digest_of(fixtures.stop_as_alpha)
    assert first["mechanism_artifact_digest"] == alpha["artifact_digest"]
    assert controller.bound_mechanism_artifact(genesis) == alpha
    genesis.persist(tmp_path)

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.parent_body,
        grade=bodies.grade,
    )
    assert controller.bound_mechanism_artifact(restored) == alpha

    with pytest.raises((controller.ControllerError, tr.TrustRootError), match="mechanism|machinery|admit|lineage"):
        controller.run(restored, _empty_world(), fixtures.stop_as_beta, max_steps=1)


def test_checkpoint_transitively_binds_the_lineage_owned_decision_machinery():
    """The mechanism is held in state, and the checkpoint commits that state digest."""
    genesis = _genesis()
    controller.run(genesis, _empty_world(), fixtures.stop_as_alpha, max_steps=1)
    artifact = controller.bound_mechanism_artifact(genesis)
    checkpoint = genesis.checkpoint()

    assert artifact == tr.artifact_digest_of(fixtures.stop_as_alpha)
    tools = [tool for tool in genesis.state["tools"] if tool.get("role") == "acquisition_policy"]
    assert len(tools) == 1
    assert tools[0]["artifact"] == artifact
    assert checkpoint["state_digest"] == genesis.state["state_digest"]


def test_isolated_mechanism_can_condition_its_next_intent_on_retained_rejection_evidence():
    """A retained failure must be readable as inert evidence, not merely increment a counter."""
    genesis = _genesis()
    run = controller.run(
        genesis,
        _transform_world(),
        fixtures.react_to_rejection,
        max_steps=3,
    )

    assert run["steps"][0]["intent"] == "Transform"
    assert run["steps"][0]["accepted"] is False
    assert run["steps"][1]["intent"] == "stop"
    assert "retained rejection" in run["steps"][1]["reason"]
    context = controller._controller_context(genesis)
    assert any(
        evidence.get("kind") == "observation"
        and (evidence.get("record") or {}).get("kind") == "rejected_candidate"
        for evidence in context.evidence
    )


def test_controller_makes_each_handled_step_durable_before_the_next_intent(tmp_path):
    """A crash after one step must resume that step, not the checkpoint from before the campaign."""
    genesis = _genesis()
    run = controller.run(
        genesis,
        _transform_world(),
        fixtures.always_regress,
        max_steps=1,
        checkpoint_directory=tmp_path,
    )
    committed_state = genesis.state["state_digest"]
    committed_head = genesis.journal.head

    assert run["durable_step_persistence"] is True
    assert run["steps"][0]["durable_before_next_intent"] is True
    assert run["steps"][0]["checkpoint_digest"]

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.parent_body,
        grade=bodies.grade,
    )
    assert restored.state["state_digest"] == committed_state
    assert restored.journal.head == committed_head
    assert controller.bound_mechanism_artifact(restored) == tr.artifact_digest_of(
        fixtures.always_regress
    )
    assert any(item.get("kind") == "rejected_candidate" for item in restored.state["observations"])
