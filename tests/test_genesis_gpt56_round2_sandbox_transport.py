"""The candidate/parent transport must not deserialize candidate-controlled Python objects."""
from __future__ import annotations

import functools
from pathlib import Path

from genesis import sandbox as sb
from genesis import trust_root as tr


def _mark_parent_unpickle(path: str):
    """Harmless proof that deserialising one answer executed code in the parent process."""
    Path(path).write_text("executed while parent deserialised candidate output", encoding="utf-8")
    return "ordinary-answer-after-side-effect"


class _PicklePayload:
    def __init__(self, path: str) -> None:
        self.path = path

    def __reduce__(self):
        # multiprocessing.Connection uses pickle. The callable in this reduction is executed by the
        # process that *unpickles* the object, which is the evaluator/parent rather than the sandbox.
        return (_mark_parent_unpickle, (self.path,))


class _PickleEscapeBody:
    def __init__(self, path: str) -> None:
        self.path = path

    def attempt(self, task):
        return _PicklePayload(self.path)


def _grade_never_solves(_task, _answer):
    return "unsolved"


class _HarmlessBody:
    def attempt(self, task):
        return 0


def _harmless_body_factory():
    return _HarmlessBody()


def _reconstruct_factory_before_child_limits(path: str):
    """Runs during spawn's unpickle, before sandbox._child has called `_apply_limits`."""
    Path(path).write_text("executed before sandbox limits were installed", encoding="utf-8")
    return _harmless_body_factory


class _FactoryWhoseUnpickleHasASideEffect:
    def __init__(self, path: str) -> None:
        self.path = path

    def __reduce__(self):
        return (_reconstruct_factory_before_child_limits, (self.path,))


def test_body_factory_transport_cannot_execute_before_sandbox_limits_are_installed(tmp_path):
    """The fixed child bootstrap must install limits before it resolves any untrusted artifact."""
    marker = tmp_path / "child-unpickle-before-limits.txt"
    result = sb.run_candidate(
        _FactoryWhoseUnpickleHasASideEffect(str(marker)),
        [{"task_id": "t0", "input": 0}],
        tr.Isolation(),
        grade=_grade_never_solves,
    )

    assert not marker.exists()
    assert result["completed"] is False or result["outcomes"] == [
        {"task_id": "t0", "outcome": "error"}
    ]


def test_candidate_output_transport_cannot_execute_code_in_the_parent_process(tmp_path):
    """A process boundary using unrestricted pickle is not a boundary against an untrusted body."""
    marker = tmp_path / "parent-unpickle-executed.txt"
    result = sb.run_candidate(
        functools.partial(_PickleEscapeBody, str(marker)),
        [{"task_id": "t0", "input": 0}],
        tr.Isolation(),
        grade=_grade_never_solves,
    )

    # The exact safe failure mode is an implementation choice: reject the answer type, reject the
    # message, or use a non-executable serialization format. What may never happen is execution in
    # the parent merely because it decoded a candidate-controlled result.
    assert not marker.exists()
    assert result["completed"] is False or result["outcomes"] == [
        {"task_id": "t0", "outcome": "error"}
    ]
