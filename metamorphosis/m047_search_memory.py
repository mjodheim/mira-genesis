from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json

class ModularSearchError(ValueError):
    """Raised when an M047 search contract or resource bound is violated."""

class PatchSearchStatus(str, Enum):
    READY = 'ready'
    INSUFFICIENT_DIAGNOSIS = 'insufficient_diagnosis'
    RESOURCE_BUDGET_EXHAUSTED = 'resource_budget_exhausted'

@dataclass(frozen=True)
class ModularResourceBudget:
    max_public_cases: int = 8
    max_generated_patches: int = 8
    max_validation_attempts: int = 4
    max_total_source_bytes: int = 131072
    max_working_memory_bytes: int = 262144
    max_causal_memory_bytes: int = 262144
    max_search_seconds: float = 60.0
    sandbox_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        for name, value in (('max_public_cases', self.max_public_cases), ('max_generated_patches', self.max_generated_patches), ('max_validation_attempts', self.max_validation_attempts), ('max_total_source_bytes', self.max_total_source_bytes), ('max_working_memory_bytes', self.max_working_memory_bytes), ('max_causal_memory_bytes', self.max_causal_memory_bytes)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ModularSearchError(f'{name} must be a positive integer')
        for name, value in (('max_search_seconds', self.max_search_seconds), ('sandbox_timeout_seconds', self.sandbox_timeout_seconds)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ModularSearchError(f'{name} must be positive')

    def to_dict(self) -> dict[str, object]:
        return {'max_public_cases': self.max_public_cases, 'max_generated_patches': self.max_generated_patches, 'max_validation_attempts': self.max_validation_attempts, 'max_total_source_bytes': self.max_total_source_bytes, 'max_working_memory_bytes': self.max_working_memory_bytes, 'max_causal_memory_bytes': self.max_causal_memory_bytes, 'max_search_seconds': self.max_search_seconds, 'sandbox_timeout_seconds': self.sandbox_timeout_seconds}

def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()

@dataclass(frozen=True)
class SoftwareProposalEpisode:
    task_id: str
    outcome: str
    diagnosed_module: str | None
    selected_template: str | None
    exact_rejected_templates: tuple[str, ...]
    dominated_templates: tuple[str, ...]
    generated_patches: int
    validation_attempts: int
    reason: str

    def __post_init__(self) -> None:
        if self.outcome not in {'accepted', 'insufficient_evidence'}:
            raise ModularSearchError('unsupported software proposal outcome')
        if self.generated_patches < 0 or self.validation_attempts < 0:
            raise ModularSearchError('software proposal counters must be non-negative')

    def to_dict(self) -> dict[str, object]:
        return {'task_id': self.task_id, 'outcome': self.outcome, 'diagnosed_module': self.diagnosed_module, 'selected_template': self.selected_template, 'exact_rejected_templates': list(self.exact_rejected_templates), 'dominated_templates': list(self.dominated_templates), 'generated_patches': self.generated_patches, 'validation_attempts': self.validation_attempts, 'reason': self.reason}

@dataclass(frozen=True)
class CausalSoftwareMemory:
    episodes: tuple[SoftwareProposalEpisode, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {'schema': 'm047-causal-software-memory-v1', 'episodes': [episode.to_dict() for episode in self.episodes]}

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(b'm047-causal-software-memory-v1\x00' + self.to_bytes()).hexdigest()

    def append(self, episode: SoftwareProposalEpisode, *, maximum_bytes: int) -> 'CausalSoftwareMemory':
        updated = CausalSoftwareMemory(self.episodes + (episode,))
        if len(updated.to_bytes()) > maximum_bytes:
            raise ModularSearchError('causal software memory budget exhausted')
        return updated

    def template_bias(self, template_id: str) -> int:
        successes = 0
        exact_rejections = 0
        dominated = 0
        for episode in self.episodes:
            if episode.outcome == 'accepted' and episode.selected_template == template_id:
                successes += 1
            exact_rejections += episode.exact_rejected_templates.count(template_id)
            dominated += episode.dominated_templates.count(template_id)
        return successes * 25 - exact_rejections * 30 - dominated

    def has_success(self, template_id: str) -> bool:
        return any((episode.outcome == 'accepted' and episode.selected_template == template_id for episode in self.episodes))

    @property
    def accepted_episodes(self) -> int:
        return sum((episode.outcome == 'accepted' for episode in self.episodes))

    @property
    def failure_evidence_count(self) -> int:
        return sum((len(episode.exact_rejected_templates) + len(episode.dominated_templates) + (1 if episode.outcome == 'insufficient_evidence' else 0) for episode in self.episodes))
