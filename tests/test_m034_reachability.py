"""Reachability separates transported output from transported capability.

Two claims are pinned here, both decidable in this finite domain:

1. under `MacroCost.PER_OPERATION` a learned tool adds **nothing** to the reachable set,
   because it is a composition of primitives charged what those primitives cost;
2. under `MacroCost.UNIT` the same tool enlarges the reachable set, which is what turns
   retained experience into capability rather than a shortcut.
"""

from __future__ import annotations

import pytest

from metamorphosis.m020_self_rewrite import (
    LearnedRewriteTool,
    MacroCost,
    PatchOperation,
    ToolRegistry,
)
from metamorphosis.m034_reachability import behaviour, reachable_behaviours

BODY = "def policy(state, symbol):\n    return state * symbol % 3 + 0\n"

MACRO = LearnedRewriteTool(
    "macro_add_mod2",
    (PatchOperation("binary_operator", 2, "add"), PatchOperation("constant", 0, 2)),
)


def _reach(tools, budget, macro_cost):
    registry = ToolRegistry()
    registry.learned.extend(tools)
    return reachable_behaviours(
        registry,
        BODY,
        "policy",
        state_count=2,
        budget=budget,
        macro_cost=macro_cost,
    )


def test_behaviour_rejects_a_body_that_leaves_the_state_range():
    outside = "def policy(state, symbol):\n    return state * symbol % -2 + 0\n"
    assert behaviour(outside, "policy", state_count=2) is None
    assert behaviour(BODY, "policy", state_count=2) == (0, 0, 0, 1)


@pytest.mark.parametrize("budget", (1, 2, 3))
def test_per_operation_macros_add_no_reachable_capability(budget):
    """The central negative result: today's learned tools cannot enlarge R."""

    without = _reach([], budget, MacroCost.PER_OPERATION)
    with_macro = _reach([MACRO], budget, MacroCost.PER_OPERATION)
    assert with_macro.behaviours == without.behaviours


@pytest.mark.parametrize("budget", (1, 3))
def test_unit_cost_macros_do_add_reachable_capability(budget):
    baseline = _reach([], budget, MacroCost.PER_OPERATION)
    unit = _reach([MACRO], budget, MacroCost.UNIT)
    assert unit.size > baseline.size
    assert set(baseline.behaviours) < set(unit.behaviours)


def test_reachability_is_deterministic_and_addressable():
    a = _reach([MACRO], 3, MacroCost.UNIT)
    b = _reach([MACRO], 3, MacroCost.UNIT)
    assert a.canonical_json() == b.canonical_json()
    assert a.sha256() == b.sha256()
    assert '"version":"m034-reachability/1"' in a.canonical_json()


def test_reachability_grows_monotonically_with_budget():
    sizes = [_reach([], k, MacroCost.PER_OPERATION).size for k in (1, 2, 3)]
    assert sizes == sorted(sizes)
    assert sizes[0] < sizes[-1]


def test_every_reachable_behaviour_is_a_valid_state_table():
    result = _reach([MACRO], 3, MacroCost.UNIT)
    for table in result.behaviours:
        assert len(table) == 4
        assert all(v in (0, 1) for v in table)
