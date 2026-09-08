"""Counterexamples for provenance and discovered-substrate boundaries.

These tests keep separate two claims that are easy to blur: content addressing tells us whether a
record changed; provenance tells us who was entitled to create it; discovery tells the lineage what
it actually learned rather than everything the host already knew.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import migration as mg
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis


LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")


def _seed_state(**overrides):
    arguments = {
        "body_digest": "b0",
        "components": [
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        "vocabulary": [{"name": "axis_progress", "origin": "seed", "certificate": None}],
    }
    arguments.update(overrides)
    return st.create_state(**arguments)


def _vocabulary_certificate():
    return st.vocabulary_extension_certificate(
        prior_vocabulary=["axis_progress"],
        new_feature="requires_joint",
        demand_digests=["d1", "d2"],
        shared_prior_row=[False],
        limiting_components=["a", "b"],
        separated_rows=[[False, True], [False, False]],
    )


def test_an_acquired_vocabulary_entry_records_who_produced_it():
    extended = st.extend_vocabulary(_seed_state(), certificate=_vocabulary_certificate())
    acquired = extended["vocabulary"][-1]
    assert acquired["origin"] == "acquired"
    assert acquired["provenance"]["class"] == "lineage_owned"


def test_arbitrary_acquisition_records_without_provenance_are_refused():
    with pytest.raises(st.StateError, match="provenance"):
        _seed_state(acquisitions=[{"name": "history_inserted_without_a_producer"}])


def _read(task):
    return task


def _undiscovered(task):
    return task


def test_lineage_visible_substrate_record_does_not_reveal_operations_never_discovered():
    genesis = Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    substrate = mg.Substrate(
        name="hidden-capability-substrate",
        operations={"read": _read, "undiscovered_secret": _undiscovered},
    )
    assert substrate.probe("read") is True

    mg.migrate(
        genesis,
        substrate,
        lambda _state, _operations: bodies.parent_body,
        used_operations=["read"],
        tasks=None,
    )

    migration_entry = genesis.journal.of_kind("migration")[-1]
    visible = migration_entry["payload"]["substrate"]
    assert visible["operations_discovered"] == ["read"]
    assert "undiscovered_secret" not in visible.get("operations_available", [])
