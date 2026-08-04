"""M038 two-speed lineage in the bounded DFA domain.

This module integrates the fast path, the exact escalation certificate, the
checkpoint, the slow causal journal, adoption, a forced failing provisional
adoption, exact rollback to F1, and the B/C proof-cost comparison.

The task generator belongs to the laboratory. The organism-facing proposal
path receives only a body and oracle evidence; the hidden target is used only
by the independent exact evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from itertools import chain
from typing import Iterable, Iterator, Mapping, Sequence

from .m012b_dfa import DFA, exact_equivalence, random_minimal_dfa
from .m017_lab import BehavioralOracle
from .m038_certificate import (
    MAXIMUM_PREFIX_COUNT,
    MAXIMUM_SEARCH_NODES,
    StructuralIncapacityCertificate,
    evidence_digest,
    proved_structural_incapacity,
    verify_structural_incapacity_certificate,
)
from .m038_journal import (
    DOMAIN_CAUSAL_EVENT,
    GENESIS_HASH,
    SCHEMA_VERSION,
    AuditCounters,
    CausalJournal,
    EscalationCheckpoint,
    encode,
    functional_digest,
    project_archive,
    verify_projection,
)
from .structural import (
    Atom,
    all_atoms,
    apply_atom,
    apply_atoms,
    atoms_to_json,
    enumerate_words,
    flip,
    growth_atoms,
    normalize_dfa,
)

Word = tuple[int, ...]

OBSERVATION_DEPTH = 6
OBSERVATION_WORDS: tuple[Word, ...] = enumerate_words(OBSERVATION_DEPTH)
MAXIMUM_CANDIDATE_SEARCH_NODES = 100_000
MAXIMUM_TASK_GENERATION_PROGRAMS = 50_000
MAXIMUM_TASK_GENERATION_ATTEMPTS = 16
SEARCH_DEPTH = 3
_FAST_EVENT_SCHEMA = "m038-full-fast-path-event/1"
_TRANSCRIPT_DOMAIN = b"m038-decision-transcript-v1"
_CERTIFICATE_DOMAIN = b"m038-certificate-artifact-v1"


@dataclass(frozen=True)
class M038Task:
    seed: int
    founder: DFA
    target: DFA
    generating_program: tuple[Atom, ...]
    observation_words: tuple[Word, ...] = OBSERVATION_WORDS

    def public_mapping(self) -> dict[str, object]:
        """Metadata safe to report without exposing the target to the proposer."""

        return {
            "seed": self.seed,
            "founder": self.founder.to_dict(),
            "founder_states": self.founder.n_states,
            "target_minimal_states": self.target.n_states,
            "observation_depth": OBSERVATION_DEPTH,
            "observation_words": len(self.observation_words),
            "generating_program_length": len(self.generating_program),
        }


@dataclass
class FunctionalCounters:
    oracle_queries: int = 0
    functional_deterministic_operations: int = 0
    certificate_search_nodes: int = 0
    certificate_pair_tests: int = 0
    certificate_suffix_probes: int = 0
    search_nodes: int = 0
    candidates_constructed: int = 0
    candidates_evaluated: int = 0
    candidate_construction_operations: int = 0
    candidate_construction_nodes: int = 0
    candidate_construction_tool_calls: int = 0
    candidate_construction_bytes: int = 0
    tool_calls: int = 0
    rng_draws: int = 0
    escalations: int = 0
    false_escalations: int = 0
    missed_escalations: int = 0

    def to_mapping(self) -> dict[str, int]:
        return {
            "oracle_queries": self.oracle_queries,
            "functional_deterministic_operations": self.functional_deterministic_operations,
            "certificate_search_nodes": self.certificate_search_nodes,
            "certificate_pair_tests": self.certificate_pair_tests,
            "certificate_suffix_probes": self.certificate_suffix_probes,
            "search_nodes": self.search_nodes,
            "candidates_constructed": self.candidates_constructed,
            "candidates_evaluated": self.candidates_evaluated,
            "candidate_construction_operations": self.candidate_construction_operations,
            "candidate_construction_nodes": self.candidate_construction_nodes,
            "candidate_construction_tool_calls": self.candidate_construction_tool_calls,
            "candidate_construction_bytes": self.candidate_construction_bytes,
            "tool_calls": self.tool_calls,
            "rng_draws": self.rng_draws,
            "escalations": self.escalations,
            "false_escalations": self.false_escalations,
            "missed_escalations": self.missed_escalations,
        }


@dataclass(frozen=True)
class ProposedCandidate:
    program_indices: tuple[int, ...]
    program: tuple[Atom, ...]
    body: DFA
    candidate_id: str

    def mapping(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "program_indices": list(self.program_indices),
            "program": atoms_to_json(self.program),
            "body": normalize_dfa(self.body).to_dict(),
        }


@dataclass
class FullFastPathRecorder:
    """Arm C's extra evidence: a full immutable record for every fast operation.

    Arm C still produces the same compact rolling commitment as arm B. These
    records are a strict instrumentation superset and never feed a decision.
    """

    counters: AuditCounters
    _records: list[bytes] = field(default_factory=list)
    _head: bytes = GENESIS_HASH

    @property
    def records(self) -> tuple[bytes, ...]:
        return tuple(self._records)

    @property
    def head(self) -> bytes:
        return self._head

    def record(
        self,
        *,
        sequence: int,
        operation_parameters: Mapping[str, object],
        functional_state: Mapping[str, object],
    ) -> None:
        state_digest = functional_digest(functional_state)
        self.counters.body_serializations += 1
        draft = {
            "sequence": sequence,
            "schema_version": _FAST_EVENT_SCHEMA,
            "previous_event_hash": self._head,
            "previous_state_digest": state_digest,
            "operation_parameters": dict(operation_parameters),
            "result_state_digest": state_digest,
        }
        hashed_payload = encode(draft)
        self.counters.hashed_event_payload_serializations += 1
        event_hash = hashlib.sha256(DOMAIN_CAUSAL_EVENT + hashed_payload).digest()
        self.counters.hash_operations += 1
        record = encode({**draft, "event_hash": event_hash})
        self.counters.persisted_event_serializations += 1
        self.counters.journal_bytes_persisted += len(record)
        self._records.append(record)
        self._head = event_hash
        self.counters.observe_persistent_artifacts(len(self._records))

    def verify(self, *, expected_head: bytes) -> None:
        previous = GENESIS_HASH
        for position, raw in enumerate(self._records):
            fields = _mapping(encode_decode(raw))
            if fields["sequence"] != position:
                raise ValueError("full fast-path sequence is not canonical")
            if fields["schema_version"] != _FAST_EVENT_SCHEMA:
                raise ValueError("unknown full fast-path schema")
            if fields["previous_event_hash"] != previous:
                raise ValueError("full fast-path chain is broken")
            event_hash = fields["event_hash"]
            draft = dict(fields)
            del draft["event_hash"]
            self.counters.hashed_event_payload_serializations += 1
            self.counters.hash_operations += 1
            if hashlib.sha256(DOMAIN_CAUSAL_EVENT + encode(draft)).digest() != event_hash:
                raise ValueError("full fast-path event was altered")
            if fields["previous_state_digest"] != fields["result_state_digest"]:
                raise ValueError("an observation changed the functional state")
            previous = event_hash
        if previous != expected_head:
            raise ValueError("full fast-path head does not match its external anchor")


def _json_safe(value: object) -> object:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


@dataclass(frozen=True)
class ArmResult:
    arm: str
    task: Mapping[str, object]
    certificate: Mapping[str, object]
    solved: bool
    control_impossibility_proved: bool
    infrastructure_cycle_valid: bool
    functional_metamorphosis_supported: bool
    final_body: DFA
    initial_state_digest: bytes
    final_state_digest: bytes
    rolling_head: bytes
    checkpoint_digest: bytes | None
    journal_head: bytes | None
    full_fast_path_head: bytes | None
    decision_transcript: tuple[Mapping[str, object], ...]
    decision_transcript_digest: str
    functional_counters: Mapping[str, int]
    audit_counters: Mapping[str, int]
    journal_records: tuple[bytes, ...] = ()
    full_fast_path_records: tuple[bytes, ...] = ()

    def summary(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "task": dict(self.task),
            "certificate": _json_safe(dict(self.certificate)),
            "solved": self.solved,
            "control_impossibility_proved": self.control_impossibility_proved,
            "infrastructure_cycle_valid": self.infrastructure_cycle_valid,
            "functional_metamorphosis_supported": self.functional_metamorphosis_supported,
            "initial_state_digest": self.initial_state_digest.hex(),
            "final_state_digest": self.final_state_digest.hex(),
            "rolling_head": self.rolling_head.hex(),
            "checkpoint_digest": self.checkpoint_digest.hex() if self.checkpoint_digest else None,
            "journal_head": self.journal_head.hex() if self.journal_head else None,
            "full_fast_path_head": (
                self.full_fast_path_head.hex() if self.full_fast_path_head else None
            ),
            "decision_transcript_digest": self.decision_transcript_digest,
            "functional_counters": dict(self.functional_counters),
            "audit_counters": dict(self.audit_counters),
            "journal_record_count": len(self.journal_records),
            "full_fast_path_record_count": len(self.full_fast_path_records),
            "final_body": self.final_body.to_dict(),
        }


@dataclass(frozen=True)
class M038Comparison:
    task: M038Task
    arm_a: ArmResult
    arm_b: ArmResult
    arm_c: ArmResult
    decision_equivalent: bool
    compact_trace_equal: bool
    evidence_strict_subset: bool
    efficiency_claim_supported: bool
    combined_expected_claim_supported: bool

    def summary(self) -> dict[str, object]:
        return {
            "task": self.task.public_mapping(),
            "arm_a": self.arm_a.summary(),
            "arm_b": self.arm_b.summary(),
            "arm_c": self.arm_c.summary(),
            "decision_equivalent": self.decision_equivalent,
            "compact_trace_equal": self.compact_trace_equal,
            "evidence_strict_subset": self.evidence_strict_subset,
            "efficiency_claim_supported": self.efficiency_claim_supported,
            "combined_expected_claim_supported": self.combined_expected_claim_supported,
        }


def encode_decode(raw: bytes) -> object:
    from .m038_journal import decode

    return decode(raw)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("canonical record is not a mapping")
    return value


def _functional_state(
    body: DFA,
    *,
    portable_learning_state: Mapping[str, object],
    tool_registry: Sequence[object],
    rng_algorithm_and_state: object,
) -> dict[str, object]:
    return {
        "body": body.to_dict(),
        "portable_learning_state": dict(portable_learning_state),
        "tool_registry": list(tool_registry),
        "rng_algorithm_and_state": rng_algorithm_and_state,
    }


def _program_candidates() -> Iterable[tuple[Atom, ...]]:
    primitives = all_atoms()
    growth = growth_atoms()
    return chain(
        ((grow_atom, atom) for grow_atom in growth for atom in primitives),
        (
            (grow_atom, first, second)
            for grow_atom in growth
            for first in primitives
            for second in primitives
        ),
        (
            (first, grow_atom, second)
            for first in primitives
            for grow_atom in growth
            for second in primitives
        ),
    )


def make_m038_task(seed: int) -> M038Task:
    """Generate a reachable target that is provably larger than the founder."""

    for attempt in range(MAXIMUM_TASK_GENERATION_ATTEMPTS):
        founder = normalize_dfa(random_minimal_dfa(seed + attempt * 7919, 4, 4))
        programs_seen = 0
        for program in _program_candidates():
            programs_seen += 1
            if programs_seen > MAXIMUM_TASK_GENERATION_PROGRAMS:
                break
            raw = apply_atoms(founder, program)
            if raw is None:
                continue
            target = normalize_dfa(raw)
            if target.n_states <= founder.n_states:
                continue
            evidence = {word: target.accepts(word) for word in OBSERVATION_WORDS}
            certificate = proved_structural_incapacity(founder, evidence)
            if certificate.proves_incapacity():
                return M038Task(seed, founder, target, tuple(program))
    raise RuntimeError("unable to derive an M038 task inside the committed generator budget")


def _tool_registry() -> tuple[Mapping[str, object], ...]:
    blocks = tuple((atom,) for atom in all_atoms() + growth_atoms())
    return tuple(
        {
            "tool_id": f"structural-symbol-{index}",
            "origin": "protocol_supplied",
            "construction_kind": "primitive",
            "introduction_phase": "birth",
            "program": atoms_to_json(block),
            "eligible_for_gate2": False,
        }
        for index, block in enumerate(blocks)
    )


def _collect_evidence(
    task: M038Task,
    *,
    functional_state: Mapping[str, object],
    rolling,
    full_recorder: FullFastPathRecorder | None,
    counters: FunctionalCounters,
) -> dict[Word, bool]:
    oracle = BehavioralOracle(task.target)
    evidence: dict[Word, bool] = {}
    for sequence, word in enumerate(task.observation_words):
        label = oracle.query(word)
        evidence[word] = label
        counters.oracle_queries += 1
        counters.functional_deterministic_operations += 1
        compact = {
            "operation": "oracle_query",
            "sequence": sequence,
            "word": list(word),
            "label": label,
            "cost": 1,
        }
        rolling.record(compact)
        if full_recorder is not None:
            full_recorder.record(
                sequence=sequence,
                operation_parameters=compact,
                functional_state=functional_state,
            )
    rolling.flush()
    return evidence


def _candidate_id(program_indices: Sequence[int], body: DFA) -> str:
    payload = {
        "program_indices": list(program_indices),
        "body": normalize_dfa(body).to_dict(),
    }
    return hashlib.sha256(b"m038-candidate-v1" + encode(payload)).hexdigest()


def _candidate_stream(
    founder: DFA,
    evidence: Mapping[Word, bool],
    counters: FunctionalCounters,
) -> Iterator[ProposedCandidate]:
    blocks = tuple((atom,) for atom in all_atoms() + growth_atoms())
    ordered_evidence = tuple(sorted(evidence.items()))

    def descend(
        current: DFA,
        chosen: tuple[int, ...],
        program: tuple[Atom, ...],
        remaining: int,
    ) -> Iterator[ProposedCandidate]:
        if remaining == 0:
            counters.candidates_constructed += 1
            counters.candidate_construction_bytes += len(
                encode(
                    {
                        "program_indices": list(chosen),
                        "program": atoms_to_json(program),
                        "body": normalize_dfa(current).to_dict(),
                    }
                )
            )
            for word, expected in ordered_evidence:
                counters.functional_deterministic_operations += 1
                if current.accepts(word) != expected:
                    return
            yield ProposedCandidate(
                chosen,
                program,
                current,
                _candidate_id(chosen, current),
            )
            return

        for index, block in enumerate(blocks):
            counters.search_nodes += 1
            counters.candidate_construction_nodes += 1
            counters.candidate_construction_tool_calls += 1
            counters.tool_calls += 1
            if counters.search_nodes > MAXIMUM_CANDIDATE_SEARCH_NODES:
                raise RuntimeError("candidate search exceeded the committed node budget")
            nxt: DFA | None = current
            for atom in block:
                counters.candidate_construction_operations += 1
                counters.functional_deterministic_operations += 1
                nxt = apply_atom(nxt, atom)  # type: ignore[arg-type]
                if nxt is None:
                    break
            if nxt is not None:
                yield from descend(
                    nxt,
                    chosen + (index,),
                    program + tuple(block),
                    remaining - 1,
                )

    for depth in range(1, SEARCH_DEPTH + 1):
        yield from descend(founder, (), (), depth)


def _evaluate_candidate(candidate: DFA, target: DFA, counters: FunctionalCounters):
    counters.candidates_evaluated += 1
    counters.functional_deterministic_operations += 1
    return exact_equivalence(normalize_dfa(candidate), target)


def _certificate_artifact_digest(certificate: StructuralIncapacityCertificate) -> bytes:
    return hashlib.sha256(_CERTIFICATE_DOMAIN + encode(certificate.to_mapping())).digest()


def _transcript_digest(transcript: Sequence[Mapping[str, object]]) -> str:
    return hashlib.sha256(_TRANSCRIPT_DOMAIN + encode(list(transcript))).hexdigest()


def _charge_certificate(
    counters: FunctionalCounters,
    certificate: StructuralIncapacityCertificate,
) -> None:
    counters.certificate_search_nodes += certificate.search_nodes_used
    counters.certificate_pair_tests += certificate.pair_tests
    counters.certificate_suffix_probes += certificate.suffix_probes
    counters.functional_deterministic_operations += (
        certificate.search_nodes_used
        + certificate.pair_tests
        + certificate.suffix_probes
    )


def _run_arm(
    task: M038Task,
    arm: str,
    *,
    protocol_commitment: str,
) -> ArmResult:
    if arm not in {"A", "B", "C"}:
        raise ValueError("arm must be A, B or C")

    from .m038_journal import RollingCommitment

    functional_counters = FunctionalCounters()
    audit_counters = AuditCounters()
    rolling = RollingCommitment(batch_size=1, counters=audit_counters)
    full_recorder = FullFastPathRecorder(audit_counters) if arm == "C" else None
    portable_learning_state: dict[str, object] = {
        "memory": [],
        "uncertainty": [],
        "exploration_frontier": [],
    }
    registry = _tool_registry()
    rng_state = None
    f0_mapping = _functional_state(
        task.founder,
        portable_learning_state=portable_learning_state,
        tool_registry=registry,
        rng_algorithm_and_state=rng_state,
    )
    f0_digest = functional_digest(f0_mapping)
    evidence = _collect_evidence(
        task,
        functional_state=f0_mapping,
        rolling=rolling,
        full_recorder=full_recorder,
        counters=functional_counters,
    )
    certificate = proved_structural_incapacity(
        task.founder,
        evidence,
        maximum_search_nodes=MAXIMUM_SEARCH_NODES,
        maximum_prefix_count=MAXIMUM_PREFIX_COUNT,
    )
    _charge_certificate(functional_counters, certificate)
    verify_structural_incapacity_certificate(
        task.founder,
        evidence,
        certificate,
        recompute=False,
    )
    control_impossible = task.target.n_states > task.founder.n_states
    transcript: list[Mapping[str, object]] = [
        {
            "decision": "observations_admitted",
            "evidence_digest": evidence_digest(evidence),
            "observation_count": len(evidence),
        },
        {
            "decision": "structural_incapacity",
            "certificate": certificate.to_mapping(),
            "proved": certificate.proves_incapacity(),
        },
    ]

    if arm == "A":
        transcript.append({"decision": "escalation", "taken": False, "reason": "control_arm"})
        solved = exact_equivalence(task.founder, task.target)[0]
        return ArmResult(
            arm=arm,
            task=task.public_mapping(),
            certificate=certificate.to_mapping(),
            solved=solved,
            control_impossibility_proved=control_impossible,
            infrastructure_cycle_valid=False,
            functional_metamorphosis_supported=False,
            final_body=task.founder,
            initial_state_digest=f0_digest,
            final_state_digest=f0_digest,
            rolling_head=rolling.head,
            checkpoint_digest=None,
            journal_head=None,
            full_fast_path_head=None,
            decision_transcript=tuple(transcript),
            decision_transcript_digest=_transcript_digest(transcript),
            functional_counters=functional_counters.to_mapping(),
            audit_counters=audit_counters.as_mapping(),
        )

    target_requires_growth = task.target.n_states > task.founder.n_states
    if not certificate.proves_incapacity():
        functional_counters.missed_escalations += int(target_requires_growth)
        transcript.append(
            {
                "decision": "escalation",
                "taken": False,
                "reason": certificate.certificate_status,
            }
        )
        return ArmResult(
            arm=arm,
            task=task.public_mapping(),
            certificate=certificate.to_mapping(),
            solved=False,
            control_impossibility_proved=control_impossible,
            infrastructure_cycle_valid=False,
            functional_metamorphosis_supported=False,
            final_body=task.founder,
            initial_state_digest=f0_digest,
            final_state_digest=f0_digest,
            rolling_head=rolling.head,
            checkpoint_digest=None,
            journal_head=None,
            full_fast_path_head=full_recorder.head if full_recorder else None,
            decision_transcript=tuple(transcript),
            decision_transcript_digest=_transcript_digest(transcript),
            functional_counters=functional_counters.to_mapping(),
            audit_counters=audit_counters.as_mapping(),
            full_fast_path_records=full_recorder.records if full_recorder else (),
        )

    functional_counters.escalations += 1
    functional_counters.false_escalations += int(not target_requires_growth)
    transcript.append(
        {
            "decision": "escalation",
            "taken": True,
            "reason": "proved_structural_incapacity",
        }
    )
    checkpoint = EscalationCheckpoint(
        schema_version=SCHEMA_VERSION,
        protocol_commitment=protocol_commitment,
        fast_trace_head=rolling.head,
        fast_event_count=rolling.event_count,
        body=task.founder.to_dict(),
        body_digest=functional_digest({"body": task.founder.to_dict()}),
        portable_learning_state=portable_learning_state,
        tool_registry=registry,
        deterministic_counters=functional_counters.to_mapping(),
        rng_algorithm_and_state=rng_state,
        admitted_observations=[
            {"word": list(word), "label": label}
            for word, label in sorted(evidence.items())
        ],
        evidence_digest=evidence_digest(evidence),
        incapacity_certificate=certificate.to_mapping(),
        escalation_reason="proved_structural_incapacity",
    )
    journal = CausalJournal.open_from_checkpoint(checkpoint, counters=audit_counters)
    checkpoint_digest = checkpoint.checkpoint_digest()

    recomputed_certificate = proved_structural_incapacity(
        task.founder,
        evidence,
        maximum_search_nodes=certificate.maximum_search_nodes,
        maximum_prefix_count=certificate.maximum_prefix_count,
    )
    _charge_certificate(functional_counters, recomputed_certificate)
    if recomputed_certificate.to_mapping() != certificate.to_mapping():
        raise RuntimeError("slow-path certificate recomputation diverged")
    verify_structural_incapacity_certificate(
        task.founder,
        evidence,
        recomputed_certificate,
        recompute=False,
    )
    certificate_digest = _certificate_artifact_digest(certificate)
    journal.append(
        "StructuralIncapacityCertified",
        result_state_digest=f0_digest,
        operation_parameters={"certificate": certificate.to_mapping()},
        immutable_input_digests=(certificate_digest, evidence_digest(evidence)),
    )

    adopted: ProposedCandidate | None = None
    f1_body: DFA | None = None
    for candidate in _candidate_stream(task.founder, evidence, functional_counters):
        journal.append(
            "CandidateProposed",
            result_state_digest=journal.state_digest,
            operation_parameters=candidate.mapping(),
        )
        transcript.append(
            {
                "decision": "candidate_proposed",
                "candidate_id": candidate.candidate_id,
                "program_indices": list(candidate.program_indices),
            }
        )
        exact, separating_word = _evaluate_candidate(
            candidate.body,
            task.target,
            functional_counters,
        )
        journal.append(
            "CandidateEvaluated",
            result_state_digest=journal.state_digest,
            operation_parameters={
                "candidate_id": candidate.candidate_id,
                "exact": exact,
                "separating_word": (
                    list(separating_word) if separating_word is not None else None
                ),
            },
        )
        transcript.append(
            {
                "decision": "candidate_evaluated",
                "candidate_id": candidate.candidate_id,
                "exact": exact,
                "separating_word": (
                    list(separating_word) if separating_word is not None else None
                ),
            }
        )
        if not exact:
            journal.append(
                "CandidateRejected",
                result_state_digest=journal.state_digest,
                operation_parameters={
                    "candidate_id": candidate.candidate_id,
                    "reason": "not_exactly_equivalent",
                },
            )
            continue

        adopted = candidate
        f1_body = normalize_dfa(candidate.body)
        break

    if adopted is None or f1_body is None:
        journal.append(
            "CycleCompleted",
            result_state_digest=f0_digest,
            operation_parameters={"functional_success": False, "reason": "no_exact_candidate"},
        )
        transcript.append(
            {"decision": "cycle_completed", "functional_success": False}
        )
        journal.verify_internal_consistency()
        persisted_archive = project_archive(journal.events, counters=audit_counters)
        verify_projection(journal.events, persisted_archive.archive_digest())
        audit_counters.observe_persistent_artifacts(
            len(journal.records) + (len(full_recorder.records) if full_recorder else 0) + 1
        )
        return ArmResult(
            arm=arm,
            task=task.public_mapping(),
            certificate=certificate.to_mapping(),
            solved=False,
            control_impossibility_proved=control_impossible,
            infrastructure_cycle_valid=True,
            functional_metamorphosis_supported=False,
            final_body=task.founder,
            initial_state_digest=f0_digest,
            final_state_digest=f0_digest,
            rolling_head=rolling.head,
            checkpoint_digest=checkpoint_digest,
            journal_head=journal.head,
            full_fast_path_head=full_recorder.head if full_recorder else None,
            decision_transcript=tuple(transcript),
            decision_transcript_digest=_transcript_digest(transcript),
            functional_counters=functional_counters.to_mapping(),
            audit_counters=audit_counters.as_mapping(),
            journal_records=journal.records,
            full_fast_path_records=full_recorder.records if full_recorder else (),
        )

    f1_mapping = _functional_state(
        f1_body,
        portable_learning_state=portable_learning_state,
        tool_registry=registry,
        rng_algorithm_and_state=rng_state,
    )
    f1_digest = functional_digest(f1_mapping)
    journal.append(
        "MutationAdopted",
        result_state_digest=f1_digest,
        operation_parameters={
            "candidate_id": adopted.candidate_id,
            "program_indices": list(adopted.program_indices),
            "program": atoms_to_json(adopted.program),
            "strict_improvement": {
                "f0_exact": False,
                "f1_exact": True,
                "target_minimal_states": task.target.n_states,
                "f0_states": task.founder.n_states,
            },
        },
    )
    transcript.append(
        {
            "decision": "candidate_adopted",
            "candidate_id": adopted.candidate_id,
            "program_indices": list(adopted.program_indices),
        }
    )

    bad_program = (flip("initial"),)
    bad_raw = apply_atoms(f1_body, bad_program)
    if bad_raw is None:
        raise RuntimeError("the forced failing provisional adoption did not change F1")
    bad_body = normalize_dfa(bad_raw)
    bad_id = _candidate_id((-1,), bad_body)
    journal.append(
        "CandidateProposed",
        result_state_digest=f1_digest,
        operation_parameters={
            "candidate_id": bad_id,
            "program_indices": [-1],
            "program": atoms_to_json(bad_program),
            "forced_rollback_probe": True,
        },
    )
    bad_mapping = _functional_state(
        bad_body,
        portable_learning_state=portable_learning_state,
        tool_registry=registry,
        rng_algorithm_and_state=rng_state,
    )
    bad_digest = functional_digest(bad_mapping)
    journal.append(
        "MutationProvisionallyAdopted",
        result_state_digest=bad_digest,
        operation_parameters={
            "candidate_id": bad_id,
            "forced_rollback_probe": True,
        },
    )
    bad_exact, bad_witness = _evaluate_candidate(
        bad_body,
        task.target,
        functional_counters,
    )
    if bad_exact:
        raise RuntimeError("the forced rollback candidate unexpectedly passed")
    journal.append(
        "CandidateEvaluated",
        result_state_digest=bad_digest,
        operation_parameters={
            "candidate_id": bad_id,
            "exact": False,
            "separating_word": list(bad_witness) if bad_witness is not None else None,
            "forced_rollback_probe": True,
        },
    )
    journal.append(
        "CandidateRejected",
        result_state_digest=bad_digest,
        operation_parameters={
            "candidate_id": bad_id,
            "reason": "forced_probe_failed_exact_evaluation",
        },
    )
    journal.rollback(
        target_state_digest=f1_digest,
        reason="forced failing provisional adoption",
    )
    transcript.extend(
        [
            {
                "decision": "provisional_candidate_failed",
                "candidate_id": bad_id,
                "separating_word": (
                    list(bad_witness) if bad_witness is not None else None
                ),
            },
            {
                "decision": "rollback_completed",
                "restored_state_digest": f1_digest,
            },
        ]
    )

    f0_exact = exact_equivalence(task.founder, task.target)[0]
    f1_exact = exact_equivalence(f1_body, task.target)[0]
    functional_counters.functional_deterministic_operations += 2
    final_success = (
        not f0_exact
        and f1_exact
        and journal.state_digest == f1_digest
        and task.target.n_states > task.founder.n_states
    )
    journal.append(
        "CycleCompleted",
        result_state_digest=f1_digest,
        operation_parameters={
            "functional_success": final_success,
            "returned_to_fast_path": True,
            "f0_exact": f0_exact,
            "f1_exact": f1_exact,
        },
    )
    transcript.append(
        {
            "decision": "cycle_completed",
            "functional_success": final_success,
            "returned_to_fast_path": True,
            "final_state_digest": f1_digest,
        }
    )

    journal.verify_internal_consistency()
    external_head = journal.head
    journal.verify_against(
        expected_initial_state_digest=checkpoint.functional_state_digest(),
        expected_checkpoint_digest=checkpoint_digest,
        expected_head=external_head,
    )
    archive = project_archive(journal.events, counters=audit_counters)
    verify_projection(journal.events, archive.archive_digest())
    if full_recorder is not None:
        full_recorder.verify(expected_head=full_recorder.head)
    audit_counters.observe_persistent_artifacts(
        len(journal.records) + (len(full_recorder.records) if full_recorder else 0) + 1
    )

    return ArmResult(
        arm=arm,
        task=task.public_mapping(),
        certificate=certificate.to_mapping(),
        solved=f1_exact,
        control_impossibility_proved=control_impossible,
        infrastructure_cycle_valid=True,
        functional_metamorphosis_supported=final_success,
        final_body=f1_body,
        initial_state_digest=f0_digest,
        final_state_digest=f1_digest,
        rolling_head=rolling.head,
        checkpoint_digest=checkpoint_digest,
        journal_head=external_head,
        full_fast_path_head=full_recorder.head if full_recorder else None,
        decision_transcript=tuple(transcript),
        decision_transcript_digest=_transcript_digest(transcript),
        functional_counters=functional_counters.to_mapping(),
        audit_counters=audit_counters.as_mapping(),
        journal_records=journal.records,
        full_fast_path_records=full_recorder.records if full_recorder else (),
    )


_EQUAL_FUNCTIONAL_DIMENSIONS = (
    "search_nodes",
    "candidates_constructed",
    "candidates_evaluated",
    "tool_calls",
    "rng_draws",
    "escalations",
    "functional_deterministic_operations",
    "certificate_search_nodes",
    "certificate_pair_tests",
    "certificate_suffix_probes",
)

_PROOF_COST_DIMENSIONS = (
    "hash_operations",
    "hashed_event_payload_serializations",
    "persisted_event_serializations",
    "journal_bytes_persisted",
    "compact_events_recorded",
    "compact_batches_serialized",
    "compact_trace_bytes",
    "archive_projection_operations",
    "body_serializations",
    "full_checkpoint_serializations",
    "peak_persistent_audit_artifacts",
    "audit_deterministic_operations",
)

_STRICT_PROOF_DIMENSIONS = (
    "persisted_event_serializations",
    "journal_bytes_persisted",
    "audit_deterministic_operations",
)


def compare_arms_b_and_c(arm_b: ArmResult, arm_c: ArmResult) -> tuple[bool, bool, bool, bool]:
    decision_equivalent = (
        arm_b.decision_transcript_digest == arm_c.decision_transcript_digest
        and arm_b.final_state_digest == arm_c.final_state_digest
        and arm_b.checkpoint_digest == arm_c.checkpoint_digest
        and arm_b.journal_head == arm_c.journal_head
        and all(
            arm_b.functional_counters[name] == arm_c.functional_counters[name]
            for name in _EQUAL_FUNCTIONAL_DIMENSIONS
        )
    )
    compact_equal = arm_b.rolling_head == arm_c.rolling_head
    evidence_subset = (
        compact_equal
        and arm_b.journal_records == arm_c.journal_records
        and len(arm_c.full_fast_path_records) > 0
    )
    no_worse = all(
        arm_b.audit_counters[name] <= arm_c.audit_counters[name]
        for name in _PROOF_COST_DIMENSIONS
    )
    strictly_better = all(
        arm_b.audit_counters[name] < arm_c.audit_counters[name]
        for name in _STRICT_PROOF_DIMENSIONS
    )
    efficiency = decision_equivalent and compact_equal and evidence_subset and no_worse and strictly_better
    return decision_equivalent, compact_equal, evidence_subset, efficiency


def run_m038_development_cycle(
    seed: int = 380_038,
    *,
    protocol_commitment: str = "m038-development",
) -> M038Comparison:
    task = make_m038_task(seed)
    arm_a = _run_arm(task, "A", protocol_commitment=protocol_commitment)
    arm_b = _run_arm(task, "B", protocol_commitment=protocol_commitment)
    arm_c = _run_arm(task, "C", protocol_commitment=protocol_commitment)
    decision, compact, subset, efficiency = compare_arms_b_and_c(arm_b, arm_c)
    combined = (
        not arm_a.solved
        and arm_a.control_impossibility_proved
        and arm_b.infrastructure_cycle_valid
        and arm_c.infrastructure_cycle_valid
        and arm_b.functional_metamorphosis_supported
        and arm_c.functional_metamorphosis_supported
        and efficiency
    )
    return M038Comparison(
        task=task,
        arm_a=arm_a,
        arm_b=arm_b,
        arm_c=arm_c,
        decision_equivalent=decision,
        compact_trace_equal=compact,
        evidence_strict_subset=subset,
        efficiency_claim_supported=efficiency,
        combined_expected_claim_supported=combined,
    )
