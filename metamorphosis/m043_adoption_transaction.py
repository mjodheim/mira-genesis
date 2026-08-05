"""Versioned transactional adoption and exact rollback for M043 Q4."""
from __future__ import annotations

from dataclasses import replace

from metamorphosis.m043_adoption_codec import (
    AdoptionError,
    AdoptionReceipt,
    CandidatePackage,
    FaultKind,
    ValidationDecision,
    ValidationReport,
)
from metamorphosis.m043_lineage_state import (
    CausalJournalEntry,
    LearningState,
    LineageSnapshot,
    ToolRecord,
    _core_digest,
    learning_state_digest,
    tool_registry_digest,
)
from metamorphosis.m043_mealy import MealyMachine
from metamorphosis.m043_rewrite import exact_body_digest, trace_digest


def _updated_learning_state(
    current: LearningState, package: CandidatePackage
) -> LearningState:
    observed = tuple(
        dict.fromkeys(step.certificate.effect_kind.value for step in package.trace.steps)
    )
    priority = observed + tuple(
        item for item in current.operation_priority if item not in observed
    )
    identity = trace_digest(package.trace)
    if identity in current.successful_trace_digests:
        raise AdoptionError("trace is already present in the learning state")
    return LearningState(priority, current.successful_trace_digests + (identity,))


def stage_adoption(
    snapshot: LineageSnapshot,
    decision: ValidationDecision,
    package: CandidatePackage,
) -> LineageSnapshot:
    report = decision.report
    candidate = decision.candidate
    if not report.accepted or candidate is None:
        raise AdoptionError("only an accepted validation decision may be staged")
    if report.parent_lineage_digest != snapshot.digest():
        raise AdoptionError("validation report is stale for the current lineage")
    if report.package_digest != package.digest():
        raise AdoptionError("validation report does not bind the candidate package")
    if report.candidate_body_digest != exact_body_digest(candidate):
        raise AdoptionError("validation report does not bind the candidate body")

    new_version = snapshot.version + 1
    identity = trace_digest(package.trace)
    if any(record.trace_digest == identity for record in snapshot.tool_registry):
        raise AdoptionError("candidate trace is already registered")
    effects = tuple(
        step.certificate.effect_kind.value for step in package.trace.steps
    )
    registry = snapshot.tool_registry + (
        ToolRecord(
            identity,
            package.task_id,
            effects,
            new_version,
            report.digest(),
        ),
    )
    learning = _updated_learning_state(snapshot.learning_state, package)
    commitments = snapshot.accepted_task_commitments + (package.target_commitment,)
    child_core = _core_digest(
        version=new_version,
        accepted_body=candidate,
        tool_registry=registry,
        learning_state=learning,
        accepted_task_commitments=commitments,
    )
    previous_entry = (
        None if not snapshot.causal_journal else snapshot.causal_journal[-1].digest()
    )
    entry = CausalJournalEntry(
        sequence=new_version,
        event="adopt_exact_candidate",
        parent_snapshot_digest=snapshot.digest(),
        child_core_digest=child_core,
        package_digest=package.digest(),
        validation_report_digest=report.digest(),
        accepted_body_digest=exact_body_digest(candidate),
        tool_registry_digest=tool_registry_digest(registry),
        learning_state_digest=learning_state_digest(learning),
        previous_entry_digest=previous_entry,
    )
    staged = LineageSnapshot(
        new_version,
        candidate,
        registry,
        learning,
        commitments,
        snapshot.causal_journal + (entry,),
    )
    audit_snapshot(staged, expected_report=report, expected_package=package)
    return staged


def audit_snapshot(
    snapshot: LineageSnapshot,
    *,
    expected_report: ValidationReport | None = None,
    expected_package: CandidatePackage | None = None,
) -> None:
    previous_digest: str | None = None
    for index, entry in enumerate(snapshot.causal_journal, start=1):
        if entry.sequence != index:
            raise AdoptionError("causal journal sequence is discontinuous")
        if entry.previous_entry_digest != previous_digest:
            raise AdoptionError("causal journal hash chain is broken")
        previous_digest = entry.digest()
    if snapshot.version == 0:
        if snapshot.tool_registry or snapshot.accepted_task_commitments:
            raise AdoptionError("version-zero lineage must have empty adopted state")
        return
    last = snapshot.causal_journal[-1]
    if last.child_core_digest != snapshot.core_digest():
        raise AdoptionError("journal child core does not match the snapshot")
    if last.accepted_body_digest != exact_body_digest(snapshot.accepted_body):
        raise AdoptionError("journal body identity does not match the snapshot")
    if last.tool_registry_digest != tool_registry_digest(snapshot.tool_registry):
        raise AdoptionError("journal registry identity does not match the snapshot")
    if last.learning_state_digest != learning_state_digest(snapshot.learning_state):
        raise AdoptionError("journal learning identity does not match the snapshot")
    if not snapshot.tool_registry:
        raise AdoptionError("versioned snapshot must contain a registered tool")
    if last.validation_report_digest != snapshot.tool_registry[-1].validation_report_digest:
        raise AdoptionError("journal and registry validation identities differ")
    if expected_report is not None:
        if not expected_report.accepted:
            raise AdoptionError("expected report must be accepted")
        if last.validation_report_digest != expected_report.digest():
            raise AdoptionError("journal does not bind the accepted validation report")
        if last.parent_snapshot_digest != expected_report.parent_lineage_digest:
            raise AdoptionError("journal parent does not bind the validation report")
        if expected_report.candidate_body_digest != exact_body_digest(
            snapshot.accepted_body
        ):
            raise AdoptionError("accepted body differs from the validation report")
    if expected_package is not None:
        if last.package_digest != expected_package.digest():
            raise AdoptionError("journal does not bind the candidate package")
        if expected_package.target_commitment not in snapshot.accepted_task_commitments:
            raise AdoptionError("accepted target commitment is missing")
        if not any(
            record.trace_digest == trace_digest(expected_package.trace)
            for record in snapshot.tool_registry
        ):
            raise AdoptionError("accepted trace is missing from the tool registry")


