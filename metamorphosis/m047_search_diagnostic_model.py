from __future__ import annotations
from dataclasses import dataclass
from metamorphosis.m047_search_memory import _domain_digest

@dataclass(frozen=True)
class ModuleDiagnosis:
    module: str | None
    reason: str
    evidence_case_ids: tuple[str, ...]
    unknown_token: str | None = None
    missing_operation: str | None = None

    @property
    def sufficient(self) -> bool:
        return self.module is not None

    def to_dict(self) -> dict[str, object]:
        return {
            'module': self.module,
            'reason': self.reason,
            'evidence_case_ids': list(self.evidence_case_ids),
            'unknown_token': self.unknown_token,
            'missing_operation': self.missing_operation,
            'sufficient': self.sufficient,
        }

    def digest(self) -> str:
        return _domain_digest(b'm047-module-diagnosis-v1\x00', self.to_dict())
