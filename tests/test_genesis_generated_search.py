"""DEVELOPMENT regressions for endogenous executable-candidate construction.

The policy is intentionally tiny and authored. These tests ask a narrower question: can a persistent
lineage use retained evidence to emit new program *data*, have the runtime construct executable
candidates that were not preinstalled in ``World.artifacts``, reject the bad ones, adopt the good one
under the unchanged trust root, and make each attempt durable?
"""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import endogenous_frontier_fixtures as fixtures
from genesis import programs
from genesis import sandbox as sb
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="generated-search fixture")
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
        # The important negative: there is no improved body to select. The only executable target
        # admitted for generated descendants is the fixed interpreter in genesis.programs.
        artifacts={},
        grade=bodies.grade,
    )


def test_generated_program_identity_binds_the_program_data():
    first = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("double",),
    )
    second = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("double", "increment"),
    )
    assert tr.artifact_digest_of(first)["artifact_digest"] != tr.artifact_digest_of(second)[
        "artifact_digest"
    ]


def test_generated_program_runs_through_the_existing_inert_candidate_boundary():
    generated = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("double", "increment"),
    )
    result = sb.run_candidate(
        generated,
        TASKS,
        tr.Isolation(),
        grade=bodies.grade,
    )
    assert result["completed"] is True
    assert all(row["outcome"] == "solved" for row in result["outcomes"])
    assert result["uses_executable_deserialization"] is False


def test_controller_search_constructs_and_adopts_a_body_not_preinstalled_in_the_world(tmp_path):
    genesis = _genesis()
    here = _world()
    run = controller.run(
        genesis,
        here,
        fixtures.generated_search_policy,
        max_steps=6,
        checkpoint_directory=tmp_path,
    )

    generated_steps = [step for step in run["steps"] if step["intent"] == "GenerateTransform"]
    assert [step["generated_program"]["operations"] for step in generated_steps] == [
        ["double"],
        ["increment"],
        ["double", "double"],
        ["double", "increment"],
    ]
    assert [step["accepted"] for step in generated_steps] == [False, False, False, True]
    assert run["steps"][-1]["intent"] == "stop"
    assert run["steps"][-1]["reason"] == "a generated descendant was adopted"
    assert all(step["selected_from_world_artifacts"] is False for step in generated_steps)
    assert here.artifacts == {}

    assert isinstance(genesis.body_factory, ConfiguredBody)
    assert genesis.body_factory.target == programs.PROGRAM_TARGET
    # The executable configuration is intentionally frozen after admission; sequence fields are
    # tuples internally even though the controller's inert records remain JSON lists.
    assert genesis.body_factory.configuration["operations"] == ("double", "increment")
    assert genesis.state["acquisitions"][-1]["name"] == "generated:3"
    assert run["final_generation"] == 1

    # Search is a sequence of controller steps, so every rejected hypothesis and the adopted one is
    # committed before the next policy invocation rather than living only in the driver's memory.
    assert all(step["durable_before_next_intent"] for step in generated_steps)
    assert all(step["checkpoint_digest"] for step in generated_steps)


def test_rejected_generated_candidates_become_evidence_used_by_the_next_policy_step():
    genesis = _genesis()
    controller.run(
        genesis,
        _world(),
        fixtures.generated_search_policy,
        max_steps=3,
    )
    rejected = [
        evidence
        for evidence in controller._controller_context(genesis).evidence
        if evidence.get("kind") == "observation"
        and str((evidence.get("record") or {}).get("name", "")).startswith("generated:")
    ]
    assert [item["record"]["name"] for item in rejected] == [
        "generated:0",
        "generated:1",
        "generated:2",
    ]
