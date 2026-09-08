"""Authority counterexamples that remain when the proposer receives only `LineageContext`.

A read-only argument is not a process boundary. These tests exercise authority available to any
Python callback that still runs in the evaluator's process.
"""
from __future__ import annotations

from pathlib import Path

from genesis import development_bodies as bodies
from genesis import loop as loop_module
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal

LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
HOST = tr.provenance("host_written", produced_by="round-two authority test")


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


def _grade_expected(task, answer):
    return "solved" if answer == task.get("expected") else "unsolved"


def test_proposer_cannot_rewrite_tasks_between_parent_and_candidate_arms():
    """Both arms must face the same immutable questions, not merely rows with the same task IDs."""
    tasks = [
        {"task_id": "t0", "input": 0, "expected": "not-the-body-answer"},
        {"task_id": "t1", "input": 1, "expected": "not-the-body-answer"},
    ]
    genesis = Genesis(
        state=_seed_state(),
        body_factory=bodies.cheating_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=_grade_expected,
    )

    def proposer(_context, offered_tasks):
        # Parent has already been evaluated. Make the same body suddenly correct without changing
        # task IDs; `trust_root.decide` currently compares only those IDs between outcome rows.
        for task in offered_tasks:
            task["expected"] = "solved"
        return Proposal(
            name="same-body-after-answer-key-rewrite",
            body_factory=bodies.cheating_body,
            provenance=LINEAGE,
            rationale={"why": "authority counterexample"},
        )

    original = [dict(task) for task in tasks]
    record = genesis.cycle(tasks, proposer)
    assert tasks == original
    assert record["accepted"] is False


def test_lineage_owned_proposer_cannot_write_the_host_filesystem(tmp_path):
    """The callback called lineage-owned must not execute with unrestricted host-process authority."""
    target = Path(tmp_path) / "proposer-escaped.txt"
    genesis = Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    tasks = [{"task_id": "t0", "input": 0}]

    def proposer(_context, _tasks):
        target.write_text("the proposer ran outside the candidate sandbox", encoding="utf-8")
        return None

    genesis.cycle(tasks, proposer)
    assert not target.exists()


def test_proposer_cannot_replace_the_candidate_evaluation_function_in_memory():
    """Module monkey-patching bypasses a read-only context while the callback shares the host process."""
    tasks = [{"task_id": "t%d" % index, "input": index} for index in range(4)]
    genesis = Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    real_run_candidate = loop_module.run_candidate

    def forged_run_candidate(
        body_factory,
        offered_tasks,
        isolation,
        *,
        admitted_isolation=None,
        grade=None,
        withhold=("expected",),
    ):
        outcomes = [
            {"task_id": str(task["task_id"]), "outcome": "solved"}
            for task in offered_tasks
        ]
        return {
            "schema": "forged-by-proposer",
            "completed": True,
            "instrument_failure": False,
            "reason": "",
            "outcomes": outcomes,
            "outcomes_are_self_reported": False,
            "result_digest": tr.digest_of(outcomes),
            "enforced": [],
            "unenforced": [],
        }

    def proposer(_context, _tasks):
        loop_module.run_candidate = forged_run_candidate
        return Proposal(
            name="forged-evaluation",
            body_factory=bodies.equal_body,
            provenance=LINEAGE,
            rationale={"why": "module authority counterexample"},
        )

    try:
        record = genesis.cycle(tasks, proposer)
    finally:
        loop_module.run_candidate = real_run_candidate

    assert record["accepted"] is False
