"""Lineage-owned controller code is untrusted even when its input is a frozen value."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import hostile_fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis


def _genesis():
    state = st.create_state(
        body_digest="seed",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )
    return Genesis(
        state=state,
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 1}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def test_lineage_mechanism_cannot_mutate_evaluator_module_state():
    """A frozen context prevents reference writes; only a process boundary removes ambient authority."""
    hostile_fixtures.MECHANISM_SIDE_EFFECT = 0
    genesis = _genesis()
    here = controller.world(
        tasks=[{"task_id": "t0", "input": 0}],
        demands={},
        substrates={},
        probe_registry="genesis.development_bodies:PROBE_OPERATIONS",
        component_operations={},
        artifacts={},
        grade=bodies.grade,
    )

    record = controller.run(genesis, here, hostile_fixtures.mutating_mechanism, max_steps=1)

    assert hostile_fixtures.MECHANISM_SIDE_EFFECT == 0
    assert record["mechanism_execution_isolated"] is True
    assert record["mechanism_artifact_digest"]
