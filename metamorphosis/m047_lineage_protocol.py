from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json
from metamorphosis.m047_search import ModularResourceBudget

class ModularLineageError(RuntimeError):
    """Raised when the single integrated M047 experiment fails closed."""

PROTOCOL_SCHEMA = 'm047-modular-software-lineage-protocol-v1'

MANIFEST_SCHEMA = 'm047-modular-software-lineage-manifest-v1'

def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()

class SoftwareFaultKind(str, Enum):
    JOURNAL = 'journal'

@dataclass(frozen=True)
class M047Protocol:
    accepted_cycles: int = 6
    rollback_fault: str = SoftwareFaultKind.JOURNAL.value
    rollback_task_ordinal: int = 7
    terminal_task_ordinal: int = 8
    resources: ModularResourceBudget = ModularResourceBudget()
    schema: str = PROTOCOL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROTOCOL_SCHEMA:
            raise ModularLineageError('unsupported M047 protocol schema')
        if self.accepted_cycles != 6:
            raise ModularLineageError('M047 fixes six accepted software adaptations')
        if self.rollback_fault != SoftwareFaultKind.JOURNAL.value:
            raise ModularLineageError('M047 fixes causal-journal corruption as rollback probe')
        if self.rollback_task_ordinal != 7 or self.terminal_task_ordinal != 8:
            raise ModularLineageError('M047 fixes one rollback and one terminal task')
        if self.resources != ModularResourceBudget():
            raise ModularLineageError('M047 resource bounds are frozen as one experiment')

    def to_dict(self) -> dict[str, object]:
        return {'schema': self.schema, 'accepted_cycles': self.accepted_cycles, 'rollback_fault': self.rollback_fault, 'rollback_task_ordinal': self.rollback_task_ordinal, 'terminal_task_ordinal': self.terminal_task_ordinal, 'resources': self.resources.to_dict()}

    def digest(self) -> str:
        return _domain_digest(b'm047-protocol-v1\x00', self.to_dict())

M047_PROTOCOL = M047Protocol()
