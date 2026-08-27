"""M114's corrective `P15`, attacked clause by clause.

`P15` is the one predicate this milestone versions, and it is the predicate that decides whether a
bank was obtained under the frozen delivery rule. So it gets the treatment the rule itself got in
`tests/test_m114_delivery.py`: every clause is given a record built specifically to slip past it.

The property that matters most is asserted directly rather than inferred: nothing this predicate
does can improve a verdict. A milestone permitted three delivery attempts has exactly one way to
cheat -- keep drawing until something passes -- and a boundary predicate that could ever turn a
failure into a pass would be the instrument of it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m114_carrier_bank as bank
from metamorphosis import m114_delivery as delivery
from scripts import check_m114_result as checker

MODEL = "deepseek/deepseek-v4-flash-0731"
PROVIDER = "Morph"
BODY = "02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc"
SPEC = "c" * 64

ROUTING = {
    "allow_fallbacks": False,
    "automatic_routing": False,
    "model_fallbacks": [],
    "provider_fallbacks": [],
    "require_parameters": True,
}


def _attempt(index, outcome, *, waited=None, **overrides):
    """One attempt whose recorded evidence agrees with its recorded outcome."""
    rejected = outcome == "capacity_rejected"
    attempt = {
        "attempt_index": index,
        "started_at": "2026-08-27T09:00:0%dZ" % index,
        "status": 429 if rejected else (200 if outcome == "materialized" else 503),
        "requested_provider": PROVIDER,
        "served_provider": None if rejected else PROVIDER,
        "requested_model": MODEL,
        "served_model": None if rejected else MODEL,
        "response_headers": {},
        "error_body": {"error": {"code": 429}} if rejected else None,
        "response_sha256": "%064d" % index,
        "request_body_sha256": BODY,
        "completion_present": outcome == "materialized",
        "model_execution_cannot_be_excluded": outcome == "failed_ambiguous",
        "outcome": outcome,
        "retry_permitted_by_the_frozen_rule": delivery.retry_permitted(outcome, index),
        "waited_seconds_before_this_attempt": (0 if index == 1 else 60) if waited is None else waited,
    }
    attempt.update(overrides)
    return attempt


def _ledger(*attempts):
    materialized = [
        a["attempt_index"] for a in attempts if a.get("outcome") == "materialized"
    ]
    return {
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": "M114",
        "spec_commitment_sha256": SPEC,
        "bank_materialization_index": materialized[0] if materialized else None,
        "attempts": list(attempts),
    }


def _development() -> dict:
    return json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )


def _canonical(ledger=None, *, routing=None, **overrides) -> dict:
    """A canonical-looking result. Its science is the development run's; only the record differs."""
    result = dict(_development(), is_a_canonical_attempt=True, development=False)
    attempts = (ledger or {}).get("attempts") or []
    result["delivery_ledger"] = ledger
    result["physical_delivery_attempts"] = len(attempts) if ledger is not None else None
    result["bank_materializations"] = sum(
        1 for a in attempts if a.get("outcome") == "materialized"
    ) if ledger is not None else None
    result["model_execution_evidence"] = [
        {
            "attempt_index": a.get("attempt_index"),
            "status": a.get("status"),
            "completion_present": a.get("completion_present"),
            "model_execution_cannot_be_excluded": a.get("model_execution_cannot_be_excluded"),
            "outcome": a.get("outcome"),
            "response_sha256": a.get("response_sha256"),
        }
        for a in attempts
    ] if ledger is not None else None
    result["frozen_instrument"] = {
        "spec_commitment_sha256": SPEC,
        "canonical_request_body_sha256": BODY,
        "model": MODEL,
        "provider": PROVIDER,
        "routing": ROUTING if routing is None else routing,
    }
    result.update(overrides)
    return result


# ------------------------------------------------------------------ the predicate is versioned

def test_p15_is_the_only_predicate_this_milestone_versions():
    """The claim the PR makes about itself, asserted rather than written in prose."""
    provenance = checker.PREDICATE_PROVENANCE
    assert provenance["versioned_for_this_milestone"] == ["P15"]
    assert provenance["p15_version"] == "m114-phase-boundary-v1"
    retained = provenance["retain_m113_scientific_computations"]
    assert "P15" not in retained
    assert set(retained) == {"P%d" % i for i in range(1, 23)} - {"P15"}
    assert len(retained) == 21
    assert provenance["p22_scientific_computation_is_unchanged_and_applied_to"] == "H59"


