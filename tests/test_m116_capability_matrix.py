"""Hostile tests for the M116 DEVELOPMENT capability matrix.

Every test is local. `_request` is replaced everywhere, so no network call is made.

The attacks these defend against are the ones that would make the matrix meaningless: conflating a
parse failure with a schema violation, letting an unsupported keyword pass unnoticed, leaking a
generated value into the record, redrawing a probe because its content was inconvenient, adapting a
later probe to an earlier observation, smuggling carrier semantics into DEVELOPMENT, substituting
the route, weakening the census, or moving the interpretation after seeing the outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m116_capability_probes as probes
from metamorphosis import m116_schema as schema_tools
from scripts import audit_m116_capability_matrix as matrix

ROOT = Path(__file__).resolve().parents[1]


def _census() -> dict:
    return json.loads((ROOT / "experiments" / "M116" / "CARRIER_SCHEMA_CENSUS.json")
                      .read_text("utf-8"))["frozen_carrier_census"]


def _conforming(schema: dict):
    """Build an instance that satisfies `schema`, used to simulate an enforcing route."""
    kind = schema.get("type")
    if kind == "object":
        return {k: _conforming(v) for k, v in (schema.get("properties") or {}).items()}
    if kind == "array":
        return [_conforming(schema["items"]) for _ in range(max(int(schema.get("minItems", 1)), 1))]
    if kind == "string":
        if "enum" in schema:
            return schema["enum"][0]
        if schema.get("pattern") == r"^zq[0-9]{4}$":
            return "zq0001"
        return "ok"
    if kind == "integer":
        return int(schema.get("minimum", 0))
    if kind == "boolean":
        return True
    return None


def _observed(content, status: int = 200, finish: str = "stop", tokens: int = 120):
    body = {
        "model": matrix.MODEL, "provider": matrix.PROVIDER,
        "choices": [{"finish_reason": finish,
                     "message": {"content": content if isinstance(content, str)
                                 else json.dumps(content)}}],
        "usage": {"completion_tokens": tokens, "prompt_tokens": 40,
                  "total_tokens": 40 + tokens,
                  "completion_tokens_details": {"reasoning_tokens": 0}},
    }
    return {"status": status, "body": body, "response_bytes": 900,
            "started_at": "2026-09-01T00:00:00Z", "finished_at": "2026-09-01T00:00:05Z",
            "response_headers": {"x-generation-id": "gen-probe"},
            "transport_failure_class": None, "model_execution_cannot_be_excluded": False}


# ---------------------------------------------------------------------------------------------
# The observability gap this milestone exists to close
# ---------------------------------------------------------------------------------------------

def test_parse_failure_and_schema_violation_are_never_conflated():
    probe = probes.build_matrix(_census())[0]
    invalid = matrix.diagnose(probe, _observed("this is not json"))
    violated = matrix.diagnose(probe, _observed({"band_%d" % i: "notaband" for i in range(6)}))
    assert invalid["outcome"] == "invalid_json"
    assert invalid["content_parses_as_json"] is False
    assert violated["outcome"] == "enum_violation"
    assert violated["content_parses_as_json"] is True
    assert invalid["outcome"] != violated["outcome"]


@pytest.mark.parametrize(
    "probe_name,bad,expected",
    [
        ("enum", {"band_%d" % i: "notaband" for i in range(6)}, "enum_violation"),
        ("pattern", {"ref_%d" % i: "nope" for i in range(6)}, "pattern_violation"),
        ("required", {"named_0": "a", "named_1": "b", "named_2": "c"}, "required_violation"),
        ("integer_bounds", {"gauge_%d" % i: 7 for i in range(6)}, "bounds_violation"),
    ],
)
def test_each_violation_class_is_reported_distinctly(probe_name, bad, expected):
    probe = next(p for p in probes.build_matrix(_census()) if p["name"] == probe_name)
    result = matrix.diagnose(probe, _observed(bad))
    assert result["outcome"] == expected
    assert result["first_failing_keyword"]
    assert result["failing_schema_location"]


def test_additional_properties_and_cardinality_violations_are_distinct():
    built = {p["name"]: p for p in probes.build_matrix(_census())}
    extra = matrix.diagnose(built["additional_properties"],
                            _observed({"kept": "a", "extra_a": "b"}))
    too_few = matrix.diagnose(built["min_items"], _observed({"readings": [1, 2, 3]}))
    too_many = matrix.diagnose(built["max_items"], _observed({"samples": list(range(20))}))
    assert extra["outcome"] == "additional_properties_violation"
    assert too_few["outcome"] == "min_items_violation"
    assert too_many["outcome"] == "max_items_violation"
    assert len({extra["outcome"], too_few["outcome"], too_many["outcome"]}) == 3


def test_a_conforming_probe_is_reported_as_enforced():
    probe = probes.build_matrix(_census())[0]
    result = matrix.diagnose(probe, _observed(_conforming(probe["schema"])))
    assert result["outcome"] == "conforming"
    assert result["schema_conforms"] is True


def test_wrong_top_level_type_is_its_own_outcome():
    probe = probes.build_matrix(_census())[0]
    result = matrix.diagnose(probe, _observed([1, 2, 3]))
    assert result["outcome"] == "wrong_top_level_type"
    assert result["content_parses_as_json"] is True
    assert result["top_level_type_correct"] is False


def test_missing_completion_and_transport_failure_are_distinct():
    probe = probes.build_matrix(_census())[0]
    empty = matrix.diagnose(probe, _observed(""))
    assert empty["outcome"] == "missing_completion"
    dead = dict(_observed("{}"))
    dead.update({"status": None, "body": None, "transport_failure_class": "TimeoutError"})
    assert matrix.diagnose(probe, dead)["outcome"] == "transport_or_provider_failure"


def test_every_declared_outcome_is_reachable():
    """A vocabulary wider than the classifier is exactly the defect this milestone corrects.

    Every outcome must be produced by some observation, or be `not_attempted`, which the runner
    assigns when a prerequisite fails and the combined probe is never sent.
    """
    built = {p["name"]: p for p in probes.build_matrix(_census())}
    dead = {**_observed("{}"), "status": None, "body": None,
            "transport_failure_class": "TimeoutError"}
    produced = {
        matrix.diagnose(built["enum"], _observed(_conforming(built["enum"]["schema"])))["outcome"],
        matrix.diagnose(built["enum"], _observed("not json"))["outcome"],
        matrix.diagnose(built["enum"], _observed([1, 2]))["outcome"],
        matrix.diagnose(built["enum"], _observed({"band_%d" % i: "x" for i in range(6)}))["outcome"],
        matrix.diagnose(built["pattern"], _observed({"ref_%d" % i: "x" for i in range(6)}))["outcome"],
        matrix.diagnose(built["min_items"], _observed({"readings": [1]}))["outcome"],
        matrix.diagnose(built["max_items"], _observed({"samples": list(range(9))}))["outcome"],
        matrix.diagnose(built["required"], _observed({"named_0": "a"}))["outcome"],
        matrix.diagnose(built["additional_properties"],
                        _observed({"kept": "a", "z": "b"}))["outcome"],
        matrix.diagnose(built["integer_bounds"],
                        _observed({"gauge_%d" % i: 1 for i in range(6)}))["outcome"],
        matrix.diagnose(built["integer_bounds"],
                        _observed({"gauge_%d" % i: "s" for i in range(6)}))["outcome"],
        matrix.diagnose(built["nesting_depth"], _observed({"root": "terminus"}))["outcome"],
        matrix.diagnose(built["enum"], _observed(""))["outcome"],
        matrix.diagnose(built["enum"], dead)["outcome"],
        "not_attempted",
    }
    # `other_schema_violation` is the fail-closed default for a keyword with no specific mapping.
    assert produced == set(matrix.OUTCOMES) - {"other_schema_violation"}
    assert "other_schema_violation" in matrix.OUTCOMES


# ---------------------------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------------------------

def test_no_generated_value_reaches_the_record():
    probe = next(p for p in probes.build_matrix(_census()) if p["name"] == "pattern")
    secret_value = "TELLTALE-GENERATED-VALUE"
    result = matrix.diagnose(probe, _observed({"ref_%d" % i: secret_value for i in range(6)}))
    serialized = json.dumps(result)
    assert secret_value not in serialized
    assert result["outcome"] == "pattern_violation"
    # Only the schema's own vocabulary and array indices may appear in the paths.
    assert result["failing_instance_path"].startswith("/ref_")


def test_the_record_carries_no_raw_completion():
    probe = probes.build_matrix(_census())[0]
    result = matrix.diagnose(probe, _observed(_conforming(probe["schema"])))
    assert result["raw_completion_persisted"] is False
    assert "content" not in result and "message" not in result


def test_free_text_provider_messages_do_not_survive():
    probe = probes.build_matrix(_census())[0]
    observed = _observed("{}")
    observed["body"]["choices"][0]["finish_reason"] = "stopped: quota for org_9f3 exceeded"
    result = matrix.diagnose(probe, observed)
    assert result["finish_reason"] is None


# ---------------------------------------------------------------------------------------------
# Boundaries the matrix must not cross
# ---------------------------------------------------------------------------------------------

def test_no_probe_carries_carrier_vocabulary():
    probes.assert_non_carrier(probes.build_matrix(_census()))


def test_no_probe_prompt_overlaps_a_qualifying_input():
    matrix.matrix()  # asserts non-qualifying internally
    for probe in probes.build_matrix(_census()):
        for milestone in ("M113", "M114", "M115"):
            path = ROOT / "experiments" / milestone / "QUALIFYING_INPUT.txt"
            if path.is_file():
                assert probe["prompt"].strip() not in path.read_text("utf-8", errors="replace")


def test_the_route_is_unchanged_from_m116():
    frozen = matrix.plan()
    assert frozen["route"]["model"] == "deepseek/deepseek-v4-flash-0731"
    assert frozen["route"]["canonical_checkpoint"] == "deepseek/deepseek-v4-flash-20260731"
    assert frozen["route"]["provider"] == "Alibaba"
    body = matrix.request_body(probes.build_matrix(_census())[0])
    assert body["provider"] == {"only": ["Alibaba"], "allow_fallbacks": False,
                                "require_parameters": True}


def test_the_required_classes_are_derived_from_the_census_not_listed():
    census = _census()
    assert probes.required_feature_classes(census) == matrix.plan()["required_feature_classes"]
    thinner = json.loads(json.dumps(census))
    thinner["keyword_counts"]["pattern"] = 0
    assert "pattern" not in probes.required_feature_classes(thinner)
    assert "pattern" in probes.required_feature_classes(census)


def test_a_weakened_census_produces_a_smaller_matrix_and_is_visible():
    census = _census()
    thinner = json.loads(json.dumps(census))
    thinner["keyword_counts"]["enum"] = 0
    assert len(probes.build_matrix(thinner)) < len(probes.build_matrix(census))


# ---------------------------------------------------------------------------------------------
# The frozen plan and the decision rule
# ---------------------------------------------------------------------------------------------

def test_the_plan_is_deterministic():
    assert matrix.plan()["plan_sha256"] == matrix.plan()["plan_sha256"]


def test_the_combined_probe_is_last_and_marked_non_isolated():
    entries = matrix.plan()["probes"]
    assert entries[-1]["name"] == "combined"
    assert entries[-1]["isolated"] is False
    assert all(e["isolated"] for e in entries[:-1])


def test_case_b_when_any_isolated_capability_is_unenforced():
    observations = [
        {"probe": "enum", "feature_class": "enum", "outcome": "conforming"},
        {"probe": "pattern", "feature_class": "pattern", "outcome": "pattern_violation"},
    ]
    decision = matrix.decide(observations)
    assert decision["case"] == "B"
    assert decision["route_validated_for_h61"] is False
    assert decision["unenforced_feature_classes"] == ["pattern"]
    assert decision["h61_remains_untested"] is True


def test_case_a_requires_every_isolated_probe_and_the_combined_one():
    passing = [{"probe": n, "feature_class": n, "outcome": "conforming"}
               for n in ("enum", "pattern")]
    assert matrix.decide(passing)["case"] == "B", "no combined probe means not Case A"
    with_combined = passing + [{"probe": "combined", "feature_class": "combined",
                                "outcome": "conforming"}]
    assert matrix.decide(with_combined)["case"] == "A"
    failed_combined = passing + [{"probe": "combined", "feature_class": "combined",
                                  "outcome": "min_items_violation"}]
    assert matrix.decide(failed_combined)["case"] == "B"


def test_the_decision_rule_never_authorizes_weakening_or_route_change():
    rule = matrix.plan()["decision_rule"]
    assert rule["weakening_the_carrier_schema_permitted"] is False
    assert rule["changing_route_inside_h61_permitted"] is False
    assert matrix.plan()["content_dependent_redraw_permitted"] is False
    assert matrix.plan()["repair_permitted"] is False
    assert matrix.plan()["probe_adaptation_after_observation_permitted"] is False


# ---------------------------------------------------------------------------------------------
# Execution lifecycle, no network
# ---------------------------------------------------------------------------------------------

@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(matrix, "REPORT_PATH", tmp_path / "report.json")
    monkeypatch.setattr(matrix, "LEDGER_PATH", tmp_path / "ledger.json")
    monkeypatch.setattr(matrix, "LOCK_PATH", tmp_path / "lock")
    monkeypatch.setattr(matrix, "RETRY_WAIT_SECONDS", 0)
    monkeypatch.setenv(matrix.SECRET_VARIABLE, "test-key-never-real")
    return tmp_path


def test_an_enforcing_route_reaches_case_a(sandbox, monkeypatch):
    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: _observed(_conforming(probe["schema"])))
    report = matrix.execute()
    assert report["decision"]["case"] == "A"
    assert report["decision"]["route_validated_for_h61"] is True
    assert report["qualifying_calls"] == 0
    assert len(report["observations"]) == 10


def test_a_non_enforcing_route_reaches_case_b_and_skips_the_combined_probe(sandbox, monkeypatch):
    monkeypatch.setattr(matrix, "_request", lambda probe, **k: _observed({"anything": "at all"}))
    report = matrix.execute()
    assert report["decision"]["case"] == "B"
    combined = [o for o in report["observations"] if o["probe"] == "combined"]
    assert combined and combined[0]["outcome"] == "not_attempted"
    assert report["decision"]["unenforced_feature_classes"]


def test_a_schema_violation_never_triggers_a_redraw(sandbox, monkeypatch):
    calls = []

    def once(probe, **kwargs):
        calls.append(probe["name"])
        return _observed({"wrong": "shape"})

    monkeypatch.setattr(matrix, "_request", once)
    matrix.execute()
    # One call per isolated probe; the combined probe is skipped, and nothing is retried.
    assert len(calls) == len(set(calls)) == 9


def test_only_a_pre_generation_429_retries(sandbox, monkeypatch):
    calls = []

    def flaky(probe, **kwargs):
        calls.append(probe["name"])
        if probe["name"] == "enum" and calls.count("enum") < 2:
            observed = _observed("", status=429, tokens=0)
            observed["body"]["choices"] = []
            observed["body"]["usage"]["completion_tokens"] = 0
            return observed
        return _observed(_conforming(probe["schema"]))

    monkeypatch.setattr(matrix, "_request", flaky)
    report = matrix.execute()
    assert calls.count("enum") == 2
    assert report["decision"]["case"] == "A"


def test_a_429_carrying_execution_evidence_does_not_retry(sandbox, monkeypatch):
    calls = []

    def busy(probe, **kwargs):
        calls.append(probe["name"])
        observed = _observed({"partial": True}, status=429)
        return observed

    monkeypatch.setattr(matrix, "_request", busy)
    matrix.execute()
    assert calls.count("enum") == 1


def test_the_matrix_is_never_redrawn(sandbox, monkeypatch):
    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: _observed(_conforming(probe["schema"])))
    matrix.execute()
    with pytest.raises(matrix.CapabilityMatrixError, match="not redrawn"):
        matrix.execute()


def test_no_credential_stops_before_any_request(sandbox, monkeypatch):
    reached = []
    monkeypatch.delenv(matrix.SECRET_VARIABLE, raising=False)
    monkeypatch.setattr(matrix, "_request", lambda probe, **k: reached.append(1) or _observed("{}"))
    with pytest.raises(matrix.CapabilityMatrixError, match="not set"):
        matrix.execute()
    assert reached == []


def test_the_persisted_report_carries_no_generated_values(sandbox, monkeypatch):
    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: _observed({"telltale_key": "TELLTALE-VALUE"}))
    matrix.execute()
    persisted = (sandbox / "report.json").read_text("utf-8")
    assert "TELLTALE-VALUE" not in persisted
    assert '"raw_completion_persisted":false' in persisted.replace(" ", "")


def test_probes_are_not_adapted_between_observations(sandbox, monkeypatch):
    """The sequence sent must equal the sequence planned, whatever the observations say."""
    planned = [e["name"] for e in matrix.plan()["probes"]]
    sent = []
    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: sent.append(probe["name"]) or
                        _observed(_conforming(probe["schema"])))
    matrix.execute()
    assert sent == planned


def test_the_frozen_h61_records_are_untouched_by_the_matrix():
    for absent in ("ANALYSIS_PLAN.json", "GENERATOR_SPEC.json", "SEALED_BANK.json.gpg",
                   "DELIVERY_LEDGER.json", "RESULT.json"):
        assert not (ROOT / "experiments" / "M116" / absent).exists()
    m115 = json.loads((ROOT / "experiments" / "M115" / "RESULT.json").read_text("utf-8"))
    assert m115["verdict"] == "instrument-aborted"
    assert m115["hypothesis_status"] == "untested"


# ---------------------------------------------------------------------------------------------
# Hostile-review finding: a scalar type error is not a nesting failure
# ---------------------------------------------------------------------------------------------

def test_a_scalar_type_error_is_not_reported_as_a_nesting_violation():
    """Calling every `type` failure "nesting" would put a structural claim in the profile that the
    evidence does not support."""
    probe = next(p for p in probes.build_matrix(_census()) if p["name"] == "integer_bounds")
    result = matrix.diagnose(probe, _observed({"gauge_%d" % i: "not-a-number" for i in range(6)}))
    assert result["first_failing_keyword"] == "type"
    assert result["outcome"] == "type_violation"
    assert result["outcome"] != "nesting_violation"


def test_a_structural_probe_reports_a_depth_shortfall_as_nesting():
    for name in ("nesting_depth", "nested_arrays"):
        probe = next(p for p in probes.build_matrix(_census()) if p["name"] == name)
        shallow = {"root": "terminus"} if name == "nesting_depth" else {"tier": ["flat"]}
        result = matrix.diagnose(probe, _observed(shallow))
        assert result["outcome"] == "nesting_violation", name


def test_only_the_structural_probes_may_yield_a_nesting_violation():
    structural = {p["name"] for p in probes.build_matrix(_census())
                  if p["feature_class"] in matrix._STRUCTURAL_FEATURES}
    assert structural == {"nesting_depth", "nested_arrays"}


def test_type_violation_is_in_the_frozen_vocabulary():
    assert "type_violation" in matrix.OUTCOMES
    assert "nesting_violation" in matrix.OUTCOMES


def test_an_undiagnosable_response_becomes_evidence_not_a_crash(sandbox, monkeypatch):
    """A crash mid-matrix would abort before the report exists, leaving sent probes re-sendable."""
    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: {"status": 200, "body": {"choices": "not-a-list"},
                                            "response_bytes": 10, "response_headers": {},
                                            "transport_failure_class": None,
                                            "model_execution_cannot_be_excluded": False})
    report = matrix.execute()
    assert report["decision"]["case"] == "B"
    assert all(o["outcome"] in matrix.OUTCOMES for o in report["observations"])


def test_a_restart_resumes_and_never_re_sends_an_observed_probe(sandbox, monkeypatch):
    sent = []

    def crash_after_three(probe, **kwargs):
        if len(sent) == 3:
            raise RuntimeError("process died mid-matrix")
        sent.append(probe["name"])
        return _observed(_conforming(probe["schema"]))

    monkeypatch.setattr(matrix, "_request", crash_after_three)
    with pytest.raises(RuntimeError):
        matrix.execute()
    first_pass = list(sent)
    assert len(first_pass) == 3

    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: sent.append(probe["name"]) or
                        _observed(_conforming(probe["schema"])))
    report = matrix.execute()
    resumed = sent[len(first_pass):]
    assert not (set(first_pass) & set(resumed)), "a probe was re-sent after being observed"
    assert report["decision"]["case"] == "A"
    assert len(report["observations"]) == 10


def test_a_ledger_from_a_different_plan_is_refused(sandbox, monkeypatch):
    (sandbox / "ledger.json").write_text(json.dumps(
        {"plan_sha256": "0" * 64, "observations": []}), encoding="utf-8")
    monkeypatch.setattr(matrix, "_request",
                        lambda probe, **k: _observed(_conforming(probe["schema"])))
    with pytest.raises(matrix.CapabilityMatrixError, match="different frozen plan"):
        matrix.execute()


def test_changing_the_decision_rule_changes_the_plan_digest(monkeypatch):
    """The interpretation is pinned by the same digest the report records."""
    before = matrix.plan()["plan_sha256"]
    original = matrix.plan

    def altered():
        record = original()
        record["decision_rule"]["case_a"] = "something more convenient"
        record["plan_sha256"] = ""
        from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
        record["plan_sha256"] = sha256_hex(
            canonical_bytes({k: v for k, v in record.items() if k != "plan_sha256"}))
        return record

    assert altered()["plan_sha256"] != before
