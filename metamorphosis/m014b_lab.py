from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Sequence

from .m012b_dfa import DFA, exact_equivalence, random_minimal_dfa
from .m014b_policy import (
    CandidateUpdate,
    EditHypothesis,
    LEARNABLE_SCHEMAS,
    apply_hypothesis,
    dfa_accepts,
    generate_candidates,
    normalize_dfa,
)


@dataclass
class BehavioralUpdateOracle:
    """Lab-owned behavioral surface; the target DFA is never exposed to Genesis."""

    target: DFA
    mode: str = "stable"
    alternate_target: DFA | None = None
    calls: int = 0

    def __post_init__(self) -> None:
        self._per_word_calls: dict[tuple[int, ...], int] = {}

    def query(self, word: tuple[int, ...]) -> bool:
        frozen = tuple(int(value) for value in word)
        self.calls += 1
        self._per_word_calls[frozen] = self._per_word_calls.get(frozen, 0) + 1
        target = self.target
        if self.mode == "changing" and self.alternate_target is not None and self.calls > 8:
            target = self.alternate_target
        value = dfa_accepts(target, frozen)
        if self.mode == "alternating" and self._per_word_calls[frozen] % 2 == 0:
            return not value
        if self.mode == "periodic_three" and self._per_word_calls[frozen] % 3 == 0:
            return not value
        return value

    # Evaluator-only method. Public policy and engine source are audited against this name.
    def _audit_target(self) -> DFA:
        return self.target


def _select_candidate(base: DFA, schema: str, seed: int) -> CandidateUpdate:
    candidates = generate_candidates(base, (schema,), 5000)
    if not candidates:
        raise RuntimeError(f"no distinct candidate for schema {schema}")
    return random.Random(seed).choice(candidates)


def make_development_demonstrations() -> tuple[tuple[DFA, DFA], ...]:
    demonstrations: list[tuple[DFA, DFA]] = []
    for index in range(12):
        base = normalize_dfa(random_minimal_dfa(31_000 + index))
        schema = LEARNABLE_SCHEMAS[index % len(LEARNABLE_SCHEMAS)]
        selected = _select_candidate(base, schema, 31_500 + index)
        demonstrations.append((base, selected.dfa))
    return tuple(demonstrations)


def make_positive_update(base: DFA, update_seed: int) -> CandidateUpdate:
    schema = LEARNABLE_SCHEMAS[update_seed % len(LEARNABLE_SCHEMAS)]
    return _select_candidate(normalize_dfa(base), schema, update_seed ^ 0x14B5_EED)


def make_development_positive_case(index: int) -> tuple[DFA, CandidateUpdate]:
    base = normalize_dfa(random_minimal_dfa(32_000 + index))
    return base, make_positive_update(base, 33_000 + index)


def _outside_learned_language(base: DFA, target: DFA) -> bool:
    return all(
        not exact_equivalence(candidate.dfa, target)[0]
        for candidate in generate_candidates(base, LEARNABLE_SCHEMAS, 5000)
    )


def make_three_edit_target(base: DFA, seed: int) -> DFA:
    normalized = normalize_dfa(base)
    rng = random.Random(seed)
    state_count = len(normalized.transitions)
    for _ in range(512):
        acceptance_state = rng.randrange(state_count)
        first_state = rng.randrange(state_count)
        first_symbol = rng.randrange(2)
        first_target = rng.randrange(state_count)
        second_state = rng.randrange(state_count)
        second_symbol = rng.randrange(2)
        second_target = rng.randrange(state_count)
        if first_target == normalized.transitions[first_state][first_symbol]:
            continue
        if second_target == normalized.transitions[second_state][second_symbol]:
            continue
        if (first_state, first_symbol) == (second_state, second_symbol):
            continue
        first = apply_hypothesis(
            normalized,
            EditHypothesis(
                "two_independent_local_edits",
                (acceptance_state, first_state, first_symbol, first_target),
            ),
        )
        target = apply_hypothesis(
            first,
            EditHypothesis(
                "transition_redirect",
                (second_state, second_symbol, second_target),
            ),
        )
        if not exact_equivalence(normalized, target)[0] and _outside_learned_language(normalized, target):
            return normalize_dfa(target)
    raise RuntimeError("unable to construct a distinct three-edit negative target")


def make_state_adding_target(base: DFA, seed: int) -> DFA:
    normalized = normalize_dfa(base)
    rng = random.Random(seed)
    state_count = len(normalized.transitions)
    for _ in range(512):
        transitions = [list(row) for row in normalized.transitions]
        accepting = list(normalized.accepting)
        new_state = state_count
        transitions.append([rng.randrange(state_count + 1), rng.randrange(state_count + 1)])
        accepting.append(bool(rng.randrange(2)))
        source = rng.randrange(state_count)
        symbol = rng.randrange(2)
        transitions[source][symbol] = new_state
        target = DFA(
            tuple(normalized.alphabet),
            tuple(tuple(int(value) for value in row) for row in transitions),
            tuple(bool(value) for value in accepting),
            normalized.initial,
        )
        target = normalize_dfa(target)
        if len(target.transitions) > len(normalized.transitions) and _outside_learned_language(normalized, target):
            return target
    raise RuntimeError("unable to construct a distinct state-adding negative target")


def make_nondeterministic_oracle(base: DFA, seed: int, kind: int) -> BehavioralUpdateOracle:
    selected = make_positive_update(base, seed)
    if kind % 3 == 0:
        return BehavioralUpdateOracle(selected.dfa, "alternating")
    if kind % 3 == 1:
        return BehavioralUpdateOracle(selected.dfa, "periodic_three")
    alternate = make_three_edit_target(base, seed ^ 0xC0FFEE)
    return BehavioralUpdateOracle(selected.dfa, "changing", alternate)


def hidden_words(seed: int, count: int = 10_000) -> tuple[tuple[int, ...], ...]:
    rng = random.Random(seed)
    return tuple(
        tuple(rng.randrange(2) for _ in range(rng.randint(0, 128)))
        for _ in range(count)
    )


def hidden_accuracy(target: DFA, candidate: DFA, words: Iterable[tuple[int, ...]]) -> float:
    values = [dfa_accepts(target, word) == dfa_accepts(candidate, word) for word in words]
    return sum(values) / len(values) if values else 1.0
