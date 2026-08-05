from __future__ import annotations

from dataclasses import replace
import ast
import inspect
import sys

import pytest

import metamorphosis.m047_runtime_worker as runtime_worker
import metamorphosis.m047_search as search_module
from metamorphosis.m047_modular_lineage import (
    M047_PROTOCOL,
    ModularLineageError,
    run_m047_modular_software_lineage,
)
from metamorphosis.m047_software_body import (
    REQUIRED_MODULES,
    SoftwareBodyError,
    SourceModule,
    founder_software_body,
)


@pytest.fixture(scope="module")
def manifest():
    value = run_m047_modular_software_lineage()
    sys.__stdout__.write(f"\nM047_MANIFEST_SHA256={value.digest()}\n")
    sys.__stdout__.flush()
    return value


def test_protocol_is_one_fixed_integrated_software_experiment() -> None:
    assert M047_PROTOCOL.accepted_cycles == 6
    assert M047_PROTOCOL.rollback_task_ordinal == 7
    assert M047_PROTOCOL.terminal_task_ordinal == 8
    assert M047_PROTOCOL.resources.max_generated_patches == 8
    assert M047_PROTOCOL.resources.max_validation_attempts == 4
    assert M047_PROTOCOL.resources.max_total_source_bytes == 131_072


def test_protocol_drift_fails_closed() -> None:
    with pytest.raises(ModularLineageError):
        replace(M047_PROTOCOL, accepted_cycles=5)
    with pytest.raises(ModularLineageError):
        replace(M047_PROTOCOL, terminal_task_ordinal=9)
    with pytest.raises(ModularLineageError):
        replace(
            M047_PROTOCOL,
            resources=replace(
                M047_PROTOCOL.resources,
                max_generated_patches=9,
            ),
        )


def test_founder_is_real_parseable_modular_python() -> None:
    founder = founder_software_body()
    assert set(REQUIRED_MODULES).issubset(founder.module_names())
    assert len(founder.modules) == 8
    for module in founder.modules:
        ast.parse(module.source)
        assert module.source.startswith("# M047_META ")
        assert module.source.endswith("\n")


def test_unsafe_candidate_source_is_rejected() -> None:
    with pytest.raises(SoftwareBodyError):
        SourceModule(
            "tool_bad",
            '# M047_META {"module":"tool_bad"}\nimport os\nTOOLS = {}\n',
        )


def test_one_lineage_diagnoses_and_changes_multiple_real_modules(manifest) -> None:
    assert [cycle.family for cycle in manifest.cycles] == [
        "alias_sum",
        "recursive_planning",
        "synthesize_mean_tool",
        "critic_round_two",
        "dynamic_plan_budget",
        "alias_average",
    ]
    assert [cycle.diagnosed_module for cycle in manifest.cycles] == [
        "interpretation",
        "planning",
        "selection",
        "critique",
        "allocation",
        "interpretation",
    ]
    assert [cycle.changed_modules for cycle in manifest.cycles] == [
        ("interpretation",),
        ("planning",),
        ("selection", "tool_mean"),
        ("critique",),
        ("allocation",),
        ("interpretation",),
    ]
    assert manifest.all_module_diagnoses_correct is True


def test_lineage_writes_source_and_executable_regression_tests(manifest) -> None:
    assert all(cycle.source_delta_bytes != 0 for cycle in manifest.cycles)
    assert all(cycle.generated_tests_added == 2 for cycle in manifest.cycles)
    assert manifest.final_regression_test_count == 12
    assert manifest.all_generated_tests_persisted is True
    assert manifest.final_body_source_bytes > 0


def test_independent_hidden_validation_rejects_overfit_planner(manifest) -> None:
    planner = manifest.cycles[1]
    assert planner.validation_attempts == 2
    assert planner.independent_rejections == 1
    assert planner.selected_template == "planner_recursive_postorder"
    assert planner.independent_hidden_validation is True
    assert planner.disposable_runtime_validation is True


