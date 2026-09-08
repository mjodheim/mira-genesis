"""Counterexamples at the post-controller endogenous-search frontier.

These tests are DEVELOPMENT apparatus tests. A red test means the integrated runtime still claims a
continuity property more strongly than its implementation supplies; it is not a scientific result.
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
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _world():
    # A Stop intent needs no task, artifact, demand or substrate. Keeping the world empty makes the
    # counterexample about mechanism identity only rather than about some other controller service.
    return controller.world(
        tasks=(),
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=bodies.grade,
    )


def test_process_death_cannot_replace_the_lineage_controller_mechanism(tmp_path):
    """The body cannot be substituted after restore; lineage-owned acquisition machinery cannot either.

    Today `controller.run` records the supplied mechanism artifact in its run record but neither the
    state nor the checkpoint owns that identity. The same persisted lineage can therefore be resumed
    under a different callback with no adoption or re-admission transaction.
    """
    genesis = _genesis()
    first = controller.run(genesis, _world(), fixtures.stop_as_alpha, max_steps=1)
    assert first["mechanism_artifact_digest"] == tr.artifact_digest_of(fixtures.stop_as_alpha)[
        "artifact_digest"
    ]
    genesis.persist(tmp_path)

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.parent_body,
        grade=bodies.grade,
    )

    with pytest.raises((controller.ControllerError, tr.TrustRootError), match="mechanism|admit|lineage"):
        controller.run(restored, _world(), fixtures.stop_as_beta, max_steps=1)


def test_a_checkpoint_binds_the_lineage_owned_decision_machinery_after_it_runs():
    """A run record is not persistence: the next process needs a committed identity to resume."""
    genesis = _genesis()
    controller.run(genesis, _world(), fixtures.stop_as_alpha, max_steps=1)
    checkpoint = genesis.checkpoint()

    assert checkpoint.get("mechanism_artifact") == tr.artifact_digest_of(fixtures.stop_as_alpha)
