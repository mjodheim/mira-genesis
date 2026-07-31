from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import itertools
import json
import random
from typing import Mapping, Protocol, Sequence

from .m012b_dfa import DFA, canonicalize, exact_equivalence, minimize_dfa

Word = tuple[int, ...]


def normalize_dfa(dfa: DFA) -> DFA:
    return canonicalize(minimize_dfa(dfa))


def dfa_key(dfa: DFA) -> str:
    normalized = normalize_dfa(dfa)
    return json.dumps(normalized.to_dict(), sort_keys=True, separators=(",", ":"))


def _graph_features(dfa: DFA) -> tuple[list[int], list[int]]:
    n = dfa.n_states
    distances = [10**9] * n
    distances[dfa.initial] = 0
    queue = deque([dfa.initial])
    while queue:
        state = queue.popleft()
        for target in dfa.transitions[state]:
            if distances[target] > distances[state] + 1:
                distances[target] = distances[state] + 1
                queue.append(target)
    indegree = [0] * n
    for row in dfa.transitions:
        for target in row:
            indegree[target] += 1
    return distances, indegree


def role_state(dfa: DFA, role: str) -> int | None:
    distances, indegree = _graph_features(dfa)
    states = list(range(dfa.n_states))
    if role == "initial":
        return dfa.initial
    want_accepting: bool | None = None
    if role.endswith("_accepting"):
        want_accepting = True
        base_role = role[: -len("_accepting")]
    elif role.endswith("_rejecting"):
        want_accepting = False
        base_role = role[: -len("_rejecting")]
    else:
        base_role = role
    if want_accepting is not None:
        states = [state for state in states if bool(dfa.accepting[state]) == want_accepting]
    if not states:
        return None
    if base_role == "deepest":
        return max(states, key=lambda state: (distances[state], indegree[state], -state))
    if base_role == "max_indegree":
        return max(states, key=lambda state: (indegree[state], distances[state], -state))
    if base_role == "min_indegree":
        return min(states, key=lambda state: (indegree[state], -distances[state], state))
    raise ValueError(f"unknown structural role: {role}")


