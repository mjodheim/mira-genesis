from __future__ import annotations
from dataclasses import replace
import hashlib
from metamorphosis.m047_search import CausalSoftwareMemory, ModularSearchError
from metamorphosis.m047_software_body import BASELINE_CASES, SoftwareBodyError, founder_software_body
from metamorphosis.m047_task import ModularTaskError
from metamorphosis.m047_lineage_store import M047_PROTOCOL, M047Protocol, ModularLineageError, VersionedSoftwareStore, initial_software_snapshot, patch_registry_digest, software_journal_digest
from metamorphosis.m047_lineage_records import ModularSoftwareManifest
from metamorphosis.m047_lineage_cycles import _run_accepted_cycle, _run_forced_rollback, _run_terminal_challenge
from metamorphosis.m047_lineage_replay import _M047ExecutionArtifacts, _replay_execution_artifacts, _retained_cases

def _execute_with_artifacts(protocol: M047Protocol) -> _M047ExecutionArtifacts:
    founder = founder_software_body()
    initial = initial_software_snapshot(founder)
    store = VersionedSoftwareStore(initial)
    memory = CausalSoftwareMemory()
    cycles: list[ModularCycleRecord] = []
    checkpoints: list[ModularCheckpoint] = []
    protected_cases: list[SoftwareCase] = []
    selections: list[IndependentSoftwareSelection] = []
    episodes: list[SoftwareProposalEpisode] = []
    for ordinal in range(1, protocol.accepted_cycles + 1):
        memory, cycle, task, selection, episode = _run_accepted_cycle(store, memory, protocol, ordinal=ordinal, protected_cases=tuple(protected_cases))
        cycles.append(cycle)
        checkpoints.append(cycle.checkpoint)
        selections.append(selection)
        episodes.append(episode)
        protected_cases.extend(task.hidden_cases)
    rollback, rollback_selection = _run_forced_rollback(store, memory, protocol, tuple(protected_cases))
    memory, terminal, terminal_episode = _run_terminal_challenge(store, memory, protocol, tuple(protected_cases))
    final = store.current
    retained_case_count = len(BASELINE_CASES) + len(final.accepted_body.regression_cases) + len(protected_cases)
    if final.version != protocol.accepted_cycles:
        raise ModularLineageError('M047 final software version is incorrect')
    if len(final.patch_registry) != protocol.accepted_cycles:
        raise ModularLineageError('M047 did not retain every accepted patch tool')
    if len(final.causal_journal) != protocol.accepted_cycles:
        raise ModularLineageError('M047 software journal is incomplete')
    if len(final.accepted_body.regression_cases) != protocol.accepted_cycles * 2:
        raise ModularLineageError('M047 generated regression suite is incomplete')
    if 'tool_mean' not in final.accepted_body.module_names():
        raise ModularLineageError('M047 lost its synthesized mean tool')
    if memory.accepted_episodes != protocol.accepted_cycles:
        raise ModularLineageError('M047 causal memory lost accepted episodes')
    if memory.failure_evidence_count <= 0:
        raise ModularLineageError('M047 causal memory contains no failure evidence')
    checkpoints_verified = all((checkpoint.version == index and checkpoint.snapshot_digest == cycles[index - 1].adopted_snapshot_digest and (checkpoint.memory_digest == cycles[index - 1].causal_memory_digest) for index, checkpoint in enumerate(checkpoints, start=1)))
    all_resources = all((cycle.generated_patches <= protocol.resources.max_generated_patches and cycle.validation_attempts <= protocol.resources.max_validation_attempts and (cycle.working_memory_bytes <= protocol.resources.max_working_memory_bytes) and cycle.time_budget_respected for cycle in cycles))
    all_non_exhaustive = all((not cycle.complete_program_space_enumerated and cycle.generated_patches < cycle.program_space_lower_bound for cycle in cycles))
    manifest = ModularSoftwareManifest(protocol_digest=protocol.digest(), founder_body_digest=founder.digest(), founder_snapshot_digest=initial.digest(), founder_module_count=len(founder.modules), cycles=tuple(cycles), checkpoints=tuple(checkpoints), rollback=rollback, terminal=terminal, final_snapshot_digest=final.digest(), final_snapshot_bytes_sha256=hashlib.sha256(final.to_bytes()).hexdigest(), final_body_digest=final.accepted_body.digest(), final_body_source_bytes=final.accepted_body.total_source_bytes, final_module_count=len(final.accepted_body.modules), final_regression_test_count=len(final.accepted_body.regression_cases), final_patch_registry_digest=patch_registry_digest(final.patch_registry), final_journal_digest=software_journal_digest(final.causal_journal), final_patch_registry_count=len(final.patch_registry), final_journal_entries=len(final.causal_journal), final_causal_memory_digest=memory.digest(), final_causal_memory_bytes=len(memory.to_bytes()), final_causal_memory_episodes=len(memory.episodes), final_causal_failure_evidence_count=memory.failure_evidence_count, retained_validation_case_count=retained_case_count, retained_validation_all_passed=True, accepted_cycle_count=len(cycles), patch_template_reuse_cycles=sum((cycle.reused_patch_template for cycle in cycles)), causal_memory_reuse_cycles=sum((cycle.reused_causal_memory for cycle in cycles)), acquired_runtime_tool_reuse_cycles=sum((cycle.required_runtime_tool_reused for cycle in cycles)), all_module_diagnoses_correct=all((cycle.module_diagnosis_correct for cycle in cycles)), all_generated_tests_persisted=len(final.accepted_body.regression_cases) == sum((cycle.generated_tests_added for cycle in cycles)), all_independent_validations_disposable=all((cycle.independent_hidden_validation and cycle.disposable_runtime_validation for cycle in cycles)), all_resource_budgets_respected=all_resources, all_searches_non_exhaustive=all_non_exhaustive, checkpoints_verified=checkpoints_verified, replay_identical=False)
    return _M047ExecutionArtifacts(manifest=manifest, selections=tuple(selections), episodes=tuple(episodes), rollback_selection=rollback_selection, terminal_episode=terminal_episode)

def _execute_once(protocol: M047Protocol) -> ModularSoftwareManifest:
    return _execute_with_artifacts(protocol).manifest

def run_m047_modular_software_lineage(protocol: M047Protocol=M047_PROTOCOL) -> ModularSoftwareManifest:
    """Execute once, then replay every accepted source patch and exact checkpoint."""
    try:
        artifacts = _execute_with_artifacts(protocol)
        _replay_execution_artifacts(artifacts, protocol)
    except (ModularSearchError, ModularTaskError, SoftwareBodyError) as exc:
        raise ModularLineageError(str(exc)) from exc
    return replace(artifacts.manifest, replay_identical=True)
