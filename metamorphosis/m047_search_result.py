from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from metamorphosis.m047_search_memory import PatchSearchStatus, _domain_digest
from metamorphosis.m047_search_diagnostic_model import ModuleDiagnosis
from metamorphosis.m047_search_proposal import SoftwarePatch

@dataclass(frozen=True)
class PatchSearchResult:
    status: PatchSearchStatus
    diagnosis: ModuleDiagnosis
    incumbent_case_results: tuple[Mapping[str, object], ...]
    proposals: tuple[SoftwarePatch, ...]
    generated_patches: int
    invalid_patches: int
    program_space_lower_bound: int
    exploration_fraction_ppm: int
    reused_causal_memory: bool
    sandbox_runs: int
    working_memory_bytes: int
    time_budget_respected: bool
    complete_program_space_enumerated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            'status': self.status.value,
            'diagnosis': self.diagnosis.to_dict(),
            'incumbent_case_results': [dict(item) for item in self.incumbent_case_results],
            'proposal_digests': [proposal.digest() for proposal in self.proposals],
            'proposal_templates': [proposal.template_id for proposal in self.proposals],
            'generated_patches': self.generated_patches,
            'invalid_patches': self.invalid_patches,
            'program_space_lower_bound': self.program_space_lower_bound,
            'exploration_fraction_ppm': self.exploration_fraction_ppm,
            'reused_causal_memory': self.reused_causal_memory,
            'sandbox_runs': self.sandbox_runs,
            'working_memory_bytes': self.working_memory_bytes,
            'time_budget_respected': self.time_budget_respected,
            'complete_program_space_enumerated': self.complete_program_space_enumerated,
        }

    def digest(self) -> str:
        return _domain_digest(b'm047-patch-search-result-v1\x00', self.to_dict())
