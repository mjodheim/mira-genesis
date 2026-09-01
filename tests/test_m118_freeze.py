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


def test_the_control_construction_is_named_not_left_implicit():
    """An auditor should find the comparison in the plan, not infer it from an import closure."""
    control = freeze.analysis_plan(freeze.inherited_digests())["control_construction"]
    assert control["arms_rule"] == "scripts/run_m113_qualification.py::ARM_NAMES"
    assert "T0" in control["arms"] and "budget_plus" in control["arms"]
    assert control["only_the_genesis_state_differs_across_arms"] is True
    assert control["arms_restored_from_frozen_producer_bytes_never_reimplemented"] is True
    assert control["inherited_unchanged"] is True


def test_the_arm_names_are_read_from_the_runner_not_restated():
    from scripts import run_m113_qualification as qualification
    control = freeze.analysis_plan(freeze.inherited_digests())["control_construction"]
    assert control["arms"] == list(qualification.ARM_NAMES)


def test_the_control_path_is_bound_by_the_tested_system_freeze():
    from metamorphosis import m118_chronology as chronology
    for module in ("scripts/run_m113_qualification.py", "scripts/check_m113_result.py",
                   "metamorphosis/m113_evaluator.py"):
        assert module in chronology.TESTED_SYSTEM_PATHS, module


def test_budget_is_separable_from_capability():
    """Without the budget_plus arm, 'could not' and 'could not afford to' are indistinguishable."""
    control = freeze.analysis_plan(freeze.inherited_digests())["control_construction"]
    assert "budget_plus" in control["arms"]
    assert "could not afford" in control["budget_separated_from_capability_by"]
