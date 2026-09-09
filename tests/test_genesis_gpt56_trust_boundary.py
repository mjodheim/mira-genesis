"""Trust-boundary counterexamples found after the first GPT-5.6 review pass.

They are intentionally red until the runtime stops handing lineage-owned proposal code authority over
its evaluator and admission envelope. These are DEVELOPMENT apparatus tests, not scientific evidence.
"""
from __future__ import annotations

from genesis import development_bodies as bodies
from genesis import migration as mg
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal, task_set_digest


LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _seed_state():
    return st.create_state(
        body_digest="b0",
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


def _genesis(*, body=bodies.parent_body, generations=4):
    return Genesis(
        state=_seed_state(),
        body_factory=body,
        budget=tr.Budget(limits={"generations": generations}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def test_proposer_cannot_replace_the_lineage_body_without_an_adoption():
    genesis = _genesis()
    original = genesis.body_factory

    def propose(runtime, _tasks):
        runtime.body_factory = bodies.improved_body
        return None

    record = genesis.cycle(TASKS, propose)
    assert record["accepted"] is False
    assert genesis.body_factory is original


def test_proposer_cannot_replace_the_budget_or_evaluator_between_arms():
    genesis = _genesis(generations=2)
    original_budget = genesis.budget
    original_grade = genesis.grade

    def grade_everything_as_solved(_task, _answer):
        return "solved"

    def propose(runtime, _tasks):
        runtime.budget = tr.Budget(limits={"generations": 999})
        runtime.grade = grade_everything_as_solved
        return None

    genesis.cycle(TASKS, propose)
    assert genesis.budget is original_budget
    assert genesis.budget.limits["generations"] == 2
    assert genesis.grade is original_grade


def test_proposal_digest_changes_when_the_executable_candidate_changes():
    common = {
        "name": "same-metadata",
        "provenance": LINEAGE,
        "rationale": {"why": "same"},
    }
    first = Proposal(body_factory=bodies.parent_body, **common)
    second = Proposal(body_factory=bodies.improved_body, **common)
    assert first.digest() != second.digest()


def test_an_instrument_abort_does_not_mark_the_task_set_as_evaluated():
    genesis = _genesis(body=bodies.unconstructible_body)
    record = genesis.cycle(TASKS, lambda *_: None)
    assert record["instrument_abort"] is True
    assert task_set_digest(TASKS) not in genesis.evaluated_task_digests


def test_metamorphosis_success_requires_measured_preserved_capability():
    migration = {
        "journal_continues": True,
        "used_only_discovered_operations": True,
        "carried": {},
        "capability": {
            "measured": False,
            "preserved": None,
            "why": "no tasks were supplied",
        },
    }
    later = [
        {
            "accepted": True,
            "causal_dependency": {"established": True},
        }
    ]
    outcome = mg.metamorphosis_succeeded(migration, later)
    assert outcome["succeeded"] is False
    assert any("capability" in reason for reason in outcome["reasons"])
