"""M033 — deterministic post-migration plasticity controls.

Primary seeds remain unopened.  This module constructs the six declared lineages,
generates control-only tasks from seeds 1024+, and executes bounded post-migration
rewrite audits with exact finite-state evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from itertools import product
import json
import random
from typing import Sequence

from .m012b_dfa import DFA, canonicalize, minimize_dfa
from .m013e_engine import MigrationCertificate, UnknownSubstrateMigrator
from .m013e_lab import OpaqueBooleanMachine
from .m013e_runtime import OpaqueNativeBody
from .m020_self_rewrite import (
    Case,
    SelfRewriteEngine,
    ToolRegistry,
    VersionedCodeBody,
    source_digest,
)
from .m024_rewrite_passport import import_passport
from .m032_trans_substrate_lifecycle import (
    PortableLearningState,
    TransSubstratePacket,
    compile_policy_to_dfa,
)


class LineageVariant(StrEnum):
    COMPLETE = "complete"
    FRESH_B = "fresh_b"
    UNCHANGED_PARENT = "unchanged_parent"
    OUTPUT_ONLY = "output_only"
    LEARNING_STATE_ABLATED = "learning_state_ablated"
    LEARNED_TOOLS_ABLATED = "learned_tools_ablated"


PACKET_DERIVED_VARIANTS = (
    LineageVariant.COMPLETE,
    LineageVariant.OUTPUT_ONLY,
    LineageVariant.LEARNING_STATE_ABLATED,
    LineageVariant.LEARNED_TOOLS_ABLATED,
)


class ControlTaskFamily(StrEnum):
    POSITIVE_TOOL = "positive_tool"
    NEGATIVE_TOOL = "negative_tool"


@dataclass(frozen=True)
class DeterministicCost:
    packet_validations: int = 0
    substrate_probes: int = 0
    native_candidate_evaluations: int = 0
    native_components: int = 0
    serialized_bytes: int = 0
    rewrite_candidate_evaluations: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "packet_validations": self.packet_validations,
            "substrate_probes": self.substrate_probes,
            "native_candidate_evaluations": self.native_candidate_evaluations,
            "native_components": self.native_components,
            "serialized_bytes": self.serialized_bytes,
            "rewrite_candidate_evaluations": self.rewrite_candidate_evaluations,
        }

    def plus(self, other: "DeterministicCost") -> "DeterministicCost":
        return DeterministicCost(
            packet_validations=self.packet_validations + other.packet_validations,
            substrate_probes=self.substrate_probes + other.substrate_probes,
            native_candidate_evaluations=(
                self.native_candidate_evaluations
                + other.native_candidate_evaluations
            ),
            native_components=self.native_components + other.native_components,
            serialized_bytes=self.serialized_bytes + other.serialized_bytes,
            rewrite_candidate_evaluations=(
                self.rewrite_candidate_evaluations
                + other.rewrite_candidate_evaluations
            ),
        )


@dataclass
class PostMigrationLineage:
    """One isolated lineage at the post-migration task-reveal boundary."""

    variant: LineageVariant
    body: VersionedCodeBody
    registry: ToolRegistry
    source_dfa: DFA
    opaque_body: OpaqueNativeBody
    learning_state: PortableLearningState
    can_update_learning_state: bool
    can_rewrite: bool
    source_packet_sha256: str | None
    origin_checkpoint: str
    construction_cost: DeterministicCost

    def canonical_snapshot(self) -> str:
        """Serialise every evaluator-visible lineage surface."""

        return json.dumps(
            {
                "active_source": self.body.active_source,
                "function_name": self.body.function_name,
                "archive": list(self.body.archive),
                "adopted_digests": list(self.body.adopted_digests),
                "primitive_tools": [tool.name for tool in self.registry.primitives],
                "learned_tools": [
                    {
                        "name": tool.name,
                        "operations": [
                            list(operation.key()) for operation in tool.operations
                        ],
                    }
                    for tool in self.registry.learned
                ],
                "source_dfa": self.source_dfa.to_dict(),
                "opaque_body": json.loads(self.opaque_body.to_json()),
                "learning_state": self.learning_state.to_dict(),
                "can_update_learning_state": self.can_update_learning_state,
                "can_rewrite": self.can_rewrite,
                "source_packet_sha256": self.source_packet_sha256,
                "origin_checkpoint": self.origin_checkpoint,
                "construction_cost": self.construction_cost.to_dict(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def snapshot_sha256(self) -> str:
        return hashlib.sha256(self.canonical_snapshot().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ControlTask:
    seed: int
    family: ControlTaskFamily
    function_name: str
    baseline_source: str
    target_source: str
    state_count: int
    accepting_states: tuple[bool, ...]
    initial_state: int
    development_cases: tuple[Case, ...]
    held_out_words: tuple[tuple[int, ...], ...]
    target_dfa: DFA
    max_edits: int

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-control-task/1",
                "seed": self.seed,
                "family": self.family.value,
                "function_name": self.function_name,
                "baseline_source": self.baseline_source,
                "target_source": self.target_source,
                "state_count": self.state_count,
                "accepting_states": [int(value) for value in self.accepting_states],
                "initial_state": self.initial_state,
                "development_cases": [
                    [list(case.arguments), case.expected]
                    for case in self.development_cases
                ],
                "held_out_words": [list(word) for word in self.held_out_words],
                "target_dfa": self.target_dfa.to_dict(),
                "max_edits": self.max_edits,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ControlTaskResult:
    variant: LineageVariant
    task_sha256: str
    attempted: bool
    adopted: bool
    exact: bool
    quality_per_mille: int
    candidates_evaluated: int
    learned_tool_name: str | None
    final_source: str
    lineage_snapshot_sha256: str

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m033-control-result/1",
                "variant": self.variant.value,
                "task_sha256": self.task_sha256,
                "attempted": self.attempted,
                "adopted": self.adopted,
                "exact": self.exact,
                "quality_per_mille": self.quality_per_mille,
                "candidates_evaluated": self.candidates_evaluated,
                "learned_tool_name": self.learned_tool_name,
                "final_source": self.final_source,
                "lineage_snapshot_sha256": self.lineage_snapshot_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def _rehydrate_base(packet_json: str) -> tuple[
    TransSubstratePacket,
    VersionedCodeBody,
    ToolRegistry,
    DFA,
    OpaqueNativeBody,
]:
    packet = TransSubstratePacket.from_json(packet_json)
    body, registry, _ = import_passport(packet.rewrite_passport_json)
    return (
        packet,
        body,
        registry,
        DFA.from_dict(packet.source_dfa),
        OpaqueNativeBody.from_json(packet.opaque_body_json),
    )


def _migration_cost(certificate: MigrationCertificate) -> DeterministicCost:
    return DeterministicCost(
        substrate_probes=certificate.probe_calls,
        native_candidate_evaluations=certificate.candidate_evaluations,
        native_components=certificate.native_components,
        serialized_bytes=certificate.serialized_bytes,
    )


def _migrate_or_raise(
    dfa: DFA,
    machine: OpaqueBooleanMachine,
    search_seed: int,
    *,
    migrator: UnknownSubstrateMigrator | None,
    trace: dict[str, object],
) -> MigrationCertificate:
    certificate = (migrator or UnknownSubstrateMigrator()).migrate(
        dfa,
        machine,
        search_seed,
        trace=trace,
    )
    if certificate.status != "success" or certificate.body is None:
        raise ValueError(
            f"M033 control migration failed: {certificate.status}:{certificate.reason}"
        )
    return certificate


def build_packet_derived_lineage(
    packet_json: str,
    variant: LineageVariant,
) -> PostMigrationLineage:
    """Build one independent packet-derived lineage from a validated M032 packet."""

    if variant not in PACKET_DERIVED_VARIANTS:
        raise ValueError(f"variant is not packet-derived: {variant}")

    packet, body, registry, source_dfa, opaque_body = _rehydrate_base(packet_json)
    learning_state = packet.learning_state
    can_update_learning_state = True
    can_rewrite = True

    if variant is LineageVariant.OUTPUT_ONLY:
        can_update_learning_state = False
        can_rewrite = False
    elif variant is LineageVariant.LEARNING_STATE_ABLATED:
        learning_state = PortableLearningState()
    elif variant is LineageVariant.LEARNED_TOOLS_ABLATED:
        registry.learned.clear()

    return PostMigrationLineage(
        variant=variant,
        body=body,
        registry=registry,
        source_dfa=source_dfa,
        opaque_body=opaque_body,
        learning_state=learning_state,
        can_update_learning_state=can_update_learning_state,
        can_rewrite=can_rewrite,
        source_packet_sha256=packet.sha256(),
        origin_checkpoint="validated_m032_packet",
        construction_cost=DeterministicCost(packet_validations=1),
    )


def build_packet_derived_lineages(
    packet_json: str,
) -> dict[LineageVariant, PostMigrationLineage]:
    return {
        variant: build_packet_derived_lineage(packet_json, variant)
        for variant in PACKET_DERIVED_VARIANTS
    }


def build_unchanged_parent_lineage(
    packet_json: str,
    *,
    state_count: int,
    accepting_states: Sequence[bool],
    machine: OpaqueBooleanMachine,
    search_seed: int,
    initial_state: int = 0,
    migrator: UnknownSubstrateMigrator | None = None,
) -> PostMigrationLineage:
    """Reconstruct and migrate the exact parent immediately preceding M025 adoption."""

    packet, adopted_body, adopted_registry, _, _ = _rehydrate_base(packet_json)
    if not adopted_body.archive:
        raise ValueError("M032 passport has no pre-rewrite parent archive")
    if len(adopted_body.adopted_digests) < 2:
        raise ValueError("M032 passport has no pre-adoption digest history")
    if not adopted_registry.learned:
        raise ValueError("M032 passport has no learned rewrite to remove")

    parent_source = adopted_body.archive[-1]
    parent_digests = list(adopted_body.adopted_digests[:-1])
    if not parent_digests or parent_digests[-1] != source_digest(parent_source):
        raise ValueError("M032 parent archive and digest history disagree")

    parent_body = VersionedCodeBody(
        adopted_body.function_name,
        parent_source,
        list(adopted_body.archive[:-1]),
        parent_digests,
    )
    parent_registry = ToolRegistry(
        primitives=adopted_registry.primitives,
        learned=list(adopted_registry.learned[:-1]),
    )
    parent_dfa = compile_policy_to_dfa(
        parent_source,
        parent_body.function_name,
        state_count=state_count,
        accepting_states=accepting_states,
        initial_state=initial_state,
    )
    certificate = _migrate_or_raise(
        parent_dfa,
        machine,
        search_seed,
        migrator=migrator,
        trace={
            "m033_variant": LineageVariant.UNCHANGED_PARENT.value,
            "m032_packet_sha256": packet.sha256(),
        },
    )
    assert certificate.body is not None

    return PostMigrationLineage(
        variant=LineageVariant.UNCHANGED_PARENT,
        body=parent_body,
        registry=parent_registry,
        source_dfa=parent_dfa,
        opaque_body=certificate.body,
        learning_state=packet.learning_state,
        can_update_learning_state=True,
        can_rewrite=True,
        source_packet_sha256=packet.sha256(),
        origin_checkpoint="pre_rewrite_parent_migrated_to_b",
        construction_cost=DeterministicCost(packet_validations=1).plus(
            _migration_cost(certificate)
        ),
    )


def build_fresh_b_lineage(
    initial_source: str,
    function_name: str,
    *,
    state_count: int,
    accepting_states: Sequence[bool],
    machine: OpaqueBooleanMachine,
    search_seed: int,
    initial_state: int = 0,
    migrator: UnknownSubstrateMigrator | None = None,
) -> PostMigrationLineage:
    """Create a fresh learner on B after task reveal, with no migrated state."""

    body = VersionedCodeBody(function_name, initial_source)
    registry = ToolRegistry()
    source_dfa = compile_policy_to_dfa(
        initial_source,
        function_name,
        state_count=state_count,
        accepting_states=accepting_states,
        initial_state=initial_state,
    )
    certificate = _migrate_or_raise(
        source_dfa,
        machine,
        search_seed,
        migrator=migrator,
        trace={"m033_variant": LineageVariant.FRESH_B.value},
    )
    assert certificate.body is not None

    return PostMigrationLineage(
        variant=LineageVariant.FRESH_B,
        body=body,
        registry=registry,
        source_dfa=source_dfa,
        opaque_body=certificate.body,
        learning_state=PortableLearningState(),
        can_update_learning_state=True,
        can_rewrite=True,
        source_packet_sha256=None,
        origin_checkpoint="created_on_b_after_task_reveal",
        construction_cost=_migration_cost(certificate),
    )


def _control_sources(
    family: ControlTaskFamily,
) -> tuple[str, str, int, int]:
    baseline = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""
    if family is ControlTaskFamily.POSITIVE_TOOL:
        target = """\
