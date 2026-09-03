#!/usr/bin/env python3
"""DEVELOPMENT readiness for the M120 candidate schema. Not a qualifying call, and never redrawn.

M119 inherited M118's readiness result and treated it as evidence about its own generator contract.
It was evidence about M115's schema. That was defensible there, because M119 inherited M115's schema
byte for byte. It is not defensible here: M120's candidate schema uses the same eleven feature
classes and far more of them, and M118's stress schema does not dominate its keyword census. A gate
that carries across that gap is asserting a measurement nobody took.

So this runs again, against a stress schema that **does** dominate the M120 candidate census, and
`m120_chronology.assert_readiness_passed` refuses the scientific freeze until its result is
committed and says `ready`.

## What it measures, and what it deliberately does not

It measures the route: runtime identity on every request, each schema feature class the census
requires, the reasoning control, and one full-scale conforming completion. Every threshold is
inherited from M118's gate rather than chosen here, because a threshold rewritten for M120 could be
rewritten until the route passed.

It does **not** send the qualifying input, and the stress schema is not the candidate schema. Both
are deliberate. Sending the carrier contract at scale would hand the project a preview of what this
generator produces under the contract H65 is about to be frozen on -- and a preview of the bank is
a degree of freedom over the contract. The result record carries no qualification statistic, no
carrier count and no completion content, so there is nothing in it to tune against.

The API key is read from `OPENROUTER_API_KEY` and is never written or printed.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_capability_probes as probes  # noqa: E402
from metamorphosis import m116_schema as schema_tools  # noqa: E402
from metamorphosis import m118_route as fixed  # noqa: E402
from metamorphosis import m120_carrier_contract as contract  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis import m120_stress_schema as stress  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

DIRECTORY = ROOT / chronology.DIRECTORY
RESULT_PATH = ROOT / chronology.READINESS_RESULT
LEDGER_PATH = DIRECTORY / "READINESS_LEDGER.json"

PLAN_SCHEMA = "m120-readiness-plan-v1"
RESULT_SCHEMA = "m120-readiness-result-v1"

# Inherited from M118's gate unchanged, so this measures the route rather than a new instrument.
PROBE_MAX_TOKENS = 131072
STRESS_MAX_TOKENS = 131072
STRESS_MIN_COMPLETION_TOKENS = 32000
REASONING_EFFORT = "none"
MAX_REASONING_TOKENS = 0

RETRYABLE = ("pre_generation_429",)
MAX_RETRIES = 2


class ReadinessError(RuntimeError):
    """Fail closed. A readiness gate that guesses is not a gate."""


# The endpoint the frozen generator spec names. Asserted against it below rather than restated:
# a readiness gate that certified one endpoint while the generation used another would be
# certifying nothing.
COMPLETIONS_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SECRET_VARIABLE = "OPENROUTER_API_KEY"

# Response headers worth keeping. Account, credential and workspace surfaces never survive.
KEPT_HEADERS = ("date", "retry-after", "x-generation-id")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise ReadinessError("%s is not set; no network request was made" % SECRET_VARIABLE)
    return secret


def _http(url: str, *, method: str = "POST", body: bytes | None = None,
          timeout: int = 900) -> dict[str, Any]:
    """One physical request. No redirect, no retry, no connection reuse.

    This is the readiness gate's own transport, and it is deliberately the same shape as the one
    `run_m120_generation.py` uses for the qualifying request: same stdlib client, same headers,
    same treatment of an ambiguous failure as evidence rather than a crash.

    An earlier draft borrowed M117's transport instead. That was wrong twice over. It certified the
    route through code the qualifying generation will never execute, which is not what a readiness
    gate is for; and it dragged in a module that reaches for `fcntl` at import time -- for a *file
    lock*, nothing to do with HTTP -- which made the gate unrunnable anywhere but a POSIX host. The
    gate crashed on exactly that before sending a single request, which is the cheapest possible
    place to learn it.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ReadinessError("the readiness endpoint must use https")
    headers = {"Accept": "application/json", "Authorization": "Bearer %s" % _secret()}
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["X-OpenRouter-Metadata"] = "enabled"
        headers["X-OpenRouter-Cache"] = "false"
    started = _now()
    context = ssl.create_default_context()
    connection = None
    began = False
    try:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            via = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
            connection = http.client.HTTPSConnection(via.hostname, via.port or 80,
                                                     timeout=timeout, context=context)
            connection.set_tunnel(parsed.hostname, parsed.port or 443)
        else:
            connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                                     timeout=timeout, context=context)
        path = parsed.path or "/"
        if parsed.query:
            path = "%s?%s" % (path, parsed.query)
        began = True
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        observed_headers = {k.lower(): v for k, v in response.getheaders()
                            if k.lower() in KEPT_HEADERS}
    except Exception as exc:  # noqa: BLE001 -- ambiguity is evidence, not a crash
        return {"status": None, "body": None, "response_bytes": None, "started_at": started,
                "finished_at": _now(), "response_headers": {},
                "transport_failure_class": type(exc).__name__,
                "model_execution_cannot_be_excluded": began and body is not None}
    finally:
        if connection is not None:
            connection.close()
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        decoded = None
    return {"status": status, "body": decoded if isinstance(decoded, Mapping) else None,
            "response_bytes": len(raw), "started_at": started, "finished_at": _now(),
            "response_headers": observed_headers, "transport_failure_class": None,
            "model_execution_cannot_be_excluded": False}


