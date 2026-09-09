"""DEVELOPMENT integration tests for the M109 -> Genesis two-generation machinery bridge."""
from __future__ import annotations

from pathlib import Path

import pytest

from genesis import m109_bridge as bridge
from genesis import recovery
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody, derive_ablation
from genesis.loop import Genesis
from genesis.sandbox import run_candidate
from metamorphosis import m109_runtime as m109

HOST = tr.provenance(
    "host_written", produced_by="Genesis M109 bridge DEVELOPMENT harness"
)


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
                },
                {
                    "name": "signal_interface",
                    "origin": "seed",
                    "certificate": None,
                    "provenance": HOST,
                },
                {
                    "name": "candidate_space",
                    "origin": "seed",
                    "certificate": None,
                    "provenance": HOST,
                },
            ],
            vocabulary=[
                {
                    "name": "reach_improve_membership",
                    "origin": "seed",
                    "certificate": None,
                }
            ],
        ),
        body_factory=factory,
        budget=tr.Budget(limits={"generations": 4, "probes": 10000}),
        isolation=tr.Isolation(),
        grade=bridge.grade,
    )


def _solved(run: dict) -> int:
    return sum(1 for row in run["outcomes"] if row["outcome"] == "solved")


def _two_generations() -> tuple[Genesis, dict, dict]:
    genesis = _genesis()
    tasks = bridge.evaluation_tasks()
    first = genesis.cycle(tasks, bridge.propose_generation_one)
    assert first["accepted"] is True
    second = genesis.cycle(tasks, bridge.propose_generation_two)
    return genesis, first, second


def test_generation_one_replay_never_reads_stage_two(monkeypatch: pytest.MonkeyPatch):
    touched: list[Path] = []
    original = Path.read_bytes
    stage1 = bridge.STAGE1_PATH.resolve()
    stage2 = bridge.STAGE2_PATH.resolve()

    def guarded(self: Path) -> bytes:
        resolved = self.resolve()
        touched.append(resolved)
        if resolved == stage2:
            raise AssertionError("generation one touched M109 stage two")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    replay = bridge.replay_generation_one()

    assert replay["confirmed"] is True
    assert stage1 in touched
    assert stage2 not in touched
    assert replay["stage_one_resolution"]["confirmed"] is True


def test_frozen_m109_replay_reproduces_two_lineage_determined_generations():
    first = bridge.replay_generation_one()
    second = bridge.replay_generation_two(first)

    assert first["confirmed"] is True
    assert second["confirmed"] is True
    assert first["selected_component"] == m109.COMPONENT_SIGNALS
    assert second["selected_component"] == m109.COMPONENT_CANDIDATES
    assert first["surviving_rule_classes"] == 1
    assert second["surviving_rule_classes"] == 1
    assert first["episode1"]["trial"]["label_source"] == "lineage_component_trial"
    assert second["episode2"]["trial"]["label_source"] == "lineage_component_trial"
    assert first["adopted_rule"]["rule_id"] != second["adopted_rule"]["rule_id"]
    assert second["generation_two_inexpressible_before_generation_one"] is True
    assert second["stage_two_before_generation_two"]["confirmed"] is False
    assert second["stage_two_resolution"]["confirmed"] is True


def test_reach_census_is_complete_and_exactly_6_20_243():
    tasks = bridge.evaluation_tasks()
    first = bridge.replay_generation_one()
    second = bridge.replay_generation_two(first)

    assert len(tasks) == 256
    assert len({task["table"] for task in tasks}) == 256
    assert len({task["task_id"] for task in tasks}) == 256
    assert first["reach_m0"]["size"] == 6
    assert first["reach_m1"]["size"] == 20
    assert second["reach_m2"]["size"] == 243

    m0 = set(first["reach_m0"]["tables"])
    m1 = set(first["reach_m1"]["tables"])
    m2 = set(second["reach_m2"]["tables"])
    assert m0 < m1 < m2
    assert len(m1 - m0) == 14
    assert len(m2 - m1) == 223