def _corrupt_body(machine: MealyMachine) -> MealyMachine:
    outputs = [list(row) for row in machine.outputs]
    current = outputs[0][0]
    replacement = next(symbol for symbol in machine.output_alphabet if symbol != current)
    outputs[0][0] = replacement
    return MealyMachine(
        machine.input_alphabet,
        machine.output_alphabet,
        machine.transitions,
        tuple(tuple(row) for row in outputs),
        machine.initial,
    )


def corrupt_snapshot(snapshot: LineageSnapshot, fault: FaultKind) -> LineageSnapshot:
    if snapshot.version == 0:
        raise AdoptionError("cannot corrupt a version-zero staged snapshot")
    if fault is FaultKind.BODY:
        return replace(snapshot, accepted_body=_corrupt_body(snapshot.accepted_body))
    if fault is FaultKind.REGISTRY:
        bogus = ToolRecord(
            "0" * 64,
            "forced-corruption",
            ("forced",),
            snapshot.version,
            "1" * 64,
        )
        return replace(snapshot, tool_registry=snapshot.tool_registry + (bogus,))
    if fault is FaultKind.LEARNING_STATE:
        learning = LearningState(
            snapshot.learning_state.operation_priority,
            snapshot.learning_state.successful_trace_digests + ("0" * 64,),
        )
        return replace(snapshot, learning_state=learning)
    if fault is FaultKind.JOURNAL:
        last = replace(snapshot.causal_journal[-1], package_digest="0" * 64)
        return replace(snapshot, causal_journal=snapshot.causal_journal[:-1] + (last,))
    raise TypeError(f"unsupported fault kind: {fault!r}")


class VersionedLineageStore:
    """A small transactional store whose rollback target is the exact prior snapshot."""

    def __init__(self, initial: LineageSnapshot) -> None:
        audit_snapshot(initial)
        self.current = initial
        self._versions: dict[int, LineageSnapshot] = {initial.version: initial}

    def adopt(
        self,
        decision: ValidationDecision,
        package: CandidatePackage,
        *,
        forced_fault: FaultKind | None = None,
    ) -> AdoptionReceipt:
        before = self.current
        before_bytes = before.to_bytes()
        before_digest = before.digest()
        attempted_version = before.version + 1
        if not decision.report.accepted or decision.candidate is None:
            return AdoptionReceipt(
                False,
                False,
                "validation decision was not accepted",
                before_digest,
                before_digest,
                before_bytes,
                before_bytes,
                attempted_version,
                before.version,
                forced_fault,
            )
        try:
            staged = stage_adoption(before, decision, package)
            self.current = staged
            if forced_fault is not None:
                self.current = corrupt_snapshot(self.current, forced_fault)
            audit_snapshot(
                self.current,
                expected_report=decision.report,
                expected_package=package,
            )
        except (AdoptionError, ValueError) as exc:
            self.current = before
            if self.current.to_bytes() != before_bytes or self.current.digest() != before_digest:
                raise AdoptionError("rollback failed to restore the exact checkpoint") from exc
            return AdoptionReceipt(
                False,
                True,
                str(exc),
                before_digest,
                self.current.digest(),
                before_bytes,
                self.current.to_bytes(),
                attempted_version,
                self.current.version,
                forced_fault,
            )
        self._versions[self.current.version] = self.current
        return AdoptionReceipt(
            True,
            False,
            "adopted",
            before_digest,
            self.current.digest(),
            before_bytes,
            self.current.to_bytes(),
            attempted_version,
            self.current.version,
            forced_fault,
        )

    def rollback_to(self, version: int) -> AdoptionReceipt:
        if version not in self._versions:
            raise AdoptionError("requested rollback version is not archived")
        before = self.current
        before_bytes = before.to_bytes()
        target = self._versions[version]
        self.current = target
        audit_snapshot(self.current)
        return AdoptionReceipt(
            False,
            True,
            "explicit version rollback",
            before.digest(),
            self.current.digest(),
            before_bytes,
            self.current.to_bytes(),
            before.version,
            self.current.version,
            None,
        )


__all__ = [
    "VersionedLineageStore",
    "audit_snapshot",
    "corrupt_snapshot",
    "stage_adoption",
]