def _census() -> dict[str, Any]:
    """The keyword census of the schema the generator will actually be handed."""
    return schema_tools.census(contract.candidate_schema())


def _matrix() -> list[dict[str, Any]]:
    return probes.build_matrix(_census())


def required_feature_classes() -> list[str]:
    return sorted(probes.required_feature_classes(_census()))


def _assert_stress_dominates() -> dict[str, Any]:
    """The stress schema must be at least as demanding as the candidate schema, on every axis.

    Checked here rather than asserted, because this is the whole reason the gate is being re-run:
    M118's stress schema did not dominate this candidate census, and a stress that is easier than
    the contract proves nothing about the contract.
    """
    candidate = _census()
    stressed = schema_tools.census(stress.build_stress_schema())
    dominates, shortfalls = schema_tools.census_dominates(stressed, candidate)
    if not dominates:
        raise ReadinessError(
            "the stress schema does not dominate the candidate schema census, so it cannot "
            "establish readiness for it: %s" % ", ".join(shortfalls))
    return {
        "candidate_schema_census": candidate,
        "stress_schema_census": stressed,
        "stress_dominates_the_candidate_schema": True,
        "stress_schema_is_not_the_candidate_schema": True,
        "why_not_the_candidate_schema":
            "sending the carrier contract at scale during DEVELOPMENT would preview the bank the "
            "frozen contract is about to draw, which is a degree of freedom over the contract",
    }


def _assert_endpoint_matches_the_frozen_spec() -> str:
    """Certifying one endpoint while the generation uses another would certify nothing."""
    from metamorphosis import m120_bank as bank  # noqa: PLC0415

    declared = bank.build_generator_spec(
        bank.build_analysis_plan(ROOT), ROOT)["generator_identity"]["endpoint"]
    if declared != COMPLETIONS_ENDPOINT:
        raise ReadinessError(
            "the readiness gate would probe %s while the frozen spec sends to %s"
            % (COMPLETIONS_ENDPOINT, declared))
    return declared


