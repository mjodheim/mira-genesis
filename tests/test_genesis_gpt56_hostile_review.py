"""Counterexamples found by the GPT-5.6 hostile review of PR #275.

These tests are intentionally written before the fixes. Each one captures a property the runtime
currently claims more strongly than its implementation supports. The review branch is expected to
be red until the corresponding mechanism is tightened; deleting or weakening a test is not a fix.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal, task_set_digest


LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _seed_state(*, acquisitions=()):
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
        acquisitions=list(acquisitions),
    )


def _genesis(*, state=None, generations=6, body=bodies.parent_body):
    return Genesis(
        state=state or _seed_state(),
        body_factory=body,
        budget=tr.Budget(limits={"generations": generations}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def test_task_identity_covers_the_question_not_only_its_label():
    """Reusing IDs with easier contents must not turn a new verification set into an old one."""
    evaluated = [
        {"task_id": "same-0", "input": 100, "expected": 999},
        {"task_id": "same-1", "input": 200, "expected": 999},
    ]
    substituted = [
        {"task_id": "same-0", "input": 0, "expected": 0},
        {"task_id": "same-1", "input": 1, "expected": 1},
    ]
    assert task_set_digest(evaluated) != task_set_digest(substituted)


def test_restore_does_not_reset_a_spent_generation_budget(tmp_path):
    """Process death must not manufacture a fresh allowance."""
    genesis = _genesis(generations=2)
    genesis.cycle(TASKS, lambda *_: None)
    assert genesis.budget.spent["generations"] == 1
    genesis.persist(tmp_path)

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 2}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    assert restored.budget.spent["generations"] == 1


def test_restore_refuses_a_different_executable_body(tmp_path):
    """A persisted lineage cannot wake up in an arbitrary caller-supplied body under the same state."""
    genesis = _genesis(body=bodies.parent_body)
    genesis.persist(tmp_path)

    with pytest.raises(tr.TrustRootError, match="body"):
        Genesis.restore(
            tmp_path,
            body_factory=bodies.improved_body,
            budget=tr.Budget(limits={"generations": 6}),
            isolation=tr.Isolation(),
            grade=bodies.grade,
        )


def test_create_state_revalidates_acquired_component_certificate_semantics():
    """A self-consistent digest is not evidence that the prior registry was exhausted."""
    forged = {
        "schema": st.COMPONENT_CERTIFICATE_SCHEMA,
        "prior_registry": ["operator_table"],
        "new_component": "joint_registry",
        "demand_digest": "d",
        # The only held component was never probed. The certificate builder refuses this shape.
        "probe_records": [],
        "prior_registry_exhausted": True,
        "resolves_with_new_component": True,
    }
    forged["certificate_digest"] = tr.digest_of(forged)

    with pytest.raises(st.StateError, match="never probed"):
        st.create_state(
            body_digest="b0",
            components=[
                {
                    "name": "operator_table",
                    "origin": "seed",
                    "certificate": None,
                    "provenance": tr.provenance("host_written", produced_by="seed"),
                },
                {
                    "name": "joint_registry",
                    "origin": "acquired",
                    "certificate": forged,
                    "provenance": LINEAGE,
                },
            ],
            vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
        )


def test_adoption_cannot_trade_away_a_parent_solved_task_for_a_larger_total():
    """Retention means keeping solved work, not merely increasing a scalar score."""
    parent = [
        {"task_id": "t0", "outcome": "solved"},
        {"task_id": "t1", "outcome": "solved"},
        {"task_id": "t2", "outcome": "unsolved"},
        {"task_id": "t3", "outcome": "unsolved"},
    ]
    candidate = [
        {"task_id": "t0", "outcome": "unsolved"},  # forgot something the parent knew
        {"task_id": "t1", "outcome": "solved"},
        {"task_id": "t2", "outcome": "solved"},
        {"task_id": "t3", "outcome": "solved"},
    ]
    verdict = tr.decide(
        parent_outcomes=parent,
        candidate_outcomes=candidate,
        budget=tr.Budget(limits={"generations": 1}),
        isolation=tr.Isolation(),
        admitted_isolation=tr.Isolation(),
        candidate_provenance=LINEAGE,
        evaluation_contract_record=tr.evaluation_contract(grade=bodies.grade),
    )
    assert verdict["accepted"] is False
    assert verdict["lost_solved_tasks"] == ["t0"]


def test_an_arbitrary_bad_body_cannot_be_presented_as_a_causal_ablation():
    """`depends_on` must name and remove a real acquisition; a weak unrelated body proves nothing."""
    prior = {
        "name": "real_prior_acquisition",
        "generation": 0,
        "verdict_digest": "v0",
        "provenance": LINEAGE,
        "causal_dependency": {"established": False},
    }
    genesis = _genesis(state=_seed_state(acquisitions=[prior]))

    def propose(*_):
        return Proposal(
            name="candidate",
            body_factory=bodies.improved_body,
            provenance=LINEAGE,
            rationale={"why": "counterexample"},
            # This is simply a deliberately worse body; it is not the candidate minus an acquisition.
            ablated_body_factory=bodies.regressed_body,
            depends_on="made_up_acquisition",
        )

    record = genesis.cycle(TASKS, propose)
    assert record["causal_dependency"]["established"] is False
    assert "made_up_acquisition" in record["causal_dependency"]["why"]
