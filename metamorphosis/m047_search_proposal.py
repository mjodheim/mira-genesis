from __future__ import annotations
from dataclasses import dataclass
from metamorphosis.m047_software_body import SoftwareBody
from metamorphosis.m047_search_memory import ModularSearchError, _domain_digest

@dataclass(frozen=True)
class SoftwarePatch:
    template_id: str
    diagnosed_module: str
    changed_modules: tuple[str, ...]
    added_modules: tuple[str, ...]
    parent_body_digest: str
    candidate_body: SoftwareBody
    generated_case_ids: tuple[str, ...]
    public_passes: int
    public_total: int
    memory_bias: int
    evidence_case_ids: tuple[str, ...]
    source_delta_bytes: int

    def __post_init__(self) -> None:
        if not self.changed_modules:
            raise ModularSearchError('software patch changes no modules')
        if self.public_total <= 0 or not 0 <= self.public_passes <= self.public_total:
            raise ModularSearchError('invalid public patch score')
        if self.candidate_body.digest() == self.parent_body_digest:
            raise ModularSearchError('software patch is a no-op')

    @property
    def ranking_score(self) -> int:
        return self.public_passes * 1000 // self.public_total + self.memory_bias

    def to_dict(self) -> dict[str, object]:
        return {
            'template_id': self.template_id,
            'diagnosed_module': self.diagnosed_module,
            'changed_modules': list(self.changed_modules),
            'added_modules': list(self.added_modules),
            'parent_body_digest': self.parent_body_digest,
            'candidate_body_digest': self.candidate_body.digest(),
            'candidate_module_digests': {
                module.name: module.digest() for module in self.candidate_body.modules
            },
            'candidate_regression_case_ids': [
                case.case_id for case in self.candidate_body.regression_cases
            ],
            'generated_case_ids': list(self.generated_case_ids),
            'public_passes': self.public_passes,
            'public_total': self.public_total,
            'memory_bias': self.memory_bias,
            'ranking_score': self.ranking_score,
            'evidence_case_ids': list(self.evidence_case_ids),
            'source_delta_bytes': self.source_delta_bytes,
        }

    def digest(self) -> str:
        return _domain_digest(b'm047-software-patch-v1\x00', self.to_dict())
