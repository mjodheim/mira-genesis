"""DEVELOPMENT regressions for evidence-backed search over how search machinery changes."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_application as application
from genesis import meta_policy_controller as meta
from genesis import objective_policy_controller as opc
from genesis import policies, policy_body_lineage, policy_controller, policy_mutations, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="generated policy-mutation fixture")
SQUARE_OBJECTIVE = (
    {"task_id": "s0", "input": 2, "expected": 4},
    {"task_id": "s1", "input": 3, "expected": 9},
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


def _genesis(*, mutation_budget=4):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 16,
                "policy_updates": 0,
                "policy_evaluations": 16,
                "policy_mutations": mutation_budget,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world():
    return controller.world(
        tasks=SQUARE_OBJECTIVE,
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
        ceiling_length=1,
        max_candidates=8,
    )


def _meta_policy():
    return meta.create_meta_policy(
        (
            policy_mutations.create("add_operation", operation="negate"),
            policy_mutations.create("add_operation", operation="square"),
        )
    )


def _exhaust_seed(genesis, here, *, directory=None):
    run = retentive.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(),
        max_steps=4,
        checkpoint_directory=directory,
    )
    attempts = [step for step in run["steps"] if step["intent"] == "GenerateTransform"]
    assert len(attempts) == 1
    assert attempts[0]["program"]["operations"] == ["increment"]
    assert attempts[0]["accepted"] is False
    assert opc.exhausted(genesis, here) is True


def test_policy_mutations_are_canonical_single_structural_edits():
    prior = _seed_policy()
    add_square = policy_mutations.create("add_operation", operation="square")
    descendant = policy_mutations.apply(prior, add_square)

    assert descendant["parent_policy_digest"] == prior["policy_digest"]
    assert descendant["operation_names"] == ["increment", "square"]
    assert policy_mutations.structural_difference(prior, descendant) == ["operation_names"]

    with pytest.raises(policy_mutations.PolicyMutationError, match="already holds"):
        policy_mutations.apply(prior, policy_mutations.create("add_operation", operation="increment"))
    with pytest.raises(policy_mutations.PolicyMutationError, match="outside"):
        policy_mutations.apply(prior, policy_mutations.create("add_operation", operation="not-admitted"))


def test_lineage_held_meta_policy_rejects_one_policy_edit_then_adopts_the_one_with_measured_reach(tmp_path):
    genesis = _genesis()
    here = _world()
    _exhaust_seed(genesis, here, directory=tmp_path)
    prior = policy_controller.bound_policy(genesis)

    run = meta.run_meta_policy(
        genesis,
        here,
        seed_meta_policy=_meta_policy(),
        max_steps=4,
        checkpoint_directory=tmp_path,
    )
    attempts = [step for step in run["steps"] if step["intent"] == "PolicyMutation"]
    assert len(attempts) == 2
    assert [step["mutation"]["operation"] for step in attempts] == ["negate", "square"]
    assert [step["accepted"] for step in attempts] == [False, True]
    assert attempts[0]["durable_before_next_meta_intent"] is True
    assert attempts[0]["checkpoint_digest"]

    current = policy_controller.bound_policy(genesis)
    assert current["parent_policy_digest"] == prior["policy_digest"]
    assert current["operation_names"] == ["increment", "square"]
    assert current["max_length"] == prior["max_length"] == 1
    assert current["ceiling_length"] == prior["ceiling_length"] == 1
    assert attempts[1]["certificate"]["structural_difference"] == ["operation_names"]
    assert attempts[1]["certificate"]["causal_dependency"]["established"] is True
    assert attempts[1]["certificate"]["resolving_program"]["operations"] == ["square"]
    assert meta.bound_meta_policy(genesis)["meta_policy_digest"] == _meta_policy()["meta_policy_digest"]
    assert genesis.budget.spent["policy_mutations"] == 2
    assert genesis.budget.spent["policy_evaluations"] == 2

    rejected = [
        item
        for item in genesis.state["observations"]
        if item.get("kind") == "policy_mutation_rejected"
    ]
    assert len(rejected) == 1
    assert rejected[0]["mutation"]["operation"] == "negate"


def test_meta_policy_selected_machinery_produces_and_is_linked_to_the_next_body(tmp_path):
    genesis = _genesis()
    here = _world()
    _exhaust_seed(genesis, here, directory=tmp_path)

    result = application.evolve_and_apply(
        genesis,
        here,
        seed_meta_policy=_meta_policy(),
        checkpoint_directory=tmp_path,
    )
    assert result["policy_changed"] is True
    assert result["body_adopted"] is True
    assert result["body_attempt"]["program"]["operations"] == ["square"]
    link = result["body_attempt"]["policy_body_link"]
    assert link["machinery_dependency"]["established"] is True
    assert link["machinery_dependency"]["update_certificate_digest"]
    assert link["policy"]["operation_names"] == ["increment", "square"]
    assert link["policy"]["parent_policy_digest"] == result["policy_update"]["prior_policy_digest"]
    assert len(retentive.bound_corpus(genesis)["question_digests"]) == 2

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert policy_controller.bound_policy(restored)["operation_names"] == ["increment", "square"]
    assert meta.bound_meta_policy(restored)["meta_policy_digest"] == _meta_policy()["meta_policy_digest"]
    assert policy_body_lineage.links(restored)[-1]["link_digest"] == link["link_digest"]
    assert retentive.bound_corpus(restored) == retentive.bound_corpus(genesis)


def test_meta_policy_cannot_replace_itself_or_mutate_without_prospective_budget():
    genesis = _genesis(mutation_budget=0)
    here = _world()
    _exhaust_seed(genesis, here)
    meta.admit_meta_policy(genesis, _meta_policy())

    other = meta.create_meta_policy((policy_mutations.create("add_operation", operation="square"),))
    with pytest.raises(meta.MetaPolicyError, match="replacing"):
        meta.admit_meta_policy(genesis, other)

    with pytest.raises(meta.MetaPolicyError, match="policy_mutations"):
        meta.run_meta_policy(genesis, here, max_steps=1)
    assert policy_controller.bound_policy(genesis) == _seed_policy()
