"""Exact finite-state evaluation helpers for M033 controls and future primary rows."""

from __future__ import annotations

from collections import deque
from typing import Iterable, Sequence

from .m012b_dfa import DFA


def exact_dfa_match(candidate: DFA, target: DFA) -> bool:
    """Decide behavioural equivalence by exhaustive reachable product traversal."""

    if candidate.alphabet != target.alphabet:
        return False
    pending = deque([(candidate.initial, target.initial)])
    visited: set[tuple[int, int]] = set()
    while pending:
        left, right = pending.popleft()
        if (left, right) in visited:
            continue
        visited.add((left, right))
        if candidate.accepting[left] != target.accepting[right]:
            return False
        for index in range(len(candidate.alphabet)):
            pending.append(
                (
                    candidate.transitions[left][index],
                    target.transitions[right][index],
                )
            )
    return True


def held_out_quality_per_mille(
    candidate: DFA,
    target: DFA,
    words: Sequence[Sequence[int]],
) -> int:
    """Return exact agreement on a frozen held-out word surface."""

    if not words:
        raise ValueError("held-out quality requires at least one word")
    if candidate.alphabet != target.alphabet:
        return 0
    passed = sum(candidate.accepts(word) == target.accepts(word) for word in words)
    return (1000 * passed) // len(words)


def exhaustive_words(alphabet: Iterable[int], max_length: int) -> tuple[tuple[int, ...], ...]:
    """Enumerate every word through ``max_length`` in deterministic breadth order."""

    if max_length < 0:
        raise ValueError("max_length must be non-negative")
    symbols = tuple(alphabet)
    words: list[tuple[int, ...]] = [()]
    frontier: list[tuple[int, ...]] = [()]
    for _ in range(max_length):
        frontier = [word + (symbol,) for word in frontier for symbol in symbols]
        words.extend(frontier)
    return tuple(words)
