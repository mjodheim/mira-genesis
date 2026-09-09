"""A lineage that changes its own acquisition machinery, and is made to earn it.

The objective asks for a program that modifies its body *and progressively its own machinery of
acquisition*. The body half is `SearchTransform`. This is the other half: the rule that decides what
to attempt is itself lineage-held state, and replacing it is a transaction with evidence rather than
a caller passing a different callback.

What makes it evidence: both policies drive a fork of the **same** committed lineage, with the same
world, the same allowance and the same number of steps, and the descendants they produce are compared
by the unchanged trust root under the admitted contract. Neither policy grades anything. A policy is
adopted for what it caused, never for what it says about itself — which is the same separation that
makes a candidate body's adoption mean something, applied one level up.

DEVELOPMENT apparatus. Two fixture policies over a four-operation alphabet establish that the
transaction exists and refuses what it claims to refuse; they establish nothing about generality.
"""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import search_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="policy-update fixture")


def _genesis(**overrides):
    state = st.create_state(
        body_digest="seed",
        components=[
            {"name": "operator_table", "origin": "seed", "certificate": None, "provenance": HOST}
        ],
        vocabulary=[{"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None}],
    )
    arguments = {
        "state": state,
        "body_factory": fixtures.seed_body,
        "budget": tr.Budget(limits={"generations": 200, "probes": 200}),
        "isolation": tr.Isolation(),
        "grade": fixtures.graded_against_expected,
    }
    arguments.update(overrides)
    return Genesis(**arguments)


def _under(policy, *, steps=1):
    """A lineage already admitted under one policy, ready to be asked to change it.

    `steps=0` admits the policy without letting it act, which is what a comparison needs when the
    question is what each policy *would* produce from the same starting point.
    """
    genesis = _genesis()
    controller.run(genesis, fixtures.policy_world(), policy, max_steps=steps)
    return genesis


def _digest(genesis):
    return (controller.bound_mechanism_artifact(genesis) or {}).get("artifact_digest", "")


# -- the transaction -----------------------------------------------------------------------------

def test_a_policy_whose_descendants_answer_more_replaces_the_one_in_force():
    """The machinery changes because of what it produced, measured by something outside both."""
    genesis = _under(fixtures.timid_policy)
    incumbent = _digest(genesis)

    outcome = controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="bolder", steps=2)
    )

    assert outcome["policy_updated"] is True
    assert outcome["incumbent_solved"] < outcome["candidate_solved"]
    assert outcome["descendants_compared_by"] == "genesis.trust_root.decide"
    assert outcome["graded_by_either_policy"] is False
    assert _digest(genesis) == outcome["candidate_policy_digest"] != incumbent


def test_the_replacement_is_recorded_in_the_lineage_rather_than_in_the_caller():
    """Machinery is state. A policy the journal does not record is a caller's variable."""
    genesis = _under(fixtures.timid_policy)
    controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="bolder", steps=2)
    )
    updates = [
        entry
        for entry in genesis.journal.of_kind("observation")
        if entry["payload"].get("arm") == "controller_mechanism_update"
    ]
    assert len(updates) == 1
    assert updates[0]["payload"]["artifact_digest"] == _digest(genesis)
    assert "beat" in updates[0]["payload"]["why"]
    assert genesis.checkpoint()["state_digest"] == genesis.state["state_digest"]


def test_a_policy_update_survives_process_death(tmp_path):
    genesis = _under(fixtures.timid_policy)
    controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="bolder", steps=2)
    )
    adopted = _digest(genesis)
    genesis.persist(tmp_path)

    restored = Genesis.restore(
        tmp_path, body_factory=fixtures.seed_body, grade=fixtures.graded_against_expected
    )
    assert _digest(restored) == adopted


# -- the negative controls -------------------------------------------------------------------------

def test_a_policy_whose_descendants_are_no_better_is_refused():
    """No strict improvement, no change of machinery."""
    genesis = _under(fixtures.bolder_policy, steps=0)
    incumbent = _digest(genesis)

    outcome = controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="timid", steps=2)
    )

    assert outcome["policy_updated"] is False
    assert _digest(genesis) == incumbent


