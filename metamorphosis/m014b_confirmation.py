from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping, Protocol

from .m012b_dfa import DFA
from .m014b_policy import dfa_accepts


class BehavioralOracle(Protocol):
    def query(self, word: tuple[int, ...]) -> bool: ...


@dataclass(frozen=True)
class ConformanceConfirmation:
    status: str
    reason: str
    raw_oracle_calls: int
    unique_queries: int
    checked_words: tuple[tuple[int, ...], ...]


def bounded_confirmation_words(max_length: int = 3) -> tuple[tuple[int, ...], ...]:
    return tuple(
        word
        for length in range(max_length + 1)
        for word in product((0, 1), repeat=length)
    )


def _query_repeated(
    oracle: BehavioralOracle,
    word: tuple[int, ...],
    repetitions: int,
) -> tuple[bool | None, int]:
    answers = [bool(oracle.query(word)) for _ in range(repetitions)]
    if len(set(answers)) != 1:
        return None, repetitions
    return answers[0], repetitions


def confirm_candidate(
    candidate: DFA,
    oracle: BehavioralOracle,
    *,
    prior_answers: Mapping[tuple[int, ...], bool] | None = None,
    raw_budget: int,
    repetitions: int = 2,
    max_length: int = 3,
    replay_count: int = 3,
) -> ConformanceConfirmation:
    remembered = dict(prior_answers or {})
    checked: list[tuple[int, ...]] = []
    raw_calls = 0

    # Replay early evidence to detect an oracle that changed after identification.
    for word, expected in list(remembered.items())[:replay_count]:
        if raw_calls + repetitions > raw_budget:
            return ConformanceConfirmation(
                "abstained",
                "insufficient_budget_for_evidence_replay",
                raw_calls,
                len(checked),
                tuple(checked),
            )
        answer, calls = _query_repeated(oracle, word, repetitions)
        raw_calls += calls
        checked.append(word)
        if answer is None:
            return ConformanceConfirmation(
                "abstained",
                "behavioral_oracle_inconsistent_during_replay",
                raw_calls,
                len(checked),
                tuple(checked),
            )
        if answer != expected:
            return ConformanceConfirmation(
                "abstained",
                "behavioral_oracle_changed_after_identification",
                raw_calls,
                len(checked),
                tuple(checked),
            )

    # A small independent conformance suite checks that uniqueness inside the
    # learned language is not mistaken for truth outside that language.
    for word in bounded_confirmation_words(max_length):
        if word in remembered:
            continue
        if raw_calls + repetitions > raw_budget:
            return ConformanceConfirmation(
                "abstained",
                "insufficient_budget_for_bounded_conformance_confirmation",
                raw_calls,
                len(checked),
                tuple(checked),
            )
        answer, calls = _query_repeated(oracle, word, repetitions)
        raw_calls += calls
        checked.append(word)
        if answer is None:
            return ConformanceConfirmation(
                "abstained",
                "behavioral_oracle_inconsistent_during_confirmation",
                raw_calls,
                len(checked),
                tuple(checked),
            )
        if answer != dfa_accepts(candidate, word):
            return ConformanceConfirmation(
                "abstained",
                "candidate_failed_bounded_conformance_confirmation",
                raw_calls,
                len(checked),
                tuple(checked),
            )
    return ConformanceConfirmation(
        "confirmed",
        "evidence_replay_and_bounded_conformance_passed",
        raw_calls,
        len(checked),
        tuple(checked),
    )
