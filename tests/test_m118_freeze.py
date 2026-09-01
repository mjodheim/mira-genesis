"""The H63 apparatus inherits M115's science byte-for-byte and changes only the instrument."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m118_route as fixed
from scripts import build_m118_freeze as freeze

ROOT = Path(__file__).resolve().parents[1]
M115 = ROOT / "experiments" / "M115"


def test_the_scientific_artifacts_are_m115s_unchanged():
    digests = freeze.inherited_digests()
    spec = json.loads((M115 / "GENERATOR_SPEC.json").read_text(encoding="utf-8"))
    assert digests["OUTPUT_SCHEMA.json"] == spec["output_schema"]["sha256"]
    assert digests["GENERATOR_PROMPT.txt"] == spec["prompt"]["sha256"]


def test_a_tampered_inherited_artifact_is_refused(tmp_path, monkeypatch):
    fake = tmp_path / "M115"
    fake.mkdir()
    for name in freeze.INHERITED_VERBATIM + ("GENERATOR_SPEC.json",):
        (fake / name).write_bytes((M115 / name).read_bytes())
    (fake / "OUTPUT_SCHEMA.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(freeze, "M115", fake)
    with pytest.raises(freeze.FreezeError, match="does not match the digest"):
        freeze.inherited_digests()


def test_no_scientific_rule_changed():
    digests = freeze.inherited_digests()
    plan = freeze.analysis_plan(digests)
    spec = freeze.generator_spec(
        plan, digests, (M115 / "QUALIFYING_INPUT.txt").read_text(encoding="utf-8"))
    assert spec["instrumental_delta_from_m115"]["scientific_rules_changed"] == []
    assert plan["predicates_versioned_for_this_milestone"] == []
    assert plan["predicates_newly_versioned_for_this_milestone"] == []


def test_the_thresholds_are_m115s():
    inherited = json.loads((M115 / "ANALYSIS_PLAN.json").read_text(encoding="utf-8"))
    plan = freeze.analysis_plan(freeze.inherited_digests())
    for key in ("minimum_qualifying_carriers", "minimum_distinct_qualifying_structures",
                "requested_carrier_count", "insufficient_bank_verdict",
                "max_bank_materializations", "retries_permitted",
                "selection_among_carriers_permitted", "closure_rule",
                "demand_derivation_rule", "qualification_rule", "scoring_rule"):
        assert plan[key] == inherited[key], key


def test_the_proposition_is_unchanged_and_the_number_is_procedural():
    plan = freeze.analysis_plan(freeze.inherited_digests())
    assert plan["states_the_same_scientific_proposition_as"] == ["H60", "H61", "H62"]
    assert plan["new_hypothesis_number_is_procedural_not_scientific"] is True


def test_the_request_body_carries_the_fixed_route_and_no_fallback():
    body = freeze.canonical_request_body("input")
    assert body["model"] == fixed.REQUESTED_MODEL
    assert body["provider"]["only"] == [fixed.PROVIDER]
    assert body["provider"]["allow_fallbacks"] is False
    assert body["max_tokens"] == freeze.MAX_TOKENS
    assert body["reasoning"] == {"effort": freeze.REASONING_EFFORT}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["seed"] == 0 and body["stream"] is False and body["temperature"] == 1.0


def test_the_request_body_carries_the_qualifying_input_as_the_sole_message():
    body = freeze.canonical_request_body("THE-INPUT")
    assert len(body["messages"]) == 1
    assert body["messages"][0] == {"role": "user", "content": "THE-INPUT"}


def test_the_plan_records_that_the_route_predates_any_h63_observation():
    plan = freeze.analysis_plan(freeze.inherited_digests())
    assert plan["route_fixed_before_any_h63_observation"] is True
    assert plan["route_selected_using_an_h63_carrier_outcome"] is False
    assert plan["provider_substitution_permitted"] is False
    assert plan["readiness_may_not_alter_the_proposition_schema_or_thresholds"] is True


def test_the_nonce_is_drawn_before_any_completion_and_committed_by_digest():
    import hashlib
    record = freeze.nonce_commitment()
    assert record["drawn_before_any_completion_existed"] is True
    assert record["bank_nonce_sha256"] == hashlib.sha256(
        record["bank_nonce"].encode("ascii")).hexdigest()
    assert len(record["bank_nonce"]) == 64
    assert freeze.nonce_commitment()["bank_nonce"] != record["bank_nonce"]


def test_the_claim_boundary_is_inherited_intact():
    plan = freeze.analysis_plan(freeze.inherited_digests())
    boundary = plan["claim_boundary"]
    assert boundary["agi"] is False
    assert boundary["advances_any_generality_gate"] is False
    assert boundary["closes_g1"] is False and boundary["closes_g4"] is False


def test_the_control_construction_names_the_m118_arms_not_m113s():
    """An earlier draft froze M113's nine arms, P22 and the withdrawn symmetry claim."""
    control = freeze.analysis_plan(freeze.inherited_digests())["control_construction"]
    from metamorphosis import m118_arms as arms
    assert control["arms_rule"] == "metamorphosis/m118_arms.py::ARM_NAMES"
    assert control["arms"] == list(arms.ARM_NAMES)
    assert control["primary_fresh_comparator"] == arms.PRIMARY_FRESH_ARM
    assert control["legacy_arm_is_a_constant_function"] is True
    assert control["factorial_cells"]["rules_absent_policy_present"] == "probe_only"


