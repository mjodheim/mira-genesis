"""DEVELOPMENT regression for two endogenous transformation-language extensions in one lineage."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import objective_policy_controller as opc
from genesis import policies, policy_body_lineage, policy_controller, recovery
from genesis import recursive_transformation_language as recursive
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import transformation_language as tl
from genesis import transformation_language_application as application
from genesis import transformation_language_controller as tlc
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="Genesis v2 recursive-language fixture")

OBJECTIVE_ONE = (
    {"task_id": "open-0", "input": -3, "expected": -3},
)
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "open-1", "input": -5, "expected": -9},
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
                "policy_updates": 0,
                "policy_evaluations": 0,
                "policy_mutations": 0,
                "language_operator_evaluations": 128,
                "language_body_evaluations": 512,
                "language_application_evaluations": 2,
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
    # With two operations the complete depth-two image has six programs.  The cap of five makes
    # negate->negate structurally unreachable even after depth grows unless capacity grows too.
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment", "negate"),
        max_length=1,
        ceiling_length=3,
        max_candidates=5,
    )


def _deepen():
    return tl.create_step("increase_policy_depth")


def _widen_five():
    return tl.create_step("increase_candidate_limit", amount=5)


def _add_triple():
    return tl.create_step("append_policy_operation", operation="triple")


def _seed_language():
    return tl.create_language(
        (
            tl.create_operator("deepen", (_deepen(),)),
            tl.create_operator("widen-five", (_widen_five(),)),
            tl.create_operator("add-triple", (_add_triple(),)),
        ),
        max_operator_steps=2,
    )


def _exhaust(genesis, here, *, directory):
    run = retentive.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy() if policy_controller.bound_policy(genesis) is None else None,
        max_steps=32,
        checkpoint_directory=directory,
    )
    assert opc.exhausted(genesis, here)
    return run


def test_second_language_extension_uses_first_as_a_primitive_after_process_death(tmp_path):
    first_world = _world(OBJECTIVE_ONE)
    genesis = _genesis()

    # L0 body search is exhausted. Neither `deepen`, `widen-five`, nor `add-triple` alone can expose
    # the identity program negate->negate under the seed cap.
    first_exhaustion = _exhaust(genesis, first_world, directory=tmp_path)
    assert all(not step.get("accepted") for step in first_exhaustion["steps"] if step.get("intent") == "GenerateTransform")

    l1_search = tlc.run_extension_search(
        genesis,
        first_world,
        admitted_steps=(_deepen(), _widen_five(), _add_triple()),
        seed_language=_seed_language(),
        checkpoint_directory=tmp_path,
    )
    assert l1_search["status"] == "unique_strict_maximum"
    l1_operator = l1_search["certificate"]["operator"]
    assert [step["kind"] for step in l1_operator["steps"]] == [
        "increase_policy_depth",
        "increase_candidate_limit",
    ]
    assert l1_search["certificate"]["witness"]["operations"] == ["negate", "negate"]

    l1_application = application.apply_acquired_extension(
        genesis,
        first_world,
        max_policy_steps=16,
        checkpoint_directory=tmp_path,
    )
    assert l1_application["body_adopted"] is True
    assert l1_application["causal_record"]["language_ablation"]["established"] is True
    assert l1_application["causal_record"]["adopted_body"]["program"]["operations"] == [
        "negate",
        "negate",
    ]
    l1_language = tlc.bound_language(genesis)
    l1_policy = policy_controller.bound_policy(genesis)
    l1_causal_digest = l1_application["causal_record"]["causal_digest"]

    # Hard process boundary: continuation comes only from the persisted Genesis checkpoint.
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert tlc.bound_language(restored) == l1_language
    assert policy_controller.bound_policy(restored) == l1_policy
    assert any(
        item.get("causal_digest") == l1_causal_digest
        for item in restored.state["observations"]
    )

    second_world = _world(OBJECTIVE_TWO)
    second_exhaustion = _exhaust(restored, second_world, directory=tmp_path)
    attempts = [
        step for step in second_exhaustion["steps"] if step.get("intent") == "GenerateTransform"
    ]
    assert attempts and all(not step.get("accepted") for step in attempts)

    # The recursive wrapper derives `invoke L1` from lineage history. The caller supplies neither
    # L1's digest nor an L2 operator. The winning L2 operator combines that acquired primitive with
    # the already-held add-triple primitive.
    l2_search = recursive.run_recursive_extension_search(
        restored,
        second_world,
        checkpoint_directory=tmp_path,
    )
    assert l2_search["recursive_extension"] is True
    assert l2_search["lineage_history_derived_invocation"] is True
    assert l2_search["caller_supplied_recursive_operator"] is False
    assert l2_search["dependency_ablation"]["established"] is True
    assert l2_search["dependency_ablation"]["descendant_reconstructs_without_predecessor"] is False
    assert l1_operator["operator_digest"] in l2_search["invoked_acquired_operator_digests"]

    # Dependency must also be empirical, not merely syntactic.  The ordinary controller measured
    # the complete same-round candidate image before choosing L2.  Every candidate independent of
    # L1 therefore competes under the same objective snapshot and budget, and the recursive winner
    # must have strictly greater measured reach than the best of them.
    reach = l2_search["dependency_ablation"]["same_round_reach"]
    assert reach["established"] is True
    assert reach["complete_candidate_image_measured"] is True
    assert reach["strict_reach_loss_without_predecessor"] is True
    assert reach["independent_candidate_count"] > 0
    assert reach["candidate_count"] == len(l2_search["extension_run"]["candidate_measurements"])
    assert (
        reach["winner_selection_score"]
        > reach["best_selection_score_without_invoked_predecessor"]
    )

    l2_operator = l2_search["extension_run"]["certificate"]["operator"]
    kinds = [step["kind"] for step in l2_operator["steps"]]
    assert kinds == ["append_policy_operation", "invoke_held_operator"]
    invoked = [
        step for step in l2_operator["steps"] if step["kind"] == "invoke_held_operator"
    ]
    assert invoked[0]["operator_digest"] == l1_operator["operator_digest"]
    assert l2_search["extension_run"]["certificate"]["witness"]["operations"] == [
        "increment",
        "increment",
        "triple",
    ]

    l2_application = application.apply_acquired_extension(
        restored,
        second_world,
        max_policy_steps=32,
        checkpoint_directory=tmp_path,
    )
    assert l2_application["body_adopted"] is True
    assert l2_application["causal_record"]["language_ablation"]["established"] is True
    assert l2_application["causal_record"]["adopted_body"]["program"]["operations"] == [
        "increment",
        "increment",
        "triple",
    ]
    assert l2_application["new_policy"]["operation_names"] == [
        "increment",
        "negate",
        "triple",
    ]
    assert l2_application["new_policy"]["max_length"] == 3
    assert l2_application["new_policy"]["max_candidates"] == 15

    # A third process must reconstruct both language generations, the second policy/body link, and
    # both causal application records without redrawing either language search.
    final = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    final_language = tlc.bound_language(final)
    assert final_language["language_digest"] == l2_search["descendant_language_digest"]
    assert final_language["parent_language_digest"] == l1_language["language_digest"]
    assert policy_controller.bound_policy(final) == policy_controller.bound_policy(restored)
    assert len(policy_body_lineage.links(final)) >= 2
    causal_records = [
        item
        for item in final.state["observations"]
        if item.get("schema") == application.CAUSAL_RECORD_SCHEMA
    ]
    assert len(causal_records) == 2
    recursive_records = [
        item
        for item in final.state["observations"]
        if item.get("schema") == recursive.RECURSION_SCHEMA and item.get("recursive_extension")
    ]
    assert len(recursive_records) == 1
    assert recursive_records[0]["invoked_acquired_operator_digests"] == [
        l1_operator["operator_digest"]
    ]
    persisted_reach = recursive_records[0]["dependency_ablation"]["same_round_reach"]
    assert persisted_reach["evidence_digest"] == reach["evidence_digest"]
