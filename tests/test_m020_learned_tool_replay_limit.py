"""A learned rewrite tool is a literal replay, not a generalising transformation.

`PatchOperation` binds every edit to a positional AST index, and
`LearnedRewriteTool.propose` returns its stored operations verbatim. A learned tool can
therefore only reapply the same edits at the same sites.

Two consequences are pinned here because they bound what Gate 8 can measure:

1. the tool that produced a body is a no-op on that body;
2. the tool does not transfer to an equivalent site at a different index.
"""

from __future__ import annotations

import pytest

from metamorphosis.m020_self_rewrite import (
    Case,
    LearnedRewriteTool,
    PatchOperation,
    SelfRewriteEngine,
    ToolRegistry,
    apply_patch,
)

BASELINE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

AND_CASES = (
    Case((0, 0), 0),
    Case((0, 1), 0),
    Case((1, 0), 0),
    Case((1, 1), 1),
)


def _learn_a_tool() -> tuple[ToolRegistry, str, LearnedRewriteTool]:
    registry = ToolRegistry()
    result = SelfRewriteEngine(registry, max_edits=2, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert result.adopted
    assert registry.learned, "an accepted multi-edit trace must become a learned tool"
    return registry, result.selected.source, registry.learned[-1]


def test_learned_tool_is_a_noop_on_the_body_it_produced():
    _, improved, tool = _learn_a_tool()
    assert apply_patch(improved, tool.operations) == improved


def test_learned_tool_proposes_its_operations_verbatim():
    _, improved, tool = _learn_a_tool()
    proposals = list(tool.propose(improved))
    assert proposals == [tool.operations]


def test_patch_operations_are_bound_to_a_positional_index():
    """The same edit at a different site is a different, non-interchangeable operation."""

    source = """\
def policy(state, symbol):
    value = (state + symbol) + 0
    return value + 0
"""
    first = apply_patch(source, (PatchOperation("constant", 0, 4),))
    second = apply_patch(source, (PatchOperation("constant", 1, 4),))
    assert first != second
    assert "+ 4" in first and "+ 4" in second


def test_learned_tool_does_not_transfer_to_an_equivalent_site():
    """A tool learned at index 0 cannot fire at index 1, however similar the site."""

    tool = LearnedRewriteTool(
        "learned_shift_first_constant",
        (PatchOperation("constant", 0, 4),),
    )
    single_site = """\
def policy(state, symbol):
    return (state + symbol) + 0
"""
    patched = apply_patch(single_site, tool.operations)
    assert patched != single_site

    # Re-running the tool on its own output is a no-op, because the site already holds
    # the value: the tool encodes a destination, not a relative transformation.
    assert apply_patch(patched, tool.operations) == patched


def test_a_tool_whose_indices_are_absent_cannot_apply():
    tool = LearnedRewriteTool(
        "learned_out_of_range",
        (PatchOperation("constant", 9, 1),),
    )
    constant_free = """\
def policy(state, symbol):
    return state
"""
    assert list(tool.propose(constant_free)) == []
    with pytest.raises(ValueError):
        apply_patch(constant_free, tool.operations)
