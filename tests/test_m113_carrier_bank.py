"""M113: the frozen rules, the boundaries, and the two M112 defects that must not return."""

from __future__ import annotations

import json
from pathlib import Path

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
    report = evaluator.cardinality_report(24, 24, 24, 22, 5, 3, 5, 3)
    evaluator.assert_cardinality(report)
    assert report["identities_hold"] is True
    assert report["minimum_met"] is True
    assert report["distinct_minimum_met"] is True
    assert report["renaming_collapse"] == 0


def test_the_m112_defect_would_now_fail_the_guard():
    """A hundred requested, twenty enveloped. The exact shape of M112's materialization defect."""
    report = evaluator.cardinality_report(100, 100, 20, 20, 5, 3, 5, 3)
    assert report["identities_hold"] is False
    with pytest.raises(evaluator.EvaluationError):
        evaluator.assert_cardinality(report)


def test_a_non_monotone_cardinality_chain_is_refused():
    report = evaluator.cardinality_report(24, 24, 24, 24, 30, 3, 30, 3)
    with pytest.raises(evaluator.EvaluationError):
        evaluator.assert_cardinality(report)


def test_more_distinct_structures_than_qualifying_carriers_is_refused():
    """Every distinct structure is a qualifying carrier, so the reverse cannot happen."""
    report = evaluator.cardinality_report(24, 24, 24, 24, 5, 3, 9, 3)
    assert report["monotone"] is False
    with pytest.raises(evaluator.EvaluationError):
        evaluator.assert_cardinality(report)


def test_the_minimum_can_be_missed():
    report = evaluator.cardinality_report(24, 24, 24, 20, 2, 3, 2, 3)
    evaluator.assert_cardinality(report)
    assert report["minimum_met"] is False
    assert report["distinct_minimum_met"] is False


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
            "qualifying_to_distinct_structures": "measured_after_reveal",
        },
        "minimum_distinct_qualifying_structures": 3,
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
                                    "carriers_to_qualifying": "measured_after_reveal",
                                    "qualifying_to_distinct_structures": "measured_after_reveal"}},
        {"cardinality_derivation": {"records_to_carriers": "identity",
                                    "carriers_to_qualifying": "identity",
                                    "qualifying_to_distinct_structures": "measured_after_reveal"}},
        {"cardinality_derivation": {"records_to_carriers": "identity",
                                    "carriers_to_qualifying": "measured_after_reveal",
                                    "qualifying_to_distinct_structures": "identity"}},
        {"minimum_distinct_qualifying_structures": 1},
        {"minimum_distinct_qualifying_structures": 9},
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
        "tested_system_digest_modes": dict(bank.TESTED_SYSTEM_DIGEST_MODES),
    }
    protocol["protocol_commitment_sha256"] = bank.system_protocol_commitment(protocol)
    with pytest.raises(bank.CarrierBankError, match="changed after it was frozen"):
        bank.validate_system_protocol(protocol, root=bank.EXPERIMENT_DIRECTORY.parent.parent)


def test_the_tested_system_binding_refuses_an_undeclared_digest_mode():
    """A default is a decision nobody made, and the decision is which bytes a third party reproduces."""
    root = bank.EXPERIMENT_DIRECTORY.parent.parent
    protocol = {
        "schema": bank.SYSTEM_PROTOCOL_SCHEMA,
        "tested_system_unmodified_after_reveal": True,
        "tested_system_digests": bank.tested_system_digests(root),
        "tested_system_digest_modes": {
            path: mode
            for path, mode in bank.TESTED_SYSTEM_DIGEST_MODES.items()
            if path != "metamorphosis/m109_runtime.py"
        },
    }
    protocol["protocol_commitment_sha256"] = bank.system_protocol_commitment(protocol)
    with pytest.raises(bank.CarrierBankError, match="digest mode"):
        bank.validate_system_protocol(protocol, root=root)


def test_the_tested_system_digest_does_not_depend_on_the_checkout(tmp_path):
    """The defect this mode exists for, constructed rather than argued.

    Four of the eleven bound members are CRLF in this working tree and five belong to frozen
    milestones no attributes file here may extend. A raw-byte binding would therefore pin the
    bytes of one checkout; under `lf_normalized` a CRLF copy and an LF copy hash the same.
    """
    crlf = bytes((13, 10))
    lf = bytes((10,))
    root = bank.EXPERIMENT_DIRECTORY.parent.parent
    reference = bank.tested_system_digests(root)

    for name, convert in (("crlf", lambda raw: raw.replace(crlf, lf).replace(lf, crlf)),
                          ("lf", lambda raw: raw.replace(crlf, lf))):
        checkout = tmp_path / name
        for relative in bank.TESTED_SYSTEM_PATHS:
            target = checkout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(convert((root / relative).read_bytes()))
        assert bank.tested_system_digests(checkout) == reference, name

    # And the mode still binds: a real edit is still refused.
    edited = tmp_path / "lf" / "metamorphosis" / "m113_evaluator.py"
    edited.write_bytes(edited.read_bytes() + b"# drift" + lf)
    assert bank.tested_system_digests(tmp_path / "lf") != reference


def test_this_milestone_declares_no_attributes_file_a_freeze_already_binds():
    """Three protocols bind the four attributes files this milestone would otherwise reach for.

    The root file is bound by M105 and M106; metamorphosis/, scripts/ and tests/ are bound by
    M107, which created them to stop later milestones editing the root. M113 tried both in turn
    and broke an M106 test, then an M107 one. Git reads one attributes filename per directory, so
    there is no fourth place -- which is why the tested system is bound by a declared digest mode
    rather than by an attribute.
    """
    root = bank.EXPERIMENT_DIRECTORY.parent.parent
    frozen_elsewhere = (
        ".gitattributes",
        "metamorphosis/.gitattributes",
        "scripts/.gitattributes",
        "tests/.gitattributes",
    )
    for relative in frozen_elsewhere:
        text = (root / relative).read_text(encoding="utf-8").lower()
        assert "m113" not in text, relative
        assert "carrier_host" not in text, relative

    local = bank.EXPERIMENT_DIRECTORY / ".gitattributes"
    assert local.is_file()
    assert set(bank.TESTED_SYSTEM_DIGEST_MODES.values()) == {"lf_normalized"}


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


# ---------------------------------------------------------------- producer death and preservation


