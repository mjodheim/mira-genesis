"""M113: the frozen rules, the boundaries, and the two M112 defects that must not return."""

from __future__ import annotations

import json

import pytest

from metamorphosis import carrier_host as host
from metamorphosis import m113_carrier_bank as bank
from metamorphosis import m113_carrier_devkit as devkit
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m113_runtime as runtime
from metamorphosis.blind_bank_protocol import opaque_domain_id

NONCE = "a" * 64
BUDGET = 4000


def qualifying_carriers(count: int, seed: str = "test") -> list[dict]:
    found: list[dict] = []
    index = 0
    while len(found) < count:
        carrier = devkit.development_carrier("%s:%d" % (seed, index))
        if evaluator.qualification_report(carrier)["qualifies"]:
            found.append(carrier)
        index += 1
    return found


# ---------------------------------------------------------------- qualification is structural


def test_qualification_is_decided_by_an_exact_fixed_point():
    carrier = qualifying_carriers(1)[0]
    report = evaluator.qualification_report(carrier)
    assert report["qualifies"] is True
    assert report["clauses"]["closed_by_fixed_point"] is True
    assert report["closure_iterations"] >= 1
    assert report["max_observation_depth"] >= evaluator.MIN_OBSERVATION_DEPTH
    assert report["unreachable_observation_count"] >= 1


def test_a_carrier_that_cannot_refuse_anything_does_not_qualify():
    raw = {
        "surface": {
            "kind": "json_object",
            "ok_token": "ok",
            "error_token": "err",
            "field_separator": " ",
            "pair_separator": "=",
            "action_key": "op",
            "argument_key": "arg",
            "status_key": "st",
        },
        "cells": [{"name": "one", "size": 2}],
        "initial": [0],
        "visible": [True],
        "errors": ["nope"],
        "actions": [
            {
                "name": "flip",
                "arity": 0,
                "guard": [],
                "effect": [{"cell": 0, "mode": "add", "operand": 1}],
                "error": "nope",
            },
            {
                "name": "zero",
                "arity": 0,
                "guard": [],
                "effect": [{"cell": 0, "mode": "set", "operand": 0}],
                "error": "nope",
            },
        ],
    }
    report = evaluator.qualification_report(host.validate_carrier(raw))
    assert report["qualifies"] is False
    assert "the_carrier_imposes_a_protocol" in report["blocking_clauses"]


# ---------------------------------------------------------------- the pair is one object


def test_the_twins_differ_in_the_target_and_nothing_else():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    evaluator.assert_demand_pair_delta(pair)
    left = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    right = evaluator.materialize_twin(pair, evaluator.CLASS_UNREACHABLE)
    differing = sorted(key for key in left if left[key] != right[key])
    assert differing == ["demand_class", "target"]
    assert left["entry"] == right["entry"]
    assert left["session_budget"] == right["session_budget"]


def test_a_twin_that_grows_a_field_of_its_own_is_refused():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    tampered = json.loads(json.dumps(pair))
    tampered["targets"][evaluator.CLASS_UNREACHABLE] = tampered["targets"][
        evaluator.CLASS_REACHABLE
    ]
    with pytest.raises(evaluator.EvaluationError):
        evaluator.assert_demand_pair_delta(tampered)


def test_the_unreachable_twin_is_unreachable_by_exhaustion_not_by_phrasing():
    for carrier in qualifying_carriers(6):
        pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
        target = tuple(pair["targets"][evaluator.CLASS_UNREACHABLE])
        closure = host.observation_closure(carrier)
        assert target in {tuple(item) for item in closure["unreachable_observations"]}
        entry = pair["shared"]["entry"]
        trial = evaluator.component_trial(
            carrier,
            target,
            action_width=entry["action_width"],
            observation_width=entry["observation_width"],
            composition_space=entry["composition_space"],
        )
        assert trial["resolving_components"] == []
        assert trial["already_constructible"] is False


