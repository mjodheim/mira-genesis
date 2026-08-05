from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Sequence
from metamorphosis.m047_search import SoftwarePatch
from metamorphosis.m047_software_body import SoftwareBody
from metamorphosis.m047_lineage_protocol import ModularLineageError, _canonical_json, _domain_digest

@dataclass(frozen=True)
class PatchToolRecord:
    patch_digest: str
    task_id: str
    template_id: str
    diagnosed_module: str
    changed_modules: tuple[str, ...]
    added_modules: tuple[str, ...]
    adopted_version: int
    validation_report_digest: str
    candidate_body_digest: str
    generated_test_count: int

    def to_dict(self) -> dict[str, object]:
        return {'patch_digest': self.patch_digest, 'task_id': self.task_id, 'template_id': self.template_id, 'diagnosed_module': self.diagnosed_module, 'changed_modules': list(self.changed_modules), 'added_modules': list(self.added_modules), 'adopted_version': self.adopted_version, 'validation_report_digest': self.validation_report_digest, 'candidate_body_digest': self.candidate_body_digest, 'generated_test_count': self.generated_test_count}

    def digest(self) -> str:
        return _domain_digest(b'm047-patch-tool-record-v1\x00', self.to_dict())

def patch_registry_digest(registry: Sequence[PatchToolRecord]) -> str:
    return _domain_digest(b'm047-patch-registry-v1\x00', [record.to_dict() for record in registry])

@dataclass(frozen=True)
class SoftwareJournalEntry:
    sequence: int
    event: str
    parent_snapshot_digest: str
    child_core_digest: str
    patch_digest: str
    validation_report_digest: str
    accepted_body_digest: str
    patch_registry_digest: str
    previous_entry_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {'sequence': self.sequence, 'event': self.event, 'parent_snapshot_digest': self.parent_snapshot_digest, 'child_core_digest': self.child_core_digest, 'patch_digest': self.patch_digest, 'validation_report_digest': self.validation_report_digest, 'accepted_body_digest': self.accepted_body_digest, 'patch_registry_digest': self.patch_registry_digest, 'previous_entry_digest': self.previous_entry_digest}

    def digest(self) -> str:
        return _domain_digest(b'm047-software-journal-entry-v1\x00', self.to_dict())

def software_journal_digest(journal: Sequence[SoftwareJournalEntry]) -> str:
    return _domain_digest(b'm047-software-journal-v1\x00', [entry.to_dict() for entry in journal])

@dataclass(frozen=True)
class SoftwareSnapshot:
    version: int
    accepted_body: SoftwareBody
    patch_registry: tuple[PatchToolRecord, ...]
    accepted_task_ids: tuple[str, ...]
    causal_journal: tuple[SoftwareJournalEntry, ...]

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 0:
            raise ModularLineageError('software snapshot version must be non-negative')

    def core_mapping(self) -> dict[str, object]:
        return {'version': self.version, 'accepted_body_digest': self.accepted_body.digest(), 'patch_registry_digest': patch_registry_digest(self.patch_registry), 'accepted_task_ids': list(self.accepted_task_ids)}

    def core_digest(self) -> str:
        return _domain_digest(b'm047-software-snapshot-core-v1\x00', self.core_mapping())

    def to_dict(self) -> dict[str, object]:
        return {'schema': 'm047-software-snapshot-v1', 'version': self.version, 'accepted_body': self.accepted_body.to_dict(), 'patch_registry': [record.to_dict() for record in self.patch_registry], 'accepted_task_ids': list(self.accepted_task_ids), 'causal_journal': [entry.to_dict() for entry in self.causal_journal]}

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(b'm047-software-snapshot-v1\x00' + self.to_bytes()).hexdigest()

def initial_software_snapshot(body: SoftwareBody) -> SoftwareSnapshot:
    snapshot = SoftwareSnapshot(0, body, (), (), ())
    audit_software_snapshot(snapshot)
    return snapshot

def audit_software_snapshot(snapshot: SoftwareSnapshot, *, expected_report_digest: str | None=None, expected_patch: SoftwarePatch | None=None) -> None:
    if snapshot.version == 0:
        if snapshot.patch_registry or snapshot.accepted_task_ids or snapshot.causal_journal:
            raise ModularLineageError('version-zero software snapshot must be empty')
        return
    if not len(snapshot.patch_registry) == len(snapshot.accepted_task_ids) == len(snapshot.causal_journal) == snapshot.version:
        raise ModularLineageError('software snapshot versioned components are discontinuous')
    previous: str | None = None
    for index, entry in enumerate(snapshot.causal_journal, start=1):
        if entry.sequence != index:
            raise ModularLineageError('software journal sequence is discontinuous')
        if entry.previous_entry_digest != previous:
            raise ModularLineageError('software journal hash chain is broken')
        previous = entry.digest()
    last = snapshot.causal_journal[-1]
    if last.child_core_digest != snapshot.core_digest():
        raise ModularLineageError('software journal child core mismatch')
    if last.accepted_body_digest != snapshot.accepted_body.digest():
        raise ModularLineageError('software journal body identity mismatch')
    if last.patch_registry_digest != patch_registry_digest(snapshot.patch_registry):
        raise ModularLineageError('software journal registry identity mismatch')
    if last.patch_digest != snapshot.patch_registry[-1].patch_digest:
        raise ModularLineageError('software journal patch identity mismatch')
    if last.validation_report_digest != snapshot.patch_registry[-1].validation_report_digest:
        raise ModularLineageError('software journal validation identity mismatch')
    if expected_report_digest is not None:
        if last.validation_report_digest != expected_report_digest:
            raise ModularLineageError('software snapshot does not bind validation report')
    if expected_patch is not None:
        if last.patch_digest != expected_patch.digest():
            raise ModularLineageError('software snapshot does not bind accepted patch')
        if snapshot.accepted_body.digest() != expected_patch.candidate_body.digest():
            raise ModularLineageError('software snapshot body differs from accepted patch')
