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

    `routed` is what makes an ablation mean anything. A task listed there is answered *through* a
    named acquired component rather than out of the body's own table. Take the component away and
    the body does not degrade into its parent: it reaches for something that is not there and
    errors. That asymmetry is the whole difference between an ablation and the verdict relabelled —
    the parent generation never reached for the component at all, so an ablated candidate that
    behaves exactly like the parent is a sign that nothing was actually removed.
    """

    def __init__(self, solves, operation_names, *, routed=(), capabilities=()):
        self.solves = set(solves)
        self.operation_names = tuple(operation_names)
        self.routed = dict(routed)
        self.capabilities = frozenset(capabilities)

    def attempt(self, task):
        from genesis.development_bodies import SUBSTRATE_OPERATIONS

        for name in self.operation_names:
            if name not in SUBSTRATE_OPERATIONS:
                return "error"
        key = SUBSTRATE_OPERATIONS["read"](task)
        required = self.routed.get(key)
        if required is not None:
            return "solved" if required in self.capabilities else "error"
        return "solved" if key in self.solves else "unsolved"


#: The operations the second substrate really supports. A lineage learns these by probing.
SUBSTRATE_OPERATIONS = {
    "read": lambda task: str(task["task_id"]),
    "list": lambda task: [str(task["task_id"])],
}


#: The component the later migrated generation routes its new solutions through.
ACQUIRED_COMPONENT = "joint_registry"

#: The tasks that generation answers through it rather than out of its own table.
ROUTED_TASKS = {"t2": ACQUIRED_COMPONENT, "t3": ACQUIRED_COMPONENT}


def migrated_parent_body():
    return RecordBody({"t0", "t1"}, ("read",))


def migrated_improved_body():
    """The later generation: it gains t2 and t3 *through* the acquired component."""
    return RecordBody(
        {"t0", "t1"}, ("read",), routed=ROUTED_TASKS, capabilities={ACQUIRED_COMPONENT}
    )


def migrated_ablated_body():
    """The same generation with the acquisition removed, and nothing else changed.

    Comparing a candidate against its parent is the verdict, not an ablation. To show a later
    generation *needed* an earlier acquisition, the acquisition has to be taken away and that same
    generation retried at the same budget. Only `capabilities` differs from
    `migrated_improved_body`; a test asserts that rather than trusting this docstring.
    """
    return RecordBody({"t0", "t1"}, ("read",), routed=ROUTED_TASKS, capabilities=())


def migrated_uncoupled_ablation_body():
    """Negative control: an 'ablated' arm that never routed through anything.

    Nothing was removed from it, because it never depended on the acquisition in the first place.
    The causal check must refuse this arm. It exists so the check's positive verdict is a finding
    rather than a property of how the fixtures were written.
    """
    return RecordBody({"t0", "t1"}, ("read",))


# ---------------------------------------------------------------------------------------------
# Bodies that reach outside the sandbox, for testing that the isolation is applied and not merely
# declared
# ---------------------------------------------------------------------------------------------
class WritingBody:
    """A body that tries to write a file. Blocked writes surface as `error` rows."""

    def __init__(self, path):
        self.path = str(path)

    def attempt(self, task):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(str(task["task_id"]))
        return "solved"


class NetworkingBody:
    """A body that tries a name resolution. Blocked network access surfaces as `error` rows.

    `getaddrinfo` on the loopback name succeeds without any network, so this body reports `solved`
    when nothing stops it. That is what makes the blocked case evidence rather than a coincidence.
    """

    def attempt(self, task):
        import socket

        socket.getaddrinfo("localhost", 80)
        return "solved"


class LowLevelWritingBody:
    """A body that opens for writing through `os.open`, where the intent is in the flags.

    `open(path, "w")` is the spelling a guard is written against. This is the one it forgets.
    """

    def __init__(self, path):
        self.path = str(path)

    def attempt(self, task):
        import os

        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(descriptor, str(task["task_id"]).encode("utf-8"))
        finally:
            os.close(descriptor)
        return "solved"


class DeletingBody:
    """A body that removes a file. Nothing in it ever calls `open`."""

    def __init__(self, path):
        self.path = str(path)

    def attempt(self, task):
        import os

        os.remove(self.path)
        return "solved"


class SubprocessBody:
    """A body that shells out. `RLIMIT_NPROC` is not available everywhere; the guard is."""

    def attempt(self, task):
        import subprocess

        subprocess.run(["/bin/true"], check=False)
        return "solved"


def writing_body(path):
    return WritingBody(path)


def low_level_writing_body(path):
    return LowLevelWritingBody(path)


def deleting_body(path):
    return DeletingBody(path)


def subprocess_body():
    return SubprocessBody()


def networking_body():
    return NetworkingBody()


# ---------------------------------------------------------------------------------------------
# Primitive operations a lineage can compose probes from
# ---------------------------------------------------------------------------------------------
#: What the host supplies to `genesis.probe`: the alphabet, not the sentence. The host cannot know
#: which composition solves a given demand, and cannot make one solve it by saying so — the
#: composition either maps the inputs to the expected outputs when it runs, or it does not.
PROBE_OPERATIONS = {
    "increment": lambda value: value + 1,
    "negate": lambda value: -value,
    "triple": lambda value: value * 3,
    "double": lambda value: value * 2,
    "square": lambda value: value * value,
    "halve": lambda value: value // 2,
}

#: Which operations each seed component gives the lineage access to. Neither component alone spans
#: the demands below; that is a fact about this partition, discoverable only by running probes.
COMPONENT_OPERATIONS = {
    "operator_table": ["increment", "negate", "triple"],
    "signal_interface": ["double", "square", "halve"],
}

PROBE_REGISTRY = "genesis.development_bodies:PROBE_OPERATIONS"

#: A demand needing `double` then `increment` — one operation from each component, so no held
#: component can express it and the wider registry can.
SPANNING_DEMAND = [
    {"task_id": "p0", "input": 3, "expected": 7},
    {"task_id": "p1", "input": 5, "expected": 11},
]

#: A demand one held component resolves on its own. Same machinery, opposite finding.
LOCAL_DEMAND = [
    {"task_id": "p0", "input": 3, "expected": 4},
    {"task_id": "p1", "input": 5, "expected": 6},
]

#: A demand nothing in the registry can reach at all. Exhaustion without reachability is a failed
#: search, not a finding about the lineage's representation, and must not license anything.
UNREACHABLE_DEMAND = [
    {"task_id": "p0", "input": 3, "expected": 1000},
    {"task_id": "p1", "input": 5, "expected": 2000},
]

#: Two demands the per-component vocabulary cannot tell apart — neither component resolves either —
#: whose causes differ: one lives mostly in `operator_table` and needs something from
#: `signal_interface`, the other the reverse. The lineage finds that by measuring, not by being told.
#: `increment`, `negate`, `double`: 3 -> 4 -> -4 -> -8.
CONFUSABLE_A = [
    {"task_id": "q0", "input": 3, "expected": -8},
    {"task_id": "q1", "input": 5, "expected": -12},
]
#: `double`, `square`, `negate`: 3 -> 6 -> 36 -> -36.
CONFUSABLE_B = [
    {"task_id": "q0", "input": 3, "expected": -36},
    {"task_id": "q1", "input": 5, "expected": -100},
]