def test_exactly_one_component_resolves_the_reachable_twin():
    for carrier in qualifying_carriers(8):
        pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
        entry = pair["shared"]["entry"]
        trial = evaluator.component_trial(
            carrier,
            pair["targets"][evaluator.CLASS_REACHABLE],
            action_width=entry["action_width"],
            observation_width=entry["observation_width"],
            composition_space=entry["composition_space"],
        )
        assert trial["determined"] is True
        assert trial["component"] == pair["ground_truth"]["component"]


# ---------------------------------------------------------------- scoring reads the carrier


def test_a_claimed_sequence_is_replayed_and_not_believed():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    lie = {
        "schema": evaluator.OUTCOME_SCHEMA,
        "verdict": evaluator.OUTCOME_CONSTRUCTED,
        "sequence": [],
        "invocations_used": 1,
    }
    score = evaluator.score_attempt(carrier, demand, lie)
    assert score["correct_construction"] is False
    assert score["unmet_construction"] is True
    assert score["replay"]["requests"] == 0


def test_claiming_an_unreachable_target_is_scored_as_an_invented_adapter():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_UNREACHABLE)
    claim = {
        "schema": evaluator.OUTCOME_SCHEMA,
        "verdict": evaluator.OUTCOME_CONSTRUCTED,
        "sequence": [],
        "invocations_used": 1,
    }
    score = evaluator.score_attempt(carrier, demand, claim)
    assert score["invented_adapter"] is True
    assert score["reached_target"] is False


def test_refusing_the_unreachable_twin_is_a_calibrated_refusal():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_UNREACHABLE)
    outcome = {
        "schema": evaluator.OUTCOME_SCHEMA,
        "verdict": evaluator.OUTCOME_REFUSED,
        "invocations_used": 12,
    }
    score = evaluator.score_attempt(carrier, demand, outcome)
    assert score["calibrated_refusal"] is True
    assert score["invented_adapter"] is False


