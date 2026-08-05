from __future__ import annotations
from dataclasses import dataclass, replace
import hashlib
from metamorphosis.m047_lineage_protocol import MANIFEST_SCHEMA, _canonical_json
from metamorphosis.m047_cycle_records import ModularCheckpoint, ModularCycleRecord, ModularRollbackRecord, ModularTerminalRecord

@dataclass(frozen=True)
class ModularSoftwareManifest:
    protocol_digest: str
    founder_body_digest: str
    founder_snapshot_digest: str
    founder_module_count: int
    cycles: tuple[ModularCycleRecord, ...]
    checkpoints: tuple[ModularCheckpoint, ...]
    rollback: ModularRollbackRecord
    terminal: ModularTerminalRecord
    final_snapshot_digest: str
    final_snapshot_bytes_sha256: str
    final_body_digest: str
    final_body_source_bytes: int
    final_module_count: int
    final_regression_test_count: int
    final_patch_registry_digest: str
    final_journal_digest: str
    final_patch_registry_count: int
    final_journal_entries: int
    final_causal_memory_digest: str
    final_causal_memory_bytes: int
    final_causal_memory_episodes: int
    final_causal_failure_evidence_count: int
    retained_validation_case_count: int
    retained_validation_all_passed: bool
    accepted_cycle_count: int
    patch_template_reuse_cycles: int
    causal_memory_reuse_cycles: int
    acquired_runtime_tool_reuse_cycles: int
    all_module_diagnoses_correct: bool
    all_generated_tests_persisted: bool
    all_independent_validations_disposable: bool
    all_resource_budgets_respected: bool
    all_searches_non_exhaustive: bool
    checkpoints_verified: bool
    replay_identical: bool
    schema: str = MANIFEST_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {'schema': self.schema, 'protocol_digest': self.protocol_digest, 'founder_body_digest': self.founder_body_digest, 'founder_snapshot_digest': self.founder_snapshot_digest, 'founder_module_count': self.founder_module_count, 'cycles': [cycle.to_dict() for cycle in self.cycles], 'checkpoints': [checkpoint.to_dict() for checkpoint in self.checkpoints], 'rollback': self.rollback.to_dict(), 'terminal': self.terminal.to_dict(), 'final_snapshot_digest': self.final_snapshot_digest, 'final_snapshot_bytes_sha256': self.final_snapshot_bytes_sha256, 'final_body_digest': self.final_body_digest, 'final_body_source_bytes': self.final_body_source_bytes, 'final_module_count': self.final_module_count, 'final_regression_test_count': self.final_regression_test_count, 'final_patch_registry_digest': self.final_patch_registry_digest, 'final_journal_digest': self.final_journal_digest, 'final_patch_registry_count': self.final_patch_registry_count, 'final_journal_entries': self.final_journal_entries, 'final_causal_memory_digest': self.final_causal_memory_digest, 'final_causal_memory_bytes': self.final_causal_memory_bytes, 'final_causal_memory_episodes': self.final_causal_memory_episodes, 'final_causal_failure_evidence_count': self.final_causal_failure_evidence_count, 'retained_validation_case_count': self.retained_validation_case_count, 'retained_validation_all_passed': self.retained_validation_all_passed, 'accepted_cycle_count': self.accepted_cycle_count, 'patch_template_reuse_cycles': self.patch_template_reuse_cycles, 'causal_memory_reuse_cycles': self.causal_memory_reuse_cycles, 'acquired_runtime_tool_reuse_cycles': self.acquired_runtime_tool_reuse_cycles, 'all_module_diagnoses_correct': self.all_module_diagnoses_correct, 'all_generated_tests_persisted': self.all_generated_tests_persisted, 'all_independent_validations_disposable': self.all_independent_validations_disposable, 'all_resource_budgets_respected': self.all_resource_budgets_respected, 'all_searches_non_exhaustive': self.all_searches_non_exhaustive, 'checkpoints_verified': self.checkpoints_verified, 'replay_identical': self.replay_identical, 'replay_scope': 'accepted_sources_registry_memory_checkpoints_and_forced_rollback', 'mutable_body_is_executable_python_modules': True, 'candidate_sources_executed_only_in_disposable_worker': True, 'hidden_suite_exposed_to_generator': False, 'repository_write_authority_granted_to_lineage': False, 'selected_seed': None, 'canonical_workflow_authorised': False, 'claim_scope': 'bounded_modular_software_development_lineage'}

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(b'm047-modular-software-manifest-v1\x00' + self.to_bytes()).hexdigest()
