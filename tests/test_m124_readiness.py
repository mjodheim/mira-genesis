"""The M124 readiness gate, exercised before it is spent.

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
from metamorphosis import m122_carrier_contract as contract
from metamorphosis import m124_stress_schema as stress
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from scripts import run_m124_readiness as readiness

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
    """Stands in for the gate's own transport. Records what was sent; decides nothing."""

    def __init__(self, *, break_identity=False, break_probe=None, reasoning_tokens=0,
                 stress_tokens=40000, statuses=None, truncate_probe=None,
                 omit_finish_reason_on=None):
        self.break_identity = break_identity
        self.break_probe = break_probe
        self.truncate_probe = truncate_probe
        # The shape that closed M124's predecessor: HTTP 200, content present, no finish_reason.
        self.omit_finish_reason_on = omit_finish_reason_on
        self.reasoning_tokens = reasoning_tokens
        self.stress_tokens = stress_tokens
        self.statuses = list(statuses or [])
        self.sent: list[str] = []

    def __call__(self, url, *, method="POST", body=b"", timeout=900):
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
        finish = "stop"
        if self.truncate_probe and self.truncate_probe in name:
            # Enforcement failing open: a huge completion cut off at the cap, which is what
            # closed M124's predecessor.
            finish = "length"
            instance = {"runaway": ["x"] * 50}
        choice = {"index": 0, "message": {"role": "assistant",
                                          "content": json.dumps(instance)}}
        if not (self.omit_finish_reason_on and self.omit_finish_reason_on in name):
            choice["finish_reason"] = finish
        body_out["choices"] = [choice]
        body_out["usage"] = {
            "completion_tokens": self.stress_tokens if is_stress else 400,
            "completion_tokens_details": {"reasoning_tokens": self.reasoning_tokens},
        }
        return {"status": 200, "body": body_out}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect every write and every chronology gate; leave the gate's own logic alone."""
    directory = tmp_path / "experiments" / "M124"
    directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(readiness, "DIRECTORY", directory)
    # The ceiling scan crosses milestones, so it needs redirecting too. The sandbox mirrors the
    # real layout -- experiments/<milestone>/ -- so the inherited counting tests keep testing the
    # thing they were written for.
    monkeypatch.setattr(readiness, "CEILING_SCAN_ROOT", tmp_path / "experiments")
    monkeypatch.setattr(readiness, "RESULT_PATH", directory / "READINESS_RESULT.json")
    monkeypatch.setattr(readiness, "LEDGER_PATH", directory / "READINESS_LEDGER.json")
    monkeypatch.setattr(readiness.chronology, "assert_stage_permitted",
                        lambda stage, root=None: {"stage": stage, "permitted": True})
    monkeypatch.setattr(readiness.chronology, "assert_no_scientific_observation_yet",
                        lambda root=None: None)
    monkeypatch.setattr(readiness.chronology, "_head_blob", lambda *a, **k: None)
    # The retry path now backs off for real. The wait is tested directly in
    # test_a_retry_waits_and_honours_retry_after; everywhere else it is dead time.
    monkeypatch.setattr(readiness.time, "sleep", lambda _seconds: None)
    return directory


def _run(monkeypatch, route: FakeRoute):
    monkeypatch.setattr(readiness, "_http", route)
    monkeypatch.setenv(readiness.SECRET_VARIABLE, "development-not-a-credential")
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
    # A result with no verdict at all is not a delivery verdict, so the allowance does not apply
    # and the gate refuses exactly as it did before the allowance existed.
    sandbox.joinpath("READINESS_RESULT.json").write_text("{}", encoding="utf-8")
    with pytest.raises(readiness.ReadinessError, match="only a .* verdict may be superseded"):
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
    monkeypatch.setattr(readiness, "_http", route)
    monkeypatch.setenv(readiness.SECRET_VARIABLE, "development-not-a-credential")
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
    # qualification clauses in August, carries no M124 observation, and is the same bytes whatever
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
    """The prompt H69 will be frozen on must not appear in a DEVELOPMENT request."""
    route = FakeRoute()
    sent_bodies = []

    def _record(url, *, method="POST", body=b"", timeout=900):
        sent_bodies.append(body.decode("utf-8"))
        return route(url, method=method, body=body, timeout=timeout)

    monkeypatch.setattr(readiness, "_http", _record)
    monkeypatch.setenv(readiness.SECRET_VARIABLE, "development-not-a-credential")
    readiness.execute()
    # The bank module does not exist yet -- this milestone builds the gate first on purpose -- so
    # the check is against the contract's own vocabulary rather than against a derived prompt.
    assert sent_bodies
    for sent in sent_bodies:
        # The contract's own vocabulary. The generic identifier regex is deliberately *not*
        # checked: the stress schema uses the same lowercase-identifier pattern for its own codes,
        # and flagging it would be flagging a coincidence rather than a leak.
        for vocabulary in ("arg_size", "error_index", "guard", "carrier", "machines",
                           "conditional_actions", "hidden"):
            assert vocabulary not in sent, (
                "a DEVELOPMENT request carried the carrier contract's vocabulary: %r" % vocabulary)


