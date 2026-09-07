"""Offline adversarial tests for the prospective M125/H70 readiness instrument.

No test in this module sends a network request. One temporary test at the bottom intentionally
fails on the first implementation commit to print the exact committed source manifest; it is
removed once PROTOCOL.json has been frozen from those bytes.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from metamorphosis import m116_schema as schema_tools
from metamorphosis import m122_carrier_contract as contract
from metamorphosis import m125_capability_probes as probes
from metamorphosis import m125_protocol_gate as gate
from metamorphosis import m125_stress_schema as stress
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from scripts import run_m125_readiness as readiness

ROOT = Path(__file__).resolve().parents[1]

IDENTITY = {
    "model": "deepseek/deepseek-v4-flash-0731",
    "provider": "OpenInference",
    "openrouter_metadata": {
        "requested": "deepseek/deepseek-v4-flash-0731",
        "strategy": "direct",
        "attempt": 1,
        "endpoints": {"available": [{
            "provider": "OpenInference",
            "model": "deepseek/deepseek-v4-flash-20260731",
            "selected": True,
        }]},
    },
}

_PATTERN_VALUES = {
    r"^zq[0-9]{4}$": "zq0000",
    r"^[a-z][a-z0-9_]{1,11}$": "alpha_one",
    r"^[a-z][a-z0-9]{1,7}$": "alpha1",
}


def conforming(schema):
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        return {name: conforming(child) for name, child in (schema.get("properties") or {}).items()}
    if kind == "array":
        count = max(1, int(schema.get("minItems", 1)))
        count = min(count, int(schema.get("maxItems", count)))
        return [conforming(schema.get("items") or {"type": "string", "maxLength": 2})
                for _ in range(count)]
    if kind == "integer":
        return int(schema.get("minimum", 0))
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    if kind == "string":
        pattern = schema.get("pattern")
        if pattern:
            value = _PATTERN_VALUES.get(pattern)
            assert value is not None and re.fullmatch(pattern, value)
            return value
        return "ok"
    raise AssertionError("unsupported test schema %r" % kind)


def modules():
    return readiness._instrument_modules()


def protocol_record():
    m = modules()
    census = schema_tools.census(contract.candidate_schema())
    matrix = probes.build_matrix(census)
    record = {
        "schema": "m125-readiness-protocol-v1",
        "milestone": "M125",
        "hypothesis": "H70",
        "development": True,
        "scientific_observation": False,
        "probe_names": [row["name"] for row in matrix],
        "required_feature_classes": probes.required_feature_classes(census),
        "probe_max_tokens": readiness.PROBE_MAX_TOKENS,
        "stress_max_tokens": readiness.STRESS_MAX_TOKENS,
        "calibration_queue": list(stress.CALIBRATION_QUEUE),
        "minimum_completion_tokens": stress.MIN_COMPLETION_TOKENS,
        "maximum_completion_tokens": stress.MAX_COMPLETION_TOKENS,
        "retryable_statuses": list(readiness.RETRYABLE_STATUSES),
        "max_retries_per_logical_step": readiness.MAX_RETRIES,
        "endpoint": contract.GENERATOR_ENDPOINT,
        "requested_model": m["fixed"].REQUESTED_MODEL,
        "provider": m["fixed"].PROVIDER,
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "physical_request_budget": 42,
        "inherited_delivery_spent": 4,
        "interpreting_source_manifest": {},
        "historical_token_observations_used_for_calibration": False,
        "refit_after_final_observation_permitted": False,
        "protocol_sha256": "",
    }
    record["protocol_sha256"] = gate.protocol_payload_sha256(record)
    return record


class FakeRoute:
    def __init__(self, *, first_empty=False, always_empty=False):
        self.first_empty = first_empty
        self.always_empty = always_empty
        self.calls = []

    def __call__(self, _url, *, method="POST", body=b"", timeout=900):
        request = json.loads(body.decode("utf-8"))
        declaration = request["response_format"]["json_schema"]
        name, schema = declaration["name"], declaration["schema"]
        self.calls.append(name)
        if self.always_empty or (self.first_empty and len(self.calls) == 1):
            return {"status": 200, "body": {}, "response_headers": {}}
        instance = conforming(schema)
        if name.startswith("m125_calibration_"):
            stations = int(name.rsplit("_", 1)[1])
            tokens = stations * 1000
        elif name.startswith("m125_final_"):
            stations = int(name.rsplit("_", 1)[1])
            tokens = stations * 1000
        else:
            tokens = 200
        output = dict(IDENTITY)
        output["choices"] = [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(instance)},
        }]
        output["usage"] = {
            "completion_tokens": tokens,
            "completion_tokens_details": {"reasoning_tokens": 0},
        }
        return {"status": 200, "body": output, "response_headers": {}}


# --------------------------------------------------------------------------------------
# Bounded probe matrix and complete feature coverage
# --------------------------------------------------------------------------------------


def test_every_required_feature_has_named_decisive_coverage_including_items():
    census = schema_tools.census(contract.candidate_schema())
    matrix = probes.build_matrix(census)
    mapping = probes.coverage_map(census, matrix)
    required = probes.required_feature_classes(census)
    assert "items" in required
    assert mapping["items"] == ["items"]
    assert all(mapping.get(feature) for feature in required)


def test_every_probe_has_a_finite_static_bound_below_the_safety_cap():
    matrix = probes.build_matrix(schema_tools.census(contract.candidate_schema()))
    assert matrix
    for row in matrix:
        assert 0 < row["max_compact_json_bytes"] < probes.PROBE_OUTPUT_SAFETY_CAP_TOKENS
        assert probes.max_compact_json_bytes(row["schema"]) == row["max_compact_json_bytes"]


def test_probe_matrix_is_non_carrier():
    probes.assert_non_carrier(probes.build_matrix(schema_tools.census(contract.candidate_schema())))


def test_unbounded_probe_string_is_refused():
    with pytest.raises(probes.ProbeError, match="maxLength"):
        probes.max_compact_json_bytes({"type": "string"})


# --------------------------------------------------------------------------------------
# Pinned stress and fresh-only sizing
# --------------------------------------------------------------------------------------


def _array_ranges(node, path=()):
    found = []
    if isinstance(node, dict):
        if node.get("type") == "array":
            found.append((path, node.get("minItems"), node.get("maxItems")))
        for key, value in node.items():
            found.extend(_array_ranges(value, path + (str(key),)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_array_ranges(value, path + (str(index),)))
    return found


def test_pinning_is_deterministic_and_leaves_the_census_bit_identical():
    proof = stress.pinning_proof(8)
    assert proof["census_bit_identical"] is True
    assert proof["census_before"] == proof["census_after"]
    schema = stress.build_stress_schema(8)
    for path, low, high in _array_ranges(schema):
        assert low == high, path


def test_upper_midpoint_rule_is_fixed():
    assert stress.upper_midpoint(1, 3) == 2
    assert stress.upper_midpoint(3, 4) == 4
    assert stress.upper_midpoint(0, 1) == 1
    assert stress.upper_midpoint(1, 4) == 3
    assert stress.upper_midpoint(2, 3) == 3


def _point(stations, tokens):
    return {"stations": stations, "completion_tokens": tokens, "answered": True,
            "finish_reason": "stop", "schema_conforms": True}


def test_fresh_8_16_32_calibration_derives_one_new_out_of_sample_size():
    derivation = stress.derive_final_size([_point(8, 8000), _point(16, 16000), _point(32, 32000)])
    assert derivation["final_stations"] == 42
    assert derivation["final_is_out_of_sample"] is True
    assert derivation["historical_token_observations_used"] is False
    assert derivation["refit_after_final_observation_permitted"] is False


def test_calibration_with_no_admissible_window_closes_instead_of_refitting():
    with pytest.raises(stress.StressError, match="no admissible"):
        stress.derive_final_size([_point(8, 4000), _point(16, 8000), _point(32, 200000)])


def test_old_or_missing_calibration_point_cannot_enter_the_fit():
    with pytest.raises(stress.StressError, match="exactly one fresh"):
        stress.derive_final_size([_point(8, 8000), _point(16, 16000), _point(24, 24000)])


# --------------------------------------------------------------------------------------
# One answered predicate, retry semantics and terminal request rejection
# --------------------------------------------------------------------------------------


def _answered_body(finish="stop", content="{}"):
    return {"status": 200, "body": {"choices": [{"finish_reason": finish,
                                                   "message": {"content": content}}]},
            "response_headers": {}}


def test_empty_200_and_missing_finish_are_unanswered_and_retryable():
    assert readiness.answered({"status": 200, "body": {}}) is False
    assert readiness.retryable_delivery({"status": 200, "body": {}}) is True
    missing = _answered_body(); missing["body"]["choices"][0].pop("finish_reason")
    assert readiness.answered(missing) is False
    assert readiness.retryable_delivery(missing) is True


def test_length_is_answered_and_not_retried():
    observed = _answered_body(finish="length", content="partial")
    assert readiness.answered(observed) is True
    assert readiness.retryable_delivery(observed) is False


def test_non_429_4xx_is_terminal_request_rejection_and_not_retried():
    observed = {"status": 400, "body": {"error": {}}, "response_headers": {}}
    assert readiness.deterministic_request_rejection(observed) is True
    assert readiness.retryable_delivery(observed) is False
    calls = []
    def transport(*_a, **_k):
        calls.append(1); return observed
    result = readiness._send(transport, "https://example.invalid", b"{}",
                             {"spent": 0, "limit": 9}, sleeper=lambda _x: None)
    assert result["status"] == 400
    assert len(calls) == 1


def test_retry_after_comes_from_response_headers_not_legacy_headers():
    slept = []
    delay = readiness._wait_before_retrying(
        {"response_headers": {"Retry-After": "7"}, "headers": {"retry-after": "99"}},
        0, sleeper=slept.append)
    assert delay == 7
    assert slept == [7]


def test_empty_200_is_retried_at_the_request_level():
    sequence = [
        {"status": 200, "body": {}, "response_headers": {}},
        _answered_body(),
    ]
    calls = []
    def transport(*_a, **_k):
        calls.append(1); return sequence.pop(0)
    result = readiness._send(transport, "https://example.invalid", b"{}",
                             {"spent": 0, "limit": 9}, sleeper=lambda _x: None)
    assert readiness.answered(result) is True
    assert len(calls) == 2


# --------------------------------------------------------------------------------------
# Temporary git repositories for HEAD/working-tree anti-rearm and manifest tests
# --------------------------------------------------------------------------------------


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True)


def _init_repo(root):
    _git(root, "init")
    _git(root, "config", "user.email", "m125-test@example.invalid")
    _git(root, "config", "user.name", "M125 Test")


def _commit_all(root, message="fixture"):
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")


def _delivery(protocol_sha="p", digest="d"):
    return {"schema": readiness.RESULT_SCHEMA, "milestone": "M125", "hypothesis": "H70",
            "development": True, "verdict": gate.DELIVERY_VERDICT,
            "protocol_sha256": protocol_sha, "result_sha256": digest}


def _terminal(verdict="not_ready_features"):
    return {"schema": readiness.RESULT_SCHEMA, "milestone": "M125", "hypothesis": "H70",
            "development": True, "verdict": verdict, "result_sha256": "terminal"}


def test_terminal_working_tree_result_refuses(tmp_path):
    _init_repo(tmp_path); _write_json(tmp_path / gate.RESULT_REL, _terminal())
    with pytest.raises(gate.GateError, match="terminal"):
        gate.inspect_anti_rearm(tmp_path)


def test_terminal_head_result_deleted_locally_still_refuses(tmp_path):
    _init_repo(tmp_path); path = tmp_path / gate.RESULT_REL; _write_json(path, _terminal()); _commit_all(tmp_path)
    path.unlink()
    with pytest.raises(gate.GateError, match="HEAD result"):
        gate.inspect_anti_rearm(tmp_path)


def test_terminal_head_result_replaced_locally_by_delivery_still_refuses(tmp_path):
    _init_repo(tmp_path); path = tmp_path / gate.RESULT_REL; _write_json(path, _terminal()); _commit_all(tmp_path)
    _write_json(path, _delivery())
    with pytest.raises(gate.GateError, match="HEAD result"):
        gate.inspect_anti_rearm(tmp_path)


def test_terminal_head_archive_deleted_locally_still_refuses(tmp_path):
    _init_repo(tmp_path); path = tmp_path / "experiments/M125/READINESS_ATTEMPT_01_not_ready_features.json"
    _write_json(path, _terminal()); _commit_all(tmp_path); path.unlink()
    with pytest.raises(gate.GateError, match="HEAD experiments/M125/READINESS_ATTEMPT"):
        gate.inspect_anti_rearm(tmp_path)


def test_terminal_head_archive_replaced_locally_by_delivery_still_refuses(tmp_path):
    _init_repo(tmp_path); path = tmp_path / "experiments/M125/READINESS_ATTEMPT_01_not_ready_features.json"
    _write_json(path, _terminal()); _commit_all(tmp_path); _write_json(path, _delivery())
    with pytest.raises(gate.GateError, match="terminal"):
        gate.inspect_anti_rearm(tmp_path)


def test_missing_verdict_on_any_existing_surface_fails_closed(tmp_path):
    _init_repo(tmp_path); _write_json(tmp_path / gate.RESULT_REL, {"milestone": "M125"})
    with pytest.raises(gate.GateError, match="missing/unrecognized verdict"):
        gate.inspect_anti_rearm(tmp_path)


def _make_manifest_fixture(root):
    _init_repo(root)
    manifest = {}
    for relative in gate.MINIMUM_MANIFEST_PATHS:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# %s\n" % relative, encoding="utf-8")
        manifest[relative] = gate.sha256(gate.normalized(path.read_bytes()))
    record = {
        "schema": "m125-readiness-protocol-v1", "milestone": "M125", "hypothesis": "H70",
        "development": True, "scientific_observation": False,
        "interpreting_source_manifest": manifest, "inherited_delivery_spent": 4,
        "protocol_sha256": "",
    }
    record["protocol_sha256"] = gate.protocol_payload_sha256(record)
    _write_json(root / gate.PROTOCOL_REL, record)
    _commit_all(root)
    return record


def test_dirty_manifest_listed_working_tree_source_refuses(tmp_path):
    protocol = _make_manifest_fixture(tmp_path)
    target = tmp_path / gate.MINIMUM_MANIFEST_PATHS[0]
    target.write_text(target.read_text(encoding="utf-8") + "# dirty\n", encoding="utf-8")
    with pytest.raises(gate.GateError, match="differs from HEAD"):
        gate.verify_source_manifest(tmp_path, protocol)


def test_missing_manifest_listed_working_tree_source_refuses(tmp_path):
    protocol = _make_manifest_fixture(tmp_path)
    (tmp_path / gate.MINIMUM_MANIFEST_PATHS[0]).unlink()
    with pytest.raises(gate.GateError, match="working-tree source is missing"):
        gate.verify_source_manifest(tmp_path, protocol)


def test_committed_source_change_after_freeze_invalidates_manifest(tmp_path):
    protocol = _make_manifest_fixture(tmp_path)
    target = tmp_path / gate.MINIMUM_MANIFEST_PATHS[0]
    target.write_text(target.read_text(encoding="utf-8") + "# committed drift\n", encoding="utf-8")
    _commit_all(tmp_path, "drift")
    with pytest.raises(gate.GateError, match="committed interpreting-source digest changed"):
        gate.verify_source_manifest(tmp_path, protocol)


def test_missing_network_authorization_blocks_before_credential_accessor(tmp_path, monkeypatch):
    _make_manifest_fixture(tmp_path)
    touched = []
    def secret():
        touched.append(True); raise AssertionError("credential accessor became reachable")
    monkeypatch.setattr(readiness, "_secret", secret)
    with pytest.raises(gate.GateError, match="no committed M125 DEVELOPMENT network authorization"):
        readiness.execute(tmp_path)
    assert touched == []


def test_future_network_authorization_must_bind_exact_protocol(tmp_path):
    protocol = _make_manifest_fixture(tmp_path)
    auth = {"schema": "m125-network-authorization-v1", "scope": "development_network_only",
            "protocol_sha256": "wrong", "authorizes_h70_scientific_generation": False}
    _write_json(tmp_path / gate.AUTHORIZATION_REL, auth); _commit_all(tmp_path, "authorization")
    with pytest.raises(gate.GateError, match="exact frozen protocol"):
        gate.load_network_authorization(tmp_path, protocol["protocol_sha256"])


# --------------------------------------------------------------------------------------
# Complete offline rehearsal and no-redraw journal
# --------------------------------------------------------------------------------------


def test_full_offline_fake_route_rehearsal_reaches_ready_without_science(tmp_path):
    protocol = protocol_record(); route = FakeRoute()
    result = readiness.run_with_transport(protocol, modules(), route, tmp_path,
                                          delivery_accounting={"spent": 4, "total": 6, "remaining": 2},
                                          sleeper=lambda _x: None)
    assert result["verdict"] == "ready" and result["ready"] is True
    assert result["fresh_sizing"]["final_stations"] == 42
    assert result["historical_token_observations_used_for_calibration"] is False
    assert result["qualifying_input_was_sent"] is False
    assert result["is_a_qualifying_call"] is False
    assert result["advances_a_generality_gate"] is False
    assert result["raw_completion_persisted"] is False
    assert "m125_readiness_items" in route.calls
    assert "m125_final_42" in route.calls


def test_completed_probe_is_never_redrawn_on_resume(tmp_path):
    protocol = protocol_record(); route = FakeRoute()
    journal = readiness._new_journal(protocol["protocol_sha256"])
    journal["steps"]["probe:enum"] = {
        "answered": True, "step": "probe:enum", "feature_class": "enum", "probe": "enum",
        "finish_reason": "stop", "schema_conforms": True, "completion_tokens": 1,
    }
    result = readiness.run_with_transport(protocol, modules(), route, tmp_path,
                                          initial_journal=journal,
                                          delivery_accounting={"spent": 4, "total": 6, "remaining": 2},
                                          sleeper=lambda _x: None)
    assert result["ready"] is True
    assert "m125_readiness_enum" not in route.calls


def test_delivery_failure_does_not_mark_unanswered_step_complete(tmp_path):
    protocol = protocol_record(); route = FakeRoute(always_empty=True)
    result = readiness.run_with_transport(protocol, modules(), route, tmp_path,
                                          delivery_accounting={"spent": 4, "total": 6, "remaining": 2},
                                          sleeper=lambda _x: None)
    assert result["verdict"] == gate.DELIVERY_VERDICT
    assert result["completed_logical_steps"] == []
    journal = json.loads((tmp_path / "STEP_JOURNAL.json").read_text(encoding="utf-8"))
    assert journal["steps"] == {}


# --------------------------------------------------------------------------------------
# Temporary first-pass manifest emitter
# --------------------------------------------------------------------------------------


def test_emit_exact_committed_m125_source_manifest_for_protocol_freeze():
    """Intentional one-run failure; replaced after PROTOCOL.json is committed."""
    manifest = {}
    for relative in gate.MINIMUM_MANIFEST_PATHS:
        committed = gate.head_blob(ROOT, relative)
        assert committed is not None, relative
        manifest[relative] = gate.sha256(gate.normalized(committed))
    pytest.fail("M125_INTERPRETING_SOURCE_MANIFEST=" + json.dumps(manifest, sort_keys=True))
