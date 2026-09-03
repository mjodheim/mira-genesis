"""The M120 readiness gate, exercised before it is spent.

This gate is **single-use by construction**: once its result is committed at HEAD it can never be
re-armed, and deleting the file does not re-arm it either. It has also never run. Spending a
one-shot on code that has only been read is the M119 pattern exactly, so every branch that decides
its verdict is exercised here against a stubbed transport first.

The seam is the same one the DEVELOPMENT rehearsal uses on the generation runner: the network call
is replaced from outside and nothing else is. `plan`, `execute`, the probe loop, the stress, the
verdict ladder, the once-only guard, the budget and the record's information boundary are the real
code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from metamorphosis import m116_capability_probes as probes
from metamorphosis import m116_schema as schema_tools
from metamorphosis import m120_carrier_contract as contract
from metamorphosis import m120_stress_schema as stress
from metamorphosis.blind_bank_protocol import canonical_bytes
from scripts import run_m120_readiness as readiness

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------------------------
# A conforming instance for any schema in the probe vocabulary
# ---------------------------------------------------------------------------------------------

# Every pattern the probe matrix and the stress schema actually use, with a value built for it
# rather than guessed at. Each is checked against its own pattern below, so a wrong entry fails
# here instead of silently making a probe look enforced.
_PATTERN_VALUES = {
    r"^zq[0-9]{4}$": "zq0000",
    r"^[a-z][a-z0-9_]{1,11}$": "alpha_one",
    r"^[a-z][a-z0-9]{1,7}$": "alpha1",
}
for _pattern, _value in _PATTERN_VALUES.items():
    assert re.fullmatch(_pattern, _value), (_pattern, _value)


def _satisfy_pattern(pattern: str) -> str:
    """Build a value for a known pattern rather than guess at an arbitrary one."""
    if pattern in _PATTERN_VALUES:
        return _PATTERN_VALUES[pattern]
    raise AssertionError(
        "the probe matrix grew a pattern this test cannot satisfy: %r. Add a case rather than "
        "loosening the check, or the readiness gate goes back to being untested." % pattern)


def conforming(schema) -> object:
    """Build an instance the frozen validator accepts, over the probe schema vocabulary."""
    kind = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if kind == "object":
        return {name: conforming(child)
                for name, child in (schema.get("properties") or {}).items()}
    if kind == "array":
        item = schema.get("items") or {"type": "string"}
        count = max(int(schema.get("minItems", 1)), 1)
        count = min(count, int(schema.get("maxItems", count)))
        return [conforming(item) for _ in range(count)]
    if kind == "integer":
        low = schema.get("minimum")
        return int(low) if isinstance(low, int) else 0
    if kind == "boolean":
        return True
    if "pattern" in schema:
        return _satisfy_pattern(schema["pattern"])
    return "ok"


def test_the_generator_produces_instances_the_frozen_validator_accepts():
    """If this helper drifted, every test below would be measuring itself."""
    matrix = probes.build_matrix(schema_tools.census(contract.candidate_schema()))
    assert matrix, "the probe matrix is empty"
    for probe in matrix:
        ok, location, keyword = schema_tools.instance_is_valid(
            conforming(probe["schema"]), probe["schema"])
        assert ok, "%s: %s failed %s" % (probe["name"], location, keyword)
    ok, _, _ = schema_tools.instance_is_valid(
        conforming(stress.build_stress_schema()), stress.build_stress_schema())
    assert ok


# ---------------------------------------------------------------------------------------------
# The stubbed route
# ---------------------------------------------------------------------------------------------

IDENTITY = {
    "model": "deepseek/deepseek-v4-flash-0731",
    "provider": "OpenInference",
    "openrouter_metadata": {
        "requested": "deepseek/deepseek-v4-flash-0731",
        "strategy": "direct",
        "attempt": 1,
        "endpoints": {"available": [
            {"provider": "OpenInference",
             "model": "deepseek/deepseek-v4-flash-20260731",
             "selected": True}]},
    },
}


class FakeRoute:
    """Stands in for M117's transport. Records what was sent; decides nothing."""

    def __init__(self, *, break_identity=False, break_probe=None, reasoning_tokens=0,
                 stress_tokens=40000, statuses=None):
        self.break_identity = break_identity
        self.break_probe = break_probe
        self.reasoning_tokens = reasoning_tokens
        self.stress_tokens = stress_tokens
        self.statuses = list(statuses or [])
        self.sent: list[str] = []
        self.COMPLETIONS_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def _now(self):
        return "2026-09-03T00:00:00Z"

    def _http(self, url, *, method="POST", body=b"", timeout=900):
        request = json.loads(body.decode("utf-8"))
        declared = request["response_format"]["json_schema"]
        name, schema = declared["name"], declared["schema"]
        self.sent.append(name)
        if self.statuses:
            status = self.statuses.pop(0)
            if status != 200:
                return {"status": status, "body": {"error": {"code": status}}}
        is_stress = name == stress.STRESS_SCHEMA_NAME
        instance = conforming(schema)
        if self.break_probe and self.break_probe in name:
            # A completion the schema refuses: the route did not enforce that class.
            instance = {"unexpected_key_the_schema_forbids": "x"}
        body_out = dict(IDENTITY)
        if self.break_identity:
            body_out["model"] = "some/other-model"
        body_out["choices"] = [{"finish_reason": "stop", "index": 0,
                                "message": {"role": "assistant",
                                            "content": json.dumps(instance)}}]
        body_out["usage"] = {
            "completion_tokens": self.stress_tokens if is_stress else 400,
            "completion_tokens_details": {"reasoning_tokens": self.reasoning_tokens},
        }
        return {"status": 200, "body": body_out}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect every write and every chronology gate; leave the gate's own logic alone."""
    directory = tmp_path / "experiments" / "M120"
    directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(readiness, "DIRECTORY", directory)
    monkeypatch.setattr(readiness, "RESULT_PATH", directory / "READINESS_RESULT.json")
    monkeypatch.setattr(readiness, "LEDGER_PATH", directory / "READINESS_LEDGER.json")
    monkeypatch.setattr(readiness.chronology, "assert_stage_permitted",
                        lambda stage, root=None: {"stage": stage, "permitted": True})
    monkeypatch.setattr(readiness.chronology, "assert_no_scientific_observation_yet",
                        lambda root=None: None)
    monkeypatch.setattr(readiness.chronology, "_head_blob", lambda *a, **k: None)
    return directory


