"""D013 follow-up: repeated cycles restore what a single cycle cannot express.

D013 established that a learned tool is a literal replay at fixed AST indices, so the
tool that produced a body is a no-op on that body. That makes Gate 8's learned-tool
ablation inert for a single-cycle lineage.

D013 predicted the condition is repairable by the repeated cycles Gate 9 already
requires. These tests measure that prediction rather than assuming it.

The mechanism is narrow and worth stating exactly: the newest tool is always inert,
because it is by construction the trace that produced the current body. An older tool
becomes able to act again once a later cycle moves the body away from what that tool
wrote.
"""

from __future__ import annotations

from metamorphosis.m020_self_rewrite import (
    Case,
    SelfRewriteEngine,
    ToolRegistry,
    apply_patch,
)

BASELINE = """\
def policy(state, symbol):
    return ((state + symbol) % 1) + 0
"""

AND_CASES = tuple(Case((s, y), s * y) for s in (0, 1) for y in (0, 1))
OR_CASES = tuple(Case((s, y), 1 if (s or y) else 0) for s in (0, 1) for y in (0, 1))
XOR_CASES = tuple(Case((s, y), (s + y) % 2) for s in (0, 1) for y in (0, 1))


def _cycle(registry: ToolRegistry, source: str, cases) -> str:
    result = SelfRewriteEngine(registry, max_edits=3, beam_width=64).improve(
        source, "policy", cases
    )
    return result.selected.source if result.adopted else source


def _three_cycle_lineage() -> tuple[ToolRegistry, str]:
    registry = ToolRegistry()
    body = _cycle(registry, BASELINE, AND_CASES)
    body = _cycle(registry, body, OR_CASES)
    body = _cycle(registry, body, XOR_CASES)
    return registry, body


def _is_noop(tool, body: str) -> bool:
    try:
        return apply_patch(body, tool.operations) == body
    except (SyntaxError, ValueError):
        return True  # a tool that cannot apply also cannot act


def test_three_distinct_cycles_accumulate_three_tools():
    registry, _ = _three_cycle_lineage()
    assert len(registry.learned) == 3
    assert len({tool.name for tool in registry.learned}) == 3


def test_the_newest_tool_is_always_inert_on_the_body_it_produced():
    registry, body = _three_cycle_lineage()
    assert _is_noop(registry.learned[-1], body)


def test_an_earlier_tool_reactivates_once_the_body_moves_away():
    """The property Gate 8's tool control needs in order to measure anything."""

    registry, body = _three_cycle_lineage()
    active = [tool for tool in registry.learned if not _is_noop(tool, body)]
    assert active, "a multi-cycle lineage must carry at least one tool that can act"
    assert registry.learned[-1] not in active


def test_a_single_cycle_lineage_carries_no_active_tool():
    """The D013 baseline, restated here so the contrast is pinned in one place."""

    registry = ToolRegistry()
    body = _cycle(registry, BASELINE, AND_CASES)
    assert len(registry.learned) == 1
    assert all(_is_noop(tool, body) for tool in registry.learned)


def test_reactivated_tool_rewrites_the_body_rather_than_reproducing_it():
    registry, body = _three_cycle_lineage()
    active = [tool for tool in registry.learned if not _is_noop(tool, body)]
    for tool in active:
        assert apply_patch(body, tool.operations) != body
