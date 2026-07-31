from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from collections import deque
from typing import Callable, Iterable, Sequence
import json
import math
import random

import numpy as np
import torch

Word = tuple[int, ...]


@dataclass(frozen=True)
class DFA:
    alphabet: tuple[int, ...]
    transitions: tuple[tuple[int, ...], ...]
    accepting: tuple[bool, ...]
    initial: int = 0

    @property
    def n_states(self) -> int:
        return len(self.transitions)

    def run_state(self, word: Sequence[int]) -> int:
        state = self.initial
        for symbol in word:
            state = self.transitions[state][symbol]
        return state

    def accepts(self, word: Sequence[int]) -> bool:
        return self.accepting[self.run_state(word)]

    def reachable_states(self) -> set[int]:
        seen = {self.initial}
        queue = deque([self.initial])
        while queue:
            s = queue.popleft()
            for a in self.alphabet:
                t = self.transitions[s][a]
                if t not in seen:
                    seen.add(t)
                    queue.append(t)
        return seen

    def to_dict(self) -> dict:
        return {
            "alphabet": list(self.alphabet),
            "transitions": [list(row) for row in self.transitions],
            "accepting": list(self.accepting),
            "initial": self.initial,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DFA":
        return cls(
            alphabet=tuple(int(x) for x in data["alphabet"]),
            transitions=tuple(tuple(int(x) for x in row) for row in data["transitions"]),
            accepting=tuple(bool(x) for x in data["accepting"]),
            initial=int(data.get("initial", 0)),
        )


def canonicalize(dfa: DFA) -> DFA:
    """Remove unreachable states and rename by BFS from the initial state."""
    mapping: dict[int, int] = {dfa.initial: 0}
    order = [dfa.initial]
    queue = deque([dfa.initial])
    while queue:
        s = queue.popleft()
        for a in dfa.alphabet:
            t = dfa.transitions[s][a]
            if t not in mapping:
                mapping[t] = len(mapping)
                order.append(t)
                queue.append(t)
    trans = []
    acc = []
    for old in order:
        trans.append(tuple(mapping[dfa.transitions[old][a]] for a in dfa.alphabet))
        acc.append(dfa.accepting[old])
    return DFA(dfa.alphabet, tuple(trans), tuple(acc), 0)


def minimize_dfa(dfa: DFA) -> DFA:
    dfa = canonicalize(dfa)
    states = set(range(dfa.n_states))
    accepting = {s for s in states if dfa.accepting[s]}
    rejecting = states - accepting
    partitions = [p for p in (accepting, rejecting) if p]
    changed = True
    while changed:
        changed = False
        state_to_part = {s: i for i, p in enumerate(partitions) for s in p}
        new_parts: list[set[int]] = []
        for part in partitions:
            buckets: dict[tuple[int, ...], set[int]] = {}
            for s in part:
                sig = tuple(state_to_part[dfa.transitions[s][a]] for a in dfa.alphabet)
                buckets.setdefault(sig, set()).add(s)
            new_parts.extend(buckets.values())
            if len(buckets) > 1:
                changed = True
        partitions = new_parts
    state_to_part = {s: i for i, p in enumerate(partitions) for s in p}
    initial_part = state_to_part[dfa.initial]
    trans = []
    acc = []
    for p in partitions:
        rep = next(iter(p))
        trans.append(tuple(state_to_part[dfa.transitions[rep][a]] for a in dfa.alphabet))
        acc.append(dfa.accepting[rep])
    return canonicalize(DFA(dfa.alphabet, tuple(trans), tuple(acc), initial_part))


def random_minimal_dfa(rng: random.Random, min_states: int = 3, max_states: int = 7) -> DFA:
    for _ in range(10_000):
        n = rng.randint(min_states, max_states)
        alphabet = (0, 1)
        trans = tuple(tuple(rng.randrange(n) for _ in alphabet) for _ in range(n))
        accepting = tuple(rng.random() < 0.5 for _ in range(n))
        if all(accepting) or not any(accepting):
            continue
        dfa = minimize_dfa(DFA(alphabet, trans, accepting, 0))
        if min_states <= dfa.n_states <= max_states and len(dfa.reachable_states()) == dfa.n_states:
            return dfa
    raise RuntimeError("Unable to generate a suitable minimal DFA")


class OpaqueTensorParent:
    """Exact recurrent tensor substrate with a private scrambled state basis."""

    def __init__(self, dfa: DFA, seed: int) -> None:
        self._dfa = dfa
        self._rng = np.random.default_rng(seed)
        q, _ = np.linalg.qr(self._rng.normal(size=(dfa.n_states, dfa.n_states)))
        self._encode = q.astype(np.float64)
        self._decode = self._encode.T
        mats = []
        for a in dfa.alphabet:
            m = np.zeros((dfa.n_states, dfa.n_states), dtype=np.float64)
            for s in range(dfa.n_states):
                m[s, dfa.transitions[s][a]] = 1.0
            mats.append(self._decode @ m @ self._encode)
        self._transition = tuple(mats)
        initial = np.zeros(dfa.n_states, dtype=np.float64)
        initial[dfa.initial] = 1.0
        self._initial = initial @ self._encode
        accept = np.asarray(dfa.accepting, dtype=np.float64)
        self._readout = self._decode @ accept
        self.query_count = 0

    def query(self, word: Sequence[int]) -> bool:
        self.query_count += 1
        z = self._initial.copy()
        for a in word:
            z = z @ self._transition[a]
        score = float(z @ self._readout)
        return score > 0.5


class MembershipOracle:
    def __init__(self, fn: Callable[[Word], bool]) -> None:
        self.fn = fn
        self.cache: dict[Word, bool] = {}
        self.calls = 0

    def __call__(self, word: Word) -> bool:
        if word not in self.cache:
            self.cache[word] = bool(self.fn(word))
            self.calls += 1
        return self.cache[word]


def words_up_to(alphabet: tuple[int, ...], max_len: int) -> Iterable[Word]:
    yield ()
    for length in range(1, max_len + 1):
        yield from product(alphabet, repeat=length)


@dataclass
class ExtractionStats:
    membership_queries: int
    rounds: int
    counterexamples: int
    observation_prefixes: int
    suffix_tests: int


class LStarExtractor:
    """L* learner using a bounded, hidden-behaviour counterexample search."""

    def __init__(
        self,
        alphabet: tuple[int, ...],
        membership: MembershipOracle,
        exhaustive_depth: int = 11,
        random_probes: int = 4000,
        random_max_len: int = 48,
        seed: int = 0,
    ) -> None:
        self.alphabet = alphabet
        self.mq = membership
        self.exhaustive_depth = exhaustive_depth
        rng = random.Random(seed)
        self.probes = [
            tuple(rng.choice(alphabet) for _ in range(rng.randint(0, random_max_len)))
            for _ in range(random_probes)
        ]
        self.S: list[Word] = [()]
        self.E: list[Word] = [()]
        self.rounds = 0
        self.counterexamples = 0

    def _row(self, prefix: Word) -> tuple[bool, ...]:
        return tuple(self.mq(prefix + suffix) for suffix in self.E)

    def _close_and_consistent(self) -> None:
        while True:
            rows = {self._row(s): s for s in self.S}
            added = False
            for s in list(self.S):
                for a in self.alphabet:
                    sa = s + (a,)
                    if self._row(sa) not in rows:
                        self.S.append(sa)
                        added = True
                        break
                if added:
                    break
            if added:
                continue

            for i, s1 in enumerate(self.S):
                for s2 in self.S[i + 1 :]:
                    if self._row(s1) != self._row(s2):
                        continue
                    for a in self.alphabet:
                        r1 = self._row(s1 + (a,))
                        r2 = self._row(s2 + (a,))
                        if r1 == r2:
                            continue
                        for idx, (v1, v2) in enumerate(zip(r1, r2)):
                            if v1 != v2:
                                candidate = (a,) + self.E[idx]
                                if candidate not in self.E:
                                    self.E.append(candidate)
                                added = True
                                break
                        if added:
                            break
                    if added:
                        break
                if added:
                    break
            if not added:
                return

    def _hypothesis(self) -> DFA:
        unique_rows: dict[tuple[bool, ...], int] = {}
        reps: list[Word] = []
        for s in self.S:
            row = self._row(s)
            if row not in unique_rows:
                unique_rows[row] = len(unique_rows)
                reps.append(s)
        trans = []
        acc = []
        for rep in reps:
            acc.append(self.mq(rep))
            trans.append(tuple(unique_rows[self._row(rep + (a,))] for a in self.alphabet))
        initial = unique_rows[self._row(())]
        return canonicalize(DFA(self.alphabet, tuple(trans), tuple(acc), initial))

    def _counterexample(self, candidate: DFA) -> Word | None:
        for word in words_up_to(self.alphabet, self.exhaustive_depth):
            if candidate.accepts(word) != self.mq(word):
                return word
        for word in self.probes:
            if candidate.accepts(word) != self.mq(word):
                return word
        return None

    def extract(self, max_rounds: int = 100) -> tuple[DFA, ExtractionStats]:
        for _ in range(max_rounds):
            self.rounds += 1
            self._close_and_consistent()
            candidate = self._hypothesis()
            ce = self._counterexample(candidate)
            if ce is None:
                stats = ExtractionStats(
                    membership_queries=self.mq.calls,
                    rounds=self.rounds,
                    counterexamples=self.counterexamples,
                    observation_prefixes=len(self.S),
                    suffix_tests=len(self.E),
                )
                return minimize_dfa(candidate), stats
            self.counterexamples += 1
            for i in range(len(ce) + 1):
                prefix = ce[:i]
                if prefix not in self.S:
                    self.S.append(prefix)
        raise RuntimeError("L* did not converge")


def exact_equivalence(a: DFA, b: DFA) -> tuple[bool, Word | None]:
    if a.alphabet != b.alphabet:
        return False, ()
    queue = deque([(a.initial, b.initial, ())])
    seen = {(a.initial, b.initial)}
    while queue:
        sa, sb, w = queue.popleft()
        if a.accepting[sa] != b.accepting[sb]:
            return False, w
        for symbol in a.alphabet:
            na = a.transitions[sa][symbol]
            nb = b.transitions[sb][symbol]
            pair = (na, nb)
            if pair not in seen:
                seen.add(pair)
                queue.append((na, nb, w + (symbol,)))
    return True, None


@dataclass(frozen=True)
class CognitivePassport:
    version: str
    alphabet: tuple[int, ...]
    transitions: tuple[tuple[int, ...], ...]
    accepting: tuple[bool, ...]
    initial: int
    provenance: dict

    @classmethod
    def from_dfa(cls, dfa: DFA, provenance: dict) -> "CognitivePassport":
        dfa = canonicalize(minimize_dfa(dfa))
        return cls("metamorphosis-passport/1", dfa.alphabet, dfa.transitions, dfa.accepting, dfa.initial, provenance)

    def dfa(self) -> DFA:
        return DFA(self.alphabet, self.transitions, self.accepting, self.initial)

    def to_json(self) -> str:
        data = {
            "version": self.version,
            "alphabet": list(self.alphabet),
            "transitions": [list(x) for x in self.transitions],
            "accepting": list(self.accepting),
            "initial": self.initial,
            "provenance": self.provenance,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> "CognitivePassport":
        d = json.loads(raw)
        return cls(
            d["version"], tuple(d["alphabet"]), tuple(tuple(r) for r in d["transitions"]),
            tuple(d["accepting"]), d["initial"], d["provenance"]
        )


class SymbolicSubstrate:
    def __init__(self, passport: CognitivePassport) -> None:
        self.dfa = passport.dfa()

    def accepts(self, word: Sequence[int]) -> bool:
        return self.dfa.accepts(word)


class GraphSubstrate:
    def __init__(self, passport: CognitivePassport) -> None:
        self.initial = passport.initial
        self.accepting = set(i for i, x in enumerate(passport.accepting) if x)
        self.edges = {(s, a): t for s, row in enumerate(passport.transitions) for a, t in enumerate(row)}

    def accepts(self, word: Sequence[int]) -> bool:
        node = self.initial
        for symbol in word:
            node = self.edges[(node, int(symbol))]
        return node in self.accepting


class MatrixRecurrentSubstrate:
    def __init__(self, passport: CognitivePassport) -> None:
        n = len(passport.transitions)
        self.matrices = []
        for a in passport.alphabet:
            m = torch.zeros((n, n), dtype=torch.float64)
            for s, row in enumerate(passport.transitions):
                m[s, row[a]] = 1.0
            self.matrices.append(m)
        self.h0 = torch.zeros(n, dtype=torch.float64)
        self.h0[passport.initial] = 1.0
        self.readout = torch.tensor(passport.accepting, dtype=torch.float64)

    def accepts(self, word: Sequence[int]) -> bool:
        h = self.h0.clone()
        for symbol in word:
            h = h @ self.matrices[int(symbol)]
        return bool((h @ self.readout).item() > 0.5)

    def batch_accepts(self, words: Sequence[Word]) -> list[bool]:
        if not words:
            return []
        out = [False] * len(words)
        by_len: dict[int, list[tuple[int, Word]]] = {}
        for i, word in enumerate(words):
            by_len.setdefault(len(word), []).append((i, word))
        for length, items in by_len.items():
            h = self.h0.repeat(len(items), 1)
            if length:
                tokens = torch.tensor([w for _, w in items], dtype=torch.long)
                for t in range(length):
                    next_h = torch.zeros_like(h)
                    for a, matrix in enumerate(self.matrices):
                        mask = tokens[:, t] == a
                        if mask.any():
                            next_h[mask] = h[mask] @ matrix
                    h = next_h
            values = (h @ self.readout) > 0.5
            for (idx, _), value in zip(items, values.tolist()):
                out[idx] = bool(value)
        return out


class CellularWaveSubstrate:
    def __init__(self, passport: CognitivePassport) -> None:
        self.passport = passport
        self.transition = torch.tensor(passport.transitions, dtype=torch.long)
        self.accepting = torch.tensor(passport.accepting, dtype=torch.bool)

    def accepts(self, word: Sequence[int]) -> bool:
        if not word:
            return bool(self.accepting[self.passport.initial].item())
        state = self.passport.initial
        for symbol in word:
            state = int(self.transition[state, int(symbol)].item())
        return bool(self.accepting[state].item())

    def batch_accepts(self, words: Sequence[Word]) -> list[bool]:
        if not words:
            return []
        out = [False] * len(words)
        by_len: dict[int, list[tuple[int, Word]]] = {}
        for i, word in enumerate(words):
            by_len.setdefault(len(word), []).append((i, word))
        for length, items in by_len.items():
            state = torch.full((len(items),), self.passport.initial, dtype=torch.long)
            if length:
                tokens = torch.tensor([w for _, w in items], dtype=torch.long)
                for tick in range(length):
                    state = self.transition[state, tokens[:, tick]]
            values = self.accepting[state]
            for (idx, _), value in zip(items, values.tolist()):
                out[idx] = bool(value)
        return out


def random_words(rng: random.Random, alphabet: tuple[int, ...], count: int, min_len: int, max_len: int) -> list[Word]:
    return [tuple(rng.choice(alphabet) for _ in range(rng.randint(min_len, max_len))) for _ in range(count)]


def substrate_agreement(passport: CognitivePassport, oracle: Callable[[Word], bool], words: Iterable[Word]) -> dict[str, float]:
    word_list = list(words)
    truths = [oracle(w) for w in word_list]
    symbolic = SymbolicSubstrate(passport)
    graph = GraphSubstrate(passport)
    matrix = MatrixRecurrentSubstrate(passport)
    cellular = CellularWaveSubstrate(passport)
    predictions = {
        "symbolic": [symbolic.accepts(w) for w in word_list],
        "graph": [graph.accepts(w) for w in word_list],
        "matrix_recurrent": matrix.batch_accepts(word_list),
        "cellular_wave": cellular.batch_accepts(word_list),
    }
    return {
        name: sum(int(p == t) for p, t in zip(preds, truths)) / max(1, len(truths))
        for name, preds in predictions.items()
    }
