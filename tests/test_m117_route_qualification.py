"""Hostile tests for M117 Stage 1 route qualification. No test makes a network call.

The attacks here are the ones that would let a route be selected for a reason other than the frozen
rule: catalogue order deciding the universe, a provider appearing or vanishing between derivation
and execution, an observation changing what comes next, a threshold moving after a result, partial
capability qualifying, declared capability standing in for measured enforcement, or M116's old
route being treated as special.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m117_route_qualification as rule
from scripts import audit_m117_route_qualification as stage1

ROOT = Path(__file__).resolve().parents[1]


def _entry(provider="Alpha", model="a/model", **overrides):
    entry = {
        "model": model, "provider": provider, "canonical_checkpoint": "%s-2026" % model,
        "provider_found": True, "endpoint_available": True,
        "uptime_last_1d": 99.9, "uptime_last_30m": 99.5,
        "latency_last_30m": {"p50": 500.0}, "max_completion_tokens": 100000,
        "supported_parameters": list(rule.REQUIRED_SUPPORTED_PARAMETERS),
    }
    entry.update(overrides)
    return entry


def _profile(model="a/model", provider="Alpha", **overrides):
    profile = {
        "model": model, "provider": provider,
        "required_feature_classes": ["enum", "pattern"],
        "unenforced_feature_classes": [],
        "combined_probe_conforms": True, "token_capacity_holds": True,
        "requested_model_exact": True, "canonical_checkpoint_exact": True, "provider_exact": True,
        "router_direct": True, "router_no_fallback": True, "router_one_endpoint": True,
        "router_one_attempt": True, "router_no_pipeline_intervention": True,
        "reliability_minimum_holds": True,
    }
    profile.update(overrides)
    profile["qualification"] = rule.qualifies(profile)
    return profile


# ---------------------------------------------------------------------------------------------
# Declared capability never qualifies anything
# ---------------------------------------------------------------------------------------------

def test_declared_capability_does_not_qualify_a_route():
    """M116's route advertised structured outputs and enforced nothing. That must not recur."""
    advertised = _profile(unenforced_feature_classes=["enum", "pattern"],
                          combined_probe_conforms=False)
    assert advertised["qualification"]["qualifies"] is False
    # Eligibility, which reads the advertisement, still lets it through to be measured.
    assert rule.eligibility(_entry())["eligible"] is True
    assert stage1.plan()["eligibility"]["bounds_budget_never_qualifies"] is True


def test_partial_capability_is_not_qualification():
    for missing in (["enum"], ["pattern"], ["enum", "pattern"]):
        assert rule.qualifies(_profile(unenforced_feature_classes=missing))["qualifies"] is False


def test_every_qualification_clause_is_load_bearing():
    baseline = _profile()
    assert baseline["qualification"]["qualifies"] is True
    for clause in ("combined_probe_conforms", "token_capacity_holds", "requested_model_exact",
                   "canonical_checkpoint_exact", "provider_exact", "router_direct",
                   "router_no_fallback", "router_one_endpoint", "router_one_attempt",
                   "router_no_pipeline_intervention", "reliability_minimum_holds"):
        broken = _profile(**{clause: False})
        assert broken["qualification"]["qualifies"] is False, clause


def test_a_route_with_no_required_classes_cannot_qualify_vacuously():
    assert rule.qualifies(_profile(required_feature_classes=[]))["qualifies"] is False


def test_token_capacity_must_be_measured_not_inferred():
    assert rule.qualifies(_profile(token_capacity_holds=None))["qualifies"] is False
    assert rule.qualifies(_profile(token_capacity_holds="probably"))["qualifies"] is False


# ---------------------------------------------------------------------------------------------
# The universe and its order
# ---------------------------------------------------------------------------------------------

def test_the_universe_does_not_depend_on_catalogue_order():
    entries = [_entry(provider="Gamma"), _entry(provider="Alpha"), _entry(provider="Beta")]
    forward = rule.derive_universe(entries)
    backward = rule.derive_universe(list(reversed(entries)))
    assert [c["provider"] for c in forward["ordered_candidates"]] == \
           [c["provider"] for c in backward["ordered_candidates"]]


def test_the_order_is_the_inherited_reliability_ordering():
    assert rule.RELIABILITY_ORDERING == (
        "uptime_last_1d_desc", "uptime_last_30m_desc",
        "latency_last_30m_p50_asc", "provider_name_asc")
    entries = [
        _entry(provider="Slow", latency_last_30m={"p50": 900.0}),
        _entry(provider="Fast", latency_last_30m={"p50": 100.0}),
        _entry(provider="Best", uptime_last_1d=100.0, latency_last_30m={"p50": 900.0}),
    ]
    ordered = [c["provider"] for c in rule.derive_universe(entries)["ordered_candidates"]]
    assert ordered == ["Best", "Fast", "Slow"]


