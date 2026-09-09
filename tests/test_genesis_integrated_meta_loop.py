"""DEVELOPMENT regressions for the integrated body-search / policy-mutation loop."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import metamorphic_policy_loop as loop
from genesis import policies, policy_body_lineage, policy_controller, policy_mutations, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="integrated meta-loop fixture")

# Objective one is reachable only after adding `square` to a depth-one alphabet.
OBJECTIVE_ONE = (
    {"task_id": "i0", "input": 1, "expected": 1},
)
# Objective two retains objective one and adds a point requiring `square -> square`. The already
# acquired `square` operation is not enough at depth one, so a different policy mutation is needed.
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "i1", "input": 2, "expected": 16},
)


def _state():
    return st.create_state(
        body_digest=tr.artifact_digest_of(fixtures.null_body)["artifact_digest"],
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
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 24,
                "policy_evaluations": 24,
                "policy_mutations": 12,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world(tasks):
    return controller.world(
        tasks=tasks,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def _seed_policy():
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment",),
        max_length=1,
        ceiling_length=2,
        max_candidates=16,
    )


def _meta_policy():
    return meta.create_meta_policy(
        (
            policy_mutations.create("add_operation", operation="negate"),
            policy_mutations.create("add_operation", operation="square"),
            policy_mutations.create("increase_depth"),
        )
    )


def _accepted_mutation(meta_step):
    accepted = [step for step in meta_step["mutations"] if step.get("accepted")]
    assert len(accepted) == 1
    return accepted[0]


def test_one_runtime_campaign_selects_two_different_machinery_mutations_and_two_bodies(tmp_path):
    genesis = _genesis()
    campaign = loop.run_objectives(
        genesis,
        [_world(OBJECTIVE_ONE), _world(OBJECTIVE_TWO)],
        seed_policy=_seed_policy(),
        seed_meta_policy=_meta_policy(),
        checkpoint_directory=tmp_path,
    )

    meta_steps = [
        step
        for run in campaign["objectives"]
        for step in run["steps"]
        if step["intent"] == "MetaPolicySearch"
    ]
    assert len(meta_steps) == 2
    first_update = _accepted_mutation(meta_steps[0])
    second_update = _accepted_mutation(meta_steps[1])

    # The same lineage-held meta-policy chooses different structural edits because the held policy
    # and retained evidence changed. The launcher supplies neither mutation.
    assert first_update["mutation"]["kind"] == "add_operation"
    assert first_update["mutation"]["operation"] == "square"
    assert first_update["certificate"]["structural_difference"] == ["operation_names"]
    assert second_update["mutation"]["kind"] == "increase_depth"
    assert second_update["certificate"]["structural_difference"] == ["max_length"]
    assert second_update["candidate_policy"]["parent_policy_digest"] == first_update[
        "candidate_policy"
    ]["policy_digest"]

    accepted_bodies = [
        step
        for run in campaign["objectives"]
        for step in run["steps"]
        if step["intent"] == "GenerateTransform" and step.get("accepted")
    ]
    assert [step["program"]["operations"] for step in accepted_bodies] == [
        ["square"],
        ["square", "square"],
    ]
    assert all(step["policy_body_link"]["machinery_dependency"]["established"] for step in accepted_bodies)
    assert all(step["durable_before_next_round"] for step in accepted_bodies)

    links = list(policy_body_lineage.links(genesis))
    assert len(links) == 2
    assert [link["generated_program"]["operations"] for link in links] == [
        ["square"],
        ["square", "square"],
    ]
    assert all(link["machinery_dependency"]["established"] for link in links)

    final_policy = policy_controller.bound_policy(genesis)
    assert final_policy["operation_names"] == ["increment", "square"]
    assert final_policy["max_length"] == 2
    assert final_policy["parent_policy_digest"] == first_update["candidate_policy"]["policy_digest"]
    assert meta.bound_meta_policy(genesis)["meta_policy_digest"] == _meta_policy()["meta_policy_digest"]
    assert len(retentive.bound_corpus(genesis)["question_digests"]) == 2
    assert isinstance(genesis.body_factory, ConfiguredBody)
    assert genesis.body_factory.configuration["operations"] == ("square", "square")

    # Evidence-ranked selection measures the complete admitted mutation set before choosing. Three
    # mutations are therefore measured on each objective. Candidate-policy evaluation is complete as
    # well: objective one runs one new sequence for each mutation (3), while objective two runs one
    # for negate, none for the duplicate-square edit, and all four newly reachable depth-two programs
    # (5). Total: six mutation measurements and eight candidate-program measurements.
    assert genesis.budget.spent["policy_mutations"] == 6
    assert genesis.budget.spent["policy_evaluations"] == 8

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert restored.body_factory.configuration["operations"] == ("square", "square")
    assert policy_controller.bound_policy(restored) == final_policy
    assert meta.bound_meta_policy(restored) == meta.bound_meta_policy(genesis)
    assert policy_body_lineage.links(restored) == tuple(links)
    assert retentive.bound_corpus(restored) == retentive.bound_corpus(genesis)


def test_integrated_loop_stops_when_meta_policy_exhausts_without_useful_mutation(tmp_path):
    genesis = _genesis()
    useless = meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
    )
    run = loop.run_objective(
        genesis,
        _world(OBJECTIVE_ONE),
        seed_policy=_seed_policy(),
        seed_meta_policy=useless,
        checkpoint_directory=tmp_path,
    )

    assert run["body_adopted"] is False
    meta_step = next(step for step in run["steps"] if step["intent"] == "MetaPolicySearch")
    assert meta_step["accepted"] is False
    assert len(meta_step["mutations"]) == 1
    assert meta_step["mutations"][0]["accepted"] is False
    assert run["steps"][-1]["intent"] == "stop"
    assert policy_controller.bound_policy(genesis) == _seed_policy()

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert policy_controller.bound_policy(restored) == _seed_policy()
    assert restored.budget.spent["policy_mutations"] == 1
    assert restored.budget.spent["policy_evaluations"] == 1
    rejected = [
        item
        for item in restored.state["observations"]
        if item.get("kind") == "policy_mutation_rejected"
    ]
    assert len(rejected) == 1
    assert rejected[0]["mutation"]["operation"] == "negate"
