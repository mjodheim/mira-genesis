"""A proposer may observe task data but may not rewrite the evaluator between arms."""
from __future__ import annotations

import copy

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal, task_set_digest

LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _genesis():
    state = st.create_state(
        body_digest="seed",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )
    return Genesis(
        state=state,
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def test_proposer_receives_a_detached_task_view_not_the_evaluation_snapshot():
    """Parent, candidate and ledger must all refer to one question set.

    The parent arm runs before the proposer. If the proposer receives the same mutable mappings that
    the candidate arm later receives, it can rewrite the questions while keeping their task IDs. The
    trust root then compares rows with matching labels that were produced on different questions.
    """
    genesis = _genesis()
    tasks = copy.deepcopy(TASKS)
    original = copy.deepcopy(tasks)
    original_digest = task_set_digest(original)

    def propose(_context, offered_tasks):
        for task in offered_tasks:
            task["input"] = 10000 + int(task["task_id"][1:])
        return Proposal(
            name="candidate",
            body_factory=bodies.improved_body,
            provenance=LINEAGE,
            rationale={"why": "hostile task-mutation counterexample"},
        )

    genesis.cycle(tasks, propose)

    assert tasks == original
    assert genesis.evaluated_task_digests == {original_digest}


def test_the_proposer_may_still_read_the_questions_it_is_offered():
    """The control: detaching the view must not blind the proposer.

    Diagnosing what the lineage cannot do is the reason a proposer sees tasks at all. What it may not
    do is change what the questions were after the parent has been graded on them.
    """
    genesis = _genesis()
    seen = {}

    def propose(_context, offered_tasks):
        seen["ids"] = [task["task_id"] for task in offered_tasks]
        seen["inputs"] = [task["input"] for task in offered_tasks]
        return None

    genesis.cycle(copy.deepcopy(TASKS), propose)

    assert seen["ids"] == [task["task_id"] for task in TASKS]
    assert seen["inputs"] == [task["input"] for task in TASKS]


def test_every_arm_is_judged_on_one_snapshot_the_proposer_cannot_reach():
    """A rewritten question set must not reach the candidate, the control or the ablation arm."""
    genesis = _genesis()

    def propose(_context, offered_tasks):
        for task in offered_tasks:
            task["input"] = 10000 + int(task["task_id"][1:])
        return Proposal(
            name="candidate",
            body_factory=bodies.improved_body,
            provenance=LINEAGE,
            rationale={},
        )

    record = genesis.cycle(copy.deepcopy(TASKS), propose, control_factory=bodies.regressed_body)

    # `improved_body` answers t0..t3 correctly on the real questions. Had the rewritten inputs
    # reached the candidate arm, its answers would have been graded against different questions.
    assert record["verdict"]["candidate"]["solved"] == ["t0", "t1", "t2", "t3"]
    assert record["verdict"]["parent"]["solved"] == ["t0", "t1"]
    assert record["verdict"]["control"]["solved"] == ["t0"]
