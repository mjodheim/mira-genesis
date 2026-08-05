from __future__ import annotations

import inspect
import json
import os

from metamorphosis import m043_validation_worker as worker
from metamorphosis.m043_adoption import (
    CandidatePackage,
    WorkerResult,
    build_candidate_package,
    initial_lineage,
    worker_request_bytes,
)
from metamorphosis.m043_task_model import CatalogueStatus
from metamorphosis.m043_task_search import (
    q3_development_parent,
    run_q3_development_catalogue,
)


def _fixture():
    catalogue = run_q3_development_catalogue()
    assert catalogue.status is CatalogueStatus.QUALIFIED
    task = catalogue.entries[0]
    snapshot = initial_lineage(q3_development_parent())
    package = build_candidate_package(snapshot, task)
    return snapshot, package


def test_worker_source_has_no_q3_evaluator_dependency():
    source = inspect.getsource(worker)
    assert "m043_task" not in source
    assert "HiddenTargetEvaluator" not in source
    assert "_evaluate_exact" not in source


def test_worker_request_contains_parent_and_commitment_but_no_hidden_table_field():
    snapshot, package = _fixture()
    request = json.loads(worker_request_bytes(snapshot.accepted_body, package))
    assert set(request) == {"schema", "parent", "candidate_package"}
    assert request["candidate_package"]["target_commitment"] == (
        package.target_commitment
    )
    assert "target" not in request
    assert "target_body" not in request
    assert "witness_trace" not in request


def test_direct_worker_replays_exact_parent_bound_trace():
    snapshot, package = _fixture()
    result = worker.replay_request(worker_request_bytes(snapshot.accepted_body, package))
    assert result.replayed
    assert result.worker_pid == os.getpid()
    assert result.candidate is not None
    assert result.candidate_body_digest == package.expected_final_body_digest
    parsed = WorkerResult.from_bytes(result.to_bytes())
    assert parsed == result


def test_worker_rejects_malformed_request_fields():
    result = worker.replay_request(json.dumps({"schema": "wrong"}))
    assert not result.replayed
    assert result.candidate is None


def test_worker_rejects_wrong_parent_identity():
    snapshot, package = _fixture()
    wrong = CandidatePackage(
        package.task_id,
        package.parent_lineage_digest,
        "0" * 64,
        package.target_commitment,
        package.trace,
        package.search_budget,
        package.expected_final_body_digest,
    )
    result = worker.replay_request(worker_request_bytes(snapshot.accepted_body, wrong))
    assert not result.replayed
    assert result.candidate is None


def test_worker_rejects_trace_over_its_declared_depth_budget():
    snapshot, package = _fixture()
    too_small = CandidatePackage(
        package.task_id,
        package.parent_lineage_digest,
        package.parent_body_digest,
        package.target_commitment,
        package.trace,
        type(package.search_budget)(
            max_depth=1,
            max_nodes=package.search_budget.max_nodes,
            max_states=package.search_budget.max_states,
        ),
        package.expected_final_body_digest,
    )
    result = worker.replay_request(
        worker_request_bytes(snapshot.accepted_body, too_small)
    )
    assert not result.replayed
    assert "depth" in result.reason


def test_worker_result_parser_rejects_incomplete_success():
    malformed = {
        "schema": "m043-q4-worker-result-v1",
        "replayed": True,
        "reason": "replayed",
        "worker_pid": 1,
        "parent_body_digest": None,
        "candidate_body_digest": None,
        "candidate_behaviour_digest": None,
        "candidate_state_count": None,
        "trace_digest": None,
        "candidate": None,
    }
    try:
        WorkerResult.from_bytes(json.dumps(malformed))
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete successful worker result was accepted")
