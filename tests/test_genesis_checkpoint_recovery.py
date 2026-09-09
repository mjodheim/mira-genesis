"""Checkpointing must preserve the last committed lineage across an interrupted next write."""
from __future__ import annotations

from pathlib import Path

import pytest

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal

LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _genesis(*, isolation=None):
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
        budget=tr.Budget(limits={"generations": 3}),
        isolation=isolation or tr.Isolation(),
        grade=bodies.grade,
    )


def test_interrupted_next_persist_leaves_previous_checkpoint_recoverable(tmp_path, monkeypatch):
    """Publishing the manifest last is useful only if the old manifest still has its old payloads."""
    genesis = _genesis()
    genesis.persist(tmp_path)
    committed_state = genesis.state["state_digest"]
    committed_head = genesis.journal.head

    def propose(*_):
        return Proposal(
            name="improved",
            body_factory=bodies.improved_body,
            provenance=LINEAGE,
            rationale={"why": "create a second checkpoint candidate"},
        )

    assert genesis.cycle(TASKS, propose)["accepted"] is True

    real_replace = Path.replace

    def crash_before_manifest_publish(path, target):
        if path.name.startswith("runtime_checkpoint") and path.suffix == ".partial":
            raise RuntimeError("simulated process death before manifest publish")
        return real_replace(path, target)

    monkeypatch.setattr(Path, "replace", crash_before_manifest_publish)
    with pytest.raises(RuntimeError, match="simulated process death"):
        genesis.persist(tmp_path)
    monkeypatch.setattr(Path, "replace", real_replace)

    restored = Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)
    assert restored.state["state_digest"] == committed_state
    assert restored.journal.head == committed_head


def test_restore_preserves_current_isolation_without_forgetting_the_admitted_ceiling(tmp_path):
    """A narrowed lineage may not wake up at the wider ceiling merely because that ceiling was admitted."""
    admitted = tr.Isolation(cpu_seconds=30.0, memory_bytes=512 * 1024 * 1024, wall_clock_seconds=60.0)
    narrowed = tr.Isolation(cpu_seconds=5.0, memory_bytes=256 * 1024 * 1024, wall_clock_seconds=20.0)
    genesis = _genesis(isolation=admitted)
    narrowed.assert_no_wider_than(genesis.admitted_isolation)
    genesis.isolation = narrowed
    genesis.persist(tmp_path)

    restored = Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)
    assert restored.isolation.record() == narrowed.record()
    assert restored.admitted_isolation.record() == admitted.record()
