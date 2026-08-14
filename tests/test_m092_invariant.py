"""The M092 expressive invariant, and the ways it is allowed to fail.

A soundness check that cannot fail proves nothing, so several of these tests deliberately break the
abstraction and require the break to be detected.
"""
from __future__ import annotations

import itertools
import random

import pytest

from metamorphosis.m090_language import (
    INPUT_COUNT, MAX_BODY_LENGTH, SLOT_COUNT, LanguageError, MetaLanguageState, execute, run_body,
)
from metamorphosis.m090_migration import INHERITED_DEFINITIONS, migrated_l0
from metamorphosis.m091_substrate import SIGNATURES, enumerate_candidate_bodies
from metamorphosis.m092_invariant import (
    GERM_VARIABLE, Germ, constant_poly, degree_bound, germ_binary, germ_constant,
    germ_matches_parity, germ_of_body, germ_of_program, germ_unary, invariant_manifest,
    poly_add, poly_degree, poly_evaluate, poly_multiply, poly_subtract, refute_parity,
    sign_threshold,
)
from scripts.audit_m092_design import ACQUIRED_CLAMP, inherited_l1


# --------------------------------------------------------------------------------- polynomials


def test_polynomial_arithmetic_is_canonical() -> None:
    assert poly_add((1, 2), (3, -2)) == (4,)          # trailing zero trimmed
    assert poly_subtract((5,), (5,)) == ()            # the zero polynomial is empty
    assert poly_multiply((0, 1), (0, 1)) == (0, 0, 1)  # x * x = x^2
    assert poly_degree(()) == -1
    assert poly_evaluate((1, 2, 3), 2) == 1 + 4 + 12


def test_sign_threshold_really_bounds_the_roots() -> None:
    rng = random.Random(4)
    for _ in range(2000):
        poly = tuple(rng.randint(-9, 9) for _ in range(rng.randint(1, 4)))
        while poly and poly[-1] == 0:
            poly = poly[:-1]
        if not poly:
            continue
        bound = sign_threshold(poly)
        expected = 1 if poly[-1] > 0 else -1
        for x in (bound, bound + 1, bound + 37, bound + 9001):
            value = poly_evaluate(poly, x)
            assert value != 0 and (1 if value > 0 else -1) == expected


# ------------------------------------------------------------------------------ M092-I soundness


def _bindings(signature):
    axes = []
    for kind in signature:
        axes.append(range(SLOT_COUNT) if kind == "slot" else range(INPUT_COUNT))
    return [tuple(row) for row in itertools.product(*axes)] if axes else [()]


def test_germ_is_exact_on_the_frozen_assembly_space() -> None:
    """Exhaustive at length three, which exercises max, mul, DUP and SWAP in combination."""

    checked = 0
    for signature in SIGNATURES:
        for body in enumerate_candidate_bodies(signature, 3):
            for arguments in _bindings(signature):
                other = {1: 3, 2: -4}
                inputs = [
                    GERM_VARIABLE if i == 0 else germ_constant(other.get(i, 0))
                    for i in range(INPUT_COUNT)
                ]
                initial = [0, 2, -3, 5]
                try:
                    germs = germ_of_body(
                        body, arguments, [germ_constant(v) for v in initial], inputs,
                    )
                except LanguageError:
                    continue
                threshold = max((g.threshold for g in germs), default=0)
                for step in (1, 5, 40):
                    x = threshold + step
                    concrete = run_body(
                        body, arguments, initial,
                        [x if i == 0 else other.get(i, 0) for i in range(INPUT_COUNT)],
                    )
                    assert [g.at(x) for g in germs] == list(concrete)
                    checked += 1
    assert checked > 10_000


def test_germ_and_interpreter_agree_about_refusals() -> None:
    """An abstraction that ran where the concrete interpreter refuses would compare two things."""

    for body in (
        (("BINOP", "add"),),                      # empty stack
        (("UNOP", "inc"),),                       # empty stack
        (("SWAP", None),),                        # one operand
        (("PUSH_SLOT", 99), ("STORE_SLOT", 0)),   # slot out of range
        tuple(("PUSH_CONST", 1) for _ in range(MAX_BODY_LENGTH + 1)),  # length bound
    ):
        with pytest.raises(LanguageError):
            run_body(body, (), [0] * SLOT_COUNT, [0] * INPUT_COUNT)
        with pytest.raises(LanguageError):
            germ_of_body(
                body, (), [germ_constant(0)] * SLOT_COUNT, [GERM_VARIABLE] * INPUT_COUNT,
            )


def test_max_is_decided_not_widened() -> None:
    """`max` returns one of its arguments' germs exactly, with a justified threshold."""

    left, right = Germ((0, 1)), Germ((10,))        # x versus 10
    combined = germ_binary("max", left, right)
    assert combined.polynomial == (0, 1)           # x wins eventually
    assert combined.threshold >= 10
    for x in (combined.threshold + 1, combined.threshold + 500):
        assert combined.at(x) == max(x, 10)


