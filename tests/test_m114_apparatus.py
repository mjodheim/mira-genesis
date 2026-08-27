"""M114's instrument: the delivery loop, the phase-boundary count, and the subtractive verdicts.

`tests/test_m114_delivery.py` attacks the contract. This file attacks the programs that produce and
consume the records the contract judges, because a rule that is enforced only where it is written
down and violated where the record is actually made is not enforced at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m114_carrier_bank as bank
from metamorphosis import m114_delivery as delivery
from metamorphosis.blind_bank_protocol import canonical_bytes
from scripts import check_m114_result as checker
from scripts import run_m114_generation as client
from scripts import run_m114_qualification as qualification

ROOT = Path(bank.EXPERIMENT_DIRECTORY).parents[1]


# ------------------------------------------------------------------ what the evidence says

def _response(status, body=None, raw=None):
    return {
        "started_at": "2026-08-27T10:00:00Z",
        "finished_at": "2026-08-27T10:00:01Z",
        "status": status,
        "response_headers": {},
        "response_sha256": "a" * 64,
        "response_bytes": 0,
        "body": body,
        "raw_text": raw,
    }


def _completion(text="{}"):
    return {
        "id": "gen-1",
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": "Morph",
        "choices": [{"finish_reason": "stop", "message": {"content": text}}],
        "usage": {"completion_tokens": 12},
    }


def test_a_clean_capacity_rejection_is_the_only_thing_that_classifies_as_retryable():
    evidence = client._evidence(_response(429, {"error": {"code": 429}}), None)
    assert evidence["completion_present"] is False
    assert evidence["model_execution_cannot_be_excluded"] is False
    assert delivery.classify_attempt({**evidence, "status": 429}) == "capacity_rejected"


@pytest.mark.parametrize("observed,failure", [
    # A 429 that carries billed completion tokens but no content.
    (_response(429, {"usage": {"completion_tokens": 40}}), None),
    # A 429 whose body carries an empty choices entry.
    (_response(429, {"choices": [{"message": {"content": ""}}]}), None),
    # A transport failure. A read timeout after transmission and a refused connection look
    # identical once the exception is caught, so execution is not excluded.
    (None, "TimeoutError: timed out"),
])
def test_anything_that_may_have_reached_the_model_is_never_retryable(observed, failure):
    evidence = client._evidence(observed, failure)
    attempt = {**evidence, "status": (observed or {}).get("status")}
    assert evidence["model_execution_cannot_be_excluded"] is True
    assert delivery.classify_attempt(attempt) == "failed_ambiguous"
    assert delivery.retry_permitted("failed_ambiguous", 1) is False


def test_a_429_that_carried_a_completion_is_a_materialization_and_not_a_second_draw():
    """The queue said no and something answered anyway. Whatever that is, it is not retryable.

    A capacity rejection is defined by the *absence* of generation, not by the status line. Reading
    this as a capacity rejection because it says 429 would be reading the label instead of the
    evidence, and it would authorize a second draw against a model that has already produced one.
    """
    evidence = client._evidence(_response(429, _completion('{"machines": []}')), None)
    assert evidence["completion_present"] is True
    attempt = {**evidence, "status": 429}
    assert delivery.classify_attempt(attempt) == "materialized"
    assert delivery.retry_permitted("materialized", 1) is False


def test_a_completion_materializes_and_a_dry_five_hundred_does_not_retry():
    evidence = client._evidence(_response(200, _completion('{"machines": []}')), None)
    assert delivery.classify_attempt({**evidence, "status": 200}) == "materialized"

    evidence = client._evidence(_response(503, {"error": {"code": 503}}), None)
    attempt = {**evidence, "status": 503}
    assert delivery.classify_attempt(attempt) == "failed_no_completion"
    assert delivery.retry_permitted("failed_no_completion", 1) is False


# ------------------------------------------------------------------ the delivery loop

@pytest.fixture
def instrument(tmp_path, monkeypatch):
    """A frozen spec and an empty experiment directory, with the network and the clock replaced."""
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    spec = json.loads(
        (bank.GENERATOR_SPEC_CANDIDATE_PATH).read_bytes().decode("utf-8")
    )
    spec.pop("unset_before_freeze", None)
    spec["frozen_before_generation"] = True
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)

    monkeypatch.setattr(client, "EXPERIMENT", experiment)
    monkeypatch.setattr(client, "LEDGER_PATH", experiment / "DELIVERY_LEDGER.json")
    monkeypatch.setattr(client, "RESPONSE_PATH", experiment / "GENERATION_RESPONSE.json")
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)
    return spec


def _ledger(instrument_dir: Path) -> dict:
    return json.loads((instrument_dir / "DELIVERY_LEDGER.json").read_text(encoding="utf-8"))


def test_three_capacity_rejections_end_the_milestone_and_leave_a_valid_record(
    instrument, monkeypatch, tmp_path
):
    calls = []

    def rejected(url, *, body=None, **kwargs):
        calls.append(body)
        return _response(429, {"error": {"code": 429, "message": "upstream at capacity"}})

    monkeypatch.setattr(client, "request", rejected)
    assert client.deliver(instrument) == 1

    assert len(calls) == delivery.MAX_DELIVERY_ATTEMPTS
    # The same frozen body, byte for byte, on every attempt.
    assert all(canonical_bytes(b) == canonical_bytes(calls[0]) for b in calls)

    ledger = _ledger(tmp_path / "experiments" / "M114")
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=instrument["spec_commitment_sha256"],
        request_body_sha256=instrument["canonical_request_body_sha256"],
    )
    summary = delivery.delivery_summary(ledger)
    assert summary["delivery_attempts"] == 3
    assert summary["capacity_rejections"] == 3
    assert summary["bank_materializations"] == 0
    assert ledger["bank_materialization_index"] is None
    assert not (tmp_path / "experiments" / "M114" / "GENERATION_RESPONSE.json").is_file()
    assert ledger["delivery_rule_was_never_part_of_m113"] is True


def test_the_loop_stops_the_instant_a_bank_materializes(instrument, monkeypatch, tmp_path):
    seen = {"n": 0}

    def once(url, *, body=None, **kwargs):
        seen["n"] += 1
        if seen["n"] == 1:
            return _response(429, {"error": {"code": 429}})
        return _response(200, _completion('{"machines": []}'))

    monkeypatch.setattr(client, "request", once)
    assert client.deliver(instrument) == 0

    assert seen["n"] == 2, "a materialized bank must not be followed by another attempt"
    ledger = _ledger(tmp_path / "experiments" / "M114")
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=instrument["spec_commitment_sha256"],
        request_body_sha256=instrument["canonical_request_body_sha256"],
    )
    assert ledger["bank_materialization_index"] == 2
    assert (tmp_path / "experiments" / "M114" / "GENERATION_RESPONSE.json").is_file()


def test_a_terminal_outcome_stops_the_loop_with_budget_left(instrument, monkeypatch, tmp_path):
    """An ambiguous first attempt ends the sequence; two unspent attempts are not a second draw."""
    calls = {"n": 0}

    def ambiguous(url, *, body=None, **kwargs):
        calls["n"] += 1
        raise TimeoutError("timed out")

    monkeypatch.setattr(client, "request", ambiguous)
    assert client.deliver(instrument) == 1
    assert calls["n"] == 1

    ledger = _ledger(tmp_path / "experiments" / "M114")
    assert [a["outcome"] for a in ledger["attempts"]] == ["failed_ambiguous"]
    delivery.validate_delivery_ledger(ledger)


def test_a_closed_sequence_cannot_be_resumed(instrument, monkeypatch, tmp_path):
    monkeypatch.setattr(
        client, "request",
        lambda url, *, body=None, **kwargs: _response(503, {"error": {"code": 503}}),
    )
    assert client.deliver(instrument) == 1

    # A second invocation against the same frozen spec. The rule is recomputed from the record
    # rather than read from the previous attempt's own claim about itself.
    with pytest.raises(client.GenerationError, match="closed"):
        client.deliver(instrument)


def test_an_exhausted_budget_cannot_be_resumed(instrument, monkeypatch, tmp_path):
    monkeypatch.setattr(
        client, "request",
        lambda url, *, body=None, **kwargs: _response(429, {"error": {"code": 429}}),
    )
    assert client.deliver(instrument) == 1
    with pytest.raises(client.GenerationError, match="closed"):
        client.deliver(instrument)


def test_a_ledger_opened_against_a_different_spec_is_refused(instrument, monkeypatch, tmp_path):
    (tmp_path / "experiments" / "M114" / "DELIVERY_LEDGER.json").write_bytes(canonical_bytes({
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": "M114",
        "spec_commitment_sha256": "f" * 64,
        "bank_materialization_index": None,
        "attempts": [],
    }) + b"\n")
    with pytest.raises(client.GenerationError, match="different frozen spec"):
        client.deliver(instrument)


def test_a_materialized_response_is_never_delivered_over(instrument, monkeypatch, tmp_path):
    (tmp_path / "experiments" / "M114" / "GENERATION_RESPONSE.json").write_text("{}")
    with pytest.raises(client.GenerationError, match="not delivered twice"):
        client.deliver(instrument)


def test_a_served_identity_that_is_not_the_frozen_one_is_refused(instrument, monkeypatch, tmp_path):
    served = _completion('{"machines": []}')
    served["provider"] = "Together"
    monkeypatch.setattr(
        client, "request", lambda url, *, body=None, **kwargs: _response(200, served)
    )
    assert client.deliver(instrument) == 1
    assert not (tmp_path / "experiments" / "M114" / "GENERATION_RESPONSE.json").is_file()
    # The substitution stays in the record, and the contract refuses the record that carries it.
    ledger = _ledger(tmp_path / "experiments" / "M114")
    assert ledger["attempts"][0]["served_provider"] == "Together"
    with pytest.raises(delivery.DeliveryError, match="served by"):
        delivery.validate_delivery_ledger(ledger)


# ------------------------------------------------------------------ P15's generator half

def test_the_phase_boundary_counts_materializations_and_not_requests(tmp_path):
    """Three attempts that never reached the model are zero model calls, not three."""
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    attempts = [
        {
            "attempt_index": i,
            "started_at": "2026-08-27T09:00:0%dZ" % i,
            "status": 429,
            "requested_provider": "Morph",
            "served_provider": None,
            "requested_model": "deepseek/deepseek-v4-flash-0731",
            "served_model": None,
            "response_headers": {},
            "error_body": {"error": {"code": 429}},
            "response_sha256": "%064d" % i,
            "request_body_sha256": "a" * 64,
            "completion_present": False,
            "model_execution_cannot_be_excluded": False,
            "outcome": "capacity_rejected",
            "retry_permitted_by_the_frozen_rule": i < 3,
            "waited_seconds_before_this_attempt": 0 if i == 1 else 60,
        }
        for i in (1, 2, 3)
    ]
    (experiment / "DELIVERY_LEDGER.json").write_bytes(canonical_bytes({
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": "M114",
        "spec_commitment_sha256": "c" * 64,
        "bank_materialization_index": None,
        "attempts": attempts,
    }) + b"\n")

    assert qualification.bank_generation_invocations(tmp_path) == 0
    summary = qualification.bank_delivery(tmp_path)
    assert summary["delivery_attempts"] == 3
    assert summary["ledger_violates_the_frozen_rule"] is None


def test_an_absent_generator_phase_is_not_applicable_rather_than_satisfied(tmp_path):
    assert qualification.bank_generation_invocations(tmp_path) is None
    assert qualification.bank_delivery(tmp_path) is None


# ------------------------------------------------------------------ the subtractive verdicts

def _canonical_result(verdict_source: dict) -> dict:
    return dict(verdict_source, is_a_canonical_attempt=True, development=False)


def test_a_development_run_reaches_a_verdict_and_carries_the_filiation():
    result = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )
    report = checker.check(result)
    assert report["milestone"] == "M114"
    assert report["hypothesis"] == "H59"
    assert report["filiation"]["predecessor"] == "M113"
    assert report["verdict"] in ("positive", "negative")
    assert report["delivery"]["state"] == "not_applicable_on_a_development_run"


def test_a_canonical_attempt_without_a_delivery_record_is_invalid():
    result = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )
    report = checker.check(_canonical_result(result))
    assert report["verdict"] == checker.INVALID


def test_the_extra_verdicts_can_only_ever_subtract():
    """The one property that matters: nothing M114 adds can make a verdict better.

    A milestone permitted three delivery attempts has exactly one way to go wrong that M113 did
    not -- the extra attempts becoming a way to keep drawing until something passes. A checker
    whose additions could ever *help* a verdict would be the mechanism by which that happened, so
    the property is asserted directly rather than inferred from the branches.
    """
    result = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )
    baseline = checker.check(result)["verdict"]
    assert baseline == "negative"

    for recorded in (
        {"bank_materializations": 1, "ledger_violates_the_frozen_rule": None},
        {"bank_materializations": 0, "ledger_violates_the_frozen_rule": None},
        {"bank_materializations": 1, "ledger_violates_the_frozen_rule": "four attempts"},
        None,
    ):
        report = checker.check(_canonical_result(dict(result, bank_delivery=recorded)))
        assert report["verdict"] != "positive", (
            "a delivery record must never be able to turn %r into a positive" % baseline
        )


def test_a_violating_ledger_is_invalid_and_an_empty_one_is_instrument_aborted():
    result = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )
    invalid = checker.check(_canonical_result(dict(result, bank_delivery={
        "bank_materializations": 1, "ledger_violates_the_frozen_rule": "a fourth attempt",
    })))
    assert invalid["verdict"] == checker.INVALID

    aborted = checker.check(_canonical_result(dict(result, bank_delivery={
        "bank_materializations": 0, "ledger_violates_the_frozen_rule": None,
    })))
    assert aborted["verdict"] == checker.INSTRUMENT_ABORTED
    assert aborted["delivery"]["state"] == "no_bank_materialized"


def test_the_checker_states_that_an_abort_is_not_a_result_about_the_hypothesis():
    result = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )
    report = checker.check(_canonical_result(dict(result, bank_delivery={
        "bank_materializations": 0, "ledger_violates_the_frozen_rule": None,
    })))
    assert "not a result about H59" in report["verdict_rule"]


# ------------------------------------------------------------------ the freeze

def test_the_freeze_refuses_to_run_twice(tmp_path, monkeypatch):
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    monkeypatch.setattr(client, "PLAN_PATH", experiment / "ANALYSIS_PLAN.json")
    monkeypatch.setattr(client, "SPEC_PATH", experiment / "GENERATOR_SPEC.json")
    monkeypatch.setattr(client, "LEDGER_PATH", experiment / "DELIVERY_LEDGER.json")
    (experiment / "GENERATOR_SPEC.json").write_text("{}")
    with pytest.raises(client.GenerationError, match="consumed once"):
        client.freeze()


def test_the_freeze_refuses_to_run_behind_a_delivery_history(tmp_path, monkeypatch):
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    monkeypatch.setattr(client, "PLAN_PATH", experiment / "ANALYSIS_PLAN.json")
    monkeypatch.setattr(client, "SPEC_PATH", experiment / "GENERATOR_SPEC.json")
    monkeypatch.setattr(client, "LEDGER_PATH", experiment / "DELIVERY_LEDGER.json")
    (experiment / "DELIVERY_LEDGER.json").write_text("{}")
    with pytest.raises(client.GenerationError, match="already acted on"):
        client.freeze()


def test_the_frozen_spec_the_freeze_would_write_validates(tmp_path, monkeypatch):
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    monkeypatch.setattr(client, "PLAN_PATH", experiment / "ANALYSIS_PLAN.json")
    monkeypatch.setattr(client, "SPEC_PATH", experiment / "GENERATOR_SPEC.json")
    monkeypatch.setattr(client, "LEDGER_PATH", experiment / "DELIVERY_LEDGER.json")

    report = client.freeze()
    assert report["hypothesis"] == "H59"
    assert all(report["generator_inputs_are_m113s"].values())
    assert report["max_delivery_attempts"] == 3
    assert report["max_bank_materializations"] == 1

    plan = json.loads((experiment / "ANALYSIS_PLAN.json").read_text(encoding="utf-8"))
    spec = json.loads((experiment / "GENERATOR_SPEC.json").read_text(encoding="utf-8"))
    bank.validate_analysis_plan(plan)
    bank.validate_generator_spec(
        spec, root=ROOT, plan_commitment_sha256=plan["plan_commitment_sha256"]
    )
    assert spec["frozen_before_generation"] is True
    assert "unset_before_freeze" not in spec
    # The freeze changes the instrument's status, never the request it will send.
    assert spec["canonical_request_body_sha256"] == (
        "02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc"
    )


# ------------------------------------------------------------------ failing closed, not crashing

def test_a_spec_under_a_root_without_the_predecessors_copies_is_refused_not_crashed(tmp_path):
    """The delegation points at `experiments/M113`, which a caller's root need not contain.

    An unreadable file there must be a refusal. `assess_carrier_bank_readiness` catches
    `CarrierBankError` and reports it as a blocker; an `OSError` escaping the delegation would take
    the phase machine down while it was in the middle of explaining why a reveal is not permitted.
    """
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    for name in bank.GENERATOR_INPUT_DIGESTS:
        (experiment / name).write_bytes(
            (Path(bank.EXPERIMENT_DIRECTORY) / name).read_bytes()
        )
    spec = json.loads((bank.GENERATOR_SPEC_CANDIDATE_PATH).read_bytes().decode("utf-8"))
    spec.pop("unset_before_freeze", None)
    spec["frozen_before_generation"] = True
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    (experiment / "GENERATOR_SPEC.json").write_bytes(canonical_bytes(spec) + b"\n")

    with pytest.raises(bank.CarrierBankError, match="predecessor's copy"):
        bank.validate_generator_spec(spec, root=tmp_path)

    report = bank.assess_carrier_bank_readiness(tmp_path)
    assert report["revealed"] is False
    assert any("generator spec" in blocker for blocker in report["blockers"])


def test_a_response_that_is_not_an_object_is_recorded_rather_than_raised(instrument, monkeypatch, tmp_path):
    """The evidence is read after the request was sent, so it may never raise.

    An exception at this point would lose the attempt the ledger exists to record -- and the lost
    attempt would be one the budget had already spent.
    """
    monkeypatch.setattr(
        client, "request",
        lambda url, *, body=None, **kwargs: _response(200, ["not", "an", "object"]),
    )
    assert client.deliver(instrument) == 1

    ledger = _ledger(tmp_path / "experiments" / "M114")
    assert len(ledger["attempts"]) == 1
    assert ledger["attempts"][0]["outcome"] == "failed_no_completion"
    assert ledger["attempts"][0]["error_body"] == ["not", "an", "object"]
    delivery.validate_delivery_ledger(ledger)