def _run(monkeypatch, route: FakeRoute):
    monkeypatch.setattr(readiness, "_transport", lambda: route)
    return readiness.execute()


# ---------------------------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------------------------

def test_the_plan_derives_and_binds_this_candidate_schema():
    frozen = readiness.plan()
    assert frozen["sends_the_qualifying_input"] is False
    assert frozen["compares_carrier_quality"] is False
    assert frozen["candidate_schema_sha256"]
    assert frozen["stress"]["stress_dominates_the_candidate_schema"] is True
    assert frozen["stress"]["stress_schema_is_not_the_candidate_schema"] is True


def test_the_budget_affords_every_retry_the_plan_grants():
    """M118 revision 1 fixed a budget that could not pay for its own retry rule, and aborted."""
    frozen = readiness.plan()
    assert frozen["request_budget"] >= frozen["mandatory_requests"] * (
        frozen["max_retries_per_request"] + 1)


def test_the_plan_refuses_a_stress_schema_that_does_not_dominate(monkeypatch):
    """A stress easier than the contract proves nothing about the contract."""
    monkeypatch.setattr(readiness.stress, "build_stress_schema",
                        lambda: {"type": "object", "additionalProperties": False,
                                 "required": ["a"], "properties": {"a": {"type": "string"}}})
    with pytest.raises(readiness.ReadinessError, match="does not dominate"):
        readiness.plan()


# ---------------------------------------------------------------------------------------------
# The verdict ladder
# ---------------------------------------------------------------------------------------------

def test_a_clean_route_reports_ready(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute())
    assert result["verdict"] == "ready" and result["ready"] is True
    assert result["unenforced_feature_classes"] == []
    assert result["combined_probe_conforms"] is True
    assert result["identity_held_on_every_request"] is True
    assert result["token_capacity_stress"]["holds"] is True
    assert sandbox.joinpath("READINESS_RESULT.json").is_file()


def test_a_route_that_is_not_the_frozen_one_is_refused(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute(break_identity=True))
    assert result["verdict"] == "not_ready_identity" and result["ready"] is False


