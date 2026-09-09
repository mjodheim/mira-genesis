"""Hostile tests for the G9 human-baseline intake.

The interesting cases are not malformed JSON. They are the baselines that would look fine: the
author standing in for a participant, a baseline written after the system's numbers are known, a
task set swapped for an easier one, and a range quietly reported as a significance test.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from metamorphosis.human_baseline import (
    MINIMUM_PARTICIPANTS,
    PROTOCOL_SCHEMA,
    RESULT_SCHEMA,
    HumanBaselineError,
    assess_readiness,
    summarize,
    validate_baseline_protocol,
    validate_baseline_result,
)

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
TASK_SET = "ab" * 32


def _participant(index: int, **overrides) -> dict:
    entry = {
        "participant_id": "participant-%d" % index,
        "prior_exposure_to_tasks": False,
        "recruited_via": "an agency the project does not run",
        "compensation_basis": "hourly, flat",
        "compensation_contingent_on_outcome": False,
    }
    entry.update(overrides)
    return entry


def _protocol(**overrides) -> dict:
    protocol = {
        "schema": PROTOCOL_SCHEMA,
        "committed_before_system_evaluation": True,
        "task_set_sha256": TASK_SET,
        "coordinator_identity": "an-outside-coordinator",
        "participants": [_participant(i) for i in range(MINIMUM_PARTICIPANTS)],
        "participants_uncoached_attested": True,
        "no_decomposition_supplied_attested": True,
        "evaluator_owned_success_attested": True,
        "makes_a_significance_claim": False,
    }
    protocol.update(overrides)
    return protocol


def _digest(protocol: dict) -> str:
    return hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()


def _result(protocol: dict, **overrides) -> dict:
    result = {
        "schema": RESULT_SCHEMA,
        "protocol_sha256": _digest(protocol),
        "task_set_sha256": protocol["task_set_sha256"],
        "per_participant": [
            {
                "participant_id": entry["participant_id"],
                "tasks_attempted": 10,
                "tasks_solved": index + 3,
                "wall_clock_seconds": 1800.0,
            }
            for index, entry in enumerate(protocol["participants"])
        ],
        "cost": {
            "amount": 250.0,
            "currency": "EUR",
            "reason": None,
            "total_wall_clock_seconds": 9000.0,
        },
        "makes_a_significance_claim": False,
    }
    result.update(overrides)
    return result


def _validate_result(protocol: dict, result: dict) -> None:
    validate_baseline_result(result, protocol_sha256=_digest(protocol), protocol=protocol)


# -- the repository has no baseline and says so -------------------------------------------------

def test_no_human_baseline_exists_and_the_check_refuses() -> None:
    report = assess_readiness(ROOT)
    assert report["human_baseline_available"] is False
    assert report["summary"] is None
    assert any("HUMAN_BASELINE_PROTOCOL" in blocker for blocker in report["blockers"])


# -- who may stand in for a human ---------------------------------------------------------------

def test_a_complete_protocol_is_accepted() -> None:
    validate_baseline_protocol(_protocol())


def test_the_project_may_not_coordinate_its_own_baseline() -> None:
    with pytest.raises(HumanBaselineError, match="may not coordinate"):
        validate_baseline_protocol(_protocol(coordinator_identity="mjodheim"))


def test_the_project_may_not_be_a_participant() -> None:
    participants = [_participant(i) for i in range(MINIMUM_PARTICIPANTS)]
    participants[2]["participant_id"] = "mjodheim"
    with pytest.raises(HumanBaselineError, match="may not be a baseline participant"):
        validate_baseline_protocol(_protocol(participants=participants))


def test_one_person_listed_twice_is_not_two_people() -> None:
    participants = [_participant(i) for i in range(MINIMUM_PARTICIPANTS)]
    participants[3]["participant_id"] = participants[0]["participant_id"]
    with pytest.raises(HumanBaselineError, match="listed twice"):
        validate_baseline_protocol(_protocol(participants=participants))


def test_too_few_participants_is_refused() -> None:
    with pytest.raises(HumanBaselineError, match="at least %d participants" % MINIMUM_PARTICIPANTS):
        validate_baseline_protocol(
            _protocol(participants=[_participant(i) for i in range(MINIMUM_PARTICIPANTS - 1)])
        )


def test_a_participant_who_has_seen_the_tasks_is_refused() -> None:
    participants = [_participant(i) for i in range(MINIMUM_PARTICIPANTS)]
    participants[1]["prior_exposure_to_tasks"] = True
    with pytest.raises(HumanBaselineError, match="prior exposure"):
        validate_baseline_protocol(_protocol(participants=participants))


def test_outcome_contingent_pay_is_refused_but_ordinary_pay_is_not() -> None:
    participants = [_participant(i) for i in range(MINIMUM_PARTICIPANTS)]
    participants[0]["compensation_contingent_on_outcome"] = True
    with pytest.raises(HumanBaselineError, match="contingently on the outcome"):
        validate_baseline_protocol(_protocol(participants=participants))
    validate_baseline_protocol(_protocol())  # flat hourly pay is fine


def test_a_participant_must_declare_a_compensation_basis_even_if_unpaid() -> None:
    participants = [_participant(i) for i in range(MINIMUM_PARTICIPANTS)]
    participants[4]["compensation_basis"] = ""
    with pytest.raises(HumanBaselineError, match="compensation basis"):
        validate_baseline_protocol(_protocol(participants=participants))
    participants[4]["compensation_basis"] = "unpaid"
    validate_baseline_protocol(_protocol(participants=participants))


# -- when the baseline may be written -----------------------------------------------------------

def test_a_baseline_written_after_the_system_numbers_are_known_is_refused() -> None:
    with pytest.raises(HumanBaselineError, match="is not a baseline"):
        validate_baseline_protocol(_protocol(committed_before_system_evaluation=False))


def test_the_protocol_must_bind_the_task_set_by_digest() -> None:
    with pytest.raises(HumanBaselineError, match="bind a task set"):
        validate_baseline_protocol(_protocol(task_set_sha256="not-a-digest"))


@pytest.mark.parametrize(
    "flag",
    (
        "participants_uncoached_attested",
        "no_decomposition_supplied_attested",
        "evaluator_owned_success_attested",
    ),
)
def test_every_attestation_is_required(flag: str) -> None:
    with pytest.raises(HumanBaselineError, match=flag):
        validate_baseline_protocol(_protocol(**{flag: False}))


# -- the result must belong to the protocol it claims -------------------------------------------

def test_a_faithful_result_is_accepted() -> None:
    protocol = _protocol()
    _validate_result(protocol, _result(protocol))


def test_a_result_bound_to_another_protocol_is_refused() -> None:
    protocol = _protocol()
    with pytest.raises(HumanBaselineError, match="does not bind the committed protocol"):
        _validate_result(protocol, _result(protocol, protocol_sha256="cd" * 32))


def test_an_easier_task_set_swapped_in_afterwards_is_refused() -> None:
    protocol = _protocol()
    with pytest.raises(HumanBaselineError, match="different task set"):
        _validate_result(protocol, _result(protocol, task_set_sha256="ef" * 32))


def test_a_participant_who_was_never_committed_is_refused() -> None:
    protocol = _protocol()
    result = _result(protocol)
    result["per_participant"][0]["participant_id"] = "a-late-addition"
    with pytest.raises(HumanBaselineError, match="unlisted participant"):
        _validate_result(protocol, result)


def test_a_committed_participant_may_not_be_dropped_from_the_result() -> None:
    protocol = _protocol()
    result = _result(protocol)
    del result["per_participant"][-1]
    with pytest.raises(HumanBaselineError, match="absent from the result"):
        _validate_result(protocol, result)


def test_solving_more_than_was_attempted_is_refused() -> None:
    protocol = _protocol()
    result = _result(protocol)
    result["per_participant"][0]["tasks_solved"] = 99
    with pytest.raises(HumanBaselineError, match="more tasks than attempted"):
        _validate_result(protocol, result)


def test_a_participant_must_declare_their_time() -> None:
    protocol = _protocol()
    result = _result(protocol)
    del result["per_participant"][2]["wall_clock_seconds"]
    with pytest.raises(HumanBaselineError, match="declares no time cost"):
        _validate_result(protocol, result)


def test_the_human_side_must_declare_its_cost() -> None:
    protocol = _protocol()
    with pytest.raises(HumanBaselineError, match="declares no cost"):
        _validate_result(protocol, _result(protocol, cost=None))
    with pytest.raises(HumanBaselineError, match="why it is unpriced"):
        _validate_result(
            protocol,
            _result(protocol, cost={"amount": None, "reason": "", "total_wall_clock_seconds": 1}),
        )


def test_an_unpriced_baseline_may_state_its_reason() -> None:
    protocol = _protocol()
    _validate_result(
        protocol,
        _result(
            protocol,
            cost={
                "amount": None,
                "reason": "volunteers, unpaid",
                "total_wall_clock_seconds": 9000.0,
            },
        ),
    )


# -- a range is not a test ----------------------------------------------------------------------

def test_a_protocol_claiming_significance_is_refused() -> None:
    with pytest.raises(HumanBaselineError, match="not a significance test"):
        validate_baseline_protocol(_protocol(makes_a_significance_claim=True))


def test_a_result_claiming_significance_is_refused() -> None:
    protocol = _protocol()
    with pytest.raises(HumanBaselineError, match="not a significance test"):
        _validate_result(protocol, _result(protocol, makes_a_significance_claim=True))


def test_the_summary_reports_a_range_and_computes_no_p_value() -> None:
    protocol = _protocol()
    summary = summarize(_result(protocol))
    assert summary["participants"] == MINIMUM_PARTICIPANTS
    assert summary["solved_fraction_min"] == pytest.approx(0.3)
    assert summary["solved_fraction_max"] == pytest.approx(0.7)
    assert summary["solved_fraction_min"] <= summary["solved_fraction_median"]
    assert summary["solved_fraction_median"] <= summary["solved_fraction_max"]
    assert summary["is_a_significance_test"] is False
    assert "p_value" not in summary
    assert summary["total_wall_clock_seconds"] == 9000.0