def test_the_frozen_plan_must_declare_the_versioning():
    """A milestone that versioned a predicate and said nothing would have changed one in silence."""
    plan = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN_CANDIDATE.json").read_bytes().decode("utf-8")
    )
    bank.validate_analysis_plan(plan)
    assert plan["p15_version"] == bank.P15_VERSION
    assert plan["predicates_versioned_for_this_milestone"] == ["P15"]

    for mutate in (
        lambda p: p.update(predicates_versioned_for_this_milestone=[]),
        lambda p: p.update(p15_version="m113"),
        lambda p: p.update(p15_versioning_gives_no_advantage_to_the_hypothesis=False),
        lambda p: p.update(physical_requests_and_model_calls_are_never_carried_in_one_field=False),
        lambda p: p.update(
            predicates_retaining_m113_scientific_computations=["P%d" % i for i in range(1, 23)]
        ),
        lambda p: p.pop("p15_version"),
    ):
        broken = json.loads(json.dumps(plan))
        mutate(broken)
        broken["plan_commitment_sha256"] = bank.analysis_plan_commitment(broken)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_analysis_plan(broken)


def test_the_two_quantities_are_never_carried_in_one_field():
    """A 429 before generation is a physical network request and is not a model execution."""
    boundary = checker.phase_boundary(
        _canonical(_ledger(
            _attempt(1, "capacity_rejected"),
            _attempt(2, "capacity_rejected"),
            _attempt(3, "materialized"),
        ))
    )
    assert boundary["physical_delivery_attempts"] == 3
    assert boundary["bank_materializations"] == 1
    assert boundary["network_calls_in_qualification"] == 0
    # The field whose two meanings caused this correction must not have come back.
    assert "model_calls_in_bank_generation" not in boundary


# ------------------------------------------------------------------ the eight attacks

def test_two_rejections_then_a_materialization_holds_only_if_the_whole_protocol_is_valid():
    lawful = _ledger(
        _attempt(1, "capacity_rejected"),
        _attempt(2, "capacity_rejected"),
        _attempt(3, "materialized"),
    )
    boundary = checker.phase_boundary(_canonical(lawful))
    assert boundary["holds"] is True
    assert boundary["delivery_phase"]["holds"] is True
    assert boundary["generation_phase"]["holds"] is True
    assert checker.check(_canonical(lawful))["conditions"]["P15"] is True

    # The same three outcomes, with one clause of the protocol broken, must not hold.
    for mutate in (
        # a fourth attempt
        lambda a: a.append(_attempt(4, "materialized")),
        # the retry interval shortened
        lambda a: a.__setitem__(1, _attempt(2, "capacity_rejected", waited=5)),
        # the first attempt claiming it waited
        lambda a: a.__setitem__(0, _attempt(1, "capacity_rejected", waited=60)),
    ):
        attempts = [dict(a) for a in lawful["attempts"]]
        mutate(attempts)
        broken = _ledger(*attempts)
        assert checker.phase_boundary(_canonical(broken))["holds"] is False


