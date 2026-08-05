from __future__ import annotations
from typing import Mapping, Sequence
from metamorphosis.m047_search import CausalSoftwareMemory, ModularSearchError, ModuleDiagnosis, PatchSearchResult, PatchSearchStatus, SoftwarePatch, SoftwareProposalEpisode, heuristic_software_patch_search
from metamorphosis.m047_software_body import SoftwareCase, module_metadata, render_interpretation
from metamorphosis.m047_task import HiddenSoftwareTask, IndependentSoftwareSelection, StopAction, build_hidden_modular_task, validate_ranked_software_patches_independently
from metamorphosis.m047_lineage_store import M047Protocol, ModularLineageError, SoftwareFaultKind, SoftwareSnapshot, VersionedSoftwareStore
from metamorphosis.m047_lineage_records import ModularCycleRecord, ModularRollbackRecord, ModularTerminalRecord, _checkpoint
from metamorphosis.m047_cycle_acceptance import _validate_search_contract

def _prepare_valid_selection(snapshot: SoftwareSnapshot, memory: CausalSoftwareMemory, protocol: M047Protocol, ordinal: int, protected_cases: Sequence[SoftwareCase]=()) -> tuple[HiddenSoftwareTask, IndependentSoftwareSelection]:
    """Prepare the rollback probe by reusing the acquired alias-patch tool.

    The rollback probe tests transactional restoration, not fresh proposal discovery.
    Re-running the complete multi-candidate search here adds no adaptive evidence and
    needlessly multiplies disposable runtimes.  The lineage therefore instantiates the
    already acquired ``interpreter_add_alias`` template for the new public token, while
    the independent validator still receives the complete hidden and regression suites
    and remains the sole release authority.
    """
    task = build_hidden_modular_task(snapshot.accepted_body, ordinal=ordinal, protocol_digest=protocol.digest())
    if task.public.expected_changed_modules != ('interpretation',) or not task.public.public_cases:
        raise ModularLineageError('rollback probe is not an alias-only software task')
    metadata = module_metadata(snapshot.accepted_body.source('interpretation'))
    aliases = metadata.get('aliases')
    if not isinstance(aliases, Mapping):
        raise ModularLineageError('accepted interpreter lacks reusable alias metadata')
    reusable = any((record.template_id == 'interpreter_add_alias' for record in snapshot.patch_registry))
    if not reusable or not memory.has_success('interpreter_add_alias'):
        raise ModularLineageError('rollback probe lacks the acquired alias-patch tool')
    token = task.public.public_cases[0].request.split()[0].lower()
    updated_aliases = {str(key): str(value) for key, value in aliases.items()}
    updated_aliases[token] = 'add'
    generated_cases = tuple((SoftwareCase(f'case_{task.public.task_id}_{index}', case.request, case.expected, task.public.task_id) for index, case in enumerate(task.public.public_cases, start=1)))
    candidate = snapshot.accepted_body.replace_modules({'interpretation': render_interpretation(updated_aliases)}, added_regression_cases=generated_cases)
    patch = SoftwarePatch(template_id='interpreter_add_alias', diagnosed_module='interpretation', changed_modules=('interpretation',), added_modules=(), parent_body_digest=snapshot.accepted_body.digest(), candidate_body=candidate, generated_case_ids=tuple((case.case_id for case in generated_cases)), public_passes=0, public_total=len(task.public.public_cases), memory_bias=memory.template_bias('interpreter_add_alias'), evidence_case_ids=tuple((case.case_id for case in task.public.public_cases)), source_delta_bytes=candidate.total_source_bytes - snapshot.accepted_body.total_source_bytes)
    diagnosis = ModuleDiagnosis(module='interpretation', reason='reuse acquired alias-patch template for rollback probe', evidence_case_ids=tuple((case.case_id for case in task.public.public_cases)), unknown_token=token)
    lower_bound = max(4096, len(snapshot.accepted_body.modules) * 1024)
    search = PatchSearchResult(status=PatchSearchStatus.READY, diagnosis=diagnosis, incumbent_case_results=(), proposals=(patch,), generated_patches=1, invalid_patches=0, program_space_lower_bound=lower_bound, exploration_fraction_ppm=1000000 // lower_bound, reused_causal_memory=True, sandbox_runs=0, working_memory_bytes=len(patch.candidate_body.to_bytes()), time_budget_respected=True, complete_program_space_enumerated=False)
    _validate_search_contract(search, protocol)
    selection = validate_ranked_software_patches_independently(snapshot.accepted_body, task, search, protocol.resources, protected_cases=protected_cases)
    if not selection.accepted:
        raise ModularLineageError('rollback probe lacks a valid software patch')
    return (task, selection)

def _run_forced_rollback(store: VersionedSoftwareStore, memory: CausalSoftwareMemory, protocol: M047Protocol, protected_cases: Sequence[SoftwareCase]=()) -> tuple[ModularRollbackRecord, IndependentSoftwareSelection]:
    before = store.current
    before_checkpoint = _checkpoint(before, memory)
    task, selection = _prepare_valid_selection(before, memory, protocol, protocol.rollback_task_ordinal, protected_cases)
    receipt = store.adopt(selection, forced_fault=SoftwareFaultKind(protocol.rollback_fault))
    after_checkpoint = _checkpoint(store.current, memory)
    combined_exact = before_checkpoint.combined_digest == after_checkpoint.combined_digest
    if not receipt.exact_restoration or store.current != before or (not combined_exact):
        raise ModularLineageError('forced software fault did not restore the combined checkpoint')
    record = ModularRollbackRecord(task_digest=task.digest(), attempted_version=receipt.attempted_version, restored_version=receipt.committed_version, lineage_exact_restoration=receipt.exact_restoration, memory_unchanged=before_checkpoint.memory_digest == after_checkpoint.memory_digest, combined_checkpoint_before=before_checkpoint.combined_digest, combined_checkpoint_after=after_checkpoint.combined_digest, combined_checkpoint_exact_restoration=combined_exact, forced_fault=protocol.rollback_fault)
    return (record, selection)
