"""Round-two persistence/lineage-identity counterexamples."""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis
from genesis.migration import Substrate, discover, migrate

HOST = tr.provenance("host_written", produced_by="round-two persistence test")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _seed_state():
    return st.create_state(
        body_digest="b0",
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


def _genesis(*, isolation=None):
    return Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 4, "probes": 20}),
        isolation=isolation or tr.Isolation(),
        grade=bodies.grade,
    )


def test_restore_preserves_the_committed_current_isolation_not_only_the_admitted_ceiling(tmp_path):
    """A restart must not widen a runtime that had already narrowed its own current envelope."""
    genesis = _genesis()
    narrowed = tr.Isolation(
        cpu_seconds=5.0,
        memory_bytes=128 * 1024 * 1024,
        wall_clock_seconds=10.0,
        filesystem_writes_permitted=False,
        network_permitted=False,
        subprocess_permitted=False,
    )
    genesis.isolation = narrowed
    genesis.persist(tmp_path)

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.parent_body,
        grade=bodies.grade,
    )
    assert restored.isolation.record() == narrowed.record()


def test_crash_before_manifest_publish_can_restore_the_previous_committed_checkpoint(tmp_path):
    """Commit-last only works if the old manifest still points to payloads that still exist."""
    genesis = _genesis()
    genesis.persist(tmp_path)
    committed_state_digest = genesis.state["state_digest"]
    committed_journal_head = genesis.journal.head

    # Move the in-memory lineage forward, then simulate only the first write of `persist()` landing
    # before process death. The old manifest remains the last commit point. A transactional store
    # must therefore still be able to resolve the payloads named by that old manifest.
    genesis.cycle(TASKS, lambda *_: None)
    assert genesis.journal.head != committed_journal_head
    st.save_state(genesis.state, tmp_path / "lineage_state.json")

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.parent_body,
        grade=bodies.grade,
    )
    assert restored.state["state_digest"] == committed_state_digest
    assert restored.journal.head == committed_journal_head


def _migrated_with(factory):
    genesis = _genesis()
    genesis.cycle(TASKS, lambda *_: None)
    substrate = Substrate(name="record-store", operations=bodies.SUBSTRATE_OPERATIONS)
    discover(substrate, ["read"], genesis.budget)
    record = migrate(
        genesis,
        substrate,
        lambda _state, _operations: factory,
        used_operations=["read"],
        tasks=TASKS,
        translation_provenance=HOST,
    )
    return genesis, record


def test_migration_arrival_state_identity_binds_the_translated_executable_body():
    """Two distinct executable translations must not create the same arrival-state identity."""
    assert tr.artifact_digest_of(bodies.migrated_parent_body)["artifact_digest"] != tr.artifact_digest_of(
        bodies.migrated_uncoupled_ablation_body
    )["artifact_digest"]

    left, left_record = _migrated_with(bodies.migrated_parent_body)
    right, right_record = _migrated_with(bodies.migrated_uncoupled_ablation_body)

    # The two fixtures are behaviourally equal on the migration verification set but are distinct
    # executable artifacts. Lineage identity must still distinguish which body actually arrived.
    assert left_record["arrival_state_digest"] != right_record["arrival_state_digest"]
    assert left.state["body_digest"] != right.state["body_digest"]


def test_vocabulary_extension_cannot_default_host_orchestration_to_lineage_owned_provenance():
    """Who invoked an extension is evidence; the API must not invent lineage ownership by default."""
    state = _seed_state()
    certificate = st.vocabulary_extension_certificate(
        prior_vocabulary=["axis_progress"],
        new_feature="requires_increment",
        demand_digests=["d0", "d1"],
        shared_prior_row=[False],
        limiting_components=["operator_table", "other_component"],
        separated_rows=[[False, False], [False, True]],
    )
    with pytest.raises((st.StateError, tr.TrustRootError), match="provenance|producer"):
        st.extend_vocabulary(state, certificate=certificate)
