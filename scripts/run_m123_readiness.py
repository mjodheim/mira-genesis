#!/usr/bin/env python3
"""DEVELOPMENT readiness for the M123 candidate schema. Not a qualifying call, and never redrawn.

M119 inherited M118's readiness result and treated it as evidence about its own generator contract.
It was evidence about M115's schema. That was defensible there, because M119 inherited M115's schema
byte for byte. It is not defensible here: M123's candidate schema uses the same eleven feature
classes and far more of them, and M118's stress schema does not dominate its keyword census. A gate
that carries across that gap is asserting a measurement nobody took.

So this runs again, against a stress schema that **does** dominate the M123 candidate census, and
`m123_chronology.assert_readiness_passed` refuses the scientific freeze until its result is
committed and says `ready`.

## What it measures, and what it deliberately does not

It measures the route: runtime identity on every request, each schema feature class the census
requires, the reasoning control, and one full-scale conforming completion. Every threshold is
inherited from M118's gate rather than chosen here, because a threshold rewritten for M123 could be
rewritten until the route passed.

It does **not** send the qualifying input, and the stress schema is not the candidate schema. Both
are deliberate. Sending the carrier contract at scale would hand the project a preview of what this
generator produces under the contract H68 is about to be frozen on -- and a preview of the bank is
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
# The contract is M122's, inherited by import and not re-authored. Nine of nine
# capability classes were observed enforced on this route under it, which is the one
# thing M122 did establish; rebuilding it to carry a new milestone number would
# discard that and re-open a question already answered.
from metamorphosis import m122_carrier_contract as contract  # noqa: E402
from metamorphosis import m123_chronology as chronology  # noqa: E402
from metamorphosis import m123_stress_schema as stress  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

DIRECTORY = ROOT / chronology.DIRECTORY
RESULT_PATH = ROOT / chronology.READINESS_RESULT
LEDGER_PATH = DIRECTORY / "READINESS_LEDGER.json"

PLAN_SCHEMA = "m123-readiness-plan-v1"
RESULT_SCHEMA = "m123-readiness-result-v1"

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
COMPLETIONS_ENDPOINT = contract.GENERATOR_ENDPOINT
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
    `run_m123_generation.py` uses for the qualifying request: same stdlib client, same headers,
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
    # Both constraints, checked together. A stress easier than the contract certifies nothing,
    # and a stress deeper than the route enforces fails for a reason unrelated to the contract --
    # which is what M123's predecessor schema did, and what the first draft of this stress would
    # have done, since it inherited the same duplicated subtree.
    try:
        proof = stress.assert_certifies(contract.candidate_schema(),
                                        contract.CERTIFIED_ARRAY_OF_OBJECT_LEVELS)
    except stress.StressError as exc:
        raise ReadinessError(str(exc)) from exc
    return {
        # The census counts keyword *occurrences*, not values, so `minItems: 74` and `minItems: 24`
        # are identical to it. Binding only the census left the plan digest unchanged when the
        # stress was resized, which would have made the allowance reset silently do nothing while
        # appearing to work. The schema's own bytes are bound as well.
        "stress_schema_sha256": sha256_hex(canonical_bytes(stress.build_stress_schema())),
        "stress_stations": stress.STATIONS,
        "stress_sizing_derivation": stress.sizing_derivation(),
        "candidate_schema_census": proof["candidate_schema_census"],
        "stress_schema_census": proof["stress_schema_census"],
        "stress_dominates_the_candidate_schema": True,
        "stress_is_within_the_certified_nesting": True,
        "stress_schema_is_not_the_candidate_schema": True,
        "why_not_the_candidate_schema":
            "sending the carrier contract at scale during DEVELOPMENT would preview the bank the "
            "frozen contract is about to draw, which is a degree of freedom over the contract",
    }


def _assert_endpoint_matches_the_frozen_spec() -> str:
    """Certifying one endpoint while the generation uses another would certify nothing.

    M123's predecessor hardcoded the endpoint in its generator spec and again in its gate, then
    asserted the two agreed. That works only once both exist, and this milestone builds the gate
    first on purpose. So the constant lives in the contract, both read it, and there is nothing to
    keep in step.
    """
    if COMPLETIONS_ENDPOINT != contract.GENERATOR_ENDPOINT:
        raise ReadinessError(
            "the readiness gate would probe %s while the contract sends to %s"
            % (COMPLETIONS_ENDPOINT, contract.GENERATOR_ENDPOINT))
    return COMPLETIONS_ENDPOINT


def plan() -> dict[str, Any]:
    matrix = _matrix()
    record = {
        "schema": PLAN_SCHEMA,
        "milestone": "M123", "hypothesis": "H68", "development": True,
        "purpose": "does the fixed route enforce the M123 candidate schema and serve a full-scale "
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


DELIVERY_VERDICT = "not_ready_delivery"

# Owner-authorised on 3 September 2026, bounded at three. A verdict of `not_ready_delivery` says
# the route did not answer: three requests exhausted their permitted retries on HTTP 429 and no
# completion came back. That is a delivery condition and not a capability finding, and the
# project's own delivery discipline -- M114's, inherited through M119 -- already holds that an
# explicit pre-generation 429 carrying no completion and no evidence of model execution is not a
# scientific outcome.
#
# The danger is obvious and is why the allowance is bounded rather than open: re-running until a
# quiet window returns `ready` would be selection by another name. So the rule is narrow.
#
#   * only a `not_ready_delivery` verdict may be superseded. Every other verdict -- `ready`, a
#     feature finding, an identity failure, enforcement failing open -- is FINAL on its first
#     occurrence and can never be re-run;
#   * at most three delivery-failed attempts in total, counted from the recorded archive rather
#     than from anyone's memory;
#   * every attempt is archived and none is deleted, so the sequence is auditable and a reader can
#     see how many windows were tried.
#
# An attempt that produced no verdict at all does not consume the allowance, because it yielded
# nothing to select on. Attempt 1 was terminated by the operator's own harness timeout during the
# stress and is archived with that reason stated.
DELIVERY_ALLOWANCE = 3
ATTEMPT_ARCHIVE_GLOB = "READINESS_ATTEMPT_*.json"


# Across every instrument, not per instrument. An apparatus revision genuinely produces a
# different measurement and its allowance starts fresh -- but unlimited revisions would be
# unlimited retries wearing a different name, so the total is capped as well.
TOTAL_DELIVERY_CEILING = 6


def _archived_delivery_attempts(plan_sha256: str | None = None) -> list[str]:
    """Delivery-failed attempts on record, counted from the archive and never from memory.

    Two corrections, both found when the guard refused a run it should have permitted.

    **An attempt is identified by its result digest, not by how many files hold it.** Archiving a
    result by hand beside the copy the gate writes itself made one attempt count as two, and the
    allowance was then exhausted by arithmetic rather than by anything the route did.

    **An attempt against a different instrument does not count against this one.** The owner
    authorised revision 1 and recorded that the allowance resets with it; recording that in a JSON
    file gave it no mechanical effect at all. The plan digest decides it instead, so the reset is a
    property of the apparatus rather than of a note somebody wrote.
    """
    seen: dict[str, str] = {}
    for path in sorted(DIRECTORY.glob(ATTEMPT_ARCHIVE_GLOB)):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("verdict") != DELIVERY_VERDICT:
            continue
        if plan_sha256 is not None and record.get("plan_sha256") != plan_sha256:
            continue
        digest = record.get("result_sha256") or path.name
        seen.setdefault(digest, path.name)
    return sorted(seen.values())


def _assert_the_allowance_permits_another_attempt() -> dict[str, Any]:
    """May this gate run again? Only after a delivery verdict, and only within the allowance."""
    current_plan = plan()["plan_sha256"]
    spent = _archived_delivery_attempts(current_plan)
    across_every_instrument = _archived_delivery_attempts(None)
    previous = None
    for source in (RESULT_PATH, None):
        if source is not None and source.exists():
            previous = json.loads(source.read_text(encoding="utf-8"))
            break
    if previous is None:
        committed = chronology._head_blob(ROOT, chronology.READINESS_RESULT)
        if committed is not None:
            previous = json.loads(committed.decode("utf-8"))
    if previous is not None:
        verdict = previous.get("verdict")
        if verdict != DELIVERY_VERDICT:
            raise ReadinessError(
                "a readiness result recording %r already exists; only a %r verdict may be "
                "superseded, and deleting the file does not re-arm the gate"
                % (verdict, DELIVERY_VERDICT))
    # The allowance is counted from the archive and enforced whether or not a result file is
    # present. An earlier draft checked it only when a previous result could be found, so deleting
    # the result would have permitted an unbounded run -- which is the "deleting the file re-arms
    # the gate" defect the once-only guard exists to prevent, reintroduced through the exception.
    if len(spent) >= DELIVERY_ALLOWANCE:
        raise ReadinessError(
            "the delivery allowance of %d is exhausted for this instrument (%s); M123 closes on "
            "the recorded delivery verdict rather than waiting for a quieter window"
            % (DELIVERY_ALLOWANCE, ", ".join(spent)))
    if len(across_every_instrument) >= TOTAL_DELIVERY_CEILING:
        raise ReadinessError(
            "the total delivery ceiling of %d across every instrument is reached (%s); revising "
            "the apparatus may not be used to buy further attempts indefinitely"
            % (TOTAL_DELIVERY_CEILING, ", ".join(across_every_instrument)))
    return {"delivery_attempts_against_this_instrument": spent,
            "delivery_attempts_across_every_instrument": across_every_instrument,
            "delivery_allowance": DELIVERY_ALLOWANCE,
            "total_delivery_ceiling": TOTAL_DELIVERY_CEILING,
            "instrument_plan_sha256": current_plan,
            "an_attempt_is_identified_by_its_result_digest_not_its_filename": True,
            "only_a_delivery_verdict_may_be_superseded": True}


def execute() -> dict[str, Any]:
    # Once-only, with one narrow and bounded exception the owner authorised: a verdict saying the
    # route never answered may be superseded, at most three times, and nothing else may be.
    allowance = _assert_the_allowance_permits_another_attempt()
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
            "schema": "m123-readiness-ledger-v1",
            "milestone": "M123", "hypothesis": "H68", "development": True,
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
    enforcement_failed_open: list[str] = []
    undeliverable: list[dict[str, Any]] = []
    combined_conforms = False
    reasoning_intended = True

    for probe in _matrix():
        try:
            observed = _send(probe["prompt"], probe["schema"],
                             "m123_readiness_%s" % probe["name"], PROBE_MAX_TOKENS, budget)
        except ReadinessError as exc:
            _persist_ledger("instrument_aborted", "probe %s: %s" % (probe["name"], exc))
            raise
        body, first, message, usage = _parts(observed)
        content = message.get("content")
        carries_completion = isinstance(content, str) and bool(content.strip())
        # M123 correction, named by M120's outcome. M123's predecessor attested runtime identity on
        # every response including HTTP 429s, which carry no router metadata -- so two rate-limited
        # requests made `identity_held_on_every_request` false and the ladder reported
        # `not_ready_identity` when the finding was a feature class. A retry-exhausted 429 is a
        # delivery outcome, not a substituted route, and identity is attested only where there is
        # something to attest.
        attestation = fixed.identity_holds(body) if carries_completion else None
        if attestation is not None:
            identity = identity or attestation
            identities.append(attestation)
        else:
            undeliverable.append({"probe": probe["name"],
                                  "http_status": observed.get("status"),
                                  "transport_failure_class":
                                      observed.get("transport_failure_class")})
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
        finish = (first.get("finish_reason")
                  if isinstance(first.get("finish_reason"), str) else None)
        # M123 correction, named by M120's outcome. Folding a truncated completion into
        # non-conformance loses the distinction between "the route emitted something the schema
        # refuses" and "the route emitted 101,379 tokens because enforcement failed open". The
        # second is what closed M123's predecessor, and it is now named.
        ran_away = finish == "length"
        if ran_away:
            enforcement_failed_open.append(probe["feature_class"])
        record = {
            "schema": "m123-capability-probe-observation-v1",
            "probe": probe["name"], "feature_class": probe["feature_class"],
            "development": True, "is_a_qualifying_call": False,
            "enforcement_failed_open": ran_away,
            "http_status": observed.get("status"),
            "finish_reason": finish,
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
            combined_conforms = bool(conforms) if carries_completion else None
        elif not conforms and carries_completion:
            unenforced.append(probe["feature_class"])
        # M123 correction, the defect M120 and M122 both carried. A probe that never answered is
        # not a probe that failed: `conforms` is false for an HTTP 429 exactly as it is for a
        # completion the schema refuses, and both milestones therefore listed feature classes as
        # unenforced when their probes had only ever been rate-limited. The verdict ladder checked
        # delivery first so the headline stayed right, but the field misdescribed the evidence --
        # and a reader trusting it would conclude the route lacks a capability nobody measured.
        _persist_ledger("probing", probe["name"])

    try:
        observed = _send(stress.STRESS_PROMPT, stress.build_stress_schema(),
                         stress.STRESS_SCHEMA_NAME, STRESS_MAX_TOKENS, budget)
    except ReadinessError as exc:
        _persist_ledger("instrument_aborted", "stress: %s" % exc)
        raise
    body, first, message, usage = _parts(observed)
    tokens = usage.get("completion_tokens")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        identities.append(fixed.identity_holds(body))
    else:
        undeliverable.append({"probe": "token_capacity_stress",
                              "http_status": observed.get("status"),
                              "transport_failure_class":
                                  observed.get("transport_failure_class")})
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
    elif undeliverable:
        # Distinct from an identity failure and from a feature finding: the route did not answer.
        verdict = "not_ready_delivery"
    elif enforcement_failed_open:
        verdict = "not_ready_enforcement_failed_open"
    elif unenforced or combined_conforms is False:
        verdict = "not_ready_features"
    elif not reasoning_intended:
        verdict = "not_ready_reasoning"
    elif not stress_record["holds"]:
        verdict = "not_ready_stress"

    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M123", "hypothesis": "H68", "development": True,
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
        "feature_classes_where_enforcement_failed_open": sorted(set(enforcement_failed_open)),
        "feature_classes_never_answered": sorted(
            {u["probe"] for u in undeliverable} - {"token_capacity_stress"}),
        "unenforced_means_answered_and_refused_not_merely_unanswered": True,
        "requests_that_carried_no_completion": undeliverable,
        "identity_is_attested_only_where_a_completion_exists": True,
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
    result["delivery_allowance"] = allowance
    result["result_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in result.items() if k != "result_sha256"}))
    LEDGER_PATH.write_bytes(canonical_bytes(result) + b"\n")
    RESULT_PATH.write_bytes(canonical_bytes(result) + b"\n")
    # Every attempt is archived under its own name and none is ever deleted, so the sequence of
    # windows tried is visible rather than reconstructible only from a commit log.
    index = len(list(DIRECTORY.glob(ATTEMPT_ARCHIVE_GLOB))) + 1
    (DIRECTORY / ("READINESS_ATTEMPT_%02d_%s.json" % (index, result["verdict"]))).write_bytes(
        canonical_bytes(result) + b"\n")
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
        "enforcement_failed_open": report["feature_classes_where_enforcement_failed_open"],
        "requests_that_carried_no_completion":
            len(report["requests_that_carried_no_completion"]),
        "combined_probe_conforms": report["combined_probe_conforms"],
        "stress": {k: report["token_capacity_stress"][k]
                   for k in ("holds", "completion_tokens", "finish_reason", "schema_conforms")},
        "requests_spent": report["requests_spent"],
        "result_sha256": report["result_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
