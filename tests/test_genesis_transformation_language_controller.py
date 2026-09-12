"""DEVELOPMENT regressions for Genesis v2 transformation-language self-extension."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import objective_policy_controller as opc
from genesis import policies, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import transformation_language as tl
from genesis import transformation_language_controller as tlc
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="Genesis v2 language-controller fixture")


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


def _genesis(*, operator_budget=16, body_budget=64):
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 16,
                "policy_updates": 0,
                "policy_evaluations": 0,
                "policy_mutations": 0,
                "language_operator_evaluations": operator_budget,
                "language_body_evaluations": body_budget,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world(expected=0):
    return controller.world(
        tasks=({"task_id": "v2", "input": 1, "expected": expected},),
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


def _exhaust_body_policy(genesis, here, *, directory=None):
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


def test_complete_lower_image_finds_composite_extension_only_after_held_language_is_exhausted(tmp_path):
    genesis = _genesis()
    here = _world(expected=0)
    _exhaust_body_policy(genesis, here, directory=tmp_path)
    prior_policy = policy_controller.bound_policy(genesis)
    seed_language = _seed_language()

    run = tlc.run_extension_search(
        genesis,
        here,
        admitted_steps=(_add_negate_step(), _deepen_step()),
        seed_language=seed_language,
        checkpoint_directory=tmp_path,
    )

    assert run["status"] == "unique_strict_maximum"
    assert run["language_changed"] is True
    assert len(run["held_measurements"]) == 2
    assert all(item["accepted"] is False for item in run["held_measurements"])

    # With two lower steps and a maximum operator length of two, the single-step programs are already
    # held. The complete outside image is therefore: add+add, add+depth, depth+depth.
    assert len(run["candidate_image"]) == 3
    viable = [item for item in run["candidate_measurements"] if item["accepted"]]
    assert len(viable) == 1
    winner = viable[0]
    assert [step["kind"] for step in winner["operator"]["steps"]] == [
        "append_policy_operation",
        "increase_policy_depth",
    ]
    assert winner["structural_difference"] == ["max_length", "operation_names"]
    assert winner["witness"]["operations"] == ["negate", "increment"]

    current_language = tlc.bound_language(genesis)
    assert current_language["parent_language_digest"] == seed_language["language_digest"]
    assert current_language["language_digest"] == run["certificate"]["descendant_language_digest"]
    assert run["certificate"]["held_language_exhausted"] is True
    assert run["certificate"]["trust_root_source_sha256"] == genesis.admitted_source_sha256
    assert (
        run["certificate"]["evaluation_contract_digest"]
        == genesis.evaluation_contract["contract_digest"]
    )

    # Language extension does not silently install the policy it evaluated. The newly acquired
    # operator must later be used through its own evidence-backed machinery transition.
    assert policy_controller.bound_policy(genesis) == prior_policy

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert tlc.bound_language(restored) == current_language
    tool = next(
        item
        for item in restored.state["tools"]
        if item["name"] == tlc.LANGUAGE_TOOL_NAME
    )
    assert tool["provenance"]["class"] == "lineage_owned"


def test_controller_refuses_to_extend_while_held_language_still_has_measured_reach():
    genesis = _genesis()
    here = _world(expected=-1)
    _exhaust_body_policy(genesis, here)

    run = tlc.run_extension_search(
        genesis,
        here,
        admitted_steps=(_add_negate_step(), _deepen_step()),
        seed_language=_seed_language(),
    )

    assert run["status"] == "held_language_has_measured_reach"
    assert run["language_changed"] is False
    assert run["candidate_image"] == []
    assert any(item["accepted"] is True for item in run["held_measurements"])
    assert tlc.bound_language(genesis) == _seed_language()


def test_language_search_preflights_complete_round_budget_before_first_measurement():
    genesis = _genesis(operator_budget=1)
    here = _world(expected=0)
    _exhaust_body_policy(genesis, here)

    with pytest.raises(
        tlc.TransformationLanguageControllerError,
        match="language_operator_evaluations budget cannot measure the complete round",
    ):
        tlc.run_extension_search(
            genesis,
            here,
            admitted_steps=(_add_negate_step(), _deepen_step()),
            seed_language=_seed_language(),
        )
    assert genesis.budget.spent.get("language_operator_evaluations", 0) == 0


def test_caller_cannot_replace_an_admitted_language_without_evidence():
    genesis = _genesis()
    tlc.admit_seed_language(genesis, _seed_language())
    other = tl.create_language(
        (tl.create_operator("deepen-only", (_deepen_step(),)),),
        max_operator_steps=2,
    )
    with pytest.raises(tlc.TransformationLanguageControllerError, match="already holds a different"):
        tlc.admit_seed_language(genesis, other)


def test_noncanonical_operator_order_is_not_an_alias_in_the_candidate_space():
    with pytest.raises(tl.TransformationLanguageError, match="canonical"):
        tl.create_operator(
            "reverse-alias",
            (_deepen_step(), _add_negate_step()),
        )