def test_composition_is_closed_over_the_real_extended_language() -> None:
    """The claim that makes a budget arm semantically negative rather than merely unlucky."""

    rng = random.Random(31)
    language = inherited_l1()
    for _ in range(120):
        program = []
        for _ in range(rng.randint(40, 160)):
            definition = rng.choice(list(language.primitives))
            arguments = []
            for kind in definition.parameter_kinds:
                if kind == "slot":
                    arguments.append(rng.randrange(SLOT_COUNT))
                elif kind == "input":
                    arguments.append(rng.randrange(INPUT_COUNT))
                elif kind == "const":
                    arguments.append(rng.choice((0, 1)))
                elif kind == "unary_op":
                    arguments.append(rng.choice(("inc", "dec", "neg", "double")))
            program.append((definition.primitive_id, tuple(arguments)))
        other = {1: rng.randint(-4, 4), 2: rng.randint(-4, 4)}
        germs = germ_of_program(program, language, 0, other)
        threshold = max(g.threshold for g in germs)
        for step in (1, 77, 2503):
            x = threshold + step
            concrete = execute(
                program, [x if i == 0 else other[i] for i in range(INPUT_COUNT)], language,
            )
            assert [g.at(x) for g in germs] == list(concrete)


# --------------------------------------------------------------------------- M092-P, and failure


def test_no_germ_matches_parity() -> None:
    for polynomial in ((), (0,), (1,), (0, 1), (1, 1), (0, 0, 1), (3, -2, 5), (0, 1, 0, 7)):
        assert not germ_matches_parity(Germ(polynomial))


def test_refutation_witnesses_are_above_the_threshold_and_opposite_parity() -> None:
    for polynomial, threshold in (((), 0), ((0, 1), 12), ((5,), 3), ((1, 0, 2), 40)):
        refutation = refute_parity(Germ(polynomial, threshold))
        assert refutation.witness_even > threshold
        assert refutation.witness_even % 2 == 0
        assert refutation.witness_odd == refutation.witness_even + 1
        germ = Germ(polynomial, threshold)
        assert not (
            germ.at(refutation.witness_even) == 0 and germ.at(refutation.witness_odd) == 1
        )


def test_the_soundness_check_can_fail() -> None:
    """Break `mul` and require the concrete cross-check to notice. Otherwise it proves nothing."""

    body = ((("PUSH_INPUT", 0)), ("DUP", None), ("BINOP", "mul"), ("STORE_SLOT", 0))
    inputs = [GERM_VARIABLE] + [germ_constant(0)] * (INPUT_COUNT - 1)
    good = germ_of_body(body, (), [germ_constant(0)] * SLOT_COUNT, inputs)
    x = 9
    assert good[0].at(x) == run_body(body, (), [0] * SLOT_COUNT, [x, 0, 0])[0] == 81

    spoiled = Germ(poly_add(good[0].polynomial, constant_poly(1)), good[0].threshold)
    assert spoiled.at(x) != run_body(body, (), [0] * SLOT_COUNT, [x, 0, 0])[0]


def test_parity_would_be_detected_if_it_were_reachable() -> None:
    """`germ_matches_parity` must be a live computation, not a hard-coded False.

    The constant germ 1 really does agree with `x mod 2` at the single odd sample `x = 1`, so a
    one-sample window must return True. Widening the window to two samples reaches an even `x` and
    the agreement collapses -- which is Corollary M092-P happening in miniature.
    """

    assert germ_matches_parity(Germ(constant_poly(1), 0), samples=1) is True
    assert germ_matches_parity(Germ(constant_poly(1), 0), samples=2) is False


# --------------------------------------------------------------------------------- bookkeeping


def test_degree_bound_is_stated_and_not_load_bearing() -> None:
    assert degree_bound(4, 1) == 16
    assert degree_bound(0, 5) == 0
    # the actual degree the evaluator computes is far below the bound
    body = (("PUSH_INPUT", 0), ("DUP", None), ("BINOP", "mul"), ("STORE_SLOT", 0))
    germs = germ_of_body(
        body, (), [germ_constant(0)] * SLOT_COUNT,
        [GERM_VARIABLE] + [germ_constant(0)] * (INPUT_COUNT - 1),
    )
    assert poly_degree(germs[0].polynomial) == 2 <= degree_bound(len(body))


def test_manifest_records_what_the_gate_asked_about() -> None:
    manifest = invariant_manifest()
    assert manifest["abstraction_is_exact"] is True
    assert manifest["abstraction_is_a_widening"] is False
    assert manifest["length_independent"] is True
    assert manifest["counts_alternations"] is False
    assert manifest["uses_the_word_monotone"] is False
    assert manifest["domain"].startswith("unbounded")
    assert len(manifest["digest"]) == 64


def test_m091_artifacts_are_untouched_by_this_module() -> None:
    """M092 imports M091; it never redefines it."""

    assert ACQUIRED_CLAMP.origin == "acquired"
    assert ACQUIRED_CLAMP.body == (
        ("PUSH_SLOT", "$0"), ("PUSH_CONST", 0), ("BINOP", "max"), ("STORE_SLOT", "$0"),
    )
    assert {d.primitive_id for d in migrated_l0().primitives} == {
        "SET_CONST", "COPY_INPUT", "APPLY_UNARY",
    }
    assert INHERITED_DEFINITIONS[0].origin == "inherited"
