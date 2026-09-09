"""Small importable fixtures for objective-scoped recursive policy DEVELOPMENT tests.

The first objective can only be solved by a length-two program over ``increment`` and ``square``.
The second retains the first objective's tasks and adds one new point that only a length-three program
in the same bounded language can satisfy without forgetting the old points.
"""
from __future__ import annotations

from typing import Any, Mapping


class NullBody:
    """Seed body with no useful answer; candidate gains are therefore measured, not inherited."""

    def attempt(self, task: Mapping[str, Any]) -> Any:
        return None


def null_body() -> NullBody:
    return NullBody()


def grade_expected(task: Mapping[str, Any], answer: Any) -> str:
    """Parent-side grader. The candidate never receives ``expected`` in the sandbox task."""
    return "solved" if answer == task["expected"] else "unsolved"


OBJECTIVE_ONE = (
    {"task_id": "r0", "input": 0, "expected": 2},
    {"task_id": "r1", "input": 1, "expected": 3},
)

# ``increment -> increment`` still solves r0/r1, but returns 4 on r2. The length-three program
# ``square -> increment -> increment`` returns 2, 3 and 6 respectively, so it is a strict extension
# on this retained-capability objective rather than a trade.
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "r2", "input": 2, "expected": 6},
)
