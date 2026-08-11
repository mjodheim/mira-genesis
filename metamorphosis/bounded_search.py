"""Uniform-cost enumeration of every cheapest-per-terminal-state plan within a budget.

Extracted verbatim from M079's `satisfying_plans`, which sealed a general search inside one
transport domain's affordances. M084 needs the same enumeration over resource carriers in real
environments, and restating it there would let the two copies quietly diverge.

The extraction is behaviour-preserving: the queue order, the counter tie-break, the dominated-state
pruning and the final sort key are unchanged, so M079 re-derives its preserved result exactly.

Callers supply the domain: a successor function yielding `(action, successor_state, step_cost)`, and
a predicate saying whether a state satisfies the goal. Nothing here knows what a state is.
"""
from __future__ import annotations

import heapq
from typing import Callable, Hashable, Iterable, TypeVar


State = TypeVar("State", bound=Hashable)

Successors = Callable[[State], Iterable[tuple[tuple, State, int]]]
GoalReached = Callable[[State], bool]


def uniform_cost_plans(
    initial: State,
    successors: Successors,
    goal_reached: GoalReached,
    budget: int,
) -> list[tuple[int, tuple, State]]:
    """Every cheapest plan per goal-satisfying terminal state, ordered by cost then by plan text.

    A goal-satisfying state is terminal: the search does not expand through it. Returning several
    terminal states is the point — a caller that finds more than one materially different terminal
    state has discovered that its goal is under-determined.
    """

    best: dict[State, tuple[int, tuple]] = {}
    seen: dict[State, int] = {initial: 0}
    queue: list[tuple[int, int, State, tuple]] = [(0, 0, initial, ())]
    counter = 1
    while queue:
        cost, _, current, plan = heapq.heappop(queue)
        if cost > budget:
            continue
        if goal_reached(current):
            if current not in best or cost < best[current][0]:
                best[current] = (cost, plan)
            continue
        for action, successor, step in successors(current):
            total = cost + step
            if total > budget:
                continue
            if successor in seen and seen[successor] <= total:
                continue
            seen[successor] = total
            heapq.heappush(queue, (total, counter, successor, plan + (action,)))
            counter += 1
    return sorted(
        ((cost, plan, terminal) for terminal, (cost, plan) in best.items()),
        key=lambda entry: (entry[0], str(entry[1])),
    )
