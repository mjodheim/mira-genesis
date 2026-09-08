"""Neutral development bodies for exercising the runtime.

These are fixtures, not science. They exist so the loop can be driven end to end without a real
mechanism attached, and so the tests can assert what the runtime does when a candidate is better,
worse, broken or merely equal.

They live in an importable module because the sandbox spawns a fresh interpreter: a body defined in
a `__main__` that cannot be re-imported would fail to construct in the child, and the runtime would
correctly report an instrument abort rather than a candidate failure.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


class TableBody:
    """A body that solves exactly the tasks it was told it can solve."""

    def __init__(self, solves: Sequence[str], *, refuses: Sequence[str] = ()) -> None:
        self.solves = set(solves)
        self.refuses = set(refuses)

    def attempt(self, task: Mapping[str, Any]) -> str:
        task_id = str(task["task_id"])
        if task_id in self.refuses:
            return "refused"
        return "solved" if task_id in self.solves else "unsolved"


class ThrowingBody:
    """A body whose every attempt raises. The runtime must record `error` rows, not crash."""

    def attempt(self, task: Mapping[str, Any]) -> str:
        raise RuntimeError("this body cannot attempt anything")


class LyingBody(TableBody):
    """A body that reports a flattering summary alongside honest per-task outcomes.

    The trust root must ignore the summary entirely. This exists so a test can prove that rather
    than assume it.
    """

    def summary(self) -> dict[str, Any]:  # pragma: no cover - never read by design
        return {"score": 1.0, "solved_count": 999, "accepted": True}


def parent_body() -> TableBody:
    return TableBody({"t0", "t1"})


def improved_body() -> TableBody:
    return TableBody({"t0", "t1", "t2", "t3"})


def regressed_body() -> TableBody:
    return TableBody({"t0"})


def equal_body() -> TableBody:
    return TableBody({"t0", "t1"})


def refusing_body() -> TableBody:
    return TableBody({"t0", "t1"}, refuses={"t2"})


def throwing_body() -> ThrowingBody:
    return ThrowingBody()


def lying_body() -> LyingBody:
    return LyingBody({"t0"})


def unconstructible_body():
    raise RuntimeError("this body cannot be constructed at all")


# ---------------------------------------------------------------------------------------------
# A second substrate, for exercising migration
# ---------------------------------------------------------------------------------------------
class RecordBody:
    """A body whose tasks are answered through a substrate's discovered operations.

    It holds only operation *names*, never the callables, so it can be pickled into the sandbox's
    spawned interpreter. The operations are rebound from the substrate registry in the child.
    """

    def __init__(self, solves, operation_names):
        self.solves = set(solves)
        self.operation_names = tuple(operation_names)

    def attempt(self, task):
        from genesis.development_bodies import SUBSTRATE_OPERATIONS

        for name in self.operation_names:
            if name not in SUBSTRATE_OPERATIONS:
                return "error"
        key = SUBSTRATE_OPERATIONS["read"](task)
        return "solved" if key in self.solves else "unsolved"


#: The operations the second substrate really supports. A lineage learns these by probing.
SUBSTRATE_OPERATIONS = {
    "read": lambda task: str(task["task_id"]),
    "list": lambda task: [str(task["task_id"])],
}


def migrated_parent_body():
    return RecordBody({"t0", "t1"}, ("read",))


def migrated_improved_body():
    return RecordBody({"t0", "t1", "t2", "t3"}, ("read",))
