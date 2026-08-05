"""Disposable replay and hidden-evaluator validation for M043 Q4."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from metamorphosis.m043_adoption_codec import (
    AdoptionError,
    CandidatePackage,
    MAX_CANDIDATE_BYTES,
    VALIDATION_TIMEOUT_SECONDS,
    ValidationDecision,
    ValidationReport,
    ValidationStatus,
    WORKER_REQUEST_SCHEMA,
    WorkerResult,
    _canonical_json,
)
from metamorphosis.m043_lineage_state import LineageSnapshot
from metamorphosis.m043_mealy import MealyMachine, mealy_digest
from metamorphosis.m043_rewrite import exact_body_digest, trace_digest
from metamorphosis.m043_task_model import AdmittedConstructiveTask


def build_candidate_package(
    snapshot: LineageSnapshot, task: AdmittedConstructiveTask
) -> CandidatePackage:
    trace = task.constructive_outcome.trace
    if trace is None or not task.constructive_outcome.exact:
        raise AdoptionError("task has no exact constructive trace")
    if task.public.parent_exact_digest != exact_body_digest(snapshot.accepted_body):
        raise AdoptionError("task parent does not match the accepted lineage body")
    return CandidatePackage(
        task_id=task.public.task_id,
        parent_lineage_digest=snapshot.digest(),
        parent_body_digest=exact_body_digest(snapshot.accepted_body),
        target_commitment=task.public.target_commitment,
        trace=trace,
        search_budget=task.public.search_budget,
        expected_final_body_digest=trace.final_body_digest,
    )


def worker_request_bytes(parent: MealyMachine, package: CandidatePackage) -> bytes:
    return _canonical_json(
        {
            "schema": WORKER_REQUEST_SCHEMA,
            "parent": parent.to_dict(),
            "candidate_package": package.to_dict(),
        }
    )


def _rejected_report(
    snapshot: LineageSnapshot,
    package: CandidatePackage,
    reason: str,
    *,
    status: ValidationStatus = ValidationStatus.REJECTED,
    worker_pid: int | None = None,
) -> ValidationDecision:
    return ValidationDecision(
        ValidationReport(
            status=status,
            reason=reason,
            parent_lineage_digest=snapshot.digest(),
            package_digest=package.digest(),
            task_id=package.task_id,
            target_commitment=package.target_commitment,
            trace_digest=trace_digest(package.trace),
            worker_pid=worker_pid,
            disposable_process=(worker_pid is not None and worker_pid != os.getpid()),
            candidate_body_digest=None,
            candidate_behaviour_digest=None,
            candidate_state_count=None,
            exact_target_match=False,
            parent_was_incapable=False,
            resource_limits_respected=False,
            parent_distinguishing_word=None,
        ),
        None,
    )


def validate_candidate_disposably(
    snapshot: LineageSnapshot,
    task: AdmittedConstructiveTask,
    package: CandidatePackage,
    *,
    timeout_seconds: float = VALIDATION_TIMEOUT_SECONDS,
) -> ValidationDecision:
    """Validate one package without allowing the lineage to inspect the hidden target."""

    try:
        if package.parent_lineage_digest != snapshot.digest():
            return _rejected_report(snapshot, package, "stale parent lineage identity")
        if package.parent_body_digest != exact_body_digest(snapshot.accepted_body):
            return _rejected_report(snapshot, package, "parent body identity mismatch")
        if package.task_id != task.public.task_id:
            return _rejected_report(snapshot, package, "task identity mismatch")
        if package.target_commitment != task.public.target_commitment:
            return _rejected_report(snapshot, package, "target commitment mismatch")
        if package.search_budget != task.public.search_budget:
            return _rejected_report(snapshot, package, "search budget mismatch")
        if package.trace.root_body_digest != package.parent_body_digest:
            return _rejected_report(snapshot, package, "trace root does not match parent")
        if package.expected_final_body_digest != package.trace.final_body_digest:
            return _rejected_report(snapshot, package, "candidate final identity mismatch")
        if len(package.trace.steps) > package.search_budget.max_depth:
            return _rejected_report(snapshot, package, "trace exceeds the fixed depth budget")
        if len(package.to_bytes()) > MAX_CANDIDATE_BYTES:
            return _rejected_report(snapshot, package, "candidate payload limit exceeded")
    except AdoptionError as exc:
        return _rejected_report(snapshot, package, str(exc))

    request = worker_request_bytes(snapshot.accepted_body, package)
    try:
        with tempfile.TemporaryDirectory(prefix="m043-q4-validator-") as directory:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "metamorphosis.m043_validation_worker",
                ],
                input=request,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=directory,
                timeout=timeout_seconds,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _rejected_report(
            snapshot,
            package,
            f"disposable validator failed: {type(exc).__name__}",
            status=ValidationStatus.SANDBOX_ERROR,
        )

    if completed.returncode != 0:
        return _rejected_report(
            snapshot,
            package,
            "disposable validator exited unsuccessfully",
            status=ValidationStatus.SANDBOX_ERROR,
        )
    try:
        worker = WorkerResult.from_bytes(completed.stdout)
    except AdoptionError:
        return _rejected_report(
            snapshot,
            package,
            "disposable validator returned malformed output",
            status=ValidationStatus.SANDBOX_ERROR,
        )
    if not worker.replayed or worker.candidate is None:
        return _rejected_report(
            snapshot,
            package,
            worker.reason or "candidate replay was rejected",
            worker_pid=worker.worker_pid,
        )

    candidate = worker.candidate
    resource_limits_respected = (
        candidate.n_states <= package.search_budget.max_states
        and len(package.trace.steps) <= package.search_budget.max_depth
    )
    exact_target_match, target_witness = task.evaluator._evaluate_exact(candidate)
    parent_exact, parent_witness = task.evaluator._evaluate_exact(snapshot.accepted_body)
    parent_was_incapable = (
        not parent_exact
        and parent_witness is not None
        and task.incapacity.parent_exact_digest == package.parent_body_digest
        and task.incapacity.target_behaviour_digest == package.target_commitment
        and task.incapacity.required_growth > 0
    )
    identities_consistent = (
        worker.parent_body_digest == package.parent_body_digest
        and worker.candidate_body_digest == package.expected_final_body_digest
        and worker.candidate_body_digest == exact_body_digest(candidate)
        and worker.candidate_behaviour_digest == mealy_digest(candidate, minimise=True)
        and worker.trace_digest == trace_digest(package.trace)
        and worker.candidate_state_count == candidate.n_states
    )
    disposable = worker.worker_pid != os.getpid()
    accepted = (
        exact_target_match
        and target_witness is None
        and parent_was_incapable
        and identities_consistent
        and resource_limits_respected
        and disposable
    )
    report = ValidationReport(
        status=ValidationStatus.ACCEPTED if accepted else ValidationStatus.REJECTED,
        reason="accepted" if accepted else "combined validation gate rejected candidate",
        parent_lineage_digest=snapshot.digest(),
        package_digest=package.digest(),
        task_id=package.task_id,
        target_commitment=package.target_commitment,
        trace_digest=trace_digest(package.trace),
        worker_pid=worker.worker_pid,
        disposable_process=disposable,
        candidate_body_digest=worker.candidate_body_digest,
        candidate_behaviour_digest=worker.candidate_behaviour_digest,
        candidate_state_count=worker.candidate_state_count,
        exact_target_match=exact_target_match,
        parent_was_incapable=parent_was_incapable,
        resource_limits_respected=resource_limits_respected,
        parent_distinguishing_word=parent_witness,
    )
    return ValidationDecision(report, candidate if accepted else None)


__all__ = [
    "build_candidate_package",
    "validate_candidate_disposably",
    "worker_request_bytes",
]
