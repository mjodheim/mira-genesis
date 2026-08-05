from __future__ import annotations
from typing import Sequence
from metamorphosis.m047_search import CausalSoftwareMemory, PatchSearchStatus, SoftwareProposalEpisode, heuristic_software_patch_search
from metamorphosis.m047_software_body import SoftwareCase
from metamorphosis.m047_task import StopAction, build_hidden_modular_task, validate_ranked_software_patches_independently
from metamorphosis.m047_lineage_store import M047Protocol, ModularLineageError, VersionedSoftwareStore
from metamorphosis.m047_lineage_records import ModularTerminalRecord
from metamorphosis.m047_cycle_acceptance import _dominated_templates

def _run_terminal_challenge(store: VersionedSoftwareStore, memory: CausalSoftwareMemory, protocol: M047Protocol, protected_cases: Sequence[SoftwareCase]=()) -> tuple[CausalSoftwareMemory, ModularTerminalRecord, SoftwareProposalEpisode]:
    before = store.current
    task = build_hidden_modular_task(before.accepted_body, ordinal=protocol.terminal_task_ordinal, protocol_digest=protocol.digest())
    search = heuristic_software_patch_search(before.accepted_body, task.public.task_id, task.public.public_cases, memory, protocol.resources)
    if search.complete_program_space_enumerated:
        raise ModularLineageError('terminal software task enumerated program space')
    selection = validate_ranked_software_patches_independently(before.accepted_body, task, search, protocol.resources, protected_cases=protected_cases)
    if selection.accepted:
        raise ModularLineageError('terminal compound task unexpectedly earned release authority')
    if selection.report.action is not StopAction.TERMINATE_INSUFFICIENT_EVIDENCE:
        raise ModularLineageError('terminal software task did not fail closed')
    if store.current != before:
        raise ModularLineageError('terminal software task modified the accepted body')
    episode = SoftwareProposalEpisode(task_id=task.public.task_id, outcome='insufficient_evidence', diagnosed_module=search.diagnosis.module, selected_template=None, exact_rejected_templates=selection.rejected_templates, dominated_templates=_dominated_templates(search, selection), generated_patches=search.generated_patches, validation_attempts=len(selection.report.attempts), reason=selection.report.reason)
    updated_memory = memory.append(episode, maximum_bytes=protocol.resources.max_causal_memory_bytes)
    record = ModularTerminalRecord(task_digest=task.digest(), public_task_digest=task.public.digest(), family=task.family, search_digest=search.digest(), selection_digest=selection.digest(), diagnosed_module=search.diagnosis.module, stop_action=selection.report.action.value, stop_reason=selection.report.reason, validation_attempts=len(selection.report.attempts), independent_rejections=len(selection.rejected_templates), parent_snapshot_digest=before.digest(), final_snapshot_digest=store.current.digest(), body_unchanged=store.current == before, explicit_insufficient_evidence_termination=True, memory_digest_after_failure=updated_memory.digest(), failure_evidence_count_after=updated_memory.failure_evidence_count)
    return (updated_memory, record, episode)