def test_an_isolated_capsule_cannot_reach_either_producer_result():
    """M099's distinction: a capability that lives in one process's memory is not the lineage's.

    The capsule is the boundary, and the child measures its own view of it rather than being told.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "m113_runner", bank.EXPERIMENT_DIRECTORY.parent.parent / "scripts" / "run_m113_qualification.py"
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    carrier = qualifying_carriers(1)[0]
    pair = evaluator.derive_demand_pair(carrier, opaque_domain_id(NONCE, 0), BUDGET)
    demand = evaluator.materialize_twin(pair, evaluator.CLASS_REACHABLE)
    state = runtime.create_state(
        action_width=demand["entry"]["action_width"],
        observation_width=demand["entry"]["observation_width"],
        composition_space=demand["entry"]["composition_space"],
    )
    report = runner.run_isolated_arm(state, carrier, demand)
    assert report["started"] is True
    assert report["exit_status"] == 0
    assert report["producer_result_reachable"] is False
    assert report["diagnosis_result_reachable"] is False
    assert report["capsule_holds_no_producer_result"] is True
    assert not any(member.startswith("experiments/") for member in report["capsule_members"])

    in_process = runtime.resolve(
        state, host.Channel(carrier, demand["carrier_ref"], BUDGET), demand
    )
    assert report["outcome"]["verdict"] == in_process["verdict"]
    assert report["outcome"]["sequence"] == in_process["sequence"]


def test_the_preservation_arm_finds_both_predecessors_intact():
    """M113 imports M110 and M111. If it had disturbed them, their own checkers would say so."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "m113_runner2",
        bank.EXPERIMENT_DIRECTORY.parent.parent / "scripts" / "run_m113_qualification.py",
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    report = runner.preservation_arm()
    assert report["every_predecessor_still_reproduces"] is True
    for name in ("M110", "M111"):
        entry = report[name]
        assert entry["available"] is True
        assert entry["result_digest_reproduces"] is True
        assert entry["conditions_true"] == entry["conditions_computed"]
        assert entry["false_conditions"] == []


# ---------------------------------------------------------------------- which generation did it


def test_the_checker_decomposes_the_descendant_into_its_generations():
    """`M3` against `T0` is a sum. The record has to say which acquisition the sum is owed to.

    `ablated` holds generation one and the policy, so `M3` minus `ablated` is generation two's whole
    marginal contribution. On the development population it is zero on every outcome measure, and a
    result that reported only the descendant against the fresh control would have credited the
    cascade for an effect the policy produced.
    """
    import importlib.util

    root = bank.EXPERIMENT_DIRECTORY.parent.parent
    spec = importlib.util.spec_from_file_location(
        "m113_checker", root / "scripts" / "check_m113_result.py"
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)

    development = json.loads(
        (root / "experiments" / "M113" / "DEVELOPMENT_RUN.json").read_bytes().decode("ascii")
    )
    decomposition = checker.measurements(development)["generation_decomposition"]

    for name in ("generation_two_marginal", "generation_three_marginal", "cascade_marginal"):
        assert set(decomposition[name]) == set(checker.SCORE_KEYS) | {"attribution_correct"}

    # The marginals are differences and must reconstruct the totals they were taken from.
    for key in checker.SCORE_KEYS:
        assert (
            development["per_arm_totals"]["M3"][key]
            - development["per_arm_totals"]["ablated"][key]
            == decomposition["generation_two_marginal"][key]
        )
        assert (
            development["per_arm_totals"]["M3"][key] - development["per_arm_totals"]["M2"][key]
            == decomposition["generation_three_marginal"][key]
        )

    # The finding itself, pinned so that a later run which changes it has to say so.
    assert decomposition["generation_two_changes_no_outcome_count"] is True
    assert decomposition["generation_two_marginal"]["attribution_correct"] == 1
    assert decomposition["generation_three_marginal"]["correct_construction"] == 9
    assert decomposition["generation_three_marginal"]["calibrated_refusal"] == -22


# ------------------------------------------------------- a bank of renamings is one machine twice


def _rename_carrier(carrier: dict, tag: str) -> dict:
    """A consistent renaming of every cell, action, error and surface token."""
    names = sorted(
        {item["name"] for item in carrier["cells"]}
        | {item["name"] for item in carrier["actions"]}
        | set(carrier["errors"])
        | {
            carrier["surface"][key]
            for key in ("ok_token", "error_token", "action_key", "argument_key", "status_key")
        }
    )
    mapping = {name: "%s%02d" % (tag, position) for position, name in enumerate(names)}
    surface = dict(carrier["surface"])
    for key in ("ok_token", "error_token", "action_key", "argument_key", "status_key"):
        surface[key] = mapping[surface[key]]
    return host.validate_carrier(
        {
            "surface": surface,
            "cells": [
                {"name": mapping[item["name"]], "size": item["size"]} for item in carrier["cells"]
            ],
            "initial": list(carrier["initial"]),
            "visible": list(carrier["visible"]),
            "errors": [mapping[item] for item in carrier["errors"]],
            "actions": [
                {
                    "name": mapping[item["name"]],
                    "arity": item["arity"],
                    "arg_size": item["arg_size"],
                    "guard": item["guard"],
                    "effect": item["effect"],
                    "error": mapping[item["error"]],
                }
                for item in carrier["actions"]
            ],
        }
    )


def test_a_bank_of_renamings_counts_as_one_machine():
    """M112's defect one level up: a count that stands in for the quantity that matters.

    Twenty-four renamings of one machine satisfy every cardinality identity and meet a carrier
    minimum while presenting one experiment. The renaming-invariant signature is what refuses it.
    """
    original = qualifying_carriers(1)[0]
    renamed = _rename_carrier(original, "zz")

    assert host.structural_signature(original) == host.structural_signature(renamed)
    # And they are genuinely different bytes, so nothing else in the chain would have noticed.
    assert original["carrier_digest"] != renamed["carrier_digest"]
    assert evaluator.qualification_report(renamed)["qualifies"] is True

    collapsed = evaluator.cardinality_report(
        requested_carrier_count=24,
        records_emitted=24,
        carriers_enveloped=24,
        schema_valid_carriers=24,
        qualifying_carriers=24,
        minimum_qualifying=3,
        distinct_qualifying_structures=1,
        minimum_distinct_structures=3,
    )
    assert collapsed["identities_hold"] is True
    assert collapsed["monotone"] is True
    # The carrier minimum is met by a bank that holds one machine. The distinct minimum is not.
    assert collapsed["minimum_met"] is True
    assert collapsed["distinct_minimum_met"] is False
    assert collapsed["renaming_collapse"] == 23


def test_a_plan_that_does_not_declare_the_distinct_structure_derivation_is_refused():
    """The derivation has to be declared before the bank exists, or it is chosen after it."""
    plan = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN_CANDIDATE.json").read_bytes().decode("ascii")
    )
    bank.validate_analysis_plan(plan)

    for mutate in (
        lambda p: p["cardinality_derivation"].pop("qualifying_to_distinct_structures"),
        lambda p: p["cardinality_derivation"].update(
            {"qualifying_to_distinct_structures": "identity"}
        ),
        lambda p: p.pop("minimum_distinct_qualifying_structures"),
        lambda p: p.update({"minimum_distinct_qualifying_structures": 1}),
        # Every distinct structure is a qualifying carrier, so this one could never pass.
        lambda p: p.update({"minimum_distinct_qualifying_structures": 99}),
    ):
        broken = json.loads(json.dumps(plan))
        mutate(broken)
        broken["plan_commitment_sha256"] = bank.analysis_plan_commitment(broken)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_analysis_plan(broken)