def test_a_candidate_missing_a_required_metric_is_excluded_not_defaulted():
    verdict = rule.eligibility(_entry(uptime_last_1d=None))
    assert verdict["eligible"] is False
    assert "missing_required_metric" in verdict["exclusions"]
    with pytest.raises(rule.RouteQualificationError):
        rule.rank_key(_entry(uptime_last_1d=None))


@pytest.mark.parametrize("override,reason", [
    ({"uptime_last_1d": 50.0}, "uptime_last_1d_below_minimum"),
    ({"uptime_last_30m": 10.0}, "uptime_last_30m_below_minimum"),
    ({"max_completion_tokens": 1024}, "max_completion_tokens_below_minimum"),
    ({"supported_parameters": ["response_format"]}, "missing_supported_parameter"),
    ({"canonical_checkpoint": ""}, "no_canonical_checkpoint_declared"),
    ({"endpoint_available": False}, "endpoint_not_available"),
])
def test_each_exclusion_reason_is_reachable_and_named(override, reason):
    verdict = rule.eligibility(_entry(**override))
    assert verdict["eligible"] is False
    assert reason in verdict["exclusions"]
    assert set(verdict["exclusions"]) <= set(rule.EXCLUSION_REASONS)


def test_every_declared_exclusion_reason_is_reachable():
    reached = set()
    for override in ({"uptime_last_1d": None}, {"uptime_last_1d": 50.0}, {"uptime_last_30m": 10.0},
                     {"max_completion_tokens": 1}, {"supported_parameters": []},
                     {"canonical_checkpoint": ""}, {"endpoint_available": False}):
        reached |= set(rule.eligibility(_entry(**override))["exclusions"])
    assert reached == set(rule.EXCLUSION_REASONS)


# ---------------------------------------------------------------------------------------------
# Selection cannot be influenced by an observation
# ---------------------------------------------------------------------------------------------

def test_selection_takes_the_first_qualifier_in_the_frozen_order():
    universe = rule.derive_universe([_entry(provider="Alpha"), _entry(provider="Beta")])
    profiles = [_profile(provider="Alpha", unenforced_feature_classes=["enum"]),
                _profile(provider="Beta")]
    selection = rule.select(universe, profiles)
    assert selection["selected"]["provider"] == "Beta"
    assert selection["carrier_quality_was_an_input"] is False


def test_a_later_better_candidate_cannot_displace_an_earlier_qualifier():
    """Once the first qualifier in the frozen order is found, nothing later can outrank it."""
    universe = rule.derive_universe([_entry(provider="Alpha"), _entry(provider="Beta")])
    selection = rule.select(universe, [_profile(provider="Alpha"), _profile(provider="Beta")])
    assert selection["selected"]["provider"] == "Alpha"


def test_no_qualifier_means_no_selection():
    universe = rule.derive_universe([_entry(provider="Alpha")])
    selection = rule.select(universe, [_profile(provider="Alpha",
                                                unenforced_feature_classes=["enum"])])
    assert selection["route_selected"] is False
    assert selection["selected"] is None


def test_a_profile_for_a_candidate_outside_the_universe_cannot_be_selected():
    universe = rule.derive_universe([_entry(provider="Alpha")])
    selection = rule.select(universe, [_profile(provider="Intruder")])
    assert selection["route_selected"] is False


def test_m116s_previous_route_is_not_special_cased():
    source = (ROOT / "metamorphosis" / "m117_route_qualification.py").read_text("utf-8")
    runner = (ROOT / "scripts" / "audit_m117_route_qualification.py").read_text("utf-8")
    for token in ("deepseek", "Alibaba", "v4-flash"):
        assert token not in source, token
        assert token not in runner, token


# ---------------------------------------------------------------------------------------------
# The frozen plan and its budget
# ---------------------------------------------------------------------------------------------

def test_the_plan_is_deterministic_and_binds_the_matrix():
    first, second = stage1.plan(), stage1.plan()
    assert first["plan_sha256"] == second["plan_sha256"]
    assert first["capability_matrix"]["inherited_unchanged_from"] == "M116"
    from scripts import audit_m116_capability_matrix as m116
    assert first["capability_matrix"]["plan_sha256"] == m116.plan()["plan_sha256"]


def test_changing_a_threshold_changes_the_plan_digest(monkeypatch):
    before = stage1.plan()["plan_sha256"]
    monkeypatch.setattr(rule, "MINIMUM_UPTIME_LAST_1D", 50.0)
    assert stage1.plan()["plan_sha256"] != before


def test_the_budget_is_fixed_and_bounded():
    budget = stage1.plan()["budget"]
    assert budget["max_requests_per_probe"] == 3
    assert budget["global_request_ceiling"] == rule.GLOBAL_REQUEST_CEILING
    assert budget["exceeding_the_ceiling_ends_stage_1_without_a_selection"] is True


