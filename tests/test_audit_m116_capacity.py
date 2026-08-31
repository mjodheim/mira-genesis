"""Adversarial tests for the M116 DEVELOPMENT capacity stress instrument.

These tests exercise only synthetic local observations. They never call OpenRouter and never use a
carrier-bank payload as a model input.
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import pytest

from scripts import audit_m116_capacity as capacity


def _consignments() -> list[dict]:
    """A synthetic instance satisfying the census-dominating stress schema exactly."""

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
        {
            "docket": "dock_%d" % index,
            "assayer": "asy%d" % (index % 9),
            "status": ["held", "cleared", "quarantined", "released"][index % 4],
            "moisture": index % 101,
            "priority": ["routine", "expedited", "critical"][index % 3],
            "net_masses": [index * 7 % 50001, index * 11 % 50001],
            "insured": bool(index % 2),
            "tariff_codes": ["tc%d" % (index % 90), "td%d" % (index % 90)],
            "parcels": [parcel(index), parcel(index + 1)],
            "routing": {
                "origin": "org_%d" % index, "destination": "dst_%d" % index,
                "legs": [leg(index), leg(index + 1)], "bonded": bool(index % 2),
            },
        }
        for index in range(capacity.CONSIGNMENTS)
    ]


def _router_metadata() -> dict:
    return {
        "requested": capacity.MODEL,
        "strategy": "direct",
        "attempt": 1,
        "is_byok": False,
        "endpoints": {
            "total": 30,
            "available": [
                {
                    "provider": capacity.PROVIDER,
                    "model": capacity.CANONICAL_CHECKPOINT,
                    "selected": True,
                }
            ],
        },
        "attempts": [],
        "pipeline": [],
    }


def _materialized_observation(
    *,
    completion_tokens: int = 40000,
    finish_reason: str = "stop",
    content: str | None = None,
    reasoning_tokens: int | None = 0,
    reasoning_content: str | None = None,
    provider: str = capacity.PROVIDER,
    model: str = capacity.MODEL,
    router_metadata: dict | None = None,
) -> dict:
    if content is None:
        content = json.dumps(
            {"consignments": _consignments()}, separators=(",", ":"), sort_keys=True
        )
    message: dict = {"content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    usage: dict = {"completion_tokens": completion_tokens}
    if reasoning_tokens is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "status": 200,
        "headers": {},
        "response_sha256": "a" * 64,
        "response_bytes": 200000,
        "transport_failure_class": None,
        "model_execution_cannot_be_excluded": False,
        "body": {
            "model": model,
            "provider": provider,
            "openrouter_metadata": router_metadata or _router_metadata(),
            "choices": [{"finish_reason": finish_reason, "message": message}],
            "usage": usage,
        },
    }


def _empty_observation(status: int) -> dict:
    return {
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:00:01Z",
        "status": status,
        "headers": {},
        "response_sha256": "b" * 64,
        "response_bytes": 20,
        "transport_failure_class": None,
        "model_execution_cannot_be_excluded": False,
        "body": {},
    }


def _sandbox(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    report = tmp_path / "CAPACITY_STRESS_DEVELOPMENT.json"
    ledger = tmp_path / "CAPACITY_STRESS_DEVELOPMENT_LEDGER.json"
    lock = tmp_path / "capacity.lock"
    monkeypatch.setattr(capacity, "REPORT_PATH", report)
    monkeypatch.setattr(capacity, "LEDGER_PATH", ledger)
    monkeypatch.setattr(capacity, "LOCK_PATH", lock)
    monkeypatch.setattr(capacity, "_secret", lambda: "synthetic-test-secret")
    return report, ledger, lock


def test_candidate_request_controls_are_exact():
    body = capacity.REQUEST_BODY
    assert body["model"] == "deepseek/deepseek-v4-flash-0731"
    assert body["provider"] == {
        "only": ["Alibaba"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }
    assert body["reasoning"] == {"effort": "none"}
    assert body["max_tokens"] == 131072
    assert body["seed"] == 0
    assert body["stream"] is False
    assert body["temperature"] == 1.0
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True


def test_stress_input_is_not_any_closed_qualifying_input():
    capacity._assert_nonqualifying()
    stress = capacity.STRESS_INPUT.strip()
    for path in capacity.QUALIFYING_INPUT_PATHS:
        if path.is_file():
            qualifying = path.read_text(encoding="utf-8").strip()
            assert stress != qualifying
            assert stress not in qualifying
            assert qualifying not in stress


def test_stress_schema_contains_no_carrier_vocabulary():
    serialized = json.dumps(capacity.STRESS_SCHEMA, sort_keys=True)
    for forbidden in capacity.CARRIER_SCHEMA_VOCABULARY:
        assert f'"{forbidden}"' not in serialized


def test_strict_payload_accepts_exact_synthetic_shape():
    content = json.dumps({"consignments": _consignments()}, separators=(",", ":"))
    holds, digest = capacity._strict_payload_holds(content)
    assert holds is True
    assert isinstance(digest, str) and len(digest) == 64


@pytest.mark.parametrize(
    "mutation",
    [
        "too_few_consignments",
        "extra_key",
        "missing_key",
        "below_minimum",
        "above_maximum",
        "boolean",
        "bad_enum",
        "bad_pattern",
        "shallow_nesting",
    ],
)
def test_strict_payload_rejects_shape_and_value_drift(mutation: str):
    items = _consignments()
    if mutation == "too_few_consignments":
        items.pop()
    elif mutation == "extra_key":
        items[0]["surplus"] = 1
    elif mutation == "missing_key":
        del items[0]["insured"]
    elif mutation == "below_minimum":
        items[0]["moisture"] = -1
    elif mutation == "above_maximum":
        items[0]["moisture"] = 101
    elif mutation == "boolean":
        items[0]["moisture"] = True  # type: ignore[assignment]
    elif mutation == "bad_enum":
        items[0]["status"] = "not_a_status"
    elif mutation == "bad_pattern":
        items[0]["docket"] = "Bad Docket!"
    elif mutation == "shallow_nesting":
        items[0]["parcels"][0]["samples"][0]["assays"] = []
    holds, digest = capacity._strict_payload_holds(
        json.dumps({"consignments": items}, separators=(",", ":"))
    )
    assert holds is False
    assert digest is None


def test_capacity_gate_passes_only_above_old_ceiling():
    result = capacity.evaluate_terminal_observation(
        _materialized_observation(completion_tokens=40000)
    )
    assert result["gate_holds"] is True
    assert result["checks"]["completion_exceeds_m115_ceiling"] is True
    assert result["checks"]["reasoning_response_has_zero_tokens"] is True
    assert result["synthetic_consignments"] == capacity.CONSIGNMENTS
    assert result["identity_attestation"]["holds"] is True
    assert result["observed_selected_checkpoint"] == capacity.CANONICAL_CHECKPOINT

    boundary = capacity.evaluate_terminal_observation(
        _materialized_observation(
            completion_tokens=capacity.OLD_M115_MAX_TOKENS
        )
    )
    assert boundary["gate_holds"] is False
    assert boundary["checks"]["completion_exceeds_m115_ceiling"] is False


def test_capacity_gate_rejects_invalid_json():
    result = capacity.evaluate_terminal_observation(
        _materialized_observation(content='{"rows":[')
    )
    assert result["gate_holds"] is False
    assert result["checks"]["strict_output_parsed"] is False
    assert result["synthetic_payload_sha256"] is None


def test_capacity_gate_rejects_non_stop_finish():
    result = capacity.evaluate_terminal_observation(
        _materialized_observation(finish_reason="length")
    )
    assert result["gate_holds"] is False
    assert result["checks"]["finish_reason_stop"] is False


def test_capacity_gate_requires_positive_zero_reasoning_telemetry():
    absent = capacity.evaluate_terminal_observation(
        _materialized_observation(reasoning_tokens=None)
    )
    assert absent["gate_holds"] is False
    assert absent["reasoning_tokens"] is None
    assert absent["checks"]["reasoning_response_has_zero_tokens"] is False

    exposed = capacity.evaluate_terminal_observation(
        _materialized_observation(
            reasoning_tokens=1, reasoning_content="hidden work"
        )
    )
    assert exposed["gate_holds"] is False
    assert exposed["checks"]["reasoning_response_has_zero_tokens"] is False


def test_capacity_gate_rejects_identity_substitution_and_records_observed_checkpoint():
    metadata = _router_metadata()
    metadata["endpoints"]["available"][0]["model"] = "deepseek/another-checkpoint"
    result = capacity.evaluate_terminal_observation(
        _materialized_observation(router_metadata=metadata)
    )
    assert result["gate_holds"] is False
    assert result["checks"]["runtime_identity_holds"] is False
    assert result["checks"]["canonical_checkpoint_exact"] is False
    assert result["observed_selected_checkpoint"] == "deepseek/another-checkpoint"


def test_retry_is_only_explicit_429_without_execution_evidence():
    retryable = capacity._safe_nonmaterialized_attempt(_empty_observation(429), 1)
    assert retryable["retry_permitted"] is True
    assert retryable["generation_id_present"] is False

    non429 = capacity._safe_nonmaterialized_attempt(_empty_observation(503), 1)
    assert non429["retry_permitted"] is False

    executed = _empty_observation(429)
    executed["body"] = {
        "choices": [{"finish_reason": "length", "message": {"content": ""}}],
        "usage": {"completion_tokens": 10},
    }
    ambiguous = capacity._safe_nonmaterialized_attempt(executed, 1)
    assert ambiguous["retry_permitted"] is False
    assert ambiguous["model_execution_cannot_be_excluded"] is True

    generation = _empty_observation(429)
    generation["headers"] = {"x-generation-id": "gen-synthetic-123"}
    generation_ambiguous = capacity._safe_nonmaterialized_attempt(generation, 1)
    assert generation_ambiguous["generation_id_present"] is True
    assert generation_ambiguous["model_execution_cannot_be_excluded"] is True
    assert generation_ambiguous["retry_permitted"] is False
    assert "gen-synthetic-123" not in json.dumps(generation_ambiguous)


def test_request_converts_post_send_exception_to_ambiguous_terminal_observation(
    monkeypatch,
):
    class BrokenConnection:
        def request(self, *_args, **_kwargs):
            raise TimeoutError("simulated post-call transport ambiguity")

        def close(self):
            pass

    monkeypatch.setattr(capacity, "_secret", lambda: "synthetic-test-secret")
    monkeypatch.setattr(
        capacity,
        "_connection",
        lambda _url, _timeout: (
            BrokenConnection(),
            urllib.parse.urlsplit(capacity.ENDPOINT),
        ),
    )

    observed = capacity._request(timeout=1)

    assert observed["transport_failure_class"] == "ambiguous_transport_failure"
    assert observed["model_execution_cannot_be_excluded"] is True
    assert observed["status"] is None
    assert observed["body"] == {}


def test_execution_lock_refuses_competing_process_before_network(
    monkeypatch, tmp_path: Path
):
    _sandbox(monkeypatch, tmp_path)
    monkeypatch.setattr(
        capacity,
        "_request",
        lambda: pytest.fail("network must not be reached by competing execution"),
    )

    with capacity._exclusive_audit_lock():
        with pytest.raises(capacity.CapacityAuditError, match="execution lock"):
            capacity.execute()


def test_execute_persists_ambiguous_transport_failure_and_refuses_redraw(
    monkeypatch, tmp_path: Path
):
    report_path, ledger_path, _lock = _sandbox(monkeypatch, tmp_path)
    ambiguous = capacity._transport_failure_observation(
        started_at="2026-08-31T00:00:00Z",
        request_call_began=True,
    )
    calls = 0

    def response():
        nonlocal calls
        calls += 1
        return ambiguous

    monkeypatch.setattr(capacity, "_request", response)
    monkeypatch.setattr(
        capacity.time, "sleep", lambda _seconds: pytest.fail("must not retry")
    )

    report = capacity.execute()

    assert calls == 1
    assert report["gate_holds"] is False
    assert (
        report["terminal_observation"]["terminal_failure"]
        == "ambiguous_transport_failure"
    )
    assert (
        report["terminal_observation"]["model_execution_cannot_be_excluded"]
        is True
    )
    assert report_path.is_file()
    assert ledger_path.is_file()

    with pytest.raises(capacity.CapacityAuditError, match="already exists"):
        capacity.execute()
    assert calls == 1


def test_interrupted_in_flight_attempt_becomes_terminal_without_redraw(
    monkeypatch, tmp_path: Path
):
    report_path, ledger_path, _lock = _sandbox(monkeypatch, tmp_path)
    calls = 0

    def crash():
        nonlocal calls
        calls += 1
        raise KeyboardInterrupt("simulated process death after slot reservation")

    monkeypatch.setattr(capacity, "_request", crash)

    with pytest.raises(KeyboardInterrupt):
        capacity.execute()

    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted["state"] == "in_flight"
    assert len(persisted["attempts"]) == 1
    assert persisted["attempts"][0]["state"] == "in_flight"
    assert not report_path.exists()

    monkeypatch.setattr(
        capacity,
        "_request",
        lambda: pytest.fail("restart must not redraw an in-flight attempt"),
    )
    report = capacity.execute()

    assert calls == 1
    assert report["gate_holds"] is False
    assert (
        report["terminal_observation"]["terminal_failure"]
        == "interrupted_in_flight_attempt"
    )
    assert report["terminal_observation"]["model_execution_cannot_be_excluded"] is True
    assert len(report["attempts"]) == 1


def test_retryable_429_is_durable_before_wait_and_resumes_same_budget(
    monkeypatch, tmp_path: Path
):
    _report_path, ledger_path, _lock = _sandbox(monkeypatch, tmp_path)
    calls = 0

    def first_response():
        nonlocal calls
        calls += 1
        return _empty_observation(429)

    monkeypatch.setattr(capacity, "_request", first_response)
    monkeypatch.setattr(
        capacity.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(
            KeyboardInterrupt("simulated death during retry wait")
        ),
    )

    with pytest.raises(KeyboardInterrupt):
        capacity.execute()

    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted["state"] == "retry_wait"
    assert len(persisted["attempts"]) == 1
    assert persisted["attempts"][0]["state"] == "retryable_429"
    assert persisted["attempts"][0]["retry_permitted"] is True
    assert "retry_not_before" in persisted["attempts"][0]

    monkeypatch.setattr(capacity, "_sleep_remaining", lambda _value: None)

    def second_response():
        nonlocal calls
        calls += 1
        return _materialized_observation()

    monkeypatch.setattr(capacity, "_request", second_response)
    report = capacity.execute()

    assert calls == 2
    assert report["gate_holds"] is True
    assert len(report["attempts"]) == 2
    assert report["attempts"][0]["attempt_index"] == 1
    assert report["attempts"][0]["state"] == "retryable_429"
    assert report["attempts"][1]["attempt_index"] == 2
    assert report["attempts"][1]["state"] == "materialized_stress_response"


def test_execute_allows_two_429s_then_one_materialization(
    monkeypatch, tmp_path: Path
):
    report_path, ledger_path, _lock = _sandbox(monkeypatch, tmp_path)
    observations = iter(
        [
            _empty_observation(429),
            _empty_observation(429),
            _materialized_observation(),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(capacity, "_request", lambda: next(observations))
    monkeypatch.setattr(
        capacity.time, "sleep", lambda seconds: sleeps.append(seconds)
    )

    report = capacity.execute()

    assert report["gate_holds"] is True
    assert len(report["attempts"]) == 3
    assert sleeps == [
        capacity.RETRY_WAIT_SECONDS,
        capacity.RETRY_WAIT_SECONDS,
    ]
    assert report["qualifying_calls"] == 0
    persisted = report_path.read_text(encoding="utf-8")
    ledger = ledger_path.read_text(encoding="utf-8")
    for evidence in (persisted, ledger):
        assert '"consignments"' not in evidence
        assert '"docket"' not in evidence
        assert "dock_0" not in evidence
        assert '"raw_completion_persisted":false' in evidence


def test_execute_stops_on_first_non429_without_retry(
    monkeypatch, tmp_path: Path
):
    _sandbox(monkeypatch, tmp_path)
    calls = 0

    def response():
        nonlocal calls
        calls += 1
        return _empty_observation(503)

    monkeypatch.setattr(capacity, "_request", response)
    monkeypatch.setattr(
        capacity.time, "sleep", lambda _seconds: pytest.fail("must not sleep")
    )

    report = capacity.execute()

    assert calls == 1
    assert report["gate_holds"] is False
    assert (
        report["terminal_observation"]["terminal_failure"]
        == "nonmaterialized_terminal_response"
    )


def test_execute_exhausts_exactly_three_retryable_429s(
    monkeypatch, tmp_path: Path
):
    _sandbox(monkeypatch, tmp_path)
    calls = 0
    sleeps: list[float] = []

    def response():
        nonlocal calls
        calls += 1
        return _empty_observation(429)

    monkeypatch.setattr(capacity, "_request", response)
    monkeypatch.setattr(
        capacity.time, "sleep", lambda seconds: sleeps.append(seconds)
    )

    report = capacity.execute()

    assert calls == capacity.MAX_PHYSICAL_ATTEMPTS == 3
    assert sleeps == [
        capacity.RETRY_WAIT_SECONDS,
        capacity.RETRY_WAIT_SECONDS,
    ]
    assert report["gate_holds"] is False
    assert (
        report["terminal_observation"]["terminal_failure"]
        == "development_capacity_rejections_exhausted"
    )


def test_terminal_ledger_reconstructs_report_without_network(
    monkeypatch, tmp_path: Path
):
    report_path, ledger_path, _lock = _sandbox(monkeypatch, tmp_path)
    monkeypatch.setattr(capacity, "_request", lambda: _empty_observation(503))

    first = capacity.execute()
    assert first["gate_holds"] is False
    assert report_path.exists()
    report_path.unlink()

    monkeypatch.setattr(
        capacity,
        "_request",
        lambda: pytest.fail("terminal ledger must reconstruct without network"),
    )
    second = capacity.execute()

    assert second == first
    assert ledger_path.exists()
    assert report_path.exists()


def test_execute_refuses_to_redraw_existing_report(
    monkeypatch, tmp_path: Path
):
    report_path, _ledger_path, _lock = _sandbox(monkeypatch, tmp_path)
    report_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        capacity, "_request", lambda: pytest.fail("network must not be reached")
    )

    with pytest.raises(capacity.CapacityAuditError, match="already exists"):
        capacity.execute()