def test_a_policy_that_loses_retained_capability_is_refused():
    """Retention applies to machinery too: a policy is not adopted for a trade.

    Both trials start from the seed, so the incumbent's descendants reach all six questions while
    the candidate's reach one. The candidate is refused for losing work, not merely for gaining
    less — which is the retention rule the trust root already applies to bodies, reaching machinery
    because machinery is judged the same way.
    """
    genesis = _under(fixtures.bolder_policy, steps=0)
    outcome = controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="timid", steps=2)
    )
    assert outcome["policy_updated"] is False
    assert outcome["lost_solved_tasks"], "the weaker policy's descendants must visibly lose work"
    assert "forgot work" in outcome["reason"]


def test_a_trial_may_not_change_the_machinery_it_is_measuring():
    """A policy asking to replace itself ends its trial rather than recursing without bound.

    It is not an error for a policy to answer that. It is an answer a trial cannot act on: it says
    nothing about descendants, and acting on it would change the thing under measurement while
    measuring it — and start another trial from inside this one, without end.
    """
    genesis = _under(fixtures.adopt_the_bolder_policy, steps=0)
    record = controller.run(
        genesis,
        fixtures.policy_world(),
        fixtures.adopt_the_bolder_policy,
        max_steps=2,
        allow_policy_update=False,
    )
    assert record["steps"][0]["policy_update_refused_in_trial"] is True
    assert _digest(genesis) == tr.artifact_digest_of(fixtures.adopt_the_bolder_policy)[
        "artifact_digest"
    ], "the machinery must be exactly what it was"


def test_a_policy_the_world_does_not_admit_cannot_be_adopted():
    genesis = _under(fixtures.timid_policy)
    with pytest.raises(controller.ControllerError, match="does not admit"):
        controller._adopt_policy(
            genesis,
            fixtures.policy_world(),
            controller.AdoptPolicy(candidate="something_nobody_admitted", steps=1),
        )


def test_adopting_the_policy_already_in_force_is_not_an_update():
    genesis = _under(fixtures.timid_policy)
    with pytest.raises(controller.ControllerError, match="has to be a change"):
        controller._adopt_policy(
            genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="timid", steps=1)
        )


def test_the_trial_forks_leave_the_lineage_they_were_forked_from_alone():
    """A trial that changed the lineage would make the second policy answer a different question."""
    genesis = _under(fixtures.timid_policy)
    before_state = genesis.state["state_digest"]
    before_head = genesis.journal.head
    before_body = tr.artifact_digest_of(genesis.body_factory)
    controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="bolder", steps=2)
    )

    # The machinery changed and nothing else did: no descendant was adopted into the real lineage by
    # a trial, and the body is still the one the lineage had.
    assert tr.artifact_digest_of(genesis.body_factory) == before_body
    assert genesis.state["acquisitions"] == []
    assert genesis.state["state_digest"] != before_state, "the policy binding is state"
    assert genesis.journal.head != before_head


def test_both_policies_are_tried_from_the_same_starting_lineage():
    """Matched trials. Otherwise the comparison measures which policy went first."""
    genesis = _under(fixtures.timid_policy)
    outcome = controller._adopt_policy(
        genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="bolder", steps=2)
    )
    assert outcome["trial_steps"]["incumbent"][0] == "SearchTransform"
    assert outcome["trial_steps"]["candidate"][0] == "SearchTransform"
    assert len(outcome["trial_steps"]["incumbent"]) == len(outcome["trial_steps"]["candidate"])


def test_the_policy_change_is_reachable_through_an_ordinary_controller_run():
    """The mechanism asks for its own replacement, and the runtime performs it."""
    genesis = _genesis()
    run = controller.run(
        genesis, fixtures.policy_world(), fixtures.adopt_the_bolder_policy, max_steps=3
    )
    step = run["steps"][0]
    assert step["intent"] == "AdoptPolicy"
    assert step["policy_updated"] is True
    assert _digest(genesis) == step["candidate_policy_digest"]
