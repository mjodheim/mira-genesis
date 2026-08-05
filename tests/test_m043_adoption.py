from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import json

import pytest

from metamorphosis.m043_adoption import (
    AdoptionError,
    CandidatePackage,
    FaultKind,
    LineageSnapshot,
    ValidationDecision,
    ValidationStatus,
    VersionedLineageStore,
    audit_snapshot,
    build_candidate_package,
    initial_lineage,
    run_q4_development_qualification,
    stage_adoption,
    validate_candidate_disposably,
)
from metamorphosis.m043_rewrite import exact_body_digest, trace_digest
from metamorphosis.m043_task_model import CatalogueStatus, SearchBudget
from metamorphosis.m043_task_search import (
    q3_development_parent,
    run_q3_development_catalogue,
)


@lru_cache(maxsize=1)
def qualified_fixture():
    catalogue = run_q3_development_catalogue()
    assert catalogue.status is CatalogueStatus.QUALIFIED
    task = catalogue.entries[0]
    initial = initial_lineage(q3_development_parent())
    package = build_candidate_package(initial, task)
    decision = validate_candidate_disposably(initial, task, package)
    assert decision.report.accepted
    return task, initial, package, decision


def test_candidate_package_round_trip_is_byte_identical():
    _, _, package, _ = qualified_fixture()
    parsed = CandidatePackage.from_bytes(package.to_bytes())
    assert parsed == package
    assert parsed.to_bytes() == package.to_bytes()
    assert parsed.digest() == package.digest()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: {**data, "schema": "wrong"},
        lambda data: {key: value for key, value in data.items() if key != "task_id"},
        lambda data: {**data, "extra": True},
        lambda data: {**data, "parent_body_digest": "not-a-digest"},
        lambda data: {
            **data,
            "search_budget": {"max_depth": 0, "max_nodes": 1, "max_states": 1},
        },
    ],
)
def test_candidate_package_parser_fails_closed(mutation):
    _, _, package, _ = qualified_fixture()
    malformed = mutation(package.to_dict())
    with pytest.raises((AdoptionError, ValueError)):
        CandidatePackage.from_bytes(json.dumps(malformed))


def test_candidate_package_binds_full_lineage_not_only_body():
    task, initial, package, decision = qualified_fixture()
    adopted = stage_adoption(initial, decision, package)
    assert exact_body_digest(adopted.accepted_body) != exact_body_digest(
        initial.accepted_body
    )
    stale = validate_candidate_disposably(adopted, task, package)
    assert stale.report.status is ValidationStatus.REJECTED
    assert "stale" in stale.report.reason
    assert stale.report.worker_pid is None


def test_wrong_task_identity_is_rejected_before_worker_launch():
    task, initial, package, _ = qualified_fixture()
    wrong = replace(package, task_id="wrong-task")
    decision = validate_candidate_disposably(initial, task, wrong)
    assert not decision.report.accepted
    assert decision.report.worker_pid is None


def test_wrong_target_commitment_is_rejected_before_worker_launch():
    task, initial, package, _ = qualified_fixture()
    wrong = replace(package, target_commitment="0" * 64)
    decision = validate_candidate_disposably(initial, task, wrong)
    assert not decision.report.accepted
    assert decision.report.worker_pid is None


def test_wrong_search_budget_is_rejected_before_worker_launch():
    task, initial, package, _ = qualified_fixture()
    wrong = replace(
        package,
        search_budget=SearchBudget(max_depth=1, max_nodes=1, max_states=1),
    )
    decision = validate_candidate_disposably(initial, task, wrong)
    assert not decision.report.accepted
    assert decision.report.worker_pid is None


def test_tampered_final_identity_is_rejected():
    task, initial, package, _ = qualified_fixture()
    wrong = replace(package, expected_final_body_digest="0" * 64)
    decision = validate_candidate_disposably(initial, task, wrong)
    assert not decision.report.accepted
    assert decision.candidate is None


def test_disposable_validation_combines_worker_and_hidden_evaluator():
    task, initial, package, decision = qualified_fixture()
    assert decision.report.worker_pid is not None
    assert decision.report.disposable_process
    assert decision.report.exact_target_match
    assert decision.report.parent_was_incapable
    assert decision.report.resource_limits_respected
    assert decision.report.parent_distinguishing_word is not None
    assert decision.candidate is not None
    exact, witness = task.evaluator._evaluate_exact(decision.candidate)
    assert exact and witness is None
    assert decision.report.candidate_body_digest == package.expected_final_body_digest


