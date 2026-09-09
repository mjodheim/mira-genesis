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


#: What a body returns to decline a task. Refusal is a first-class outcome — M074/M078 make it a
#: measured quantity rather than an absence — so it has to survive the trip through a grader.
REFUSED = "__refused__"


def answer_to(task: Mapping[str, Any]) -> int:
    """The right answer to a task, computed from the question.

    A body that can do the work computes this. A body that cannot has nothing to fall back on,
    because the task it receives carries the question and not the answer — the sandbox withholds
    `expected` on the way in. Before that, every fixture here simply returned `task["expected"]`,
    which meant the grader was comparing the answer key against itself and would have passed a body
    that computed nothing at all.
    """
    return int(task["input"]) * 2 + 1


def grade(task: Mapping[str, Any], answer: Any) -> str:
    """Grade an answer against the real task, in the parent, where the candidate cannot reach.

    This is the whole point of the graded path: the body says what it computed, and something else
    says whether that was right. A body that returns the string "solved" is not solving anything, it
    is claiming to, and here the claim is simply a wrong answer.
    """
    if answer == REFUSED:
        return "refused"
    return "solved" if answer == answer_to(task) else "unsolved"


class TableBody:
    """A body that answers exactly the tasks it was told it can answer."""

    def __init__(self, solves: Sequence[str], *, refuses: Sequence[str] = ()) -> None:
        self.solves = set(solves)
        self.refuses = set(refuses)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        task_id = str(task["task_id"])
        if task_id in self.refuses:
            return REFUSED
        return answer_to(task) if task_id in self.solves else None


class ThrowingBody:
    """A body whose every attempt raises. The runtime must record `error` rows, not crash."""

    def attempt(self, task: Mapping[str, Any]) -> str:
        raise RuntimeError("this body cannot attempt anything")


class LyingBody(TableBody):
    """A body that reports a flattering summary alongside honest per-task answers.

    The trust root must ignore the summary entirely. This exists so a test can prove that rather
    than assume it.
    """

    def summary(self) -> dict[str, Any]:  # pragma: no cover - never read by design
        return {"score": 1.0, "solved_count": 999, "accepted": True}


class CheatingBody:
    """A body that claims every task and answers none of them.

    Self-reported, it wins everything: its return value *is* the outcome, so declaring success is
    success. Graded in the parent, the same body scores zero, because "solved" is not the answer to
    anything. One body, two verdicts, and the difference is who decides.
    """

    def attempt(self, task: Mapping[str, Any]) -> Any:
        return "solved"


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


def cheating_body() -> CheatingBody:
    return CheatingBody()


class PeekingBody:
    """Reads the answer out of the task instead of computing it.

    This scored full marks. Every fixture in this module used to do the same thing — return
    `task["expected"]` — so the grader introduced to stop a candidate marking its own paper was
    comparing the answer key against itself. It now scores zero, because the sandbox withholds
    `expected` from the task the child receives and there is nothing left to read.
    """

    def attempt(self, task):
        return task.get("expected")


def peeking_body() -> PeekingBody:
    return PeekingBody()


class ReportingBody:
    """Answers with the task keys it was actually given, so a test can inspect the boundary.

    Checking that a withheld key changed the *outcome* leaves open that it changed it for some other
    reason. This reports what crossed the process boundary.
    """

    def attempt(self, task):
        return sorted(task)


def reporting_body() -> ReportingBody:
    return ReportingBody()


def keys_grade(task: Mapping[str, Any], answer: Any) -> str:
    """Solved when the child's key list contains no key the parent meant to keep."""
    return "solved" if "expected" not in (answer or []) else "unsolved"


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
    raises, which the sandbox records as `error`. That asymmetry is the whole difference between an
    ablation and the verdict relabelled — the parent generation never reached for the component at
    all, so an ablated candidate that behaves exactly like the parent is a sign that nothing was
    actually removed.
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
                raise RuntimeError("this substrate does not support %r" % name)
        key = SUBSTRATE_OPERATIONS["read"](task)
        required = self.routed.get(key)
        if required is not None:
            if required not in self.capabilities:
                raise RuntimeError("this body reaches for %r, which it no longer has" % required)
            return answer_to(task)
        return answer_to(task) if key in self.solves else None


#: The operations the second substrate really supports. A lineage learns these by probing.
SUBSTRATE_OPERATIONS = {
    "read": lambda task: str(task["task_id"]),
    "list": lambda task: [str(task["task_id"])],
}


# The lineage's descent after the substrate change, as a chain rather than a sequence.
#
#   generation 1  improved_body                  solves t0..t3 in the old substrate
#   migration     migrated_parent_body           the translation: must still solve t0..t3
#   generation 2  migrated_improved_body         gains t4 through what generation 2 acquires
#   generation 3  migrated_further_body          gains t5, and still needs both earlier acquisitions
#   generation 4  migrated_fourth_body           gains t6 and t7, and still needs all three
#
# Each generation introduces its own acquisition; the next one is ablated against it.
#
# Each later generation *routes* its earlier gains through the components that produced them, so an
# ablation removes something rather than merely relabelling the verdict.

#: The component the lineage named for itself, by probing, before it migrated.
ACQUIRED_COMPONENT = "joint_registry"
#: What the first post-migration generation acquires, which the one after it depends on.
SECOND_ACQUISITION = "carrier_index"

#: t2 and t3 are answered through the probe-named component rather than out of the body's own table.
ROUTED_TASKS = {"t2": ACQUIRED_COMPONENT, "t3": ACQUIRED_COMPONENT}
#: generation 2 adds t4 through its own acquisition.
ROUTED_AFTER_MIGRATION = {**ROUTED_TASKS, "t4": SECOND_ACQUISITION}
#: What generation 3 acquires, which generation 4 depends on in turn.
THIRD_ACQUISITION = "carrier_index_ii"
#: What generation 4 acquires.
FOURTH_ACQUISITION = "carrier_index_iii"