# -------------------------------------------------- the model-network boundary, measured


def _load_script(name: str, filename: str):
    import importlib.util

    root = bank.EXPERIMENT_DIRECTORY.parent.parent
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_sealed_scope_counts_and_refuses_an_outbound_connection():
    """The qualification phase's silence is measured, not asserted.

    Before this, the runner wrote `model_calls: 0` as a literal and the checker read it back, so
    `P15` agreed with the program it was judging. The scope now intercepts at the two entry points
    every outbound connection in CPython passes through, and a run that reached for the network
    carries the address it reached for.
    """
    import socket

    runner = _load_script("m113_runner_seal", "run_m113_qualification.py")

    with runner.SealedNetwork() as sealed:
        with pytest.raises(runner.SealedNetworkViolation):
            socket.create_connection(("example.invalid", 443), timeout=1)
        with pytest.raises(runner.SealedNetworkViolation):
            socket.socket().connect(("example.invalid", 80))
        sealed.selftest()
        report = sealed.report()

    assert report["network_calls_in_qualification"] == 2
    # Reaching a model and dispatching execution elsewhere both need a socket, so one measurement
    # entails all three counts rather than three separate assertions.
    assert report["model_calls_in_qualification"] == 2
    assert report["remote_execution_calls_in_qualification"] == 2
    assert report["outbound_addresses_attempted"] == [
        "('example.invalid', 443)",
        "('example.invalid', 80)",
    ]

    # And the scope leaves the interpreter as it found it.
    assert socket.create_connection.__module__ == "socket"


def test_a_guard_that_was_never_armed_is_not_a_silent_run():
    """An absent guard and a silent run both record zero. The self-test separates them."""
    runner = _load_script("m113_runner_selftest", "run_m113_qualification.py")
    checker = _load_script("m113_checker_selftest", "check_m113_result.py")

    with runner.SealedNetwork() as live:
        live.selftest()
        armed = live.report()
    with runner.SealedNetwork() as never:
        unarmed = never.report()

    assert armed["network_guard_selftest_intercepted"] is True
    assert unarmed["network_guard_selftest_intercepted"] is False
    # Both report zero calls, and only one of them is evidence.
    assert armed["network_calls_in_qualification"] == unarmed["network_calls_in_qualification"] == 0

    assert checker._phase_boundary(dict(armed))["holds"] is True
    assert checker._phase_boundary(dict(unarmed))["holds"] is False


def test_p15_separates_the_generator_phase_from_the_qualification_phase():
    """M112 required both halves; M113 had dropped the generator half entirely."""
    checker = _load_script("m113_checker_phases", "check_m113_result.py")

    silent = {
        "model_calls_in_qualification": 0,
        "network_calls_in_qualification": 0,
        "remote_execution_calls_in_qualification": 0,
        "network_guard_selftest_intercepted": True,
    }

    # A development run has no generator phase, and that is said rather than quietly satisfied.
    development = dict(silent, is_a_canonical_attempt=False)
    boundary = checker._phase_boundary(development)
    assert boundary["holds"] is True
    assert boundary["generation_phase"] == "not_applicable_on_a_development_run"

    # A canonical run must record exactly one physical invocation.
    canonical = dict(silent, is_a_canonical_attempt=True, model_calls_in_bank_generation=1)
    assert checker._phase_boundary(canonical)["holds"] is True

    for generation_calls in (0, 2, None):
        broken = dict(silent, is_a_canonical_attempt=True)
        if generation_calls is not None:
            broken["model_calls_in_bank_generation"] = generation_calls
        assert checker._phase_boundary(broken)["holds"] is False

    # And a qualification that reached the network fails whatever the generator phase did.
    reached = dict(silent, is_a_canonical_attempt=True, model_calls_in_bank_generation=1)
    reached["network_calls_in_qualification"] = 1
    assert checker._phase_boundary(reached)["holds"] is False


def test_the_qualification_body_cannot_write_its_own_phase_count():
    """The counts are merged in by the sealed wrapper, and a body that wrote them is refused."""
    runner = _load_script("m113_runner_body", "run_m113_qualification.py")
    source = (
        bank.EXPERIMENT_DIRECTORY.parent.parent / "scripts" / "run_m113_qualification.py"
    ).read_text(encoding="utf-8")
    # The literal zeros this repair removed must not come back.
    assert '"model_calls": 0' not in source
    assert '"network_calls": 0' not in source
    assert hasattr(runner, "SealedNetwork")


def test_the_generation_ledger_is_required_before_a_sealed_bank_counts(tmp_path):
    """M113 declared the ledger path and never read it, so nothing counted the invocations.

    One frozen spec admits one materialization and every failed attempt stays in the ledger. Without
    the ledger in the phase machine, several physical requests could be presented afterwards as one
    logical invocation, which is exactly what the no-retry rule exists to prevent.
    """
    report = bank.assess_carrier_bank_readiness(tmp_path)
    assert "missing %s" % bank.GENERATION_LEDGER_PATH.name in report["blockers"]
    assert report["phase"] == "draft"
    assert report["ready_for_reveal"] is False


# -------------------------------------------------- the generator spec, frozen before the identity


def _candidate_spec() -> dict:
    return json.loads(
        (bank.EXPERIMENT_DIRECTORY / "GENERATOR_SPEC_CANDIDATE.json").read_bytes().decode("utf-8")
    )


# The three fields discovery is entitled to answer. Tests that exercise adoption reset them, so
# they do not depend on how far the live candidate has already been filled in.
_DISCOVERY_ANSWERABLE = (
    ("generator_identity", "provider", None),
    ("generator_identity", "provider_serves_the_model_confirmed", False),
    ("generator_identity", "model_identity_confirmed_against_the_api", False),
)


def _unadopted_spec() -> dict:
    """A genuine pre-freeze candidate, whatever state the live artifact has reached.

    Once the identity is frozen the committed candidate equals the frozen spec, so a test that
    read it directly would be describing a moment rather than an invariant -- the mistake M112
    recorded. Every field a freeze fills is reset here, so these tests keep asserting the property
    they name for the whole life of the milestone.
    """
    spec = _candidate_spec()
    for section, field, blank in _DISCOVERY_ANSWERABLE:
        spec[section][field] = blank
    spec.pop("provider_selection", None)
    spec["frozen_before_generation"] = False
    spec["blindness_contract"]["audited_before_the_freeze"] = False
    spec["sampling"]["seed_is_honoured_by_the_provider"] = "unknown"
    spec["unset_before_freeze"] = sorted(
        {"%s.%s" % (section, field) for section, field, _ in _DISCOVERY_ANSWERABLE}
        | {
            "blindness_contract.audited_before_the_freeze",
            "frozen_before_generation",
            "sampling.seed_is_honoured_by_the_provider",
        }
    )
    return spec


