from __future__ import annotations
from typing import Mapping, Sequence
from metamorphosis.m047_search import CausalSoftwareMemory, ModularSearchError, ModuleDiagnosis, PatchSearchResult, PatchSearchStatus, SoftwarePatch, SoftwareProposalEpisode, heuristic_software_patch_search
from metamorphosis.m047_software_body import SoftwareBody, SoftwareCase, module_metadata, render_interpretation
from metamorphosis.m047_runtime_sandbox import run_body_in_sandbox
from metamorphosis.m047_task import HiddenSoftwareTask, IndependentSoftwareSelection, StopAction, build_hidden_modular_task, validate_ranked_software_patches_independently
from metamorphosis.m047_lineage_store import M047Protocol, ModularLineageError, SoftwareFaultKind, SoftwareSnapshot, VersionedSoftwareStore
from metamorphosis.m047_lineage_records import ModularCycleRecord, ModularRollbackRecord, ModularTerminalRecord, _checkpoint

def _dominated_templates(search: PatchSearchResult, selection: IndependentSoftwareSelection) -> tuple[str, ...]:
    attempted = {attempt.proposal_digest for attempt in selection.report.attempts}
    return tuple((proposal.template_id for proposal in search.proposals if proposal.digest() not in attempted))

def _validate_search_contract(search: PatchSearchResult, protocol: M047Protocol) -> None:
    if search.status is not PatchSearchStatus.READY:
        raise ModularLineageError(f'software patch search did not produce candidates: {search.status.value}')
    if search.complete_program_space_enumerated:
        raise ModularLineageError('M047 enumerated the complete source-program space')
    if search.generated_patches > protocol.resources.max_generated_patches:
        raise ModularLineageError('software patch count exceeded the fixed budget')
    if search.working_memory_bytes > protocol.resources.max_working_memory_bytes:
        raise ModularLineageError('software search memory exceeded the fixed budget')
    if not search.time_budget_respected:
        raise ModularLineageError('software patch search exceeded the fixed time budget')
    if search.program_space_lower_bound <= search.generated_patches:
        raise ModularLineageError('software patch search was not demonstrably non-exhaustive')

def _required_tool_reused(body: SoftwareBody, task: HiddenSoftwareTask, protocol: M047Protocol) -> bool:
    required = task.public.required_tool_name
    if required is None:
        return False
    result = run_body_in_sandbox(body, task.public.public_cases, timeout_seconds=protocol.resources.sandbox_timeout_seconds)
    return result.all_cases_passed and all((required in case.used_tools for case in result.cases))

def _run_accepted_cycle(store: VersionedSoftwareStore, memory: CausalSoftwareMemory, protocol: M047Protocol, *, ordinal: int, protected_cases: Sequence[SoftwareCase]=()) -> tuple[CausalSoftwareMemory, ModularCycleRecord, HiddenSoftwareTask, IndependentSoftwareSelection, SoftwareProposalEpisode]:
    before = store.current
    task = build_hidden_modular_task(before.accepted_body, ordinal=ordinal, protocol_digest=protocol.digest())
    search = heuristic_software_patch_search(before.accepted_body, task.public.task_id, task.public.public_cases, memory, protocol.resources)
    _validate_search_contract(search, protocol)
    selection = validate_ranked_software_patches_independently(before.accepted_body, task, search, protocol.resources, protected_cases=protected_cases)
    if not selection.accepted or selection.selected_patch is None or selection.candidate_body is None:
        raise ModularLineageError(f'software cycle {ordinal} terminated without an admissible patch')
    patch = selection.selected_patch
    reused_template = any((record.template_id == patch.template_id for record in before.patch_registry))
    receipt = store.adopt(selection)
    if not receipt.adopted:
        raise ModularLineageError(f'software cycle {ordinal} failed transactional adoption')
    after = store.current
    if after.version != before.version + 1:
        raise ModularLineageError('software adoption did not advance exactly one version')
    if after.accepted_body.digest() != patch.candidate_body.digest():
        store.rollback_to(before.version)
        raise ModularLineageError('software adoption changed the validated candidate')
    episode = SoftwareProposalEpisode(task_id=task.public.task_id, outcome='accepted', diagnosed_module=search.diagnosis.module, selected_template=patch.template_id, exact_rejected_templates=selection.rejected_templates, dominated_templates=_dominated_templates(search, selection), generated_patches=search.generated_patches, validation_attempts=len(selection.report.attempts), reason='independently validated source patch adopted transactionally')
    try:
        updated_memory = memory.append(episode, maximum_bytes=protocol.resources.max_causal_memory_bytes)
    except ModularSearchError as exc:
        rollback = store.rollback_to(before.version)
        if store.current != before or not rollback.exact_restoration:
            raise ModularLineageError('combined software-lineage memory rollback failed') from exc
        raise ModularLineageError('software causal memory budget exhausted') from exc
    tool_reused = _required_tool_reused(after.accepted_body, task, protocol)
    checkpoint = _checkpoint(after, updated_memory)
    record = ModularCycleRecord(ordinal=ordinal, family=task.family, task_digest=task.digest(), public_task_digest=task.public.digest(), parent_snapshot_digest=before.digest(), parent_body_digest=before.accepted_body.digest(), parent_module_count=len(before.accepted_body.modules), parent_regression_test_count=len(before.accepted_body.regression_cases), search_digest=search.digest(), search_status=search.status.value, diagnosis_digest=search.diagnosis.digest(), diagnosed_module=str(search.diagnosis.module), diagnosis_reason=search.diagnosis.reason, generated_patches=search.generated_patches, invalid_patches=search.invalid_patches, program_space_lower_bound=search.program_space_lower_bound, exploration_fraction_ppm=search.exploration_fraction_ppm, complete_program_space_enumerated=search.complete_program_space_enumerated, search_sandbox_runs=search.sandbox_runs, working_memory_bytes=search.working_memory_bytes, time_budget_respected=search.time_budget_respected, reused_causal_memory=search.reused_causal_memory, selection_digest=selection.digest(), validation_report_digest=selection.report.digest(), validation_attempts=len(selection.report.attempts), independent_rejections=len(selection.rejected_templates), selected_patch_digest=patch.digest(), selected_template=patch.template_id, changed_modules=patch.changed_modules, added_modules=patch.added_modules, source_delta_bytes=patch.source_delta_bytes, generated_tests_added=len(after.accepted_body.regression_cases) - len(before.accepted_body.regression_cases), module_diagnosis_correct=set(patch.changed_modules) == set(task.public.expected_changed_modules), independent_hidden_validation=selection.report.independent_hidden_suite_used, disposable_runtime_validation=selection.report.disposable_runtime_used, adopted_snapshot_digest=after.digest(), adopted_body_digest=after.accepted_body.digest(), adopted_version=after.version, adopted_module_count=len(after.accepted_body.modules), adopted_regression_test_count=len(after.accepted_body.regression_cases), patch_registry_count=len(after.patch_registry), causal_journal_entries=len(after.causal_journal), reused_patch_template=reused_template, required_runtime_tool=task.public.required_tool_name, required_runtime_tool_reused=tool_reused, causal_memory_digest=updated_memory.digest(), causal_memory_episodes=len(updated_memory.episodes), causal_failure_evidence_count=updated_memory.failure_evidence_count, checkpoint=checkpoint)
    return (updated_memory, record, task, selection, episode)