def test_lineage_constructs_and_reuses_a_real_tool_module(manifest) -> None:
    tool_cycle = manifest.cycles[2]
    assert tool_cycle.added_modules == ("tool_mean",)
    assert tool_cycle.selected_template == "synthesize_tool_mean"
    assert manifest.final_module_count == 9
    assert [
        cycle.required_runtime_tool_reused for cycle in manifest.cycles[3:]
    ] == [True, True, True]
    assert manifest.acquired_runtime_tool_reuse_cycles == 3


def test_patch_strategy_and_causal_memory_are_reused(manifest) -> None:
    assert manifest.cycles[0].selected_template == "interpreter_add_alias"
    assert manifest.cycles[5].selected_template == "interpreter_add_alias"
    assert manifest.cycles[5].reused_patch_template is True
    assert manifest.cycles[5].reused_causal_memory is True
    assert manifest.patch_template_reuse_cycles >= 1
    assert manifest.causal_memory_reuse_cycles >= 1
    assert manifest.final_causal_failure_evidence_count > 0


def test_every_candidate_runs_outside_the_lineage_process(manifest) -> None:
    assert manifest.all_independent_validations_disposable is True
    assert runtime_worker.RESULT_SCHEMA == "m047-runtime-batch-result-v1"


def test_generator_has_no_hidden_suite_or_release_authority_import() -> None:
    source = inspect.getsource(search_module)
    assert "m047_task" not in source
    assert "validate_ranked_software_patches_independently" not in source
    assert "hidden_cases" not in source
    assert "stage_software_adoption" not in source


def test_search_is_bounded_and_non_exhaustive(manifest) -> None:
    assert manifest.all_searches_non_exhaustive is True
    assert manifest.all_resource_budgets_respected is True
    for cycle in manifest.cycles:
        assert cycle.complete_program_space_enumerated is False
        assert cycle.generated_patches < cycle.program_space_lower_bound
        assert cycle.generated_patches <= 8
        assert cycle.validation_attempts <= 4
        assert cycle.working_memory_bytes <= 262_144
        assert cycle.time_budget_respected is True


def test_each_accepted_version_has_a_verified_combined_checkpoint(manifest) -> None:
    assert len(manifest.checkpoints) == 6
    assert [checkpoint.version for checkpoint in manifest.checkpoints] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert manifest.checkpoints_verified is True


def test_forced_fault_restores_body_registry_memory_and_journal(manifest) -> None:
    rollback = manifest.rollback
    assert rollback.attempted_version == 7
    assert rollback.restored_version == 6
    assert rollback.lineage_exact_restoration is True
    assert rollback.memory_unchanged is True
    assert rollback.combined_checkpoint_exact_restoration is True
    assert (
        rollback.combined_checkpoint_before
        == rollback.combined_checkpoint_after
    )


def test_compound_terminal_defect_fails_closed(manifest) -> None:
    terminal = manifest.terminal
    assert terminal.family == "terminal_compound_maximum"
    assert terminal.diagnosed_module == "interpretation"
    assert terminal.stop_action == "terminate_insufficient_evidence"
    assert terminal.independent_rejections == 4
    assert terminal.body_unchanged is True
    assert terminal.explicit_insufficient_evidence_termination is True
    assert terminal.parent_snapshot_digest == terminal.final_snapshot_digest


def test_prior_public_and_hidden_capabilities_remain_protected(manifest) -> None:
    assert manifest.retained_validation_case_count == 28
    assert manifest.retained_validation_all_passed is True
    assert manifest.final_patch_registry_count == 6
    assert manifest.final_journal_entries == 6


def test_exact_patch_state_and_rollback_replay_is_identical(manifest) -> None:
    assert manifest.replay_identical is True
    assert len(manifest.to_bytes()) > 0
    assert len(manifest.digest()) == 64


def test_claim_boundary_stays_bounded_and_noncanonical(manifest) -> None:
    mapping = manifest.to_dict()
    assert mapping["claim_scope"] == "bounded_modular_software_development_lineage"
    assert mapping["mutable_body_is_executable_python_modules"] is True
    assert mapping["candidate_sources_executed_only_in_disposable_worker"] is True
    assert mapping["hidden_suite_exposed_to_generator"] is False
    assert mapping["repository_write_authority_granted_to_lineage"] is False
    assert mapping["selected_seed"] is None
    assert mapping["canonical_workflow_authorised"] is False
