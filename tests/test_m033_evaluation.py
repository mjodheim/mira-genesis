from __future__ import annotations

from itertools import product

from metamorphosis.m012b_dfa import DFA, canonicalize, minimize_dfa
from metamorphosis.m033_evaluation import (
    exact_dfa_match,
    exhaustive_words,
    held_out_quality_per_mille,
)


def _two_state_dfas():
    for flat_transitions in product(range(2), repeat=4):
        transitions = (
            (flat_transitions[0], flat_transitions[1]),
            (flat_transitions[2], flat_transitions[3]),
        )
        for accepting in product((False, True), repeat=2):
            for initial in range(2):
                yield DFA((0, 1), transitions, accepting, initial)


def test_product_equivalence_agrees_with_minimal_canonical_ground_truth():
    dfas = tuple(_two_state_dfas())
    for left in dfas:
        left_minimal = canonicalize(minimize_dfa(left))
        for right in dfas:
            expected = left_minimal == canonicalize(minimize_dfa(right))
            assert exact_dfa_match(left, right) is expected


def test_held_out_quality_matches_direct_exhaustive_agreement():
    words = exhaustive_words((0, 1), 5)
    left = DFA((0, 1), ((0, 1), (1, 0)), (False, True), 0)
    right = DFA((0, 1), ((1, 0), (0, 1)), (False, True), 0)

    expected = (
        1000
        * sum(left.accepts(word) == right.accepts(word) for word in words)
    ) // len(words)
    assert held_out_quality_per_mille(left, right, words) == expected
    assert held_out_quality_per_mille(left, left, words) == 1000


def test_empty_held_out_surface_is_rejected():
    dfa = DFA((0, 1), ((0, 0),), (False,), 0)
    try:
        held_out_quality_per_mille(dfa, dfa, ())
    except ValueError as error:
        assert "at least one word" in str(error)
    else:
        raise AssertionError("empty held-out surface was accepted")
