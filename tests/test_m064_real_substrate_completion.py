from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import sys

import pytest

import metamorphosis.m064_real_substrate_completion as m064
import metamorphosis.m064_whole_wasm_completion as whole
import metamorphosis.m064_wasm_body_compiler as wasm_compiler
from metamorphosis.m064_real_substrate_completion import (
    M064Error,
    M064_PROTOCOL,
    M064_TASK_BANK,
    run_m064_development,
    select_task_bank,
)


@pytest.fixture(scope="module")
def manifests():
    values = tuple(run_m064_development(index) for index in range(len(M064_TASK_BANK)))
    for index, value in enumerate(values):
        sys.__stdout__.write(f"\nM064_BANK_{index}_MANIFEST_SHA256={value.digest()}\n")
    sys.__stdout__.flush()
    return values


@pytest.fixture(scope="module")
def native_parent():
    state, _retained, _evidence = whole._build_migrated_state(M064_PROTOCOL)
    return state["body"]


def test_protocol_freezes_four_arms_three_cycles_and_three_runtime_stages() -> None:
    assert M064_PROTOCOL.source_runtime == "cpython"
    assert M064_PROTOCOL.intermediate_runtime == "node-esm"
    assert M064_PROTOCOL.target_runtime == "webassembly"
    assert M064_PROTOCOL.accepted_post_migration_cycles == 3
    assert M064_PROTOCOL.arms == (
        "complete_continued_lineage",
        "fresh_on_b",
        "unchanged_parent_migrated",
        "learned_state_ablated",
    )
    assert M064_PROTOCOL.candidate_budget_per_arm_cycle == 8_192
    assert M064_PROTOCOL.task_bank_entries == 4
    assert M064_PROTOCOL.extensions == ()
    assert len(M064_PROTOCOL.task_bank_commitment) == 64


def test_protocol_drift_fails_closed() -> None:
    with pytest.raises(M064Error):
        replace(M064_PROTOCOL, target_runtime="node-wrapper")
    with pytest.raises(M064Error):
        replace(M064_PROTOCOL, accepted_post_migration_cycles=2)
    with pytest.raises(M064Error):
        replace(M064_PROTOCOL, candidate_budget_per_arm_cycle=8_193)
    with pytest.raises(M064Error):
        replace(M064_PROTOCOL, task_bank_commitment="0" * 64)


def test_all_precommitted_banks_finish_one_continuous_whole_native_lineage(manifests) -> None:
    assert len({value.digest() for value in manifests}) == 4
    for value in manifests:
        mapping = value.to_dict()
        assert mapping["source_version"] == 6
        assert mapping["intermediate_version"] == 8
        assert mapping["migration_version"] == 9
        assert mapping["complete_final_version"] == 12
        assert mapping["source_retained_cases_after_node_learning"] == 32
        assert mapping["complete_final_retained_cases"] == 68
        assert mapping["complete_final_retained_passed"] == 68
        assert mapping["complete_patch_records"] == 3
        assert mapping["complete_archived_parent_versions"] == [9, 10, 11]
        assert mapping["final_native_memory_episodes"] == mapping["source_native_memory_episodes"] + 3


