from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
import random
import statistics
from typing import Iterable, Protocol, Sequence

from .m012b_dfa import DFA, canonicalize, exact_equivalence, minimize_dfa


LEARNABLE_SCHEMAS = (
    "acceptance_flip",
    "transition_redirect",
    "two_independent_local_edits",
)
GENERIC_SCHEMAS = LEARNABLE_SCHEMAS + (
    "two_acceptance_flips",
    "double_transition_redirect",
)


class BehavioralOracle(Protocol):
    def query(self, word: tuple[int, ...]) -> bool: ...


@dataclass(frozen=True)
class EditHypothesis:
    kind: str
    args: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "args": list(self.args)}


@dataclass(frozen=True)
class CandidateUpdate:
    dfa: DFA
    hypothesis: EditHypothesis


@dataclass(frozen=True)
class PlasticityPassport:
    version: str
    hypothesis_language: tuple[str, ...]
    learned_prior: tuple[tuple[str, float], ...]
    query_policy: str
    length_penalty: float
    repeat_queries: int
    max_pair_samples: int
    max_candidates: int
    uncertainty_representation: str
    abstention_rule: str
    consolidation_rule: str
    development_provenance_sha256: str

    def prior_map(self) -> dict[str, float]:
        return dict(self.learned_prior)

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": self.version,
                "hypothesis_language": list(self.hypothesis_language),
                "learned_prior": [[name, value] for name, value in self.learned_prior],
                "query_policy": self.query_policy,
                "length_penalty": self.length_penalty,
                "repeat_queries": self.repeat_queries,
                "max_pair_samples": self.max_pair_samples,
                "max_candidates": self.max_candidates,
                "uncertainty_representation": self.uncertainty_representation,
                "abstention_rule": self.abstention_rule,
                "consolidation_rule": self.consolidation_rule,
                "development_provenance_sha256": self.development_provenance_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "PlasticityPassport":
        data = json.loads(raw)
        if data.get("version") != "m014b-plasticity-passport/1":
            raise ValueError("unsupported plasticity passport version")
        return PlasticityPassport(
            version=str(data["version"]),
            hypothesis_language=tuple(str(value) for value in data["hypothesis_language"]),
            learned_prior=tuple((str(name), float(value)) for name, value in data["learned_prior"]),
            query_policy=str(data["query_policy"]),
            length_penalty=float(data["length_penalty"]),
            repeat_queries=int(data["repeat_queries"]),
            max_pair_samples=int(data["max_pair_samples"]),
            max_candidates=int(data["max_candidates"]),
            uncertainty_representation=str(data["uncertainty_representation"]),
            abstention_rule=str(data["abstention_rule"]),
            consolidation_rule=str(data["consolidation_rule"]),
            development_provenance_sha256=str(data["development_provenance_sha256"]),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class UpdateInference:
    status: str
    reason: str
    updated_passport: DFA | None
    selected_hypothesis: EditHypothesis | None
    raw_oracle_calls: int
    unique_queries: int
    initial_candidates: int
    remaining_candidates: int
    initial_entropy_bits: float
    final_entropy_bits: float
    query_trace: tuple[dict[str, object], ...]


def dfa_accepts(dfa: DFA, word: Iterable[int]) -> bool:
    state = dfa.initial
    for symbol in word:
        state = dfa.transitions[state][int(symbol)]
    return bool(dfa.accepting[state])


def normalize_dfa(dfa: DFA) -> DFA:
    return canonicalize(minimize_dfa(dfa))


def dfa_key(dfa: DFA) -> tuple[object, ...]:
    normalized = normalize_dfa(dfa)
    return (
        tuple(normalized.alphabet),
        tuple(tuple(row) for row in normalized.transitions),
        tuple(bool(value) for value in normalized.accepting),
        int(normalized.initial),
    )


def apply_hypothesis(base: DFA, hypothesis: EditHypothesis) -> DFA:
    transitions = [list(row) for row in base.transitions]
    accepting = list(base.accepting)
    kind = hypothesis.kind
    args = hypothesis.args
    if kind == "acceptance_flip":
        (state,) = args
        accepting[state] = not accepting[state]
    elif kind == "transition_redirect":
        state, symbol, target = args
        transitions[state][symbol] = target
    elif kind == "two_independent_local_edits":
        accept_state, transition_state, symbol, target = args
        accepting[accept_state] = not accepting[accept_state]
        transitions[transition_state][symbol] = target
    elif kind == "two_acceptance_flips":
        first, second = args
        accepting[first] = not accepting[first]
        accepting[second] = not accepting[second]
    elif kind == "double_transition_redirect":
        first_state, first_symbol, first_target, second_state, second_symbol, second_target = args
        transitions[first_state][first_symbol] = first_target
        transitions[second_state][second_symbol] = second_target
    else:
        raise ValueError(f"unsupported edit hypothesis: {kind}")
    return DFA(
        tuple(base.alphabet),
        tuple(tuple(int(value) for value in row) for row in transitions),
        tuple(bool(value) for value in accepting),
        int(base.initial),
    )


def infer_demonstrated_schema(base: DFA, updated: DFA) -> str:
    if len(base.transitions) != len(updated.transitions):
        raise ValueError("state-changing demonstration is outside M014b language")
    acceptance_changes = [
        index for index, (before, after) in enumerate(zip(base.accepting, updated.accepting))
        if bool(before) != bool(after)
    ]
    transition_changes = [
        (state, symbol)
        for state, (before_row, after_row) in enumerate(zip(base.transitions, updated.transitions))
        for symbol, (before, after) in enumerate(zip(before_row, after_row))
        if int(before) != int(after)
    ]
    if len(acceptance_changes) == 1 and not transition_changes:
        return "acceptance_flip"
    if not acceptance_changes and len(transition_changes) == 1:
        return "transition_redirect"
    if len(acceptance_changes) == 1 and len(transition_changes) == 1:
        return "two_independent_local_edits"
    raise ValueError("demonstration is outside the learnable M014b schema language")


def _add_candidate(
    store: dict[tuple[object, ...], CandidateUpdate],
    base_key: tuple[object, ...],
    base: DFA,
    hypothesis: EditHypothesis,
) -> None:
    candidate = normalize_dfa(apply_hypothesis(base, hypothesis))
    key = dfa_key(candidate)
    if key != base_key:
        store.setdefault(key, CandidateUpdate(candidate, hypothesis))


def generate_candidates(
    inherited: DFA,
    schemas: Sequence[str],
    max_candidates: int = 5000,
) -> tuple[CandidateUpdate, ...]:
    base = normalize_dfa(inherited)
    base_key = dfa_key(base)
    states = range(len(base.transitions))
    positions = [(state, symbol) for state in states for symbol in (0, 1)]
    store: dict[tuple[object, ...], CandidateUpdate] = {}

    if "acceptance_flip" in schemas:
        for state in states:
            _add_candidate(store, base_key, base, EditHypothesis("acceptance_flip", (state,)))

    if "transition_redirect" in schemas:
        for state, symbol in positions:
            current = base.transitions[state][symbol]
            for target in states:
                if target != current:
                    _add_candidate(
                        store,
                        base_key,
                        base,
                        EditHypothesis("transition_redirect", (state, symbol, target)),
                    )

    if "two_independent_local_edits" in schemas:
        for accept_state in states:
            for transition_state, symbol in positions:
                if accept_state == transition_state:
                    continue
                current = base.transitions[transition_state][symbol]
                for target in states:
                    if target != current:
                        _add_candidate(
                            store,
                            base_key,
                            base,
                            EditHypothesis(
                                "two_independent_local_edits",
                                (accept_state, transition_state, symbol, target),
                            ),
                        )

    if "two_acceptance_flips" in schemas:
        for first, second in itertools.combinations(states, 2):
            _add_candidate(
                store,
                base_key,
                base,
                EditHypothesis("two_acceptance_flips", (first, second)),
            )

    if "double_transition_redirect" in schemas:
        for first_index, (first_state, first_symbol) in enumerate(positions):
            first_current = base.transitions[first_state][first_symbol]
            for second_state, second_symbol in positions[first_index + 1 :]:
                second_current = base.transitions[second_state][second_symbol]
                for first_target in states:
                    if first_target == first_current:
                        continue
                    for second_target in states:
                        if second_target == second_current:
                            continue
                        _add_candidate(
                            store,
                            base_key,
                            base,
                            EditHypothesis(
                                "double_transition_redirect",
                                (
                                    first_state,
                                    first_symbol,
                                    first_target,
                                    second_state,
                                    second_symbol,
                                    second_target,
                                ),
                            ),
                        )
                        if len(store) >= max_candidates:
                            return tuple(store.values())

    return tuple(store.values())


def distinguishing_word(first: DFA, second: DFA) -> tuple[int, ...] | None:
    queue: deque[tuple[int, int, tuple[int, ...]]] = deque(
        [(first.initial, second.initial, ())]
    )
    seen = {(first.initial, second.initial)}
    while queue:
        first_state, second_state, word = queue.popleft()
        if bool(first.accepting[first_state]) != bool(second.accepting[second_state]):
            return word
        for symbol in (0, 1):
            next_first = first.transitions[first_state][symbol]
            next_second = second.transitions[second_state][symbol]
            pair = (next_first, next_second)
            if pair not in seen:
                seen.add(pair)
                queue.append((next_first, next_second, word + (symbol,)))
    return None


def _entropy(weights: Sequence[float]) -> float:
    total = sum(weights)
    if total <= 0:
        return 0.0
    return -sum(
        (weight / total) * math.log2(weight / total)
        for weight in weights
        if weight > 0
    )


def _candidate_weights(
    candidates: Sequence[CandidateUpdate],
    passport: PlasticityPassport,
) -> list[float]:
    counts = Counter(candidate.hypothesis.kind for candidate in candidates)
    priors = passport.prior_map()
    weights = [
        max(priors.get(candidate.hypothesis.kind, 0.0), 1e-12)
        / max(counts[candidate.hypothesis.kind], 1)
        for candidate in candidates
    ]
    total = sum(weights)
    return [weight / total for weight in weights]


def _fixed_query_words(max_length: int = 8) -> tuple[tuple[int, ...], ...]:
    return tuple(
        word
        for length in range(max_length + 1)
        for word in itertools.product((0, 1), repeat=length)
    )


def _fixed_query_signature(dfa: DFA, max_length: int = 8) -> tuple[bool, ...]:
    outputs = [bool(dfa.accepting[dfa.initial])]
    frontier = [dfa.initial]
    for _ in range(max_length):
        next_frontier: list[int] = []
        for state in frontier:
            next_frontier.append(dfa.transitions[state][0])
            next_frontier.append(dfa.transitions[state][1])
        outputs.extend(bool(dfa.accepting[state]) for state in next_frontier)
        frontier = next_frontier
    return tuple(outputs)


def _witness_pool(
    candidates: Sequence[CandidateUpdate],
    asked: set[tuple[int, ...]],
    rng: random.Random,
    max_pair_samples: int,
) -> tuple[tuple[int, ...], ...]:
    count = len(candidates)
    all_pair_count = count * (count - 1) // 2
    if all_pair_count <= max_pair_samples:
        pairs = list(itertools.combinations(range(count), 2))
    else:
        selected: set[tuple[int, int]] = set()
        while len(selected) < max_pair_samples:
            first = rng.randrange(count)
            second = rng.randrange(count - 1)
            if second >= first:
                second += 1
            selected.add((min(first, second), max(first, second)))
        pairs = sorted(selected)
    words: set[tuple[int, ...]] = set()
    for first, second in pairs:
        word = distinguishing_word(candidates[first].dfa, candidates[second].dfa)
        if word is not None and word not in asked:
            words.add(word)
    return tuple(sorted(words, key=lambda word: (len(word), word)))


def identify_update(
    inherited: DFA,
    oracle: BehavioralOracle,
    passport: PlasticityPassport,
    *,
    query_budget: int = 192,
    policy: str | None = None,
    search_seed: int = 0,
) -> UpdateInference:
    candidates = list(
        generate_candidates(
            inherited,
            passport.hypothesis_language,
            passport.max_candidates,
        )
    )
    initial_candidates = len(candidates)
    if not candidates:
        return UpdateInference(
            "abstained", "empty_hypothesis_language", None, None, 0, 0, 0, 0,
            0.0, 0.0, (),
        )
    weights = _candidate_weights(candidates, passport)
    initial_entropy = _entropy(weights)
    asked: set[tuple[int, ...]] = set()
    trace: list[dict[str, object]] = []
    raw_calls = 0
    selected_policy = policy or passport.query_policy
    rng = random.Random(search_seed)
    fixed_words = _fixed_query_words(8)
    fixed_word_index = {word: index for index, word in enumerate(fixed_words)}
    fixed_signatures = {
        id(candidate): _fixed_query_signature(candidate.dfa, 8)
        for candidate in candidates
    }

    def predicted(candidate: CandidateUpdate, word: tuple[int, ...]) -> bool:
        index = fixed_word_index.get(word)
        if index is not None:
            return fixed_signatures[id(candidate)][index]
        return dfa_accepts(candidate.dfa, word)

    while len(candidates) > 1:
        if raw_calls + passport.repeat_queries > query_budget:
            return UpdateInference(
                "abstained", "update_query_budget_exhausted", None, None,
                raw_calls, len(asked), initial_candidates, len(candidates),
                initial_entropy, _entropy(weights), tuple(trace),
            )
        words = tuple(
            word
            for index, word in enumerate(fixed_words)
            if word not in asked
            and any(fixed_signatures[id(candidate)][index] for candidate in candidates)
            and not all(fixed_signatures[id(candidate)][index] for candidate in candidates)
        )
        if not words:
            words = _witness_pool(candidates, asked, rng, passport.max_pair_samples)
        if not words:
            reference = candidates[0]
            if all(exact_equivalence(reference.dfa, candidate.dfa)[0] for candidate in candidates[1:]):
                return UpdateInference(
                    "success", "equivalent_version_space_collapsed", reference.dfa,
                    reference.hypothesis, raw_calls, len(asked), initial_candidates,
                    len(candidates), initial_entropy, _entropy(weights), tuple(trace),
                )
            return UpdateInference(
                "abstained", "no_distinguishing_query_available", None, None,
                raw_calls, len(asked), initial_candidates, len(candidates),
                initial_entropy, _entropy(weights), tuple(trace),
            )

        if selected_policy == "random":
            word = rng.choice(words)
            score = None
        else:
            parent_entropy = _entropy(weights)
            best_ranking = None
            best_word = None
            best_score = None
            for candidate_word in words:
                zero_pairs = [
                    (candidate, weight)
                    for candidate, weight in zip(candidates, weights)
                    if not predicted(candidate, candidate_word)
                ]
                one_pairs = [
                    (candidate, weight)
                    for candidate, weight in zip(candidates, weights)
                    if predicted(candidate, candidate_word)
                ]
                zero_weights = [weight for _, weight in zero_pairs]
                one_weights = [weight for _, weight in one_pairs]
                probability_zero = sum(zero_weights)
                probability_one = sum(one_weights)
                posterior_entropy = (
                    probability_zero * _entropy(zero_weights)
                    + probability_one * _entropy(one_weights)
                )
                information_gain = parent_entropy - posterior_entropy
                candidate_score = information_gain - passport.length_penalty * len(candidate_word)
                ranking = (
                    -max(len(zero_pairs), len(one_pairs)),
                    -max(probability_zero, probability_one),
                    candidate_score,
                    -len(candidate_word),
                    tuple(-value for value in candidate_word),
                )
                if best_ranking is None or ranking > best_ranking:
                    best_ranking = ranking
                    best_word = candidate_word
                    best_score = candidate_score
            assert best_word is not None
            word = best_word
            score = best_score

        answers = [bool(oracle.query(word)) for _ in range(passport.repeat_queries)]
        raw_calls += passport.repeat_queries
        asked.add(word)
        if len(set(answers)) != 1:
            return UpdateInference(
                "abstained", "behavioral_oracle_inconsistent", None, None,
                raw_calls, len(asked), initial_candidates, len(candidates),
                initial_entropy, _entropy(weights), tuple(trace),
            )
        answer = answers[0]
        before = len(candidates)
        filtered = [
            (candidate, weight)
            for candidate, weight in zip(candidates, weights)
            if predicted(candidate, word) == answer
        ]
        if not filtered:
            return UpdateInference(
                "abstained", "target_outside_hypothesis_language", None, None,
                raw_calls, len(asked), initial_candidates, 0,
                initial_entropy, 0.0, tuple(trace),
            )
        candidates = [candidate for candidate, _ in filtered]
        weights = [weight for _, weight in filtered]
        total = sum(weights)
        weights = [weight / total for weight in weights]
        trace.append(
            {
                "word": list(word),
                "answer": answer,
                "candidates_before": before,
                "candidates_after": len(candidates),
                "entropy_after_bits": _entropy(weights),
                "selection_score": score,
            }
        )

    selected = candidates[0]
    return UpdateInference(
        "success", "unique_update_identified", selected.dfa, selected.hypothesis,
        raw_calls, len(asked), initial_candidates, 1,
        initial_entropy, 0.0, tuple(trace),
    )


def _demonstration_digest(demonstrations: Sequence[tuple[DFA, DFA]]) -> str:
    payload = [
        {"before": dfa_key(before), "after": dfa_key(after)}
        for before, after in demonstrations
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class _TrainingOracle:
    def __init__(self, target: DFA) -> None:
        self.target = target

    def query(self, word: tuple[int, ...]) -> bool:
        return dfa_accepts(self.target, word)


def train_plasticity_passport(
    demonstrations: Sequence[tuple[DFA, DFA]],
) -> PlasticityPassport:
    if not demonstrations:
        raise ValueError("at least one development demonstration is required")
    kinds = [infer_demonstrated_schema(before, after) for before, after in demonstrations]
    counts = Counter(kinds)
    schemas = tuple(schema for schema in LEARNABLE_SCHEMAS if counts[schema] > 0)
    total = sum(counts.values())
    prior = tuple((schema, counts[schema] / total) for schema in schemas)
    digest = _demonstration_digest(demonstrations)

    best_penalty = 0.0

    return PlasticityPassport(
        "m014b-plasticity-passport/1",
        schemas,
        prior,
        "active_minimax_information_gain",
        best_penalty,
        2,
        1024,
        5000,
        "normalized_version_space_entropy_bits",
        "abstain_on_inconsistency_empty_or_unresolved_version_space",
        "canonical_minimal_updated_behavioral_passport",
        digest,
    )


def generic_no_passport_baseline() -> PlasticityPassport:
    uniform = 1.0 / len(GENERIC_SCHEMAS)
    return PlasticityPassport(
        "m014b-plasticity-passport/1",
        GENERIC_SCHEMAS,
        tuple((schema, uniform) for schema in GENERIC_SCHEMAS),
        "active_minimax_information_gain",
        0.0,
        2,
        1024,
        5000,
        "normalized_version_space_entropy_bits",
        "abstain_on_inconsistency_empty_or_unresolved_version_space",
        "canonical_minimal_updated_behavioral_passport",
        "no-development-provenance",
    )
