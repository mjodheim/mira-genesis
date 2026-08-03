"""A negative integer constant does not survive the unparse/parse round trip.

`_IndexedNodeTransformer.visit_Constant` writes `ast.Constant(-2)`. `ast.unparse`
renders that as `-2`, and re-parsing `-2` yields `UnaryOp(USub, Constant(2))`, because
Python has no negative integer literal. Every later patch at that index therefore sees a
*positive* constant inside a negation and wraps another one around it.

Three consequences, all pinned below:

1. a constant patch is **not idempotent** for negative values — applying it twice flips
   the sign instead of leaving the source unchanged;
2. the AST grows without bound under repeated negative patches;
3. the search can reach bodies whose outputs fall outside the declared state range.

These tests document the defect as it currently behaves. They are deliberately written
to fail if the behaviour is corrected, so that a fix cannot land silently: correcting
`apply_patch` changes the reachable candidate set and therefore may move recorded
digests, which is a decision that belongs with the protocol owner.

No recorded M033 calibration is affected: 776 of 776 adopted sources across the fixed,
structural, combined and body-anchored blocks contain no negative constant.
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


def test_positive_constant_patch_is_idempotent():
    once = apply_patch(SOURCE, (PatchOperation("constant", 0, 3),))
    twice = apply_patch(once, (PatchOperation("constant", 0, 3),))
    assert once == twice
    assert _unary_count(once) == 0


def test_negative_constant_patch_is_not_idempotent():
    """The defect. Applying the same operation twice does not leave the source alone."""

    once = apply_patch(SOURCE, (PatchOperation("constant", 0, -2),))
    twice = apply_patch(once, (PatchOperation("constant", 0, -2),))
    assert once != twice
    assert "--2" in twice


def test_repeated_negative_patches_grow_the_ast_without_bound():
    source = SOURCE
    for expected in range(1, 6):
        source = apply_patch(source, (PatchOperation("constant", 0, -2),))
        assert _unary_count(source) == expected


def test_the_effective_value_flips_on_each_reapplication():
    source = SOURCE
    behaviours = []
    for _ in range(4):
        source = apply_patch(source, (PatchOperation("constant", 0, -2),))
        policy = compile_policy(source, "policy")
        behaviours.append(tuple(policy(s, y) for s, y in PAIRS))
    # odd applications leave a negative modulus, even ones cancel back to positive
    assert behaviours[0] == behaviours[2]
    assert behaviours[1] == behaviours[3]
    assert behaviours[0] != behaviours[1]


def test_a_patched_body_can_leave_the_declared_state_range():
    """A next-state of -1 is not a valid state of a two-state machine."""

    source = apply_patch(SOURCE, (PatchOperation("constant", 0, -2),))
    policy = compile_policy(source, "policy")
    outputs = {policy(s, y) for s, y in PAIRS}
    assert not outputs <= {0, 1}
