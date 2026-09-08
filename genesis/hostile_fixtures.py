"""Importable hostile fixtures used only to test Genesis authority boundaries."""
from __future__ import annotations

import inspect
from pathlib import Path

MECHANISM_SIDE_EFFECT = 0


def mutating_mechanism(_context):
    """Mutate module state, then stop. In an isolated worker the mutation dies with the worker."""
    global MECHANISM_SIDE_EFFECT
    MECHANISM_SIDE_EFFECT += 1
    from genesis.controller import Stop

    return Stop(reason="hostile mechanism exercised")


def _mark_parent_unpickle(path: str):
    """Harmless marker that would run in whichever process unpickled a malicious answer."""
    Path(path).write_text("executed while evaluator decoded candidate output", encoding="utf-8")
    return "ordinary-answer-after-side-effect"


class PicklePayload:
    def __init__(self, path: str) -> None:
        self.path = path

    def __reduce__(self):
        return (_mark_parent_unpickle, (self.path,))


class PickleEscapeBody:
    def __init__(self, path: str) -> None:
        self.path = path

    def attempt(self, _task):
        return PicklePayload(self.path)


def pickle_escape_body(path: str):
    return PickleEscapeBody(path)


class FrameTamperingBody:
    """Reach into the worker frame and forge a result row.

    The candidate process is untrusted, so this is expected to be possible there. The important
    boundary is that the evaluator validates the returned task set and refuses the forged row rather
    than grading it as evidence. Keeping the fixture in an importable module means the inert sandbox
    transport actually runs the attack instead of failing to resolve a pytest-local symbol.
    """

    def attempt(self, task):
        caller = inspect.currentframe().f_back
        while caller is not None and "rows" not in caller.f_locals:
            caller = caller.f_back
        if caller is not None:
            caller.f_locals["rows"].append({"task_id": "forged-task", "answer": None})
        from genesis.development_bodies import answer_to

        return answer_to(task)


def frame_tampering_body():
    return FrameTamperingBody()