def _frozen_spec() -> dict:
    """The candidate with exactly the three fields discovery cannot answer filled in.

    Whatever provider the candidate currently pins is kept, so this follows the real artifact
    rather than a name frozen into the test.
    """
    from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

    spec = _candidate_spec()
    provider = spec["generator_identity"]["provider"]
    assert provider, "the candidate has no provider adopted yet"
    spec["frozen_before_generation"] = True
    spec["blindness_contract"]["audited_before_the_freeze"] = True
    spec["sampling"]["seed_is_honoured_by_the_provider"] = False
    spec.pop("unset_before_freeze", None)
    spec["canonical_request_body_sha256"] = sha256_hex(
        canonical_bytes(spec["canonical_request_body"])
    )
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    return spec


def _root() -> object:
    return bank.EXPERIMENT_DIRECTORY.parent.parent


def _plan_commitment() -> str:
    return json.loads(
        (bank.EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json").read_bytes().decode("utf-8")
    )["plan_commitment_sha256"]


def test_a_spec_with_any_freeze_field_unfilled_cannot_pass_as_a_frozen_one():
    """Each field a freeze fills is load-bearing on its own, not merely in combination.

    Stated as an invariant rather than as a fact about the candidate file: once the identity is
    frozen that file *is* the frozen spec, and a test written against the earlier moment would
    quietly stop testing anything.
    """
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(
            _unadopted_spec(), root=_root(), plan_commitment_sha256=_plan_commitment()
        )

    # And each one alone is enough to refuse a spec that is otherwise complete.
    for mutate in (
        lambda s: s.update(frozen_before_generation=False),
        lambda s: s["blindness_contract"].update(audited_before_the_freeze=False),
        lambda s: s["generator_identity"].update(provider=None),
        lambda s: s["generator_identity"].update(provider_serves_the_model_confirmed=False),
        lambda s: s["generator_identity"].update(model_identity_confirmed_against_the_api=False),
    ):
        spec = _frozen_spec()
        mutate(spec)
        spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_generator_spec(
                spec, root=_root(), plan_commitment_sha256=_plan_commitment()
            )


def test_a_fully_pinned_generator_spec_validates():
    """And the contract must be satisfiable, or it decides nothing."""
    bank.validate_generator_spec(
        _frozen_spec(), root=_root(), plan_commitment_sha256=_plan_commitment()
    )


@pytest.mark.parametrize(
    "mutate",
    [
        # A model identifier whose purpose is to be repointed cannot identify a bank's generator.
        lambda s: s["generator_identity"].update(model="deepseek/deepseek-v4-flash:latest"),
        lambda s: s["generator_identity"].update(model="openrouter/auto"),
        lambda s: s["generator_identity"].update(model="deepseek/deepseek-v4-flash:free"),
        # An unset provider means the host picks the backend.
        lambda s: s["generator_identity"].update(provider=None),
        lambda s: s["generator_identity"].update(provider_serves_the_model_confirmed=False),
        lambda s: s["generator_identity"].update(model_identity_confirmed_against_the_api=False),
        lambda s: s["generator_identity"].update(transport="hermes"),
        # A fallback is a silent substitution by design.
        lambda s: s["routing"].update(allow_fallbacks=True),
        lambda s: s["routing"].update(automatic_routing=True),
        lambda s: s["routing"].update(provider_fallbacks=["Together"]),
        lambda s: s["routing"].update(model_fallbacks=["deepseek/deepseek-v3"]),
        # One physical invocation, and every layer that could produce a second named and disabled.
        lambda s: s["invocation_policy"].update(retries_permitted=True),
        lambda s: s["invocation_policy"].update(qualifying_invocations_permitted=2),
        lambda s: s["invocation_policy"].update(
            second_request_to_correct_the_output_permitted=True
        ),
        lambda s: s["invocation_policy"].update(repair_parsing_permitted=True),
        lambda s: s["invocation_policy"]["retries_disabled_at"].remove("rate_limit_429"),
        lambda s: s["invocation_policy"].update(
            invalid_output_is_the_result_of_the_single_invocation=False
        ),
        # Blindness is audited, not asserted, and every channel is named.
        lambda s: s["blindness_contract"]["absent"].remove("tools"),
        lambda s: s["blindness_contract"]["absent"].remove("rag"),
        lambda s: s["blindness_contract"].update(audited_before_the_freeze=False),
        # A hosted model does not become reproducible by being sent a seed.
        lambda s: s["sampling"].update(determinism_is_claimed=True),
        # The schema is the contract and may not become a sentence.
        lambda s: s["structured_output"].update(mode="prose_instruction"),
        lambda s: s["structured_output"].update(strict=False),
        lambda s: s.update(requested_carrier_count=100),
        # A credential may never enter a published artifact.
        lambda s: s["canonical_request_body"].update(api_key="sk-abcdefghijklmnopqrstuvwxyz"),
        lambda s: s.update(authorization="Bearer sk-abcdefghijklmnopqrstuvwxyz"),
        # Nor may project context enter the generator's sole input.
        lambda s: s["canonical_request_body"]["messages"][0].update(
            content="Emit machines for hypothesis H58 in the mira genesis project."
        ),
        lambda s: s["qualifying_input"].update(sha256="0" * 64),
        lambda s: s["claim_boundary"].update(human_independence=True),
    ],
)
def test_the_generator_spec_refuses_every_shape_that_would_lose_the_identity(mutate):
    from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

    spec = _frozen_spec()
    mutate(spec)
    spec["canonical_request_body_sha256"] = sha256_hex(
        canonical_bytes(spec["canonical_request_body"])
    )
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(
            spec, root=_root(), plan_commitment_sha256=_plan_commitment()
        )


def test_a_spec_written_for_another_plan_is_refused():
    """The spec binds the frozen plan, so it cannot have been written for a different rule set."""
    spec = _frozen_spec()
    spec["analysis_plan_commitment_sha256"] = "0" * 64
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(
            spec, root=_root(), plan_commitment_sha256=_plan_commitment()
        )


def test_the_credential_guard_does_not_fire_on_the_carrier_meta_schema():
    """A guard that refuses the thing it protects gets switched off.

    A carrier's wire surface has an `action_key`, an `argument_key`, a `status_key`, an `ok_token`
    and an `error_token`. An earlier form of this guard matched any key ending in `_key` or
    `_token` and refused the frozen output schema itself.
    """
    schema = json.loads(
        (bank.EXPERIMENT_DIRECTORY / "OUTPUT_SCHEMA.json").read_bytes().decode("utf-8")
    )
    bank._refuse_secret_material(schema)

    surface = schema["properties"]["machines"]["items"]["properties"]["surface"]["properties"]
    assert {"action_key", "argument_key", "status_key", "ok_token", "error_token"} <= set(surface)

    with pytest.raises(bank.CarrierBankError):
        bank._refuse_secret_material({"headers": {"authorization": "Bearer x"}})


def test_the_generator_input_carries_no_project_context():
    """The schema travels to the model inside the request, so its own strings are its input too.

    The schema's `title` was `mira-blind-carrier-v1 emission`, which would have told a blind
    generator the name of the contract it was emitting for. Nothing frozen bound the schema yet,
    so it was repaired rather than recorded.
    """
    from metamorphosis.blind_bank_protocol import contamination_hits

    for name in ("OUTPUT_SCHEMA.json", "GENERATOR_PROMPT.txt", "QUALIFYING_INPUT.txt"):
        text = (bank.EXPERIMENT_DIRECTORY / name).read_bytes().decode("utf-8")
        assert not contamination_hits(text), (name, contamination_hits(text))

    spec = _candidate_spec()
    assert not contamination_hits(
        json.dumps(spec["canonical_request_body"], sort_keys=True)
    )


def test_the_qualifying_input_is_the_prompt_with_the_frozen_count_and_nothing_else():
    template = (bank.EXPERIMENT_DIRECTORY / "GENERATOR_PROMPT.txt").read_bytes().decode("utf-8")
    qualifying = (bank.EXPERIMENT_DIRECTORY / "QUALIFYING_INPUT.txt").read_bytes().decode("utf-8")
    assert qualifying.replace("24", "N", 1) == template
    assert "exactly 24 entries" in qualifying


def test_the_generation_client_refuses_before_it_can_reach_anything():
    """Every gate the client holds is reachable without a network, and each of them is checked."""
    client = _load_script("m113_generation", "run_m113_generation.py")
    import os

    # The credential is read at the moment of use and never stored.
    previous = os.environ.pop(client.SECRET_VARIABLE, None)
    try:
        with pytest.raises(client.GenerationError):
            client._secret()
    finally:
        if previous is not None:
            os.environ[client.SECRET_VARIABLE] = previous

    # A qualifying call requires a frozen spec. Checked against a tree that has none, so the
    # assertion survives this milestone freezing its own.
    import tempfile

    with tempfile.TemporaryDirectory() as empty:
        previous_spec, previous_candidate = client.SPEC_PATH, client.CANDIDATE_SPEC_PATH
        client.SPEC_PATH = Path(empty) / "GENERATOR_SPEC.json"
        client.CANDIDATE_SPEC_PATH = Path(empty) / "GENERATOR_SPEC_CANDIDATE.json"
        try:
            with pytest.raises(client.GenerationError):
                client.load_spec(frozen_required=True)
        finally:
            client.SPEC_PATH, client.CANDIDATE_SPEC_PATH = previous_spec, previous_candidate

    # A smoke test on a spec with no provider chosen is refused.
    with pytest.raises(client.GenerationError):
        client.smoke(_unadopted_spec(), write=False)

    # Not http, and no third-party client whose retry behaviour would have to be disabled.
    source = (
        bank.EXPERIMENT_DIRECTORY.parent.parent / "scripts" / "run_m113_generation.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import httpx", "import openai", "urllib.request"):
        assert forbidden not in source

    # The smoke input can never be the qualifying input.
    qualifying = (bank.EXPERIMENT_DIRECTORY / "QUALIFYING_INPUT.txt").read_bytes().decode("utf-8")
    assert client.SMOKE_INPUT.strip() not in qualifying
    assert "machines" not in client.SMOKE_INPUT


def test_a_second_materialization_against_one_frozen_spec_is_refused(tmp_path, monkeypatch):
    """One frozen spec admits one bank. The second attempt is the retry the contract refuses."""
    client = _load_script("m113_generation_ledger", "run_m113_generation.py")
    ledger = tmp_path / "GENERATION_LEDGER.json"
    ledger.write_text(
        json.dumps({
            "schema": client.LEDGER_SCHEMA,
            "entries": [{
                "attempt_index": 1,
                "spec_commitment_sha256": "a" * 64,
                "started_at": "2026-08-26T00:00:00Z",
                "outcome": "materialized",
                "payload_sha256": "b" * 64,
                "isolation_attestation_sha256": "c" * 64,
                "note": "",
            }],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(client, "LEDGER_PATH", ledger)
    spec = {"spec_commitment_sha256": "a" * 64, "generator_identity": {}, "canonical_request_body": {}}
    with pytest.raises(client.GenerationError):
        client.qualify(spec)


# ------------------------------------ the pre-freeze sequence, as one development pass


def _generation_client():
    return _load_script("m113_generation_prepare", "run_m113_generation.py")


def _discovery_report(*, in_catalogue=True, capable=("Fireworks",)):
    return {
        "schema": "m113-provider-discovery-development-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "milestone": "M113",
        "requested_model": "deepseek/deepseek-v4-flash-0731",
        "model_is_in_the_catalogue": in_catalogue,
        "catalogue_entry": {"id": "deepseek/deepseek-v4-flash-0731"} if in_catalogue else None,
        "providers": [
            {
                "name": name,
                "context_length": 128000,
                "supported_parameters": ["structured_outputs", "temperature"],
                "supports_structured_outputs": True,
                "quantization": None,
                "status": None,
            }
            for name in capable
        ],
        "providers_that_can_serve_the_frozen_request": sorted(capable),
        "observed_at": "2026-08-26T00:00:00Z",
    }


def test_the_provider_rule_adopts_only_when_the_choice_is_mechanical():
    """One capable provider is a fact. Several is a judgement made after seeing the catalogue.

    A judgement made after seeing the data is exactly the shape this milestone exists to keep out
    of the record, so several stops and goes to the owner rather than picking.
    """
    client = _generation_client()

    outcome = client.adopt(_discovery_report(), _unadopted_spec())
    assert outcome["adopted"] is True
    assert outcome["provider"] == "Fireworks"

    for report in (
        _discovery_report(capable=("Fireworks", "Novita")),
        _discovery_report(capable=()),
        _discovery_report(in_catalogue=False),
    ):
        refused = client.adopt(report, _unadopted_spec())
        assert refused["adopted"] is False
        assert refused["reason"]


def test_discovery_can_never_complete_the_freeze():
    """Adoption answers three fields. The other three are not discovery's to answer."""
    client = _generation_client()
    spec = _unadopted_spec()
    before = set(spec["unset_before_freeze"])

    outcome = client.adopt(_discovery_report(), spec)
    assert outcome["adopted"] is True

    remaining = set(spec["unset_before_freeze"])
    assert before - remaining == set(client.DISCOVERY_ANSWERS)
    assert remaining == {
        "blindness_contract.audited_before_the_freeze",
        "frozen_before_generation",
        "sampling.seed_is_honoured_by_the_provider",
    }
    # And the adopted candidate still cannot pass as a frozen spec.
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(
            spec, root=_root(), plan_commitment_sha256=_plan_commitment()
        )


def _stub_transport(client, monkeypatch, *, served_model, served_provider, content):
    """Replace the one function that touches a socket, and count the calls it would have made."""
    calls = []

    def fake_request(url, *, method="POST", body=None, timeout=900):
        calls.append({"url": url, "method": method})
        if method == "GET" and url.endswith("/models"):
            payload = {"data": [{"id": "deepseek/deepseek-v4-flash-0731"}]}
        elif method == "GET":
            payload = {"data": {"endpoints": [{
                "provider_name": "Fireworks",
                "context_length": 128000,
                "supported_parameters": ["structured_outputs", "temperature"],
                "quantization": None,
                "status": None,
            }]}}
        else:
            payload = {
                "id": "gen-stub",
                "model": served_model,
                "provider": served_provider,
                "choices": [{"finish_reason": "stop", "message": {"content": content}}],
                "usage": {"total_tokens": 12},
            }
        return {
            "started_at": "2026-08-26T00:00:00Z",
            "finished_at": "2026-08-26T00:00:01Z",
            "status": 200,
            "response_headers": {"x-request-id": "stub"},
            "response_sha256": "0" * 64,
            "response_bytes": 1,
            "body": payload,
            "raw_text": None,
        }

    monkeypatch.setattr(client, "request", fake_request)
    return calls


def _isolate_paths(client, monkeypatch, tmp_path):
    experiment = tmp_path / "experiments" / "M113"
    experiment.mkdir(parents=True)
    from metamorphosis.blind_bank_protocol import canonical_bytes

    candidate = experiment / "GENERATOR_SPEC_CANDIDATE.json"
    # A pre-freeze candidate, not whatever the milestone has since frozen.
    pristine = _unadopted_spec()
    pristine["spec_commitment_sha256"] = bank.generator_spec_commitment(pristine)
    candidate.write_bytes(canonical_bytes(pristine) + b"\n")
    monkeypatch.setattr(client, "EXPERIMENT", experiment)
    monkeypatch.setattr(client, "CANDIDATE_SPEC_PATH", candidate)
    monkeypatch.setattr(client, "SPEC_PATH", experiment / "GENERATOR_SPEC.json")
    monkeypatch.setattr(client, "DISCOVERY_PATH", experiment / "PROVIDER_DISCOVERY_DEVELOPMENT.json")
    monkeypatch.setattr(client, "SMOKE_PATH", experiment / "TRANSPORT_SMOKE_DEVELOPMENT.json")
    monkeypatch.setattr(client, "BUNDLE_PATH", experiment / "PRE_FREEZE_BUNDLE_DEVELOPMENT.json")
    return experiment


def test_the_pre_freeze_pass_completes_without_consuming_a_gate(tmp_path, monkeypatch):
    """Discover, adopt and smoke in one pass, and nothing qualifying may exist afterwards."""
    client = _generation_client()
    experiment = _isolate_paths(client, monkeypatch, tmp_path)
    calls = _stub_transport(
        client, monkeypatch,
        served_model="deepseek/deepseek-v4-flash-0731",
        served_provider="Fireworks",
        content='{"colours": [{"name": "amber"}, {"name": "slate"}]}',
    )

    code, bundle = client.prepare()
    assert code == 0, bundle.get("stopped_at")
    assert bundle["adoption"]["provider"] == "Fireworks"
    assert bundle["smoke"]["identity_served_matches_identity_requested"] is True
    assert bundle["smoke"]["structured_output_parsed"] is True
    assert bundle["qualifying_invocation_performed"] is False
    assert bundle["retries_performed"] == 0
    assert bundle["ready_for_generator_freeze_review"] is True

    # Three physical requests: two GETs for discovery, one POST for the probe. No fourth.
    assert len(calls) == 3
    assert [c["method"] for c in calls] == ["GET", "GET", "POST"]
    assert bundle["physical_requests"]["qualifying"] == 0

    assert bundle["post_conditions"]["phase"] == "draft"
    assert bundle["post_conditions"]["revealed"] is False
    assert not any(bundle["post_conditions"]["artifacts_that_must_not_exist"].values())
    assert not (experiment / "GENERATION_LEDGER.json").exists()
    assert not (experiment / "SEALED_BANK.json.gpg").exists()


def test_the_pre_freeze_pass_stops_when_the_served_identity_is_not_the_requested_one(
    tmp_path, monkeypatch
):
    """Fallbacks and routing are disabled precisely so this cannot pass unnoticed."""
    client = _generation_client()
    _isolate_paths(client, monkeypatch, tmp_path)
    _stub_transport(
        client, monkeypatch,
        served_model="deepseek/deepseek-v3",
        served_provider="Fireworks",
        content='{"colours": [{"name": "amber"}, {"name": "slate"}]}',
    )

    code, bundle = client.prepare()
    assert code == 3
    assert "served identity" in bundle["stopped_at"]
    assert bundle.get("ready_for_generator_freeze_review") is None


def test_the_pre_freeze_pass_stops_when_strict_decoding_did_not_hold(tmp_path, monkeypatch):
    client = _generation_client()
    _isolate_paths(client, monkeypatch, tmp_path)
    _stub_transport(
        client, monkeypatch,
        served_model="deepseek/deepseek-v4-flash-0731",
        served_provider="Fireworks",
        content="here are two colours: amber and slate",
    )

    code, bundle = client.prepare()
    assert code == 4
    assert "structured output" in bundle["stopped_at"]


def test_the_pre_freeze_pass_refuses_to_report_success_if_it_created_qualifying_state(
    tmp_path, monkeypatch
):
    """The post-conditions are checked, not assumed, and a development pass that produced a
    qualifying artifact is an instrument fault the operator must see before any freeze."""
    client = _generation_client()
    experiment = _isolate_paths(client, monkeypatch, tmp_path)
    _stub_transport(
        client, monkeypatch,
        served_model="deepseek/deepseek-v4-flash-0731",
        served_provider="Fireworks",
        content='{"colours": [{"name": "amber"}, {"name": "slate"}]}',
    )
    (experiment / "GENERATION_LEDGER.json").write_text("{}", encoding="utf-8")

    code, bundle = client.prepare()
    assert code == 5
    assert bundle["unexpectedly_created"] == ["GENERATION_LEDGER.json"]


# ------------------------------- the transport, and the difference between silence and denial


def test_the_generation_client_tunnels_through_the_environment_proxy(monkeypatch):
    """Written with no reachable endpoint, this client opened a direct connection.

    The first live call came back 403 `host_not_allowed` from an interception point that had never
    seen the allowlist. Every other tool in this environment goes through `HTTPS_PROXY`, and so
    must this one -- one plaintext CONNECT to the proxy, then TLS to the target through it, which
    is still one physical connection carrying one request.
    """
    client = _generation_client()
    seen = {}

    class FakeConnection:
        def __init__(self, host, port, timeout=None, context=None):
            seen["connected_to"] = (host, port)

        def set_tunnel(self, host, port):
            seen["tunnelled_to"] = (host, port)

        def request(self, method, path, body=None, headers=None):
            seen["headers"] = headers

        def getresponse(self):
            class R:
                status = 200

                def read(self):
                    return b'{"ok": true}'

                def getheaders(self):
                    return [("x-request-id", "stub")]

            return R()

        def close(self):
            pass

    monkeypatch.setattr(client.http.client, "HTTPSConnection", FakeConnection)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-a-real-credential")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:34229")

    client.request("https://openrouter.ai/api/v1/models", method="GET", body=None, timeout=5)
    assert seen["connected_to"] == ("127.0.0.1", 34229)
    assert seen["tunnelled_to"] == ("openrouter.ai", 443)

    # Without a proxy configured it connects straight to the target, unchanged.
    seen.clear()
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)
    client.request("https://openrouter.ai/api/v1/models", method="GET", body=None, timeout=5)
    assert seen["connected_to"] == ("openrouter.ai", 443)
    assert "tunnelled_to" not in seen


def test_a_denied_request_is_never_reported_as_a_fact_about_the_catalogue():
    """The dangerous defect, and the reason it is dangerous.

    The first live discovery was denied by the egress proxy. The body was unparseable, so the
    entry list was empty, so the report said `model_is_in_the_catalogue: false` -- a conclusion
    about DeepSeek's availability manufactured out of a network denial. Acting on it would have
    meant hunting for a substitute for a model that was there all along, and substituting the
    generator is the one thing the frozen contract exists to prevent.
    """
    client = _generation_client()

    def denied(url, *, method="POST", body=None, timeout=900):
        return {
            "started_at": "2026-08-27T00:00:00Z",
            "finished_at": "2026-08-27T00:00:01Z",
            "status": 403,
            "response_headers": {"x-deny-reason": "host_not_allowed"},
            "response_sha256": "0" * 64,
            "response_bytes": 100,
            "body": None,
            "raw_text": "Host not in allowlist: openrouter.ai.",
        }

    original = client.request
    client.request = denied
    try:
        with pytest.raises(client.GenerationError) as denial:
            client.discover(_candidate_spec(), write=False)
        assert "instrument failure" in str(denial.value)
        assert "not a finding about the catalogue" in str(denial.value)

        spec = _unadopted_spec()
        spec["generator_identity"]["provider"] = "Fireworks"
        with pytest.raises(client.GenerationError) as probe:
            client.smoke(spec, write=False)
        assert "not a finding about the provider" in str(probe.value)
    finally:
        client.request = original


# ------------------------------------- the provider criterion, and what quantization can claim


def _adopted_spec() -> dict:
    """The candidate as it stands once a provider has been selected and recorded."""
    return _candidate_spec()


def test_the_recorded_criterion_must_actually_select_the_pinned_provider():
    """A criterion that does not name the provider the spec pins is decoration."""
    spec = _frozen_spec()
    assert spec["provider_selection"]["selected"] == spec["generator_identity"]["provider"]

    from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

    for mutate in (
        lambda s: s["provider_selection"].update(selected="Together"),
        lambda s: s["provider_selection"].update(candidates_considered=["Together"]),
        lambda s: s["provider_selection"].update(criterion="   "),
        lambda s: s["provider_selection"].pop("criterion"),
        lambda s: s.pop("provider_selection"),
    ):
        broken = json.loads(json.dumps(spec))
        mutate(broken)
        broken["spec_commitment_sha256"] = bank.generator_spec_commitment(broken)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_generator_spec(broken, root=_root())


def test_a_criterion_that_could_have_been_informed_by_the_result_is_refused():
    """The whole point of recording when a criterion was formed.

    A provider chosen for what it does to the hypothesis is not a criterion, it is an outcome
    being selected for. And a criterion formed after the freeze, or after the bank, is one the
    record cannot distinguish from that.
    """
    spec = _frozen_spec()
    for key in (
        "formulated_before_any_bank_existed",
        "formulated_before_generator_freeze",
        "formulated_before_smoke_with_the_final_identity",
        "formulated_before_the_qualifying_invocation",
    ):
        broken = json.loads(json.dumps(spec))
        broken["provider_selection"][key] = False
        broken["spec_commitment_sha256"] = bank.generator_spec_commitment(broken)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_generator_spec(broken, root=_root())

    depends = json.loads(json.dumps(spec))
    depends["provider_selection"]["depends_on_any_h58_result"] = True
    depends["spec_commitment_sha256"] = bank.generator_spec_commitment(depends)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(depends, root=_root())

    # Whether the catalogue had been seen must be recorded either way. Silence on it is the part
    # a reader cannot check, so it is refused rather than defaulted.
    silent = json.loads(json.dumps(spec))
    silent["provider_selection"].pop("formulated_after_observing_the_provider_catalogue")
    silent["spec_commitment_sha256"] = bank.generator_spec_commitment(silent)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(silent, root=_root())

    # Recording it as true is permitted: this project's criterion was formed after discovery ran,
    # and says so.
    honest = json.loads(json.dumps(spec))
    honest["provider_selection"]["formulated_after_observing_the_provider_catalogue"] = True
    honest["spec_commitment_sha256"] = bank.generator_spec_commitment(honest)
    bank.validate_generator_spec(honest, root=_root())


def test_quantization_is_pinned_as_discovery_bound_and_never_as_attested():
    """The nearest thing a hosted generator has to M112's weight digest, and its exact limit.

    OpenRouter reports quantization in the provider catalogue and not in the completion response.
    It can be pinned from discovery; it cannot be re-verified from the served answer. A spec that
    recorded it as attested at serve time would be claiming more than the instrument supports.
    """
    spec = _frozen_spec()
    assert spec["generator_identity"]["quantization_source"] == "provider_discovery_catalogue"
    assert spec["generator_identity"]["quantization_is_runtime_attested"] is False

    for mutate in (
        lambda s: s["generator_identity"].update(quantization_is_runtime_attested=True),
        lambda s: s["generator_identity"].update(quantization_source="completion_response"),
        lambda s: s["generator_identity"].update(quantization=""),
        lambda s: s["generator_identity"].pop("quantization"),
    ):
        broken = json.loads(json.dumps(spec))
        mutate(broken)
        broken["spec_commitment_sha256"] = bank.generator_spec_commitment(broken)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_generator_spec(broken, root=_root())


def test_an_unmeasured_seed_guarantee_is_recorded_as_unknown_and_never_as_a_boolean():
    """Three states, and the third is the honest one for a hosted provider.

    A provider may list `seed` among its supported parameters -- so the value is accepted rather
    than dropped -- while promising nothing about whether the same seed returns the same
    completion. `false` would assert the seed is ignored, a measurement nobody made; `true` would
    claim reproducibility the provider does not offer. What stays refused is silence.
    """
    from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

    for value in (True, False, "unknown"):
        spec = _frozen_spec()
        spec["sampling"]["seed_is_honoured_by_the_provider"] = value
        spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
        bank.validate_generator_spec(spec, root=_root())

    for value in (None, "probably", 1):
        spec = _frozen_spec()
        spec["sampling"]["seed_is_honoured_by_the_provider"] = value
        spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
        with pytest.raises(bank.CarrierBankError):
            bank.validate_generator_spec(spec, root=_root())

    # Silence is refused, and so is a determinism claim under any of the three.
    silent = _frozen_spec()
    silent["sampling"].pop("seed_is_honoured_by_the_provider")
    silent["spec_commitment_sha256"] = bank.generator_spec_commitment(silent)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(silent, root=_root())

    claimed = _frozen_spec()
    claimed["sampling"]["seed_is_honoured_by_the_provider"] = "unknown"
    claimed["sampling"]["determinism_is_claimed"] = True
    claimed["spec_commitment_sha256"] = bank.generator_spec_commitment(claimed)
    with pytest.raises(bank.CarrierBankError):
        bank.validate_generator_spec(claimed, root=_root())


def test_the_pre_freeze_pass_refuses_to_run_against_a_frozen_instrument(tmp_path, monkeypatch):
    """The freeze is the point after which the instrument stops being choosable.

    Re-running the pre-freeze pass afterwards would re-adopt a provider and rewrite the candidate
    underneath a spec the record has already committed to.
    """
    client = _generation_client()
    experiment = _isolate_paths(client, monkeypatch, tmp_path)
    frozen = experiment / "GENERATOR_SPEC.json"
    monkeypatch.setattr(client, "SPEC_PATH", frozen)
    frozen.write_text("{}", encoding="utf-8")

    with pytest.raises(client.GenerationError) as refusal:
        client.prepare()
    assert "already frozen" in str(refusal.value)


# ------------------------------------ what a failed qualifying attempt must leave behind


def test_a_failed_attempt_is_recorded_in_the_contract_s_own_vocabulary(tmp_path, monkeypatch):
    """The client wrote an outcome the shared contract does not admit, and only the phase machine
    reading the record back discovered it.

    `LEDGER_OUTCOMES` is closed: materialized, failed_structural_validation, failed_isolation,
    aborted. An attempt that ended before any payload existed is none of the middle two, because
    neither stage was reached, so it is `aborted`. A record written in a private vocabulary is
    unreadable by the contract that governs it, which is the same as not having been written.
    """
    from metamorphosis.blind_bank_protocol import LEDGER_OUTCOMES, validate_generation_ledger

    client = _generation_client()
    experiment = _isolate_paths(client, monkeypatch, tmp_path)
    ledger = experiment / "GENERATION_LEDGER.json"
    monkeypatch.setattr(client, "LEDGER_PATH", ledger)
    monkeypatch.setattr(client, "FAILED_ATTEMPT_PATH", experiment / "GENERATION_FAILED_ATTEMPT.json")

    spec = _frozen_spec()

    def denied(url, *, method="POST", body=None, timeout=900):
        return {
            "started_at": "2026-08-27T07:27:49Z",
            "finished_at": "2026-08-27T07:27:50Z",
            "status": 429,
            "response_headers": {"server": "cloudflare"},
            "response_sha256": "0" * 64,
            "response_bytes": 220,
            "body": {"error": {"code": 429, "message": "Provider returned error"}},
            "raw_text": None,
        }

    monkeypatch.setattr(client, "request", denied)
    assert client.qualify(spec) == 1

    recorded = json.loads(ledger.read_text(encoding="utf-8"))
    entry = recorded["entries"][0]
    assert entry["outcome"] in LEDGER_OUTCOMES
    assert entry["outcome"] == "aborted"
    assert entry["payload_sha256"] is None
    # Well-formed, and still refusing to authorize a bank the attempt did not produce.
    with pytest.raises(Exception) as refusal:
        validate_generation_ledger(
            recorded, spec_commitment_sha256=spec["spec_commitment_sha256"]
        )
    assert "materialized 0 banks" in str(refusal.value)


def test_a_failed_attempt_preserves_what_it_observed(tmp_path, monkeypatch):
    """A failed attempt's record is the evidence of an instrument failure.

    An earlier form of this wrote only the status code, so the body explaining why was lost at
    exactly the moment it mattered most -- and the first real qualifying invocation was the one
    that lost it.
    """
    client = _generation_client()
    experiment = _isolate_paths(client, monkeypatch, tmp_path)
    failed = experiment / "GENERATION_FAILED_ATTEMPT.json"
    monkeypatch.setattr(client, "LEDGER_PATH", experiment / "GENERATION_LEDGER.json")
    monkeypatch.setattr(client, "FAILED_ATTEMPT_PATH", failed)

    detail = {"error": {"code": 429, "metadata": {"provider_name": "Morph",
                                                 "limit_source": "upstream_provider_shared_pool"}}}

    def denied(url, *, method="POST", body=None, timeout=900):
        return {
            "started_at": "2026-08-27T07:27:49Z",
            "finished_at": "2026-08-27T07:27:50Z",
            "status": 429,
            "response_headers": {"server": "cloudflare", "x-request-id": "abc"},
            "response_sha256": "1" * 64,
            "response_bytes": 220,
            "body": detail,
            "raw_text": None,
        }

    monkeypatch.setattr(client, "request", denied)
    assert client.qualify(_frozen_spec()) == 1

    preserved = json.loads(failed.read_text(encoding="utf-8"))
    assert preserved["status"] == 429
    assert preserved["body"] == detail
    assert preserved["response_headers"]["x-request-id"] == "abc"
    assert preserved["this_is_an_instrument_failure_not_a_hypothesis_result"] is True
    # And no bank, no result, came out of it.
    assert not (experiment / "GENERATION_RESPONSE.json").exists()
    assert not (experiment / "RESULT.json").exists()