def test_validation_report_identity_excludes_runtime_pid():
    _, _, _, decision = qualified_fixture()
    other = replace(decision.report, worker_pid=(decision.report.worker_pid or 1) + 1000)
    assert other.to_dict() != decision.report.to_dict()
    assert other.digest() == decision.report.digest()


def test_only_accepted_decision_can_be_staged():
    _, initial, package, decision = qualified_fixture()
    rejected_report = replace(decision.report, status=ValidationStatus.REJECTED)
    with pytest.raises(AdoptionError):
        stage_adoption(initial, ValidationDecision(rejected_report, None), package)


def test_successful_adoption_versions_every_causal_component():
    _, initial, package, decision = qualified_fixture()
    staged = stage_adoption(initial, decision, package)
    assert staged.version == 1
    assert staged.accepted_body == decision.candidate
    assert len(staged.tool_registry) == 1
    assert staged.tool_registry[0].trace_digest == trace_digest(package.trace)
    assert (
        staged.tool_registry[0].validation_report_digest == decision.report.digest()
    )
    assert staged.learning_state.successful_trace_digests == (
        trace_digest(package.trace),
    )
    assert staged.accepted_task_commitments == (package.target_commitment,)
    assert len(staged.causal_journal) == 1
    assert staged.causal_journal[0].parent_snapshot_digest == initial.digest()
    audit_snapshot(staged, expected_report=decision.report, expected_package=package)


def test_snapshot_round_trip_is_byte_identical_and_audited():
    _, initial, package, decision = qualified_fixture()
    staged = stage_adoption(initial, decision, package)
    parsed = LineageSnapshot.from_bytes(staged.to_bytes())
    assert parsed == staged
    assert parsed.to_bytes() == staged.to_bytes()
    assert parsed.digest() == staged.digest()


def test_snapshot_parser_rejects_tampered_journal():
    _, initial, package, decision = qualified_fixture()
    staged = stage_adoption(initial, decision, package)
    raw = staged.to_dict()
    raw["causal_journal"][0]["package_digest"] = "0" * 64
    with pytest.raises(AdoptionError):
        LineageSnapshot.from_bytes(json.dumps(raw), expected_digest=staged.digest())


def test_store_commits_only_after_post_commit_audit():
    _, initial, package, decision = qualified_fixture()
    store = VersionedLineageStore(initial)
    receipt = store.adopt(decision, package)
    assert receipt.adopted
    assert not receipt.rolled_back
    assert store.current.version == 1
    assert store.current.digest() == receipt.after_snapshot_digest


def test_rejected_decision_never_mutates_store():
    _, initial, package, decision = qualified_fixture()
    rejected = ValidationDecision(
        replace(decision.report, status=ValidationStatus.REJECTED), None
    )
    store = VersionedLineageStore(initial)
    before = store.current.to_bytes()
    receipt = store.adopt(rejected, package)
    assert not receipt.adopted
    assert not receipt.rolled_back
    assert store.current.to_bytes() == before


@pytest.mark.parametrize("fault", list(FaultKind))
def test_forced_component_fault_restores_exact_checkpoint(fault):
    _, initial, package, decision = qualified_fixture()
    store = VersionedLineageStore(initial)
    before = store.current.to_bytes()
    receipt = store.adopt(decision, package, forced_fault=fault)
    assert not receipt.adopted
    assert receipt.rolled_back
    assert receipt.exact_restoration
    assert receipt.fault_kind is fault
    assert store.current.to_bytes() == before
    assert store.current.digest() == initial.digest()


def test_explicit_version_rollback_restores_original_snapshot_exactly():
    _, initial, package, decision = qualified_fixture()
    store = VersionedLineageStore(initial)
    assert store.adopt(decision, package).adopted
    receipt = store.rollback_to(0)
    assert receipt.rolled_back
    assert store.current.to_bytes() == initial.to_bytes()
    assert store.current.digest() == initial.digest()


def test_unknown_rollback_version_fails_closed():
    _, initial, _, _ = qualified_fixture()
    store = VersionedLineageStore(initial)
    with pytest.raises(AdoptionError):
        store.rollback_to(99)


def test_q4_development_qualification_is_deterministic():
    first = run_q4_development_qualification()
    second = run_q4_development_qualification()
    assert first == second
    assert first["status"] == "qualified"
    assert first["validator_was_disposable"]
    assert first["candidate_exact_target_match"]
    assert first["parent_structurally_incapable"]
    assert first["explicit_rollback_to_version_zero"]
    assert all(first["forced_fault_exact_restoration"].values())
    assert first["tampered_candidate_rejected"]
    assert first["stale_candidate_rejected"]
    assert not first["hidden_target_body_sent_to_worker"]
    assert first["selected_seed"] is None
    assert not first["canonical_workflow_authorised"]
