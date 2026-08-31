"""End-to-end lifecycle of the DEVELOPMENT capacity audit, with no network.

The audit spends a bounded, non-redrawable attempt budget, and a failed or exhausted audit may not
be redrawn under the merged candidate. Unit tests of its predicates are therefore not enough: the
whole `execute()` path is driven here against a stubbed endpoint, so that the one real run happens
against apparatus that has already been through its own lifecycle.

Nothing here reaches the network. `_request` is replaced in every test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m116_stress_schema as stress
from scripts import audit_m116_capacity as capacity

ROOT = Path(__file__).resolve().parents[1]


def _consignments() -> list[dict]:
    def assay(k: int) -> dict:
        return {"element": "au%d" % (k % 9), "grade": 1000 + (k % 8999),
                "method": "icp", "replicates": 1 + (k % 6), "certified": bool(k % 2)}

    def sample(k: int) -> dict:
        return {"label": "samp_%d" % (k % 1000), "depth": 1 + (k % 400),
                "assays": [assay(k), assay(k + 1)], "retained": bool(k % 3)}

    def parcel(k: int) -> dict:
        return {"reference": "parc_%d" % (k % 1000), "tonnes": 1 + (k % 5000),
                "grade_band": ["low", "medium", "high", "reject"][k % 4],
                "samples": [sample(k), sample(k + 1)],
                "seals": ["sl%d" % (k % 90), "sm%d" % (k % 90)]}

    def leg(k: int) -> dict:
        return {"carrier_mode": ["rail", "barge", "road", "conveyor"][k % 4],
                "hours": 1 + (k % 240), "distance_km": 1 + (k % 9000),
                "checkpoint": "chk_%d" % (k % 1000)}

    return [
        {"docket": "dock_%d" % i, "assayer": "asy%d" % (i % 9),
         "status": ["held", "cleared", "quarantined", "released"][i % 4],
         "moisture": i % 101, "priority": ["routine", "expedited", "critical"][i % 3],
         "net_masses": [i * 7 % 50001, i * 11 % 50001], "insured": bool(i % 2),
         "tariff_codes": ["tc%d" % (i % 90), "td%d" % (i % 90)],
         "parcels": [parcel(i), parcel(i + 1)],
         "routing": {"origin": "org_%d" % i, "destination": "dst_%d" % i,
                     "legs": [leg(i), leg(i + 1)], "bonded": bool(i % 2)}}
        for i in range(capacity.CONSIGNMENTS)
    ]


def _success_body(completion_tokens: int = 41203) -> dict:
    return {
        "model": capacity.MODEL,
        "provider": capacity.PROVIDER,
        "choices": [{"finish_reason": "stop",
                     "message": {"content": json.dumps({"consignments": _consignments()})}}],
        "usage": {"prompt_tokens": 400, "completion_tokens": completion_tokens,
                  "total_tokens": 400 + completion_tokens,
                  "completion_tokens_details": {"reasoning_tokens": 0}},
        "openrouter_metadata": {
            "requested": capacity.MODEL, "strategy": "direct", "attempt": 1, "is_byok": False,
            "endpoints": {"total": 30, "available": [
                {"provider": capacity.PROVIDER, "model": capacity.CANONICAL_CHECKPOINT,
                 "selected": True}]},
            "attempts": [], "pipeline": [],
        },
    }


def _observation(body: dict, status: int = 200) -> dict:
    return {"status": status, "body": body, "response_sha256": "a" * 64,
            "response_bytes": 1234, "started_at": "2026-09-01T00:00:00Z",
            "finished_at": "2026-09-01T00:04:00Z",
            "response_headers": {"x-generation-id": "gen-dev-0001"}}


@pytest.fixture()
def sandbox(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(capacity, "REPORT_PATH", tmp_path / "CAPACITY_STRESS_DEVELOPMENT.json")
    monkeypatch.setattr(capacity, "LEDGER_PATH", tmp_path / "LEDGER.json")
    monkeypatch.setattr(capacity, "LOCK_PATH", tmp_path / "lock")
    monkeypatch.setenv(capacity.SECRET_VARIABLE, "test-key-never-real")
    monkeypatch.setattr(capacity, "RETRY_WAIT_SECONDS", 0)
    return tmp_path


def test_a_passing_audit_writes_a_holding_gate_and_no_raw_completion(sandbox, monkeypatch):
    monkeypatch.setattr(capacity, "_request", lambda **k: _observation(_success_body()))
    report = capacity.execute()
    assert report["gate_holds"] is True
    assert len(report["attempts"]) == 1

    persisted = (sandbox / "CAPACITY_STRESS_DEVELOPMENT.json").read_text("utf-8")
    assert '"gate_holds":true' in persisted.replace(" ", "")
    # The synthetic completion must never be persisted. The report legitimately names the
    # *count* (`synthetic_consignments`) and a digest of the payload; neither is content, so the
    # assertion targets values the completion actually carried.
    for value in ("dock_0", "asy0", "parc_0", "samp_0", "chk_0", "\"cleared\"", "\"icp\""):
        assert value not in persisted, "completion content leaked: %s" % value
    assert "test-key-never-real" not in persisted
    assert '"raw_completion_persisted":false' in persisted.replace(" ", "")


def test_an_audit_below_the_old_ceiling_does_not_hold(sandbox, monkeypatch):
    monkeypatch.setattr(
        capacity, "_request",
        lambda **k: _observation(_success_body(completion_tokens=capacity.OLD_M115_MAX_TOKENS)))
    report = capacity.execute()
    assert report["gate_holds"] is False


def test_a_truncated_development_completion_does_not_hold(sandbox, monkeypatch):
    body = _success_body()
    body["choices"][0]["finish_reason"] = "length"
    monkeypatch.setattr(capacity, "_request", lambda **k: _observation(body))
    report = capacity.execute()
    assert report["gate_holds"] is False


def test_reasoning_tokens_present_do_not_hold(sandbox, monkeypatch):
    body = _success_body()
    body["usage"]["completion_tokens_details"]["reasoning_tokens"] = 128
    monkeypatch.setattr(capacity, "_request", lambda **k: _observation(body))
    report = capacity.execute()
    assert report["gate_holds"] is False


def test_a_substituted_checkpoint_does_not_hold(sandbox, monkeypatch):
    body = _success_body()
    body["openrouter_metadata"]["endpoints"]["available"][0]["model"] = "someone/else-20260101"
    monkeypatch.setattr(capacity, "_request", lambda **k: _observation(body))
    report = capacity.execute()
    assert report["gate_holds"] is False


def test_the_audit_is_never_redrawn_once_a_report_exists(sandbox, monkeypatch):
    monkeypatch.setattr(capacity, "_request", lambda **k: _observation(_success_body()))
    capacity.execute()
    with pytest.raises(capacity.CapacityAuditError, match="not redrawn"):
        capacity.execute()


def test_a_non429_terminal_response_ends_the_audit_without_retry(sandbox, monkeypatch):
    calls = []

    def once(**kwargs):
        calls.append(1)
        return _observation({"error": {"code": "server_error"}}, status=503)

    monkeypatch.setattr(capacity, "_request", once)
    report = capacity.execute()
    assert report["gate_holds"] is False
    assert len(calls) == 1, "a non-429 terminal response must not be retried"


def test_a_429_without_execution_evidence_retries_within_the_frozen_budget(sandbox, monkeypatch):
    calls = []

    def flaky(**kwargs):
        calls.append(1)
        if len(calls) < 3:
            return _observation({"error": {"code": "rate_limited"}}, status=429)
        return _observation(_success_body())

    monkeypatch.setattr(capacity, "_request", flaky)
    report = capacity.execute()
    assert len(calls) == 3
    assert report["gate_holds"] is True


def test_the_budget_is_exhausted_after_three_physical_attempts(sandbox, monkeypatch):
    calls = []

    def always_429(**kwargs):
        calls.append(1)
        return _observation({"error": {"code": "rate_limited"}}, status=429)

    monkeypatch.setattr(capacity, "_request", always_429)
    report = capacity.execute()
    assert len(calls) == capacity.MAX_PHYSICAL_ATTEMPTS
    assert report["gate_holds"] is False


def test_no_credential_stops_the_audit_before_any_attempt(sandbox, monkeypatch):
    reached = []
    monkeypatch.delenv(capacity.SECRET_VARIABLE, raising=False)
    monkeypatch.setattr(capacity, "_request", lambda **k: reached.append(1) or _observation({}))
    with pytest.raises(capacity.CapacityAuditError, match="not set"):
        capacity.execute()
    assert reached == []


def test_the_real_stress_instance_satisfies_the_frozen_stress_schema():
    from metamorphosis import m116_schema as schema_tools

    holds, location, keyword = schema_tools.instance_is_valid(
        {"consignments": _consignments()}, stress.build_stress_schema())
    assert holds is True, "%s failed %s" % (location, keyword)