def test_the_plan_forbids_the_things_that_would_break_it():
    forbidden = stage1.plan()["prohibited"]
    for clause in ("adding a candidate after probing begins", "manually preferring a candidate",
                   "carrier quality as a selection input", "substituting a route",
                   "treating M116's previous route specially"):
        assert clause in forbidden
    assert stage1.plan()["retry"]["content_dependent_redraw_permitted"] is False
    assert stage1.plan()["retry"]["repair_permitted"] is False


def test_the_stress_runs_only_after_full_structural_qualification():
    assert stage1.plan()["token_capacity_stress"][
        "runs_only_after_full_structural_qualification"] is True


# ---------------------------------------------------------------------------------------------
# Execution boundaries, without network
# ---------------------------------------------------------------------------------------------

def test_execution_refuses_without_a_committed_universe(tmp_path, monkeypatch):
    monkeypatch.setattr(stage1, "UNIVERSE_PATH", tmp_path / "universe.json")
    monkeypatch.setattr(stage1, "REPORT_PATH", tmp_path / "report.json")
    monkeypatch.setattr(stage1, "LEDGER_PATH", tmp_path / "ledger.json")
    monkeypatch.setattr(stage1, "LOCK_PATH", tmp_path / "lock")
    monkeypatch.setenv(stage1.SECRET_VARIABLE, "test-key")
    with pytest.raises(stage1.Stage1Error, match="committed before any candidate is probed"):
        stage1.execute()


def test_a_tampered_universe_is_refused(tmp_path, monkeypatch):
    universe = rule.derive_universe([_entry()])
    universe.update({"plan_sha256": stage1.plan()["plan_sha256"],
                     "catalogue_snapshot_sha256": "a" * 64, "universe_sha256": "b" * 64})
    path = tmp_path / "universe.json"
    path.write_text(json.dumps(universe), encoding="utf-8")
    monkeypatch.setattr(stage1, "UNIVERSE_PATH", path)
    monkeypatch.setattr(stage1, "REPORT_PATH", tmp_path / "report.json")
    monkeypatch.setattr(stage1, "LEDGER_PATH", tmp_path / "ledger.json")
    monkeypatch.setattr(stage1, "LOCK_PATH", tmp_path / "lock")
    monkeypatch.setenv(stage1.SECRET_VARIABLE, "test-key")
    with pytest.raises(stage1.Stage1Error, match="digest does not match"):
        stage1.execute()


def test_no_credential_stops_before_any_request(tmp_path, monkeypatch):
    monkeypatch.delenv(stage1.SECRET_VARIABLE, raising=False)
    monkeypatch.setattr(stage1, "REPORT_PATH", tmp_path / "report.json")
    with pytest.raises(stage1.Stage1Error, match="not set"):
        stage1.execute()


