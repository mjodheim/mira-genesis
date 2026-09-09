"""Executable deserialisation may not cross the candidate/evaluator boundary."""
from __future__ import annotations

import functools
from pathlib import Path

import pytest

from genesis import hostile_fixtures
from genesis import sandbox as sb
from genesis import trust_root as tr


def _grade_never_solves(_task, _answer):
    return "unsolved"


class _HarmlessBody:
    def attempt(self, task):
        return 0


def _harmless_body_factory():
    return _HarmlessBody()


def _reconstruct_factory_before_child_limits(path: str):
    Path(path).write_text("executed before child limits existed", encoding="utf-8")
    return _harmless_body_factory


class _FactoryWhoseUnpickleHasASideEffect:
    def __init__(self, path: str) -> None:
        self.path = path

    def __call__(self):
        return _HarmlessBody()

    def __reduce__(self):
        return (_reconstruct_factory_before_child_limits, (self.path,))


def test_live_factory_object_is_refused_without_deserialising_it(tmp_path):
    marker = tmp_path / "child-unpickle-before-limits.txt"
    with pytest.raises(sb.SandboxError, match="refuses to pickle|live callable"):
        sb.run_candidate(
            _FactoryWhoseUnpickleHasASideEffect(str(marker)),
            [{"task_id": "t0", "input": 0}],
            tr.Isolation(),
            grade=_grade_never_solves,
        )
    assert not marker.exists()


def test_candidate_answer_cannot_execute_code_in_the_evaluator_on_receive(tmp_path):
    marker = tmp_path / "parent-unpickle-executed.txt"
    result = sb.run_candidate(
        functools.partial(hostile_fixtures.pickle_escape_body, str(marker)),
        [{"task_id": "t0", "input": 0}],
        tr.Isolation(),
        grade=_grade_never_solves,
    )
    assert not marker.exists()
    assert result["outcomes"] == [{"task_id": "t0", "outcome": "error"}]
    assert result["transport_format"] == "canonical-json"
    assert result["uses_executable_deserialization"] is False
    assert result["candidate_loaded_after_limits"] is True