def policy(state, symbol):
    return ((state * symbol) % 2) + 1
"""
        return baseline, target, 3, 3
    if family is ControlTaskFamily.NEGATIVE_TOOL:
        target = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 1
"""
        return baseline, target, 2, 3
    raise ValueError(f"unsupported M033 control family: {family}")


def generate_control_task(seed: int, family: ControlTaskFamily) -> ControlTask:
    """Generate a control-only task.  Primary seeds 0–63 are rejected by construction."""

    if seed < 1024:
        raise ValueError("M033 control tasks require a seed of at least 1024")

    baseline_source, target_source, state_count, max_edits = _control_sources(family)
    accepting_index = seed % state_count
    accepting_states = tuple(index == accepting_index for index in range(state_count))
    target_dfa = compile_policy_to_dfa(
        target_source,
        "policy",
        state_count=state_count,
        accepting_states=accepting_states,
    )

    transitions: list[Case] = []
    for state in range(state_count):
        for symbol in (0, 1):
            transitions.append(
                Case((state, symbol), target_dfa.transitions[state][symbol])
            )
    rng = random.Random(seed)
    rng.shuffle(transitions)

    held_out: set[tuple[int, ...]] = set()
    while len(held_out) < 8:
        length = rng.randint(2, 5)
        held_out.add(tuple(rng.randrange(2) for _ in range(length)))

    return ControlTask(
        seed=seed,
        family=family,
        function_name="policy",
        baseline_source=baseline_source,
        target_source=target_source,
        state_count=state_count,
        accepting_states=accepting_states,
        initial_state=0,
        development_cases=tuple(transitions),
        held_out_words=tuple(sorted(held_out, key=lambda word: (len(word), word))),
        target_dfa=target_dfa,
        max_edits=max_edits,
    )


