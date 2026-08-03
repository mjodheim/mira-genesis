"""Negative integer constants survive the patch round trip (D014 resolved).

Python has no negative integer literal: `-2` parses as `UnaryOp(USub, Constant(2))`.
The kernel previously read the inner `Constant(2)` as the patch target, so writing a
negative value stacked another negation on every reapplication.

`_negative_int_literal` now makes the collector and the transformer treat a `-<int>`
expression as one constant target, so the value is replaced rather than wrapped.

This file replaces `test_m020_negative_constant_defect.py`, which asserted the defective
behaviour so that a fix could not land unnoticed. That was its purpose; it has been
consciously retired, not deleted in passing.
"""

from __future__ import annotations

import ast

from metamorphosis.m020_self_rewrite import (
    PatchOperation,
    apply_patch,
    compile_policy,
)

SOURCE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

PAIRS = [(s, y) for s in (0, 1) for y in (0, 1)]


def _unary_count(source: str) -> int:
    return len([n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.UnaryOp)])


def test_a_constant_patch_is_idempotent_for_every_sign():
    for value in (3, -2, 1, -1, 0, 4):
        once = apply_patch(SOURCE, (PatchOperation("constant", 0, value),))
        twice = apply_patch(once, (PatchOperation("constant", 0, value),))
        assert once == twice, f"patch for {value} is not idempotent"


def test_repeated_negative_patches_do_not_grow_the_ast():
    source = SOURCE
    for _ in range(6):
        source = apply_patch(source, (PatchOperation("constant", 0, -2),))
        assert _unary_count(source) == 1
        assert "--" not in source


def test_the_effective_behaviour_is_stable_under_reapplication():
    source = SOURCE
    behaviours = []
    for _ in range(4):
        source = apply_patch(source, (PatchOperation("constant", 0, -2),))
        policy = compile_policy(source, "policy")
        behaviours.append(tuple(policy(s, y) for s, y in PAIRS))
    assert len(set(behaviours)) == 1


def test_a_negative_constant_can_be_replaced_by_a_positive_one():
    negative = apply_patch(SOURCE, (PatchOperation("constant", 0, -2),))
    positive = apply_patch(negative, (PatchOperation("constant", 0, 3),))
    assert "% 3" in positive
    assert "-" not in positive.split("return")[1]
    assert _unary_count(positive) == 0


def test_constant_indices_are_stable_across_a_sign_change():
    """The second constant must keep index 1 whether the first is negative or not."""

    negative = apply_patch(SOURCE, (PatchOperation("constant", 0, -2),))
    patched = apply_patch(negative, (PatchOperation("constant", 1, 4),))
    assert "% -2" in patched
    assert "+ 4" in patched
