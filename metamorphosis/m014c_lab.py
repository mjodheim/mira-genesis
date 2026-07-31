from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Mapping

from .m012b_dfa import DFA, random_minimal_dfa
from .m014c_meta import StructuralProgram, apply_program, dfa_key, generate_candidates, normalize_dfa


PROGRAM_LIBRARY: tuple[StructuralProgram, ...] = (
    StructuralProgram("flip_deep_accept", (("flip", "deepest_accepting"),), "flip"),
    StructuralProgram("flip_deep_reject", (("flip", "deepest_rejecting"),), "flip"),
    StructuralProgram("flip_hub_accept", (("flip", "max_indegree_accepting"),), "flip"),
    StructuralProgram("flip_hub_reject", (("flip", "max_indegree_rejecting"),), "flip"),
    StructuralProgram("redir_deep_accept_0_initial", (("redirect", "deepest_accepting", 0, "initial"),), "return"),
    StructuralProgram("redir_deep_reject_1_initial", (("redirect", "deepest_rejecting", 1, "initial"),), "return"),
    StructuralProgram("redir_hub_accept_1_deep_reject", (("redirect", "max_indegree_accepting", 1, "deepest_rejecting"),), "cross"),
    StructuralProgram("redir_hub_reject_0_deep_accept", (("redirect", "max_indegree_rejecting", 0, "deepest_accepting"),), "cross"),
    StructuralProgram("redir_initial_0_deep_accept", (("redirect", "initial", 0, "deepest_accepting"),), "expand"),
    StructuralProgram("redir_initial_1_deep_reject", (("redirect", "initial", 1, "deepest_rejecting"),), "expand"),
    StructuralProgram("combo_accept_return", (("flip", "deepest_accepting"), ("redirect", "max_indegree_rejecting", 1, "initial")), "combo"),
    StructuralProgram("combo_reject_expand", (("flip", "deepest_rejecting"), ("redirect", "initial", 0, "max_indegree_accepting")), "combo"),
)

DEVELOPMENT_PROFILES: Mapping[str, Mapping[str, int]] = {
    "dev-flip": {"flip": 9, "return": 2, "cross": 1, "expand": 1, "combo": 1},
    "dev-return": {"flip": 2, "return": 9, "cross": 2, "expand": 1, "combo": 1},
    "dev-cross": {"flip": 1, "return": 2, "cross": 9, "expand": 2, "combo": 1},
    "dev-mixed": {"flip": 3, "return": 3, "cross": 3, "expand": 3, "combo": 3},
}

HELD_OUT_PROFILES: Mapping[str, Mapping[str, int]] = {
    "held-expand": {"flip": 1, "return": 1, "cross": 2, "expand": 10, "combo": 2},
    "held-combo": {"flip": 1, "return": 2, "cross": 1, "expand": 2, "combo": 10},
    "held-shifted-return": {"flip": 3, "return": 8, "cross": 1, "expand": 4, "combo": 2},
}


@dataclass
class BehavioralOracle:
    target: DFA
    mode: str = "stable"
    alternate: DFA | None = None
    calls: int = 0

    def __post_init__(self) -> None:
        self._per_word: dict[tuple[int, ...], int] = {}

    def query(self, word: tuple[int, ...]) -> bool:
        self.calls += 1
        frozen = tuple(int(value) for value in word)
        self._per_word[frozen] = self._per_word.get(frozen, 0) + 1
        target = self.target
        if self.mode == "changing" and self.alternate is not None and self.calls > 10:
            target = self.alternate
        value = target.accepts(frozen)
        if self.mode == "alternating" and self._per_word[frozen] % 2 == 0:
            return not value
        return value

    def _audit_target(self) -> DFA:
        return self.target


def _weighted_program(rng: random.Random, profile: Mapping[str, int]) -> StructuralProgram:
    programs = [program for program in PROGRAM_LIBRARY if profile.get(program.group, 0) > 0]
    weights = [profile[program.group] for program in programs]
    return rng.choices(programs, weights=weights, k=1)[0]


def _equivalent_program_ids(base: DFA, target: DFA) -> list[str]:
    target_key = dfa_key(target)
    return [
        program.program_id
        for program in PROGRAM_LIBRARY
        if (candidate := apply_program(base, program)) is not None and dfa_key(candidate) == target_key
    ]


def generate_episode(
    profile: Mapping[str, int], seed: int, *, min_states: int = 5,
    max_states: int = 8, min_candidates: int = 7,
) -> tuple[DFA, DFA, StructuralProgram]:
    rng = random.Random(seed)
    for attempt in range(2048):
        base = normalize_dfa(random_minimal_dfa(
            seed ^ (0xC014_0000 + attempt * 7919),
            min_states=min_states, max_states=max_states,
        ))
        if len(generate_candidates(base, PROGRAM_LIBRARY)) < min_candidates:
            continue
        program = _weighted_program(rng, profile)
        target = apply_program(base, program)
        if target is not None and _equivalent_program_ids(base, target) == [program.program_id]:
            return base, target, program
    raise RuntimeError("unable to generate an ambiguous uniquely labelled structural episode")


def generate_environment_sequence(
    profile: Mapping[str, int], seed: int, episodes: int = 10, *,
    min_states: int = 5, max_states: int = 8, min_candidates: int = 7,
) -> tuple[tuple[DFA, DFA, StructuralProgram], ...]:
    return tuple(generate_episode(
        profile, seed ^ (0xE015_0000 + index * 104729),
        min_states=min_states, max_states=max_states, min_candidates=min_candidates,
    ) for index in range(episodes))


def development_demonstrations() -> tuple[tuple[DFA, DFA, str, str], ...]:
    rows: list[tuple[DFA, DFA, str, str]] = []
    for env_index, (environment_id, profile) in enumerate(DEVELOPMENT_PROFILES.items()):
        sequence = generate_environment_sequence(
            profile, 51_000 + env_index, episodes=18,
            min_states=4, max_states=7, min_candidates=6,
        )
        rows.extend((before, after, program.program_id, environment_id)
                    for before, after, program in sequence)
    return tuple(rows)


def generated_profile(seed: int, dominant_weight: int = 16, secondary_weight: int = 4) -> dict[str, int]:
    groups = sorted({program.group for program in PROGRAM_LIBRARY})
    rng = random.Random(seed)
    rng.shuffle(groups)
    profile = {group: 1 for group in groups}
    profile[groups[0]] = dominant_weight
    profile[groups[1]] = secondary_weight
    return profile


def make_out_of_library_target(base: DFA, seed: int) -> DFA:
    programs = [
        StructuralProgram("outside_triple_a", (("flip", "deepest_accepting"), ("redirect", "initial", 0, "deepest_rejecting"), ("redirect", "max_indegree_rejecting", 1, "initial")), "outside"),
        StructuralProgram("outside_triple_b", (("flip", "deepest_rejecting"), ("redirect", "initial", 1, "deepest_accepting"), ("redirect", "max_indegree_accepting", 0, "initial")), "outside"),
    ]
    random.Random(seed).shuffle(programs)
    library_keys = {dfa_key(candidate.dfa) for candidate in generate_candidates(base, PROGRAM_LIBRARY)}
    for program in programs:
        target = apply_program(base, program)
        if target is not None and dfa_key(target) not in library_keys:
            return target
    raise RuntimeError("unable to build an out-of-library structural target")
