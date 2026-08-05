"""M046 integrated scalable, non-exhaustive continuous lineage.

M046 reuses the exact M043/M044 body, rewrite, validation and transaction mechanisms.  Its
new claim is narrower and orthogonal: one longer lineage proposes and selects transformations
from bounded observations without enumerating the complete candidate space.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json

from metamorphosis.m043_adoption import (
    FaultKind,
    VersionedLineageStore,
    build_candidate_package,
    initial_lineage,
    validate_candidate_disposably,
)
from metamorphosis.m043_lineage_state import (
    LineageSnapshot,
    journal_digest,
    learning_state_digest,
    tool_registry_digest,
)
from metamorphosis.m043_rewrite import exact_body_digest
from metamorphosis.m043_task_search import q3_development_parent
from metamorphosis.m046_search import (
    CausalProposalMemory,
    ProposalEpisode,
    ProposalSearchResult,
    ProposalSearchStatus,
    ScalableResourceBudget,
    ScalableSearchError,
    heuristic_proposal_search,
)
from metamorphosis.m046_task import (
    IndependentSelectionResult,
    ScalableTaskError,
    StopAction,
    build_hidden_scalable_task,
    validate_ranked_proposals_independently,
)


class ScalableLineageError(RuntimeError):
    """Raised when the single M046 experiment fails closed."""


PROTOCOL_SCHEMA = "m046-scalable-lineage-protocol-v1"
MANIFEST_SCHEMA = "m046-scalable-lineage-manifest-v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class M046Protocol:
    accepted_cycles: int = 6
    maximum_exploration_fraction_ppm: int = 100_000
    rollback_fault: str = FaultKind.JOURNAL.value
    terminal_required_growth: int = 2
    resources: ScalableResourceBudget = ScalableResourceBudget()
    schema: str = PROTOCOL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROTOCOL_SCHEMA:
            raise ScalableLineageError("unsupported M046 protocol schema")
        if self.accepted_cycles != 6:
            raise ScalableLineageError("M046 fixes six accepted adaptive cycles")
        if self.maximum_exploration_fraction_ppm != 100_000:
            raise ScalableLineageError(
                "M046 fixes a ten-percent maximum explored lower-bound fraction"
            )
        if self.rollback_fault != FaultKind.JOURNAL.value:
            raise ScalableLineageError("M046 fixes journal corruption as rollback probe")
        if self.terminal_required_growth != 2:
            raise ScalableLineageError(
                "M046 fixes a two-growth terminal challenge"
            )
        expected = ScalableResourceBudget()
        if self.resources != expected:
            raise ScalableLineageError("M046 resource bounds are frozen as one experiment")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "accepted_cycles": self.accepted_cycles,
            "maximum_exploration_fraction_ppm": self.maximum_exploration_fraction_ppm,
            "rollback_fault": self.rollback_fault,
            "terminal_required_growth": self.terminal_required_growth,
            "resources": self.resources.to_dict(),
        }

    def digest(self) -> str:
        return _domain_digest(b"m046-protocol-v1\x00", self.to_dict())


M046_PROTOCOL = M046Protocol()


@dataclass(frozen=True)
class ScalableCheckpoint:
    version: int
    snapshot_digest: str
    snapshot_bytes_sha256: str
    memory_digest: str
    memory_bytes_sha256: str
    combined_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "snapshot_digest": self.snapshot_digest,
            "snapshot_bytes_sha256": self.snapshot_bytes_sha256,
            "memory_digest": self.memory_digest,
            "memory_bytes_sha256": self.memory_bytes_sha256,
            "combined_digest": self.combined_digest,
        }


def _checkpoint(
    snapshot: LineageSnapshot, memory: CausalProposalMemory
) -> ScalableCheckpoint:
    mapping = {
        "schema": "m046-scalable-checkpoint-v1",
        "version": snapshot.version,
        "snapshot_digest": snapshot.digest(),
        "snapshot_bytes_sha256": hashlib.sha256(snapshot.to_bytes()).hexdigest(),
        "memory_digest": memory.digest(),
        "memory_bytes_sha256": hashlib.sha256(memory.to_bytes()).hexdigest(),
    }
    return ScalableCheckpoint(
        version=snapshot.version,
        snapshot_digest=mapping["snapshot_digest"],
        snapshot_bytes_sha256=mapping["snapshot_bytes_sha256"],
        memory_digest=mapping["memory_digest"],
        memory_bytes_sha256=mapping["memory_bytes_sha256"],
        combined_digest=_domain_digest(
            b"m046-scalable-checkpoint-v1\x00", mapping
        ),
    )


@dataclass(frozen=True)
class ScalableCycleRecord:
    ordinal: int
    task_id: str
    hidden_task_digest: str
    hidden_family: str
    parent_snapshot_digest: str
    parent_body_digest: str
    parent_states: int
    proposal_search_digest: str
    proposal_status: str
    observations_used: int
    generated_candidates: int
    invalid_candidates: int
    candidate_space_lower_bound: int
    exploration_fraction_ppm: int
    complete_candidate_space_enumerated: bool
    working_memory_bytes: int
    time_budget_respected: bool
    reused_causal_memory: bool
    independent_selection_digest: str
    independent_validation_attempts: int
    independent_exact_rejections: int
    selected_proposal_digest: str
    selected_template: str
    task_side_independent_validation: bool
    adoption_validation_report_digest: str
    adoption_validator_disposable: bool
    adopted_snapshot_digest: str
    adopted_body_digest: str
    adopted_states: int
    reused_registered_tool_effects: bool
    registered_tool_count: int
    lineage_learning_trace_count: int
    lineage_journal_entries: int
    causal_memory_digest: str
    causal_memory_episodes: int
    causal_failure_evidence_count: int
    checkpoint: ScalableCheckpoint

    def to_dict(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "task_id": self.task_id,
            "hidden_task_digest": self.hidden_task_digest,
            "hidden_family": self.hidden_family,
            "parent_snapshot_digest": self.parent_snapshot_digest,
            "parent_body_digest": self.parent_body_digest,
            "parent_states": self.parent_states,
            "proposal_search_digest": self.proposal_search_digest,
            "proposal_status": self.proposal_status,
            "observations_used": self.observations_used,
            "generated_candidates": self.generated_candidates,
            "invalid_candidates": self.invalid_candidates,
            "candidate_space_lower_bound": self.candidate_space_lower_bound,
            "exploration_fraction_ppm": self.exploration_fraction_ppm,
            "complete_candidate_space_enumerated": self.complete_candidate_space_enumerated,
            "working_memory_bytes": self.working_memory_bytes,
            "time_budget_respected": self.time_budget_respected,
            "reused_causal_memory": self.reused_causal_memory,
            "independent_selection_digest": self.independent_selection_digest,
            "independent_validation_attempts": self.independent_validation_attempts,
            "independent_exact_rejections": self.independent_exact_rejections,
            "selected_proposal_digest": self.selected_proposal_digest,
            "selected_template": self.selected_template,
            "task_side_independent_validation": self.task_side_independent_validation,
            "adoption_validation_report_digest": self.adoption_validation_report_digest,
            "adoption_validator_disposable": self.adoption_validator_disposable,
            "adopted_snapshot_digest": self.adopted_snapshot_digest,
            "adopted_body_digest": self.adopted_body_digest,
            "adopted_states": self.adopted_states,
            "reused_registered_tool_effects": self.reused_registered_tool_effects,
            "registered_tool_count": self.registered_tool_count,
            "lineage_learning_trace_count": self.lineage_learning_trace_count,
            "lineage_journal_entries": self.lineage_journal_entries,
            "causal_memory_digest": self.causal_memory_digest,
            "causal_memory_episodes": self.causal_memory_episodes,
            "causal_failure_evidence_count": self.causal_failure_evidence_count,
            "checkpoint": self.checkpoint.to_dict(),
        }


@dataclass(frozen=True)
class RollbackRecord:
    task_id: str
    attempted_version: int
    restored_version: int
    lineage_exact_restoration: bool
    combined_checkpoint_before: str
    combined_checkpoint_after: str
    combined_checkpoint_exact_restoration: bool
    memory_unchanged: bool
    forced_fault: str

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "attempted_version": self.attempted_version,
            "restored_version": self.restored_version,
            "lineage_exact_restoration": self.lineage_exact_restoration,
            "combined_checkpoint_before": self.combined_checkpoint_before,
            "combined_checkpoint_after": self.combined_checkpoint_after,
            "combined_checkpoint_exact_restoration": self.combined_checkpoint_exact_restoration,
            "memory_unchanged": self.memory_unchanged,
            "forced_fault": self.forced_fault,
        }


@dataclass(frozen=True)
class TerminalRecord:
    task_id: str
    hidden_task_digest: str
    hidden_family: str
    required_growth: int
    proposal_search_digest: str
    independent_selection_digest: str
    stop_action: str
    stop_reason: str
    validation_attempts: int
    exact_rejections: int
    parent_snapshot_digest: str
    final_snapshot_digest: str
    body_unchanged: bool
    explicit_insufficient_evidence_termination: bool
    memory_digest_after_failure: str
    failure_evidence_count_after: int

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "hidden_task_digest": self.hidden_task_digest,
            "hidden_family": self.hidden_family,
            "required_growth": self.required_growth,
            "proposal_search_digest": self.proposal_search_digest,
            "independent_selection_digest": self.independent_selection_digest,
            "stop_action": self.stop_action,
            "stop_reason": self.stop_reason,
            "validation_attempts": self.validation_attempts,
            "exact_rejections": self.exact_rejections,
            "parent_snapshot_digest": self.parent_snapshot_digest,
            "final_snapshot_digest": self.final_snapshot_digest,
            "body_unchanged": self.body_unchanged,
            "explicit_insufficient_evidence_termination": self.explicit_insufficient_evidence_termination,
            "memory_digest_after_failure": self.memory_digest_after_failure,
            "failure_evidence_count_after": self.failure_evidence_count_after,
        }


@dataclass(frozen=True)
class ScalableManifest:
    protocol_digest: str
    founder_body_digest: str
    founder_snapshot_digest: str
    cycles: tuple[ScalableCycleRecord, ...]
    checkpoints: tuple[ScalableCheckpoint, ...]
    rollback: RollbackRecord
    terminal: TerminalRecord
    final_snapshot_digest: str
    final_snapshot_bytes_sha256: str
    final_body_digest: str
    final_body_states: int
    final_tool_registry_digest: str
    final_learning_state_digest: str
    final_journal_digest: str
    final_tool_count: int
    final_learning_trace_count: int
    final_journal_entries: int
    final_causal_memory_digest: str
    final_causal_memory_bytes: int
    final_causal_memory_episodes: int
    final_causal_failure_evidence_count: int
    maximum_observed_exploration_fraction_ppm: int
    all_searches_non_exhaustive: bool
    all_resource_budgets_respected: bool
    accepted_cycle_count: int
    tool_reuse_cycles: int
    causal_memory_reuse_cycles: int
    checkpoints_verified: bool
    replay_identical: bool
    schema: str = MANIFEST_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "protocol_digest": self.protocol_digest,
            "founder_body_digest": self.founder_body_digest,
            "founder_snapshot_digest": self.founder_snapshot_digest,
            "cycles": [cycle.to_dict() for cycle in self.cycles],
            "checkpoints": [
                checkpoint.to_dict() for checkpoint in self.checkpoints
            ],
            "rollback": self.rollback.to_dict(),
            "terminal": self.terminal.to_dict(),
            "final_snapshot_digest": self.final_snapshot_digest,
            "final_snapshot_bytes_sha256": self.final_snapshot_bytes_sha256,
            "final_body_digest": self.final_body_digest,
            "final_body_states": self.final_body_states,
            "final_tool_registry_digest": self.final_tool_registry_digest,
            "final_learning_state_digest": self.final_learning_state_digest,
            "final_journal_digest": self.final_journal_digest,
            "final_tool_count": self.final_tool_count,
            "final_learning_trace_count": self.final_learning_trace_count,
            "final_journal_entries": self.final_journal_entries,
            "final_causal_memory_digest": self.final_causal_memory_digest,
            "final_causal_memory_bytes": self.final_causal_memory_bytes,
            "final_causal_memory_episodes": self.final_causal_memory_episodes,
            "final_causal_failure_evidence_count": self.final_causal_failure_evidence_count,
            "maximum_observed_exploration_fraction_ppm": self.maximum_observed_exploration_fraction_ppm,
            "all_searches_non_exhaustive": self.all_searches_non_exhaustive,
            "all_resource_budgets_respected": self.all_resource_budgets_respected,
            "accepted_cycle_count": self.accepted_cycle_count,
            "tool_reuse_cycles": self.tool_reuse_cycles,
            "causal_memory_reuse_cycles": self.causal_memory_reuse_cycles,
            "checkpoints_verified": self.checkpoints_verified,
            "replay_identical": self.replay_identical,
            "m043_transaction_and_validator_reused_without_reimplementation": True,
            "selected_seed": None,
            "canonical_workflow_authorised": False,
            "claim_scope": "bounded_scalable_non_exhaustive_development_lineage",
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(
            b"m046-scalable-manifest-v1\x00" + self.to_bytes()
        ).hexdigest()


def _dominated_templates(
    search: ProposalSearchResult,
    selection: IndependentSelectionResult,
) -> tuple[str, ...]:
    attempted = {attempt.proposal_digest for attempt in selection.attempts}
    return tuple(
        proposal.template_id
        for proposal in search.proposals
        if proposal.digest() not in attempted
    )


def _validate_search_contract(
    search: ProposalSearchResult, protocol: M046Protocol
) -> None:
    if search.status is not ProposalSearchStatus.READY:
        raise ScalableLineageError(
            f"proposal search did not produce candidates: {search.status.value}"
        )
    if search.complete_candidate_space_enumerated:
        raise ScalableLineageError("M046 enumerated the complete candidate space")
    if search.generated_candidates > protocol.resources.max_generated_candidates:
        raise ScalableLineageError("proposal count exceeded the fixed budget")
    if len(search.observations) > protocol.resources.max_observations:
        raise ScalableLineageError("observation count exceeded the fixed budget")
    if search.working_memory_bytes > protocol.resources.max_working_memory_bytes:
        raise ScalableLineageError("working memory exceeded the fixed budget")
    if not search.time_budget_respected:
        raise ScalableLineageError("proposal search exceeded the fixed time budget")
    if search.candidate_space_lower_bound <= search.generated_candidates:
        raise ScalableLineageError("M046 search was not demonstrably non-exhaustive")
    if (
        search.exploration_fraction_ppm
        > protocol.maximum_exploration_fraction_ppm
    ):
        raise ScalableLineageError(
            "M046 explored too much of the conservative candidate-space lower bound"
        )


def _run_accepted_cycle(
    store: VersionedLineageStore,
    memory: CausalProposalMemory,
    protocol: M046Protocol,
    *,
    ordinal: int,
) -> tuple[CausalProposalMemory, ScalableCycleRecord]:
    before = store.current
    hidden = build_hidden_scalable_task(
        before.accepted_body,
        ordinal=ordinal,
        protocol_digest=protocol.digest(),
        budget=protocol.resources,
    )
    search = heuristic_proposal_search(
        before.accepted_body,
        hidden.evaluator,
        memory,
        protocol.resources,
    )
    _validate_search_contract(search, protocol)
    selection = validate_ranked_proposals_independently(
        before.accepted_body,
        hidden,
        search,
        protocol.resources,
    )
    if not selection.accepted:
        raise ScalableLineageError(
            f"cycle {ordinal} terminated before an exact proposal was found: "
            f"{selection.decision.reason}"
        )
    if selection.admitted_task is None or selection.selected_proposal is None:
        raise ScalableLineageError("accepted selection lacks its admitted task")

    package = build_candidate_package(before, selection.admitted_task)
    effects = tuple(
        step.certificate.effect_kind.value for step in package.trace.steps
    )
    reused_tool = any(
        record.effect_kinds == effects for record in before.tool_registry
    )
    decision = validate_candidate_disposably(
        before, selection.admitted_task, package
    )
    if not decision.report.accepted or decision.candidate is None:
        raise ScalableLineageError(
            f"cycle {ordinal} failed disposable independent validation"
        )
    receipt = store.adopt(decision, package)
    if not receipt.adopted:
        raise ScalableLineageError(
            f"cycle {ordinal} failed transactional adoption"
        )
    after = store.current
    if after.accepted_body.n_states != before.accepted_body.n_states + 1:
        store.rollback_to(before.version)
        raise ScalableLineageError(
            f"cycle {ordinal} did not add exactly one minimal state"
        )

    episode = ProposalEpisode(
        task_id=hidden.public.task_id,
        outcome="accepted",
        selected_template=selection.selected_proposal.template_id,
        exact_rejected_templates=selection.rejected_templates,
        dominated_templates=_dominated_templates(search, selection),
        generated_candidates=search.generated_candidates,
        validation_attempts=len(selection.attempts),
        reason="exact proposal independently validated and transactionally adopted",
    )
    try:
        updated_memory = memory.append(
            episode,
            maximum_bytes=protocol.resources.max_causal_memory_bytes,
        )
    except ScalableSearchError as exc:
        rollback = store.rollback_to(before.version)
        if store.current != before or not rollback.exact_restoration:
            raise ScalableLineageError(
                "combined lineage-memory rollback failed"
            ) from exc
        raise ScalableLineageError(
            "causal memory update exceeded its resource budget"
        ) from exc

    checkpoint = _checkpoint(after, updated_memory)
    record = ScalableCycleRecord(
        ordinal=ordinal,
        task_id=hidden.public.task_id,
        hidden_task_digest=hidden.digest(),
        hidden_family=hidden.family,
        parent_snapshot_digest=before.digest(),
        parent_body_digest=exact_body_digest(before.accepted_body),
        parent_states=before.accepted_body.n_states,
        proposal_search_digest=search.digest(),
        proposal_status=search.status.value,
        observations_used=len(search.observations),
        generated_candidates=search.generated_candidates,
        invalid_candidates=search.invalid_candidates,
        candidate_space_lower_bound=search.candidate_space_lower_bound,
        exploration_fraction_ppm=search.exploration_fraction_ppm,
        complete_candidate_space_enumerated=search.complete_candidate_space_enumerated,
        working_memory_bytes=search.working_memory_bytes,
        time_budget_respected=search.time_budget_respected,
        reused_causal_memory=search.reused_causal_memory,
        independent_selection_digest=selection.digest(),
        independent_validation_attempts=len(selection.attempts),
        independent_exact_rejections=len(selection.rejected_templates),
        selected_proposal_digest=selection.selected_proposal.digest(),
        selected_template=selection.selected_proposal.template_id,
        task_side_independent_validation=True,
        adoption_validation_report_digest=decision.report.digest(),
        adoption_validator_disposable=decision.report.disposable_process,
        adopted_snapshot_digest=after.digest(),
        adopted_body_digest=exact_body_digest(after.accepted_body),
        adopted_states=after.accepted_body.n_states,
        reused_registered_tool_effects=reused_tool,
        registered_tool_count=len(after.tool_registry),
        lineage_learning_trace_count=len(
            after.learning_state.successful_trace_digests
        ),
        lineage_journal_entries=len(after.causal_journal),
        causal_memory_digest=updated_memory.digest(),
        causal_memory_episodes=len(updated_memory.episodes),
        causal_failure_evidence_count=updated_memory.failure_evidence_count,
        checkpoint=checkpoint,
    )
    return updated_memory, record


def _run_forced_rollback(
    store: VersionedLineageStore,
    memory: CausalProposalMemory,
    protocol: M046Protocol,
) -> RollbackRecord:
    before = store.current
    before_checkpoint = _checkpoint(before, memory)
    hidden = build_hidden_scalable_task(
        before.accepted_body,
        ordinal=protocol.accepted_cycles + 1,
        protocol_digest=protocol.digest(),
        budget=protocol.resources,
    )
    search = heuristic_proposal_search(
        before.accepted_body,
        hidden.evaluator,
        memory,
        protocol.resources,
    )
    _validate_search_contract(search, protocol)
    selection = validate_ranked_proposals_independently(
        before.accepted_body,
        hidden,
        search,
        protocol.resources,
    )
    if not selection.accepted or selection.admitted_task is None:
        raise ScalableLineageError(
            "rollback probe could not prepare a valid provisional candidate"
        )
    package = build_candidate_package(before, selection.admitted_task)
    decision = validate_candidate_disposably(
        before, selection.admitted_task, package
    )
    if not decision.report.accepted:
        raise ScalableLineageError(
            "rollback probe candidate failed disposable validation"
        )
    receipt = store.adopt(
        decision,
        package,
        forced_fault=FaultKind(protocol.rollback_fault),
    )
    after_checkpoint = _checkpoint(store.current, memory)
    combined_exact = (
        before_checkpoint.combined_digest == after_checkpoint.combined_digest
    )
    if (
        not receipt.exact_restoration
        or store.current != before
        or not combined_exact
    ):
        raise ScalableLineageError(
            "forced fault did not restore the combined scalable checkpoint"
        )
    return RollbackRecord(
        task_id=hidden.public.task_id,
        attempted_version=receipt.attempted_version,
        restored_version=receipt.committed_version,
        lineage_exact_restoration=receipt.exact_restoration,
        combined_checkpoint_before=before_checkpoint.combined_digest,
        combined_checkpoint_after=after_checkpoint.combined_digest,
        combined_checkpoint_exact_restoration=combined_exact,
        memory_unchanged=(
            before_checkpoint.memory_digest == after_checkpoint.memory_digest
        ),
        forced_fault=protocol.rollback_fault,
    )


def _run_terminal_challenge(
    store: VersionedLineageStore,
    memory: CausalProposalMemory,
    protocol: M046Protocol,
) -> tuple[CausalProposalMemory, TerminalRecord]:
    before = store.current
    hidden = build_hidden_scalable_task(
        before.accepted_body,
        ordinal=protocol.accepted_cycles + 2,
        protocol_digest=protocol.digest(),
        budget=protocol.resources,
        required_growth=protocol.terminal_required_growth,
    )
    search = heuristic_proposal_search(
        before.accepted_body,
        hidden.evaluator,
        memory,
        protocol.resources,
    )
    if search.complete_candidate_space_enumerated:
        raise ScalableLineageError(
            "terminal challenge enumerated the complete candidate space"
        )
    selection = validate_ranked_proposals_independently(
        before.accepted_body,
        hidden,
        search,
        protocol.resources,
    )
    if selection.accepted:
        raise ScalableLineageError(
            "terminal challenge unexpectedly produced an exact bounded proposal"
        )
    if selection.decision.action is not StopAction.TERMINATE_INSUFFICIENT_EVIDENCE:
        raise ScalableLineageError(
            "terminal challenge did not fail closed for insufficient evidence"
        )
    if store.current != before:
        raise ScalableLineageError(
            "terminal challenge changed the accepted body without adoption"
        )

    episode = ProposalEpisode(
        task_id=hidden.public.task_id,
        outcome="insufficient_evidence",
        selected_template=None,
        exact_rejected_templates=selection.rejected_templates,
        dominated_templates=_dominated_templates(search, selection),
        generated_candidates=search.generated_candidates,
        validation_attempts=len(selection.attempts),
        reason=selection.decision.reason,
    )
    updated_memory = memory.append(
        episode,
        maximum_bytes=protocol.resources.max_causal_memory_bytes,
    )
    record = TerminalRecord(
        task_id=hidden.public.task_id,
        hidden_task_digest=hidden.digest(),
        hidden_family=hidden.family,
        required_growth=hidden.required_growth,
        proposal_search_digest=search.digest(),
        independent_selection_digest=selection.digest(),
        stop_action=selection.decision.action.value,
        stop_reason=selection.decision.reason,
        validation_attempts=len(selection.attempts),
        exact_rejections=len(selection.rejected_templates),
        parent_snapshot_digest=before.digest(),
        final_snapshot_digest=store.current.digest(),
        body_unchanged=store.current == before,
        explicit_insufficient_evidence_termination=True,
        memory_digest_after_failure=updated_memory.digest(),
        failure_evidence_count_after=updated_memory.failure_evidence_count,
    )
    return updated_memory, record


def _execute_once(protocol: M046Protocol) -> ScalableManifest:
    founder = q3_development_parent()
    initial = initial_lineage(founder)
    store = VersionedLineageStore(initial)
    memory = CausalProposalMemory()
    cycles: list[ScalableCycleRecord] = []
    checkpoints: list[ScalableCheckpoint] = []

    for ordinal in range(1, protocol.accepted_cycles + 1):
        memory, cycle = _run_accepted_cycle(
            store, memory, protocol, ordinal=ordinal
        )
        cycles.append(cycle)
        checkpoints.append(cycle.checkpoint)

    rollback = _run_forced_rollback(store, memory, protocol)
    memory, terminal = _run_terminal_challenge(
        store, memory, protocol
    )
    final = store.current

    expected_states = founder.n_states + protocol.accepted_cycles
    if final.accepted_body.n_states != expected_states:
        raise ScalableLineageError("M046 final body has the wrong state count")
    if len(final.tool_registry) != protocol.accepted_cycles:
        raise ScalableLineageError("M046 did not preserve every acquired tool")
    if len(final.causal_journal) != protocol.accepted_cycles:
        raise ScalableLineageError("M046 causal journal is incomplete")
    if memory.accepted_episodes != protocol.accepted_cycles:
        raise ScalableLineageError("M046 proposal memory lost accepted episodes")
    if memory.failure_evidence_count <= 0:
        raise ScalableLineageError("M046 proposal memory contains no failure evidence")

    maximum_fraction = max(
        cycle.exploration_fraction_ppm for cycle in cycles
    )
    all_non_exhaustive = all(
        not cycle.complete_candidate_space_enumerated
        and cycle.generated_candidates < cycle.candidate_space_lower_bound
        for cycle in cycles
    )
    all_resources = all(
        cycle.observations_used <= protocol.resources.max_observations
        and cycle.generated_candidates
        <= protocol.resources.max_generated_candidates
        and cycle.independent_validation_attempts
        <= protocol.resources.max_validation_attempts
        and cycle.working_memory_bytes
        <= protocol.resources.max_working_memory_bytes
        and cycle.time_budget_respected
        for cycle in cycles
    )
    checkpoints_verified = all(
        checkpoint.version == index
        and checkpoint.snapshot_digest == cycles[index - 1].adopted_snapshot_digest
        and checkpoint.memory_digest == cycles[index - 1].causal_memory_digest
        for index, checkpoint in enumerate(checkpoints, start=1)
    )

    return ScalableManifest(
        protocol_digest=protocol.digest(),
        founder_body_digest=exact_body_digest(founder),
        founder_snapshot_digest=initial.digest(),
        cycles=tuple(cycles),
        checkpoints=tuple(checkpoints),
        rollback=rollback,
        terminal=terminal,
        final_snapshot_digest=final.digest(),
        final_snapshot_bytes_sha256=hashlib.sha256(
            final.to_bytes()
        ).hexdigest(),
        final_body_digest=exact_body_digest(final.accepted_body),
        final_body_states=final.accepted_body.n_states,
        final_tool_registry_digest=tool_registry_digest(final.tool_registry),
        final_learning_state_digest=learning_state_digest(
            final.learning_state
        ),
        final_journal_digest=journal_digest(final.causal_journal),
        final_tool_count=len(final.tool_registry),
        final_learning_trace_count=len(
            final.learning_state.successful_trace_digests
        ),
        final_journal_entries=len(final.causal_journal),
        final_causal_memory_digest=memory.digest(),
        final_causal_memory_bytes=len(memory.to_bytes()),
        final_causal_memory_episodes=len(memory.episodes),
        final_causal_failure_evidence_count=memory.failure_evidence_count,
        maximum_observed_exploration_fraction_ppm=maximum_fraction,
        all_searches_non_exhaustive=all_non_exhaustive,
        all_resource_budgets_respected=all_resources,
        accepted_cycle_count=len(cycles),
        tool_reuse_cycles=sum(
            cycle.reused_registered_tool_effects for cycle in cycles
        ),
        causal_memory_reuse_cycles=sum(
            cycle.reused_causal_memory for cycle in cycles
        ),
        checkpoints_verified=checkpoints_verified,
        replay_identical=False,
    )


def run_m046_scalable_lineage(
    protocol: M046Protocol = M046_PROTOCOL,
) -> ScalableManifest:
    """Execute the complete integrated experiment twice and require exact replay."""

    try:
        first = _execute_once(protocol)
        second = _execute_once(protocol)
    except (ScalableSearchError, ScalableTaskError) as exc:
        raise ScalableLineageError(str(exc)) from exc
    if first.to_bytes() != second.to_bytes():
        raise ScalableLineageError("M046 deterministic replay diverged")
    return replace(first, replay_identical=True)


__all__ = [
    "M046_PROTOCOL",
    "M046Protocol",
    "RollbackRecord",
    "ScalableCheckpoint",
    "ScalableCycleRecord",
    "ScalableLineageError",
    "ScalableManifest",
    "TerminalRecord",
    "run_m046_scalable_lineage",
]
