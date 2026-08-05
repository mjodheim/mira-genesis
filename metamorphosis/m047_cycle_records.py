from __future__ import annotations
from dataclasses import dataclass
import hashlib
from metamorphosis.m047_search import CausalSoftwareMemory
from metamorphosis.m047_lineage_state import SoftwareSnapshot
from metamorphosis.m047_lineage_protocol import _domain_digest

@dataclass(frozen=True)
class ModularCheckpoint:
    version: int
    snapshot_digest: str
    snapshot_bytes_sha256: str
    memory_digest: str
    memory_bytes_sha256: str
    combined_digest: str

    def to_dict(self) -> dict[str, object]:
        return {'version': self.version, 'snapshot_digest': self.snapshot_digest, 'snapshot_bytes_sha256': self.snapshot_bytes_sha256, 'memory_digest': self.memory_digest, 'memory_bytes_sha256': self.memory_bytes_sha256, 'combined_digest': self.combined_digest}

def _checkpoint(snapshot: SoftwareSnapshot, memory: CausalSoftwareMemory) -> ModularCheckpoint:
    mapping = {'schema': 'm047-modular-checkpoint-v1', 'version': snapshot.version, 'snapshot_digest': snapshot.digest(), 'snapshot_bytes_sha256': hashlib.sha256(snapshot.to_bytes()).hexdigest(), 'memory_digest': memory.digest(), 'memory_bytes_sha256': hashlib.sha256(memory.to_bytes()).hexdigest()}
    return ModularCheckpoint(version=snapshot.version, snapshot_digest=str(mapping['snapshot_digest']), snapshot_bytes_sha256=str(mapping['snapshot_bytes_sha256']), memory_digest=str(mapping['memory_digest']), memory_bytes_sha256=str(mapping['memory_bytes_sha256']), combined_digest=_domain_digest(b'm047-modular-checkpoint-v1\x00', mapping))

@dataclass(frozen=True)
class ModularCycleRecord:
    ordinal: int
    family: str
    task_digest: str
    public_task_digest: str
    parent_snapshot_digest: str
    parent_body_digest: str
    parent_module_count: int
    parent_regression_test_count: int
    search_digest: str
    search_status: str
    diagnosis_digest: str
    diagnosed_module: str
    diagnosis_reason: str
    generated_patches: int
    invalid_patches: int
    program_space_lower_bound: int
    exploration_fraction_ppm: int
    complete_program_space_enumerated: bool
    search_sandbox_runs: int
    working_memory_bytes: int
    time_budget_respected: bool
    reused_causal_memory: bool
    selection_digest: str
    validation_report_digest: str
    validation_attempts: int
    independent_rejections: int
    selected_patch_digest: str
    selected_template: str
    changed_modules: tuple[str, ...]
    added_modules: tuple[str, ...]
    source_delta_bytes: int
    generated_tests_added: int
    module_diagnosis_correct: bool
    independent_hidden_validation: bool
    disposable_runtime_validation: bool
    adopted_snapshot_digest: str
    adopted_body_digest: str
    adopted_version: int
    adopted_module_count: int
    adopted_regression_test_count: int
    patch_registry_count: int
    causal_journal_entries: int
    reused_patch_template: bool
    required_runtime_tool: str | None
    required_runtime_tool_reused: bool
    causal_memory_digest: str
    causal_memory_episodes: int
    causal_failure_evidence_count: int
    checkpoint: ModularCheckpoint

    def to_dict(self) -> dict[str, object]:
        return {'ordinal': self.ordinal, 'family': self.family, 'task_digest': self.task_digest, 'public_task_digest': self.public_task_digest, 'parent_snapshot_digest': self.parent_snapshot_digest, 'parent_body_digest': self.parent_body_digest, 'parent_module_count': self.parent_module_count, 'parent_regression_test_count': self.parent_regression_test_count, 'search_digest': self.search_digest, 'search_status': self.search_status, 'diagnosis_digest': self.diagnosis_digest, 'diagnosed_module': self.diagnosed_module, 'diagnosis_reason': self.diagnosis_reason, 'generated_patches': self.generated_patches, 'invalid_patches': self.invalid_patches, 'program_space_lower_bound': self.program_space_lower_bound, 'exploration_fraction_ppm': self.exploration_fraction_ppm, 'complete_program_space_enumerated': self.complete_program_space_enumerated, 'search_sandbox_runs': self.search_sandbox_runs, 'working_memory_bytes': self.working_memory_bytes, 'time_budget_respected': self.time_budget_respected, 'reused_causal_memory': self.reused_causal_memory, 'selection_digest': self.selection_digest, 'validation_report_digest': self.validation_report_digest, 'validation_attempts': self.validation_attempts, 'independent_rejections': self.independent_rejections, 'selected_patch_digest': self.selected_patch_digest, 'selected_template': self.selected_template, 'changed_modules': list(self.changed_modules), 'added_modules': list(self.added_modules), 'source_delta_bytes': self.source_delta_bytes, 'generated_tests_added': self.generated_tests_added, 'module_diagnosis_correct': self.module_diagnosis_correct, 'independent_hidden_validation': self.independent_hidden_validation, 'disposable_runtime_validation': self.disposable_runtime_validation, 'adopted_snapshot_digest': self.adopted_snapshot_digest, 'adopted_body_digest': self.adopted_body_digest, 'adopted_version': self.adopted_version, 'adopted_module_count': self.adopted_module_count, 'adopted_regression_test_count': self.adopted_regression_test_count, 'patch_registry_count': self.patch_registry_count, 'causal_journal_entries': self.causal_journal_entries, 'reused_patch_template': self.reused_patch_template, 'required_runtime_tool': self.required_runtime_tool, 'required_runtime_tool_reused': self.required_runtime_tool_reused, 'causal_memory_digest': self.causal_memory_digest, 'causal_memory_episodes': self.causal_memory_episodes, 'causal_failure_evidence_count': self.causal_failure_evidence_count, 'checkpoint': self.checkpoint.to_dict()}