def plan() -> dict[str, Any]:
    matrix = _matrix()
    record = {
        "schema": PLAN_SCHEMA,
        "milestone": "M120", "hypothesis": "H65", "development": True,
        "purpose": "does the fixed route enforce the M120 candidate schema and serve a full-scale "
                   "conforming completion under it",
        "selects_among_providers": False,
        "compares_carrier_quality": False,
        "sends_the_qualifying_input": False,
        "probe_count": len(matrix),
        "mandatory_requests": len(matrix) + 1,
        "max_retries_per_request": MAX_RETRIES,
        "request_budget": (len(matrix) + 1) * (MAX_RETRIES + 1),
        "required_feature_classes": required_feature_classes(),
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "endpoint": _assert_endpoint_matches_the_frozen_spec(),
        "stress": _assert_stress_dominates(),
        "stress_min_completion_tokens": STRESS_MIN_COMPLETION_TOKENS,
        "reasoning_effort": REASONING_EFFORT,
        "max_reasoning_tokens": MAX_REASONING_TOKENS,
        "plan_sha256": "",
    }
    record["plan_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "plan_sha256"}))
    return record


def _request_body(prompt: str, schema: Mapping[str, Any], name: str,
                  max_tokens: int) -> dict[str, Any]:
    """One shape, for every request this gate sends."""
    fixed.assert_is_the_fixed_route(fixed.REQUESTED_MODEL, fixed.PROVIDER)
    return {
        "model": fixed.REQUESTED_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "provider": fixed.provider_block(),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": name, "strict": True, "schema": schema}},
        "max_tokens": max_tokens,
        "seed": 0, "stream": False, "temperature": 1.0,
        "reasoning": {"effort": REASONING_EFFORT},
    }


def _send(prompt: str, schema: Mapping[str, Any], name: str, max_tokens: int,
          budget: dict[str, int]) -> dict[str, Any]:
    body = _request_body(prompt, schema, name, max_tokens)
    for attempt in range(MAX_RETRIES + 1):
        if budget["spent"] >= budget["limit"]:
            raise ReadinessError("the frozen request budget is exhausted")
        budget["spent"] += 1
        observed = _http(COMPLETIONS_ENDPOINT, method="POST",
                         body=canonical_bytes(body), timeout=900)
        if observed.get("status") == 429 and not (observed.get("body") or {}).get("choices"):
            if attempt < MAX_RETRIES:
                continue  # explicit pre-generation 429, no completion, no execution evidence
        return observed
    raise ReadinessError("pre-generation 429 persisted beyond the frozen retry allowance")


def _reasoning_tokens(body: Mapping[str, Any]) -> int | None:
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    detail = usage.get("completion_tokens_details")
    if isinstance(detail, Mapping) and isinstance(detail.get("reasoning_tokens"), int):
        return detail["reasoning_tokens"]
    return usage.get("reasoning_tokens") if isinstance(usage.get("reasoning_tokens"), int) else None


def _parts(observed: Mapping[str, Any]) -> tuple[dict, dict, dict, dict]:
    body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
    choices = body.get("choices") if isinstance(body.get("choices"), list) else []
    first = choices[0] if choices and isinstance(choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first.get("message"), Mapping) else {}
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    return body, first, message, usage


def execute() -> dict[str, Any]:
    # Once-only, structurally rather than by an on-disk test. A file check alone is re-armed by
    # deleting the file; a result ever committed at HEAD blocks the gate whether or not it is
    # still on disk.
    if RESULT_PATH.exists():
        raise ReadinessError("a readiness result already exists; this gate is not redrawn")
    if chronology._head_blob(ROOT, chronology.READINESS_RESULT) is not None:
        raise ReadinessError(
            "a readiness result is committed at HEAD; this gate is not redrawn, and deleting the "
            "file does not re-arm it")
    permission = chronology.assert_stage_permitted("development", ROOT)
    chronology.assert_no_scientific_observation_yet(ROOT)
    frozen = plan()
    budget = {"spent": 0, "limit": frozen["request_budget"]}
    observations: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    DIRECTORY.mkdir(parents=True, exist_ok=True)

    def _persist_ledger(state: str, note: str = "") -> None:
        """Write what has been measured so far. An abort is when the evidence matters most."""
        LEDGER_PATH.write_bytes(canonical_bytes({
            "schema": "m120-readiness-ledger-v1",
            "milestone": "M120", "hypothesis": "H65", "development": True,
            "state": state, "note": note,
            "plan_sha256": frozen["plan_sha256"],
            "route": fixed.route(),
            "identity": identity,
            "observations": observations,
            "requests_spent": budget["spent"],
            "request_budget": budget["limit"],
            "raw_completion_persisted": False,
        }) + b"\n")

    _persist_ledger("started")
    unenforced: list[str] = []
    combined_conforms = False
    reasoning_intended = True

    for probe in _matrix():
        try:
            observed = _send(probe["prompt"], probe["schema"],
                             "m120_readiness_%s" % probe["name"], PROBE_MAX_TOKENS, budget)
        except ReadinessError as exc:
            _persist_ledger("instrument_aborted", "probe %s: %s" % (probe["name"], exc))
            raise
        body, first, message, usage = _parts(observed)
        attestation = fixed.identity_holds(body)
        identity = identity or attestation
        identities.append(attestation)
        content = message.get("content")
        conforms = False
        location = keyword = ""
        if isinstance(content, str):
            try:
                conforms, location, keyword = schema_tools.instance_is_valid(
                    json.loads(content), probe["schema"])
            except ValueError:
                conforms = False
        reasoning = _reasoning_tokens(body)
        if isinstance(reasoning, int) and reasoning > MAX_REASONING_TOKENS:
            reasoning_intended = False
        record = {
            "schema": "m120-capability-probe-observation-v1",
            "probe": probe["name"], "feature_class": probe["feature_class"],
            "development": True, "is_a_qualifying_call": False,
            "http_status": observed.get("status"),
            "finish_reason": first.get("finish_reason") if isinstance(
                first.get("finish_reason"), str) else None,
            "completion_tokens": usage.get("completion_tokens") if isinstance(
                usage.get("completion_tokens"), int) else None,
            "reasoning_tokens": reasoning,
            "content_present": isinstance(content, str) and bool(content.strip()),
            "schema_conforms": bool(conforms),
            "failing_schema_location": location, "first_failing_keyword": keyword,
            "served_model": body.get("model"), "served_provider": body.get("provider"),
            "raw_completion_persisted": False,
        }
        observations.append(record)
        # A probe is a *negative* instance for its feature class: the matrix asks the route for
        # output the schema forbids, so a conforming completion means the class was enforced.
        if probe["name"] == "combined":
            combined_conforms = bool(conforms)
        elif not conforms:
            unenforced.append(probe["feature_class"])
        _persist_ledger("probing", probe["name"])

    try:
        observed = _send(stress.STRESS_PROMPT, stress.build_stress_schema(),
                         stress.STRESS_SCHEMA_NAME, STRESS_MAX_TOKENS, budget)
    except ReadinessError as exc:
        _persist_ledger("instrument_aborted", "stress: %s" % exc)
        raise
    body, first, message, usage = _parts(observed)
    identities.append(fixed.identity_holds(body))
    tokens = usage.get("completion_tokens")
    content = message.get("content")
    conforms = False
    if isinstance(content, str):
        try:
            conforms = schema_tools.instance_is_valid(
                json.loads(content), stress.build_stress_schema())[0]
        except ValueError:
            conforms = False
    stress_record = {
        "ran": True,
        "http_status": observed.get("status"),
        "finish_reason": first.get("finish_reason") if isinstance(
            first.get("finish_reason"), str) else None,
        "completion_tokens": tokens if isinstance(tokens, int) else None,
        "reasoning_tokens": _reasoning_tokens(body),
        "schema_conforms": conforms,
        "raw_completion_persisted": False,
    }
    stress_record["holds"] = bool(
        stress_record["http_status"] == 200
        and stress_record["finish_reason"] == "stop"
        and conforms
        and isinstance(tokens, int) and tokens > STRESS_MIN_COMPLETION_TOKENS)

    verdict = "ready"
    if identity is None or not identity["holds"] or not all(r["holds"] for r in identities):
        verdict = "not_ready_identity"
    elif unenforced or not combined_conforms:
        verdict = "not_ready_features"
    elif not reasoning_intended:
        verdict = "not_ready_reasoning"
    elif not stress_record["holds"]:
        verdict = "not_ready_stress"

    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M120", "hypothesis": "H65", "development": True,
        "is_a_qualifying_call": False, "qualifying_input_was_sent": False,
        "is_evidence_for_h65": False, "advances_a_generality_gate": False,
        "carries_no_qualification_statistic": True,
        "plan_sha256": frozen["plan_sha256"],
        "candidate_schema_sha256": frozen["candidate_schema_sha256"],
        "stress_schema_dominates_the_candidate_schema": True,
        "chronology": permission,
        "route": fixed.route(),
        "observed_at": _now(),
        "identity": identity or {"holds": False, "failed_checks": ["no_response"]},
        "identity_per_request": identities,
        "identity_held_on_every_request": bool(identities) and all(
            row["holds"] for row in identities),
        "required_feature_classes": required_feature_classes(),
        "unenforced_feature_classes": sorted(set(unenforced)),
        "combined_probe_conforms": combined_conforms,
        "reasoning_state_as_intended": reasoning_intended,
        "token_capacity_stress": stress_record,
        "observations": observations,
        "requests_spent": budget["spent"],
        "raw_completion_persisted": False,
        "verdict": verdict,
        "ready": verdict == "ready",
        "result_sha256": "",
    }
    result["result_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in result.items() if k != "result_sha256"}))
    LEDGER_PATH.write_bytes(canonical_bytes(result) + b"\n")
    RESULT_PATH.write_bytes(canonical_bytes(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true",
                     help="print the frozen readiness plan; sends nothing")
    mode.add_argument("--execute", action="store_true",
                     help="run the DEVELOPMENT readiness gate against the fixed route")
    args = parser.parse_args()
    try:
        report = plan() if args.plan else execute()
    except (ReadinessError, chronology.ChronologyError, fixed.RouteError,
            schema_tools.SchemaError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    if args.plan:
        print(json.dumps({k: v for k, v in report.items() if k != "stress"},
                         indent=2, sort_keys=True))
        return 0
    print(json.dumps({
        "verdict": report["verdict"], "ready": report["ready"],
        "identity_held_on_every_request": report["identity_held_on_every_request"],
        "unenforced_feature_classes": report["unenforced_feature_classes"],
        "combined_probe_conforms": report["combined_probe_conforms"],
        "stress": {k: report["token_capacity_stress"][k]
                   for k in ("holds", "completion_tokens", "finish_reason", "schema_conforms")},
        "requests_spent": report["requests_spent"],
        "result_sha256": report["result_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