def test_an_unenforced_feature_class_is_refused(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute(break_probe="enum"))
    assert result["verdict"] == "not_ready_features" and result["ready"] is False
    assert "enum" in result["unenforced_feature_classes"]


def test_reasoning_tokens_are_refused(sandbox, monkeypatch):
    """The control is sent explicitly; a route that reasons anyway is not the frozen instrument."""
    result = _run(monkeypatch, FakeRoute(reasoning_tokens=12))
    assert result["verdict"] == "not_ready_reasoning" and result["ready"] is False


def test_a_short_stress_completion_is_refused(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute(stress_tokens=10))
    assert result["verdict"] == "not_ready_stress" and result["ready"] is False
    assert result["token_capacity_stress"]["holds"] is False


def test_the_verdict_ladder_reports_the_first_failure_not_the_last(sandbox, monkeypatch):
    """Identity outranks features: a route that is not the frozen one is not a feature finding."""
    result = _run(monkeypatch, FakeRoute(break_identity=True, break_probe="enum"))
    assert result["verdict"] == "not_ready_identity"


# ---------------------------------------------------------------------------------------------
# Single use, budget and evidence preservation
# ---------------------------------------------------------------------------------------------

def test_the_gate_refuses_when_a_result_is_already_on_disk(sandbox, monkeypatch):
    sandbox.joinpath("READINESS_RESULT.json").write_text("{}", encoding="utf-8")
    with pytest.raises(readiness.ReadinessError, match="not redrawn"):
        _run(monkeypatch, FakeRoute())


def test_deleting_the_file_does_not_re_arm_the_gate(sandbox, monkeypatch):
    """A file check alone is re-armed by deleting the file. A commit at HEAD is not."""
    monkeypatch.setattr(readiness.chronology, "_head_blob", lambda *a, **k: b"{}")
    assert not sandbox.joinpath("READINESS_RESULT.json").exists()
    with pytest.raises(readiness.ReadinessError, match="does not re-arm"):
        _run(monkeypatch, FakeRoute())


def test_an_exhausted_budget_aborts_and_preserves_what_was_measured(sandbox, monkeypatch):
    """M118 revision 1 lost every observation it had paid for when it aborted. This one keeps them."""
    # The real budget is sized to afford every retry the rule grants, so exhausting it needs the
    # budget shrunk rather than the route made worse -- which is the point: the gate must abort on
    # its own arithmetic without losing what it already paid for.
    starved = dict(readiness.plan(), request_budget=2)
    monkeypatch.setattr(readiness, "plan", lambda: starved)
    route = FakeRoute(statuses=[429] * 60)
    monkeypatch.setattr(readiness, "_transport", lambda: route)
    with pytest.raises(readiness.ReadinessError, match="budget is exhausted"):
        readiness.execute()
    ledger = json.loads(sandbox.joinpath("READINESS_LEDGER.json").read_text(encoding="utf-8"))
    assert ledger["state"] == "instrument_aborted"
    assert ledger["requests_spent"] > 0
    assert ledger["raw_completion_persisted"] is False
    assert not sandbox.joinpath("READINESS_RESULT.json").exists(), (
        "an aborted gate must not leave a result behind")


def test_a_pre_generation_429_is_retried_and_then_succeeds(sandbox, monkeypatch):
    """The only retry the frozen rule permits, and it must actually be taken."""
    route = FakeRoute(statuses=[429])
    result = _run(monkeypatch, route)
    assert result["verdict"] == "ready"
    assert result["requests_spent"] == len(route.sent)
    assert result["requests_spent"] > readiness.plan()["mandatory_requests"]


# ---------------------------------------------------------------------------------------------
# The information boundary
# ---------------------------------------------------------------------------------------------

def _keys(value, found=None):
    found = found if found is not None else set()
    if isinstance(value, dict):
        for name, child in value.items():
            found.add(name)
            _keys(child, found)
    elif isinstance(value, list):
        for child in value:
            _keys(child, found)
    return found


