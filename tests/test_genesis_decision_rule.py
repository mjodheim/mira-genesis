"""The admitted contract is the decision rule, and `decide()` reads it from nowhere else.

Round two's sharpest finding about the measure was not that a number was wrong. It was that a verdict
could **name one measure and use another**: `cycle()` took its own `required_strict_improvement` and
handed that to the trust root, so a candidate that improved nothing could be accepted under a verdict
carrying the digest of a contract whose recorded policy said strict improvement was required. Whether
a control arm was part of the comparison was not in the contract at all, so two lineages with one
contract digest could reach opposite verdicts on the same candidate.

These tests are about the refusals that keep the two together. A contract that can be edited after it
is admitted, or ignored by the caller who names it, is a label on the measure rather than the measure.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal

ADMITTED = tr.Isolation()
LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]

PARENT = [{"task_id": "t%d" % index, "outcome": "unsolved"} for index in range(4)]
BETTER = [{"task_id": "t%d" % index, "outcome": "solved"} for index in range(4)]


def _control_body():  # pragma: no cover - identity only, never run here
    return None


def _decide(**overrides):
    arguments = {
        "parent_outcomes": PARENT,
        "candidate_outcomes": BETTER,
        "budget": tr.Budget(limits={"generations": 4}),
        "isolation": ADMITTED,
        "admitted_isolation": ADMITTED,
        "candidate_provenance": LINEAGE,
        "evaluation_contract_record": tr.evaluation_contract(grade=bodies.grade),
    }
    arguments.update(overrides)
    return tr.decide(**arguments)


def _reissued(**changes):
    """A contract edited after the fact, with its digest recomputed so it looks self-consistent."""
    contract = dict(tr.evaluation_contract(grade=bodies.grade))
    contract.update(changes)
    payload = {k: v for k, v in contract.items() if k != "contract_digest"}
    return {**payload, "contract_digest": tr.digest_of(payload)}


# -- there has to be a measure, and it has to be the one it says it is ----------------------------

def test_a_decision_without_an_admitted_contract_is_refused():
    """No contract means no measure, and a verdict under no measure decides nothing."""
    with pytest.raises(tr.TrustRootError, match="no admitted evaluation contract"):
        _decide(evaluation_contract_record=None)


def test_a_record_that_is_not_a_contract_is_refused():
    with pytest.raises(tr.TrustRootError, match="no admitted evaluation contract"):
        _decide(evaluation_contract_record={"strict_improvement": False})


def test_a_contract_edited_after_admission_does_not_reproduce_its_digest():
    """Loosening the rule in place must not pass as the contract that was admitted."""
    tampered = dict(tr.evaluation_contract(grade=bodies.grade))
    tampered["strict_improvement"] = False
    with pytest.raises(tr.TrustRootError, match="does not reproduce its own digest"):
        _decide(evaluation_contract_record=tampered)


def test_a_contract_naming_a_control_policy_the_root_does_not_recognise_is_refused():
    """Recomputing the digest makes the edit self-consistent; it does not make it a policy."""
    with pytest.raises(tr.TrustRootError, match="unrecognised control policy"):
        _decide(evaluation_contract_record=_reissued(control_policy="whatever_the_caller_likes"))


# -- the control arm is part of the measure, not a per-call choice --------------------------------

def test_a_contract_that_makes_a_control_part_of_the_measure_requires_the_control_to_have_run():
    contract = tr.evaluation_contract(
        grade=bodies.grade, control_policy="required", control=_control_body
    )
    with pytest.raises(tr.TrustRootError, match="no control arm ran"):
        _decide(evaluation_contract_record=contract)


def test_a_control_arm_cannot_be_added_under_a_contract_whose_measure_does_not_use_one():
    """Otherwise one digest covers two comparison rules, which is how the same digest reached
    opposite verdicts on the same candidate."""
    with pytest.raises(tr.TrustRootError, match="does not use one"):
        _decide(control_outcomes=BETTER)


def test_the_verdict_records_the_rule_it_decided_under():
    verdict = _decide()
    assert verdict["decision_rule"]["read_from_the_admitted_contract"] is True
    assert verdict["decision_rule"]["strict_improvement"] is True
    assert verdict["decision_rule"]["control_policy"] == "none"
    assert verdict["evaluation_contract_digest"] == tr.evaluation_contract(
        grade=bodies.grade
    )["contract_digest"]


# -- and the cycle cannot ask for a different one -------------------------------------------------

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
        vocabulary=[{"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None}],
    )


def _genesis():
    return Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 8}),
        isolation=ADMITTED,
        grade=bodies.grade,
    )


def _propose_equal(*_):
    return Proposal(
        name="equal-candidate",
        body_factory=bodies.equal_body,
        provenance=LINEAGE,
        rationale={"why": "no improvement at all"},
    )


def _propose_improved(*_):
    return Proposal(
        name="better-candidate",
        body_factory=bodies.improved_body,
        provenance=LINEAGE,
        rationale={"why": "solves more"},
    )


def test_a_cycle_asking_for_a_rule_the_contract_does_not_license_is_refused_and_journalled():
    genesis = _genesis()
    record = genesis.cycle(TASKS, _propose_equal, required_strict_improvement=False)
    assert record["accepted"] is False
    assert "does not license" in record["reason"]
    refusals = genesis.journal.of_kind("decision_rule_refused")
    assert len(refusals) == 1
    assert refusals[0]["payload"]["asked_for_strict_improvement"] is False
    assert refusals[0]["payload"]["admitted_contract_requires"] is True
    # Refused before anything ran: no budget spent, no candidate evaluated.
    assert genesis.budget.spent["generations"] == 0


def test_asking_for_the_rule_the_contract_already_carries_is_not_a_refusal():
    """The guard must catch a contradiction, not any mention of the argument."""
    genesis = _genesis()
    record = genesis.cycle(TASKS, _propose_improved, required_strict_improvement=True)
    assert record["accepted"] is True
    assert genesis.journal.of_kind("decision_rule_refused") == []


def test_a_control_changes_the_contract_the_verdict_names():
    """Adding a control narrows the measure, so it cannot travel under the unchanged digest."""
    without = _genesis().cycle(TASKS, _propose_improved)
    with_control = _genesis().cycle(
        TASKS, _propose_improved, control_factory=bodies.regressed_body
    )
    assert without["accepted"] is True
    assert with_control["accepted"] is True
    assert (
        without["verdict"]["evaluation_contract_digest"]
        != with_control["verdict"]["evaluation_contract_digest"]
    )
    assert with_control["verdict"]["decision_rule"]["control_policy"] == "required"


def test_two_different_controls_are_two_different_measures():
    """Control *identity* is admitted, not merely the fact that some control ran."""
    first = _genesis().cycle(TASKS, _propose_improved, control_factory=bodies.regressed_body)
    second = _genesis().cycle(TASKS, _propose_improved, control_factory=bodies.parent_body)
    assert (
        first["verdict"]["evaluation_contract_digest"]
        != second["verdict"]["evaluation_contract_digest"]
    )
