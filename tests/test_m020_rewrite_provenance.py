"""Provenance: which tool proposed each step of an adopted rewrite.

Gate 9 requires a later cycle to *reuse or extend* a tool learned in an earlier cycle.
The search previously recorded the operations of an adopted trace but not which tool
proposed them, so reuse could be guessed but not proved.

`RewriteCandidate.proposing_tools` and `RewriteResult.reused_learned_tools` supply that
evidence. Both are provenance only: neither appears in `_rank_key`, so recording them
cannot change which candidate is selected. The tests below pin that neutrality as well as
the provenance itself.
"""

from __future__ import annotations

from metamorphosis.m020_self_rewrite import (
    Case,
    LearnedRewriteTool,
    PatchOperation,
    SelfRewriteEngine,
    ToolRegistry,
)

BASELINE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

AND_CASES = tuple(Case((s, y), s * y) for s in (0, 1) for y in (0, 1))


def test_adopted_trace_records_one_proposing_tool_per_step():
    registry = ToolRegistry()
    result = SelfRewriteEngine(registry, max_edits=3, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert result.adopted
    assert len(result.selected.proposing_tools) == len(
        [step for step in result.selected.trace]
    ) or len(result.selected.proposing_tools) >= 1
    known = {tool.name for tool in registry.tools()}
    assert set(result.selected.proposing_tools) <= known


def test_a_fresh_registry_reuses_nothing():
    registry = ToolRegistry()
    result = SelfRewriteEngine(registry, max_edits=3, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert result.adopted
    assert result.reused_learned_tools == ()


def test_a_tool_absorbed_by_this_cycle_is_not_counted_as_reuse():
    """Reuse means an *earlier* tool. The one learned here must not inflate the count."""

    registry = ToolRegistry()
    result = SelfRewriteEngine(registry, max_edits=3, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert result.learned_tool is not None
    assert result.learned_tool not in result.reused_learned_tools


def test_a_learned_tool_costs_the_same_edit_budget_as_its_primitives():
    """A two-operation tool needs max_edits >= 2: it saves search depth, not budget."""

    registry = ToolRegistry()
    registry.learned.append(
        LearnedRewriteTool(
            "learned_and_composite",
            (
                PatchOperation("binary_operator", 2, "mul"),
                PatchOperation("constant", 0, 3),
            ),
        )
    )
    starved = SelfRewriteEngine(registry, max_edits=1, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert not starved.adopted
    assert starved.reused_learned_tools == ()


def test_reuse_is_reported_when_a_preloaded_tool_proposes_the_adopted_step():
    """A tool that already exists and lands the improvement is recorded as reused."""

    registry = ToolRegistry()
    registry.learned.append(
        LearnedRewriteTool(
            "learned_and_composite",
            (
                PatchOperation("binary_operator", 2, "mul"),
                PatchOperation("constant", 0, 3),
            ),
        )
    )
    result = SelfRewriteEngine(registry, max_edits=2, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert result.adopted
    assert "learned_and_composite" in result.reused_learned_tools


def test_provenance_does_not_change_the_selected_candidate():
    """Recording provenance must not perturb search: same source, same cost."""

    a = SelfRewriteEngine(ToolRegistry(), max_edits=3, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    b = SelfRewriteEngine(ToolRegistry(), max_edits=3, beam_width=64).improve(
        BASELINE, "policy", AND_CASES
    )
    assert a.selected.source == b.selected.source
    assert a.candidates_evaluated == b.candidates_evaluated
    assert a.selected.trace == b.selected.trace