def test_the_catalogue_snapshot_is_never_redrawn(tmp_path, monkeypatch):
    monkeypatch.setattr(stage1, "CATALOGUE_PATH", tmp_path / "cat.json")
    (tmp_path / "cat.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(stage1, "UNIVERSE_PATH", tmp_path / "universe.json")
    with pytest.raises(stage1.Stage1Error, match="not redrawn"):
        stage1.snapshot_catalogue()


def test_no_h62_artifact_exists_yet():
    """Stage 1's own report is not an H62 artifact; these five are, and none may exist."""
    for absent in ("ANALYSIS_PLAN.json", "GENERATOR_SPEC.json", "SEALED_BANK.json.gpg",
                   "RESULT.json", "CARRIER_BANK.json"):
        assert not (ROOT / "experiments" / "M117" / absent).exists(), absent


def test_the_stage_1_report_if_present_created_no_h62():
    """The report may exist -- Stage 1 ran -- but only saying it selected nothing."""
    report = ROOT / "experiments" / "M117" / "STAGE1_ROUTE_QUALIFICATION.json"
    if not report.is_file():
        return
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload.get("route_selected") is not True
    assert payload.get("selected") in (None, {})
    assert payload.get("is_a_qualifying_call") is not True
    assert payload.get("qualifying_input_was_sent") is not True


def test_stage1_is_marked_development_and_non_qualifying():
    frozen = stage1.plan()
    assert frozen["development_only"] is True
    assert frozen["is_a_qualifying_call"] is False
    assert frozen["qualifying_input_was_sent"] is False


# ---------------------------------------------------------------------------------------------
# Fidelity to the inherited matrix
# ---------------------------------------------------------------------------------------------

def test_probes_use_the_same_output_budget_as_the_inherited_matrix():
    """A smaller cap would make any truncation this harness's artifact, not the route's."""
    from scripts import audit_m116_capability_matrix as m116
    assert stage1.PROBE_MAX_TOKENS == m116.MAX_TOKENS
    body = stage1._request_body(_entry(), "p", {"type": "object"}, "n", stage1.PROBE_MAX_TOKENS)
    assert body["max_tokens"] == m116.MAX_TOKENS


def test_the_reasoning_control_follows_a_mechanical_rule():
    with_reasoning = _entry(supported_parameters=list(rule.REQUIRED_SUPPORTED_PARAMETERS)
                            + ["reasoning"])
    without = _entry()
    assert stage1.declares_reasoning(with_reasoning) is True
    assert stage1.declares_reasoning(without) is False
    assert stage1._request_body(with_reasoning, "p", {}, "n", 10)["reasoning"] == {"effort": "none"}
    assert "reasoning" not in stage1._request_body(without, "p", {}, "n", 10)


def test_every_probe_request_pins_the_route_and_forbids_fallback():
    body = stage1._request_body(_entry(provider="Alpha", model="a/model"), "p", {}, "n", 10)
    assert body["provider"] == {"only": ["Alpha"], "allow_fallbacks": False,
                                "require_parameters": True}
    assert body["model"] == "a/model"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["stream"] is False and body["seed"] == 0


def test_a_candidate_cut_short_by_the_ceiling_is_recorded_not_dropped(tmp_path, monkeypatch):
    # Patch the ceiling first: the plan digest binds the budget, so the universe must be built
    # against the same plan the runner will recompute.
    monkeypatch.setattr(rule, "GLOBAL_REQUEST_CEILING", 2)
    universe = rule.derive_universe([_entry(provider="Alpha"), _entry(provider="Beta")])
    universe.update({"plan_sha256": stage1.plan()["plan_sha256"],
                     "catalogue_snapshot_sha256": "a" * 64})
    from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
    universe["universe_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in universe.items() if k != "universe_sha256"}))
    path = tmp_path / "universe.json"
    path.write_bytes(canonical_bytes(universe) + b"\n")
    monkeypatch.setattr(stage1, "UNIVERSE_PATH", path)
    monkeypatch.setattr(stage1, "REPORT_PATH", tmp_path / "report.json")
    monkeypatch.setattr(stage1, "LEDGER_PATH", tmp_path / "ledger.json")
    monkeypatch.setattr(stage1, "LOCK_PATH", tmp_path / "lock")
    monkeypatch.setenv(stage1.SECRET_VARIABLE, "test-key")

    def refuse(*args, **kwargs):
        raise AssertionError("no network in tests")

    monkeypatch.setattr(stage1, "_http", refuse)

    def fake_send(candidate, prompt, schema, name, max_tokens, budget):
        if budget["global"] >= rule.GLOBAL_REQUEST_CEILING:
            raise stage1.Stage1Error("the global DEVELOPMENT request ceiling is reached")
        budget["global"] += 1
        budget["candidate"] += 1
        return {"status": 200, "body": {"choices": [{"finish_reason": "stop",
                                                     "message": {"content": "{}"}}]},
                "response_bytes": 5, "response_headers": {}, "transport_failure_class": None,
                "model_execution_cannot_be_excluded": False}

    monkeypatch.setattr(stage1, "_send", fake_send)
    report = stage1.execute()
    incomplete = [p for p in report["profiles"] if p.get("incomplete")]
    assert incomplete, "a candidate cut short must be recorded"
    assert incomplete[0]["qualification"]["qualifies"] is False
    assert report["selection"]["route_selected"] is False
    assert report["requests_spent"] <= rule.GLOBAL_REQUEST_CEILING


def test_a_forged_qualification_claim_cannot_select_a_route():
    """The decision point rests on the evidence, not on what the record says about it."""
    universe = rule.derive_universe([_entry(provider="Alpha")])
    forged = {"model": "a/model", "provider": "Alpha",
              "qualification": {"qualifies": True}}          # asserts it passed; nothing did
    selection = rule.select(universe, [forged])
    assert selection["route_selected"] is False
    assert selection["qualification_recomputed_at_selection"] is True


def test_selection_recomputes_rather_than_trusting_a_stale_verdict():
    universe = rule.derive_universe([_entry(provider="Alpha")])
    stale = _profile(provider="Alpha", unenforced_feature_classes=["enum"])
    stale["qualification"] = {"qualifies": True}   # verdict says pass, evidence says otherwise
    assert rule.select(universe, [stale])["route_selected"] is False


def test_an_incomplete_candidate_is_skipped_not_selected():
    universe = rule.derive_universe([_entry(provider="Alpha"), _entry(provider="Beta")])
    profiles = [{"model": "a/model", "provider": "Alpha", "incomplete": True,
                 "qualification": {"qualifies": False}},
                _profile(provider="Beta")]
    assert rule.select(universe, profiles)["selected"]["provider"] == "Beta"
