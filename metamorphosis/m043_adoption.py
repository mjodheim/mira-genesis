"""M043 Q4 public facade and deterministic development qualification."""
from __future__ import annotations

from dataclasses import replace

from metamorphosis.m043_adoption_codec import (
    AdoptionError,
    AdoptionReceipt,
    CandidatePackage,
    FaultKind,
    MAX_CANDIDATE_BYTES,
    ValidationDecision,
    ValidationReport,
    ValidationStatus,
    WorkerResult,
)
from metamorphosis.m043_adoption_transaction import (
    VersionedLineageStore,
    audit_snapshot,
    corrupt_snapshot,
    stage_adoption,
)
from metamorphosis.m043_adoption_validation import (
    build_candidate_package,
    validate_candidate_disposably,
    worker_request_bytes,
)
from metamorphosis.m043_lineage_state import (
    CausalJournalEntry,
    DEFAULT_LEARNING_STATE,
    LearningState,
    LineageSnapshot,
    ToolRecord,
    initial_lineage,
)
from metamorphosis.m043_task_model import CatalogueStatus
from metamorphosis.m043_task_search import (
    q3_development_parent,
    run_q3_development_catalogue,
)


def run_q4_development_qualification() -> dict[str, object]:
    catalogue = run_q3_development_catalogue()
    if catalogue.status is not CatalogueStatus.QUALIFIED or not catalogue.entries:
        raise AdoptionError("Q3 did not provide a qualified development task")
    task = catalogue.entries[0]
    initial = initial_lineage(q3_development_parent())
    package = build_candidate_package(initial, task)
    decision = validate_candidate_disposably(initial, task, package)
    if not decision.report.accepted:
        raise AdoptionError(f"Q4 exact candidate was rejected: {decision.report.reason}")

    success_store = VersionedLineageStore(initial)
    success = success_store.adopt(decision, package)
    if not success.adopted:
        raise AdoptionError("Q4 exact adoption failed")
    adopted_snapshot = success_store.current
    explicit_rollback = success_store.rollback_to(0)

    fault_receipts: dict[str, AdoptionReceipt] = {}
    for fault in FaultKind:
        store = VersionedLineageStore(initial)
        receipt = store.adopt(decision, package, forced_fault=fault)
        if not receipt.exact_restoration:
            raise AdoptionError(f"forced {fault.value} fault did not restore exactly")
        fault_receipts[fault.value] = receipt

    tampered = replace(package, expected_final_body_digest="0" * 64)
    tampered_decision = validate_candidate_disposably(initial, task, tampered)
    stale_decision = validate_candidate_disposably(adopted_snapshot, task, package)

    return {
        "schema": "m043-q4-development-result-v1",
        "status": "qualified",
        "catalogue_entry_digest": task.digest(),
        "candidate_package_digest": package.digest(),
        "validation_report_digest": decision.report.digest(),
        "validator_was_disposable": decision.report.disposable_process,
        "parent_snapshot_digest": initial.digest(),
        "adopted_snapshot_digest": adopted_snapshot.digest(),
        "adopted_version": adopted_snapshot.version,
        "candidate_exact_target_match": decision.report.exact_target_match,
        "parent_structurally_incapable": decision.report.parent_was_incapable,
        "resource_limits_respected": decision.report.resource_limits_respected,
        "tool_registry_entries": len(adopted_snapshot.tool_registry),
        "causal_journal_entries": len(adopted_snapshot.causal_journal),
        "explicit_rollback_to_version_zero": explicit_rollback.after_snapshot_digest
        == initial.digest(),
        "forced_fault_exact_restoration": {
            name: receipt.exact_restoration for name, receipt in fault_receipts.items()
        },
        "tampered_candidate_rejected": not tampered_decision.report.accepted,
        "stale_candidate_rejected": not stale_decision.report.accepted,
        "hidden_target_body_sent_to_worker": False,
        "selected_seed": None,
        "canonical_workflow_authorised": False,
    }


__all__ = [
    "AdoptionError",
    "AdoptionReceipt",
    "CandidatePackage",
    "CausalJournalEntry",
    "DEFAULT_LEARNING_STATE",
    "FaultKind",
    "LearningState",
    "LineageSnapshot",
    "MAX_CANDIDATE_BYTES",
    "ToolRecord",
    "ValidationDecision",
    "ValidationReport",
    "ValidationStatus",
    "VersionedLineageStore",
    "WorkerResult",
    "audit_snapshot",
    "build_candidate_package",
    "corrupt_snapshot",
    "initial_lineage",
    "run_q4_development_qualification",
    "stage_adoption",
    "validate_candidate_disposably",
    "worker_request_bytes",
]
