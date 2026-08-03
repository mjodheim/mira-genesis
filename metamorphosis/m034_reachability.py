"""Reachability as an exact capability measure.

Deterministic search cost is a proxy. It conflates two different things: how close a
lineage started, and how much it can do. The body-anchored M033 block shows the confound
directly — the complete lineage beat its parent 32/0/0 largely because it began from a
better body, which is transported *output*.

Reachability is exact rather than proxied, and separates them:

    R(lineage, k) = { behaviours obtainable from its body within budget k }

- a better body moves *where* R sits;
- a genuinely transported capability makes R *larger* at a common body.

The set is finite and enumerable here, so it is ground truth rather than an estimate.

This module measures. It does not construct tasks and never touches a task generator, so
it cannot reach the reserved primary seed block.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .m020_self_rewrite import (
    LearnedRewriteTool,
    MacroCost,
    ToolRegistry,
    apply_patch,
    compile_policy,
    validate_source,
)


@dataclass(frozen=True)
class ReachabilityResult:
    budget: int
    macro_cost: str
    behaviours: tuple[tuple[int, ...], ...]
    sources_explored: int
    learned_tool_names: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.behaviours)

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": "m034-reachability/1",
                "budget": self.budget,
                "macro_cost": self.macro_cost,
                "reachable_count": self.size,
                "behaviours": [list(b) for b in self.behaviours],
                "sources_explored": self.sources_explored,
                "learned_tool_names": list(self.learned_tool_names),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def behaviour(
    source: str,
    function_name: str,
    state_count: int,
) -> tuple[int, ...] | None:
    """Return the transition table, or None if it leaves the declared state range."""

    try:
        policy = compile_policy(source, function_name)
        table = tuple(
            policy(state, symbol)
            for state in range(state_count)
            for symbol in (0, 1)
        )
    except Exception:  # noqa: BLE001 - any candidate failure means unreachable
        return None
    if any(not isinstance(v, int) or v < 0 or v >= state_count for v in table):
        return None
    return table


def reachable_behaviours(
    registry: ToolRegistry,
    body: str,
    function_name: str,
    *,
    state_count: int,
    budget: int,
    macro_cost: MacroCost = MacroCost.PER_OPERATION,
) -> ReachabilityResult:
    """Enumerate every valid behaviour obtainable from `body` within `budget` edits."""

    if budget < 1:
        raise ValueError("budget must be positive")

    seen_sources = {body}
    frontier = [(body, 0)]
    behaviours: set[tuple[int, ...]] = set()

    start = behaviour(body, function_name, state_count)
    if start is not None:
        behaviours.add(start)

    while frontier:
        source, used = frontier.pop()
        if used >= budget:
            continue
        for tool in registry.tools():
            charge_as_one = (
                macro_cost is MacroCost.UNIT
                and isinstance(tool, LearnedRewriteTool)
            )
            for proposed in tool.propose(source):
                step_cost = 1 if charge_as_one else len(proposed)
                if used + step_cost > budget:
                    continue
                try:
                    candidate = apply_patch(source, proposed)
                    validate_source(candidate, function_name)
                except Exception:  # noqa: BLE001
                    continue
                if candidate in seen_sources:
                    continue
                seen_sources.add(candidate)
                frontier.append((candidate, used + step_cost))
                table = behaviour(candidate, function_name, state_count)
                if table is not None:
                    behaviours.add(table)

    return ReachabilityResult(
        budget=budget,
        macro_cost=macro_cost.value,
        behaviours=tuple(sorted(behaviours)),
        sources_explored=len(seen_sources),
        learned_tool_names=tuple(tool.name for tool in registry.learned),
    )
