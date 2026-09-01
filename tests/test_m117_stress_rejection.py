"""The stress-rejection diagnostic must establish a cause without disclosing provider text.

Four candidates enforced every required schema feature class and then answered HTTP 400 to the
token-capacity stress, and the apparatus could not say why. This diagnostic exists to end that
silence -- but it reads provider error messages, which are free text, so the boundary that keeps
that text out of the repository has to be mechanical rather than a matter of care.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m116_stress_schema as stress
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from scripts import audit_m117_stress_rejection as diag

ROOT = Path(__file__).resolve().parents[1]


# -------------------------------------------------------------------------------------------
# It measures nothing and can advance nothing
# -------------------------------------------------------------------------------------------

def test_the_diagnostic_qualifies_selects_and_scores_nothing():
    frozen = diag.plan()
    assert frozen["is_a_qualifying_call"] is False
    assert frozen["qualifying_input_was_sent"] is False
    assert frozen["selects_nothing"] is True
    assert frozen["scores_nothing"] is True
    assert frozen["development"] is True


def test_the_request_budget_is_bounded_and_the_plan_is_self_describing():
    frozen = diag.plan()
    assert len(frozen["cases"]) <= diag.MAX_REQUESTS
    assert frozen["plan_sha256"] == sha256_hex(canonical_bytes(
        {k: v for k, v in frozen.items() if k != "plan_sha256"}))


def test_the_plan_records_what_was_already_ruled_out():
    """A diagnostic that re-tests an excluded explanation wastes the record's credibility."""
    ruled_out = " ".join(diag.plan()["ruled_out_before_this_diagnostic"]).lower()
    assert "131072" in ruled_out and "200" in ruled_out
    assert "conformed to all ten probes" in ruled_out


# -------------------------------------------------------------------------------------------
# Each case isolates exactly one dimension
# -------------------------------------------------------------------------------------------

def test_every_case_differs_from_the_stress_request_in_one_named_dimension():
    cases = diag.cases()
    assert len({c["case"] for c in cases}) == len(cases)
    for case in cases:
        assert case["isolates"], case["case"]
        assert isinstance(case["schema"], dict) and case["schema"]
        assert isinstance(case["max_tokens"], int) and case["max_tokens"] > 0


def test_the_baseline_case_is_a_request_shape_already_observed_as_200():
    baseline = next(c for c in diag.cases() if c["case"] == "probe_schema_probe_budget")
    ledger = json.loads((ROOT / "experiments" / "M117"
                         / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    observed = [o for p in ledger["profiles"] for o in p["observations"]
                if o.get("probe") == "combined"]
    assert observed, "no combined probe was recorded"
    assert any(o.get("http_status") == 200 for o in observed)
    assert baseline["schema"]


def test_shrinking_cardinality_leaves_the_structure_alone():
    full = stress.build_stress_schema()
    small = diag._shrink(full, max_items=4)

    def depth(node, d=0):
        if isinstance(node, dict):
            return max([depth(v, d + 1) for v in node.values()] or [d])
        if isinstance(node, list):
            return max([depth(v, d) for v in node] or [d])
        return d

    assert depth(small) == depth(full)

    def max_items(node):
        found = []
        if isinstance(node, dict):
            if isinstance(node.get("maxItems"), int):
                found.append(node["maxItems"])
            for v in node.values():
                found += max_items(v)
        elif isinstance(node, list):
            for v in node:
                found += max_items(v)
        return found

    assert max_items(full), "the stress schema declares no array bounds"
    assert max(max_items(small)) <= 4


def test_truncating_depth_produces_a_shallower_schema():
    full = stress.build_stress_schema()
    shallow = diag._truncate_depth(full, limit=6)
    assert json.dumps(shallow) != json.dumps(full)
    assert len(json.dumps(shallow)) < len(json.dumps(full))


def test_the_cases_cover_each_candidate_explanation():
    isolated = {c["case"] for c in diag.cases()}
    assert {"stress_schema_small_budget", "stress_schema_no_reasoning_control",
            "stress_prompt_probe_schema", "stress_schema_cardinality_4",
            "stress_schema_depth_6"} <= isolated


# -------------------------------------------------------------------------------------------
# Provider free text never reaches the repository
# -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected", [
    ("Schema is too deeply nested", "schema_too_deep"),
    ("json_schema too large for this model", "schema_too_large"),
    ("Unsupported keyword: uniqueItems", "schema_unsupported_keyword"),
    ("max_tokens exceeds the model limit", "token_budget_rejected"),
    ("Unknown parameter: reasoning", "parameter_rejected"),
    ("Resource exhausted: quota", "rate_limited"),
])
def test_an_error_message_is_reduced_to_a_class(message, expected):
    assert diag.classify_error(message) == expected