def _exact_dfa_match(candidate: DFA, target: DFA) -> bool:
    return canonicalize(minimize_dfa(candidate)) == canonicalize(minimize_dfa(target))


def execute_control_task(
    lineage: PostMigrationLineage,
    task: ControlTask,
    *,
    beam_width: int = 64,
) -> ControlTaskResult:
    """Run one bounded control task without accessing any primary task generator."""

    task_body = VersionedCodeBody(task.function_name, task.baseline_source)
    if not lineage.can_rewrite:
        baseline_dfa = compile_policy_to_dfa(
            task.baseline_source,
            task.function_name,
            state_count=task.state_count,
            accepting_states=task.accepting_states,
            initial_state=task.initial_state,
        )
        passed = sum(
            baseline_dfa.transitions[case.arguments[0]][case.arguments[1]]
            == case.expected
            for case in task.development_cases
        )
        return ControlTaskResult(
            variant=lineage.variant,
            task_sha256=task.sha256(),
            attempted=False,
            adopted=False,
            exact=_exact_dfa_match(baseline_dfa, task.target_dfa),
            quality_per_mille=(1000 * passed) // len(task.development_cases),
            candidates_evaluated=0,
            learned_tool_name=None,
            final_source=task.baseline_source,
            lineage_snapshot_sha256=lineage.snapshot_sha256(),
        )

    rewrite = SelfRewriteEngine(
        lineage.registry,
        max_edits=task.max_edits,
        beam_width=beam_width,
    ).improve(
        task.baseline_source,
        task.function_name,
        task.development_cases,
    )
    adopted = task_body.adopt(rewrite)
    final_source = task_body.active_source
    final_dfa = compile_policy_to_dfa(
        final_source,
        task.function_name,
        state_count=task.state_count,
        accepting_states=task.accepting_states,
        initial_state=task.initial_state,
    )
    passed = rewrite.selected.development.passed

    if lineage.can_update_learning_state:
        lineage.learning_state = PortableLearningState(
            memory=lineage.learning_state.memory
            + ((task.seed, passed, len(task.development_cases)),),
            uncertainty=lineage.learning_state.uncertainty
            + (len(task.development_cases) - passed,),
            exploration_frontier=lineage.learning_state.exploration_frontier
            + ((rewrite.candidates_evaluated, int(adopted)),),
        )
    lineage.construction_cost = lineage.construction_cost.plus(
        DeterministicCost(
            rewrite_candidate_evaluations=rewrite.candidates_evaluated
        )
    )

    return ControlTaskResult(
        variant=lineage.variant,
        task_sha256=task.sha256(),
        attempted=True,
        adopted=adopted,
        exact=_exact_dfa_match(final_dfa, task.target_dfa),
        quality_per_mille=(1000 * passed) // len(task.development_cases),
        candidates_evaluated=rewrite.candidates_evaluated,
        learned_tool_name=rewrite.learned_tool,
        final_source=final_source,
        lineage_snapshot_sha256=lineage.snapshot_sha256(),
    )


def opaque_matches_source(
    lineage: PostMigrationLineage,
    machine: OpaqueBooleanMachine,
    *,
    max_word_length: int = 5,
) -> bool:
    """Exhaustively compare the source DFA and opaque body on a bounded word set."""

    for length in range(max_word_length + 1):
        for word in product((0, 1), repeat=length):
            if lineage.source_dfa.accepts(word) != lineage.opaque_body.accepts(
                machine, word
            ):
                return False
    return True