#: generation 3 adds t5 through its own acquisition, and keeps needing generation 2's.
ROUTED_THIRD_GENERATION = {**ROUTED_AFTER_MIGRATION, "t5": THIRD_ACQUISITION}
#: generation 4 adds t6 and t7 through its own, and still needs everything before it.
ROUTED_FOURTH_GENERATION = {
    **ROUTED_THIRD_GENERATION,
    "t6": FOURTH_ACQUISITION,
    "t7": FOURTH_ACQUISITION,
}


class FragileBody(RecordBody):
    """A body that cannot be *constructed* without one particular acquisition.

    Its derived ablation therefore fails in the child process rather than answering badly, which is
    what the runtime needs in order to distinguish a measurement it could not take from one that
    came back negative.
    """

    def __init__(self, solves, operation_names, *, routed=(), capabilities=()):
        super().__init__(solves, operation_names, routed=routed, capabilities=capabilities)
        if FRAGILE_ACQUISITION not in self.capabilities:
            raise RuntimeError("this body cannot be constructed without %r" % FRAGILE_ACQUISITION)


#: An acquisition whose removal makes the body unbuildable rather than merely worse.
FRAGILE_ACQUISITION = "unbuildable_without_this"

RECORD_BODY = "genesis.development_bodies:RecordBody"
FRAGILE_BODY = "genesis.development_bodies:FragileBody"


def _configured(solves, routed, dependencies, *, target=RECORD_BODY):
    """A body factory that publishes what it is made of.

    These used to be plain functions, and the ablated arms were hand-written twins of them: a
    reviewer had to read two definitions and take on trust that they differed in one field. The
    runtime cannot read a function, so it could not build the counterfactual and had to accept
    whichever arm the proposer supplied. Now the configuration is data, `ConfiguredBody.without()`
    is the only edit, and the arm the cycle runs is one the runtime derived and checked.
    """
    from genesis.artifacts import ConfiguredBody

    return ConfiguredBody(
        target=target,
        configuration={
            "solves": sorted(solves),
            "operation_names": ["read"],
            "routed": dict(routed),
        },
        dependencies=frozenset(dependencies),
        dependency_keyword="capabilities",
    )


#: The translation of `improved_body` into the new substrate. It must still solve everything the
#: departing body solved; a translation that quietly solves less is transported output, and
#: `migration.capability_carried` refuses it.
migrated_parent_body = _configured({"t0", "t1"}, ROUTED_TASKS, {ACQUIRED_COMPONENT})

#: Generation 2, in the new form: gains t4 through its own acquisition.
migrated_improved_body = _configured(
    {"t0", "t1"}, ROUTED_AFTER_MIGRATION, {ACQUIRED_COMPONENT, SECOND_ACQUISITION}
)

#: Generation 3: gains t5 through its own acquisition, still routing t4 through generation 2's.
migrated_further_body = _configured(
    {"t0", "t1"},
    ROUTED_THIRD_GENERATION,
    {ACQUIRED_COMPONENT, SECOND_ACQUISITION, THIRD_ACQUISITION},
)

#: Generation 4: gains t6 and t7 through its own acquisition, still needing all three before.
migrated_fourth_body = _configured(
    {"t0", "t1"},
    ROUTED_FOURTH_GENERATION,
    {ACQUIRED_COMPONENT, SECOND_ACQUISITION, THIRD_ACQUISITION, FOURTH_ACQUISITION},
)

#: The ablated arms are *derived*, by the same call the runtime makes. They exist as names only so
#: tests can inspect them; nothing passes them to a cycle as evidence any more.
migrated_ablated_body = migrated_improved_body.without(ACQUIRED_COMPONENT)
migrated_further_ablated_body = migrated_further_body.without(SECOND_ACQUISITION)
migrated_fourth_ablated_body = migrated_fourth_body.without(THIRD_ACQUISITION)

#: Negative control: a candidate that *declares* a dependency it routes no work through. The runtime
#: builds the arm correctly and the arm loses nothing, so the causal claim fails on the measurement
#: rather than on the paperwork. It exists so the positive verdict elsewhere is a finding about the
#: bodies rather than a property of how the fixtures were written.
uncoupled_candidate_body = _configured(
    {"t0", "t1", "t2", "t3", "t4"}, {}, {ACQUIRED_COMPONENT, SECOND_ACQUISITION}
)

#: A candidate whose derived ablation cannot be constructed at all. A missing measurement must abort
#: the cycle rather than be scored as a candidate failure.
fragile_candidate_body = _configured(
    {"t0", "t1", "t2"},
    {},
    {FRAGILE_ACQUISITION},
    target=FRAGILE_BODY,
)


def migrated_lossy_body():
    """A translation that drops what the lineage could do. The migration must refuse it.

    Nothing in the *state* comparison notices this body: it carries every component, every
    certificate and every acquisition. It simply cannot do the work any more.
    """
    return RecordBody({"t0", "t1"}, ("read",))


def translate_to_record_store(departing, operations):
    """A translation that actually exercises the capability it declares.

    `used_operations` used to be a list the caller wrote, and the migration believed it. It is now
    derived from which capability handles the translation invoked, so a translator has to *use*
    `read` to be recorded as having used it — which this does, by reading a probe task through the
    substrate before committing to a body.
    """
    probed = operations["read"]({"task_id": "translation-probe"})
    if probed != "translation-probe":
        raise RuntimeError("this substrate does not read the way the lineage discovered it does")
    return migrated_parent_body


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
