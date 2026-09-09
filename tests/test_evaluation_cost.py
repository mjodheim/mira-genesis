"""Hostile tests for the G9 cost and efficiency instrument.

The two refusals matter more than the arithmetic: a run this module cannot price must stay unpriced,
and a compute proxy must never be presented as energy. Both are ways a cost report could quietly
become a fabricated result.
"""
from __future__ import annotations

import pytest

from metamorphosis.evaluation_cost import (
    COST_SCHEMA,
    DETERMINISTIC_FIELDS,
    RATE_CARD_SCHEMA,
    REQUIRED_REPORT_DIMENSIONS,
    CostError,
    assert_reports_required_dimensions,
    cost_record,
    measured,
    monetary_cost,
    verify_cost_record,
)

RATE_CARD = {
    "schema": RATE_CARD_SCHEMA,
    "version": "test-1",
    "currency": "USD",
    "rates": {"a-model": {"prompt_per_million": 1.0, "completion_per_million": 2.0}},
}


def _deterministic(**overrides) -> dict:
    base = {name: 0 for name in DETERMINISTIC_FIELDS}
    base.update({"episodes": 128, "work_items": 100, "candidate_evaluations": 4})
    base.update(overrides)
    return base


def _environment(**overrides) -> dict:
    with measured() as captured:
        pass
    captured.update(overrides)
    return captured


def _record(**overrides):
    kwargs = {
        "milestone": "MTEST",
        "deterministic": _deterministic(),
        "environment_costs": _environment(),
        "quality": {"exact": 1},
        "reliability": {"replays": True},
        "monetary": monetary_cost(None, model="a-model", prompt_tokens=0, completion_tokens=0),
    }
    kwargs.update(overrides)
    return cost_record(**kwargs)


# -- the environment half is measured, and admits that it cannot reproduce ----------------------

def test_measured_captures_latency_and_a_compute_proxy():
    with measured() as captured:
        sum(range(10_000))
    assert captured["wall_clock_seconds"] >= 0
    assert captured["cpu_seconds"] >= 0
    assert captured["reproducible"] is False
    assert captured["cpu_seconds_is_a_compute_proxy_not_energy"] is True
    assert captured["environment"]["python_version"]


def test_environment_costs_must_declare_themselves_non_reproducible():
    with pytest.raises(CostError, match="non-reproducible"):
        _record(environment_costs=_environment(reproducible=True))


@pytest.mark.parametrize("field", ("energy_joules", "watts"))
def test_a_record_claiming_energy_is_refused(field):
    with pytest.raises(CostError, match="nothing here measures energy"):
        _record(environment_costs=_environment(**{field: 12.0}))


def test_the_compute_proxy_is_never_presented_as_energy():
    record = _record()
    assert record["report"]["compute_proxy"]["is_energy"] is False
    record["report"]["compute_proxy"]["is_energy"] = True
    with pytest.raises(CostError, match="not be presented as energy"):
        assert_reports_required_dimensions(record)


# -- monetary cost is priced or refused, never guessed ------------------------------------------

def test_an_unpriced_run_says_why_rather_than_guessing():
    priced = monetary_cost(None, model="a-model", prompt_tokens=10, completion_tokens=5)
    assert priced["amount"] is None
    assert "not estimated" in priced["reason"]


def test_a_model_the_rate_card_does_not_price_stays_unpriced():
    priced = monetary_cost(RATE_CARD, model="other", prompt_tokens=10, completion_tokens=5)
    assert priced["amount"] is None
    assert "does not price model" in priced["reason"]


def test_a_priced_run_computes_from_the_committed_rate_card():
    priced = monetary_cost(RATE_CARD, model="a-model", prompt_tokens=1_000_000, completion_tokens=500_000)
    assert priced["amount"] == pytest.approx(1.0 + 1.0)
    assert priced["currency"] == "USD"
    assert priced["reason"] is None


