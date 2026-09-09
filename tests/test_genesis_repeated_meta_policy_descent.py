"""DEVELOPMENT regression for two retained MetaPolicy descendant transitions in one campaign."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import metamorphic_policy_loop as runtime
from genesis import policies, policy_controller, policy_mutations, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="repeated MetaPolicy descent fixture")

# Objective 1 is deliberately a fixed point of square: square(1) == square(square(1)) == 1.  The
# held M0 mutation `negate` cannot improve it, while adding square can.  Depth growth over increment
# cannot solve it either, so square is the unique useful MetaPolicy extension.
OBJECTIVE_ONE = (
    {"task_id": "m0", "input": 1, "expected": 1},
)

# Objective 2 retains the exact old work and adds a point requiring square->square.  The retained B1
# square body still solves m0 but not m1.  Adding another primitive at depth one cannot retain m0 and
# solve m1; increasing depth exposes square->square, which does both.  Thus the useful structural
# edit changes across generations without changing the trust root.
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "m1", "input": 2, "expected": 16},
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
                "generations": 96,
                "policy_mutations": 64,
                "policy_evaluations": 256,
                "meta_policy_candidates": 64,
                "meta_policy_evaluations": 256,
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
        max_candidates=64,
    )


def _seed_meta():
    return meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
    )


def _accepted_body_step(run):
    accepted = [
        step
        for step in run["steps"]
        if step.get("intent") == "GenerateTransform" and step.get("accepted")
    ]
    assert len(accepted) == 1
    return accepted[0]


def _meta_evolution_step(run):
    steps = [step for step in run["steps"] if step.get("intent") == "MetaPolicyEvolution"]
    assert len(steps) == 1
    assert steps[0]["accepted"] is True
    assert steps[0]["selection_reason"] == "unique_strict_maximum"
    assert steps[0]["durable_budget_round_digest"]
    return steps[0]


def test_two_objectives_force_m0_m1_then_m1_m2_with_retention_and_restart(tmp_path):
    genesis = _genesis()
    seed_policy = _seed_policy()
    seed_meta = _seed_meta()
    admitted_root = genesis.admitted_source_sha256
    admitted_contract = genesis.evaluation_contract["contract_digest"]

    campaign = runtime.run_objectives(
        genesis,
        [_world(OBJECTIVE_ONE), _world(OBJECTIVE_TWO)],
        seed_policy=seed_policy,
        seed_meta_policy=seed_meta,
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )

    assert len(campaign["objectives"]) == 2
    first, second = campaign["objectives"]
    assert first["body_adopted"] is True
    assert second["body_adopted"] is True

    # First limitation: M0 is exhausted; the unique strict descendant adds square.  M1 then earns
    # the lower-level P1 mutation, and P1 emits B1=square through the ordinary body path.
    first_meta_step = _meta_evolution_step(first)
    m1 = first["meta_policy"]
    p1 = first["current_policy"]
    b1 = _accepted_body_step(first)
    assert first_meta_step["parent_meta_policy_digest"] == seed_meta["meta_policy_digest"]
    assert first_meta_step["new_meta_policy_digest"] == m1["meta_policy_digest"]
    assert m1["parent_meta_policy_digest"] == seed_meta["meta_policy_digest"]
    assert {
        (item["kind"], item.get("operation")) for item in m1["mutations"]
    } == {
        ("add_operation", "negate"),
        ("add_operation", "square"),
    }
    assert p1["parent_policy_digest"] == seed_policy["policy_digest"]
    assert p1["operation_names"] == ["increment", "square"]
    assert p1["max_length"] == 1
    assert b1["program"]["operations"] == ["square"]
    assert len(first["retention_corpus"]["question_digests"]) == 1

    # Second limitation retains objective 1.  The same M1 is now exhausted on P1.  A *different*
    # structural edit — one-step depth growth — is the unique strict MetaPolicy descendant because
    # it exposes square->square, which preserves the old fixed point and solves the new task.
    second_meta_step = _meta_evolution_step(second)
    m2 = second["meta_policy"]
    p2 = second["current_policy"]
    b2 = _accepted_body_step(second)
    assert second_meta_step["parent_meta_policy_digest"] == m1["meta_policy_digest"]
    assert second_meta_step["new_meta_policy_digest"] == m2["meta_policy_digest"]
    assert m2["parent_meta_policy_digest"] == m1["meta_policy_digest"]
    assert len(m2["mutations"]) == len(m1["mutations"]) + 1
    added = [item for item in m2["mutations"] if item not in m1["mutations"]]
    assert len(added) == 1
    assert added[0]["kind"] == "increase_depth"
    assert p2["parent_policy_digest"] == p1["policy_digest"]
    assert p2["operation_names"] == ["increment", "square"]
    assert p2["max_length"] == 2
    assert b2["program"]["operations"] == ["square", "square"]
    assert len(second["retention_corpus"]["question_digests"]) == 2

    # The measure did not move while the machinery did, and the final checkpoint reconstructs the
    # complete M0->M1->M2 / P0->P1->P2 / B0->B1->B2 state without caller-supplied descendants.
    assert genesis.admitted_source_sha256 == admitted_root
    assert genesis.evaluation_contract["contract_digest"] == admitted_contract
    assert genesis.body_factory.configuration["operations"] == ("square", "square")

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert restored.admitted_source_sha256 == admitted_root
    assert restored.evaluation_contract["contract_digest"] == admitted_contract
    assert meta.bound_meta_policy(restored) == m2
    assert policy_controller.bound_policy(restored) == p2
    assert restored.body_factory.configuration["operations"] == ("square", "square")
    assert retentive.bound_corpus(restored) == second["retention_corpus"]