def test_substrate_is_discovered_before_the_whole_body_crosses(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        discovery = mapping["substrate_discovery"]
        assert discovery["arithmetic_space_scanned"] == 256
        assert discovery["arithmetic_opcodes"] == {"add": 0xA0, "div": 0xA3, "max": 0xA5, "mul": 0xA2}
        assert len(discovery["structural_opcodes"]) == 10
        assert len(discovery["structural_shapes"]) == 6
        assert mapping["whole_body_modules_left_in_node"] == 0
        assert mapping["target_declared_imports"] == 0


def test_all_arms_cross_before_the_selected_tasks_are_exposed(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        assert mapping["all_arms_migrated_before_task_selection"] is True
        arms = mapping["arm_results"]
        assert tuple(arms) == M064_PROTOCOL.arms
        assert all(arm["migration_retained_passed"] >= 4 for arm in arms.values())
        assert all(arm["migration_imports"] == 0 for arm in arms.values())
        assert all(len(arm["migration_body_digest"]) == 64 for arm in arms.values())


def test_complete_lineage_accepts_three_separated_whole_native_rewrites(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        tasks = mapping["selected_task_commitments"]
        complete = mapping["arm_results"]["complete_continued_lineage"]
        assert complete["accepted_cycles"] == 3
        assert [cycle["task_id"] for cycle in complete["cycles"]] == [task["task_id"] for task in tasks]
        assert all(cycle["adopted"] for cycle in complete["cycles"])
        assert complete["cycles"][0]["selected_referenced_tools"] == ["max", "mean"]
        assert tasks[0]["token"] in complete["cycles"][1]["selected_referenced_tools"]
        assert {tasks[0]["token"], tasks[1]["token"]} <= set(
            complete["cycles"][2]["selected_referenced_tools"]
        )
        assert all(cycle["diagnosis"]["stage"] == "native_interpretation" for cycle in complete["cycles"])
        assert all(cycle["diagnosis"]["emitted_before_hidden_validation"] for cycle in complete["cycles"])
        assert [cycle["selected_module_bytes"] for cycle in complete["cycles"]] == [1_887, 1_962, 2_037]


def test_every_public_survivor_is_validated_before_canonicalisation(manifests) -> None:
    for value in manifests:
        complete = value.to_dict()["arm_results"]["complete_continued_lineage"]
        assert [cycle["expressions_constructed"] for cycle in complete["cycles"]] == [740, 1_496, 2_668]
        assert [cycle["public_survivors"] for cycle in complete["cycles"]] == [12, 8, 8]
        for cycle in complete["cycles"]:
            assert cycle["entire_public_class_validated"] is True
            assert cycle["validation_attempts"] == cycle["public_survivors"]
            assert cycle["selection_action"] == "adopt"


def test_equal_budget_controls_remain_non_exact(manifests) -> None:
    for value in manifests:
        arms = value.to_dict()["arm_results"]
        for name in M064_PROTOCOL.arms:
            assert arms[name]["equal_candidate_budget_per_cycle"] == 8_192
        for name in M064_PROTOCOL.arms[1:]:
            assert arms[name]["accepted_cycles"] == 0
            assert arms[name]["held_out_quality"] == {
                "hidden_passes": 0,
                "hidden_total": 18,
                "exact": False,
            }
            assert all(cycle["expressions_constructed"] == 200 for cycle in arms[name]["cycles"])
            assert all(cycle["public_survivors"] == 0 for cycle in arms[name]["cycles"])


def test_complete_lineage_has_strict_primary_held_out_advantage_and_full_cost(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        assert mapping["strict_held_out_advantage"] is True
        assert mapping["arm_results"]["complete_continued_lineage"]["held_out_quality"] == {
            "hidden_passes": 18,
            "hidden_total": 18,
            "exact": True,
        }
        assert mapping["arm_results"]["complete_continued_lineage"]["cost_accounting"] == {
            "expressions_constructed": 4_904,
            "public_candidate_processes": 28,
            "independent_inspection_processes": 28,
            "independent_execution_processes": 28,
            "native_host_process_invocations": 95,
            "accepted_rewrites": 3,
        }


def test_timing_and_quality_summaries_are_falsifiable(manifests) -> None:
    mapping = manifests[0].to_dict()
    assert m064._migration_precedes_task_selection(mapping["event_trace"], M064_PROTOCOL.arms)
    wrong_order = json.loads(json.dumps(mapping["event_trace"]))
    wrong_order[-1]["sequence"] = 1
    assert not m064._migration_precedes_task_selection(wrong_order, M064_PROTOCOL.arms)
    quality = {name: arm["held_out_quality"] for name, arm in mapping["arm_results"].items()}
    assert m064._strict_quality_advantage(quality, "complete_continued_lineage")
    tied = json.loads(json.dumps(quality))
    tied["fresh_on_b"] = dict(tied["complete_continued_lineage"])
    assert not m064._strict_quality_advantage(tied, "complete_continued_lineage")


def test_forced_fault_restores_exact_code_and_behaviour(manifests) -> None:
    for value in manifests:
        rollback = value.to_dict()["forced_rollback"]
        assert rollback["exact_restoration"] is True
        assert rollback["before_digest"] == rollback["after_digest"]
        assert rollback["restored_behaviour_passed"] is True
        assert len(rollback["restored_body_digest"]) == 64


def test_complete_lineage_replays_from_whole_wasm_version_nine(manifests) -> None:
    assert all(value.to_dict()["replay_identical"] is True for value in manifests)


def test_constructor_has_no_hidden_evidence_parameter() -> None:
    signature = inspect.signature(whole._propose_whole_wasm)
    assert "hidden_cases" not in signature.parameters
    assert "public_cases" in signature.parameters


def test_owned_constructor_evaluator_renderer_and_compiler_are_serialised(manifests) -> None:
    registry = manifests[0].to_dict()["constructor_registry"]
    expression_registry = registry["expression_registry"]
    expected = {
        "constructor": m064._enumerate_expression_candidates,
        "evaluator": m064._evaluate_expression,
        "renderer": m064._render_expression,
    }
    for key, function in expected.items():
        source = inspect.getsource(function)
        assert expression_registry[key]["implementation_source"] == source
        assert expression_registry[key]["implementation_sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()
    compiler_source = Path(wasm_compiler.__file__).read_text(encoding="utf-8")
    assert registry["whole_body_compiler"]["implementation_source"] == compiler_source
    assert registry["whole_body_compiler"]["implementation_sha256"] == hashlib.sha256(
        compiler_source.encode("utf-8")
    ).hexdigest()


def test_validator_is_passive_and_cannot_adopt() -> None:
    source = inspect.getsource(whole._independent_validate_whole_class)
    assert "_adopt_candidate" not in source
    assert "patch_registry" not in source
    assert "native_journal" not in source


def test_native_safety_claim_can_be_falsified_by_wrong_module_bytes(native_parent) -> None:
    expression = m064._call(
        "mean",
        m064._call("max", m064._arg(0), m064._arg(1)),
        m064._arg(0),
        m064._arg(1),
    )
    task = M064_TASK_BANK[0][0]
    candidate = whole._materialize_candidate(
        native_parent,
        task.task_id,
        task.token,
        task.public_cases(),
        expression,
        M064_PROTOCOL,
    )
    assert whole._candidate_audit(native_parent, candidate, task.token, M064_PROTOCOL) == (
        True,
        "passed",
        0,
    )
    corrupted = json.loads(json.dumps(candidate))
    module = bytearray.fromhex(corrupted["candidate_body"]["module_hex"])
    module[-1] ^= 1
    corrupted["candidate_body"]["module_hex"] = bytes(module).hex()
    assert whole._candidate_audit(native_parent, corrupted, task.token, M064_PROTOCOL) == (
        False,
        "compiler_trace_mismatch",
        -1,
    )


def test_host_has_explicit_bounds_and_native_body_has_no_outward_authority(manifests) -> None:
    limits = manifests[0].to_dict()["execution_limits"]
    assert limits["wall_timeout_seconds"] == 30.0
    assert limits["node_old_space_megabytes"] == 128
    assert limits["linear_memory_pages"] == 1
    assert limits["expression_node_limit"] == 7
    assert limits["network_and_syscalls"] == "zero-import_webassembly_module"
    source = inspect.getsource(whole._isolated_wasm_call)
    assert "--max-old-space-size=128" in source
    assert "TemporaryDirectory" in source
    assert "timeout=protocol.node_timeout_seconds" in source


def test_authorship_boundary_is_preserved_beside_discovery(manifests) -> None:
    for value in manifests:
        boundary = value.to_dict()["authorship_boundary"]
        assert boundary["whole_body_compiler_authored"] is True
        assert boundary["block_structure_authored"] is True
        assert boundary["task_families_authored_and_precommitted"] is True
        assert boundary["candidate_expressions_constructed_by_serialised_registry"] is True


def test_marker_selection_is_deterministic_and_bound_to_protocol() -> None:
    sha = "1" * 40
    assert select_task_bank(sha) == select_task_bank(sha)
    assert 0 <= select_task_bank(sha) < len(M064_TASK_BANK)
    with pytest.raises(M064Error):
        select_task_bank("not-a-git-sha")


def test_development_result_does_not_cross_release_or_canonical_boundaries(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        assert mapping["constructor_receives_hidden_cases"] is False
        assert mapping["validator_owns_adoption"] is False
        assert mapping["canonical_workflow_authorised"] is False
        assert mapping["repository_write_authority_granted_to_lineage"] is False
