"""Three interactive worlds whose observations are not request/value pairs.

M087's experiment space was `fam.acquirable_requests` — a literal tuple of eight strings written by
a person and passed into `execute_policy`. The lineage filtered it and ranked it. It never built
one. That is the layer this milestone removes, so the first thing that has to change is what an
experiment *is*: here it is a **program of interaction steps** executed against a stateful world,
and the world hands out a small vocabulary of primitives rather than an enumerated list of probes.

Each world is a real deterministic state machine. Running a program means running it: `reset`, then
one transition per step, with the observation read from the state that actually resulted. Nothing
is looked up.

The three worlds are structurally different on purpose. A protocol whose meaning lives in the order
of messages, a graph whose meaning lives in the path taken, and a service whose meaning lives in
what is durable. What they share is only the shape of the epistemic problem: several candidate
models of the world agree on everything observable at depth one, and separate only when actions are
composed.

Nothing here knows which candidate is true. `truth_id` is read by the evaluator and by nothing that
the lineage can reach.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


WORLDS = ("stateful_protocol", "path_graph", "durable_service")


class WorldError(RuntimeError):
    """Raised when a program uses a primitive the world does not offer."""


@dataclass(frozen=True)
class Primitive:
    """One interaction the world offers. A primitive is not an experiment."""

    name: str
    # `True` when the primitive returns an observation rather than only changing state. The
    # lineage has to discover which ones these are; the constructor is not told.
    observing: bool

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "observing": self.observing}


# --------------------------------------------------------------------------------------------
# world definitions
# --------------------------------------------------------------------------------------------


def _protocol_transition(state: tuple[str, ...], action: str) -> tuple[str, ...]:
    return state + (action,)


def _protocol_truth(history: Sequence[str]) -> str:
    sends = [item for item in history if item in {"send_a", "send_b"}]
    if not sends:
        return "ready"
    if sends[:2] == ["send_a", "send_b"]:
        return "unlocked"
    if sends[:2] == ["send_b", "send_a"]:
        return "error"
    return "ack"


def _protocol_memoryless(history: Sequence[str]) -> str:
    sends = [item for item in history if item in {"send_a", "send_b"}]
    return "ack" if sends else "ready"


def _protocol_count(history: Sequence[str]) -> str:
    sends = [item for item in history if item in {"send_a", "send_b"}]
    if not sends:
        return "ready"
    return "unlocked" if len(sends) >= 2 else "ack"


def _protocol_always_ack(history: Sequence[str]) -> str:
    return "ack" if history else "ready"


def _graph_truth(history: Sequence[str]) -> str:
    path = [item for item in history if item.startswith("follow_")]
    if not path:
        return "node_root"
    if path[:2] == ["follow_x", "follow_y"]:
        return "node_leaf"
    if path[:2] == ["follow_y", "follow_x"]:
        return "node_trap"
    return "node_mid"


def _graph_symmetric(history: Sequence[str]) -> str:
    path = [item for item in history if item.startswith("follow_")]
    if not path:
        return "node_root"
    return "node_leaf" if len(path) >= 2 else "node_mid"


def _graph_depth_blind(history: Sequence[str]) -> str:
    path = [item for item in history if item.startswith("follow_")]
    return "node_mid" if path else "node_root"


def _graph_first_edge(history: Sequence[str]) -> str:
    """Only the first edge matters. Agrees with the truth at depth one and diverges after."""

    path = [item for item in history if item.startswith("follow_")]
    if not path:
        return "node_root"
    return "node_mid" if path[0] == "follow_x" else "node_trap"


def _service_truth(history: Sequence[str]) -> str:
    written = False
    durable = False
    for action in history:
        if action == "write":
            written = True
        elif action == "flush":
            if written:
                durable = True
        elif action == "crash":
            written = False
    if durable:
        return "durable"
    return "buffered" if written else "empty"


def _service_write_through(history: Sequence[str]) -> str:
    written = any(action == "write" for action in history)
    if any(action == "crash" for action in history):
        written = "write" in history[history.index("crash") + 1:] if "crash" in history else False
    return "durable" if written else "empty"


def _service_never_durable(history: Sequence[str]) -> str:
    return "buffered" if any(action == "write" for action in history) else "empty"


def _service_flush_only(history: Sequence[str]) -> str:
    if any(action == "flush" for action in history):
        return "durable"
    return "buffered" if any(action == "write" for action in history) else "empty"


@dataclass(frozen=True)
class World:
    """A deterministic interactive system, its vocabulary, and the candidate models of it."""

    world_id: str
    primitives: tuple[Primitive, ...]
    candidates: Mapping[str, Callable[[Sequence[str]], str]]
    truth_id: str
    public_program: tuple[str, ...]
    hidden_programs: tuple[tuple[str, ...], ...]

    @property
    def action_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.primitives if not item.observing)

    @property
    def observer_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.primitives if item.observing)

    def execute(self, program: Sequence[str]) -> str:
        """Run a program against the real world and return what was observed.

        The world is the source of truth about itself. This is not the evaluator: it answers
        "what happens if I do this", which is what interacting with the system tells anyone who
        interacts with it. The evaluator answers "is this candidate right", on programs nobody may
        run, and is a different object entirely.
        """

        known = {item.name for item in self.primitives}
        history: list[str] = []
        for step in program:
            if step not in known:
                raise WorldError(f"{self.world_id}: unknown primitive {step!r}")
            if step == "reset":
                history = []
                continue
            if step in self.observer_names:
                continue
            history.append(step)
        return self.candidates[self.truth_id](history)

    def predict(self, candidate_id: str, program: Sequence[str]) -> str:
        """What one candidate model says the same program would produce."""

        if candidate_id not in self.candidates:
            raise WorldError(f"{self.world_id}: unknown candidate {candidate_id!r}")
        known = {item.name for item in self.primitives}
        history: list[str] = []
        for step in program:
            if step not in known:
                raise WorldError(f"{self.world_id}: unknown primitive {step!r}")
            if step == "reset":
                history = []
                continue
            if step in self.observer_names:
                continue
            history.append(step)
        return self.candidates[candidate_id](history)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "world_id": self.world_id,
            "primitives": [item.to_dict() for item in self.primitives],
            "candidate_ids": sorted(self.candidates),
            "public_program": list(self.public_program),
            "hidden_program_count": len(self.hidden_programs),
        }


def stateful_protocol_world() -> World:
    """Meaning lives in the ORDER of messages. `a` then `b` unlocks; `b` then `a` faults."""

    return World(
        world_id="stateful_protocol",
        primitives=(
            Primitive("reset", False), Primitive("send_a", False),
            Primitive("send_b", False), Primitive("observe", True),
        ),
        candidates={
            "order_sensitive": _protocol_truth,
            "memoryless": _protocol_memoryless,
            "count_based": _protocol_count,
            "always_ack": _protocol_always_ack,
        },
        truth_id="order_sensitive",
        public_program=("reset", "send_a", "observe"),
        hidden_programs=(
            ("reset", "send_a", "send_b", "send_a", "observe"),
            ("reset", "send_b", "send_a", "send_b", "observe"),
        ),
    )


def path_graph_world() -> World:
    """Meaning lives in the PATH taken. `x` then `y` reaches a leaf; `y` then `x` a trap."""

    return World(
        world_id="path_graph",
        primitives=(
            Primitive("reset", False), Primitive("follow_x", False),
            Primitive("follow_y", False), Primitive("observe", True),
        ),
        candidates={
            "path_sensitive": _graph_truth,
            "symmetric_depth": _graph_symmetric,
            "depth_blind": _graph_depth_blind,
            "first_edge_only": _graph_first_edge,
        },
        truth_id="path_sensitive",
        public_program=("reset", "follow_x", "observe"),
        hidden_programs=(
            ("reset", "follow_x", "follow_y", "follow_x", "observe"),
            ("reset", "follow_y", "follow_x", "follow_y", "observe"),
        ),
    )


def durable_service_world() -> World:
    """Meaning lives in DURABILITY. A write is buffered until flushed, and a crash discards it."""

    return World(
        world_id="durable_service",
        primitives=(
            Primitive("reset", False), Primitive("write", False),
            Primitive("flush", False), Primitive("crash", False), Primitive("observe", True),
        ),
        candidates={
            "buffered_until_flush": _service_truth,
            "write_through": _service_write_through,
            "never_durable": _service_never_durable,
            "flush_only": _service_flush_only,
        },
        truth_id="buffered_until_flush",
        public_program=("reset", "write", "observe"),
        hidden_programs=(
            ("reset", "write", "flush", "crash", "observe"),
            ("reset", "write", "crash", "flush", "observe"),
        ),
    )


# --------------------------------------------------------------------------------------------
# qualification materialization
# --------------------------------------------------------------------------------------------
#
# The hidden programs above are DEVELOPMENT ones. The qualifying set is drawn from a salt released
# only after the adopted constructor has been committed by digest, so the chronology is a recorded
# fact rather than a promise -- the defect that disqualified M086-A.
#
# Every program in every pool uses THREE actions. The adopted constructor composes at most two, so
# no hidden program lies inside its constructive image: the lineage cannot build one, and therefore
# cannot run one, whatever it does. That is a structural no-leak guarantee rather than a rule about
# which requests are allowed, and `hidden_outside_constructive_image` checks it.

QUALIFICATION_POOL: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "stateful_protocol": (
        ("reset", "send_a", "send_b", "send_a", "observe"),
        ("reset", "send_b", "send_a", "send_b", "observe"),
        ("reset", "send_a", "send_a", "send_b", "observe"),
        ("reset", "send_b", "send_b", "send_a", "observe"),
    ),
    "path_graph": (
        ("reset", "follow_x", "follow_y", "follow_x", "observe"),
        ("reset", "follow_y", "follow_x", "follow_y", "observe"),
        ("reset", "follow_x", "follow_x", "follow_y", "observe"),
        ("reset", "follow_y", "follow_y", "follow_x", "observe"),
    ),
    "durable_service": (
        ("reset", "write", "flush", "crash", "observe"),
        ("reset", "write", "crash", "flush", "observe"),
        ("reset", "crash", "write", "flush", "observe"),
        ("reset", "flush", "write", "crash", "observe"),
    ),
}


def materialize_qualification(
    world_id: str, salt: str, count: int = 2,
) -> tuple[tuple[str, ...], ...]:
    """Draw this world's qualifying hidden programs from a post-adoption salt."""

    import hashlib as _hashlib

    pool = QUALIFICATION_POOL[world_id]
    order = sorted(
        range(len(pool)),
        key=lambda index: _hashlib.sha256(
            f"m088-qualification-v1|{world_id}|{salt}|{index}".encode("utf-8")
        ).hexdigest(),
    )
    return tuple(pool[index] for index in sorted(order[:count]))


def qualified_world(world_id: str, salt: str) -> World:
    """The world with its hidden programs replaced by the post-adoption draw."""

    from dataclasses import replace as _replace

    return _replace(world(world_id), hidden_programs=materialize_qualification(world_id, salt))


def world(world_id: str) -> World:
    builders = {
        "stateful_protocol": stateful_protocol_world,
        "path_graph": path_graph_world,
        "durable_service": durable_service_world,
    }
    if world_id not in builders:
        raise WorldError(f"unknown world {world_id!r}")
    return builders[world_id]()


def all_worlds() -> tuple[World, ...]:
    return tuple(world(name) for name in WORLDS)


__all__ = [
    "Primitive", "WORLDS", "World", "WorldError", "all_worlds", "durable_service_world",
    "path_graph_world", "stateful_protocol_world", "world",
]
