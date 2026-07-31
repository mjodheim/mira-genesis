from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import product
import hashlib
import random
from typing import Iterable, Mapping, Sequence

Word = tuple[int, ...]
TruthTable = tuple[int, ...]
Signature = tuple[int, ...]

@dataclass(frozen=True)
class DFA:
    alphabet: tuple[int, ...]
    transitions: tuple[tuple[int, ...], ...]
    accepting: tuple[bool, ...]
    initial: int = 0

    def __post_init__(self) -> None:
        n = len(self.transitions)
        if not n or len(self.accepting) != n:
            raise ValueError("invalid DFA dimensions")
        if not 0 <= self.initial < n:
            raise ValueError("invalid initial state")
        width = len(self.alphabet)
        if any(len(row) != width for row in self.transitions):
            raise ValueError("transition width mismatch")
        if any(not 0 <= target < n for row in self.transitions for target in row):
            raise ValueError("invalid transition target")

    @property
    def n_states(self) -> int:
        return len(self.transitions)

    def run_state(self, word: Sequence[int]) -> int:
        state = self.initial
        for symbol in word:
            if symbol not in self.alphabet:
                raise ValueError(f"unknown symbol: {symbol}")
            state = self.transitions[state][self.alphabet.index(symbol)]
        return state

    def accepts(self, word: Sequence[int]) -> bool:
        return self.accepting[self.run_state(word)]

    def to_dict(self) -> dict[str, object]:
        return {
            "alphabet": list(self.alphabet),
            "transitions": [list(row) for row in self.transitions],
            "accepting": list(self.accepting),
            "initial": self.initial,
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "DFA":
        return DFA(
            alphabet=tuple(int(x) for x in data["alphabet"]),  # type: ignore[index]
            transitions=tuple(tuple(int(x) for x in row) for row in data["transitions"]),  # type: ignore[index]
            accepting=tuple(bool(x) for x in data["accepting"]),  # type: ignore[index]
            initial=int(data.get("initial", 0)),
        )


def canonicalize(dfa: DFA) -> DFA:
    mapping = {dfa.initial: 0}
    order = [dfa.initial]
    queue = deque([dfa.initial])
    while queue:
        state = queue.popleft()
        for target in dfa.transitions[state]:
            if target not in mapping:
                mapping[target] = len(mapping)
                order.append(target)
                queue.append(target)
    transitions = tuple(
        tuple(mapping[target] for target in dfa.transitions[old]) for old in order
    )
    accepting = tuple(dfa.accepting[old] for old in order)
    return DFA(dfa.alphabet, transitions, accepting, 0)


def minimize_dfa(dfa: DFA) -> DFA:
    dfa = canonicalize(dfa)
    states = set(range(dfa.n_states))
    accepting = {state for state in states if dfa.accepting[state]}
    rejecting = states - accepting
    partitions = [part for part in (accepting, rejecting) if part]
    while True:
        state_to_part = {
            state: index for index, part in enumerate(partitions) for state in part
        }
        refined: list[set[int]] = []
        changed = False
        for part in partitions:
            buckets: dict[tuple[int, ...], set[int]] = {}
            for state in part:
                signature = tuple(
                    state_to_part[target] for target in dfa.transitions[state]
                )
                buckets.setdefault(signature, set()).add(state)
            refined.extend(buckets.values())
            changed |= len(buckets) > 1
        partitions = refined
        if not changed:
            break
    state_to_part = {
        state: index for index, part in enumerate(partitions) for state in part
    }
    transitions: list[tuple[int, ...]] = []
    accepting_out: list[bool] = []
    for part in partitions:
        representative = min(part)
        transitions.append(
            tuple(state_to_part[target] for target in dfa.transitions[representative])
        )
        accepting_out.append(dfa.accepting[representative])
    return canonicalize(
        DFA(
            dfa.alphabet,
            tuple(transitions),
            tuple(accepting_out),
            state_to_part[dfa.initial],
        )
    )


def exact_equivalence(left: DFA, right: DFA) -> tuple[bool, Word | None]:
    if left.alphabet != right.alphabet:
        return False, ()
    queue = deque([(left.initial, right.initial, ())])
    seen = {(left.initial, right.initial)}
    while queue:
        l_state, r_state, word = queue.popleft()
        if left.accepting[l_state] != right.accepting[r_state]:
            return False, word
        for index, symbol in enumerate(left.alphabet):
            nxt = (left.transitions[l_state][index], right.transitions[r_state][index])
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt[0], nxt[1], word + (symbol,)))
    return True, None


def random_minimal_dfa(seed: int, min_states: int = 3, max_states: int = 8) -> DFA:
    """Deterministically derive a suitable DFA from a seed.

    Rejection is deterministic and depends only on the supplied seed. The
    evaluation seed itself is generated only after the evaluation commit is
    frozen.
    """

    for attempt in range(20_000):
        digest = hashlib.sha256(f"{seed}:{attempt}".encode("utf-8")).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        n = rng.randint(min_states, max_states)
        transitions = tuple(tuple(rng.randrange(n) for _ in (0, 1)) for _ in range(n))
        accepting = tuple(rng.random() < 0.5 for _ in range(n))
        if all(accepting) or not any(accepting):
            continue
        candidate = minimize_dfa(DFA((0, 1), transitions, accepting, 0))
        if min_states <= candidate.n_states <= max_states:
            return candidate
    raise RuntimeError("unable to derive a suitable deterministic target")


def words_up_to(max_length: int) -> Iterable[Word]:
    yield ()
    for length in range(1, max_length + 1):
        yield from product((0, 1), repeat=length)
