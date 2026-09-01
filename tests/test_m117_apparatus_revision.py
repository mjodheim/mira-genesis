"""The Stage 1 apparatus revision changes extraction only.

Attempt 01 reached no candidate and produced no selection: it read three catalogue fields out of
places the endpoints API does not populate, which nulled `uptime_last_1d` and
`latency_last_30m_p50` for every endpoint and excluded the whole universe on
`missing_required_metric`. That is an instrument abort, and repairing it is legitimate only if the
repair cannot have been chosen for its effect on which candidate wins.

These tests hold the repair to that: every threshold, ordering key, tie-break, budget bound and
qualification clause is pinned to the value attempt 01 carried, the decision rule is shown to be
untouched, and the corrected checkpoint field is shown to reproduce a checkpoint M116 recorded
independently, before M117 existed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m117_route_qualification as rule
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from scripts import audit_m117_route_qualification as stage1

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_01 = ROOT / "experiments" / "M117" / "ATTEMPT_01_INSTRUMENT_ABORT"


# -------------------------------------------------------------------------------------------
# The decision rule did not move
# -------------------------------------------------------------------------------------------

def test_every_threshold_is_the_value_attempt_01_carried():
    assert rule.MINIMUM_UPTIME_LAST_1D == 99.0
    assert rule.MINIMUM_UPTIME_LAST_30M == 95.0
    assert rule.MINIMUM_MAX_COMPLETION_TOKENS == 32768
    assert rule.REQUIRED_SUPPORTED_PARAMETERS == ("response_format", "structured_outputs", "seed")
    assert rule.REQUIRED_METRICS == ("uptime_last_1d", "uptime_last_30m", "latency_last_30m_p50")


def test_ordering_tie_break_and_budget_are_unchanged():
    assert rule.RELIABILITY_ORDERING == ("uptime_last_1d_desc", "uptime_last_30m_desc",
                                         "latency_last_30m_p50_asc", "provider_name_asc")
    assert rule.MAX_REQUESTS_PER_PROBE == 3
    assert rule.MAX_REQUESTS_PER_CANDIDATE == 40
    assert rule.GLOBAL_REQUEST_CEILING == 160


def test_no_exclusion_reason_was_added_or_removed():
    assert rule.EXCLUSION_REASONS == (
        "missing_required_metric", "uptime_last_1d_below_minimum", "uptime_last_30m_below_minimum",
        "max_completion_tokens_below_minimum", "missing_supported_parameter",
        "no_canonical_checkpoint_declared", "endpoint_not_available")


def test_the_frozen_constants_match_the_universe_attempt_01_committed():
    """Pinning the constants in this file is only worth something if they match the record."""
    committed = json.loads(
        (ATTEMPT_01 / "STAGE1_CANDIDATE_UNIVERSE.json").read_text(encoding="utf-8"))
    assert committed["ordering"] == list(rule.RELIABILITY_ORDERING)
    assert committed["required_supported_parameters"] == list(rule.REQUIRED_SUPPORTED_PARAMETERS)
    assert committed["minimum_uptime_last_1d"] == rule.MINIMUM_UPTIME_LAST_1D
    assert committed["minimum_uptime_last_30m"] == rule.MINIMUM_UPTIME_LAST_30M
    assert committed["minimum_max_completion_tokens"] == rule.MINIMUM_MAX_COMPLETION_TOKENS


def test_every_qualification_clause_is_still_load_bearing():
    """No clause was dropped to let a candidate through."""
    passing = {k: True for k in (
        "requested_model_exact", "provider_exact", "canonical_checkpoint_exact", "router_direct",
        "router_no_fallback", "router_one_endpoint", "router_one_attempt",
        "router_no_pipeline_intervention", "combined_probe_conforms", "token_capacity_holds",
        "reliability_minimum_holds")}
    passing["required_feature_classes"] = ["enum", "pattern"]
    passing["unenforced_feature_classes"] = []
    verdict = rule.qualifies(passing)
    assert verdict["qualifies"] is True
    assert set(verdict["checks"]) == {
        "every_required_feature_class_enforced", "combined_structural_test_holds",
        "token_capacity_stress_holds", "requested_model_identity_exact",
        "canonical_checkpoint_exact", "provider_exact", "direct_route", "no_fallback",
        "one_selected_endpoint", "one_router_attempt", "no_pipeline_intervention",
        "reliability_minimum_holds"}
    for flag in [k for k in passing if k.endswith(("_exact", "_conforms", "_holds", "_direct",
                                                   "_fallback", "_endpoint", "_attempt",
                                                   "_intervention"))]:
        assert rule.qualifies(dict(passing, **{flag: False}))["qualifies"] is False, flag
    # An unenforced feature class alone is disqualifying.
    assert rule.qualifies(
        dict(passing, unenforced_feature_classes=["enum"]))["qualifies"] is False


# -------------------------------------------------------------------------------------------
# The repair reads where the API actually publishes
# -------------------------------------------------------------------------------------------

def test_metrics_are_read_from_the_endpoint_not_a_stats_object():
    endpoint = {"uptime_last_1d": 99.5, "uptime_last_30m": 100,
                "latency_last_30m": {"p50": 600, "p90": 1193}}
    assert stage1._metric(endpoint, {}, "uptime_last_1d") == 99.5
    assert stage1._metric(endpoint, {}, "latency_last_30m")["p50"] == 600


def test_a_stats_object_is_only_a_fallback():
    assert stage1._metric({}, {"uptime_last_1d": 98.0}, "uptime_last_1d") == 98.0
    assert stage1._metric({"uptime_last_1d": 99.5}, {"uptime_last_1d": 1.0},
                          "uptime_last_1d") == 99.5


def test_the_attempt_01_shape_would_still_null_every_metric():
    """The defect, reproduced: `stats` is absent, so a stats-only read yields nothing."""
    endpoint = {"uptime_last_1d": 99.5, "latency_last_30m": {"p50": 600}, "stats": None}
    stats = endpoint.get("stats") if isinstance(endpoint.get("stats"), dict) else {}
    assert stats.get("uptime_last_1d") is None
    assert stage1._metric(endpoint, stats, "uptime_last_1d") == 99.5


def test_an_endpoint_read_the_attempt_01_way_is_excluded_for_a_missing_metric():
    """Why the whole universe was excluded, stated as a test rather than as a claim."""
    broken = {"model": "x/y", "provider": "P", "canonical_checkpoint": "x/y-20260101",
              "provider_found": True, "endpoint_available": True,
              "max_completion_tokens": 131072,
              "supported_parameters": list(rule.REQUIRED_SUPPORTED_PARAMETERS),
              "uptime_last_1d": None, "uptime_last_30m": 100,
              "latency_last_30m": {"p50": None}}
    assert "missing_required_metric" in rule.eligibility(broken)["exclusions"]
    repaired = dict(broken, uptime_last_1d=99.9, latency_last_30m={"p50": 600})
    assert rule.eligibility(repaired)["exclusions"] == []


def test_the_defect_nulled_the_metric_for_every_endpoint_uniformly():
    """Content-independent: it cannot have favoured or disfavoured any candidate."""
    universe = json.loads(
        (ATTEMPT_01 / "STAGE1_CANDIDATE_UNIVERSE.json").read_text(encoding="utf-8"))
    assessed = universe["assessed"]
    assert assessed, "attempt 01 assessed no endpoint"
    assert all(row["metrics"]["uptime_last_1d"] is None for row in assessed)
    assert all(row["metrics"]["latency_last_30m_p50"] is None for row in assessed)
    assert all("missing_required_metric" in row["exclusions"] for row in assessed)
    assert universe["eligible_count"] == 0


# -------------------------------------------------------------------------------------------
# The corrected checkpoint field is confirmed by a record that predates M117
# -------------------------------------------------------------------------------------------

def test_the_router_attests_a_dated_canonical_slug_not_the_requested_slug():
    route = json.loads((ROOT / "experiments" / "M116" / "CAPABILITY_MATRIX_DEVELOPMENT.json")
                       .read_text(encoding="utf-8"))["route"]
    assert route["canonical_checkpoint"] != route["model"]
    assert route["canonical_checkpoint"].startswith("deepseek/deepseek-v4-flash-2026")


def test_the_endpoint_display_name_is_not_a_checkpoint_identifier():
    """Attempt 01 fell back to it, which would have made the clause trivially satisfiable."""
    assert " | " in "Mancer 2 | anthracite-org/magnum-v4-72b"
    assert stage1._identity_token("Mancer 2 | anthracite-org/magnum-v4-72b") != "mancer/fp8"


# -------------------------------------------------------------------------------------------
# An identity mismatch stays diagnosable
# -------------------------------------------------------------------------------------------

def test_the_observed_identity_is_recorded_beside_the_declared_one():
    body = {"model": "x/y", "provider": "P"}
    observed = stage1._identity(
        {"model": "x/y", "provider": "P", "canonical_checkpoint": "x/y-20260101"}, body)
    assert observed["declared_canonical_checkpoint"] == "x/y-20260101"
    assert "observed_canonical_checkpoint" in observed


def test_free_text_can_never_reach_the_record_through_an_identity_field():
    assert stage1._identity_token("x" * 4096).startswith("<refused")
    assert stage1._identity_token("a\nb").startswith("<refused")
    assert stage1._identity_token({"a": 1}).startswith("<refused")
    assert stage1._identity_token(None) is None


# -------------------------------------------------------------------------------------------
# Attempt 01 is preserved, and cannot be mistaken for attempt 02
# -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,key", [
    ("STAGE1_CATALOGUE_SNAPSHOT.json", "snapshot_sha256"),
    ("STAGE1_CANDIDATE_UNIVERSE.json", "universe_sha256"),
])
def test_attempt_01_artifacts_are_preserved_and_still_verify(name, key):
    record = json.loads((ATTEMPT_01 / name).read_text(encoding="utf-8"))
    recomputed = sha256_hex(canonical_bytes({k: v for k, v in record.items() if k != key}))
    assert record[key] == recomputed


PLAN_01 = "d22c3fde72c70c8f73948aba95250685befcdca5ae90c7b85934c8a6e8508c67"
PLAN_02 = "5cc9c648f9881fd36c8d882c08b513514a5236cf29f7ecc107aad2867f112997"


def test_each_aborted_attempt_is_bound_to_its_own_frozen_plan():
    """No attempt can be confused with another, and none with the live one."""
    universe = json.loads(
        (ATTEMPT_01 / "STAGE1_CANDIDATE_UNIVERSE.json").read_text(encoding="utf-8"))
    assert universe["plan_sha256"] == PLAN_01
    universe_02 = json.loads((ROOT / "experiments" / "M117" / "ATTEMPT_02_INSTRUMENT_ABORT"
                              / "STAGE1_CANDIDATE_UNIVERSE.json").read_text(encoding="utf-8"))
    assert universe_02["plan_sha256"] == PLAN_02
    live = stage1.plan()["plan_sha256"]
    assert live not in (PLAN_01, PLAN_02)
    assert stage1.SUPERSEDED_PLAN_SHA256 == PLAN_02


def test_the_revision_is_recorded_in_the_plan_itself():
    frozen = stage1.plan()
    assert frozen["apparatus_revision"] == stage1.APPARATUS_REVISION >= 3
    assert frozen["supersedes_plan_sha256"] == stage1.SUPERSEDED_PLAN_SHA256
    assert "unchanged" in frozen["revision_rationale"]


def test_a_universe_from_the_superseded_plan_cannot_be_probed(tmp_path, monkeypatch):
    """The stale universe is not merely ignored -- it is refused."""
    stale = json.loads(
        (ATTEMPT_01 / "STAGE1_CANDIDATE_UNIVERSE.json").read_text(encoding="utf-8"))
    path = tmp_path / "STAGE1_CANDIDATE_UNIVERSE.json"
    path.write_bytes(canonical_bytes(stale) + b"\n")
    monkeypatch.setattr(stage1, "UNIVERSE_PATH", path)
    with pytest.raises(stage1.Stage1Error, match="different frozen plan"):
        stage1._committed_universe()


def test_attempt_02_still_sends_no_qualifying_input():
    frozen = stage1.plan()
    assert frozen["is_a_qualifying_call"] is False
    assert frozen["qualifying_input_was_sent"] is False


# -------------------------------------------------------------------------------------------
# Revision 3: the stress must not be malformed by the plan's own eligibility bound
# -------------------------------------------------------------------------------------------

def test_the_stress_never_asks_for_more_than_a_candidate_declares():
    """Derivable from the frozen constants alone: eligibility admits candidates at 32768."""
    floor = rule.MINIMUM_MAX_COMPLETION_TOKENS
    assert stage1._stress_max_tokens({"max_completion_tokens": floor}) == floor
    assert stage1._stress_max_tokens({"max_completion_tokens": 65536}) == 65536
    assert stage1._stress_max_tokens(
        {"max_completion_tokens": 393216}) == stage1.STRESS_MAX_TOKENS


def test_a_candidate_admitted_at_the_floor_can_still_clear_the_stress_threshold():
    """The bound would be worthless if the threshold were unreachable at the floor."""
    assert stage1.STRESS_MIN_COMPLETION_TOKENS < rule.MINIMUM_MAX_COMPLETION_TOKENS


def test_the_plan_refuses_to_freeze_an_unsatisfiable_stress(monkeypatch):
    monkeypatch.setattr(stage1, "STRESS_MIN_COMPLETION_TOKENS",
                        rule.MINIMUM_MAX_COMPLETION_TOKENS + 1)
    with pytest.raises(stage1.Stage1Error, match="more completion tokens than eligibility"):
        stage1.plan()


def test_the_stress_threshold_itself_did_not_move():
    """The request was bounded; the bar was not lowered."""
    assert stage1.STRESS_MIN_COMPLETION_TOKENS == 32000
    assert stage1.STRESS_MAX_TOKENS == 131072
    assert stage1.PROBE_MAX_TOKENS == 131072


def test_attempt_02_was_halted_on_that_defect_and_is_preserved():
    ledger = json.loads((ROOT / "experiments" / "M117" / "ATTEMPT_02_INSTRUMENT_ABORT"
                         / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    assert ledger["requests_spent"] < rule.GLOBAL_REQUEST_CEILING, "not a halt"
    stressed = [p for p in ledger["profiles"] if p.get("token_capacity_stress")]
    assert stressed, "no candidate reached the stress"
    # Every candidate that reached the stress was structurally qualified and answered HTTP 400.
    for p in stressed:
        assert p["unenforced_feature_classes"] == []
        assert p["token_capacity_stress"]["http_status"] == 400


def test_attempt_02_belongs_to_the_superseded_plan():
    ledger = json.loads((ROOT / "experiments" / "M117" / "ATTEMPT_02_INSTRUMENT_ABORT"
                         / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    assert ledger["plan_sha256"] == stage1.SUPERSEDED_PLAN_SHA256
    assert stage1.plan()["plan_sha256"] != stage1.SUPERSEDED_PLAN_SHA256


# -------------------------------------------------------------------------------------------
# Revision 3: the diagnostic that was itself blind
# -------------------------------------------------------------------------------------------

def test_the_declared_and_observed_pair_reaches_the_profile():
    """Attempt 02 recorded the verdicts and dropped the evidence for them."""
    identity = stage1._identity(
        {"model": "x/y", "provider": "P", "canonical_checkpoint": "x/y-20260101"},
        {"model": "x/y", "provider": "P"})
    clauses = {"requested_model_exact", "provider_exact", "canonical_checkpoint_exact",
               "router_direct", "router_no_fallback", "router_one_endpoint",
               "router_one_attempt", "router_no_pipeline_intervention"}
    profile = {}
    profile.update({k: v for k, v in identity.items() if k not in clauses})
    profile.update({k: identity.get(k, False) for k in clauses})
    for key in ("declared_model", "observed_model", "declared_canonical_checkpoint",
                "observed_canonical_checkpoint", "observed_attempts_shape",
                "observed_pipeline_shape", "observed_selected_endpoints"):
        assert key in profile, key
    assert clauses <= set(profile)


def test_a_missing_verdict_still_reads_as_a_failure_not_a_pass():
    clauses = ("requested_model_exact", "router_no_fallback")
    profile = {k: {}.get(k, False) for k in clauses}
    assert profile["requested_model_exact"] is False
    assert rule.qualifies(profile)["qualifies"] is False


def test_missing_router_metadata_is_distinguishable_from_a_real_fallback():
    """Absence and a populated list must not look the same in the record."""
    assert stage1._shape(None) == "absent"
    assert stage1._shape([]) == "empty_list"
    assert stage1._shape([{"x": 1}]) == "non_empty_list"
    assert stage1._shape("nope") == "not_a_list"


def test_the_no_fallback_clause_was_not_relaxed():
    """Only instrumented. Absent metadata still fails closed."""
    for absent in ({}, {"openrouter_metadata": {"strategy": "direct"}}):
        identity = stage1._identity({"model": "x", "provider": "P"}, absent)
        assert identity["router_no_fallback"] is False
        assert identity["router_no_pipeline_intervention"] is False
    proven = {"openrouter_metadata": {"strategy": "direct", "attempts": [], "pipeline": [],
                                      "attempt": 1,
                                      "endpoints": {"available": [
                                          {"model": "x-2026", "selected": True}]}}}
    identity = stage1._identity({"model": "x", "provider": "P"}, proven)
    assert identity["router_no_fallback"] is True
    assert identity["router_no_pipeline_intervention"] is True
    assert identity["observed_attempts_shape"] == "empty_list"