def test_a_demand_belonging_to_another_carrier_is_refused():
    left, right = qualifying_carriers(2)
    pair = evaluator.derive_demand_pair(left, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    outcome = {
        "schema": evaluator.OUTCOME_SCHEMA,
        "verdict": evaluator.OUTCOME_REFUSED,
        "invocations_used": 1,
    }
    with pytest.raises(evaluator.EvaluationError):
        evaluator.score_attempt(right, demand, outcome)


# ---------------------------------------------------------------- the M112 cardinality defect


def test_the_cardinality_identity_holds_on_a_well_formed_materialization():
    report = evaluator.cardinality_report(24, 24, 24, 22, 5, 3)
    evaluator.assert_cardinality(report)
    assert report["identities_hold"] is True
    assert report["minimum_met"] is True


def test_the_m112_defect_would_now_fail_the_guard():
    """A hundred requested, twenty enveloped. The exact shape of M112's materialization defect."""
    report = evaluator.cardinality_report(100, 100, 20, 20, 5, 3)
    assert report["identities_hold"] is False
    with pytest.raises(evaluator.EvaluationError):
        evaluator.assert_cardinality(report)


def test_a_non_monotone_cardinality_chain_is_refused():
    report = evaluator.cardinality_report(24, 24, 24, 24, 30, 3)
    with pytest.raises(evaluator.EvaluationError):
        evaluator.assert_cardinality(report)


def test_the_minimum_can_be_missed():
    report = evaluator.cardinality_report(24, 24, 24, 20, 2, 3)
    evaluator.assert_cardinality(report)
    assert report["minimum_met"] is False


# ---------------------------------------------------------------- the payload contract


def payload(carriers, *, development=False):
    return {
        "schema": bank.DEVELOPMENT_PAYLOAD_SCHEMA if development else bank.CARRIER_PAYLOAD_SCHEMA,
        "bank_nonce": NONCE,
        "carriers": [
            dict(
                {
                    key: value
                    for key, value in item.items()
                    if key not in ("schema", "carrier_digest", "carrier_ref")
                },
                carrier_ref=opaque_domain_id(NONCE, index),
            )
            for index, item in enumerate(carriers)
        ],
    }


def test_a_well_formed_payload_is_accepted_and_counted():
    carriers = qualifying_carriers(4)
    accepted = bank.validate_carrier_bank_payload(payload(carriers))
    assert accepted["records_emitted"] == 4
    assert accepted["carriers_enveloped"] == 4
    assert accepted["schema_valid_carriers"] == 4
    assert accepted["distinct_structural_signatures"] == 4
    assert accepted["repeated_structural_signatures"] == []


def test_a_payload_naming_a_key_a_blind_generator_could_not_know_is_refused():
    carriers = qualifying_carriers(2)
    raw = payload(carriers)
    raw["carriers"][0]["component"] = "signal_interface"
    with pytest.raises(bank.CarrierBankError, match="could not know"):
        bank.validate_carrier_bank_payload(raw)


def test_a_contaminated_payload_is_refused():
    carriers = qualifying_carriers(2)
    raw = payload(carriers)
    raw["carriers"][0]["cells"][0]["name"] = "lineage"
    with pytest.raises(bank.CarrierBankError, match="contaminated"):
        bank.validate_carrier_bank_payload(raw)


def test_an_identifier_not_derived_from_the_nonce_is_refused():
    carriers = qualifying_carriers(2)
    raw = payload(carriers)
    raw["carriers"][1]["carrier_ref"] = opaque_domain_id(NONCE, 7)
    with pytest.raises(bank.CarrierBankError, match="opaque identifier"):
        bank.validate_carrier_bank_payload(raw)


def test_a_malformed_body_is_counted_rather_than_repaired():
    carriers = qualifying_carriers(3)
    raw = payload(carriers)
    raw["carriers"][1]["cells"] = []
    accepted = bank.validate_carrier_bank_payload(raw)
    assert accepted["records_emitted"] == 3
    assert accepted["schema_valid_carriers"] == 2
    assert len(accepted["refused_carriers"]) == 1
    assert accepted["refused_carriers"][0]["index"] == 1


def test_a_development_payload_cannot_pass_as_a_qualifying_one():
    carriers = qualifying_carriers(2)
    with pytest.raises(bank.CarrierBankError, match="schema is not the declared one"):
        bank.validate_carrier_bank_payload(payload(carriers, development=True))


# ---------------------------------------------------------------- the plan must be able to fail


def a_plan(**overrides):
    plan = {
        "schema": bank.ANALYSIS_PLAN_SCHEMA,
        "milestone": "M113",
        "hypothesis": "H58",
        "frozen_before_generation": True,
        "requested_carrier_count": 24,
        "minimum_qualifying_carriers": 3,
        "measured_qualification_rate": 0.23,
        "measured_over_carriers": 1200,
        "cardinality_derivation": {
            "records_to_carriers": "identity",
            "carriers_to_qualifying": "measured_after_reveal",
        },
        "qualification_rule": "m113_evaluator.qualification_report",
        "demand_derivation_rule": "m113_evaluator.derive_demand_pair",
        "closure_rule": "exact_fixed_point_no_inherited_bound",
        "insufficient_bank_verdict": "negative",
        "retries_permitted": False,
        "evidence_tier": "blind_generated_sealed_bank",
        "claim_boundary": bank.CARRIER_BANK_CLAIM_BOUNDARY,
    }
    plan.update(overrides)
    plan["plan_commitment_sha256"] = bank.analysis_plan_commitment(plan)
    return plan


def test_a_well_formed_plan_validates():
    bank.validate_analysis_plan(a_plan())


@pytest.mark.parametrize(
    "override",
    [
        {"minimum_qualifying_carriers": 1},
        {"minimum_qualifying_carriers": 20},
        {"retries_permitted": True},
        {"insufficient_bank_verdict": "retry"},
        {"closure_rule": "bounded_at_seven_nodes"},
        {"qualification_rule": "chosen_after_reveal"},
        {"demand_derivation_rule": "chosen_by_the_project"},
        {"measured_over_carriers": 40},
        {"cardinality_derivation": {"records_to_carriers": "five_to_one",
                                    "carriers_to_qualifying": "measured_after_reveal"}},
        {"cardinality_derivation": {"records_to_carriers": "identity",
                                    "carriers_to_qualifying": "identity"}},
    ],
)
def test_a_plan_that_weakens_the_contract_is_refused(override):
    with pytest.raises(bank.CarrierBankError):
        bank.validate_analysis_plan(a_plan(**override))


def test_a_drifted_plan_commitment_is_refused():
    plan = a_plan()
    plan["minimum_qualifying_carriers"] = 4
    with pytest.raises(bank.CarrierBankError, match="commitment drifted"):
        bank.validate_analysis_plan(plan)


def test_the_claim_boundary_does_not_claim_what_it_must_not():
    boundary = bank.CARRIER_BANK_CLAIM_BOUNDARY
    assert boundary["human_independence"] is False
    assert boundary["external_reproduction"] is False
    assert boundary["closes_g1"] is False
    assert boundary["closes_g4"] is False
    assert boundary["advances_any_generality_gate"] is False
    assert boundary["agi"] is False
    assert boundary["removes_substrate_authorship"] is False


# ---------------------------------------------------------------- the phase machine fails closed


def test_the_readiness_report_is_draft_and_never_opens_a_payload(tmp_path):
    report = bank.assess_carrier_bank_readiness(tmp_path)
    assert report["phase"] == "draft"
    assert report["ready_for_reveal"] is False
    assert report["revealed"] is False
    assert report["blockers"]
    assert report["payload_never_opened_by_this_assessor"] is True


def test_the_tested_system_binding_refuses_a_drifted_member(tmp_path):
    protocol = {
        "schema": bank.SYSTEM_PROTOCOL_SCHEMA,
        "tested_system_unmodified_after_reveal": True,
        "tested_system_digests": {path: "0" * 64 for path in bank.TESTED_SYSTEM_PATHS},
    }
    protocol["protocol_commitment_sha256"] = bank.system_protocol_commitment(protocol)
    with pytest.raises(bank.CarrierBankError, match="changed after it was frozen"):
        bank.validate_system_protocol(protocol, root=bank.EXPERIMENT_DIRECTORY.parent.parent)


# ---------------------------------------------------------------- the learner


def test_lineage_state_round_trips_and_refuses_a_drifted_digest():
    state = runtime.create_state()
    assert runtime.decode_state(runtime.encode_state(state))["state_digest"] == state["state_digest"]
    tampered = dict(state, action_width=3)
    with pytest.raises(runtime.CarrierLineageError, match="digest mismatch"):
        runtime.decode_state(tampered)


def test_the_adapter_is_equal_across_arms_and_the_cascade_is_not():
    """The only thing that may differ between arms is the Genesis machinery, and it is measured."""
    fresh = runtime.create_state()
    acquired = runtime.create_state(rules=[_first_acquired_rule()])
    assert runtime.adapter_projection(fresh) == runtime.adapter_projection(acquired)
    assert fresh["state_digest"] != acquired["state_digest"]


def _first_acquired_rule() -> dict:
    """Generation one, restored from the producer's frozen bytes rather than reconstructed."""
    result = json.loads(
        (bank.EXPERIMENT_DIRECTORY.parent / "M109" / "RESULT.json").read_bytes().decode("ascii")
    )
    return result["scientific_evidence"]["generation_one"]["acquisition"]["adopted_rule"]


def test_a_state_whose_component_registry_drifted_is_refused():
    state = runtime.create_state()
    tampered = dict(state, component_registry=["operator_table"])
    with pytest.raises(runtime.CarrierLineageError, match="component registry changed"):
        runtime.decode_state(tampered)


def test_a_state_whose_feature_vocabulary_drifted_is_refused():
    state = runtime.create_state()
    tampered = dict(state, feature_vocabulary=["g0", "g1", "g2"])
    with pytest.raises(runtime.CarrierLineageError, match="feature vocabulary changed"):
        runtime.decode_state(tampered)


def test_exploration_closes_by_a_fixed_point_and_says_at_which_level():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    state = runtime.create_state(
        action_width=demand["entry"]["action_width"],
        observation_width=demand["entry"]["observation_width"],
        composition_space=runtime.COMPLETE_SPACE,
    )
    channel = host.Channel(carrier, demand["carrier_ref"], BUDGET)
    model = runtime.explore(channel, state, demand["observed_cells"])
    assert model["closed"] is True
    assert model["budget_exhausted"] is False
    assert model["closed_at_level"] == model["levels_expanded"]


def test_a_starved_channel_yields_undetermined_rather_than_a_refusal():
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), 6)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    state = runtime.create_state(
        action_width=demand["entry"]["action_width"],
        observation_width=demand["entry"]["observation_width"],
        composition_space=demand["entry"]["composition_space"],
    )
    channel = host.Channel(carrier, demand["carrier_ref"], 6)
    outcome = runtime.resolve(state, channel, demand)
    assert outcome["verdict"] == evaluator.OUTCOME_UNDETERMINED
    assert outcome["reason"] == runtime.UNDETERMINED_BUDGET


