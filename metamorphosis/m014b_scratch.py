from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .m012b_dfa import DFA, canonicalize, exact_equivalence, minimize_dfa


class MembershipOracle(Protocol):
    def query(self, word: tuple[int, ...]) -> bool: ...


@dataclass(frozen=True)
class ScratchLearningResult:
    status: str
    hypothesis: DFA | None
    unique_membership_queries: int
    raw_membership_calls: int
    equivalence_queries: int
    rounds: int
    reason: str


def learn_dfa_from_scratch_lstar(
    target_for_privileged_equivalence: DFA,
    oracle: MembershipOracle,
    *,
    membership_budget: int = 20_000,
    equivalence_budget: int = 64,
) -> ScratchLearningResult:
    alphabet = tuple(int(value) for value in target_for_privileged_equivalence.alphabet)
    prefixes: list[tuple[int, ...]] = [()]
    suffixes: list[tuple[int, ...]] = [()]
    cache: dict[tuple[int, ...], bool] = {}
    raw_calls = 0

    def membership(word: tuple[int, ...]) -> bool:
        nonlocal raw_calls
        if word not in cache:
            if len(cache) >= membership_budget:
                raise RuntimeError("scratch_membership_budget_exhausted")
            cache[word] = bool(oracle.query(word))
            raw_calls += 1
        return cache[word]

    def row(prefix: tuple[int, ...]) -> tuple[bool, ...]:
        return tuple(membership(prefix + suffix) for suffix in suffixes)

    equivalence_queries = 0
    rounds = 0
    try:
        while equivalence_queries < equivalence_budget:
            rounds += 1
            while True:
                row_representatives = {row(prefix): prefix for prefix in prefixes}
                unclosed: tuple[int, ...] | None = None
                for prefix in tuple(prefixes):
                    for symbol in alphabet:
                        extension = prefix + (symbol,)
                        if row(extension) not in row_representatives:
                            unclosed = extension
                            break
                    if unclosed is not None:
                        break
                if unclosed is not None:
                    prefixes.append(unclosed)
                    continue

                inconsistent_suffix: tuple[int, ...] | None = None
                for first_index, first in enumerate(prefixes):
                    for second in prefixes[first_index + 1 :]:
                        if row(first) != row(second):
                            continue
                        for symbol in alphabet:
                            first_extension = first + (symbol,)
                            second_extension = second + (symbol,)
                            if row(first_extension) == row(second_extension):
                                continue
                            for suffix in suffixes:
                                if membership(first_extension + suffix) != membership(second_extension + suffix):
                                    inconsistent_suffix = (symbol,) + suffix
                                    break
                            if inconsistent_suffix is not None:
                                break
                        if inconsistent_suffix is not None:
                            break
                    if inconsistent_suffix is not None:
                        break
                if inconsistent_suffix is not None:
                    if inconsistent_suffix not in suffixes:
                        suffixes.append(inconsistent_suffix)
                    continue
                break

            representatives: dict[tuple[bool, ...], tuple[int, ...]] = {}
            for prefix in prefixes:
                representatives.setdefault(row(prefix), prefix)
            rows = tuple(representatives)
            state_index = {value: index for index, value in enumerate(rows)}
            transitions: list[tuple[int, ...]] = []
            accepting: list[bool] = []
            for value in rows:
                representative = representatives[value]
                transitions.append(
                    tuple(state_index[row(representative + (symbol,))] for symbol in alphabet)
                )
                accepting.append(membership(representative))
            hypothesis = canonicalize(
                minimize_dfa(
                    DFA(
                        alphabet,
                        tuple(transitions),
                        tuple(accepting),
                        state_index[row(())],
                    )
                )
            )
            equivalence_queries += 1
            equivalent, counterexample = exact_equivalence(
                hypothesis,
                target_for_privileged_equivalence,
            )
            if equivalent:
                return ScratchLearningResult(
                    "success",
                    hypothesis,
                    len(cache),
                    raw_calls,
                    equivalence_queries,
                    rounds,
                    "exact_hypothesis_learned",
                )
            if counterexample is None:
                return ScratchLearningResult(
                    "failed", None, len(cache), raw_calls, equivalence_queries,
                    rounds, "equivalence_oracle_returned_no_counterexample",
                )
            frozen = tuple(int(value) for value in counterexample)
            for length in range(len(frozen) + 1):
                prefix = frozen[:length]
                if prefix not in prefixes:
                    prefixes.append(prefix)
    except RuntimeError as exc:
        return ScratchLearningResult(
            "failed", None, len(cache), raw_calls, equivalence_queries, rounds, str(exc)
        )

    return ScratchLearningResult(
        "failed",
        None,
        len(cache),
        raw_calls,
        equivalence_queries,
        rounds,
        "scratch_equivalence_budget_exhausted",
    )