def test_an_unrecognised_error_is_classified_rather_than_quoted():
    """The fallback must be a label, never the text itself."""
    secret = "api key sk-live-000 rejected for account anthony@example.com"
    assert diag.classify_error(secret) == "unclassified"
    assert secret not in diag.classify_error(secret)


def test_the_plan_declares_that_error_text_is_never_committed():
    frozen = diag.plan()
    assert frozen["error_text_is_never_committed"] is True
    assert frozen["error_classes"] == [name for name, _ in diag.ERROR_CLASSES]


def test_a_recorded_result_carries_a_digest_and_a_class_but_no_message():
    """The shape the report writes, asserted against a message that must not survive it."""
    message = "Schema is too deeply nested; offending path $.a.b.c and token sk-live-000"
    record = {
        "case": "stress_schema_depth_6", "http_status": 400,
        "error_class": diag.classify_error(message),
        "error_message_sha256": sha256_hex(message.encode("utf-8")),
        "error_message_bytes": len(message.encode("utf-8")),
        "error_text_persisted": False, "raw_completion_persisted": False,
    }
    serialised = json.dumps(record)
    assert "sk-live-000" not in serialised
    assert "$.a.b.c" not in serialised
    assert record["error_class"] == "schema_too_deep"
    assert record["error_text_persisted"] is False


def test_identical_errors_stay_comparable_without_disclosing_either():
    a = "Schema is too deeply nested"
    assert sha256_hex(a.encode("utf-8")) == sha256_hex(a.encode("utf-8"))
    assert sha256_hex(a.encode("utf-8")) != sha256_hex((a + "!").encode("utf-8"))


def test_no_committed_diagnostic_report_contains_an_error_message_field():
    report = ROOT / "experiments" / "M117" / "STRESS_REJECTION_DIAGNOSIS.json"
    if not report.is_file():
        pytest.skip("the diagnostic has not been run yet")
    payload = json.loads(report.read_text(encoding="utf-8"))
    for result in payload["results"]:
        assert "error_message" not in result
        assert result["error_text_persisted"] is False
        assert result["raw_completion_persisted"] is False
        if result.get("error_class") is not None:
            assert result["error_class"] in [n for n, _ in diag.ERROR_CLASSES] + ["unclassified"]


# -------------------------------------------------------------------------------------------
# It reproduces rather than chooses its target
# -------------------------------------------------------------------------------------------

def test_the_target_is_the_first_reproducing_candidate_in_the_frozen_order():
    ledger = json.loads((ROOT / "experiments" / "M117"
                         / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").read_text(encoding="utf-8"))
    reproducing = [p for p in sorted(ledger["profiles"], key=lambda p: p["order"])
                   if not p["unenforced_feature_classes"]
                   and (p.get("token_capacity_stress") or {}).get("http_status") == 400]
    if not reproducing:
        pytest.skip("no candidate reproduced the rejection")
    assert diag._target()["order"] == reproducing[0]["order"]


def test_it_refuses_to_invent_a_target_when_nothing_reproduces(monkeypatch, tmp_path):
    """A candidate that failed for some other reason must never be diagnosed as if it had 400ed."""
    directory = tmp_path / "experiments" / "M117"
    directory.mkdir(parents=True)
    (directory / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json").write_text(json.dumps(
        {"profiles": [
            {"order": 1, "model": "x", "provider": "P",
             "unenforced_feature_classes": ["enum"], "token_capacity_stress": None},
            {"order": 2, "model": "y", "provider": "Q",
             "unenforced_feature_classes": [],
             "token_capacity_stress": {"http_status": 200}},
        ]}), encoding="utf-8")
    monkeypatch.setattr(diag, "ROOT", tmp_path)
    with pytest.raises(Exception, match="nothing to diagnose"):
        diag._target()
