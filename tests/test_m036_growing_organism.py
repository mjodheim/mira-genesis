"""M036 is a recorded negative. These tests pin why, so it is not rebuilt.

A single organism that diagnoses its own insufficiency, grows, and retries solves 2/8 of
the tasks its birth body provably cannot express. The population of M035, on the same
generator, solves 6/12. The compression of a population into one elegant lineage does not
work, and three separate attempts measured it.

What the attempt did establish is kept, because it is not obvious:

1. the growth atom is neutral at the instant it applies and increases capacity;
2. growth must live **inside** the search vocabulary, not run as a phase before it;
3. the Myhill–Nerode diagnosis is sound but too weak to gate growth on.
"""

from __future__ import annotations

from metamorphosis.m012b_dfa import exact_equivalence, random_minimal_dfa
from metamorphosis.m017_lab import BehavioralOracle, make_out_of_language_target
from metamorphosis.m036_growing_organism import (
    GrowingOrganism,
    OBSERVATION_WORDS,
    growing_library,
    required_states_lower_bound,
)
from metamorphosis.structural import (
    all_atoms,
    apply_atom,
    growth_atoms,
    normalize_dfa,
)


def _base(index: int):
    return normalize_dfa(random_minimal_dfa(50_000 + index * 7919, 4, 6))


def test_the_growth_atom_is_neutral_and_capacity_increasing():
    for index in range(6):
        base = _base(index)
        for atom in growth_atoms():
            grown = apply_atom(base, atom)
            if grown is None:
                continue
            assert grown.n_states == base.n_states + 1
            assert exact_equivalence(base, grown)[0]
            break


def test_ordinary_atoms_still_cannot_grow():
    """The ceiling the growth atom exists to lift, restated where it is used."""

    for index in range(4):
        base = _base(index)
        for atom in all_atoms():
            out = apply_atom(base, atom)
            if out is None:
                continue
            assert normalize_dfa(out).n_states <= base.n_states


def test_growth_is_in_the_search_vocabulary():
    """Measured: in the vocabulary 2/8, as a separate phase 0/8.

    A depth-3 trajectory can be edit -> grow -> edit only if growth is a symbol. Growing
    first and searching afterwards can only produce grow -> edit -> edit, which is
    strictly less expressive.
    """

    names = {symbol.name for symbol in growing_library()}
    assert any(name.startswith("g") for name in names)
    assert len(names) == len(all_atoms()) + len(growth_atoms())


def test_the_bound_is_sound_against_the_organism_s_own_behaviour():
    for index in range(6):
        base = _base(index)
        evidence = {word: base.accepts(word) for word in OBSERVATION_WORDS}
        assert required_states_lower_bound(evidence) <= base.n_states


def test_the_bound_understates_and_so_cannot_gate_growth():
    """Why failure, not diagnosis, triggers growth.

    On these cases the bound misses targets that genuinely require a larger body. Gating
    growth behind it suppressed exactly the episodes that needed it.
    """

    missed = 0
    for index in range(6):
        base = _base(index)
        target = make_out_of_language_target(base, 51_000 + index * 7919)
        assert target.n_states > base.n_states
        evidence = {word: target.accepts(word) for word in OBSERVATION_WORDS}
        if required_states_lower_bound(evidence) <= base.n_states:
            missed += 1
    assert missed > 0, "if the bound never missed, it could safely gate growth"


def test_the_organism_keeps_what_it_acquires():
    """A lineage, not a fresh start: the body carries across episodes."""

    base = _base(1)
    target = make_out_of_language_target(base, 51_000 + 1 * 7919)
    organism = GrowingOrganism(base, search_budget=200_000)
    before = organism.body.n_states

    result, _ = organism.live(BehavioralOracle(target))
    if result.status == "success":
        assert organism.record.solved == 1
        assert organism.body.n_states >= before
    assert organism.record.episodes == 1