def test_zero_billable_tokens_is_priced_at_zero_rather_than_left_unpriced():
    priced = monetary_cost(None, model="a-model", prompt_tokens=0, completion_tokens=0)
    assert priced["amount"] == 0.0
    assert priced["no_billable_usage"] is True
    assert priced["reason"] is None


def test_a_malformed_or_unrecognized_rate_card_is_refused():
    with pytest.raises(CostError, match="unrecognized schema"):
        monetary_cost({"schema": "invented"}, model="a-model", prompt_tokens=1, completion_tokens=1)
    with pytest.raises(CostError, match="no currency"):
        monetary_cost({"schema": RATE_CARD_SCHEMA, "rates": {}}, model="a", prompt_tokens=1, completion_tokens=1)
    broken = {**RATE_CARD, "rates": {"a-model": {"prompt_per_million": "free"}}}
    with pytest.raises(CostError, match="malformed"):
        monetary_cost(broken, model="a-model", prompt_tokens=1, completion_tokens=1)


def test_an_unpriced_run_with_no_reason_is_refused():
    record = _record()
    record["report"]["monetary_cost"] = {"amount": None, "currency": None, "reason": ""}
    with pytest.raises(CostError, match="why it is unpriced"):
        assert_reports_required_dimensions(record)


def test_a_priced_run_may_not_also_carry_an_excuse():
    record = _record()
    record["report"]["monetary_cost"] = {"amount": 1.0, "currency": "USD", "reason": "unpriced"}
    with pytest.raises(CostError, match="must not also carry an excuse"):
        assert_reports_required_dimensions(record)


# -- the deterministic half must be complete, well formed and independently reproducible --------

def test_every_required_dimension_is_reported():
    record = _record()
    assert set(record["report"]) >= set(REQUIRED_REPORT_DIMENSIONS)
    assert record["schema"] == COST_SCHEMA


@pytest.mark.parametrize("dimension", REQUIRED_REPORT_DIMENSIONS)
def test_dropping_any_required_dimension_is_refused(dimension):
    record = _record()
    del record["report"][dimension]
    with pytest.raises(CostError, match="omits required dimensions"):
        assert_reports_required_dimensions(record)


def test_omitted_or_unknown_deterministic_components_are_refused():
    incomplete = _deterministic()
    del incomplete["episodes"]
    with pytest.raises(CostError, match="omitted"):
        _record(deterministic=incomplete)
    with pytest.raises(CostError, match="unknown"):
        _record(deterministic=_deterministic(invented=1))


@pytest.mark.parametrize("value", (-1, 1.5, True, "many"))
def test_a_deterministic_component_must_be_a_non_negative_integer(value):
    with pytest.raises(CostError, match="non-negative integer"):
        _record(deterministic=_deterministic(episodes=value))


def test_empty_quality_or_reliability_sections_are_refused():
    with pytest.raises(CostError, match="section 'quality' is empty"):
        _record(quality={})
    with pytest.raises(CostError, match="section 'reliability' is empty"):
        _record(reliability={})


def test_verification_accepts_a_faithful_record():
    record = _record()
    assert verify_cost_record(record, recomputed_deterministic=_deterministic()) == []


def test_verification_names_the_component_that_disagrees():
    record = _record()
    problems = verify_cost_record(record, recomputed_deterministic=_deterministic(work_items=99))
    assert any("work_items: recorded 100, recomputed 99" in problem for problem in problems)


def test_verification_refuses_a_component_it_cannot_independently_recompute():
    record = _record()
    partial = _deterministic()
    del partial["episodes"]
    problems = verify_cost_record(record, recomputed_deterministic=partial)
    assert any("no independent recomputation for 'episodes'" in problem for problem in problems)


def test_verification_does_not_require_environment_costs_to_reproduce():
    """Requiring wall clock to match across hosts would fail honestly or hide a real change."""
    record = _record()
    record["environment_costs"]["wall_clock_seconds"] = 999.0
    record["environment_costs"]["peak_rss_bytes"] = 1
    assert verify_cost_record(record, recomputed_deterministic=_deterministic()) == []
