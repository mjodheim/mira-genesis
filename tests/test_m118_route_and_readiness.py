"""The H63 route is fixed before any H63 observation, and the readiness gate cannot select.

M118 exists because M117's route selection was not prospectively clean: five apparatus revisions
occurred inside it and some followed real endpoint observations. M118 inherits a route, not that
history, and fixes it in code before H63 observes anything.

These tests hold that boundary: one route with no substitution path, a readiness gate that answers
only whether the fixed route still works, and thresholds inherited from calibration rather than
invented here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m117_route_qualification as rule
from metamorphosis import m118_route as fixed
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from scripts import audit_m118_readiness as readiness

ROOT = Path(__file__).resolve().parents[1]
M117 = ROOT / "experiments" / "M117"
M118 = ROOT / "experiments" / "M118"


def _metadata(**overrides):
    base = {"strategy": "direct", "attempt": 1,
            "endpoints": {"available": [
                {"model": fixed.CANONICAL_CHECKPOINT, "provider": fixed.PROVIDER,
                 "selected": True}]}}
    base.update(overrides)
    return base


def _body(**overrides):
    base = {"model": fixed.REQUESTED_MODEL, "provider": fixed.PROVIDER,
            "openrouter_metadata": _metadata()}
    base.update(overrides)
    return base


# -------------------------------------------------------------------------------------------
# One route, fixed, with no substitution path
# -------------------------------------------------------------------------------------------

def test_the_route_is_the_one_m117_calibration_selected():
    selection = json.loads(
        (M117 / "STAGE1_ROUTE_QUALIFICATION.json").read_text(encoding="utf-8"))["selection"]
    assert fixed.REQUESTED_MODEL == selection["selected"]["model"]
    assert fixed.PROVIDER == selection["selected"]["provider"]
    assert fixed.CANONICAL_CHECKPOINT == selection["selected"]["canonical_checkpoint"]


def test_the_route_module_names_no_other_provider_or_model():
    """A second route in the module is a substitution waiting to happen."""
    source = (ROOT / "metamorphosis" / "m118_route.py").read_text(encoding="utf-8")
    for foreign in ("Alibaba", "Google AI Studio", "CoreWeave", "Cerebras", "Baidu",
                    "AtlasCloud", "gemini", "granite", "gemma", "llama"):
        assert foreign not in source, foreign


def test_substitution_is_refused_not_merely_undocumented():
    with pytest.raises(fixed.RouteError, match="does not substitute"):
        fixed.assert_is_the_fixed_route("deepseek/deepseek-v4-pro", fixed.PROVIDER)
    with pytest.raises(fixed.RouteError, match="does not substitute"):
        fixed.assert_is_the_fixed_route(fixed.REQUESTED_MODEL, "Alibaba")


def test_every_request_forbids_fallback():
    block = fixed.provider_block()
    assert block["only"] == [fixed.PROVIDER]
    assert block["allow_fallbacks"] is False
    assert block["require_parameters"] is True
    assert fixed.route()["provider_substitution_permitted"] is False
    assert fixed.route()["second_route_exists"] is False


def test_the_calibration_provenance_travels_with_the_route():
    p = fixed.CALIBRATION_PROVENANCE
    assert p["milestone"] == "M117"
    assert p["phase"] == "DEVELOPMENT calibration"
    assert p["selection_used_any_h63_observation"] is False
    assert p["h63_carrier_existed_at_selection"] is False
    assert p["m117_route_selection_claimed_prospective"] is False
    assert p["m117_disclosed_five_apparatus_revisions"] is True


def test_the_recorded_provenance_matches_the_m117_artifacts():
    """Provenance asserted in code must agree with the record it cites."""
    report = json.loads(
        (M117 / "STAGE1_ROUTE_QUALIFICATION.json").read_text(encoding="utf-8"))
    p = fixed.CALIBRATION_PROVENANCE
    assert p["plan_sha256"] == report["plan_sha256"]
    assert p["universe_sha256"] == report["universe_sha256"]
    assert p["candidates_probed"] == report["candidates_probed"]
    assert p["requests_spent"] == report["requests_spent"]
    assert p["selected_at_order"] == report["selection"]["selected"]["order"]


# -------------------------------------------------------------------------------------------
# Identity: the response must come from exactly this route
# -------------------------------------------------------------------------------------------

def test_a_clean_direct_response_from_the_fixed_route_holds():
    verdict = fixed.identity_holds(_body())
    assert verdict["holds"] is True
    assert verdict["failed_checks"] == []


@pytest.mark.parametrize("body,clause", [
    ({"model": "other/model"}, "served_model_exact"),
    ({"provider": "Alibaba"}, "served_provider_exact"),
])
def test_a_response_from_elsewhere_fails(body, clause):
    verdict = fixed.identity_holds(_body(**body))
    assert verdict["holds"] is False
    assert clause in verdict["failed_checks"]


def test_a_substituted_checkpoint_fails():
    body = _body(openrouter_metadata=_metadata(endpoints={"available": [
        {"model": "deepseek/deepseek-v4-flash-20250101", "selected": True}]}))
    verdict = fixed.identity_holds(body)
    assert verdict["holds"] is False
    assert "canonical_checkpoint_exact" in verdict["failed_checks"]


@pytest.mark.parametrize("override,clause", [
    ({"strategy": "fallback"}, "direct_strategy"),
    ({"attempt": 2}, "one_router_attempt"),
])
def test_a_non_direct_or_retried_route_fails(override, clause):
    verdict = fixed.identity_holds(_body(openrouter_metadata=_metadata(**override)))
    assert verdict["holds"] is False
    assert clause in verdict["failed_checks"]


def test_a_reported_failed_attempt_is_not_a_clean_single_attempt():
    body = _body(openrouter_metadata=_metadata(attempts=[{"status": 503}]))
    assert fixed.identity_holds(body)["holds"] is False


def test_a_reported_pipeline_intervention_fails():
    body = _body(openrouter_metadata=_metadata(pipeline=[{"type": "moderation"}]))
    verdict = fixed.identity_holds(body)
    assert verdict["holds"] is False
    assert "no_pipeline_intervention" in verdict["failed_checks"]


def test_no_metadata_fails_closed():
    assert fixed.identity_holds({})["holds"] is False
    assert fixed.identity_holds(None)["holds"] is False


def test_observation_flags_are_not_criteria():
    verdict = fixed.identity_holds(_body())
    assert "observed_attempts_reported" not in verdict["checks"]
    assert verdict["observed_attempts_reported"] is False


# -------------------------------------------------------------------------------------------
# The readiness gate answers one question and cannot select
# -------------------------------------------------------------------------------------------

def test_the_gate_selects_nothing_and_is_not_evidence():
    frozen = readiness.plan()
    assert frozen["selects_among_providers"] is False
    assert frozen["compares_carrier_quality"] is False
    assert frozen["uses_the_h63_qualifying_input"] is False
    assert frozen["is_a_qualifying_call"] is False
    assert frozen["qualifying_input_was_sent"] is False
    assert frozen["is_evidence_for_h63"] is False
    assert frozen["can_advance_a_generality_gate"] is False
    assert frozen["development"] is True


def test_the_plan_is_self_describing_and_digest_bound():
    frozen = readiness.plan()
    assert frozen["plan_sha256"] == sha256_hex(canonical_bytes(
        {k: v for k, v in frozen.items() if k != "plan_sha256"}))


def test_the_gate_targets_exactly_the_fixed_route():
    route = readiness.plan()["route"]
    assert route["requested_model"] == fixed.REQUESTED_MODEL
    assert route["provider"] == fixed.PROVIDER
    assert route["canonical_checkpoint"] == fixed.CANONICAL_CHECKPOINT
    assert route["allow_fallbacks"] is False


def test_every_request_the_gate_builds_carries_the_fixed_route_and_no_fallback():
    body = readiness._request_body("prompt", {"type": "object"}, "n", 1024)
    assert body["model"] == fixed.REQUESTED_MODEL
    assert body["provider"]["only"] == [fixed.PROVIDER]
    assert body["provider"]["allow_fallbacks"] is False
    assert body["reasoning"] == {"effort": readiness.REASONING_EFFORT}
    assert body["response_format"]["json_schema"]["strict"] is True


# -------------------------------------------------------------------------------------------
# Thresholds are inherited from calibration, not invented here
# -------------------------------------------------------------------------------------------

def test_the_thresholds_are_the_calibrated_ones():
    assert readiness.STRESS_MIN_COMPLETION_TOKENS == 32000
    assert readiness.PROBE_MAX_TOKENS == 131072
    assert readiness.STRESS_MAX_TOKENS == 131072
    assert readiness.STRESS_MIN_COMPLETION_TOKENS == \
        __import__("scripts.audit_m117_route_qualification", fromlist=["x"]) \
        .STRESS_MIN_COMPLETION_TOKENS


def test_the_stress_bar_is_reachable_by_the_route_it_gates():
    """A bar above what the route declares would be unpassable by construction."""
    universe = json.loads((M117 / "STAGE1_CANDIDATE_UNIVERSE.json").read_text(encoding="utf-8"))
    order = json.loads((M117 / "STAGE1_ROUTE_QUALIFICATION.json")
                       .read_text(encoding="utf-8"))["selection"]["selected"]["order"]
    candidate = next(c for c in universe["ordered_candidates"] if c["order"] == order)
    assert candidate["max_completion_tokens"] > readiness.STRESS_MIN_COMPLETION_TOKENS
    assert readiness.STRESS_MIN_COMPLETION_TOKENS < rule.MINIMUM_MAX_COMPLETION_TOKENS


def test_the_reasoning_requirement_matches_what_calibration_observed():
    """0 reasoning tokens was observed on every calibration probe for this route."""
    ledger = json.loads(
        (M117 / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    order = json.loads((M117 / "STAGE1_ROUTE_QUALIFICATION.json")
                       .read_text(encoding="utf-8"))["selection"]["selected"]["order"]
    profile = next(p for p in ledger["profiles"] if p.get("order") == order)
    assert profile["reasoning_control_applied"] is True
    assert all(o["reasoning_tokens"] == 0 for o in profile["observations"])
    assert readiness.MAX_REASONING_TOKENS == 0


# -------------------------------------------------------------------------------------------
# Retry and coverage
# -------------------------------------------------------------------------------------------

def test_only_the_inherited_pre_generation_retry_survives():
    retry = readiness.plan()["retry"]
    assert retry["permitted_only_for"] == ["pre_generation_429"]
    assert retry["content_dependent_redraw_permitted"] is False
    assert retry["repair_permitted"] is False
    assert retry["resend_of_a_materialized_observation_permitted"] is False


def test_every_census_required_keyword_reaches_at_least_one_probe():
    coverage = readiness.feature_coverage()
    assert coverage["required_keywords_reaching_no_probe"] == []
    assert len(coverage["required_by_census"]) == 11
    assert len(coverage["probes_with_their_own_named_class"]) == 9
    assert coverage["exercised_by"]["items"]
    assert coverage["exercised_by"]["maximum"]


def test_the_classifier_names_every_way_the_gate_can_fail():
    outcomes = readiness.plan()["result_classifier"]
    joined = " ".join(outcomes)
    for expected in ("ready:", "not_ready_identity", "not_ready_features",
                     "not_ready_stress", "not_ready_reasoning", "not_ready_transport"):
        assert expected in joined


def test_the_failure_rule_forbids_every_escape_hatch():
    rule_text = readiness.plan()["failure_rule"]
    for forbidden in ("change provider", "change model", "weaken the stress",
                      "remove a schema requirement", "rerun until it passes",
                      "create a carrier bank"):
        assert forbidden in rule_text


# -------------------------------------------------------------------------------------------
# H63 has observed nothing
# -------------------------------------------------------------------------------------------

def test_no_h63_scientific_artifact_exists():
    for absent in ("ANALYSIS_PLAN.json", "GENERATOR_SPEC.json", "SEALED_BANK.json.gpg",
                   "RESULT.json", "CARRIER_BANK.json", "DELIVERY_LEDGER.json"):
        assert not (M118 / absent).exists(), absent


def test_the_preregistration_states_the_failure_and_success_rules():
    text = (M118 / "PREREGISTRATION.md").read_text(encoding="utf-8")
    assert "stops before scientific generation" in text
    assert "H63 untested / instrument unavailable at execution time" in text
    assert "must not be used to alter the H63 scientific proposition" in text
    assert "No provider substitution" in text


# -------------------------------------------------------------------------------------------
# Readiness revision 2: the budget must afford the retries the plan grants
# -------------------------------------------------------------------------------------------

def test_the_budget_is_derived_from_the_retry_rule_not_chosen():
    budget = readiness.plan()["budget"]
    assert budget["chosen_rather_than_derived"] is False
    assert budget["max_requests"] == readiness.MANDATORY_REQUESTS * (readiness.MAX_RETRIES + 1)


def test_the_budget_affords_every_retry_the_plan_permits():
    """Revision 1 granted two retries on eleven requests with a budget of twelve."""
    assert readiness.MAX_REQUESTS >= readiness.MANDATORY_REQUESTS * (readiness.MAX_RETRIES + 1)


def test_the_plan_refuses_to_freeze_a_budget_that_cannot_afford_its_retries(monkeypatch):
    monkeypatch.setattr(readiness, "MAX_REQUESTS", 12)
    with pytest.raises(readiness.ReadinessError, match="cannot accommodate the retries"):
        readiness.plan()


def test_the_mandatory_request_count_matches_the_probes_plus_the_stress():
    matrix = readiness.probes.build_matrix(readiness.m116._census())
    assert readiness.MANDATORY_REQUESTS == len(matrix) + 1


def test_no_requirement_was_relaxed_by_the_budget_fix():
    frozen = readiness.plan()
    assert readiness.STRESS_MIN_COMPLETION_TOKENS == 32000
    assert readiness.MAX_REASONING_TOKENS == 0
    assert frozen["stress_requirement"]["finish_reason"] == "stop"
    assert frozen["stress_requirement"]["output_must_conform"] is True
    assert frozen["route"]["provider"] == fixed.PROVIDER


def test_the_aborted_attempt_is_preserved_and_wrote_no_verdict():
    directory = M118 / "READINESS_ATTEMPT_01_INSTRUMENT_ABORT"
    assert (directory / "README.md").is_file()
    text = (directory / "README.md").read_text(encoding="utf-8")
    assert "instrument abort" in text
    assert "no verdict" in text.lower()
    assert not (directory / "READINESS_RESULT.json").exists()


def test_the_abort_record_does_not_claim_the_route_failed():
    text = (M118 / "READINESS_ATTEMPT_01_INSTRUMENT_ABORT" / "README.md").read_text(
        encoding="utf-8")
    assert "no verdict about the fixed route exists" in text.lower() or \
        "Verdict about the route | **none**" in text
    assert "Nothing can be said about whether the route enforces" in text