def test_a_refusal_carries_a_closed_exploration_rather_than_an_exhausted_budget():
    refusals = 0
    for index, carrier in enumerate(qualifying_carriers(8)):
        pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, index), BUDGET)
        demand = evaluator.materialize_twin(pair, evaluator.CLASS_UNREACHABLE)
        state = runtime.create_state(
            action_width=demand["entry"]["action_width"],
            observation_width=demand["entry"]["observation_width"],
            composition_space=demand["entry"]["composition_space"],
        )
        channel = host.Channel(carrier, demand["carrier_ref"], BUDGET)
        outcome = runtime.resolve(state, channel, demand)
        if outcome["verdict"] == evaluator.OUTCOME_REFUSED:
            refusals += 1
            assert outcome["exploration_closed"] is True
    assert refusals >= 1


def test_every_arm_stays_inside_the_budget_it_was_given():
    for index, carrier in enumerate(qualifying_carriers(6)):
        pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, index), BUDGET)
        for demand_class in evaluator.DEMAND_CLASSES:
            demand = evaluator.materialize_twin(pair, demand_class)
            state = runtime.create_state(
                action_width=demand["entry"]["action_width"],
                observation_width=demand["entry"]["observation_width"],
                composition_space=demand["entry"]["composition_space"],
            )
            channel = host.Channel(carrier, demand["carrier_ref"], BUDGET)
            outcome = runtime.resolve(state, channel, demand)
            score = evaluator.score_attempt(carrier, demand, outcome)
            assert score["within_budget"] is True