def test_every_request_names_the_fixed_route(sandbox, monkeypatch):
    route = FakeRoute()
    seen = []

    def _record(url, *, method="POST", body=b"", timeout=900):
        assert url == readiness.COMPLETIONS_ENDPOINT
        seen.append(json.loads(body.decode("utf-8")))
        return route(url, method=method, body=body, timeout=timeout)

    monkeypatch.setattr(readiness, "_http", _record)
    monkeypatch.setenv(readiness.SECRET_VARIABLE, "development-not-a-credential")
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




def test_the_gate_carries_its_own_transport_and_imports_no_posix_only_module():
    """It crashed on `fcntl` -- imported by a closed milestone for a file lock -- before sending a
    single request. The transport is now the gate's own, and the same shape the qualifying
    generation uses."""
    import ast

    source = ast.parse((ROOT / "scripts" / "run_m124_readiness.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(source):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update("%s.%s" % (node.module, a.name) for a in node.names)
    assert "fcntl" not in imported
    assert not any("audit_m117" in name for name in imported), (
        "the gate must not reach into a closed milestone for its transport")
    assert callable(readiness._http)


def test_the_transport_refuses_a_non_https_endpoint(monkeypatch):
    monkeypatch.setenv(readiness.SECRET_VARIABLE, "development-not-a-credential")
    with pytest.raises(readiness.ReadinessError, match="must use https"):
        readiness._http("http://openrouter.ai/api/v1/chat/completions", body=b"{}")


def test_the_transport_refuses_to_send_without_a_credential(monkeypatch):
    monkeypatch.delenv(readiness.SECRET_VARIABLE, raising=False)
    with pytest.raises(readiness.ReadinessError, match="no network request was made"):
        readiness._http(readiness.COMPLETIONS_ENDPOINT, body=b"{}")


# ---------------------------------------------------------------------------------------------
# The two corrections M124's predecessor's outcome named
# ---------------------------------------------------------------------------------------------

def test_a_rate_limited_request_is_a_delivery_outcome_not_an_identity_failure(sandbox,
                                                                              monkeypatch):
    """The misattribution that made M124's predecessor report `not_ready_identity`.

    A 429 carries no router metadata, so attesting identity on it conflates "the route served
    something else" with "the route served nothing". The gate now attests identity only where a
    completion exists, and a retry-exhausted 429 reports as a delivery outcome.
    """
    # Enough 429s to exhaust the retries on the final probe only.
    # Nine probes answer cleanly; the stress then exhausts its two permitted retries on 429.
    route = FakeRoute(statuses=[200] * 9 + [429] * 3)
    result = _run(monkeypatch, route)
    assert result["verdict"] == "not_ready_delivery", result["verdict"]
    assert result["requests_that_carried_no_completion"], "the 429s were not recorded as delivery"
    assert result["identity_is_attested_only_where_a_completion_exists"] is True
    for attested in result["identity_per_request"]:
        assert attested["holds"] is True, (
            "identity was attested on a response carrying no completion")


def test_a_truncated_probe_is_its_own_class_not_mere_non_conformance(sandbox, monkeypatch):
    """101,379 tokens against a fifty-token requirement is enforcement failing open."""
    result = _run(monkeypatch, FakeRoute(truncate_probe="enum"))
    assert result["verdict"] == "not_ready_enforcement_failed_open", result["verdict"]
    assert "enum" in result["feature_classes_where_enforcement_failed_open"]
    truncated = [o for o in result["observations"] if o["probe"] == "enum"][0]
    assert truncated["enforcement_failed_open"] is True
    assert truncated["finish_reason"] == "length"


def test_a_clean_run_records_neither_correction(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute())
    assert result["verdict"] == "ready"
    assert result["feature_classes_where_enforcement_failed_open"] == []
    assert result["requests_that_carried_no_completion"] == []


def test_the_stress_schema_must_both_dominate_and_fit_the_route():
    """Satisfying one constraint alone is worthless, and the first draft satisfied only one."""
    from metamorphosis import m122_carrier_contract as m124_contract
    from metamorphosis import m124_stress_schema as m124_stress
    proof = m124_stress.assert_certifies(m124_contract.candidate_schema(),
                                         m124_contract.CERTIFIED_ARRAY_OF_OBJECT_LEVELS)
    assert proof["stress_dominates_the_candidate_schema"] is True
    assert proof["stress_is_within_the_certified_nesting"] is True
    assert (proof["stress_schema_census"]["array_of_object_levels"]
            <= m124_contract.CERTIFIED_ARRAY_OF_OBJECT_LEVELS)


def test_the_stress_certification_refuses_a_stress_deeper_than_the_route_enforces():
    from metamorphosis import m122_carrier_contract as m124_contract
    from metamorphosis import m124_stress_schema as m124_stress
    with pytest.raises(m124_stress.StressError, match="array-of-object levels"):
        m124_stress.assert_certifies(m124_contract.candidate_schema(), 4)


def test_the_endpoint_has_exactly_one_definition():
    """M124's predecessor defined it twice and asserted the two agreed. One is better."""
    from metamorphosis import m122_carrier_contract as m124_contract
    assert readiness.COMPLETIONS_ENDPOINT is m124_contract.GENERATOR_ENDPOINT
    assert readiness.plan()["endpoint"] == m124_contract.GENERATOR_ENDPOINT


# ---------------------------------------------------------------------------------------------
# The owner-authorised delivery allowance
# ---------------------------------------------------------------------------------------------

def _write(path, record):
    path.write_bytes(canonical_bytes(record) + b"\n")


def _delivery(index):
    """An archived delivery attempt against the *current* instrument.

    The plan digest matters: an attempt against another instrument does not count against this
    one, which is how the owner-authorised reset is enforced mechanically rather than by a note.
    """
    return {"verdict": readiness.DELIVERY_VERDICT,
            "result_sha256": "attempt-%d" % index,
            "plan_sha256": readiness.plan()["plan_sha256"]}


def test_a_capability_verdict_is_final_and_can_never_be_superseded(sandbox, monkeypatch):
    """The allowance must only ever stop the gate sooner. It may not rescue a capability finding."""
    for verdict in ("ready", "not_ready_features", "not_ready_identity",
                    "not_ready_enforcement_failed_open", "not_ready_stress"):
        _write(sandbox / "READINESS_RESULT.json", {"verdict": verdict})
        with pytest.raises(readiness.ReadinessError, match="already exists"):
            readiness._assert_the_allowance_permits_another_attempt()


def test_a_delivery_verdict_may_be_superseded_within_the_allowance(sandbox, monkeypatch):
    _write(sandbox / "READINESS_RESULT.json", {"verdict": readiness.DELIVERY_VERDICT})
    _write(sandbox / "READINESS_ATTEMPT_01_not_ready_delivery.json", _delivery(1))
    allowance = readiness._assert_the_allowance_permits_another_attempt()
    assert allowance["delivery_allowance"] == 3
    assert len(allowance["delivery_attempts_against_this_instrument"]) == 1


def test_the_allowance_refuses_a_fourth_delivery_attempt(sandbox, monkeypatch):
    """Bounded, so re-running until a quiet window returns `ready` is not available."""
    _write(sandbox / "READINESS_RESULT.json", {"verdict": readiness.DELIVERY_VERDICT})
    for index in range(1, readiness.DELIVERY_ALLOWANCE + 1):
        _write(sandbox / ("READINESS_ATTEMPT_%02d_not_ready_delivery.json" % index),
               _delivery(index))
    with pytest.raises(readiness.ReadinessError, match="allowance of 3 is exhausted"):
        readiness._assert_the_allowance_permits_another_attempt()


def test_an_attempt_that_produced_no_verdict_does_not_consume_the_allowance(sandbox):
    """It yielded nothing to select on, so counting it would penalise the science for a crash."""
    _write(sandbox / "READINESS_ATTEMPT_01_KILLED.json",
           {"state": "probing", "verdict_produced": False})
    assert readiness._archived_delivery_attempts() == []


def test_a_committed_capability_verdict_still_blocks_even_with_the_file_deleted(sandbox,
                                                                                monkeypatch):
    monkeypatch.setattr(readiness.chronology, "_head_blob",
                        lambda *a, **k: canonical_bytes({"verdict": "not_ready_features"}))
    assert not (sandbox / "READINESS_RESULT.json").exists()
    with pytest.raises(readiness.ReadinessError, match="already exists"):
        readiness._assert_the_allowance_permits_another_attempt()


def test_the_run_archives_every_attempt_under_its_own_name(sandbox, monkeypatch):
    result = _run(monkeypatch, FakeRoute())
    archived = sorted(p.name for p in sandbox.glob(readiness.ATTEMPT_ARCHIVE_GLOB))
    assert archived, "the attempt was not archived"
    assert result["verdict"] in archived[-1]
    assert result["delivery_allowance"]["delivery_allowance"] == 3


def test_deleting_the_result_does_not_bypass_the_allowance(sandbox):
    """The exception must not reintroduce the defect the once-only guard exists to prevent."""
    for index in range(1, readiness.DELIVERY_ALLOWANCE + 1):
        _write(sandbox / ("READINESS_ATTEMPT_%02d_not_ready_delivery.json" % index),
               _delivery(index))
    assert not (sandbox / "READINESS_RESULT.json").exists()
    with pytest.raises(readiness.ReadinessError, match="allowance of 3 is exhausted"):
        readiness._assert_the_allowance_permits_another_attempt()


# ---------------------------------------------------------------------------------------------
# Counting the allowance correctly -- three defects the guard itself surfaced
# ---------------------------------------------------------------------------------------------

def test_one_attempt_archived_twice_counts_once(sandbox):
    """Archiving a result by hand beside the gate's own copy made one attempt count as two."""
    for name in ("READINESS_ATTEMPT_03_DELIVERY.json",
                 "READINESS_ATTEMPT_03_not_ready_delivery.json"):
        _write(sandbox / name, {"verdict": readiness.DELIVERY_VERDICT,
                                "result_sha256": "same", "plan_sha256": "p"})
    assert len(readiness._archived_delivery_attempts("p")) == 1


def test_an_attempt_against_another_instrument_does_not_count_against_this_one(sandbox):
    """The owner's reset is a property of the apparatus, not of a note somebody wrote."""
    _write(sandbox / "READINESS_ATTEMPT_02_old.json",
           {"verdict": readiness.DELIVERY_VERDICT, "result_sha256": "a", "plan_sha256": "old"})
    assert readiness._archived_delivery_attempts("new") == []
    assert len(readiness._archived_delivery_attempts("old")) == 1
    assert len(readiness._archived_delivery_attempts(None)) == 1


def test_revising_the_apparatus_cannot_buy_attempts_indefinitely(sandbox):
    """A per-instrument allowance without a total is an unbounded retry budget in disguise."""
    for index in range(readiness.TOTAL_DELIVERY_CEILING):
        _write(sandbox / ("READINESS_ATTEMPT_%02d_x.json" % index),
               {"verdict": readiness.DELIVERY_VERDICT,
                "result_sha256": "r%d" % index, "plan_sha256": "instrument%d" % index})
    with pytest.raises(readiness.ReadinessError, match="total delivery ceiling"):
        readiness._assert_the_allowance_permits_another_attempt()


def test_the_plan_digest_moves_when_the_stress_size_moves(monkeypatch):
    """A census counts keyword occurrences, not values, so binding only it left the digest still.

    That would have made the allowance reset silently do nothing while appearing to work.
    """
    from metamorphosis import m124_stress_schema as m124_stress
    before = readiness.plan()["plan_sha256"]
    monkeypatch.setattr(m124_stress, "STATIONS", m124_stress.STATIONS * 2)
    after = readiness.plan()["plan_sha256"]
    assert before != after, "the plan does not bind the stress size"


def test_the_plan_binds_the_stress_bytes_and_the_whole_sizing_rule():
    """Everything the size depends on is inside the digest, so a revision cannot be silent."""
    frozen = readiness.plan()["stress"]
    assert len(frozen["stress_schema_sha256"]) == 64
    assert frozen["stress_stations"] == 109
    derivation = frozen["stress_sizing_derivation"]
    assert derivation["inherited_threshold_was_not_changed"] is True
    assert derivation["sizing_rule"] == "empirical_rate_envelope"
    assert derivation["no_model_is_fitted"] is True
    # The three observations, the rule, the bounds and the deterministic choice are all bound.
    assert {o["stations"] for o in derivation["observations"]} == {24, 74, 109, 167}
    assert derivation["min_stations"] == 77 and derivation["max_stations"] == 141
    assert derivation["station_choice"] == "midpoint_of_the_admissible_window"
    assert derivation["station_choice_is_deterministic"] is True
    assert derivation["observed_truncation_tokens"] == 100657
    assert derivation["operational_ceiling_tokens"] == 85000
    assert derivation["clears_the_threshold_even_at_the_lowest_observed_rate"] is True
    assert derivation["stays_under_the_operational_ceiling_even_at_the_highest_observed_rate"]


# ---------------------------------------------------------------------------------------------
# M124's two corrections
# ---------------------------------------------------------------------------------------------

def test_an_unanswered_probe_is_not_recorded_as_an_unenforced_class(sandbox, monkeypatch):
    """The defect M120 and M122 both carried, and the one M124 exists partly to fix.

    `conforms` is false for an HTTP 429 exactly as it is for a completion the schema refuses. Both
    milestones therefore named feature classes as unenforced when their probes had only ever been
    rate-limited -- a false record, even though the verdict ladder kept the headline right.
    """
    route = FakeRoute(statuses=[429] * 3 + [200] * 40)
    result = _run(monkeypatch, route)
    assert result["unenforced_feature_classes"] == [], (
        "a rate-limited probe was scored as an unenforced capability")
    assert result["feature_classes_never_answered"], "the unanswered class was not reported at all"
    assert result["unenforced_means_answered_and_refused_not_merely_unanswered"] is True
    assert result["verdict"] == "not_ready_delivery"


def test_a_probe_that_answers_and_refuses_is_still_recorded_as_unenforced(sandbox, monkeypatch):
    """The correction must not blind the gate to a real capability failure."""
    result = _run(monkeypatch, FakeRoute(break_probe="enum"))
    assert "enum" in result["unenforced_feature_classes"]
    assert result["verdict"] == "not_ready_features"


# ---------------------------------------------------------------------------------------------
# The sizing rule, after the two-point fit was falsified by its first out-of-sample test
# ---------------------------------------------------------------------------------------------

def test_no_model_is_fitted_any_more():
    """Three sizings, three failures. The third falsified the method, not just the number."""
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    assert derivation["sizing_rule"] == "empirical_rate_envelope"
    assert derivation["no_model_is_fitted"] is True
    assert not hasattr(m124_stress, "TOKENS_PER_STATION"), "the fit is still here"
    assert not hasattr(m124_stress, "FIXED_COMPLETION_COST"), "the fit is still here"
    assert not hasattr(m124_stress, "predicted_completion_tokens"), (
        "a point prediction is exactly what has now been falsified three times")


def test_every_observation_including_the_censored_one_is_carried():
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    assert derivation["observation_count"] == 4
    assert {o["stations"] for o in derivation["observations"]} == {24, 74, 109, 167}
    censored = sorted(o["stations"] for o in derivation["observations"] if o["truncated"])
    assert censored == [109, 167], (
        "both incomplete runs must be marked, because their token counts are floors and not "
        "measurements -- the 109 one did not even report a finish_reason")


def test_the_rates_are_not_monotonic_which_is_why_there_is_no_model():
    """546.6 down to 418.3 back up to >=602.7. Not a line, and not identified by three points."""
    from metamorphosis import m124_stress_schema as m124_stress
    rates = list(m124_stress.OBSERVED_RATES)
    assert rates[0] > rates[1] and rates[2] > rates[1], (
        "if the rates were monotonic a model would at least be arguable")
    assert m124_stress.LOWEST_OBSERVED_RATE == min(rates)
    assert m124_stress.HIGHEST_OBSERVED_RATE == max(rates)


def test_the_truncation_is_recorded_as_an_observation_not_as_a_known_ceiling():
    """100,657 is where one completion stopped, not a limit anybody measured."""
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    assert derivation["observed_truncation_tokens"] == 100657
    assert derivation["observed_truncation_is_not_a_known_exact_ceiling"] is True
    # Stated in the right direction: a completion of 100,657 tokens was emitted, so the limit is
    # not below it. The earlier wording said "at most ... and may be lower" and a test pinned it.
    establishes = derivation["what_the_truncation_establishes"]
    assert "at least 100,657" in establishes
    assert "at most" not in establishes, "the censoring inference is stated backwards again"
    assert derivation["worst_case_is_below_a_completion_already_served_cleanly"] is True


def test_the_operational_ceiling_is_a_conservative_choice_with_real_margin():
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    assert derivation["operational_ceiling_tokens"] == 85000
    assert derivation["operational_ceiling_is_a_conservative_choice_not_a_measurement"] is True
    margin = derivation["operational_ceiling_margin_below_the_observed_truncation"]
    assert 0.14 < margin < 0.17, "the ~15% margin is the point; %.3f is not it" % margin
    assert (derivation["operational_ceiling_tokens"]
            < derivation["observed_truncation_tokens"])


def test_the_window_is_recomputed_from_the_envelope_not_trusted_as_constants():
    """The declared bounds and the rule must agree, or one of them is stale."""
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    assert derivation["bounds_recomputed_from_the_envelope"] == [77, 141]
    assert [derivation["min_stations"], derivation["max_stations"]] == [77, 141]


def test_the_chosen_size_is_the_deterministic_midpoint():
    from metamorphosis import m124_stress_schema as m124_stress
    assert m124_stress.STATIONS == (m124_stress.MIN_STATIONS + m124_stress.MAX_STATIONS) // 2
    assert m124_stress.STATIONS == 109
    derivation = m124_stress.sizing_derivation()
    assert derivation["station_choice"] == "midpoint_of_the_admissible_window"
    assert derivation["station_choice_is_deterministic"] is True
    assert derivation["floor_and_ceiling_bracket_the_choice"] is True


def test_the_size_is_safe_under_every_rate_ever_observed():
    """Not under a fitted rate. Under the lowest and the highest that were actually seen."""
    from metamorphosis import m124_stress_schema as m124_stress
    low, high = m124_stress.predicted_completion_token_range()
    assert low > m124_stress.INHERITED_THRESHOLD_TOKENS, (
        "at the lowest observed rate this repeats M122's 3.3% shortfall")
    assert high < m124_stress.OPERATIONAL_CEILING_TOKENS, (
        "at the highest observed rate this repeats M124 attempt 1's truncation")
    assert round(low) == 45599 and round(high) == 65698


def _window(monkeypatch, module, low: int, high: int, stations: int) -> None:
    """Move the declared window and what the envelope derives together.

    The agreement check runs first and would otherwise fire on every one of these, so a test that
    moved only the constants would prove the agreement guard works and say nothing about the check
    it was actually written for.
    """
    monkeypatch.setattr(module, "MIN_STATIONS", low)
    monkeypatch.setattr(module, "MAX_STATIONS", high)
    monkeypatch.setattr(module, "STATIONS", stations)
    monkeypatch.setattr(module, "_derived_bounds", lambda: (low, high))


def test_the_guard_refuses_a_size_that_would_miss_the_threshold(monkeypatch):
    from metamorphosis import m124_stress_schema as m124_stress
    _window(monkeypatch, m124_stress, 1, 141, 10)
    with pytest.raises(m124_stress.StressError, match="would not clear"):
        m124_stress._assert_the_sizing_is_safe_across_the_whole_envelope()


def test_the_guard_refuses_a_size_that_would_truncate(monkeypatch):
    from metamorphosis import m124_stress_schema as m124_stress
    _window(monkeypatch, m124_stress, 77, 5000, 4000)
    with pytest.raises(m124_stress.StressError, match="operational ceiling"):
        m124_stress._assert_the_sizing_is_safe_across_the_whole_envelope()


def test_the_guard_refuses_a_window_that_disagrees_with_the_envelope(monkeypatch):
    """Constants that drift away from the rule they claim to come from are the silent failure."""
    from metamorphosis import m124_stress_schema as m124_stress
    monkeypatch.setattr(m124_stress, "MAX_STATIONS", 200)
    with pytest.raises(m124_stress.StressError, match="does not match the window"):
        m124_stress._assert_the_sizing_is_safe_across_the_whole_envelope()


def test_the_guard_refuses_an_operational_ceiling_with_no_margin(monkeypatch):
    from metamorphosis import m124_stress_schema as m124_stress
    monkeypatch.setattr(m124_stress, "OPERATIONAL_CEILING_TOKENS", 100657)
    _window(monkeypatch, m124_stress, 77, 167, 109)
    with pytest.raises(m124_stress.StressError, match="margin"):
        m124_stress._assert_the_sizing_is_safe_across_the_whole_envelope()


def test_the_inherited_threshold_is_still_untouched():
    """The stress moves; the bar does not. M118 set 32,000 and nothing here may move it."""
    from metamorphosis import m124_stress_schema as m124_stress
    assert m124_stress.INHERITED_THRESHOLD_TOKENS == 32000
    assert m124_stress.sizing_derivation()["inherited_threshold_was_not_changed"] is True
    assert readiness.STRESS_MIN_COMPLETION_TOKENS == 32000


def test_the_contract_is_inherited_from_m122_and_not_re_authored():
    """The one thing M122 established was that this contract is enforced. Do not rebuild it."""
    from metamorphosis import m122_carrier_contract as validated
    assert readiness.contract is validated
    assert readiness.plan()["candidate_schema_sha256"] == sha256_hex(
        canonical_bytes(validated.candidate_schema()))


def test_the_ceiling_counts_attempts_from_earlier_milestones_too():
    """M124's third correction: the scan and the sentence describing it now agree.

    M122 wrote the ceiling as "across every instrument" and counted it by globbing its own
    experiment directory. A successor milestone is a new directory, so the ceiling reset on exactly
    the move it exists to bound -- revising the apparatus and opening a successor being the same
    move at two sizes.
    """
    # M124 has no result yet, so the guard permits a run. Its predecessor was closed at a terminal
    # verdict and the same call refused there -- both are the guard working.
    allowance = readiness._assert_the_allowance_permits_another_attempt()
    across = allowance["delivery_attempts_across_every_instrument"]
    assert allowance["the_ceiling_scan_crosses_milestones_not_only_apparatus_revisions"] is True
    assert any(name.startswith("M122/") for name in across), (
        "the ceiling did not see the predecessor's delivery attempts, so it resets per milestone")
    # And still deduplicated by digest: M122 archived attempt 3 under two filenames.
    assert len(across) == len(set(across))
    assert len(across) < readiness.TOTAL_DELIVERY_CEILING
    # M123's attempt 2 was terminal, not a delivery failure, so it is not counted. Its attempt 1
    # was, and is. (M122's attempt 2 was also a delivery failure -- hence the qualified prefixes.)
    assert not any(name.startswith("M123/READINESS_ATTEMPT_02") for name in across)
    assert "M123/READINESS_ATTEMPT_01_not_ready_delivery.json" in across
    # Four after M124 attempt 1 landed: M122 twice, M123 attempt 1, M124 attempt 1. This assertion
    # counted three before the run and the run moved the world, not the code.
    assert len(across) == 4, "four delivery attempts stand across every instrument, of six"
    assert "M124/READINESS_ATTEMPT_01_not_ready_delivery.json" in across
    # The per-instrument allowance is scoped to this plan and now holds exactly attempt 1: the run
    # spent one of three. It was empty before the run.
    assert allowance["delivery_attempts_against_this_instrument"] == [
        "M124/READINESS_ATTEMPT_01_not_ready_delivery.json"]
    assert len(allowance["delivery_attempts_against_this_instrument"]) < readiness.DELIVERY_ALLOWANCE


def test_the_ceiling_refuses_a_run_once_it_is_reached(sandbox, monkeypatch):
    exhausted = [
        "M0%02d/READINESS_ATTEMPT_01.json" % i
        for i in range(readiness.TOTAL_DELIVERY_CEILING)]
    monkeypatch.setattr(
        readiness, "_archived_delivery_attempts",
        lambda plan_sha256=None: [] if plan_sha256 is not None else exhausted)
    with pytest.raises(readiness.ReadinessError, match="total delivery ceiling"):
        readiness._assert_the_allowance_permits_another_attempt()


# ---------------------------------------------------------------------------------------------
# What the pre-run adversarial panel found, before attempt 2 was spent
# ---------------------------------------------------------------------------------------------

def test_a_run_where_nothing_answers_is_retryable_not_terminal(sandbox, monkeypatch):
    """The defect that would have closed M124 on an expired key.

    `identity` is assigned only from a response carrying a completion. When NOTHING answers it
    stays None, and the ladder used to catch that as `not_ready_identity` -- terminal, refused by
    the allowance guard. So partial delivery failure was retryable and TOTAL delivery failure was
    permanent: the worse the outage, the more final the verdict.
    """
    def fresh():
        # Each case is its own attempt; four in one sandbox would exhaust the allowance, which is
        # the guard working rather than the thing under test.
        for archived in sandbox.glob(readiness.ATTEMPT_ARCHIVE_GLOB):
            archived.unlink()
        readiness.RESULT_PATH.unlink(missing_ok=True)

    for status in (429, 402, 503):
        fresh()
        result = _run(monkeypatch, FakeRoute(statuses=[status] * 60))
        assert result["verdict"] == "not_ready_delivery", (
            "a run where every request returned HTTP %s was scored %r, which is terminal"
            % (status, result["verdict"]))
        assert result["requests_that_carried_no_completion"], (
            "the record must say the route never answered")

    # And a transport failure, in the shape `_http` returns from its own except branch.
    def dead_network(url, *, method="POST", body=b"", timeout=900):
        return {"status": None, "transport_failure_class": "connection_reset", "body": {}}

    fresh()
    result = _run(monkeypatch, dead_network)
    assert result["verdict"] == "not_ready_delivery", (
        "a dead network was scored %r, which permanently closes the milestone" % result["verdict"])


def test_a_route_that_answers_as_the_wrong_model_is_still_an_identity_failure(sandbox, monkeypatch):
    """The correction must not blind the gate to a genuine substitution."""
    result = _run(monkeypatch, FakeRoute(break_identity=True))
    assert result["verdict"] == "not_ready_identity"


def test_never_answered_is_reported_in_the_feature_class_vocabulary(sandbox, monkeypatch):
    """The field carrying M124's own correction was reporting probe names.

    Attempt 1 recorded `additional_properties` and `min_items`; the class list beside it says
    `additionalProperties_false` and `minItems`. Intersecting the two gave the empty set.
    """
    result = _run(monkeypatch, FakeRoute(statuses=[429] * 3 + [200] * 60))
    classes = set(result["feature_classes_never_answered"])
    assert classes, "nothing was reported as never answered"
    assert classes <= set(result["required_feature_classes"]), (
        "reported %s, which is not in the feature-class vocabulary %s"
        % (sorted(classes), sorted(result["required_feature_classes"])))
    assert result["probes_never_answered"], "the probe names are still reported, separately"


def test_a_retry_waits_and_honours_retry_after(monkeypatch):
    """Three attempts inside the same rate-limit window learn the same thing three times."""
    slept = []
    monkeypatch.setattr(readiness.time, "sleep", lambda s: slept.append(s))
    delay = readiness._wait_before_retrying(
        {"headers": {"Retry-After": "7"}, "status": 429}, attempt=0)
    assert delay == 7.0 and slept == [7.0], "the advertised Retry-After was ignored"
    slept.clear()
    delay = readiness._wait_before_retrying({"headers": {}, "status": 429}, attempt=2)
    assert delay == readiness.RETRY_BASE_SECONDS * 4, "the backoff is not exponential"
    assert readiness._wait_before_retrying(
        {"headers": {"Retry-After": "99999"}, "status": 429}, attempt=0
    ) == readiness.RETRY_MAX_SECONDS, "the wait is not bounded"


def test_a_truncated_stress_is_recorded_as_enforcement_failing_open(sandbox, monkeypatch):
    """Attempt 1 archived a completion cut off at the cap beside an empty failed-open list."""
    result = _run(monkeypatch, FakeRoute(truncate_probe=stress.STRESS_SCHEMA_NAME))
    assert result["token_capacity_stress"]["finish_reason"] == "length"
    assert result["token_capacity_stress"]["enforcement_failed_open"] is True
    assert result["token_capacity_stress"]["holds"] is False


def test_the_stress_records_the_route_serves_at_least_the_truncated_figure():
    """The censoring inference, in the direction the evidence actually points."""
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    establishes = derivation["what_the_truncation_establishes"]
    assert "at least 100,657" in establishes
    assert "at most" not in establishes
    assert derivation["route_has_served_this_many_tokens_cleanly"] == 68368
    assert derivation["worst_case_is_below_a_completion_already_served_cleanly"] is True


# ---------------------------------------------------------------------------------------------
# M124's prospective decision: a completion with no finish_reason is a delivery outcome
# ---------------------------------------------------------------------------------------------

def test_the_shape_that_closed_the_predecessor_is_now_retryable(sandbox, monkeypatch):
    """The whole reason this milestone exists.

    M124's predecessor closed at `not_ready_stress` -- terminal -- on a stress that returned HTTP
    200, 50,232 tokens, a body that does not validate, and no `finish_reason` at all. Replay that
    exact shape: it must be a delivery outcome, which may be retried.
    """
    result = _run(monkeypatch, FakeRoute(omit_finish_reason_on=stress.STRESS_SCHEMA_NAME))
    assert result["verdict"] == "not_ready_delivery", (
        "the shape that closed the predecessor is still terminal: %r" % result["verdict"])
    stressed = result["token_capacity_stress"]
    assert stressed["reported_a_finish_reason"] is False
    assert any(u["probe"] == "token_capacity_stress"
               for u in result["requests_that_carried_no_completion"]), (
        "the stress must be recorded as a request that did not answer")


def test_a_truncated_stress_is_still_terminal(sandbox, monkeypatch):
    """The decision is narrow on purpose. Truncation is evidence about size, and it stays final.

    Making truncation retryable would let an oversized stress be re-run until it passed, which is
    the gate tuned to itself -- the failure this whole line of records exists to prevent.
    """
    result = _run(monkeypatch, FakeRoute(truncate_probe=stress.STRESS_SCHEMA_NAME))
    assert result["verdict"] == "not_ready_stress"
    assert result["token_capacity_stress"]["reported_a_finish_reason"] is True
    assert result["token_capacity_stress"]["enforcement_failed_open"] is True


def test_a_probe_without_a_finish_reason_is_unanswered_not_unenforced(sandbox, monkeypatch):
    """The same rule on the probe side, and it must not manufacture a capability finding."""
    result = _run(monkeypatch, FakeRoute(omit_finish_reason_on="enum"))
    assert "enum" not in result["unenforced_feature_classes"]
    assert result["verdict"] == "not_ready_delivery"


def test_the_decision_is_frozen_into_the_plan():
    """It cannot be adjusted after a result is seen, which is the only thing that makes it
    prospective rather than convenient."""
    frozen = readiness.plan()
    assert frozen["a_completion_without_a_finish_reason_is_a_delivery_outcome"] is True
    assert frozen["truncation_remains_a_scientific_outcome_and_is_terminal"] is True


def test_a_clean_stress_still_passes(sandbox, monkeypatch):
    """The correction must not make the gate unable to fail, or unable to pass."""
    result = _run(monkeypatch, FakeRoute(stress_tokens=50000))
    assert result["verdict"] == "ready"
    assert result["token_capacity_stress"]["reported_a_finish_reason"] is True


def test_the_fourth_observation_did_not_move_the_size():
    """A rule whose answer is stable when new evidence arrives is behaving the way a rule should."""
    from metamorphosis import m124_stress_schema as m124_stress
    derivation = m124_stress.sizing_derivation()
    assert derivation["observation_count"] == 4
    assert {o["stations"] for o in derivation["observations"]} == {24, 74, 109, 167}
    assert derivation["bounds_recomputed_from_the_envelope"] == [77, 141]
    assert derivation["stations"] == 109
    # The new point is inside the envelope the first three described, which is why nothing moved.
    rates = derivation["observed_rates"]
    fourth = [o for o in derivation["observations"] if o["stations"] == 109][0]
    rate = fourth["completion_tokens"] / fourth["stations"]
    assert derivation["lowest_observed_rate"] <= rate <= derivation["highest_observed_rate"]
    assert fourth["truncated"] is True, "it is a floor, not a measurement"
