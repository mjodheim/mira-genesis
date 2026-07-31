from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable

from .m012b_dfa import DFA, Word, minimize_dfa, words_up_to

class QueryBudgetExceeded(RuntimeError):
    pass


class InconsistentContract(RuntimeError):
    pass


class OpaqueBehavioralContract:
    """The only task interface visible to Genesis.

    The callable is intentionally wrapped. Genesis receives membership answers,
    never a target transition table or target state identifier.
    """

    def __init__(self, fn: Callable[[Word], bool], budget: int) -> None:
        self._fn = fn
        self.budget = budget
        self.calls = 0
        self.cache: dict[Word, bool] = {}

    def query_uncached(self, word: Word) -> bool:
        if self.calls >= self.budget:
            raise QueryBudgetExceeded("behavioural_query_budget_exhausted")
        self.calls += 1
        return bool(self._fn(word))

    def query(self, word: Word) -> bool:
        if word not in self.cache:
            self.cache[word] = self.query_uncached(word)
        return self.cache[word]

    def audit_consistency(self) -> None:
        probes: tuple[Word, ...] = (
            (),
            (0,),
            (1,),
            (0, 1),
            (1, 0),
            (1, 1),
            (0, 1, 0),
            (1, 0, 1),
        )
        for word in probes:
            first = self.query_uncached(word)
            second = self.query_uncached(word)
            if first != second:
                raise InconsistentContract(f"non_deterministic_contract_at:{word}")
            prior = self.cache.get(word)
            if prior is not None and prior != first:
                raise InconsistentContract(f"contract_changed_at:{word}")
            self.cache[word] = first


@dataclass(frozen=True)
class ExtractionStats:
    rounds: int
    counterexamples: int
    prefixes: int
    suffixes: int


class LStarExtractor:
    """Bounded active learner using only membership queries.

    Candidate equivalence is approximated internally by a fixed exhaustive
    prefix suite plus pseudorandom probes. Exact equivalence remains external.
    """

    def __init__(
        self,
        contract: OpaqueBehavioralContract,
        seed: int,
        exhaustive_depth: int = 11,
        random_probes: int = 4_000,
        random_max_length: int = 64,
    ) -> None:
        self.contract = contract
        self.prefixes: list[Word] = [()]
        self.suffixes: list[Word] = [()]
        self.rounds = 0
        self.counterexamples = 0
        rng = random.Random(seed)
        self.probes = [
            tuple(rng.randrange(2) for _ in range(rng.randint(0, random_max_length)))
            for _ in range(random_probes)
        ]
        self.exhaustive_depth = exhaustive_depth

    def _row(self, prefix: Word) -> tuple[bool, ...]:
        return tuple(self.contract.query(prefix + suffix) for suffix in self.suffixes)

    def _close_and_consistent(self) -> None:
        while True:
            known_rows = {self._row(prefix) for prefix in self.prefixes}
            changed = False
            for prefix in list(self.prefixes):
                for symbol in (0, 1):
                    extension = prefix + (symbol,)
                    if self._row(extension) not in known_rows:
                        self.prefixes.append(extension)
                        changed = True
                        break
                if changed:
                    break
            if changed:
                continue

            for index, left in enumerate(self.prefixes):
                for right in self.prefixes[index + 1 :]:
                    if self._row(left) != self._row(right):
                        continue
                    for symbol in (0, 1):
                        left_row = self._row(left + (symbol,))
                        right_row = self._row(right + (symbol,))
                        if left_row == right_row:
                            continue
                        for suffix_index, values in enumerate(zip(left_row, right_row)):
                            if values[0] != values[1]:
                                new_suffix = (symbol,) + self.suffixes[suffix_index]
                                if new_suffix not in self.suffixes:
                                    self.suffixes.append(new_suffix)
                                changed = True
                                break
                        if changed:
                            break
                    if changed:
                        break
                if changed:
                    break
            if not changed:
                return

    def _hypothesis(self) -> DFA:
        rows: dict[tuple[bool, ...], int] = {}
        representatives: list[Word] = []
        for prefix in self.prefixes:
            row = self._row(prefix)
            if row not in rows:
                rows[row] = len(rows)
                representatives.append(prefix)
        transitions: list[tuple[int, int]] = []
        accepting: list[bool] = []
        for representative in representatives:
            accepting.append(self.contract.query(representative))
            transitions.append(
                tuple(rows[self._row(representative + (symbol,))] for symbol in (0, 1))  # type: ignore[arg-type]
            )
        initial = rows[self._row(())]
        return minimize_dfa(DFA((0, 1), tuple(transitions), tuple(accepting), initial))

    def _counterexample(self, candidate: DFA) -> Word | None:
        for word in words_up_to(self.exhaustive_depth):
            if candidate.accepts(word) != self.contract.query(word):
                return word
        for word in self.probes:
            if candidate.accepts(word) != self.contract.query(word):
                return word
        return None

    def extract(self, max_rounds: int = 80) -> tuple[DFA, ExtractionStats]:
        for _ in range(max_rounds):
            self.rounds += 1
            self._close_and_consistent()
            candidate = self._hypothesis()
            counterexample = self._counterexample(candidate)
            if counterexample is None:
                return candidate, ExtractionStats(
                    rounds=self.rounds,
                    counterexamples=self.counterexamples,
                    prefixes=len(self.prefixes),
                    suffixes=len(self.suffixes),
                )
            self.counterexamples += 1
            for length in range(len(counterexample) + 1):
                prefix = counterexample[:length]
                if prefix not in self.prefixes:
                    self.prefixes.append(prefix)
        raise RuntimeError("active_state_discovery_did_not_converge")