# ---------------------------------------------------------------- the pre-freeze finding


def test_the_inherited_vocabulary_is_recorded_as_ambiguous_before_any_bank_exists():
    """The devkit survey's central finding, asserted so it cannot quietly change.

    If this ever comes out empty, the pre-registration's prediction is no longer supported by the
    development evidence it cites, and the claim in `PRE_REGISTRATION.md` has to be rewritten rather
    than left standing.
    """
    survey = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "DEVKIT_SURVEY.json").read_text(encoding="ascii")
    )
    assert survey["sample"] >= 1000
    assert survey["ambiguous_feature_rows"]
    assert survey["inherited_vocabulary_is_a_function_on_this_sample"] is False
    assert survey["every_carrier_closed_by_fixed_point"] is True
    assert survey["measures_the_blind_generator"] is False


# ---------------------------------------------------------------- the adversarial pass, kept

def test_a_bounded_space_is_complete_for_its_bound_and_not_budget_exhausted():
    """The two completeness facts are different, and conflating them cost the bounded arm.

    A first draft reported `closed: false` whenever the composition bound stopped the expansion, so
    every bounded attempt returned `undetermined` with a budget reason -- while only two attempts in
    eighty-eight had actually reached the ceiling. A refusal inside a bounded composition space is a
    reach fact about that space, which is the whole reason the space is an axis.
    """
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    state = runtime.create_state(
        action_width=demand["entry"]["action_width"],
        observation_width=demand["entry"]["observation_width"],
        composition_space=runtime.BOUNDED_SPACE,
    )
    channel = host.Channel(carrier, demand["carrier_ref"], BUDGET)
    model = runtime.explore(channel, state, demand["observed_cells"])
    assert model["budget_exhausted"] is False
    assert model["complete_for_the_bound"] is True
    assert model["closed"] is True
    assert model["levels_expanded"] == runtime.BOUNDED_COMPOSITION_DEPTH


