"""DEVELOPMENT regressions for self-contained process-death restoration of generated bodies."""
from __future__ import annotations

import json

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import endogenous_frontier_fixtures as fixtures
from genesis import programs
from genesis import recovery
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="generated-restore fixture")
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
            },
            {
                "name": "signal_interface",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            },
        ],
        vocabulary=[
            {"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None},
            {"name": "resolvable_by_signal_interface", "origin": "seed", "certificate": None},
        ],
    )


def _genesis():
    return Genesis(
        state=_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 8, "probes": 100}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _world():
    return controller.world(
        tasks=TASKS,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        artifacts={},
        grade=bodies.grade,
    )


def _persist_generated(tmp_path):
    genesis = _genesis()
    run = controller.run(
        genesis,
        _world(),
        fixtures.generated_search_policy,
        max_steps=6,
        checkpoint_directory=tmp_path,
    )
    assert run["final_generation"] == 1
    assert isinstance(genesis.body_factory, ConfiguredBody)
    return genesis


def test_generated_descendant_restores_without_a_caller_supplied_body_factory(tmp_path):
    original = _persist_generated(tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=bodies.grade)

    assert restored.state["state_digest"] == original.state["state_digest"]
    assert restored.journal.head == original.journal.head
    assert isinstance(restored.body_factory, ConfiguredBody)
    assert restored.body_factory.target == programs.PROGRAM_TARGET
    # Reconstruction restores the same frozen executable artifact, not a mutable caller-facing list.
    assert restored.body_factory.configuration["operations"] == ("double", "increment")
    assert tr.artifact_digest_of(restored.body_factory) == tr.artifact_digest_of(
        original.body_factory
    )
    assert controller.bound_mechanism_artifact(restored) == controller.bound_mechanism_artifact(
        original
    )


def test_restored_generated_descendant_is_still_executable_under_the_same_measure(tmp_path):
    _persist_generated(tmp_path)
    restored = recovery.restore_lineage(tmp_path, grade=bodies.grade)

    # The policy sees that a generated acquisition already exists and stops. More importantly, the
    # restored body needs no host reconstruction to remain the current executable descendant.
    run = controller.run(
        restored,
        _world(),
        fixtures.generated_search_policy,
        max_steps=1,
    )
    assert run["steps"] == [{"intent": "stop", "reason": "a generated descendant was adopted"}]


def test_recovery_refuses_a_resealed_manifest_whose_program_data_no_longer_matches_body_identity(tmp_path):
    _persist_generated(tmp_path)
    path = tmp_path / "runtime_checkpoint.json"
    manifest = json.loads(path.read_bytes().decode("utf-8"))
    manifest["body_artifact"]["configuration"]["configuration"]["operations"] = ["increment"]
    payload = {key: value for key, value in manifest.items() if key != "checkpoint_digest"}
    manifest["checkpoint_digest"] = tr.digest_of(payload)
    path.write_bytes(tr.canonical_bytes(manifest) + b"\n")

    with pytest.raises(tr.TrustRootError, match="cannot be reconstructed|does not reproduce"):
        recovery.restore_lineage(tmp_path, grade=bodies.grade)


def test_plain_importable_seed_body_is_also_reconstructible(tmp_path):
    genesis = _genesis()
    genesis.persist(tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=bodies.grade)
    assert restored.body_factory is bodies.parent_body
    assert restored.state["state_digest"] == genesis.state["state_digest"]
