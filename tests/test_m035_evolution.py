"""Duplication is neutral at birth and capacity-increasing. Both must hold.

The whole mechanism rests on a mutation that selection cannot see. If duplication changed
behaviour it would be an ordinary edit, exposed to selection before it could drift, and
the analogy to gene duplication would be decoration rather than mechanism.

The ceiling it lifts is measured in `results/M035_EVOLUTION.md`: of 53,280 atom
applications, 18,540 changed the state count and none grew it.
"""

from __future__ import annotations

import pytest

from metamorphosis.m012b_dfa import exact_equivalence, random_minimal_dfa
from metamorphosis.m017_lab import make_out_of_language_target
from metamorphosis.m035_evolution import (
    ATOMS,
    Organism,
    agreement,
    duplicable_states,
    duplicate_state,
    growth_is_necessary,
    minimal_criterion_survivors,
    required_states_lower_bound,
)
from metamorphosis.structural import apply_atoms, enumerate_words, normalize_dfa


def _bases(count: int = 8):
    return [
        normalize_dfa(random_minimal_dfa(seed * 7919 + 11, 4, 6)) for seed in range(count)
    ]


def test_duplication_preserves_behaviour_exactly():
    """Neutral at birth: selection cannot distinguish parent from child."""

    for base in _bases():
        twin = duplicate_state(base, index=duplicable_states(base)[0])
        assert twin is not None
        equal, witness = exact_equivalence(base, twin)
        assert equal, f"duplication changed behaviour, witness {witness}"


def test_duplication_increases_the_state_count():
    for base in _bases():
        twin = duplicate_state(base, index=duplicable_states(base)[0])
        assert twin is not None
        assert twin.n_states == base.n_states + 1


def test_atoms_alone_never_increase_the_state_count():
    """The ceiling this operator exists to lift."""

    for base in _bases(4):
        for atom in ATOMS:
            out = apply_atoms(base, [atom])
            if out is None:
                continue
            assert normalize_dfa(out).n_states <= base.n_states


def test_duplication_is_deterministic_and_addressable():
    base = _bases(1)[0]
    a = duplicate_state(base, index=duplicable_states(base)[0], incoming=0)
    b = duplicate_state(base, index=duplicable_states(base)[0], incoming=0)
    assert a is not None and b is not None
    assert a.transitions == b.transitions
    assert a.accepting == b.accepting


def test_a_different_incoming_edge_gives_a_different_body():
    base = _bases(1)[0]
    bodies = {
        duplicate_state(base, index=duplicable_states(base)[0], incoming=k).transitions
        for k in range(4)
        if duplicate_state(base, index=duplicable_states(base)[0], incoming=k) is not None
    }
    assert len(bodies) >= 1


def test_an_out_of_range_index_is_refused():
    base = _bases(1)[0]
    assert duplicate_state(base, index=base.n_states) is None
    assert duplicate_state(base, index=-1) is None


def test_structural_cost_grows_with_size():
    base = _bases(1)[0]
    parent = Organism(body=base)
    twin = duplicate_state(base, index=duplicable_states(base)[0])
    assert twin is not None
    child = Organism(body=twin, duplications=1)
    assert child.structural_cost() > parent.structural_cost()


def test_minimal_criterion_keeps_everyone_above_the_bar():
    """Not a ranking. Collapsing onto the best destroys the redundancy drift needs."""

    bases = _bases(4)
    population = [(Organism(body=b), score) for b, score in zip(bases, (5, 9, 3, 9))]
    survivors = minimal_criterion_survivors(population, threshold=5, capacity=10)
    assert len(survivors) == 3


def test_at_equal_agreement_the_smaller_organism_survives():
    """What stops growth from being free."""

    base = _bases(1)[0]
    twin = duplicate_state(base, index=duplicable_states(base)[0])
    assert twin is not None
    small, large = Organism(body=base), Organism(body=twin, duplications=1)
    survivors = minimal_criterion_survivors(
        [(large, 7), (small, 7)], threshold=1, capacity=1
    )
    assert survivors[0].size == small.size


def test_agreement_is_an_integer_over_a_fixed_word_set():
    base = _bases(1)[0]
    words = enumerate_words(4)
    score = agreement(base, base, words)
    assert isinstance(score, int)
    assert score == len(words)


def test_the_required_state_bound_is_sound():
    """It may never demand growth that is not needed. Under-claiming is acceptable."""

    words = enumerate_words(5)
    for base in _bases(6):
        evidence = {tuple(w): base.accepts(tuple(w)) for w in words}
        assert required_states_lower_bound(evidence) <= base.n_states


def test_an_organism_never_demands_growth_against_its_own_behaviour():
    words = enumerate_words(5)
    for base in _bases(6):
        evidence = {tuple(w): base.accepts(tuple(w)) for w in words}
        assert not growth_is_necessary(Organism(body=base), evidence)


def test_growth_is_diagnosed_for_a_target_that_needs_more_states():
    """The organism proves its own insufficiency without seeing the target."""

    words = enumerate_words(6)
    diagnosed = 0
    for index in range(6):
        base = normalize_dfa(random_minimal_dfa(50_000 + index * 7919, 4, 6))
        target = make_out_of_language_target(base, 51_000 + index * 7919)
        evidence = {tuple(w): target.accepts(tuple(w)) for w in words}
        diagnosed += growth_is_necessary(Organism(body=base), evidence)
    assert diagnosed > 0
