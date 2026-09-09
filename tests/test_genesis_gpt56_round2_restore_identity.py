"""Restore counterexamples for callable identities that share code but differ in bound values."""
from __future__ import annotations

import functools

import pytest

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="round-two restore test")


def _seed_state():
    return st.create_state(
        body_digest="b0",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _body(*task_ids):
    return functools.partial(bodies.TableBody, set(task_ids))


def _parameterized_grade(mode, task, answer):
    if mode == "honest":
        return bodies.grade(task, answer)
    return "solved"


def test_restore_refuses_different_partial_body_even_when_underlying_symbol_matches(tmp_path):
    original = _body("t0", "t1")
    replacement = _body("t0", "t1", "t2", "t3")
    genesis = Genesis(
        state=_seed_state(),
        body_factory=original,
        budget=tr.Budget(limits={"generations": 4}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    genesis.persist(tmp_path)

    with pytest.raises(tr.TrustRootError, match="body"):
        Genesis.restore(
            tmp_path,
            body_factory=replacement,
            grade=bodies.grade,
        )


def test_restore_refuses_different_partial_grader_even_when_underlying_symbol_matches(tmp_path):
    honest = functools.partial(_parameterized_grade, "honest")
    always_solved = functools.partial(_parameterized_grade, "always-solved")
    genesis = Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 4}),
        isolation=tr.Isolation(),
        grade=honest,
    )
    genesis.persist(tmp_path)

    with pytest.raises(tr.TrustRootError, match="evaluator|grader|contract"):
        Genesis.restore(
            tmp_path,
            body_factory=bodies.parent_body,
            grade=always_solved,
        )