def test_the_result_carries_no_qualification_statistic(sandbox, monkeypatch):
    """A DEVELOPMENT preview of carrier quality would be a degree of freedom over the contract.

    Checked as *statistics*, not as substrings: the record legitimately carries negations such as
    `is_a_qualifying_call: false`, and a naive substring scan would flag exactly the fields that
    exist to say the gate is not scientific evidence.
    """
    result = _run(monkeypatch, FakeRoute())
    # `route` is M118's constant calibration provenance -- it records that M117's route passed 12
    # qualification clauses in August, carries no M120 observation, and is the same bytes whatever
    # this gate sees. It is excluded from the scan for exactly that reason, not to make it pass.
    observed = {k: v for k, v in result.items() if k != "route"}
    names = _keys(observed)
    for forbidden in ("qualifying_carriers", "distinct_qualifying_structures",
                      "paired_demands_available", "qualification_rate", "adequate",
                      "carriers_enveloped", "carriers_accepted", "carriers_refused",
                      "blocking_clause_counts", "host_refusal_counts"):
        assert forbidden not in names, "the readiness record leaked %r" % forbidden
    # Anything that does mention qualification must be one of the three fields that exist to say
    # this gate is not scientific evidence, carrying exactly the value that says so.
    disclaimers = {
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "carries_no_qualification_statistic": True,
    }
    mentions = {name for name in names if "qualif" in name}
    assert mentions == set(disclaimers), (
        "the readiness record mentions qualification somewhere new: %s"
        % sorted(mentions ^ set(disclaimers)))
    for name, expected in disclaimers.items():
        assert observed[name] is expected
    assert result["carries_no_qualification_statistic"] is True
    assert result["is_a_qualifying_call"] is False
    assert result["qualifying_input_was_sent"] is False
    assert result["is_evidence_for_h65"] is False
    assert result["advances_a_generality_gate"] is False


def test_no_completion_content_survives_into_the_record(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute())
    assert result["raw_completion_persisted"] is False
    for observation in result["observations"]:
        assert observation["raw_completion_persisted"] is False
        assert set(observation) & {"content", "completion", "message"} == set()


def test_the_qualifying_input_is_never_sent(sandbox, monkeypatch):
    """The prompt H65 will be frozen on must not appear in a DEVELOPMENT request."""
    route = FakeRoute()
    monkeypatch.setattr(readiness, "_transport", lambda: route)
    sent_bodies = []
    original = route._http

    def _record(url, *, method="POST", body=b"", timeout=900):
        sent_bodies.append(body.decode("utf-8"))
        return original(url, method=method, body=body, timeout=timeout)

    route._http = _record
    readiness.execute()
    from metamorphosis import m120_bank as bank
    qualifying = bank.qualifying_input(ROOT)
    marker = qualifying.strip().splitlines()[0]
    assert sent_bodies
    for sent in sent_bodies:
        assert marker not in sent
        assert "conditional_actions" not in sent, (
            "a DEVELOPMENT request carried the carrier contract's own vocabulary")


def test_every_request_names_the_fixed_route(sandbox, monkeypatch):
    route = FakeRoute()
    monkeypatch.setattr(readiness, "_transport", lambda: route)
    seen = []
    original = route._http

    def _record(url, *, method="POST", body=b"", timeout=900):
        seen.append(json.loads(body.decode("utf-8")))
        return original(url, method=method, body=body, timeout=timeout)

    route._http = _record
    readiness.execute()
    assert seen
    for request in seen:
        assert request["model"] == "deepseek/deepseek-v4-flash-0731"
        assert request["provider"]["only"] == ["OpenInference"]
        assert request["provider"]["allow_fallbacks"] is False
        assert request["reasoning"] == {"effort": "none"}


def test_the_result_digest_reproduces(sandbox, monkeypatch):
    from metamorphosis.blind_bank_protocol import sha256_hex
    result = _run(monkeypatch, FakeRoute())
    assert result["result_sha256"] == sha256_hex(canonical_bytes(
        {k: v for k, v in result.items() if k != "result_sha256"}))


def test_the_probe_matrix_carries_no_carrier_vocabulary():
    """Inherited guard, run against the matrix this candidate schema actually produces."""
    matrix = probes.build_matrix(schema_tools.census(contract.candidate_schema()))
    probes.assert_non_carrier(matrix)
    assert re.search(r"\bcombined\b", matrix[-1]["name"]), (
        "the combined probe must remain last, so it is reached only after every prerequisite")