@dataclass(frozen=True)
class StructuralProgram:
    program_id: str
    operations: tuple[tuple[object, ...], ...]
    group: str

    def to_dict(self) -> dict[str, object]:
        return {
            "program_id": self.program_id,
            "operations": [list(operation) for operation in self.operations],
            "group": self.group,
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "StructuralProgram":
        return StructuralProgram(
            program_id=str(data["program_id"]),
            operations=tuple(tuple(operation) for operation in data["operations"]),  # type: ignore[arg-type,index]
            group=str(data["group"]),
        )


def apply_program(base: DFA, program: StructuralProgram) -> DFA | None:
    source = normalize_dfa(base)
    transitions = [list(row) for row in source.transitions]
    accepting = list(source.accepting)
    for operation in program.operations:
        kind = str(operation[0])
        if kind == "flip":
            state = role_state(source, str(operation[1]))
            if state is None:
                return None
            accepting[state] = not accepting[state]
        elif kind == "redirect":
            source_state = role_state(source, str(operation[1]))
            symbol = int(operation[2])
            target_state = role_state(source, str(operation[3]))
            if source_state is None or target_state is None:
                return None
            transitions[source_state][symbol] = target_state
        else:
            raise ValueError(f"unknown program operation: {kind}")
    candidate = normalize_dfa(
        DFA(
            source.alphabet,
            tuple(tuple(row) for row in transitions),
            tuple(accepting),
            source.initial,
        )
    )
    if exact_equivalence(source, candidate)[0]:
        return None
    return candidate


@dataclass(frozen=True)
class MetaCandidate:
    program: StructuralProgram
    dfa: DFA


class BehavioralOracle(Protocol):
    def query(self, word: Word) -> bool: ...


def generate_candidates(base: DFA, programs: Sequence[StructuralProgram]) -> tuple[MetaCandidate, ...]:
    found: dict[str, MetaCandidate] = {}
    for program in programs:
        candidate = apply_program(base, program)
        if candidate is None:
            continue
        key = dfa_key(candidate)
        found.setdefault(key, MetaCandidate(program, candidate))
    return tuple(found[key] for key in sorted(found))


def fixed_words(max_length: int = 8) -> tuple[Word, ...]:
    return tuple(
        word
        for length in range(max_length + 1)
        for word in itertools.product((0, 1), repeat=length)
    )


def signature(dfa: DFA, max_length: int = 8) -> tuple[bool, ...]:
    outputs = [bool(dfa.accepting[dfa.initial])]
    frontier = [dfa.initial]
    for _ in range(max_length):
        next_frontier: list[int] = []
        for state in frontier:
            next_frontier.extend(dfa.transitions[state])
        outputs.extend(bool(dfa.accepting[state]) for state in next_frontier)
        frontier = next_frontier
    return tuple(outputs)


@dataclass(frozen=True)
class MetaPlasticityPassport:
    version: str
    programs: tuple[StructuralProgram, ...]
    global_counts: tuple[tuple[str, int], ...]
    global_group_counts: tuple[tuple[str, int], ...]
    adaptation_increment: int
    repeat_queries: int
    query_max_length: int
    confirmation_max_length: int
    development_provenance_sha256: str

    def counts(self) -> dict[str, int]:
        return {program_id: int(count) for program_id, count in self.global_counts}

    def group_counts(self) -> dict[str, int]:
        return {group: int(count) for group, count in self.global_group_counts}

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": self.version,
                "programs": [program.to_dict() for program in self.programs],
                "global_counts": [[program_id, count] for program_id, count in self.global_counts],
                "global_group_counts": [[group, count] for group, count in self.global_group_counts],
                "adaptation_increment": self.adaptation_increment,
                "repeat_queries": self.repeat_queries,
                "query_max_length": self.query_max_length,
                "confirmation_max_length": self.confirmation_max_length,
                "development_provenance_sha256": self.development_provenance_sha256,
                "trace_number_format": "integers_only",
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "MetaPlasticityPassport":
        data = json.loads(raw)
        if data.get("version") != "m014c-meta-plasticity/2":
            raise ValueError("unsupported M014c passport")
        return MetaPlasticityPassport(
            version=str(data["version"]),
            programs=tuple(StructuralProgram.from_dict(row) for row in data["programs"]),
            global_counts=tuple((str(row[0]), int(row[1])) for row in data["global_counts"]),
            global_group_counts=tuple((str(row[0]), int(row[1])) for row in data["global_group_counts"]),
            adaptation_increment=int(data["adaptation_increment"]),
            repeat_queries=int(data["repeat_queries"]),
            query_max_length=int(data["query_max_length"]),
            confirmation_max_length=int(data["confirmation_max_length"]),
            development_provenance_sha256=str(data["development_provenance_sha256"]),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def train_meta_passport(
    programs: Sequence[StructuralProgram],
    demonstrations: Sequence[tuple[DFA, DFA, str, str]],
    adaptation_increment: int = 48,
) -> MetaPlasticityPassport:
    program_map = {program.program_id: program for program in programs}
    counts = {program.program_id: 1 for program in programs}
    group_counts = {program.group: 1 for program in programs}
    canonical_rows: list[dict[str, object]] = []
    for before, after, program_id, environment_id in demonstrations:
        if program_id not in program_map:
            raise ValueError(f"unknown demonstrated program: {program_id}")
        predicted = apply_program(before, program_map[program_id])
        if predicted is None or not exact_equivalence(predicted, after)[0]:
            raise ValueError("demonstration does not match its structural program")
        counts[program_id] += 1
        group_counts[program_map[program_id].group] += 1
        canonical_rows.append({
            "before": normalize_dfa(before).to_dict(),
            "after": normalize_dfa(after).to_dict(),
            "program_id": program_id,
            "environment_id": environment_id,
        })
    provenance = hashlib.sha256(
        json.dumps(canonical_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return MetaPlasticityPassport(
        version="m014c-meta-plasticity/2",
        programs=tuple(programs),
        global_counts=tuple(sorted(counts.items())),
        global_group_counts=tuple(sorted(group_counts.items())),
        adaptation_increment=adaptation_increment,
        repeat_queries=2,
        query_max_length=8,
        confirmation_max_length=4,
        development_provenance_sha256=provenance,
    )


def uniform_meta_passport(passport: MetaPlasticityPassport) -> MetaPlasticityPassport:
    return MetaPlasticityPassport(
        version=passport.version,
        programs=passport.programs,
        global_counts=tuple((program.program_id, 1) for program in passport.programs),
        global_group_counts=tuple(sorted({(program.group, 1) for program in passport.programs})),
        adaptation_increment=passport.adaptation_increment,
        repeat_queries=passport.repeat_queries,
        query_max_length=passport.query_max_length,
        confirmation_max_length=passport.confirmation_max_length,
        development_provenance_sha256=passport.development_provenance_sha256,
    )


@dataclass(frozen=True)
class MetaInference:
    status: str
    reason: str
    updated_passport: DFA | None
    program_id: str | None
    raw_oracle_calls: int
    identification_calls: int
    confirmation_calls: int
    initial_candidates: int
    trace_digest_sha256: str
    trace: tuple[Mapping[str, object], ...]


class MetaPlasticitySession:
    def __init__(
        self,
        passport: MetaPlasticityPassport,
        *,
        adaptive: bool = True,
    ) -> None:
        self.passport = passport
        self.adaptive = adaptive
        self._counts = passport.counts()
        self._group_counts = passport.group_counts()
        self.episode = 0

    @property
    def counts(self) -> Mapping[str, int]:
        return dict(self._counts)

    @property
    def group_counts(self) -> Mapping[str, int]:
        return dict(self._group_counts)

    def _candidate_weights(self, candidates: Sequence[MetaCandidate]) -> list[int]:
        return [max(1, self._group_counts.get(candidate.program.group, 1)) for candidate in candidates]

    def identify(
        self,
        base: DFA,
        oracle: BehavioralOracle,
        *,
        query_budget: int = 128,
        policy: str = "adaptive",
        search_seed: int = 0,
    ) -> MetaInference:
        candidates = list(generate_candidates(base, self.passport.programs))
        if not candidates:
            return MetaInference("abstained", "no_applicable_structural_program", None, None, 0, 0, 0, 0, "", ())
        initial_candidates = len(candidates)
        words = fixed_words(self.passport.query_max_length)
        signatures = {id(candidate): signature(candidate.dfa, self.passport.query_max_length) for candidate in candidates}
        weights = self._candidate_weights(candidates)
        rng = random.Random(search_seed)
        asked: set[Word] = set()
        trace: list[dict[str, object]] = []
        raw_calls = 0

        while len(candidates) > 1:
            available: list[tuple[Word, list[int], list[int]]] = []
            for index, word in enumerate(words):
                if word in asked:
                    continue
                zero = [i for i, candidate in enumerate(candidates) if not signatures[id(candidate)][index]]
                one = [i for i, candidate in enumerate(candidates) if signatures[id(candidate)][index]]
                if zero and one:
                    available.append((word, zero, one))
            if not available:
                reference = candidates[0]
                if all(exact_equivalence(reference.dfa, candidate.dfa)[0] for candidate in candidates[1:]):
                    candidates = [reference]
                    weights = [weights[0]]
                    break
                return MetaInference("abstained", "unresolved_structural_version_space", None, None, raw_calls, raw_calls, 0, initial_candidates, "", tuple(trace))
            if policy == "random":
                word, zero, one = rng.choice(available)
            else:
                ranked: list[tuple[tuple[object, ...], Word, list[int], list[int]]] = []
                for word, zero, one in available:
                    zero_weight = sum(weights[index] for index in zero)
                    one_weight = sum(weights[index] for index in one)
                    weighted_collision = zero_weight * zero_weight + one_weight * one_weight
                    worst_count = max(len(zero), len(one))
                    worst_weight = max(zero_weight, one_weight)
                    ranking = (
                        -weighted_collision,
                        -worst_weight,
                        -worst_count,
                        -len(word),
                        tuple(-value for value in word),
                    )
                    ranked.append((ranking, word, zero, one))
                _, word, zero, one = max(ranked, key=lambda row: row[0])
            if raw_calls + self.passport.repeat_queries > query_budget:
                return MetaInference("abstained", "query_budget_exhausted", None, None, raw_calls, raw_calls, 0, initial_candidates, "", tuple(trace))
            answers = [bool(oracle.query(word)) for _ in range(self.passport.repeat_queries)]
            raw_calls += self.passport.repeat_queries
            asked.add(word)
            zero_weight = sum(weights[index] for index in zero)
            one_weight = sum(weights[index] for index in one)
            trace.append({
                "episode": self.episode,
                "word": list(word),
                "zero_count": len(zero),
                "one_count": len(one),
                "zero_weight": zero_weight,
                "one_weight": one_weight,
                "answer": int(answers[0]),
            })
            if len(set(answers)) != 1:
                return MetaInference("abstained", "oracle_inconsistent", None, None, raw_calls, raw_calls, 0, initial_candidates, _trace_digest(trace), tuple(trace))
            answer = answers[0]
            keep = one if answer else zero
            candidates = [candidates[index] for index in keep]
            weights = [weights[index] for index in keep]

        selected = candidates[0]
        identification_calls = raw_calls
        confirmation_words = list(asked)
        confirmation_words.extend(word for word in fixed_words(self.passport.confirmation_max_length) if word not in asked)
        for word in confirmation_words:
            if raw_calls + self.passport.repeat_queries > query_budget:
                return MetaInference("abstained", "confirmation_budget_exhausted", None, None, raw_calls, identification_calls, raw_calls - identification_calls, initial_candidates, _trace_digest(trace), tuple(trace))
            answers = [bool(oracle.query(word)) for _ in range(self.passport.repeat_queries)]
            raw_calls += self.passport.repeat_queries
            if len(set(answers)) != 1:
                return MetaInference("abstained", "oracle_changed_during_confirmation", None, None, raw_calls, identification_calls, raw_calls - identification_calls, initial_candidates, _trace_digest(trace), tuple(trace))
            if answers[0] != selected.dfa.accepts(word):
                return MetaInference("abstained", "candidate_failed_confirmation", None, None, raw_calls, identification_calls, raw_calls - identification_calls, initial_candidates, _trace_digest(trace), tuple(trace))

        if self.adaptive:
            self._counts[selected.program.program_id] = self._counts.get(selected.program.program_id, 1) + 1
            group = selected.program.group
            self._group_counts[group] = self._group_counts.get(group, 1) + self.passport.adaptation_increment
        self.episode += 1
        return MetaInference(
            "success",
            "structural_program_identified",
            selected.dfa,
            selected.program.program_id,
            raw_calls,
            identification_calls,
            raw_calls - identification_calls,
            initial_candidates,
            _trace_digest(trace),
            tuple(trace),
        )


def _trace_digest(trace: Sequence[Mapping[str, object]]) -> str:
    return hashlib.sha256(
        json.dumps(list(trace), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
