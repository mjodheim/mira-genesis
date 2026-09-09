"""DEVELOPMENT integration tests for the frozen M107 -> Genesis bridge."""
from __future__ import annotations

from genesis import m107_bridge as bridge
from genesis import recovery
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody, derive_ablation
from genesis.loop import Genesis
from genesis.sandbox import run_candidate
from metamorphosis import m107_runtime as m107

HOST = tr.provenance("host_written", produced_by="Genesis M107 bridge DEVELOPMENT harness")


def _genesis() -> Genesis:
    factory = bridge.seed_body_factory()
    return Genesis(
        state=st.create_state(
            body_digest=tr.artifact_digest_of(factory)["artifact_digest"],
            components=[
                {
                    "name": "operator_table",
                    "origin": "seed",
                    "certificate": None,
                    "provenance": HOST,
                }
            ],
            vocabulary=[
                {
                    "name": "resolvable_by_operator_table",
                    "origin": "seed",
                    "certificate": None,
                }
            ],
        ),
        body_factory=factory,
        budget=tr.Budget(limits={"generations": 4, "probes": 100}),
        isolation=tr.Isolation(),
        grade=bridge.grade,
    )


def _solved(run):
    return sum(1 for row in run["outcomes"] if row["outcome"] == "solved")


def test_frozen_m107_acquisition_replays_as_the_same_4_to_16_reach_change():
    replay = bridge.replay_frozen_acquisition()

    assert replay["confirmed"] is True
    assert replay["development_replay_only"] is True
    assert replay["base_image_size"] == 4
    assert replay["extended_image_size"] == 16
    assert replay["operator_space_exhausted"] is True
    assert replay["source_authorship"] == "project_controlled_not_independent_task_evidence"

    seed = m107.create_state()
    acquired = m107.decode_state(replay["next_state"])
    assert len(m107.complete_image(seed["operators"])) == 4
    assert len(m107.complete_image(acquired["operators"])) == 16


def test_configured_body_ablation_removes_only_the_m107_dependency_and_restores_s0():
    replay = bridge.replay_frozen_acquisition()
    candidate = bridge.acquired_body_factory(replay)
    ablated = derive_ablation(candidate, bridge.ACQUISITION_NAME)

    assert isinstance(candidate, ConfiguredBody)
    assert candidate.target == ablated.target
    assert dict(candidate.configuration) == dict(ablated.configuration)
    assert candidate.dependencies - ablated.dependencies == {bridge.ACQUISITION_NAME}

    with_extension = candidate()
    without_extension = ablated()
    assert len(m107.complete_image(with_extension.state["operators"])) == 16
    assert m107.encode_state(without_extension.state) == m107.encode_state(m107.create_state())


def test_genesis_trust_root_accepts_the_real_m107_extension_under_parent_side_grading():
    genesis = _genesis()
    result = genesis.cycle(bridge.evaluation_tasks(), bridge.propose_frozen_m107_extension)

    assert result["accepted"] is True
    assert result["outcomes_are_self_reported"] is False
    assert _solved(result["parent_sandbox"]) == 4
    assert _solved(result["candidate_sandbox"]) == 12
    assert result["causal_dependency"]["established"] is False
    assert "first acquisition depends on nothing earlier" in result["causal_dependency"]["why"]
    assert genesis.state["generation"] == 1
    assert [item["name"] for item in genesis.state["acquisitions"]] == [
        bridge.ACQUISITION_NAME
    ]


def test_runtime_derived_ablation_loses_exactly_the_new_m107_reach():
    tasks = bridge.evaluation_tasks()
    candidate = bridge.acquired_body_factory()
    ablated = derive_ablation(candidate, bridge.ACQUISITION_NAME)

    with_extension = run_candidate(
        candidate,
        tasks,
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=bridge.grade,
    )
    without_extension = run_candidate(
        ablated,
        tasks,
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=bridge.grade,
    )
    seed = run_candidate(
        bridge.seed_body_factory(),
        tasks,
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=bridge.grade,
    )

    assert with_extension["completed"] is True
    assert without_extension["completed"] is True
    assert seed["completed"] is True
    assert _solved(with_extension) == 12
    assert _solved(without_extension) == 4
    assert without_extension["outcomes"] == seed["outcomes"]


def test_accepted_m107_body_survives_genesis_process_death_restore(tmp_path):
    genesis = _genesis()
    result = genesis.cycle(bridge.evaluation_tasks(), bridge.propose_frozen_m107_extension)
    assert result["accepted"] is True
    genesis.persist(tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=bridge.grade)

    assert isinstance(restored.body_factory, ConfiguredBody)
    assert tr.artifact_digest_of(restored.body_factory) == tr.artifact_digest_of(
        genesis.body_factory
    )
    assert restored.state["state_digest"] == genesis.state["state_digest"]
    assert restored.journal.head == genesis.journal.head

    run = run_candidate(
        restored.body_factory,
        bridge.evaluation_tasks(),
        restored.isolation,
        admitted_isolation=restored.admitted_isolation,
        grade=bridge.grade,
    )
    assert run["completed"] is True
    assert _solved(run) == 12