def test_a_429_that_carried_a_completion_may_not_be_followed_by_another_attempt():
    """The queue said no and something answered anyway. That is a draw, not a rejection."""
    contradictory = _attempt(1, "capacity_rejected")
    contradictory["completion_present"] = True
    ledger = _ledger(contradictory, _attempt(2, "materialized"))
    result = _canonical(ledger)

    assert checker.phase_boundary(result)["holds"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


def test_an_ambiguous_timeout_followed_by_a_retry_is_invalid():
    """The one failure no downstream check could ever recover from."""
    ledger = _ledger(_attempt(1, "failed_ambiguous"), _attempt(2, "materialized"))
    result = _canonical(ledger)

    boundary = checker.phase_boundary(result)
    assert boundary["holds"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


def test_two_materializations_are_invalid():
    ledger = _ledger(_attempt(1, "materialized"), _attempt(2, "materialized"))
    result = _canonical(ledger)

    assert checker.phase_boundary(result)["holds"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


def test_one_byte_of_difference_between_attempts_is_invalid():
    """A retry that changed the request is a second experiment wearing the first one's name."""
    second = _attempt(2, "materialized")
    second["request_body_sha256"] = "0" * 63 + "1"
    ledger = _ledger(_attempt(1, "capacity_rejected"), second)
    result = _canonical(ledger)

    assert checker.phase_boundary(result)["holds"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


@pytest.mark.parametrize("substitution", [
    {"served_provider": "Together"},
    {"served_model": "deepseek/deepseek-v4-flash:latest"},
])
def test_a_provider_or_model_substitution_is_invalid(substitution):
    ledger = _ledger(_attempt(1, "materialized", **substitution))
    result = _canonical(ledger)

    assert checker.phase_boundary(result)["holds"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


@pytest.mark.parametrize("routing", [
    dict(ROUTING, allow_fallbacks=True),
    dict(ROUTING, automatic_routing=True),
    dict(ROUTING, model_fallbacks=["deepseek/deepseek-v4"]),
    dict(ROUTING, provider_fallbacks=["Together"]),
])
def test_a_bank_obtained_with_a_fallback_available_is_invalid(routing):
    """A perfectly lawful ledger under an instrument that could have answered from elsewhere."""
    ledger = _ledger(_attempt(1, "materialized"))
    result = _canonical(ledger, routing=routing)

    boundary = checker.phase_boundary(result)
    assert boundary["delivery_phase"]["clauses"]["no_fallback_was_available"] is False
    assert boundary["holds"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


def test_an_absent_delivery_ledger_makes_p15_false_and_the_run_invalid():
    result = _canonical(None)
    boundary = checker.phase_boundary(result)
    assert boundary["holds"] is False
    assert boundary["delivery_phase"]["delivery_record_present"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


def test_a_forged_delivery_ledger_makes_p15_false():
    """Forged in the only way that would matter: the summary says one thing, the attempts another."""
    ledger = _ledger(_attempt(1, "capacity_rejected"))
    ledger["bank_materialization_index"] = 1          # names a bank the attempts do not carry
    result = _canonical(ledger)
    result["bank_materializations"] = 1               # and the result agrees with the forgery
    result["physical_delivery_attempts"] = 1

    boundary = checker.phase_boundary(result)
    assert boundary["holds"] is False
    assert boundary["delivery_phase"]["ledger_is_valid_under_the_frozen_rule"] is False
    assert checker.check(result)["verdict"] == checker.INVALID


def test_a_result_that_understates_its_own_physical_attempts_is_refused():
    """The count is checked against the attempts rather than believed."""
    ledger = _ledger(
        _attempt(1, "capacity_rejected"),
        _attempt(2, "capacity_rejected"),
        _attempt(3, "materialized"),
    )
    result = _canonical(ledger)
    result["physical_delivery_attempts"] = 1

    boundary = checker.phase_boundary(result)
    assert boundary["delivery_phase"]["clauses"][
        "physical_attempts_are_recorded_separately"
    ] is False
    assert boundary["holds"] is False


def test_an_absent_qualification_guard_fails_p15_even_with_a_perfect_bank():
    """Silence proves nothing unless something proved the guard was listening."""
    ledger = _ledger(_attempt(1, "materialized"))
    result = _canonical(ledger)
    result["network_guard_selftest_intercepted"] = False

    boundary = checker.phase_boundary(result)
    assert boundary["delivery_phase"]["holds"] is True
    assert boundary["generation_phase"]["holds"] is True
    assert boundary["qualification_phase"]["qualification_phase_is_silent"] is True
    assert boundary["qualification_phase"]["qualification_guard_was_live"] is False
    assert boundary["holds"] is False, "an unproven guard may not be credited as silence"
    assert checker.check(result)["conditions"]["P15"] is False


@pytest.mark.parametrize("noisy", [
    "model_calls_in_qualification",
    "network_calls_in_qualification",
    "remote_execution_calls_in_qualification",
])
def test_any_call_during_qualification_fails_p15(noisy):
    ledger = _ledger(_attempt(1, "materialized"))
    result = _canonical(ledger)
    result[noisy] = 1

    assert checker.phase_boundary(result)["holds"] is False


def test_no_materialization_is_instrument_aborted_and_not_a_negative():
    """Three clean rejections are a complete, permitted delivery history with no bank."""
    ledger = _ledger(
        _attempt(1, "capacity_rejected"),
        _attempt(2, "capacity_rejected"),
        _attempt(3, "capacity_rejected"),
    )
    result = _canonical(ledger)
    report = checker.check(result)

    assert report["verdict"] == checker.INSTRUMENT_ABORTED
    assert report["measurements"]["phase_boundary"]["generation_phase"]["holds"] is False
    assert report["measurements"]["phase_boundary"]["delivery_phase"]["holds"] is True
    assert "not a result about H59" in report["verdict_rule"]


# ------------------------------------------------------------------ it may only ever subtract

def test_the_corrective_p15_can_never_improve_a_verdict():
    """The one property the whole correction has to have.

    Swept over every delivery record shape this milestone can produce -- lawful, violating, absent,
    aborted -- against a run whose science already fails. None may reach `positive`.
    """
    lawful = _ledger(
        _attempt(1, "capacity_rejected"),
        _attempt(2, "capacity_rejected"),
        _attempt(3, "materialized"),
    )
    aborted = _ledger(*[_attempt(i, "capacity_rejected") for i in (1, 2, 3)])
    ambiguous = _ledger(_attempt(1, "failed_ambiguous"), _attempt(2, "materialized"))

    baseline = checker.check(_development())
    assert baseline["verdict"] == "negative", "the fixture must already fail on its science"
    assert baseline["conditions"]["P22"] is False

    for ledger in (lawful, aborted, ambiguous, None):
        report = checker.check(_canonical(ledger))
        assert report["conditions"]["P22"] is False, (
            "no delivery record may change the scientific computation of P22"
        )
        assert report["verdict"] != "positive"


def test_p22_is_computed_by_m113s_unchanged_rule():
    """The corrective predicate sits beside the hypothesis, never inside it."""
    from scripts import check_m113_result as m113

    result = _canonical(_ledger(_attempt(1, "materialized")))
    assert checker.check(result)["conditions"]["P22"] == m113.evaluate_conditions(result)["P22"]
    for name in checker.PREDICATE_PROVENANCE["retain_m113_scientific_computations"]:
        assert checker.check(result)["conditions"][name] == m113.evaluate_conditions(result)[name]


def test_the_corrective_p15_is_strictly_stricter_than_the_predicate_it_replaces():
    """Versioning a predicate must not loosen it, and "stricter" is checkable rather than claimed.

    M113's `P15` is the conjunction of a silent qualification phase under a live guard and exactly
    one model call in bank generation. M114's keeps both -- a materialization *is* a model call --
    and conjoins twelve delivery clauses M113 had none of. So on any record where M113's predicate
    is even well-defined, M114's holding must imply M113's holding.

    The implication is asserted in that direction only. The converse is false by construction, and
    that is the whole point: a bank M113 would have accepted can still be refused here because of
    how it was delivered.
    """
    from scripts import check_m113_result as m113

    lawful = _ledger(
        _attempt(1, "capacity_rejected"),
        _attempt(2, "capacity_rejected"),
        _attempt(3, "materialized"),
    )
    records = [
        _canonical(lawful),
        _canonical(_ledger(_attempt(1, "materialized"))),
        _canonical(_ledger(*[_attempt(i, "capacity_rejected") for i in (1, 2, 3)])),
        _canonical(_ledger(_attempt(1, "failed_ambiguous"), _attempt(2, "materialized"))),
        _canonical(_ledger(_attempt(1, "materialized")), routing=dict(ROUTING, allow_fallbacks=True)),
        _canonical(None),
    ]

    saw_both = {True: 0, False: 0}
    for record in records:
        for guard in (True, False):
            probe = dict(record, network_guard_selftest_intercepted=guard)
            # Give M113's predicate the field it reads, filled with the count it would have meant.
            probe["model_calls_in_bank_generation"] = probe.get("bank_materializations")
            ours = checker.phase_boundary(probe)["holds"]
            theirs = m113._phase_boundary(probe)["holds"]
            saw_both[ours] += 1
            assert not (ours and not theirs), (
                "M114's P15 accepted a record M113's P15 refused, so the versioning loosened it"
            )

    assert saw_both[True] and saw_both[False], "the sweep must exercise both outcomes"
