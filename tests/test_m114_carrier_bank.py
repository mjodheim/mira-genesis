"""M114's contracts: the mechanism inherited, the filiation carried, the delivery rule enforced."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m113_carrier_bank as m113
from metamorphosis import m114_carrier_bank as bank
from metamorphosis import m114_delivery as delivery
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

ROOT = Path(bank.EXPERIMENT_DIRECTORY).parents[1]


def _plan() -> dict:
    return json.loads(
        (bank.EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN_CANDIDATE.json").read_bytes().decode("utf-8")
    )


def _spec() -> dict:
    return json.loads(
        (bank.EXPERIMENT_DIRECTORY / "GENERATOR_SPEC_CANDIDATE.json").read_bytes().decode("utf-8")
    )


def _reseal_plan(plan: dict) -> dict:
    plan["plan_commitment_sha256"] = bank.analysis_plan_commitment(plan)
    return plan


def _reseal_spec(spec: dict) -> dict:
    spec["canonical_request_body_sha256"] = sha256_hex(
        canonical_bytes(spec["canonical_request_body"])
    )
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    return spec


# ------------------------------------------------------------------ the inherited mechanism


def test_every_scientific_rule_is_m113s_verbatim():
    """A corrective replication that quietly moved a scientific rule would be a new experiment.

    Checked field by field against M113's frozen plan rather than described, so a future edit to
    either plan breaks this rather than passing unnoticed.
    """
    predecessor = json.loads(
        (m113.EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json").read_bytes().decode("utf-8")
    )
    plan = _plan()
    bookkeeping = {"schema", "milestone", "hypothesis", "plan_commitment_sha256"}
    for key, value in predecessor.items():
        if key in bookkeeping:
            continue
        assert plan[key] == value, "M114 changed the scientific rule %r" % key

    assert plan["requested_carrier_count"] == 24
    assert plan["minimum_qualifying_carriers"] == 3
    assert plan["minimum_distinct_qualifying_structures"] == 3
    assert plan["closure_rule"] == "exact_fixed_point_no_inherited_bound"
    assert plan["retries_permitted"] is False
    assert plan["selection_among_carriers_permitted"] is False
    assert plan["manual_correction_permitted"] is False
    assert plan["insufficient_bank_verdict"] == "negative"
    assert plan["inherited_plan_commitment_sha256"] == predecessor["plan_commitment_sha256"]


def test_the_generator_sees_exactly_what_m113s_would_have():
    """Same prompt, same schema, same input, by digest."""
    assert all(bank.generator_inputs_are_m113s(ROOT).values())
    for name, digest in bank.GENERATOR_INPUT_DIGESTS.items():
        assert sha256_hex((m113.EXPERIMENT_DIRECTORY / name).read_bytes()) == digest


def test_the_frozen_request_body_is_m113s_byte_for_byte():
    predecessor = json.loads(
        (m113.EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json").read_bytes().decode("utf-8")
    )
    spec = _spec()
    assert spec["canonical_request_body"] == predecessor["canonical_request_body"]
    assert spec["canonical_request_body_sha256"] == predecessor["canonical_request_body_sha256"]
    for key in ("model", "provider", "quantization", "quantization_source",
                "quantization_is_runtime_attested", "transport", "endpoint"):
        assert spec["generator_identity"][key] == predecessor["generator_identity"][key]


def test_the_inherited_rules_are_delegated_and_not_re_typed():
    """A rule this milestone re-typed would be a rule it could quietly soften.

    Breaking any inherited rule must be refused by M114 too, because M114 delegates rather than
    restates.
    """
    for mutate in (
        lambda p: p.update(minimum_qualifying_carriers=1),
        lambda p: p.update(insufficient_bank_verdict="retry"),
        lambda p: p["cardinality_derivation"].update(carriers_to_qualifying="identity"),
        lambda p: p.update(minimum_distinct_qualifying_structures=99),
    ):
        plan = _plan()
        mutate(plan)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_analysis_plan(_reseal_plan(plan))


# ------------------------------------------------------------------ the filiation


def test_the_plan_must_carry_the_m113_filiation_exactly():
    """The record has to be able to say what M113 was and what M114 is, without either drifting."""
    plan = _plan()
    assert plan["filiation"] == bank.FILIATION
    f = bank.FILIATION
    assert f["predecessor"] == "M113"
    assert f["predecessor_outcome"] == "instrument-aborted before bank materialization"
    assert f["predecessor_record_is_closed_and_not_repaired"] is True
    assert f["this_hypothesis"] == "H59"
    assert f["delivery_rule_decided_after_m113_instrument_failure"] is True
    assert f["delivery_rule_decided_before_any_m114_bank_existed"] is True
    assert f["delivery_rule_decided_without_any_observation_of_the_hypothesis"] is True
    assert f["delivery_rule_was_never_part_of_m113"] is True

    for mutate in (
        lambda p: p["filiation"].update(delivery_rule_was_never_part_of_m113=False),
        lambda p: p["filiation"].update(predecessor_record_is_closed_and_not_repaired=False),
        lambda p: p["filiation"].update(
            delivery_rule_decided_without_any_observation_of_the_hypothesis=False
        ),
        lambda p: p.pop("filiation"),
    ):
        plan = _plan()
        mutate(plan)
        with pytest.raises(bank.CarrierBankError, match="filiation"):
            bank.validate_analysis_plan(_reseal_plan(plan))


def test_m114_carries_its_own_hypothesis_number():
    """One milestone, one hypothesis. M106 established that a corrective replication takes a new
    number rather than inheriting its predecessor's, so the predecessor's record stays as it was."""
    assert bank.HYPOTHESIS == "H59"
    assert m113.MILESTONE == "M113"
    plan = _plan()
    plan["hypothesis"] = "H58"
    with pytest.raises(bank.CarrierBankError, match="H59"):
        bank.validate_analysis_plan(_reseal_plan(plan))


# ------------------------------------------------------------------ the delivery clauses


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(max_delivery_attempts=4),
    lambda p: p.update(max_bank_materializations=2),
    lambda p: p.update(retry_wait_seconds=1),
    lambda p: p.update(only_capacity_rejection_before_generation_may_be_retried=False),
    lambda p: p.update(a_scientific_outcome_is_never_retried=False),
    lambda p: p.pop("delivery_semantics"),
])
def test_a_plan_that_weakens_the_delivery_rule_is_refused(mutate):
    plan = _plan()
    mutate(plan)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_analysis_plan(_reseal_plan(plan))


def test_the_candidate_spec_cannot_pass_as_frozen():
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(
            _spec(), root=ROOT, plan_commitment_sha256=_plan()["plan_commitment_sha256"]
        )


def test_a_fully_pinned_spec_validates_and_still_refuses_a_substitution():
    spec = _reseal_spec(dict(_spec(), frozen_before_generation=True))
    spec.pop("unset_before_freeze", None)
    spec = _reseal_spec(spec)
    bank.validate_generator_spec(
        spec, root=ROOT, plan_commitment_sha256=_plan()["plan_commitment_sha256"]
    )
    for mutate in (
        lambda s: s["generator_identity"].update(provider="Together"),
        lambda s: s["generator_identity"].update(model="deepseek/deepseek-v4-flash:latest"),
        lambda s: s["routing"].update(allow_fallbacks=True),
        lambda s: s.update(delivery_semantics="ad-hoc"),
    ):
        broken = json.loads(json.dumps(spec))
        mutate(broken)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_generator_spec(_reseal_spec(broken), root=ROOT)


# ------------------------------------------------------------------ the phase machine


def test_the_phase_machine_is_draft_and_names_the_delivery_ledger(tmp_path):
    report = bank.assess_carrier_bank_readiness(tmp_path)
    assert report["phase"] == "draft"
    assert report["revealed"] is False
    assert report["hypothesis"] == "H59"
    assert report["filiation"]["predecessor"] == "M113"
    assert any("DELIVERY_LEDGER.json" in b for b in report["blockers"])


def test_a_ledger_with_no_materialization_cannot_reach_a_sealed_phase(tmp_path):
    """Three capacity rejections are a complete, permitted delivery history with no bank."""
    experiment = tmp_path / "experiments" / "M114"
    experiment.mkdir(parents=True)
    ledger = {
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": "M114",
        "spec_commitment_sha256": "c" * 64,
        "bank_materialization_index": None,
        "attempts": [
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
        ],
    }
    (experiment / "DELIVERY_LEDGER.json").write_bytes(canonical_bytes(ledger) + b"\n")

    report = bank.assess_carrier_bank_readiness(tmp_path)
    assert report["revealed"] is False
    assert report["phase"] in ("draft", "spec_frozen")
    assert any("materialized a bank" in b for b in report["blockers"])
    assert report["delivery_summary"]["delivery_attempts"] == 3
    assert report["delivery_summary"]["bank_materializations"] == 0


def test_the_no_retry_enumeration_cannot_be_narrowed_in_the_plan():
    """The list of things that are final on their first outcome is inside the commitment.

    A milestone permitted three attempts has exactly one clause it must not be able to quietly
    narrow, and this is it. Stating the enumeration only in a module docstring would leave it
    outside the plan's digest, where a later edit could shorten it without the commitment moving.
    """
    assert "any_scientific_outcome_including_p22_false" in bank.NEVER_RETRIED
    assert "timeout_after_transmission_in_an_unestablished_state" in bank.NEVER_RETRIED
    bank.validate_analysis_plan(_plan())

    for mutate in (
        lambda p: p.__setitem__("never_retried", [
            item for item in p["never_retried"]
            if item != "any_scientific_outcome_including_p22_false"
        ]),
        lambda p: p.__setitem__("never_retried", list(p["never_retried"]) + ["a_429"]),
        lambda p: p.__setitem__("never_retried", list(reversed(p["never_retried"]))),
        lambda p: p.pop("never_retried"),
    ):
        plan = _plan()
        mutate(plan)
        with pytest.raises(bank.CarrierBankError, match="never retried"):
            bank.validate_analysis_plan(_reseal_plan(plan))
