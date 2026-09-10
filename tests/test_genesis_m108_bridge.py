"""DEVELOPMENT integration tests for the M108 -> Genesis machinery bridge."""
from __future__ import annotations

from genesis import m107_bridge
from genesis import m108_bridge
from genesis import recovery
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody, derive_ablation
from genesis.loop import Genesis
from genesis.sandbox import run_candidate
from metamorphosis import m107_runtime as m107
from metamorphosis import m108_runtime as m108

HOST = tr.provenance("host_written", produced_by="Genesis M108 bridge DEVELOPMENT harness")


def _genesis() -> Genesis:
    factory = m107_bridge.seed_body_factory()
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
            ],
            vocabulary=[
                {
                    "name": "resolvable_by_operator_table",
                    "origin": "seed",
                    "certificate": None,
                },
                {
                    "name": "resolvable_by_signal_interface",
                    "origin": "seed",
                    "certificate": None,
                },
            ],
        ),
        body_factory=factory,
        budget=tr.Budget(limits={"generations": 6, "probes": 200}),
        isolation=tr.Isolation(),
        grade=m107_bridge.grade,
    )


def _solved(run):
    return sum(1 for row in run["outcomes"] if row["outcome"] == "solved")


def _two_generations() -> tuple[Genesis, dict, dict]:
    genesis = _genesis()
    first = genesis.cycle(
        m107_bridge.evaluation_tasks(), m107_bridge.propose_frozen_m107_extension
    )
    assert first["accepted"] is True
    second = genesis.cycle(
        m108_bridge.evaluation_tasks(), m108_bridge.propose_frozen_m108_attribution
    )
    return genesis, first, second


def test_frozen_m108_history_reproduces_a_rule_that_structurally_requires_m107():
    replay = m108_bridge.replay_frozen_attribution()

    assert replay["confirmed"] is True
    assert replay["development_replay_only"] is True
    assert replay["pre_m107_rule_space_size"] == 4
    assert replay["m107_enabled_rule_space_size"] == 16
    assert replay["surviving_attribution_classes"] == 1
    assert replay["attribution_domain_covered"] is True
    assert replay["every_consistent_rule_is_non_monotone"] is True
    assert replay["hardwired_resolution_confirmed"] is False
    assert replay["corrected_resolution_confirmed"] is True

    m1 = m108.decode_state(replay["next_state"])
    predecessor = m107.decode_state(m107_bridge.replay_frozen_acquisition()["next_state"])
    assert m108.canonical_json(m1["operators"]) == m108.canonical_json(
        predecessor["operators"]
    )


def test_second_genesis_generation_is_accepted_and_establishes_a_real_m107_dependency():
    genesis, first, second = _two_generations()

    assert first["causal_dependency"]["established"] is False
    assert second["accepted"] is True
    assert second["outcomes_are_self_reported"] is False
    assert _solved(second["parent_sandbox"]) == 12
    assert _solved(second["candidate_sandbox"]) == 20
    assert second["causal_dependency"]["established"] is True
    assert second["causal_dependency"]["depends_on"] == m107_bridge.ACQUISITION_NAME
    assert second["causal_dependency"]["solved_with_acquisition"] == 20
    assert second["causal_dependency"]["solved_without_acquisition"] == 4
    assert second["causal_dependency"]["ablated_arm_differs_from_the_parent_arm"] is True

    assert genesis.state["generation"] == 2
    assert [item["name"] for item in genesis.state["acquisitions"]] == [
        m107_bridge.ACQUISITION_NAME,
        m108_bridge.ACQUISITION_NAME,
    ]
    chain = genesis.causal_chain()
    assert chain["acquisitions"] == 2
    assert chain["established_links"] == 1
    assert chain["makes_no_recursion_claim"] is True


def test_removing_m107_from_the_m108_body_leaves_configuration_fixed_but_collapses_reach():
    candidate = m108_bridge.acquired_body_factory()
    ablated = derive_ablation(candidate, m107_bridge.ACQUISITION_NAME)

    assert isinstance(candidate, ConfiguredBody)
    assert candidate.target == ablated.target
    assert dict(candidate.configuration) == dict(ablated.configuration)
    assert m108_bridge.ACQUISITION_NAME in ablated.dependencies
    assert m107_bridge.ACQUISITION_NAME not in ablated.dependencies

    with_m107 = run_candidate(
        candidate,
        m108_bridge.evaluation_tasks(),
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=m107_bridge.grade,
    )
    without_m107 = run_candidate(
        ablated,
        m108_bridge.evaluation_tasks(),
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=m107_bridge.grade,
    )

    assert with_m107["completed"] is True
    assert without_m107["completed"] is True
    assert _solved(with_m107) == 20
    assert _solved(without_m107) == 4


def test_removing_only_m108_retains_m107_but_restores_hardwired_machinery():
    candidate = m108_bridge.acquired_body_factory()
    without_m108 = derive_ablation(candidate, m108_bridge.ACQUISITION_NAME)

    assert without_m108.dependencies == frozenset({m107_bridge.ACQUISITION_NAME})
    assert dict(candidate.configuration) == dict(without_m108.configuration)

    run = run_candidate(
        without_m108,
        m108_bridge.evaluation_tasks(),
        tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        grade=m107_bridge.grade,
    )
    assert run["completed"] is True
    # Every M107 bridge task is retained; M108 B remains unreachable under hardwired attribution.
    assert _solved(run) == 12
    assert all(
        row["outcome"] == "refused"
        for row in run["outcomes"]
        if row["task_id"].startswith("m108-bridge:")
    )


def test_two_generation_real_mechanism_lineage_survives_process_death_restore(tmp_path):
    genesis, _, second = _two_generations()
    assert second["accepted"] is True
    genesis.persist(tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=m107_bridge.grade)

    assert isinstance(restored.body_factory, ConfiguredBody)
    assert tr.artifact_digest_of(restored.body_factory) == tr.artifact_digest_of(
        genesis.body_factory
    )
    assert restored.state["state_digest"] == genesis.state["state_digest"]
    assert restored.journal.head == genesis.journal.head
    assert restored.causal_chain()["established_links"] == 1

    run = run_candidate(
        restored.body_factory,
        m108_bridge.evaluation_tasks(),
        restored.isolation,
        admitted_isolation=restored.admitted_isolation,
        grade=m107_bridge.grade,
    )
    assert run["completed"] is True
    assert _solved(run) == 20