@dataclass(frozen=True)
class ModularRollbackRecord:
    task_digest: str
    attempted_version: int
    restored_version: int
    lineage_exact_restoration: bool
    memory_unchanged: bool
    combined_checkpoint_before: str
    combined_checkpoint_after: str
    combined_checkpoint_exact_restoration: bool
    forced_fault: str

    def to_dict(self) -> dict[str, object]:
        return {'task_digest': self.task_digest, 'attempted_version': self.attempted_version, 'restored_version': self.restored_version, 'lineage_exact_restoration': self.lineage_exact_restoration, 'memory_unchanged': self.memory_unchanged, 'combined_checkpoint_before': self.combined_checkpoint_before, 'combined_checkpoint_after': self.combined_checkpoint_after, 'combined_checkpoint_exact_restoration': self.combined_checkpoint_exact_restoration, 'forced_fault': self.forced_fault}

@dataclass(frozen=True)
class ModularTerminalRecord:
    task_digest: str
    public_task_digest: str
    family: str
    search_digest: str
    selection_digest: str
    diagnosed_module: str | None
    stop_action: str
    stop_reason: str
    validation_attempts: int
    independent_rejections: int
    parent_snapshot_digest: str
    final_snapshot_digest: str
    body_unchanged: bool
    explicit_insufficient_evidence_termination: bool
    memory_digest_after_failure: str
    failure_evidence_count_after: int

    def to_dict(self) -> dict[str, object]:
        return {'task_digest': self.task_digest, 'public_task_digest': self.public_task_digest, 'family': self.family, 'search_digest': self.search_digest, 'selection_digest': self.selection_digest, 'diagnosed_module': self.diagnosed_module, 'stop_action': self.stop_action, 'stop_reason': self.stop_reason, 'validation_attempts': self.validation_attempts, 'independent_rejections': self.independent_rejections, 'parent_snapshot_digest': self.parent_snapshot_digest, 'final_snapshot_digest': self.final_snapshot_digest, 'body_unchanged': self.body_unchanged, 'explicit_insufficient_evidence_termination': self.explicit_insufficient_evidence_termination, 'memory_digest_after_failure': self.memory_digest_after_failure, 'failure_evidence_count_after': self.failure_evidence_count_after}
