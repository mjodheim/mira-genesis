"""M044 accelerated integrated Mealy lineage.

M044 deliberately avoids another sequence of component gates. It composes the already
qualified M043 Q1-Q5 mechanisms into one deterministic bounded lineage:

founder -> two accepted rewrites -> opaque migration -> one accepted post-migration
rewrite -> native resynthesis -> forced transactional rollback -> exact replay.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

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
from metamorphosis.m043_migration import (
    NativeMigrationBundle,
    audit_native_migration_bundle,
    build_native_migration_bundle,
)
from metamorphosis.m043_native_program import native_program_to_mealy
from metamorphosis.m043_opaque_substrate import (
    discover_field_substrate,
    make_development_positive_machine,
)
from metamorphosis.m043_rewrite import exact_body_digest, trace_digest
from metamorphosis.m043_task_model import (
    AdmittedConstructiveTask,
    CatalogueStatus,
    SearchBudget,
)
from metamorphosis.m043_task_search import (
    build_development_catalogue,
    q3_development_parent,
)


class IntegratedLineageError(RuntimeError):
    """Raised when the accelerated integrated lineage fails closed."""


MANIFEST_SCHEMA = "m044-integrated-mealy-lineage-manifest-v1"
PROTOCOL_SCHEMA = "m044-integrated-mealy-lineage-protocol-v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class M044Protocol:
    pre_migration_cycles: int = 2
    post_migration_cycles: int = 1
    search_depth: int = 2
    search_nodes: int = 4_096
    maximum_states: int = 6
    catalogue_candidates: int = 96
    observation_limit: int = 64
    opaque_family: int = 0
    rollback_fault: str = FaultKind.JOURNAL.value
    schema: str = PROTOCOL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROTOCOL_SCHEMA:
            raise IntegratedLineageError("unsupported M044 protocol schema")
        if self.pre_migration_cycles != 2 or self.post_migration_cycles != 1:
            raise IntegratedLineageError("M044 fixes exactly two pre- and one post-migration cycle")
        for name, value in (
            ("search_depth", self.search_depth),
            ("search_nodes", self.search_nodes),
            ("maximum_states", self.maximum_states),
            ("catalogue_candidates", self.catalogue_candidates),
            ("observation_limit", self.observation_limit),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise IntegratedLineageError(f"{name} must be a positive integer")
        if self.maximum_states != 6:
            raise IntegratedLineageError("M044 fixes a six-state ceiling")
        if self.opaque_family != 0:
            raise IntegratedLineageError("M044 fixes opaque development family zero")
        if self.rollback_fault != FaultKind.JOURNAL.value:
            raise IntegratedLineageError("M044 fixes a journal-corruption rollback probe")

    def budget(self) -> SearchBudget:
        return SearchBudget(
            max_depth=self.search_depth,
            max_nodes=self.search_nodes,
            max_states=self.maximum_states,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "pre_migration_cycles": self.pre_migration_cycles,
            "post_migration_cycles": self.post_migration_cycles,
            "search_depth": self.search_depth,
            "search_nodes": self.search_nodes,
            "maximum_states": self.maximum_states,
            "catalogue_candidates": self.catalogue_candidates,
            "observation_limit": self.observation_limit,
            "opaque_family": self.opaque_family,
            "rollback_fault": self.rollback_fault,
        }

    def digest(self) -> str:
        return _domain_digest(b"m044-protocol-v1\x00", self.to_dict())


M044_PROTOCOL = M044Protocol()


@dataclass(frozen=True)
class CycleRecord:
    phase: str
    ordinal: int
    parent_snapshot_digest: str
    parent_body_digest: str
    parent_states: int
    catalogue_digest: str
    task_digest: str
    task_id: str
    target_commitment: str
    trace_digest: str
    trace_effects: tuple[str, ...]
    validation_report_digest: str
    adopted_snapshot_digest: str
    adopted_body_digest: str
    adopted_states: int
    registered_tool_count: int
    learning_trace_count: int
    journal_entries: int
    reused_prior_tool_pattern: bool
    reused_prior_tool_trace_digest: str | None
    complete_nodes_seen: int
    tool_ablated_nodes_seen: int
    learning_ablated_nodes_seen: int
    control_surface_distinct: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "ordinal": self.ordinal,
            "parent_snapshot_digest": self.parent_snapshot_digest,
            "parent_body_digest": self.parent_body_digest,
            "parent_states": self.parent_states,
            "catalogue_digest": self.catalogue_digest,
            "task_digest": self.task_digest,
            "task_id": self.task_id,
            "target_commitment": self.target_commitment,
            "trace_digest": self.trace_digest,
            "trace_effects": list(self.trace_effects),
            "validation_report_digest": self.validation_report_digest,
            "adopted_snapshot_digest": self.adopted_snapshot_digest,
            "adopted_body_digest": self.adopted_body_digest,
            "adopted_states": self.adopted_states,
            "registered_tool_count": self.registered_tool_count,
            "learning_trace_count": self.learning_trace_count,
            "journal_entries": self.journal_entries,
            "reused_prior_tool_pattern": self.reused_prior_tool_pattern,
            "reused_prior_tool_trace_digest": self.reused_prior_tool_trace_digest,
            "complete_nodes_seen": self.complete_nodes_seen,
            "tool_ablated_nodes_seen": self.tool_ablated_nodes_seen,
            "learning_ablated_nodes_seen": self.learning_ablated_nodes_seen,
            "control_surface_distinct": self.control_surface_distinct,
        }


@dataclass(frozen=True)
class IntegratedManifest:
    protocol_digest: str
    founder_body_digest: str
    founder_snapshot_digest: str
    cycles: tuple[CycleRecord, ...]
    first_migration_bundle_digest: str
    first_native_program_digest: str
    discovery_digest: str
    opaque_machine_id: str
    post_migration_parent_from_native: bool
    updated_migration_bundle_digest: str
    updated_native_program_digest: str
    native_program_changed_after_learning: bool
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
    native_reconstruction_exact: bool
    rollback_exact: bool
    rollback_attempted_version: int
    rollback_restored_version: int
    replay_identical: bool
    schema: str = MANIFEST_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "protocol_digest": self.protocol_digest,
            "founder_body_digest": self.founder_body_digest,
            "founder_snapshot_digest": self.founder_snapshot_digest,
            "cycles": [cycle.to_dict() for cycle in self.cycles],
            "first_migration_bundle_digest": self.first_migration_bundle_digest,
            "first_native_program_digest": self.first_native_program_digest,
            "discovery_digest": self.discovery_digest,
            "opaque_machine_id": self.opaque_machine_id,
            "post_migration_parent_from_native": self.post_migration_parent_from_native,
            "updated_migration_bundle_digest": self.updated_migration_bundle_digest,
            "updated_native_program_digest": self.updated_native_program_digest,
            "native_program_changed_after_learning": self.native_program_changed_after_learning,
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
            "native_reconstruction_exact": self.native_reconstruction_exact,
            "rollback_exact": self.rollback_exact,
            "rollback_attempted_version": self.rollback_attempted_version,
            "rollback_restored_version": self.rollback_restored_version,
            "replay_identical": self.replay_identical,
            "q1_to_q5_reused_without_reimplementation": True,
            "selected_seed": None,
            "canonical_workflow_authorised": False,
            "claim_scope": "bounded_integrated_development_lineage",
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(b"m044-manifest-v1\x00" + self.to_bytes()).hexdigest()


def _catalogue_digest(value: Mapping[str, object]) -> str:
    return _domain_digest(b"m044-catalogue-v1\x00", value)


def _choose_task(snapshot: LineageSnapshot, protocol: M044Protocol) -> tuple[object, AdmittedConstructiveTask]:
    catalogue = build_development_catalogue(
        snapshot.accepted_body,
        budget=protocol.budget(),
        minimum_entries=1,
        maximum_candidates=protocol.catalogue_candidates,
        observation_limit=protocol.observation_limit,
    )
    if catalogue.status is not CatalogueStatus.QUALIFIED or not catalogue.entries:
        raise IntegratedLineageError("M044 could not construct the next exact task")
    return catalogue, catalogue.entries[0]


def _control_nodes(task: AdmittedConstructiveTask, arm: str) -> int:
    for control in task.controls:
        if control.arm.value == arm:
            return control.nodes_seen
    raise IntegratedLineageError(f"M044 task lacks required control arm {arm}")


def _adopt_cycle(
    store: VersionedLineageStore,
    protocol: M044Protocol,
    *,
    phase: str,
    ordinal: int,
) -> CycleRecord:
    before = store.current
    catalogue, task = _choose_task(before, protocol)
    package = build_candidate_package(before, task)
    effects = tuple(
        step.certificate.effect_kind.value for step in package.trace.steps
    )
    reused = next(
        (
            record.trace_digest
            for record in before.tool_registry
            if record.effect_kinds == effects
        ),
        None,
    )
    decision = validate_candidate_disposably(before, task, package)
    if not decision.report.accepted or decision.candidate is None:
        raise IntegratedLineageError(
            f"M044 {phase} cycle {ordinal} candidate failed isolated validation"
        )
    receipt = store.adopt(decision, package)
    if not receipt.adopted:
        raise IntegratedLineageError(
            f"M044 {phase} cycle {ordinal} candidate failed transactional adoption"
        )
    after = store.current
    if after.accepted_body.n_states != before.accepted_body.n_states + 1:
        raise IntegratedLineageError("M044 accepted cycle did not grow exact capacity by one")
    tool_nodes = _control_nodes(task, "tool_ablated")
    learning_nodes = _control_nodes(task, "learning_state_ablated")
    complete_nodes = task.constructive_outcome.nodes_seen
    return CycleRecord(
        phase=phase,
        ordinal=ordinal,
        parent_snapshot_digest=before.digest(),
        parent_body_digest=exact_body_digest(before.accepted_body),
        parent_states=before.accepted_body.n_states,
        catalogue_digest=_catalogue_digest(catalogue.to_dict()),
        task_digest=task.digest(),
        task_id=task.public.task_id,
        target_commitment=task.public.target_commitment,
        trace_digest=trace_digest(package.trace),
        trace_effects=effects,
        validation_report_digest=decision.report.digest(),
        adopted_snapshot_digest=after.digest(),
        adopted_body_digest=exact_body_digest(after.accepted_body),
        adopted_states=after.accepted_body.n_states,
        registered_tool_count=len(after.tool_registry),
        learning_trace_count=len(after.learning_state.successful_trace_digests),
        journal_entries=len(after.causal_journal),
        reused_prior_tool_pattern=reused is not None,
        reused_prior_tool_trace_digest=reused,
        complete_nodes_seen=complete_nodes,
        tool_ablated_nodes_seen=tool_nodes,
        learning_ablated_nodes_seen=learning_nodes,
        control_surface_distinct=(
            complete_nodes != tool_nodes or complete_nodes != learning_nodes
        ),
    )


def _prepare_fault_candidate(
    store: VersionedLineageStore, protocol: M044Protocol
) -> tuple[object, object]:
    _, task = _choose_task(store.current, protocol)
    package = build_candidate_package(store.current, task)
    decision = validate_candidate_disposably(store.current, task, package)
    if not decision.report.accepted:
        raise IntegratedLineageError("M044 rollback probe candidate was not valid")
    return decision, package


def _execute_once(protocol: M044Protocol) -> IntegratedManifest:
    founder = q3_development_parent()
    initial = initial_lineage(founder)
    store = VersionedLineageStore(initial)
    cycles: list[CycleRecord] = []

    for ordinal in range(1, protocol.pre_migration_cycles + 1):
        cycles.append(
            _adopt_cycle(store, protocol, phase="pre_migration", ordinal=ordinal)
        )

    if not cycles[1].reused_prior_tool_pattern:
        raise IntegratedLineageError("second cycle did not reuse an acquired tool pattern")

    machine = make_development_positive_machine(protocol.opaque_family)
    discovery = discover_field_substrate(machine)
    first_bundle = build_native_migration_bundle(store.current, machine, discovery)
    audit_native_migration_bundle(first_bundle, store.current, machine, discovery)
    native_parent = native_program_to_mealy(first_bundle.native_program, machine)
    if native_parent != store.current.accepted_body:
        raise IntegratedLineageError("first native migration did not reconstruct the lineage")

    cycles.append(
        _adopt_cycle(store, protocol, phase="post_migration", ordinal=1)
    )
    post_cycle = cycles[-1]
    if post_cycle.parent_body_digest != exact_body_digest(native_parent):
        raise IntegratedLineageError("post-migration cycle did not start from native behaviour")
    if not post_cycle.reused_prior_tool_pattern:
        raise IntegratedLineageError("post-migration cycle did not reuse an acquired tool pattern")

    updated_bundle = build_native_migration_bundle(store.current, machine, discovery)
    audit_native_migration_bundle(updated_bundle, store.current, machine, discovery)
    reconstructed = native_program_to_mealy(updated_bundle.native_program, machine)
    native_exact = reconstructed == store.current.accepted_body
    if not native_exact:
        raise IntegratedLineageError("post-learning native resynthesis is not exact")
    if updated_bundle.native_program.digest() == first_bundle.native_program.digest():
        raise IntegratedLineageError("native body did not change after post-migration learning")

    stable_before_fault = store.current
    decision, package = _prepare_fault_candidate(store, protocol)
    rollback = store.adopt(
        decision,
        package,
        forced_fault=FaultKind(protocol.rollback_fault),
    )
    if not rollback.exact_restoration or store.current != stable_before_fault:
        raise IntegratedLineageError("forced post-migration fault did not restore exactly")

    final = store.current
    return IntegratedManifest(
        protocol_digest=protocol.digest(),
        founder_body_digest=exact_body_digest(founder),
        founder_snapshot_digest=initial.digest(),
        cycles=tuple(cycles),
        first_migration_bundle_digest=first_bundle.digest(),
        first_native_program_digest=first_bundle.native_program.digest(),
        discovery_digest=discovery.digest(),
        opaque_machine_id=machine.machine_id,
        post_migration_parent_from_native=True,
        updated_migration_bundle_digest=updated_bundle.digest(),
        updated_native_program_digest=updated_bundle.native_program.digest(),
        native_program_changed_after_learning=(
            first_bundle.native_program.digest()
            != updated_bundle.native_program.digest()
        ),
        final_snapshot_digest=final.digest(),
        final_snapshot_bytes_sha256=hashlib.sha256(final.to_bytes()).hexdigest(),
        final_body_digest=exact_body_digest(final.accepted_body),
        final_body_states=final.accepted_body.n_states,
        final_tool_registry_digest=tool_registry_digest(final.tool_registry),
        final_learning_state_digest=learning_state_digest(final.learning_state),
        final_journal_digest=journal_digest(final.causal_journal),
        final_tool_count=len(final.tool_registry),
        final_learning_trace_count=len(final.learning_state.successful_trace_digests),
        final_journal_entries=len(final.causal_journal),
        native_reconstruction_exact=native_exact,
        rollback_exact=rollback.exact_restoration,
        rollback_attempted_version=rollback.attempted_version,
        rollback_restored_version=rollback.committed_version,
        replay_identical=False,
    )


def run_m044_integrated_lineage(
    protocol: M044Protocol = M044_PROTOCOL,
) -> IntegratedManifest:
    """Execute the complete lineage twice and return the byte-identical manifest."""

    first = _execute_once(protocol)
    second = _execute_once(protocol)
    if first.to_bytes() != second.to_bytes():
        raise IntegratedLineageError("M044 exact replay diverged")
    mapping = first.to_dict()
    mapping["replay_identical"] = True
    return IntegratedManifest(
        protocol_digest=str(mapping["protocol_digest"]),
        founder_body_digest=str(mapping["founder_body_digest"]),
        founder_snapshot_digest=str(mapping["founder_snapshot_digest"]),
        cycles=first.cycles,
        first_migration_bundle_digest=str(mapping["first_migration_bundle_digest"]),
        first_native_program_digest=str(mapping["first_native_program_digest"]),
        discovery_digest=str(mapping["discovery_digest"]),
        opaque_machine_id=str(mapping["opaque_machine_id"]),
        post_migration_parent_from_native=bool(mapping["post_migration_parent_from_native"]),
        updated_migration_bundle_digest=str(mapping["updated_migration_bundle_digest"]),
        updated_native_program_digest=str(mapping["updated_native_program_digest"]),
        native_program_changed_after_learning=bool(mapping["native_program_changed_after_learning"]),
        final_snapshot_digest=str(mapping["final_snapshot_digest"]),
        final_snapshot_bytes_sha256=str(mapping["final_snapshot_bytes_sha256"]),
        final_body_digest=str(mapping["final_body_digest"]),
        final_body_states=int(mapping["final_body_states"]),
        final_tool_registry_digest=str(mapping["final_tool_registry_digest"]),
        final_learning_state_digest=str(mapping["final_learning_state_digest"]),
        final_journal_digest=str(mapping["final_journal_digest"]),
        final_tool_count=int(mapping["final_tool_count"]),
        final_learning_trace_count=int(mapping["final_learning_trace_count"]),
        final_journal_entries=int(mapping["final_journal_entries"]),
        native_reconstruction_exact=bool(mapping["native_reconstruction_exact"]),
        rollback_exact=bool(mapping["rollback_exact"]),
        rollback_attempted_version=int(mapping["rollback_attempted_version"]),
        rollback_restored_version=int(mapping["rollback_restored_version"]),
        replay_identical=True,
    )


__all__ = [
    "IntegratedLineageError",
    "IntegratedManifest",
    "M044_PROTOCOL",
    "M044Protocol",
    "run_m044_integrated_lineage",
]
