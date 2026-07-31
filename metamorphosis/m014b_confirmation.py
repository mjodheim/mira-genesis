from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Protocol

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


def bounded_confirmation_words(max_length: int = 5) -> tuple[tuple[int, ...], ...]:
    return tuple(
        word
        for length in range(max_length + 1)
        for word in product((0, 1), repeat=length)
    )


def confirm_candidate(
    candidate: DFA,
    oracle: BehavioralOracle,
    *,
    already_asked: set[tuple[int, ...]] | None = None,
    raw_budget: int,
    repetitions: int = 2,
    max_length: int = 5,
) -> ConformanceConfirmation:
    asked = already_asked or set()
    checked: list[tuple[int, ...]] = []
    raw_calls = 0
    for word in bounded_confirmation_words(max_length):
        if word in asked:
            continue
        if raw_calls + repetitions > raw_budget:
            return ConformanceConfirmation(
                "abstained",
                "insufficient_budget_for_bounded_conformance_confirmation",
                raw_calls,
                len(checked),
                tuple(checked),
            )
        answers = [bool(oracle.query(word)) for _ in range(repetitions)]
        raw_calls += repetitions
        checked.append(word)
        if len(set(answers)) != 1:
            return ConformanceConfirmation(
                "abstained",
                "behavioral_oracle_inconsistent_during_confirmation",
                raw_calls,
                len(checked),
                tuple(checked),
            )
        if answers[0] != dfa_accepts(candidate, word):
            return ConformanceConfirmation(
                "abstained",
                "candidate_failed_bounded_conformance_confirmation",
                raw_calls,
                len(checked),
                tuple(checked),
            )
    return ConformanceConfirmation(
        "confirmed",
        "bounded_conformance_suite_passed",
        raw_calls,
        len(checked),
        tuple(checked),
    )
