"""DEVELOPMENT regressions for causal application of a Genesis v2 language extension."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import objective_policy_controller as opc
from genesis import policies, policy_body_lineage, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import transformation_language as tl
from genesis import transformation_language_application as tla
from genesis import transformation_language_controller as tlc
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="Genesis v2 language-application fixture")


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


def _genesis(*, application_budget=1):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 32,
                "policy_updates": 0,
                "policy_evaluations": 0,
                "policy_mutations": 0,
                "language_operator_evaluations": 16,
                "language_body_evaluations": 64,
                "language_application_evaluations": application_budget,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world():
    return controller.world(
        tasks=({"task_id": "v2", "input": 1, "expected": 0},),
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


def _add_negate_step():
    return tl.create_step("append_policy_operation", operation="negate")


def _deepen_step():
    return tl.create_step("increase_policy_depth")


def _seed_language():
    return tl.create_language(
        (
            tl.create_operator("add-negate", (_add_negate_step(),)),
            tl.create_operator("deepen", (_deepen_step(),)),
        ),
        max_operator_steps=2,
    )


def _prepare_extension(genesis, here, directory):
    run = retentive.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(),
        max_steps=4,
        checkpoint_directory=directory,
    )
    attempts = [step for step in run["steps"] if step["intent"] == "GenerateTransform"]
    assert len(attempts) == 1 and attempts[0]["accepted"] is False
    assert opc.exhausted(genesis, here)
    extension = tlc.run_extension_search(
        genesis,
        here,
        admitted_steps=(_add_negate_step(), _deepen_step()),
        seed_language=_seed_language(),
        checkpoint_directory=directory,
    )
    assert extension["language_changed"] is True
    return extension


def test_acquired_operator_builds_policy_outside_parent_language_then_policy_earns_body(tmp_path):
    genesis = _genesis()
    here = _world()
    extension = _prepare_extension(genesis, here, tmp_path)
    prior_policy = policy_controller.bound_policy(genesis)

    result = tla.apply_acquired_extension(
        genesis,
        here,
        max_policy_steps=8,
        checkpoint_directory=tmp_path,
    )

    assert result["body_adopted"] is True
    assert result["prior_policy"] == prior_policy
    assert result["new_policy"]["parent_policy_digest"] == prior_policy["policy_digest"]
    assert result["new_policy"]["operation_names"] == ["increment", "negate"]
    assert result["new_policy"]["max_length"] == 2
    assert result["policy_certificate"]["candidate_policy_outside_predecessor_image"] is True
    assert result["policy_certificate"]["causal_dependency"]["established"] is True
    assert result["policy_certificate"]["objective"]["objective_digest"] == opc.objective_record(
        genesis, here
    )["objective_digest"]
    assert (
        result["policy_certificate"]["language_extension_certificate_digest"]
        == extension["certificate"]["certificate_digest"]
    )

    accepted = [step for step in result["body_steps"] if step.get("accepted")]
    assert len(accepted) == 1
    assert accepted[0]["program"]["operations"] == ["negate", "increment"]
    link = accepted[0]["policy_body_link"]
    assert link["machinery_dependency"]["established"] is True
    assert (
        link["machinery_dependency"]["update_certificate_digest"]
        == result["policy_certificate"]["certificate_digest"]
    )

    causal = result["causal_record"]
    assert causal["language_ablation"]["established"] is True
    assert causal["language_ablation"]["candidate_policy_in_predecessor_image"] is False
    assert causal["policy_body_link_digest"] == link["link_digest"]
    assert causal["adopted_body"]["program"]["operations"] == ["negate", "increment"]
    assert result["final_checkpoint_digest"]

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert tlc.bound_language(restored) == tlc.bound_language(genesis)
    assert policy_controller.bound_policy(restored) == policy_controller.bound_policy(genesis)
    assert policy_body_lineage.links(restored)[-1]["link_digest"] == link["link_digest"]
    restored_causal = [
        item for item in restored.state["observations"] if item.get("schema") == tla.CAUSAL_RECORD_SCHEMA
    ]
    assert len(restored_causal) == 1
    assert restored_causal[0]["causal_digest"] == causal["causal_digest"]


def test_language_application_refuses_seed_language_without_endogenous_extension():
    genesis = _genesis()
    here = _world()
    retentive.run_policy(genesis, here, seed_policy=_seed_policy(), max_steps=4)
    assert opc.exhausted(genesis, here)
    tlc.admit_seed_language(genesis, _seed_language())

    with pytest.raises(tla.TransformationLanguageApplicationError, match="no acquired extension"):
        tla.apply_acquired_extension(genesis, here)


def test_application_budget_is_spent_before_policy_installation(tmp_path):
    genesis = _genesis(application_budget=0)
    here = _world()
    _prepare_extension(genesis, here, tmp_path)
    prior_policy = policy_controller.bound_policy(genesis)

    with pytest.raises(
        tla.TransformationLanguageApplicationError,
        match="language_application_evaluations",
    ):
        tla.apply_acquired_extension(genesis, here, checkpoint_directory=tmp_path)
    assert policy_controller.bound_policy(genesis) == prior_policy