def test_the_frozen_plan_carries_no_replaced_or_withdrawn_claim():
    import json
    text = json.dumps(freeze.analysis_plan(freeze.inherited_digests()))
    assert "P22 (strictly better" not in text
    assert '"only_the_genesis_state_differs_across_arms": true' not in text.lower()


def test_the_frozen_plan_states_the_decision_rule():
    from metamorphosis import m118_endpoint as endpoint
    plan = freeze.analysis_plan(freeze.inherited_digests())
    measurement = plan["measurement"]
    assert measurement["primary_test"]["alpha"] == endpoint.ALPHA
    assert measurement["primary_test"]["minimum_risk_difference"] == \
        endpoint.MINIMUM_RISK_DIFFERENCE
    assert measurement["no_harm_guards"] == dict(endpoint.NO_HARM_GUARDS)
    assert measurement["dominance_guards"]["descendant_must_be_at_least"] == ["T0", "M2"]
    assert measurement["p22_is_not_carried_into_h63"] is True
    assert measurement["primary_test"]["underpowered_is_inconclusive_not_negative"] is True


def test_the_frozen_plan_records_the_comparator_and_its_seed():
    from metamorphosis import m118_arms as arms
    construction = freeze.analysis_plan(
        freeze.inherited_digests())["control_construction"]["comparator_construction"]
    assert construction["seed"] == arms.FRESH_UNIFORM_SEED
    assert construction["seed_permutes_rows_and_component_order"] is True
    assert construction["carries_no_acquired_rule"] is True
    assert construction["consults_no_carrier_semantics"] is True
    assert construction["balanced_assignment_space_size"] == len(arms.achievable_assignments())


def test_feasibility_actually_gates_the_freeze():
    """Its docstring claimed the plan refuses an unreachable criterion; nothing called it."""
    plan = freeze.analysis_plan(freeze.inherited_digests())
    assert plan["feasibility"]["criterion_can_pass_on_the_minimum_bank"] is True
    assert plan["feasibility"]["minimum_paired_demands"] == \
        plan["minimum_qualifying_carriers"] * freeze.DEMANDS_PER_CARRIER


def test_an_unreachable_criterion_refuses_to_freeze(monkeypatch):
    from metamorphosis import m118_endpoint as endpoint
    monkeypatch.setattr(freeze, "DEMANDS_PER_CARRIER", 1)
    monkeypatch.setattr(endpoint, "MINIMUM_RISK_DIFFERENCE", 0.10)
    with pytest.raises(endpoint.EndpointError, match="guaranteed negative"):
        freeze.analysis_plan(freeze.inherited_digests())


def test_the_control_path_is_bound_by_the_tested_system_freeze():
    from metamorphosis import m118_chronology as chronology
    for module in ("scripts/run_m113_qualification.py", "scripts/check_m113_result.py",
                   "metamorphosis/m113_evaluator.py", "metamorphosis/m118_arms.py",
                   "metamorphosis/m118_endpoint.py", "scripts/run_m118_qualification.py",
                   "scripts/check_m118_result.py"):
        assert module in chronology.TESTED_SYSTEM_PATHS, module
