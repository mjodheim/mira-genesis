"""Deterministic M039 development engine in the bounded DFA domain.

The engine runs one cumulative F0 -> F1 -> F2 -> F3 lineage.  Cycle 1 searches only the
birth registry and composes the adopted primitive trace into a lineage-owned macro.  Cycles
2 and 3 search at a smaller symbolic depth with that macro available.  Their tasks are
accepted by the laboratory only when equal-budget primitive-only ablation cannot solve them.

Nothing in this module opens a sealed block or supports a canonical claim.  Development
seeds are consumed as soon as their generated tasks are observed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Iterator, Mapping, Sequence

from .m012b_dfa import DFA, exact_equivalence, random_minimal_dfa
from .m038_certificate import (
    MAXIMUM_PREFIX_COUNT,
    MAXIMUM_SEARCH_NODES,
    StructuralIncapacityCertificate,
    evidence_digest,
    proved_structural_incapacity,
    verify_structural_incapacity_certificate,
)
from .m038_journal import AuditCounters, RollingCommitment, encode
from .m039_journal import LineageJournal, state_digest
from .m039_lineage import (
    CycleManifest,
    KIND_COMPOSITION,
    LINEAGE_SCHEMA,
    LineageManifest,
    LineageTool,
    ORIGIN_LINEAGE_CONSTRUCTED,
    PHASE_CYCLE,
    ReplayInputs,
    ToolProvenance,
    ToolUse,
    derive_cycle_seed,
    derive_lineage_id,
    gate2_eligible,
    protocol_primitive_tool,
    verify_replayed_manifest,
)
from .structural import (
    Atom,
    all_atoms,
    apply_atom,
    apply_atoms,
    enumerate_words,
    flip,
    growth_atoms,
    normalize_dfa,
    walk,
)

Word = tuple[int, ...]

CYCLES = 3
OBSERVATION_DEPTH = 6
OBSERVATION_WORDS: tuple[Word, ...] = enumerate_words(OBSERVATION_DEPTH)
FOUNDER_STATES = 4
CYCLE_ONE_SEARCH_DEPTH = 3
LATER_CYCLE_SEARCH_DEPTH = 2
MAXIMUM_TASK_ATTEMPTS = 32
MAXIMUM_TASK_PROGRAMS = 100_000
MAXIMUM_CANDIDATE_SEARCH_NODES = 150_000
DEVELOPMENT_SEED = 390_039
DEVELOPMENT_COMMITMENT = "m039-development-v1"

BODY_DOMAIN = b"m039-body-v1"
TASK_DOMAIN = b"m039-task-v1"
CANDIDATE_DOMAIN = b"m039-candidate-v1"
PROGRAM_DOMAIN = b"m039-program-v1"
CHECKPOINT_DOMAIN = b"m039-checkpoint-v1"
TRANSCRIPT_DOMAIN = b"m039-transcript-v1"
TOOL_DOMAIN = b"m039-tool-v1"
CONSTRUCTION_EVENT_DOMAIN = b"m039-tool-construction-event-v1"
REGISTRY_DOMAIN = b"m039-registry-v1"


class M039EngineError(RuntimeError):
    pass


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + encode(value)).hexdigest()


def dfa_digest(dfa: DFA) -> str:
    return _digest(BODY_DOMAIN, normalize_dfa(dfa).to_dict())


def _atom_mapping(atom: Atom) -> dict[str, object]:
    return {"atom": atom.to_list()}


def _tool_atoms(tool: LineageTool) -> tuple[Atom, ...]:
    atoms: list[Atom] = []
    for step in tool.program:
        raw = step.get("atom")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise M039EngineError("tool program step does not contain an atom list")
        atoms.append(Atom.from_list(raw))
    return tuple(atoms)


def _registry_digest(registry: Sequence[LineageTool]) -> str:
    return _digest(REGISTRY_DOMAIN, [tool.mapping() for tool in registry])


def _state_mapping(
    body: DFA,
    *,
    portable_state: Mapping[str, object],
    registry: Sequence[LineageTool],
    accepted_cycles: int,
) -> dict[str, object]:
    return {
        "body": normalize_dfa(body).to_dict(),
        "portable_learning_state": dict(portable_state),
        "tool_registry": [tool.mapping() for tool in registry],
        "accepted_cycles": accepted_cycles,
        "rng_algorithm_and_state": None,
    }


def primitive_registry(lineage_id: str, protocol_commitment: str) -> tuple[LineageTool, ...]:
    atoms = all_atoms() + growth_atoms()
    return tuple(
        protocol_primitive_tool(
            lineage_id=lineage_id,
            protocol_commitment=protocol_commitment,
            primitive_name=f"structural-symbol-{index}",
            program=(_atom_mapping(atom),),
            ordinal=index,
        )
        for index, atom in enumerate(atoms)
    )


@dataclass
class EngineCounters:
    oracle_queries: int = 0
    functional_operations: int = 0
    certificate_search_nodes: int = 0
    certificate_pair_tests: int = 0
    certificate_suffix_probes: int = 0
    symbolic_search_nodes: int = 0
    primitive_expansion_operations: int = 0
    candidates_constructed: int = 0
    candidates_evaluated: int = 0
    rejected_candidates: int = 0
    tool_symbols_used: int = 0

    def mapping(self) -> dict[str, int]:
        return {
            "oracle_queries": self.oracle_queries,
            "functional_operations": self.functional_operations,
            "certificate_search_nodes": self.certificate_search_nodes,
            "certificate_pair_tests": self.certificate_pair_tests,
            "certificate_suffix_probes": self.certificate_suffix_probes,
            "symbolic_search_nodes": self.symbolic_search_nodes,
            "primitive_expansion_operations": self.primitive_expansion_operations,
            "candidates_constructed": self.candidates_constructed,
            "candidates_evaluated": self.candidates_evaluated,
            "rejected_candidates": self.rejected_candidates,
            "tool_symbols_used": self.tool_symbols_used,
        }


@dataclass(frozen=True)
class M039Task:
    cycle: int
    cycle_seed: int
    founder: DFA
    target: DFA
    generating_tool_ids: tuple[str, ...]
    generating_program: tuple[Atom, ...]

    def mapping(self) -> dict[str, object]:
        return {
            "cycle": self.cycle,
            "cycle_seed": self.cycle_seed,
            "founder_digest": dfa_digest(self.founder),
            "target_digest": dfa_digest(self.target),
            "founder_states": self.founder.n_states,
            "target_states": self.target.n_states,
            "generating_tool_ids": list(self.generating_tool_ids),
            "generating_program": [atom.to_list() for atom in self.generating_program],
            "observation_depth": OBSERVATION_DEPTH,
            "observation_count": len(OBSERVATION_WORDS),
        }

    def digest(self) -> str:
        return _digest(TASK_DOMAIN, self.mapping())


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    tool_indices: tuple[int, ...]
    tool_ids: tuple[str, ...]
    expanded_program: tuple[Atom, ...]
    body: DFA

    def mapping(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "tool_indices": list(self.tool_indices),
            "tool_ids": list(self.tool_ids),
            "expanded_program": [atom.to_list() for atom in self.expanded_program],
            "body": normalize_dfa(self.body).to_dict(),
        }

    def program_digest(self) -> str:
        return _digest(
            PROGRAM_DOMAIN,
            {
                "tool_ids": list(self.tool_ids),
                "expanded_program": [atom.to_list() for atom in self.expanded_program],
            },
        )


@dataclass(frozen=True)
class CycleExecution:
    task: M039Task
    manifest: CycleManifest
    accepted: Candidate
    constructed_tool: LineageTool | None
    tool_uses: tuple[ToolUse, ...]
    ablation_solved: bool | None
    journal_event_hashes: tuple[str, ...]


@dataclass(frozen=True)
class M039DevelopmentResult:
    manifest: LineageManifest
    replay_inputs: ReplayInputs
    primitive_registry_digest: str
    lineage_journal_head: str
    lineage_journal_records: tuple[bytes, ...]
    cycle_tasks: tuple[M039Task, ...]
    gate2_tool_ids: tuple[str, ...]
    three_cycles_accepted: bool
    later_tool_reuse_supported: bool
    tool_ablation_supported: bool
    seed_to_head_replay_supported: bool
    schema: str = "m039-development-result/1"

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": "consumed-development-result",
            "manifest": self.manifest.mapping(),
            "manifest_digest": self.manifest.digest(),
            "replay_inputs": self.replay_inputs.mapping(),
            "primitive_registry_digest": self.primitive_registry_digest,
            "lineage_journal_head": self.lineage_journal_head,
            "lineage_journal_record_count": len(self.lineage_journal_records),
            "tasks": [task.mapping() for task in self.cycle_tasks],
            "gate2_tool_ids": list(self.gate2_tool_ids),
            "three_cycles_accepted": self.three_cycles_accepted,
            "later_tool_reuse_supported": self.later_tool_reuse_supported,
            "tool_ablation_supported": self.tool_ablation_supported,
            "seed_to_head_replay_supported": self.seed_to_head_replay_supported,
            "no_sealed_block_opened": True,
            "no_canonical_claim": True,
        }


def _charge_certificate(counters: EngineCounters, certificate: StructuralIncapacityCertificate) -> None:
    counters.certificate_search_nodes += certificate.search_nodes_used
    counters.certificate_pair_tests += certificate.pair_tests
    counters.certificate_suffix_probes += certificate.suffix_probes
    counters.functional_operations += (
        certificate.search_nodes_used + certificate.pair_tests + certificate.suffix_probes
    )


def _evidence(target: DFA, counters: EngineCounters) -> dict[Word, bool]:
    result: dict[Word, bool] = {}
    for word in OBSERVATION_WORDS:
        result[word] = target.accepts(word)
        counters.oracle_queries += 1
        counters.functional_operations += 1
    return result


def _certificate(founder: DFA, evidence: Mapping[Word, bool], counters: EngineCounters):
    certificate = proved_structural_incapacity(
        founder,
        evidence,
        maximum_search_nodes=MAXIMUM_SEARCH_NODES,
        maximum_prefix_count=MAXIMUM_PREFIX_COUNT,
    )
    _charge_certificate(counters, certificate)
    verify_structural_incapacity_certificate(founder, evidence, certificate, recompute=False)
    return certificate


def _apply_tools(base: DFA, tools: Sequence[LineageTool]) -> tuple[DFA | None, tuple[Atom, ...]]:
    current: DFA | None = base
    expanded: list[Atom] = []
    for tool in tools:
        for atom in _tool_atoms(tool):
            expanded.append(atom)
            current = apply_atom(current, atom)  # type: ignore[arg-type]
            if current is None:
                return None, tuple(expanded)
    return current, tuple(expanded)


def _reachable_digests(
    founder: DFA,
    registry: Sequence[LineageTool],
    maximum_depth: int,
) -> set[str]:
    blocks = tuple(_tool_atoms(tool) for tool in registry)
    reachable: set[str] = set()
    for depth in range(1, maximum_depth + 1):
        for _, body in walk(founder, blocks, depth):
            reachable.add(dfa_digest(body))
    return reachable


def _cycle_one_task(
    *,
    master_seed: int,
    protocol_commitment: str,
    founder: DFA,
    registry: Sequence[LineageTool],
) -> M039Task:
    cycle_seed = derive_cycle_seed(master_seed, 1, protocol_commitment)
    shorter = _reachable_digests(founder, registry, CYCLE_ONE_SEARCH_DEPTH - 1)
    blocks = tuple(_tool_atoms(tool) for tool in registry)
    programs_seen = 0
    for indices, raw in walk(founder, blocks, CYCLE_ONE_SEARCH_DEPTH):
        programs_seen += 1
        if programs_seen > MAXIMUM_TASK_PROGRAMS:
            break
        target = normalize_dfa(raw)
        if target.n_states <= founder.n_states or dfa_digest(target) in shorter:
            continue
        evidence = {word: target.accepts(word) for word in OBSERVATION_WORDS}
        certificate = proved_structural_incapacity(founder, evidence)
        if not certificate.proves_incapacity():
            continue
        tools = tuple(registry[index] for index in indices)
        expanded = tuple(atom for tool in tools for atom in _tool_atoms(tool))
        return M039Task(1, cycle_seed, founder, target, tuple(tool.tool_id for tool in tools), expanded)
    raise M039EngineError("cycle 1 task generation exhausted its committed program budget")


def _later_task(
    *,
    cycle: int,
    master_seed: int,
    protocol_commitment: str,
    founder: DFA,
    primitive_tools: Sequence[LineageTool],
    lineage_tool: LineageTool,
) -> M039Task:
    cycle_seed = derive_cycle_seed(master_seed, cycle, protocol_commitment)
    primitive_reachable = _reachable_digests(
        founder,
        primitive_tools,
        LATER_CYCLE_SEARCH_DEPTH,
    )
    attempts = 0
    for primitive in primitive_tools:
        for tools in ((lineage_tool, primitive), (primitive, lineage_tool)):
            attempts += 1
            if attempts > MAXIMUM_TASK_ATTEMPTS * len(primitive_tools):
                break
            raw, expanded = _apply_tools(founder, tools)
            if raw is None:
                continue
            target = normalize_dfa(raw)
            target_key = dfa_digest(target)
            if target.n_states <= founder.n_states or target_key in primitive_reachable:
                continue
            evidence = {word: target.accepts(word) for word in OBSERVATION_WORDS}
            certificate = proved_structural_incapacity(founder, evidence)
            if not certificate.proves_incapacity():
                continue
            return M039Task(
                cycle,
                cycle_seed,
                founder,
                target,
                tuple(tool.tool_id for tool in tools),
                expanded,
            )
    raise M039EngineError(f"cycle {cycle} task generation found no tool-dependent target")


def _candidate_id(cycle: int, indices: Sequence[int], tools: Sequence[LineageTool], body: DFA) -> str:
    return _digest(
        CANDIDATE_DOMAIN,
        {
            "cycle": cycle,
            "tool_indices": list(indices),
            "tool_ids": [tool.tool_id for tool in tools],
            "body": normalize_dfa(body).to_dict(),
        },
    )


def _candidate_stream(
    *,
    cycle: int,
    founder: DFA,
    evidence: Mapping[Word, bool],
    registry: Sequence[LineageTool],
    maximum_depth: int,
    counters: EngineCounters,
) -> Iterator[Candidate]:
    ordered_evidence = tuple(sorted(evidence.items()))

    def descend(
        current: DFA,
        selected_indices: tuple[int, ...],
        selected_tools: tuple[LineageTool, ...],
        expanded: tuple[Atom, ...],
        remaining: int,
    ) -> Iterator[Candidate]:
        if remaining == 0:
            counters.candidates_constructed += 1
            normalized = normalize_dfa(current)
            for word, expected in ordered_evidence:
                counters.functional_operations += 1
                if normalized.accepts(word) != expected:
                    return
            yield Candidate(
                candidate_id=_candidate_id(cycle, selected_indices, selected_tools, normalized),
                tool_indices=selected_indices,
                tool_ids=tuple(tool.tool_id for tool in selected_tools),
                expanded_program=expanded,
                body=normalized,
            )
            return

        for index, tool in enumerate(registry):
            counters.symbolic_search_nodes += 1
            if counters.symbolic_search_nodes > MAXIMUM_CANDIDATE_SEARCH_NODES:
                raise M039EngineError("candidate search exceeded its committed node budget")
            current_body: DFA | None = current
            atoms = _tool_atoms(tool)
            for atom in atoms:
                counters.primitive_expansion_operations += 1
                counters.functional_operations += 1
                current_body = apply_atom(current_body, atom)  # type: ignore[arg-type]
                if current_body is None:
                    break
            if current_body is None:
                continue
            if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED:
                counters.tool_symbols_used += 1
            yield from descend(
                current_body,
                selected_indices + (index,),
                selected_tools + (tool,),
                expanded + atoms,
                remaining - 1,
            )

    for depth in range(1, maximum_depth + 1):
        yield from descend(founder, (), (), (), depth)


def _construction_event_id(
    *,
    lineage_id: str,
    cycle: int,
    input_tool_ids: Sequence[str],
    program: Sequence[Atom],
) -> str:
    return _digest(
        CONSTRUCTION_EVENT_DOMAIN,
        {
            "lineage_id": lineage_id,
            "cycle": cycle,
            "input_tool_ids": list(input_tool_ids),
            "program": [atom.to_list() for atom in program],
        },
    )


def _compose_adopted_tool(
    *,
    lineage_id: str,
    protocol_commitment: str,
    cycle: int,
    candidate: Candidate,
    registry: Sequence[LineageTool],
) -> LineageTool:
    input_tools = tuple(registry[index] for index in candidate.tool_indices)
    event_id = _construction_event_id(
        lineage_id=lineage_id,
        cycle=cycle,
        input_tool_ids=tuple(tool.tool_id for tool in input_tools),
        program=candidate.expanded_program,
    )
    source = {
        "lineage_id": lineage_id,
        "protocol_commitment": protocol_commitment,
        "introduced_cycle": cycle,
        "construction_event_id": event_id,
        "input_tool_ids": [tool.tool_id for tool in input_tools],
        "program": [atom.to_list() for atom in candidate.expanded_program],
    }
    replay_digest = _digest(TOOL_DOMAIN, {"replay": source})
    tool_id = _digest(TOOL_DOMAIN, {**source, "replay_digest": replay_digest})
    return LineageTool(
        tool_id=tool_id,
        version=1,
        lineage_id=lineage_id,
        introduced_cycle=cycle,
        program=tuple(_atom_mapping(atom) for atom in candidate.expanded_program),
        input_tool_ids=tuple(tool.tool_id for tool in input_tools),
        replay_digest=replay_digest,
        provenance=ToolProvenance(
            origin=ORIGIN_LINEAGE_CONSTRUCTED,
            construction_kind=KIND_COMPOSITION,
            introduction_phase=PHASE_CYCLE,
            introduced_by_event=event_id,
            protocol_commitment=protocol_commitment,
        ),
    )


def _search_exact_without_journal(
    *,
    cycle: int,
    founder: DFA,
    target: DFA,
    evidence: Mapping[Word, bool],
    registry: Sequence[LineageTool],
    maximum_depth: int,
) -> Candidate | None:
    counters = EngineCounters()
    for candidate in _candidate_stream(
        cycle=cycle,
        founder=founder,
        evidence=evidence,
        registry=registry,
        maximum_depth=maximum_depth,
        counters=counters,
    ):
        counters.candidates_evaluated += 1
        exact, _ = exact_equivalence(candidate.body, target)
        counters.functional_operations += 1
        if exact:
            return candidate
    return None


def _execute_cycle(
    *,
    task: M039Task,
    current_body: DFA,
    portable_state: dict[str, object],
    registry: list[LineageTool],
    primitive_count: int,
    journal: LineageJournal,
    protocol_commitment: str,
    lineage_id: str,
) -> CycleExecution:
    counters = EngineCounters()
    audit = AuditCounters()
    rolling = RollingCommitment(batch_size=1, counters=audit)
    evidence = _evidence(task.target, counters)
    for sequence, (word, label) in enumerate(sorted(evidence.items())):
        rolling.record(
            {
                "operation": "oracle_query",
                "cycle": task.cycle,
                "sequence": sequence,
                "word": list(word),
                "label": label,
            }
        )
    rolling.flush()
    certificate = _certificate(current_body, evidence, counters)
    if not certificate.proves_incapacity():
        raise M039EngineError(f"cycle {task.cycle} lacks a structural incapacity proof")

    start_mapping = _state_mapping(
        current_body,
        portable_state=portable_state,
        registry=registry,
        accepted_cycles=task.cycle - 1,
    )
    start_digest = state_digest(start_mapping)
    certificate_digest = _digest(b"m039-certificate-v1", certificate.to_mapping())
    checkpoint = {
        "cycle": task.cycle,
        "cycle_seed": task.cycle_seed,
        "body_digest": dfa_digest(current_body),
        "registry_digest": _registry_digest(registry),
        "evidence_digest": evidence_digest(evidence),
        "certificate": certificate.to_mapping(),
        "compact_trace_head": rolling.head,
        "functional_counters": counters.mapping(),
    }
    checkpoint_digest = _digest(CHECKPOINT_DOMAIN, checkpoint)
    journal.open_cycle(
        task.cycle,
        result_state_digest=start_digest,
        operation_parameters=checkpoint,
        immutable_input_digests=(bytes.fromhex(task.digest()), bytes.fromhex(checkpoint_digest)),
        costs=audit.as_mapping(),
    )
    journal.append(
        "StructuralIncapacityCertified",
        result_state_digest=start_digest,
        operation_parameters={"certificate": certificate.to_mapping()},
        immutable_input_digests=(bytes.fromhex(certificate_digest), evidence_digest(evidence)),
    )

    transcript: list[Mapping[str, object]] = [
        {"decision": "cycle_started", "cycle": task.cycle, "task_digest": task.digest()},
        {
            "decision": "structural_incapacity",
            "proved": True,
            "certificate_digest": certificate_digest,
        },
    ]
    maximum_depth = CYCLE_ONE_SEARCH_DEPTH if task.cycle == 1 else LATER_CYCLE_SEARCH_DEPTH
    accepted: Candidate | None = None
    event_hashes: list[str] = []
    for candidate in _candidate_stream(
        cycle=task.cycle,
        founder=current_body,
        evidence=evidence,
        registry=registry,
        maximum_depth=maximum_depth,
        counters=counters,
    ):
        proposed = journal.append(
            "CandidateProposed",
            result_state_digest=journal.state_digest,
            operation_parameters=candidate.mapping(),
        )
        event_hashes.append(proposed.event_hash.hex())
        transcript.append(
            {
                "decision": "candidate_proposed",
                "candidate_id": candidate.candidate_id,
                "tool_ids": list(candidate.tool_ids),
            }
        )
        counters.candidates_evaluated += 1
        counters.functional_operations += 1
        exact, separating_word = exact_equivalence(candidate.body, task.target)
        evaluated = journal.append(
            "CandidateEvaluated",
            result_state_digest=journal.state_digest,
            operation_parameters={
                "candidate_id": candidate.candidate_id,
                "exact": exact,
                "separating_word": list(separating_word) if separating_word is not None else None,
            },
        )
        event_hashes.append(evaluated.event_hash.hex())
        transcript.append(
            {
                "decision": "candidate_evaluated",
                "candidate_id": candidate.candidate_id,
                "exact": exact,
                "separating_word": list(separating_word) if separating_word is not None else None,
            }
        )
        if exact:
            accepted = candidate
            break
        counters.rejected_candidates += 1
        rejected = journal.append(
            "CandidateRejected",
            result_state_digest=journal.state_digest,
            operation_parameters={
                "candidate_id": candidate.candidate_id,
                "reason": "not_exactly_equivalent",
            },
        )
        event_hashes.append(rejected.event_hash.hex())

    if accepted is None:
        raise M039EngineError(f"cycle {task.cycle} failed to find an exact candidate")

    accepted_body = normalize_dfa(accepted.body)
    portable_state["accepted_candidate_ids"] = list(
        tuple(portable_state.get("accepted_candidate_ids", ())) + (accepted.candidate_id,)
    )
    adopted_mapping = _state_mapping(
        accepted_body,
        portable_state=portable_state,
        registry=registry,
        accepted_cycles=task.cycle,
    )
    adopted_digest = state_digest(adopted_mapping)
    adopted_event = journal.append(
        "MutationAdopted",
        result_state_digest=adopted_digest,
        operation_parameters={
            "candidate_id": accepted.candidate_id,
            "tool_ids": list(accepted.tool_ids),
            "expanded_program": [atom.to_list() for atom in accepted.expanded_program],
            "strict_improvement": {
                "starting_states": current_body.n_states,
                "ending_states": accepted_body.n_states,
                "target_states": task.target.n_states,
            },
        },
    )
    event_hashes.append(adopted_event.event_hash.hex())
    transcript.append(
        {
            "decision": "candidate_adopted",
            "candidate_id": accepted.candidate_id,
            "tool_ids": list(accepted.tool_ids),
        }
    )

    constructed_tool: LineageTool | None = None
    if task.cycle == 1:
        constructed_tool = _compose_adopted_tool(
            lineage_id=lineage_id,
            protocol_commitment=protocol_commitment,
            cycle=1,
            candidate=accepted,
            registry=registry,
        )
        registry.append(constructed_tool)
        portable_state["constructed_tool_ids"] = [constructed_tool.tool_id]
        constructed_mapping = _state_mapping(
            accepted_body,
            portable_state=portable_state,
            registry=registry,
            accepted_cycles=task.cycle,
        )
        adopted_digest = state_digest(constructed_mapping)
        construction_event = journal.append(
            "ToolConstructed",
            result_state_digest=adopted_digest,
            operation_parameters={
                "construction_event_id": constructed_tool.provenance.introduced_by_event,
                "tool": constructed_tool.mapping(),
            },
        )
        event_hashes.append(construction_event.event_hash.hex())
        transcript.append(
            {
                "decision": "tool_constructed",
                "tool_id": constructed_tool.tool_id,
                "construction_event_id": constructed_tool.provenance.introduced_by_event,
            }
        )

    uses: list[ToolUse] = []
    lineage_tool_ids = {
        tool.tool_id
        for tool in registry
        if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED
        and tool.introduced_cycle < task.cycle
    }
    for block_index, tool_id in enumerate(accepted.tool_ids):
        if tool_id not in lineage_tool_ids:
            continue
        use = ToolUse(tool_id, task.cycle, accepted.candidate_id, True, block_index)
        uses.append(use)
        portable_state["tool_use_ids"] = list(
            tuple(portable_state.get("tool_use_ids", ())) + (tool_id,)
        )
        reused_mapping = _state_mapping(
            accepted_body,
            portable_state=portable_state,
            registry=registry,
            accepted_cycles=task.cycle,
        )
        adopted_digest = state_digest(reused_mapping)
        reuse_event = journal.append(
            "ToolReused",
            result_state_digest=adopted_digest,
            operation_parameters=use.mapping(),
        )
        event_hashes.append(reuse_event.event_hash.hex())
        transcript.append({"decision": "tool_reused", **use.mapping()})

    bad_raw = apply_atoms(accepted_body, (flip("initial"),))
    if bad_raw is None:
        raise M039EngineError("forced rollback probe failed to produce a provisional body")
    bad_body = normalize_dfa(bad_raw)
    bad_mapping = _state_mapping(
        bad_body,
        portable_state=portable_state,
        registry=registry,
        accepted_cycles=task.cycle,
    )
    bad_digest = state_digest(bad_mapping)
    journal.append(
        "MutationProvisionallyAdopted",
        result_state_digest=bad_digest,
        operation_parameters={"forced_rollback_probe": True},
    )
    bad_exact, bad_witness = exact_equivalence(bad_body, task.target)
    counters.functional_operations += 1
    counters.candidates_evaluated += 1
    if bad_exact:
        raise M039EngineError("forced rollback probe unexpectedly remained equivalent")
    journal.append(
        "CandidateEvaluated",
        result_state_digest=bad_digest,
        operation_parameters={
            "forced_rollback_probe": True,
            "exact": False,
            "separating_word": list(bad_witness) if bad_witness is not None else None,
        },
    )
    journal.append(
        "CandidateRejected",
        result_state_digest=bad_digest,
        operation_parameters={
            "forced_rollback_probe": True,
            "reason": "not_exactly_equivalent",
        },
    )
    journal.rollback(target_state_digest=adopted_digest, reason="forced provisional failure")
    rollback_exact = journal.state_digest == adopted_digest

    ablation_solved: bool | None = None
    if task.cycle > 1:
        primitive_registry_only = tuple(registry[:primitive_count])
        ablation = _search_exact_without_journal(
            cycle=task.cycle,
            founder=current_body,
            target=task.target,
            evidence=evidence,
            registry=primitive_registry_only,
            maximum_depth=LATER_CYCLE_SEARCH_DEPTH,
        )
        ablation_solved = ablation is not None

    journal.complete_cycle(
        result_state_digest=adopted_digest,
        operation_parameters={
            "cycle": task.cycle,
            "accepted": True,
            "rollback_restored_exactly": rollback_exact,
            "ablation_solved": ablation_solved,
        },
        costs={**counters.mapping(), **audit.as_mapping()},
    )
    transcript.append(
        {
            "decision": "cycle_completed",
            "cycle": task.cycle,
            "ending_body_digest": dfa_digest(accepted_body),
            "rollback_restored_exactly": rollback_exact,
            "ablation_solved": ablation_solved,
        }
    )
    transcript_digest = _digest(TRANSCRIPT_DOMAIN, list(transcript))
    cycle_manifest = CycleManifest(
        cycle=task.cycle,
        cycle_seed=task.cycle_seed,
        starting_body_digest=dfa_digest(current_body),
        target_digest=dfa_digest(task.target),
        ending_body_digest=dfa_digest(accepted_body),
        evidence_digest=evidence_digest(evidence).hex(),
        certificate_digest=certificate_digest,
        compact_trace_head=rolling.head.hex(),
        checkpoint_digest=checkpoint_digest,
        journal_head=journal.head.hex(),
        decision_transcript_digest=transcript_digest,
        accepted_candidate_id=accepted.candidate_id,
        accepted_program_digest=accepted.program_digest(),
        used_tool_ids=tuple(use.tool_id for use in uses),
        constructed_tool_ids=(constructed_tool.tool_id,) if constructed_tool else (),
        rollback_restored_exactly=rollback_exact,
        functional_counters=counters.mapping(),
        audit_counters=audit.as_mapping(),
    )
    return CycleExecution(
        task=task,
        manifest=cycle_manifest,
        accepted=accepted,
        constructed_tool=constructed_tool,
        tool_uses=tuple(uses),
        ablation_solved=ablation_solved,
        journal_event_hashes=tuple(event_hashes),
    )


def _execute(master_seed: int, protocol_commitment: str) -> M039DevelopmentResult:
    lineage_id = derive_lineage_id(master_seed, protocol_commitment)
    registry = list(primitive_registry(lineage_id, protocol_commitment))
    primitive_count = len(registry)
    primitive_digest = _registry_digest(registry)
    first_seed = derive_cycle_seed(master_seed, 1, protocol_commitment)
    founder = normalize_dfa(random_minimal_dfa(first_seed, FOUNDER_STATES, FOUNDER_STATES))
    portable_state: dict[str, object] = {
        "accepted_candidate_ids": [],
        "constructed_tool_ids": [],
        "tool_use_ids": [],
    }
    initial_mapping = _state_mapping(
        founder,
        portable_state=portable_state,
        registry=registry,
        accepted_cycles=0,
    )
    initial_digest = state_digest(initial_mapping)
    journal = LineageJournal(
        protocol_commitment=protocol_commitment,
        lineage_id=lineage_id,
        initial_state_digest=initial_digest,
    )
    journal.start(
        immutable_input_digests=(
            bytes.fromhex(primitive_digest),
            hashlib.sha256(encode({"master_seed": master_seed})).digest(),
        )
    )

    current = founder
    cycle_executions: list[CycleExecution] = []
    all_uses: list[ToolUse] = []
    lineage_tool: LineageTool | None = None
    for cycle in (1, 2, 3):
        if cycle == 1:
            task = _cycle_one_task(
                master_seed=master_seed,
                protocol_commitment=protocol_commitment,
                founder=current,
                registry=tuple(registry),
            )
        else:
            if lineage_tool is None:
                raise M039EngineError("later cycle started without the cycle-1 lineage tool")
            task = _later_task(
                cycle=cycle,
                master_seed=master_seed,
                protocol_commitment=protocol_commitment,
                founder=current,
                primitive_tools=tuple(registry[:primitive_count]),
                lineage_tool=lineage_tool,
            )
        execution = _execute_cycle(
            task=task,
            current_body=current,
            portable_state=portable_state,
            registry=registry,
            primitive_count=primitive_count,
            journal=journal,
            protocol_commitment=protocol_commitment,
            lineage_id=lineage_id,
        )
        cycle_executions.append(execution)
        all_uses.extend(execution.tool_uses)
        if execution.constructed_tool is not None:
            lineage_tool = execution.constructed_tool
        current = execution.accepted.body

    final_mapping = _state_mapping(
        current,
        portable_state=portable_state,
        registry=registry,
        accepted_cycles=3,
    )
    final_digest_bytes = state_digest(final_mapping)
    ablation_required = tuple(
        sorted(
            {
                use.tool_id
                for execution in cycle_executions
                if execution.task.cycle > 1 and execution.ablation_solved is False
                for use in execution.tool_uses
            }
        )
    )
    journal.complete_lineage(
        result_state_digest=final_digest_bytes,
        operation_parameters={
            "accepted_cycles": 3,
            "final_body_digest": dfa_digest(current),
            "ablation_required_tool_ids": list(ablation_required),
        },
    )
    journal.verify_internal_consistency()
    journal.verify_against(
        expected_initial_state_digest=initial_digest,
        expected_head=journal.head,
        expected_final_state_digest=final_digest_bytes,
    )

    manifest = LineageManifest(
        master_seed=master_seed,
        protocol_commitment=protocol_commitment,
        lineage_id=lineage_id,
        initial_body_digest=dfa_digest(founder),
        cycles=tuple(execution.manifest for execution in cycle_executions),
        tool_registry=tuple(registry),
        tool_uses=tuple(all_uses),
        ablation_required_tool_ids=ablation_required,
        final_body_digest=dfa_digest(current),
    )
    replay_inputs = ReplayInputs(
        master_seed=master_seed,
        protocol_commitment=protocol_commitment,
        primitive_registry_digest=primitive_digest,
        expected_manifest_digest=manifest.digest(),
        expected_final_body_digest=manifest.final_body_digest,
        expected_cycle_journal_heads=tuple(cycle.journal_head for cycle in manifest.cycles),
    )
    constructed = tuple(
        tool for tool in registry if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED
    )
    valid_construction_ids = tuple(
        tool.provenance.introduced_by_event
        for tool in constructed
        if tool.provenance.introduced_by_event is not None
    )
    registry_before = tuple(tool.tool_id for tool in registry[:primitive_count])
    gate2_tools = tuple(
        tool.tool_id
        for tool in constructed
        if gate2_eligible(
            tool,
            valid_construction_event_hashes=valid_construction_ids,
            registry_before_construction=registry_before,
            uses=all_uses,
            ablation_required_tool_ids=ablation_required,
        )
    )
    three_cycles = all(
        exact_equivalence(execution.accepted.body, execution.task.target)[0]
        and execution.manifest.rollback_restored_exactly
        for execution in cycle_executions
    )
    later_reuse = all(execution.tool_uses for execution in cycle_executions[1:])
    ablation_supported = all(execution.ablation_solved is False for execution in cycle_executions[1:])

    result = M039DevelopmentResult(
        manifest=manifest,
        replay_inputs=replay_inputs,
        primitive_registry_digest=primitive_digest,
        lineage_journal_head=journal.head.hex(),
        lineage_journal_records=journal.records,
        cycle_tasks=tuple(execution.task for execution in cycle_executions),
        gate2_tool_ids=gate2_tools,
        three_cycles_accepted=three_cycles,
        later_tool_reuse_supported=later_reuse,
        tool_ablation_supported=ablation_supported,
        seed_to_head_replay_supported=False,
    )
    return result


def replay_m039(inputs: ReplayInputs) -> M039DevelopmentResult:
    replayed = _execute(inputs.master_seed, inputs.protocol_commitment)
    verify_replayed_manifest(replayed.manifest, inputs)
    if replayed.primitive_registry_digest != inputs.primitive_registry_digest:
        raise M039EngineError("primitive registry digest diverged during replay")
    return replayed


def run_m039_development(
    master_seed: int = DEVELOPMENT_SEED,
    *,
    protocol_commitment: str = DEVELOPMENT_COMMITMENT,
    require_replay: bool = True,
) -> M039DevelopmentResult:
    first = _execute(master_seed, protocol_commitment)
    if not require_replay:
        return first
    replayed = replay_m039(first.replay_inputs)
    if replayed.lineage_journal_records != first.lineage_journal_records:
        raise M039EngineError("seed-to-head replay produced different causal event bytes")
    return M039DevelopmentResult(
        manifest=first.manifest,
        replay_inputs=first.replay_inputs,
        primitive_registry_digest=first.primitive_registry_digest,
        lineage_journal_head=first.lineage_journal_head,
        lineage_journal_records=first.lineage_journal_records,
        cycle_tasks=first.cycle_tasks,
        gate2_tool_ids=first.gate2_tool_ids,
        three_cycles_accepted=first.three_cycles_accepted,
        later_tool_reuse_supported=first.later_tool_reuse_supported,
        tool_ablation_supported=first.tool_ablation_supported,
        seed_to_head_replay_supported=True,
    )
