"""M040 development engine: cumulative lineage, opaque migration and post-migration rewrite."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
import hashlib
import json
import random
from typing import Mapping, Sequence

from .m012b_body import synthesize_native_body
from .m012b_dfa import DFA, canonicalize, exact_equivalence, minimize_dfa
from .m013e_engine import UnknownSubstrateMigrator
from .m013e_lab import OpaqueBooleanMachine, make_positive_machine
from .m013e_runtime import OpaqueNativeBody, opaque_body_to_dfa, unique_component_count
from .m038_certificate import (
    MAXIMUM_PREFIX_COUNT,
    MAXIMUM_SEARCH_NODES,
    StructuralIncapacityCertificate,
    evidence_digest,
    proved_structural_incapacity,
    verify_structural_incapacity_certificate,
)
from .m038_journal import decode, encode
from .m039_engine import (
    CYCLE_ONE_SEARCH_DEPTH as M039_CYCLE_ONE_SEARCH_DEPTH,
    LATER_CYCLE_SEARCH_DEPTH as M039_LATER_CYCLE_SEARCH_DEPTH,
    OBSERVATION_WORDS as M039_OBSERVATION_WORDS,
    _execute as execute_m039_lineage,
    dfa_digest,
)
from .m039_search_audit import audit_result_searches
from .m039_lineage import LineageTool, ORIGIN_LINEAGE_CONSTRUCTED, ORIGIN_PROTOCOL_SUPPLIED
from .m040_packet import M040LearningState, M040TransportPacket
from .m040_packet_verify import rehydrate_packet
from .m040_anchor import (
    derive_adapted_programs,
    generate_lineage_anchor_task,
)
from .structural import Atom, apply_atom, flip, normalize_dfa

Word = tuple[int, ...]

DEVELOPMENT_SEED = 400_047
DEVELOPMENT_COMMITMENT = "m040-development-v1"
OBSERVATION_DEPTH = 6
POST_MIGRATION_DEPTH = 4
POST_MIGRATION_NODE_BUDGET = 4_096
TASK_GENERATION_ATTEMPTS = 2_048
MIGRATION_CANDIDATE_BUDGET = 75_000
NATIVE_COMPONENT_BUDGET = 320
NATIVE_BYTE_BUDGET = 16_777_216

SEED_DOMAIN = b"m040-derived-seed-v1"
TASK_DOMAIN = b"m040-post-task-v1"
CANDIDATE_DOMAIN = b"m040-post-candidate-v1"
EVENT_DOMAIN = b"m040-event-v1"
EVENT_GENESIS = hashlib.sha256(b"m040-event-genesis-v1").digest()
RESULT_DOMAIN = b"m040-result-v1"
USE_DOMAIN = b"m040-causal-use-v1"

EVENT_TYPES = (
    "PreMigrationLineageCompleted",
    "SubstrateDiscovered",
    "ParentMigrated",
    "PacketCommitted",
    "PacketRehydrated",
    "PostMigrationTaskRevealed",
    "StructuralIncapacityCertified",
    "CandidateAdopted",
    "NativeBodySynthesised",
    "RollbackRequested",
    "RollbackCompleted",
    "ControlEvaluated",
    "ControlNativeSynthesised",
    "SearchAuditCommitted",
    "LineageCompleted",
)


class M040EngineError(RuntimeError):
    pass


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + encode(value)).hexdigest()


def _derive_seed(master_seed: int, label: str, protocol_commitment: str) -> int:
    if master_seed < 0:
        raise ValueError("master seed must be non-negative")
    if not label or not protocol_commitment:
        raise ValueError("seed label and protocol commitment must be non-empty")
    raw = hashlib.sha256(
        SEED_DOMAIN
        + encode(
            {
                "master_seed": master_seed,
                "label": label,
                "protocol_commitment": protocol_commitment,
            }
        )
    ).digest()
    return int.from_bytes(raw[:8], "big", signed=False)


def _words(depth: int) -> tuple[Word, ...]:
    return tuple(
        tuple(int(bit) for bit in word)
        for size in range(depth + 1)
        for word in product((0, 1), repeat=size)
    )


OBSERVATIONS = _words(OBSERVATION_DEPTH)


def _tool_atoms(tool: LineageTool) -> tuple[Atom, ...]:
    atoms: list[Atom] = []
    for step in tool.program:
        raw = step.get("atom")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise M040EngineError("tool program step lacks an atom sequence")
        atoms.append(Atom.from_list(raw))
    return tuple(atoms)


def _apply_tools(base: DFA, tools: Sequence[LineageTool]) -> tuple[DFA | None, tuple[Atom, ...]]:
    current: DFA | None = base
    program: list[Atom] = []
    for tool in tools:
        for atom in _tool_atoms(tool):
            program.append(atom)
            current = apply_atom(current, atom)  # type: ignore[arg-type]
            if current is None:
                return None, tuple(program)
    return current, tuple(program)


def _registry_by_memory(
    registry: Sequence[LineageTool],
    preferred_tool_ids: Sequence[str],
) -> tuple[LineageTool, ...]:
    preferred_rank = {tool_id: index for index, tool_id in enumerate(preferred_tool_ids)}
    original_rank = {tool.tool_id: index for index, tool in enumerate(registry)}
    return tuple(
        sorted(
            registry,
            key=lambda tool: (
                0 if tool.tool_id in preferred_rank else 1,
                preferred_rank.get(tool.tool_id, original_rank[tool.tool_id]),
                original_rank[tool.tool_id],
            ),
        )
    )


def _reachable(
    founder: DFA,
    registry: Sequence[LineageTool],
    maximum_depth: int,
    maximum_nodes: int = POST_MIGRATION_NODE_BUDGET,
) -> set[str]:
    found: set[str] = set()
    nodes = 0

    def descend(current: DFA, remaining: int) -> None:
        nonlocal nodes
        if remaining == 0:
            found.add(dfa_digest(normalize_dfa(current)))
            return
        for tool in registry:
            nodes += 1
            if nodes > maximum_nodes:
                return
            candidate, _ = _apply_tools(current, (tool,))
            if candidate is not None:
                descend(candidate, remaining - 1)

    for depth in range(1, maximum_depth + 1):
        descend(founder, depth)
        if nodes > maximum_nodes:
            break
    return found


@dataclass(frozen=True)
class M040PostTask:
    task_seed: int
    parent_digest: str
    target: DFA
    generating_tool_ids: tuple[str, ...]
    generating_program: tuple[Atom, ...]
    task_family: str
    observation_depth: int = OBSERVATION_DEPTH

    def mapping(self) -> dict[str, object]:
        return {
            "task_seed": self.task_seed,
            "parent_digest": self.parent_digest,
            "target_digest": dfa_digest(self.target),
            "target_states": self.target.n_states,
            "generating_tool_ids": list(self.generating_tool_ids),
            "generating_program": [atom.to_list() for atom in self.generating_program],
            "task_family": self.task_family,
            "observation_depth": self.observation_depth,
            "observation_count": len(OBSERVATIONS),
        }

    def digest(self) -> str:
        return _digest(TASK_DOMAIN, self.mapping())


@dataclass
class SearchCounters:
    symbolic_search_nodes: int = 0
    primitive_expansion_operations: int = 0
    candidates_constructed: int = 0
    candidates_evaluated: int = 0
    evidence_checks: int = 0
    tool_symbols_used: int = 0

    def mapping(self) -> dict[str, int]:
        return {
            "symbolic_search_nodes": self.symbolic_search_nodes,
            "primitive_expansion_operations": self.primitive_expansion_operations,
            "candidates_constructed": self.candidates_constructed,
            "candidates_evaluated": self.candidates_evaluated,
            "evidence_checks": self.evidence_checks,
            "tool_symbols_used": self.tool_symbols_used,
        }


@dataclass(frozen=True)
class SearchResult:
    arm: str
    exact: bool
    reason: str
    quality_numerator: int
    quality_denominator: int
    accepted_candidate_id: str | None
    accepted_tool_ids: tuple[str, ...]
    accepted_program: tuple[Atom, ...]
    accepted_body: DFA | None
    counters: Mapping[str, int]

    def mapping(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "exact": self.exact,
            "reason": self.reason,
            "quality_numerator": self.quality_numerator,
            "quality_denominator": self.quality_denominator,
            "accepted_candidate_id": self.accepted_candidate_id,
            "accepted_tool_ids": list(self.accepted_tool_ids),
            "accepted_program": [atom.to_list() for atom in self.accepted_program],
            "accepted_body_digest": (
                None if self.accepted_body is None else dfa_digest(self.accepted_body)
            ),
            "counters": dict(self.counters),
        }


@dataclass(frozen=True)
class M040Event:
    sequence: int
    event_type: str
    previous_hash: bytes
    payload: Mapping[str, object]
    event_hash: bytes

    def mapping(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "previous_hash": self.previous_hash,
            "payload": dict(self.payload),
            "event_hash": self.event_hash,
        }


@dataclass
class M040Journal:
    _records: list[bytes] = field(default_factory=list)
    _head: bytes = EVENT_GENESIS

    def append(self, event_type: str, payload: Mapping[str, object]) -> M040Event:
        if event_type not in EVENT_TYPES:
            raise M040EngineError(f"unknown M040 event type {event_type!r}")
        sequence = len(self._records)
        base = {
            "sequence": sequence,
            "event_type": event_type,
            "previous_hash": self._head,
            "payload": dict(payload),
        }
        event_hash = hashlib.sha256(EVENT_DOMAIN + encode(base)).digest()
        event = M040Event(sequence, event_type, self._head, dict(payload), event_hash)
        self._records.append(encode(event.mapping()))
        self._head = event_hash
        return event

    @property
    def head(self) -> bytes:
        return self._head

    @property
    def records(self) -> tuple[bytes, ...]:
        return tuple(self._records)

    def verify(self, *, expected_head: bytes) -> None:
        previous = EVENT_GENESIS
        for sequence, raw in enumerate(self._records):
            value = decode(raw)
            if not isinstance(value, Mapping):
                raise M040EngineError("journal record is not a mapping")
            if int(value["sequence"]) != sequence:
                raise M040EngineError("journal sequence is discontinuous")
            if str(value["event_type"]) not in EVENT_TYPES:
                raise M040EngineError("journal contains an unknown event type")
            if bytes(value["previous_hash"]) != previous:
                raise M040EngineError("journal hash chain is discontinuous")
            actual = bytes(value["event_hash"])
            base = {
                "sequence": sequence,
                "event_type": str(value["event_type"]),
                "previous_hash": previous,
                "payload": dict(value["payload"]),
            }
            if hashlib.sha256(EVENT_DOMAIN + encode(base)).digest() != actual:
                raise M040EngineError("journal event hash mismatch")
            previous = actual
        if previous != expected_head:
            raise M040EngineError("journal head differs from the external anchor")


@dataclass
class VersionedNativePair:
    source: DFA
    native_json: str
    archive: list[tuple[DFA, str]] = field(default_factory=list)

    def adopt(self, source: DFA, native_json: str) -> None:
        self.archive.append((self.source, self.native_json))
        self.source = normalize_dfa(source)
        self.native_json = native_json

    def rollback(self) -> None:
        if not self.archive:
            raise M040EngineError("rollback requested with an empty archive")
        self.source, self.native_json = self.archive.pop()


@dataclass(frozen=True)
class NativeSynthesis:
    source: DFA
    body: OpaqueNativeBody
    candidate_evaluations: int
    native_components: int
    serialized_bytes: int
    used_opcodes: tuple[str, ...]

    def mapping(self) -> dict[str, object]:
        return {
            "source_digest": dfa_digest(self.source),
            "native_body_sha256": hashlib.sha256(
                self.body.to_json().encode("utf-8")
            ).hexdigest(),
            "candidate_evaluations": self.candidate_evaluations,
            "native_components": self.native_components,
            "serialized_bytes": self.serialized_bytes,
            "used_opcodes": list(self.used_opcodes),
        }


def _synthesise_native(
    source: DFA,
    machine: OpaqueBooleanMachine,
    packet: M040TransportPacket,
    search_seed: int,
) -> NativeSynthesis:
    abstract, evaluations, reason = synthesize_native_body(
        canonicalize(minimize_dfa(source)),
        packet.discovered_substrate().catalog(),
        search_seed,
        MIGRATION_CANDIDATE_BUDGET,
    )
    if abstract is None:
        raise M040EngineError(f"native synthesis failed: {reason}")
    body = OpaqueNativeBody(
        state_width=abstract.state_width,
        next_state=abstract.next_state,
        output=abstract.output,
        initial_state=abstract.initial_state,
        initial_output=abstract.initial_output,
    )
    raw = body.to_json().encode("utf-8")
    components = unique_component_count(body)
    if components > NATIVE_COMPONENT_BUDGET:
        raise M040EngineError("native synthesis exceeded the component budget")
    if len(raw) > NATIVE_BYTE_BUDGET:
        raise M040EngineError("native synthesis exceeded the byte budget")
    exact, witness = exact_equivalence(opaque_body_to_dfa(body, machine), source)
    if not exact:
        raise M040EngineError(f"native synthesis is not exact; witness={witness}")
    return NativeSynthesis(
        source=normalize_dfa(source),
        body=body,
        candidate_evaluations=evaluations,
        native_components=components,
        serialized_bytes=len(raw),
        used_opcodes=tuple(sorted(body.used_opcodes())),
    )


def _observations(target: DFA) -> dict[Word, bool]:
    return {word: target.accepts(word) for word in OBSERVATIONS}


def _quality(body: DFA, observations: Mapping[Word, bool]) -> int:
    return sum(int(body.accepts(word) == expected) for word, expected in observations.items())


def _candidate_id(
    *,
    arm: str,
    tool_ids: Sequence[str],
    program: Sequence[Atom],
    body: DFA,
) -> str:
    return _digest(
        CANDIDATE_DOMAIN,
        {
            "arm": arm,
            "tool_ids": list(tool_ids),
            "program": [atom.to_list() for atom in program],
            "body_digest": dfa_digest(body),
        },
    )


def _search_arm(
    *,
    arm: str,
    founder: DFA | None,
    target: DFA,
    observations: Mapping[Word, bool],
    registry: Sequence[LineageTool],
    preferred_tool_ids: Sequence[str],
    output_quality_body: DFA | None = None,
    preferred_programs: Sequence[Sequence[str]] = (),
    adapt_prefixes: bool = False,
    maximum_depth: int = POST_MIGRATION_DEPTH,
    node_budget: int = POST_MIGRATION_NODE_BUDGET,
) -> SearchResult:
    if founder is None:
        return SearchResult(
            arm=arm,
            exact=False,
            reason="output_only_has_no_portable_rewrite_state",
            quality_numerator=(
                0 if output_quality_body is None else _quality(output_quality_body, observations)
            ),
            quality_denominator=len(observations),
            accepted_candidate_id=None,
            accepted_tool_ids=(),
            accepted_program=(),
            accepted_body=None,
            counters=SearchCounters().mapping(),
        )
    ordered_registry = _registry_by_memory(registry, preferred_tool_ids)
    counters = SearchCounters()
    best_quality = _quality(founder, observations)
    registry_by_id = {tool.tool_id: tool for tool in registry}


    def evaluate_completed_preferred(
        selected: Sequence[LineageTool],
        expanded: Sequence[Atom],
        current: DFA,
        *,
        reason: str,
    ) -> SearchResult | None:
        nonlocal best_quality
        counters.candidates_constructed += 1
        normalized = normalize_dfa(current)
        quality = 0
        for word, expected in sorted(observations.items()):
            counters.evidence_checks += 1
            quality += int(normalized.accepts(word) == expected)
        best_quality = max(best_quality, quality)
        if quality != len(observations):
            return None
        counters.candidates_evaluated += 1
        exact, _ = exact_equivalence(normalized, target)
        if not exact:
            return None
        ids = tuple(tool.tool_id for tool in selected)
        return SearchResult(
            arm=arm,
            exact=True,
            reason=reason,
            quality_numerator=len(observations),
            quality_denominator=len(observations),
            accepted_candidate_id=_candidate_id(
                arm=arm,
                tool_ids=ids,
                program=tuple(expanded),
                body=normalized,
            ),
            accepted_tool_ids=ids,
            accepted_program=tuple(expanded),
            accepted_body=normalized,
            counters=counters.mapping(),
        )

    def apply_prefix(tool_ids: Sequence[str]) -> tuple[DFA, list[LineageTool], list[Atom]] | None:
        current: DFA | None = founder
        selected: list[LineageTool] = []
        expanded: list[Atom] = []
        for tool_id in tool_ids:
            tool = registry_by_id.get(str(tool_id))
            if tool is None:
                return None
            counters.symbolic_search_nodes += 1
            if counters.symbolic_search_nodes > node_budget:
                return None
            atoms = _tool_atoms(tool)
            for atom in atoms:
                counters.primitive_expansion_operations += 1
                current = apply_atom(current, atom)  # type: ignore[arg-type]
                if current is None:
                    return None
                expanded.append(atom)
            if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED:
                counters.tool_symbols_used += 1
            selected.append(tool)
        if current is None:
            return None
        return current, selected, expanded

    primitive_suffixes = tuple(
        tool for tool in ordered_registry
        if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    )
    for preferred_program in preferred_programs:
        prefix = apply_prefix(preferred_program)
        if prefix is None:
            continue
        prefix_body, prefix_tools, prefix_atoms = prefix
        if adapt_prefixes:
            for suffix in primitive_suffixes:
                counters.symbolic_search_nodes += 1
                if counters.symbolic_search_nodes > node_budget:
                    return SearchResult(
                        arm=arm,
                        exact=False,
                        reason="symbolic_node_budget_exhausted",
                        quality_numerator=best_quality,
                        quality_denominator=len(observations),
                        accepted_candidate_id=None,
                        accepted_tool_ids=(),
                        accepted_program=(),
                        accepted_body=None,
                        counters=counters.mapping(),
                    )
                current: DFA | None = prefix_body
                suffix_atoms = _tool_atoms(suffix)
                for atom in suffix_atoms:
                    counters.primitive_expansion_operations += 1
                    current = apply_atom(current, atom)  # type: ignore[arg-type]
                    if current is None:
                        break
                if current is None:
                    continue
                found = evaluate_completed_preferred(
                    prefix_tools + [suffix],
                    prefix_atoms + list(suffix_atoms),
                    current,
                    reason="transported_prefix_adapted",
                )
                if found is not None:
                    return found
        else:
            found = evaluate_completed_preferred(
                prefix_tools,
                prefix_atoms,
                prefix_body,
                reason="transported_continuation_adopted",
            )
            if found is not None:
                return found
    def descend(
        current: DFA,
        selected: tuple[LineageTool, ...],
        expanded: tuple[Atom, ...],
        remaining: int,
    ) -> SearchResult | None:
        nonlocal best_quality
        if remaining == 0:
            counters.candidates_constructed += 1
            normalized = normalize_dfa(current)
            quality = 0
            for word, expected in sorted(observations.items()):
                counters.evidence_checks += 1
                quality += int(normalized.accepts(word) == expected)
            best_quality = max(best_quality, quality)
            if quality != len(observations):
                return None
            counters.candidates_evaluated += 1
            exact, _ = exact_equivalence(normalized, target)
            if not exact:
                return None
            ids = tuple(tool.tool_id for tool in selected)
            return SearchResult(
                arm=arm,
                exact=True,
                reason="exact_candidate_adopted",
                quality_numerator=len(observations),
                quality_denominator=len(observations),
                accepted_candidate_id=_candidate_id(
                    arm=arm,
                    tool_ids=ids,
                    program=expanded,
                    body=normalized,
                ),
                accepted_tool_ids=ids,
                accepted_program=expanded,
                accepted_body=normalized,
                counters=counters.mapping(),
            )

        for tool in ordered_registry:
            counters.symbolic_search_nodes += 1
            if counters.symbolic_search_nodes > node_budget:
                return SearchResult(
                    arm=arm,
                    exact=False,
                    reason="symbolic_node_budget_exhausted",
                    quality_numerator=best_quality,
                    quality_denominator=len(observations),
                    accepted_candidate_id=None,
                    accepted_tool_ids=(),
                    accepted_program=(),
                    accepted_body=None,
                    counters=counters.mapping(),
                )
            current_body: DFA | None = current
            atoms = _tool_atoms(tool)
            for atom in atoms:
                counters.primitive_expansion_operations += 1
                current_body = apply_atom(current_body, atom)  # type: ignore[arg-type]
                if current_body is None:
                    break
            if current_body is None:
                continue
            if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED:
                counters.tool_symbols_used += 1
            found = descend(
                current_body,
                selected + (tool,),
                expanded + atoms,
                remaining - 1,
            )
            if found is not None:
                return found
        return None

    for depth in range(1, maximum_depth + 1):
        result = descend(founder, (), (), depth)
        if result is not None:
            return result
    return SearchResult(
        arm=arm,
        exact=False,
        reason="no_exact_candidate_within_committed_language",
        quality_numerator=best_quality,
        quality_denominator=len(observations),
        accepted_candidate_id=None,
        accepted_tool_ids=(),
        accepted_program=(),
        accepted_body=None,
        counters=counters.mapping(),
    )


def _learning_state(pre_result, node_budget: int) -> M040LearningState:
    accepted = tuple(cycle.accepted_candidate_id for cycle in pre_result.manifest.cycles)
    lineage_tools = tuple(pre_result.gate2_tool_ids)
    uses: list[str] = []
    counts = {tool_id: 0 for tool_id in lineage_tools}
    for use in pre_result.manifest.tool_uses:
        use_id = _digest(
            USE_DOMAIN,
            {
                "tool_id": use.tool_id,
                "cycle": use.cycle,
                "candidate_id": use.candidate_id,
                "adopted": use.adopted,
                "block": use.proposing_block_index,
            },
        )
        uses.append(use_id)
        if use.tool_id in counts and use.adopted:
            counts[use.tool_id] += 1
    preferred = tuple(sorted(lineage_tools, key=lambda tool_id: (-counts[tool_id], tool_id)))
    continuations: list[tuple[str, ...]] = []
    for raw in pre_result.lineage_journal_records:
        value = decode(raw)
        if not isinstance(value, Mapping):
            raise M040EngineError("pre-migration journal record is not a mapping")
        if str(value["event_type"]) != "MutationAdopted" or int(value["cycle"]) < 2:
            continue
        parameters = dict(value["operation_parameters"])
        program = tuple(str(tool_id) for tool_id in parameters["tool_ids"])
        if any(tool_id in lineage_tools for tool_id in program) and program not in continuations:
            continuations.append(program)
    if not continuations:
        raise M040EngineError("pre-migration lineage produced no continuation frontier")
    return M040LearningState(
        accepted_candidate_ids=accepted,
        lineage_tool_ids=lineage_tools,
        causal_tool_use_ids=tuple(uses),
        preferred_tool_ids=preferred,
        continuation_programs=tuple(continuations),
        exploration_depth=POST_MIGRATION_DEPTH,
        remaining_search_nodes=node_budget,
    )


def _post_task_exact_frontier(
    *,
    packet: M040TransportPacket,
    founder: DFA,
    task_seed: int,
) -> M040PostTask:
    registry = {tool.tool_id: tool for tool in packet.tool_registry}
    primitive_tools = tuple(
        tool for tool in packet.tool_registry
        if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    )
    programs = list(packet.learning_state.continuation_programs)
    random.Random(task_seed).shuffle(programs)
    primitive_reachable = _reachable(founder, primitive_tools, POST_MIGRATION_DEPTH)
    for program_ids in programs[:TASK_GENERATION_ATTEMPTS]:
        tools = tuple(registry[tool_id] for tool_id in program_ids)
        raw, program = _apply_tools(founder, tools)
        if raw is None:
            continue
        target = normalize_dfa(raw)
        if target.n_states <= founder.n_states:
            continue
        if dfa_digest(target) in primitive_reachable:
            continue
        observations = _observations(target)
        certificate = proved_structural_incapacity(
            founder,
            observations,
            maximum_search_nodes=MAXIMUM_SEARCH_NODES,
            maximum_prefix_count=MAXIMUM_PREFIX_COUNT,
        )
        if certificate.proves_incapacity():
            return M040PostTask(
                task_seed=task_seed,
                parent_digest=dfa_digest(founder),
                target=target,
                generating_tool_ids=tuple(program_ids),
                generating_program=program,
                task_family="exact_frontier",
            )
    raise M040EngineError("no transported continuation frontier produced an admissible task")


def _post_task_prefix_adaptation(
    *,
    packet: M040TransportPacket,
    founder: DFA,
    task_seed: int,
) -> M040PostTask:
    registry = {tool.tool_id: tool for tool in packet.tool_registry}
    primitive_tools = [
        tool for tool in packet.tool_registry
        if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    ]
    if not primitive_tools:
        raise M040EngineError("transported packet contains no birth primitives")
    programs = list(packet.learning_state.continuation_programs)
    rng = random.Random(task_seed)
    rng.shuffle(programs)
    rng.shuffle(primitive_tools)
    primitive_reachable = _reachable(founder, primitive_tools, POST_MIGRATION_DEPTH)
    attempts = 0
    for prefix_ids in programs:
        prefix_tools = tuple(registry[tool_id] for tool_id in prefix_ids)
        for suffix in primitive_tools:
            attempts += 1
            if attempts > TASK_GENERATION_ATTEMPTS:
                break
            tool_ids = tuple(prefix_ids) + (suffix.tool_id,)
            if len(tool_ids) > POST_MIGRATION_DEPTH:
                continue
            raw, program = _apply_tools(founder, prefix_tools + (suffix,))
            if raw is None:
                continue
            target = normalize_dfa(raw)
            if target.n_states <= founder.n_states:
                continue
            if dfa_digest(target) in primitive_reachable:
                continue
            observations = _observations(target)
            certificate = proved_structural_incapacity(
                founder,
                observations,
                maximum_search_nodes=MAXIMUM_SEARCH_NODES,
                maximum_prefix_count=MAXIMUM_PREFIX_COUNT,
            )
            if not certificate.proves_incapacity():
                continue
            return M040PostTask(
                task_seed=task_seed,
                parent_digest=dfa_digest(founder),
                target=target,
                generating_tool_ids=tool_ids,
                generating_program=program,
                task_family="prefix_plus_primitive",
            )
    raise M040EngineError("no transported prefix plus primitive produced an admissible task")

def _certificate(
    founder: DFA,
    observations: Mapping[Word, bool],
) -> StructuralIncapacityCertificate:
    certificate = proved_structural_incapacity(
        founder,
        observations,
        maximum_search_nodes=MAXIMUM_SEARCH_NODES,
        maximum_prefix_count=MAXIMUM_PREFIX_COUNT,
    )
    verify_structural_incapacity_certificate(
        founder,
        observations,
        certificate,
        recompute=True,
    )
    if not certificate.proves_incapacity():
        raise M040EngineError("post-migration task lacks a structural-incapacity proof")
    return certificate


@dataclass(frozen=True)
class M040DevelopmentResult:
    master_seed: int
    protocol_commitment: str
    pre_migration_manifest_digest: str
    pre_migration_journal_head: str
    pre_migration_journal_records_digest: str
    machine_id: str
    migration: Mapping[str, object]
    packet_json: str
    packet_sha256: str
    task: M040PostTask
    certificate: Mapping[str, object]
    arms: Mapping[str, SearchResult]
    accepted_native: Mapping[str, object]
    control_native_baselines: Mapping[str, Mapping[str, object]]
    pre_migration_search_audits: tuple[Mapping[str, object], ...]
    post_migration_search_audits: Mapping[str, Mapping[str, object]]
    rollback_restored_exactly: bool
    accepted_tool_was_pre_migration_owned: bool
    journal_head: str
    journal_records: tuple[bytes, ...]
    trans_substrate_continuity_supported: bool
    post_migration_plasticity_supported: bool
    replay_supported: bool
    schema: str = "m040-development-result/2"

    def mapping(self, *, include_records: bool = False) -> dict[str, object]:
        result = {
            "schema": self.schema,
            "status": "consumed-development-result",
            "master_seed": self.master_seed,
            "protocol_commitment": self.protocol_commitment,
            "pre_migration_manifest_digest": self.pre_migration_manifest_digest,
            "pre_migration_journal_head": self.pre_migration_journal_head,
            "pre_migration_journal_records_digest": self.pre_migration_journal_records_digest,
            "machine_id": self.machine_id,
            "migration": dict(self.migration),
            "packet_sha256": self.packet_sha256,
            "packet_bytes": len(self.packet_json.encode("utf-8")),
            "task": self.task.mapping(),
            "task_digest": self.task.digest(),
            "certificate": dict(self.certificate),
            "arms": {name: arm.mapping() for name, arm in sorted(self.arms.items())},
            "accepted_native": dict(self.accepted_native),
            "control_native_baselines": {
                name: dict(value) for name, value in sorted(self.control_native_baselines.items())
            },
            "pre_migration_search_audits": [
                dict(value) for value in self.pre_migration_search_audits
            ],
            "post_migration_search_audits": {
                name: dict(value) for name, value in sorted(self.post_migration_search_audits.items())
            },
            "rollback_restored_exactly": self.rollback_restored_exactly,
            "accepted_tool_was_pre_migration_owned": self.accepted_tool_was_pre_migration_owned,
            "journal_head": self.journal_head,
            "journal_record_count": len(self.journal_records),
            "journal_records_sha256": hashlib.sha256(b"".join(self.journal_records)).hexdigest(),
            "trans_substrate_continuity_supported": self.trans_substrate_continuity_supported,
            "post_migration_plasticity_supported": self.post_migration_plasticity_supported,
            "replay_supported": self.replay_supported,
            "no_sealed_block_opened": True,
            "no_canonical_claim": True,
        }
        if include_records:
            result["journal_records"] = [record.hex() for record in self.journal_records]
        return result

    def digest(self) -> str:
        stable = self.mapping()
        stable["replay_supported"] = False
        return _digest(RESULT_DOMAIN, stable)


def _execute(
    master_seed: int,
    protocol_commitment: str,
    *,
    task_family: str = "lineage_anchor",
) -> M040DevelopmentResult:
    journal = M040Journal()
    pre_seed = _derive_seed(master_seed, "pre-migration-lineage", protocol_commitment)
    pre_commitment = f"{protocol_commitment}/m039-pre-migration"
    pre = execute_m039_lineage(pre_seed, pre_commitment)
    if not (
        pre.three_cycles_accepted
        and pre.later_tool_reuse_supported
        and pre.tool_ablation_supported
        and pre.gate2_tool_ids
    ):
        raise M040EngineError("pre-migration lineage did not satisfy the committed base")
    final_source = normalize_dfa(pre.cycle_tasks[-1].target)
    original_founder = normalize_dfa(pre.cycle_tasks[0].founder)
    pre_audits = audit_result_searches(
        tasks=pre.cycle_tasks,
        cycles=pre.manifest.cycles,
        final_registry=pre.manifest.tool_registry,
        cycle_one_depth=M039_CYCLE_ONE_SEARCH_DEPTH,
        later_depth=M039_LATER_CYCLE_SEARCH_DEPTH,
        observation_words=M039_OBSERVATION_WORDS,
    )
    pre_records_digest = hashlib.sha256(b"".join(pre.lineage_journal_records)).hexdigest()
    journal.append(
        "PreMigrationLineageCompleted",
        {
            "manifest_digest": pre.manifest.digest(),
            "journal_head": pre.lineage_journal_head,
            "journal_records_digest": pre_records_digest,
            "final_body_digest": dfa_digest(final_source),
            "gate2_tool_ids": list(pre.gate2_tool_ids),
        },
    )

    machine_seed = _derive_seed(master_seed, "opaque-machine", protocol_commitment)
    machine_family = machine_seed % 3
    machine = make_positive_machine(machine_seed, machine_family)
    migration_seed = _derive_seed(master_seed, "opaque-migration", protocol_commitment)
    migrator = UnknownSubstrateMigrator(
        probe_budget=120,
        candidate_budget=MIGRATION_CANDIDATE_BUDGET,
        native_component_budget=NATIVE_COMPONENT_BUDGET,
        serialized_byte_budget=NATIVE_BYTE_BUDGET,
        cpu_seconds=120.0,
    )
    migration = migrator.migrate(
        final_source,
        machine,
        migration_seed,
        trace={
            "m040_protocol_commitment": protocol_commitment,
            "m039_manifest_digest": pre.manifest.digest(),
            "m039_journal_head": pre.lineage_journal_head,
        },
    )
    if migration.status != "success" or migration.body is None:
        raise M040EngineError(
            f"opaque migration failed: {migration.status}:{migration.reason}"
        )
    migrated_dfa = opaque_body_to_dfa(migration.body, machine)
    migration_exact, migration_witness = exact_equivalence(migrated_dfa, final_source)
    if not migration_exact:
        raise M040EngineError(f"migrated parent is not exact; witness={migration_witness}")
    journal.append(
        "SubstrateDiscovered",
        {
            "machine_id": machine.machine_id,
            "probe_calls": migration.probe_calls,
            "stable_opcode_ids": [opcode.opcode for opcode in migration.substrate.stable_opcodes],
            "unstable_opcode_ids": list(migration.substrate.unstable_opcodes),
        },
    )
    journal.append(
        "ParentMigrated",
        {
            "source_body_digest": dfa_digest(final_source),
            "native_body_sha256": hashlib.sha256(
                migration.body.to_json().encode("utf-8")
            ).hexdigest(),
            "candidate_evaluations": migration.candidate_evaluations,
            "native_components": migration.native_components,
            "serialized_bytes": migration.serialized_bytes,
            "used_opcodes": list(migration.used_opcodes),
            "exact": True,
        },
    )

    learning_state = _learning_state(pre, POST_MIGRATION_NODE_BUDGET)
    packet = M040TransportPacket.build(
        protocol_commitment=protocol_commitment,
        source_lineage_commitment=pre_commitment,
        lineage_id=pre.manifest.lineage_id,
        pre_migration_manifest_digest=pre.manifest.digest(),
        source_dfa=final_source,
        opaque_body=migration.body,
        machine_id=machine.machine_id,
        substrate=migration.substrate,
        tool_registry=pre.manifest.tool_registry,
        learning_state=learning_state,
    )
    raw_packet = packet.to_json()
    journal.append(
        "PacketCommitted",
        {
            "packet_sha256": packet.sha256(),
            "packet_bytes": len(raw_packet.encode("utf-8")),
        },
    )
    rehydrated = rehydrate_packet(raw_packet, expected_sha256=packet.sha256())
    if rehydrated.to_json() != raw_packet:
        raise M040EngineError("packet did not rehydrate canonically")
    rehydrated_source = rehydrated.source_dfa()
    exact_packet_body, _ = exact_equivalence(rehydrated_source, final_source)
    if not exact_packet_body:
        raise M040EngineError("rehydrated source body differs from the migrated parent")
    rehydrated_native = rehydrated.opaque_body()
    exact_packet_native, _ = exact_equivalence(
        opaque_body_to_dfa(rehydrated_native, machine),
        final_source,
    )
    if not exact_packet_native:
        raise M040EngineError("rehydrated native body differs from the migrated parent")
    journal.append(
        "PacketRehydrated",
        {
            "packet_sha256": rehydrated.sha256(),
            "source_body_digest": dfa_digest(rehydrated_source),
            "registry_size": len(rehydrated.tool_registry),
            "preferred_tool_ids": list(rehydrated.learning_state.preferred_tool_ids),
        },
    )

    task_seed = _derive_seed(master_seed, "post-migration-task", protocol_commitment)
    if task_family == "exact_frontier":
        task = _post_task_exact_frontier(
            packet=rehydrated, founder=rehydrated_source, task_seed=task_seed
        )
        preferred_post_programs = rehydrated.learning_state.continuation_programs
    elif task_family == "prefix_adaptation":
        task = _post_task_prefix_adaptation(
            packet=rehydrated, founder=rehydrated_source, task_seed=task_seed
        )
        preferred_post_programs = rehydrated.learning_state.continuation_programs
    elif task_family == "lineage_anchor":
        anchor_task = generate_lineage_anchor_task(
            packet=rehydrated,
            founder=rehydrated_source,
            task_seed=task_seed,
            maximum_depth=POST_MIGRATION_DEPTH,
            node_budget=POST_MIGRATION_NODE_BUDGET,
            observations=OBSERVATIONS,
        )
        task = M040PostTask(
            task_seed=anchor_task.task_seed,
            parent_digest=anchor_task.parent_digest,
            target=anchor_task.target,
            generating_tool_ids=anchor_task.generating_tool_ids,
            generating_program=anchor_task.generating_program,
            task_family="lineage_anchor",
        )
        preferred_post_programs = derive_adapted_programs(
            rehydrated,
            task_seed=task_seed,
            maximum_depth=POST_MIGRATION_DEPTH,
        )
    else:
        raise M040EngineError(f"unknown M040 task family {task_family!r}")
    journal.append(
        "PostMigrationTaskRevealed",
        {
            "task_digest": task.digest(),
            "target_digest": dfa_digest(task.target),
            "target_states": task.target.n_states,
        },
    )
    observations = _observations(task.target)
    certificate = _certificate(rehydrated_source, observations)
    certificate_mapping = certificate.to_mapping()
    journal.append(
        "StructuralIncapacityCertified",
        {
            "certificate": certificate_mapping,
            "evidence_digest": evidence_digest(observations).hex(),
        },
    )

    full_registry = tuple(rehydrated.tool_registry)
    primitive_registry = tuple(
        tool
        for tool in full_registry
        if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    )
    lineage_tool_ids = set(rehydrated.learning_state.lineage_tool_ids)
    tool_ablated_registry = tuple(
        tool for tool in full_registry if tool.tool_id not in lineage_tool_ids
    )
    full = _search_arm(
        arm="complete_migrated_lineage",
        founder=rehydrated_source,
        target=task.target,
        observations=observations,
        registry=full_registry,
        preferred_tool_ids=rehydrated.learning_state.preferred_tool_ids,
        preferred_programs=preferred_post_programs,
        adapt_prefixes=(task_family == "prefix_adaptation"),
    )
    fresh = _search_arm(
        arm="fresh_on_b",
        founder=rehydrated_source,
        target=task.target,
        observations=observations,
        registry=primitive_registry,
        preferred_tool_ids=(),
    )
    unchanged = _search_arm(
        arm="unchanged_parent_migrated",
        founder=original_founder,
        target=task.target,
        observations=observations,
        registry=primitive_registry,
        preferred_tool_ids=(),
    )
    output_only = _search_arm(
        arm="output_only",
        founder=None,
        output_quality_body=rehydrated_source,
        target=task.target,
        observations=observations,
        registry=(),
        preferred_tool_ids=(),
    )
    memory_ablated = _search_arm(
        arm="learning_state_ablated",
        founder=rehydrated_source,
        target=task.target,
        observations=observations,
        registry=full_registry,
        preferred_tool_ids=(),
    )
    tool_ablated = _search_arm(
        arm="learned_tool_ablated",
        founder=rehydrated_source,
        target=task.target,
        observations=observations,
        registry=tool_ablated_registry,
        preferred_tool_ids=(),
    )
    arms = {
        result.arm: result
        for result in (full, fresh, unchanged, output_only, memory_ablated, tool_ablated)
    }
    unchanged_native = _synthesise_native(
        original_founder,
        machine,
        rehydrated,
        _derive_seed(master_seed, "unchanged-parent-native", protocol_commitment),
    )
    control_native_baselines = {
        "complete_parent_migrated": {
            "source_digest": dfa_digest(rehydrated_source),
            "native_body_sha256": hashlib.sha256(
                rehydrated_native.to_json().encode("utf-8")
            ).hexdigest(),
            "exact": True,
        },
        "unchanged_parent_migrated": {**unchanged_native.mapping(), "exact": True},
        "output_only": {
            "source_digest": dfa_digest(rehydrated_source),
            "native_body_sha256": hashlib.sha256(
                rehydrated_native.to_json().encode("utf-8")
            ).hexdigest(),
            "exact": True,
            "portable_rewrite_state": False,
        },
    }
    journal.append("ControlNativeSynthesised", control_native_baselines)
    for result in arms.values():
        journal.append("ControlEvaluated", result.mapping())

    from .m040_search_audit import audit_post_search

    audit_inputs = {
        "complete_migrated_lineage": (
            rehydrated_source,
            None,
            full_registry,
            rehydrated.learning_state.preferred_tool_ids,
            preferred_post_programs,
            task_family == "prefix_adaptation",
        ),
        "fresh_on_b": (rehydrated_source, None, primitive_registry, (), (), False),
        "unchanged_parent_migrated": (original_founder, None, primitive_registry, (), (), False),
        "output_only": (None, rehydrated_source, (), (), (), False),
        "learning_state_ablated": (rehydrated_source, None, full_registry, (), (), False),
        "learned_tool_ablated": (rehydrated_source, None, tool_ablated_registry, (), (), False),
    }
    post_audits = {}
    for name, audit_input in audit_inputs.items():
        (
            audit_founder, output_body, audit_registry, preferred_ids,
            preferred_programs, audit_adapt_prefixes,
        ) = audit_input
        audit = audit_post_search(
            arm=name,
            founder=audit_founder,
            output_quality_body=output_body,
            target=task.target,
            observations=observations,
            registry=audit_registry,
            preferred_tool_ids=preferred_ids,
            preferred_programs=preferred_programs,
            adapt_prefixes=audit_adapt_prefixes,
            maximum_depth=POST_MIGRATION_DEPTH,
            node_budget=POST_MIGRATION_NODE_BUDGET,
            expected_result=arms[name],
        )
        post_audits[name] = audit.mapping()
    journal.append(
        "SearchAuditCommitted",
        {
            "pre_migration": [audit.mapping() for audit in pre_audits],
            "post_migration": post_audits,
        },
    )

    if not full.exact or full.accepted_body is None:
        raise M040EngineError("complete migrated lineage did not solve the post-migration task")
    accepted_pre_owned = any(
        tool_id in lineage_tool_ids for tool_id in full.accepted_tool_ids
    )
    if not accepted_pre_owned:
        raise M040EngineError("accepted post-migration candidate used no pre-migration tool")
    journal.append(
        "CandidateAdopted",
        {
            "candidate_id": full.accepted_candidate_id,
            "tool_ids": list(full.accepted_tool_ids),
            "program": [atom.to_list() for atom in full.accepted_program],
            "source_body_digest": dfa_digest(full.accepted_body),
        },
    )

    accepted_native = _synthesise_native(
        full.accepted_body,
        machine,
        rehydrated,
        _derive_seed(master_seed, "post-native-synthesis", protocol_commitment),
    )
    journal.append("NativeBodySynthesised", accepted_native.mapping())
    versioned = VersionedNativePair(rehydrated_source, rehydrated_native.to_json())
    versioned.adopt(full.accepted_body, accepted_native.body.to_json())
    accepted_source_digest = dfa_digest(versioned.source)
    accepted_native_json = versioned.native_json

    bad_source_raw = apply_atom(versioned.source, flip("initial"))
    if bad_source_raw is None:
        raise M040EngineError("forced rollback mutation could not be constructed")
    bad_source = normalize_dfa(bad_source_raw)
    bad_native = _synthesise_native(
        bad_source,
        machine,
        rehydrated,
        _derive_seed(master_seed, "bad-native-synthesis", protocol_commitment),
    )
    versioned.adopt(bad_source, bad_native.body.to_json())
    bad_exact, _ = exact_equivalence(versioned.source, task.target)
    if bad_exact:
        raise M040EngineError("forced bad provisional adoption remained exact")
    journal.append(
        "RollbackRequested",
        {
            "bad_source_digest": dfa_digest(bad_source),
            "bad_native_sha256": hashlib.sha256(
                bad_native.body.to_json().encode("utf-8")
            ).hexdigest(),
        },
    )
    versioned.rollback()
    rollback_exact = (
        dfa_digest(versioned.source) == accepted_source_digest
        and versioned.native_json == accepted_native_json
    )
    if not rollback_exact:
        raise M040EngineError("rollback did not restore the accepted native/source pair")
    journal.append(
        "RollbackCompleted",
        {
            "restored_source_digest": dfa_digest(versioned.source),
            "restored_native_sha256": hashlib.sha256(
                versioned.native_json.encode("utf-8")
            ).hexdigest(),
            "exact": rollback_exact,
        },
    )

    lower_quality_controls = all(
        not arms[name].exact
        for name in (
            "fresh_on_b",
            "unchanged_parent_migrated",
            "output_only",
            "learned_tool_ablated",
        )
    )
    full_nodes = int(full.counters["symbolic_search_nodes"])
    memory_nodes = int(memory_ablated.counters["symbolic_search_nodes"])
    continuity = (
        pre.three_cycles_accepted
        and migration_exact
        and exact_packet_body
        and exact_packet_native
        and full.exact
        and rollback_exact
        and accepted_pre_owned
    )
    plasticity = (
        continuity
        and lower_quality_controls
        and full_nodes < memory_nodes
        and not tool_ablated.exact
    )
    journal.append(
        "LineageCompleted",
        {
            "trans_substrate_continuity_supported": continuity,
            "post_migration_plasticity_supported": plasticity,
            "accepted_source_digest": accepted_source_digest,
            "accepted_native_sha256": hashlib.sha256(
                accepted_native_json.encode("utf-8")
            ).hexdigest(),
        },
    )
    journal.verify(expected_head=journal.head)

    migration_mapping = {
        "machine_seed": machine_seed,
        "machine_family": machine_family,
        "migration_seed": migration_seed,
        "probe_calls": migration.probe_calls,
        "candidate_evaluations": migration.candidate_evaluations,
        "native_components": migration.native_components,
        "serialized_bytes": migration.serialized_bytes,
        "used_opcodes": list(migration.used_opcodes),
        "source_body_digest": dfa_digest(final_source),
        "native_body_sha256": hashlib.sha256(
            migration.body.to_json().encode("utf-8")
        ).hexdigest(),
        "exact": migration_exact,
    }
    return M040DevelopmentResult(
        master_seed=master_seed,
        protocol_commitment=protocol_commitment,
        pre_migration_manifest_digest=pre.manifest.digest(),
        pre_migration_journal_head=pre.lineage_journal_head,
        pre_migration_journal_records_digest=pre_records_digest,
        machine_id=machine.machine_id,
        migration=migration_mapping,
        packet_json=raw_packet,
        packet_sha256=packet.sha256(),
        task=task,
        certificate=certificate_mapping,
        arms=arms,
        accepted_native=accepted_native.mapping(),
        control_native_baselines=control_native_baselines,
        pre_migration_search_audits=tuple(audit.mapping() for audit in pre_audits),
        post_migration_search_audits=post_audits,
        rollback_restored_exactly=rollback_exact,
        accepted_tool_was_pre_migration_owned=accepted_pre_owned,
        journal_head=journal.head.hex(),
        journal_records=journal.records,
        trans_substrate_continuity_supported=continuity,
        post_migration_plasticity_supported=plasticity,
        replay_supported=False,
    )


def run_m040_development(
    master_seed: int = DEVELOPMENT_SEED,
    *,
    protocol_commitment: str = DEVELOPMENT_COMMITMENT,
    require_replay: bool = True,
    task_family: str = "lineage_anchor",
) -> M040DevelopmentResult:
    first = _execute(master_seed, protocol_commitment, task_family=task_family)
    if not require_replay:
        return first
    replayed = _execute(master_seed, protocol_commitment, task_family=task_family)
    if first.digest() != replayed.digest():
        raise M040EngineError("seed-only replay changed the M040 result digest")
    if first.packet_json != replayed.packet_json:
        raise M040EngineError("seed-only replay changed the transport packet bytes")
    if first.journal_records != replayed.journal_records:
        raise M040EngineError("seed-only replay changed the M040 journal bytes")
    return M040DevelopmentResult(
        master_seed=first.master_seed,
        protocol_commitment=first.protocol_commitment,
        pre_migration_manifest_digest=first.pre_migration_manifest_digest,
        pre_migration_journal_head=first.pre_migration_journal_head,
        pre_migration_journal_records_digest=first.pre_migration_journal_records_digest,
        machine_id=first.machine_id,
        migration=first.migration,
        packet_json=first.packet_json,
        packet_sha256=first.packet_sha256,
        task=first.task,
        certificate=first.certificate,
        arms=first.arms,
        accepted_native=first.accepted_native,
        control_native_baselines=first.control_native_baselines,
        pre_migration_search_audits=first.pre_migration_search_audits,
        post_migration_search_audits=first.post_migration_search_audits,
        rollback_restored_exactly=first.rollback_restored_exactly,
        accepted_tool_was_pre_migration_owned=first.accepted_tool_was_pre_migration_owned,
        journal_head=first.journal_head,
        journal_records=first.journal_records,
        trans_substrate_continuity_supported=first.trans_substrate_continuity_supported,
        post_migration_plasticity_supported=first.post_migration_plasticity_supported,
        replay_supported=True,
    )