def test_a_distinguishing_shortfall_never_reads_as_the_absence_of_a_collision():
    """A budget that cannot afford the comparison is not evidence that the projection is a state."""
    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    state = runtime.create_state(
        action_width=demand["entry"]["action_width"],
        observation_width=demand["entry"]["observation_width"],
        composition_space=runtime.COMPLETE_SPACE,
    )
    generous = runtime.explore(
        host.Channel(carrier, demand["carrier_ref"], BUDGET), state, demand["observed_cells"]
    )
    starved = None
    for budget in range(8, int(generous["invocations_used"]) + 1, 4):
        model = runtime.explore(
            host.Channel(carrier, demand["carrier_ref"], budget), state, demand["observed_cells"]
        )
        if model["distinguishing_completed"] is False:
            starved = model
            break
    if starved is None:
        pytest.skip("this carrier's distinguishing phase is never the stage that runs out")
    assert starved["closed"] is False
    assert starved["budget_exhausted"] is True


def test_g0_does_not_imply_g1(tmp_path):
    """`g1` reads the search, not the claim, so all eight feature rows stay occupiable.

    Reading the trusted verdict coupled the two: withholding a claim whenever the view was not a
    state made `g0` true imply `g1` true, four of the eight rows became unreachable, and over three
    hundred devkit carriers the reachable arm landed zero times out of twenty-one on a row where the
    inherited cascades disagree.
    """
    rows = set()
    for index in range(120):
        carrier = devkit.development_carrier("g0g1:%d" % index)
        if not evaluator.qualification_report(carrier)["qualifies"]:
            continue
        for pair in evaluator.derive_demand_pairs(carrier, opaque_domain_id(NONCE, index), BUDGET):
            for demand_class in evaluator.DEMAND_CLASSES:
                demand = evaluator.materialize_twin(pair, demand_class)
                state = runtime.create_state(
                    action_width=demand["entry"]["action_width"],
                    observation_width=demand["entry"]["observation_width"],
                    composition_space=demand["entry"]["composition_space"],
                )
                outcome = runtime.resolve(
                    state, host.Channel(carrier, demand["carrier_ref"], BUDGET), demand
                )
                for step in outcome["trace"]:
                    values = step["features"]["values"]
                    rows.add(step["features"]["row_index"])
                    if values[0] and not values[1]:
                        return  # a row with g0 true and g1 false exists; the coupling is gone
    raise AssertionError(
        "no observed feature row has g0 true and g1 false; rows seen: %s" % sorted(rows)
    )


def test_the_demand_rule_poses_one_pair_per_attribution_row():
    for index in range(40):
        carrier = devkit.development_carrier("perrow:%d" % index)
        if not evaluator.qualification_report(carrier)["qualifies"]:
            continue
        census = evaluator.attribution_census(carrier)
        pairs = evaluator.derive_demand_pairs(carrier, opaque_domain_id(NONCE, index), BUDGET)
        posed = [pair["ground_truth"]["row_index"] for pair in pairs]
        assert posed == sorted(set(posed))
        assert set(posed) == set(evaluator.canonical_pairs_by_row(census))
        for pair in pairs:
            evaluator.assert_demand_pair_delta(pair)
        return
    raise AssertionError("no qualifying carrier was produced by this seed range")