def test_two_genesis_cycles_measure_6_to_20_to_243_and_one_contiguous_link():
    genesis, first, second = _two_generations()

    assert _solved(first["parent_sandbox"]) == 6
    assert _solved(first["candidate_sandbox"]) == 20
    assert first["causal_dependency"]["established"] is False

    assert second["accepted"] is True
    assert second["outcomes_are_self_reported"] is False
    assert _solved(second["parent_sandbox"]) == 20
    assert _solved(second["candidate_sandbox"]) == 243
    causal = second["causal_dependency"]
    assert causal["established"] is True
    assert causal["depends_on"] == bridge.GENERATION_ONE
    assert causal["solved_with_acquisition"] == 243
    assert causal["solved_without_acquisition"] == 6
    assert len(causal["newly_solved_with_acquisition"]) == 223
    assert len(causal["newly_solved_lost_without_acquisition"]) == 223
    assert causal["newly_solved_lost_without_acquisition"] == causal[
        "newly_solved_with_acquisition"
    ]

    assert genesis.state["generation"] == 2
    assert [item["name"] for item in genesis.state["acquisitions"]] == [
        bridge.GENERATION_ONE,
        bridge.GENERATION_TWO,
    ]
    chain = genesis.causal_chain()
    assert chain["acquisitions"] == 2
    assert chain["established_links"] == 1
    assert chain["makes_no_recursion_claim"] is True


def test_derived_generation_one_ablation_collapses_m2_new_work_to_m0():
    replay = bridge.replay_generation_two()
    candidate = bridge.generation_two_body_factory(replay)
    ablated = derive_ablation(candidate, bridge.GENERATION_ONE)

    assert isinstance(candidate, ConfiguredBody)
    assert candidate.target == ablated.target
    assert dict(candidate.configuration) == dict(ablated.configuration)
    assert bridge.GENERATION_TWO in ablated.dependencies
    assert bridge.GENERATION_ONE not in ablated.dependencies

    tasks = bridge.evaluation_tasks()
    intact = run_candidate(
        candidate,
        tasks,
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=bridge.grade,
    )
    without_predecessor = run_candidate(
        ablated,
        tasks,
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=bridge.grade,
    )
    assert intact["completed"] is True
    assert without_predecessor["completed"] is True
    assert _solved(intact) == 243
    assert _solved(without_predecessor) == 6

    m1 = set(replay["reach_m1"]["tables"])
    m2 = set(replay["reach_m2"]["tables"])
    new_tables = m2 - m1
    outcomes = {row["task_id"]: row["outcome"] for row in without_predecessor["outcomes"]}
    task_for_table = {task["table"]: task["task_id"] for task in tasks}
    assert len(new_tables) == 223
    assert all(outcomes[task_for_table[table]] != "solved" for table in new_tables)


def test_removing_only_generation_two_restores_the_m1_reach_snapshot():
    candidate = bridge.generation_two_body_factory()
    without_second = derive_ablation(candidate, bridge.GENERATION_TWO)

    assert without_second.dependencies == frozenset({bridge.GENERATION_ONE})
    assert dict(candidate.configuration) == dict(without_second.configuration)

    run = run_candidate(
        without_second,
        bridge.evaluation_tasks(),
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=bridge.grade,
    )
    assert run["completed"] is True
    assert _solved(run) == 20


def test_m109_two_generation_lineage_survives_process_death_restore(tmp_path: Path):
    genesis, _, second = _two_generations()
    assert second["accepted"] is True
    genesis.persist(tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=bridge.grade)

    assert isinstance(restored.body_factory, ConfiguredBody)
    assert tr.artifact_digest_of(restored.body_factory) == tr.artifact_digest_of(
        genesis.body_factory
    )
    assert restored.state["state_digest"] == genesis.state["state_digest"]
    assert restored.journal.head == genesis.journal.head
    assert restored.causal_chain()["established_links"] == 1

    run = run_candidate(
        restored.body_factory,
        bridge.evaluation_tasks(),
        restored.isolation,
        admitted_isolation=restored.admitted_isolation,
        grade=bridge.grade,
    )
    assert run["completed"] is True
    assert _solved(run) == 243


def test_m109_body_fails_closed_on_a_non_census_task():
    body = bridge.seed_body_factory()()
    with pytest.raises(bridge.M109BridgeError, match="census row"):
        body.attempt({"task_id": "bad", "table": "0101"})
