from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from metamorphosis.m047_search import CausalSoftwareMemory, SoftwareProposalEpisode
from metamorphosis.m047_software_body import BASELINE_CASES, SoftwareCase, founder_software_body
from metamorphosis.m047_task import HiddenSoftwareTask, IndependentSoftwareSelection
from metamorphosis.m047_lineage_store import M047Protocol, ModularLineageError, SoftwareFaultKind, VersionedSoftwareStore, _domain_digest, initial_software_snapshot, patch_registry_digest, software_journal_digest, stage_software_adoption
from metamorphosis.m047_lineage_records import ModularSoftwareManifest, _checkpoint

def _retained_cases(tasks: Sequence[HiddenSoftwareTask]) -> tuple[SoftwareCase, ...]:
    cases: list[SoftwareCase] = list(BASELINE_CASES)
    for task in tasks:
        cases.extend(task.public.public_cases)
        cases.extend(task.hidden_cases)
    return tuple(cases)

@dataclass(frozen=True)
class _M047ExecutionArtifacts:
    manifest: ModularSoftwareManifest
    selections: tuple[IndependentSoftwareSelection, ...]
    episodes: tuple[SoftwareProposalEpisode, ...]
    rollback_selection: IndependentSoftwareSelection
    terminal_episode: SoftwareProposalEpisode

def _replay_execution_artifacts(artifacts: _M047ExecutionArtifacts, protocol: M047Protocol) -> str:
    founder = founder_software_body()
    store = VersionedSoftwareStore(initial_software_snapshot(founder))
    memory = CausalSoftwareMemory()
    for index, (selection, episode, cycle) in enumerate(zip(artifacts.selections, artifacts.episodes, artifacts.manifest.cycles), start=1):
        receipt = store.adopt(selection)
        if not receipt.adopted or store.current.version != index:
            raise ModularLineageError('M047 accepted-patch replay failed')
        memory = memory.append(episode, maximum_bytes=protocol.resources.max_causal_memory_bytes)
        checkpoint = _checkpoint(store.current, memory)
        if checkpoint.combined_digest != cycle.checkpoint.combined_digest:
            raise ModularLineageError('M047 replay checkpoint diverged')
        if store.current.digest() != cycle.adopted_snapshot_digest:
            raise ModularLineageError('M047 replay snapshot identity diverged')
        if memory.digest() != cycle.causal_memory_digest:
            raise ModularLineageError('M047 replay causal memory diverged')
    before = _checkpoint(store.current, memory)
    rollback = store.adopt(artifacts.rollback_selection, forced_fault=SoftwareFaultKind(protocol.rollback_fault))
    after = _checkpoint(store.current, memory)
    if not rollback.exact_restoration or before.combined_digest != after.combined_digest or after.combined_digest != artifacts.manifest.rollback.combined_checkpoint_after:
        raise ModularLineageError('M047 replay rollback diverged')
    memory = memory.append(artifacts.terminal_episode, maximum_bytes=protocol.resources.max_causal_memory_bytes)
    manifest = artifacts.manifest
    mapping = {'schema': 'm047-exact-artifact-replay-v1', 'final_snapshot_digest': store.current.digest(), 'final_body_digest': store.current.accepted_body.digest(), 'final_patch_registry_digest': patch_registry_digest(store.current.patch_registry), 'final_journal_digest': software_journal_digest(store.current.causal_journal), 'final_memory_digest': memory.digest(), 'final_memory_bytes': len(memory.to_bytes()), 'checkpoint_count': len(manifest.checkpoints), 'rollback_combined_digest': after.combined_digest}
    if mapping['final_snapshot_digest'] != manifest.final_snapshot_digest:
        raise ModularLineageError('M047 replay final snapshot diverged')
    if mapping['final_body_digest'] != manifest.final_body_digest:
        raise ModularLineageError('M047 replay final body diverged')
    if mapping['final_patch_registry_digest'] != manifest.final_patch_registry_digest:
        raise ModularLineageError('M047 replay patch registry diverged')
    if mapping['final_journal_digest'] != manifest.final_journal_digest:
        raise ModularLineageError('M047 replay journal diverged')
    if mapping['final_memory_digest'] != manifest.final_causal_memory_digest:
        raise ModularLineageError('M047 replay memory diverged')
    return _domain_digest(b'm047-exact-artifact-replay-v1\x00', mapping)
