from __future__ import annotations
from dataclasses import dataclass, replace
from metamorphosis.m047_software_body import SoftwareBodyError
from metamorphosis.m047_task import IndependentSoftwareSelection
from metamorphosis.m047_lineage_protocol import ModularLineageError, SoftwareFaultKind, _domain_digest
from metamorphosis.m047_lineage_state import PatchToolRecord, SoftwareJournalEntry, SoftwareSnapshot, audit_software_snapshot, patch_registry_digest

@dataclass(frozen=True)
class SoftwareAdoptionReceipt:
    adopted: bool
    exact_restoration: bool
    reason: str
    before_snapshot_digest: str
    after_snapshot_digest: str
    before_snapshot_bytes: bytes
    after_snapshot_bytes: bytes
    attempted_version: int
    committed_version: int
    forced_fault: str | None

def stage_software_adoption(snapshot: SoftwareSnapshot, selection: IndependentSoftwareSelection) -> SoftwareSnapshot:
    if not selection.accepted or selection.selected_patch is None or selection.candidate_body is None:
        raise ModularLineageError('only an accepted software selection may be staged')
    patch = selection.selected_patch
    report = selection.report
    if report.parent_body_digest != snapshot.accepted_body.digest():
        raise ModularLineageError('software validation report is stale')
    if report.selected_patch_digest != patch.digest():
        raise ModularLineageError('software report does not bind the patch')
    if report.candidate_body_digest != selection.candidate_body.digest():
        raise ModularLineageError('software report does not bind the candidate body')
    if patch.parent_body_digest != snapshot.accepted_body.digest():
        raise ModularLineageError('software patch parent is stale')
    if patch.candidate_body.digest() != selection.candidate_body.digest():
        raise ModularLineageError('selected software candidate mismatch')
    version = snapshot.version + 1
    if any((record.patch_digest == patch.digest() for record in snapshot.patch_registry)):
        raise ModularLineageError('software patch is already registered')
    record = PatchToolRecord(patch_digest=patch.digest(), task_id=report.public_task_digest, template_id=patch.template_id, diagnosed_module=patch.diagnosed_module, changed_modules=patch.changed_modules, added_modules=patch.added_modules, adopted_version=version, validation_report_digest=report.digest(), candidate_body_digest=patch.candidate_body.digest(), generated_test_count=len(patch.candidate_body.regression_cases) - len(snapshot.accepted_body.regression_cases))
    registry = snapshot.patch_registry + (record,)
    task_ids = snapshot.accepted_task_ids + (report.public_task_digest,)
    core_mapping = {'version': version, 'accepted_body_digest': patch.candidate_body.digest(), 'patch_registry_digest': patch_registry_digest(registry), 'accepted_task_ids': list(task_ids)}
    previous = None if not snapshot.causal_journal else snapshot.causal_journal[-1].digest()
    entry = SoftwareJournalEntry(sequence=version, event='adopt_validated_software_patch', parent_snapshot_digest=snapshot.digest(), child_core_digest=_domain_digest(b'm047-software-snapshot-core-v1\x00', core_mapping), patch_digest=patch.digest(), validation_report_digest=report.digest(), accepted_body_digest=patch.candidate_body.digest(), patch_registry_digest=patch_registry_digest(registry), previous_entry_digest=previous)
    staged = SoftwareSnapshot(version, patch.candidate_body, registry, task_ids, snapshot.causal_journal + (entry,))
    audit_software_snapshot(staged, expected_report_digest=report.digest(), expected_patch=patch)
    return staged

def _corrupt_snapshot(snapshot: SoftwareSnapshot, fault: SoftwareFaultKind) -> SoftwareSnapshot:
    if snapshot.version == 0:
        raise ModularLineageError('cannot corrupt a version-zero software snapshot')
    if fault is SoftwareFaultKind.JOURNAL:
        last = replace(snapshot.causal_journal[-1], patch_digest='0' * 64)
        return replace(snapshot, causal_journal=snapshot.causal_journal[:-1] + (last,))
    raise TypeError(f'unsupported software fault: {fault!r}')

class VersionedSoftwareStore:
    """Transactional storage for exact modular-software checkpoints."""

    def __init__(self, initial: SoftwareSnapshot) -> None:
        audit_software_snapshot(initial)
        self.current = initial
        self._versions = {initial.version: initial}

    def adopt(self, selection: IndependentSoftwareSelection, *, forced_fault: SoftwareFaultKind | None=None) -> SoftwareAdoptionReceipt:
        before = self.current
        before_bytes = before.to_bytes()
        before_digest = before.digest()
        attempted = before.version + 1
        if not selection.accepted:
            return SoftwareAdoptionReceipt(False, False, 'validation selection was not accepted', before_digest, before_digest, before_bytes, before_bytes, attempted, before.version, None if forced_fault is None else forced_fault.value)
        try:
            staged = stage_software_adoption(before, selection)
            self.current = staged
            if forced_fault is not None:
                self.current = _corrupt_snapshot(self.current, forced_fault)
            audit_software_snapshot(self.current, expected_report_digest=selection.report.digest(), expected_patch=selection.selected_patch)
        except (ModularLineageError, SoftwareBodyError, ValueError) as exc:
            self.current = before
            if self.current.to_bytes() != before_bytes or self.current.digest() != before_digest:
                raise ModularLineageError('software rollback failed to restore exact checkpoint') from exc
            return SoftwareAdoptionReceipt(False, True, str(exc), before_digest, self.current.digest(), before_bytes, self.current.to_bytes(), attempted, self.current.version, None if forced_fault is None else forced_fault.value)
        self._versions[self.current.version] = self.current
        return SoftwareAdoptionReceipt(True, False, 'adopted', before_digest, self.current.digest(), before_bytes, self.current.to_bytes(), attempted, self.current.version, None if forced_fault is None else forced_fault.value)

    def rollback_to(self, version: int) -> SoftwareAdoptionReceipt:
        if version not in self._versions:
            raise ModularLineageError('requested software rollback version is not archived')
        before = self.current
        target = self._versions[version]
        self.current = target
        audit_software_snapshot(target)
        return SoftwareAdoptionReceipt(False, True, 'explicit software version rollback', before.digest(), target.digest(), before.to_bytes(), target.to_bytes(), before.version, target.version, None)
