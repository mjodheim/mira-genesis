#!/usr/bin/env python3
"""The single H65 qualifying generation, its admission, its adequacy gate, and nothing else.

One physical request to one fixed route, under a chronology that must already be committed. What
comes back is admitted by a machine-only predicate before it is ever called a bank, and admission
here is not a filter over draws: the first completion carrying evidence of model execution consumes
the scientific generation opportunity. If admission fails there is no second completion, no repair
and no bank -- H65 ends `instrument_aborted`, which is not a result about the hypothesis.

M119 stopped there, and it was not enough. Its completion was admissible and its bank was not
testable, and the one authorized reveal was spent establishing that. So this runner asks the second
question in the same breath as the first: **can the frozen plan actually be run on this bank?** The
adequacy gate computes the qualifying carriers, the distinct structures and the paired demands the
bank would yield, and if any is short the milestone closes here, with the seal untaken and the
reveal unspent. The bank is not filtered, repaired, resampled or regenerated: an inadequate bank is
terminal.

Nothing in this script decides anything scientific. It delivers, attests, admits, gates, and
records.

The API key is read from `OPENROUTER_API_KEY` and is never written, printed, or placed anywhere but
the Authorization header of the one request. No completion content, no carrier content and no
provider free text is ever persisted by this script outside the response file the sealing step
encrypts and then removes.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m114_delivery as delivery  # noqa: E402
from metamorphosis import m115_identity as model_identity  # noqa: E402
from metamorphosis import m118_route as fixed  # noqa: E402
from metamorphosis import m120_adequacy as adequacy  # noqa: E402
from metamorphosis import m120_admission as admission  # noqa: E402
from metamorphosis import m120_bank as bank  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, contamination_hits, sha256_hex  # noqa: E402

MILESTONE = "M120"
HYPOTHESIS = "H65"
LEDGER_SCHEMA = "m120-delivery-ledger-v1"
ADMISSION_RECORD_SCHEMA = "m120-admission-v1"

EXPERIMENT = ROOT / chronology.DIRECTORY
PLAN_PATH = ROOT / chronology.ANALYSIS_PLAN
SPEC_PATH = ROOT / chronology.GENERATOR_SPEC
NONCE_PATH = ROOT / chronology.BANK_NONCE_COMMITMENT
LEDGER_PATH = ROOT / chronology.DELIVERY_LEDGER
ADMISSION_PATH = ROOT / chronology.ADMISSION
ADEQUACY_PATH = ROOT / chronology.ADEQUACY
RESPONSE_PATH = EXPERIMENT / "GENERATION_RESPONSE.json"
SECRET_VARIABLE = "OPENROUTER_API_KEY"

# Account, credential and workspace surfaces are removed from anything persisted, whatever the
# provider chooses to put in an envelope.
NEVER_PERSISTED_KEYS = ("account_id", "api_key", "credential_id", "key", "label",
                        "organization_id", "user_id", "workspace_id")


class GenerationError(RuntimeError):
    """The generation cannot proceed honestly. Every path fails closed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise GenerationError("%s is not set; no network request was made" % SECRET_VARIABLE)
    return secret


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerationError("cannot read %s: %s" % (path.name, exc))
    if not isinstance(value, dict):
        raise GenerationError("%s is not a JSON object" % path.name)
    return value


def _request(url: str, *, body: Mapping[str, Any], timeout: int = 1800) -> dict[str, Any]:
    """One physical POST. No redirect, no retry, no connection reuse."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise GenerationError("the generator endpoint must use https")
    context = ssl.create_default_context()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        via = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
        connection = http.client.HTTPSConnection(via.hostname, via.port or 80,
                                                 timeout=timeout, context=context)
        connection.set_tunnel(parsed.hostname, parsed.port or 443)
    else:
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                                 timeout=timeout, context=context)
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer %s" % _secret(),
        "Content-Type": "application/json",
        "X-OpenRouter-Metadata": "enabled",
        "X-OpenRouter-Cache": "false",
    }
    started = _now()
    try:
        connection.request("POST", parsed.path or "/", body=canonical_bytes(body), headers=headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        observed_headers = {k.lower(): v for k, v in response.getheaders()
                            if k.lower().startswith("x-")
                            or k.lower() in {"date", "server", "retry-after"}}
    finally:
        connection.close()
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        decoded = None
    return {"started_at": started, "finished_at": _now(), "status": status,
            "response_headers": observed_headers, "raw": raw,
            "body": decoded if isinstance(decoded, dict) else None}


def _safe_error(value: Any) -> Any:
    """Allowlisted operational failure evidence. Account, key and provider free text never survive."""
    if not isinstance(value, Mapping):
        return None
    error = value.get("error")
    if not isinstance(error, Mapping):
        return None
    metadata = error.get("metadata")
    allowed = ("provider_name", "limit_source", "retry_after_seconds", "is_byok", "error_code")
    safe_metadata = ({key: metadata.get(key) for key in allowed if key in metadata}
                     if isinstance(metadata, Mapping) else None)
    return {"code": error.get("code") if isinstance(error.get("code"), (str, int)) else None,
            "metadata": safe_metadata}


def _safe_body(body: Mapping[str, Any]) -> dict[str, Any]:
    """The completion, with router metadata projected and credential surfaces removed."""
    safe = dict(body)
    if "openrouter_metadata" in safe:
        safe["openrouter_metadata"] = model_identity.safe_router_metadata(
            safe.get("openrouter_metadata"))
    for key in NEVER_PERSISTED_KEYS:
        safe.pop(key, None)
    return safe


def _evidence(observed: Mapping[str, Any] | None, failure: str | None) -> dict[str, Any]:
    """Did a completion arrive, and if not, can model execution be excluded?"""
    if observed is None:
        return {"completion_present": False, "model_execution_cannot_be_excluded": True,
                "why": "transport failed before a response was read: %s" % (failure or "unknown")}
    body = observed.get("body") or {}
    choices = body.get("choices") or []
    first = choices[0] if isinstance(choices, list) and choices and isinstance(
        choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first.get("message"), Mapping) else {}
    content = message.get("content")
    completion = isinstance(content, str) and bool(content.strip())
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    executed = bool(choices) or bool(usage.get("completion_tokens")) or bool(
        first.get("finish_reason"))
    return {
        "completion_present": completion,
        "model_execution_cannot_be_excluded": bool(executed) and not completion,
        "why": ("a completion is present" if completion
                else "the response carries evidence the model executed" if executed
                else "HTTP %s carrying no completion and no evidence of execution"
                     % observed.get("status")),
    }


def _finish_reason(body: Mapping[str, Any]) -> Any:
    choices = body.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
        return choices[0].get("finish_reason")
    return None


def _validate_ledger(ledger: Mapping[str, Any], *, request_body_sha256: str) -> None:
    """M114's delivery rules, relabelled for M120 and delegated rather than reimplemented."""
    if ledger.get("schema") != LEDGER_SCHEMA or ledger.get("milestone") != MILESTONE:
        raise delivery.DeliveryError("the delivery ledger is not the M120 one")
    inherited = dict(ledger)
    inherited["schema"] = delivery.DELIVERY_LEDGER_SCHEMA
    inherited["milestone"] = delivery.MILESTONE
    delivery.validate_delivery_ledger(inherited, request_body_sha256=request_body_sha256)


def _preflight() -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any]]:
    """Everything that must hold before a single byte is sent."""
    permission = chronology.assert_qualifying_generation_permitted(ROOT)
    freeze = _load(ROOT / chronology.TESTED_SYSTEM_FREEZE)
    chronology.validate_freeze(freeze, ROOT)

    plan = _load(PLAN_PATH)
    bank.validate_analysis_plan(plan, ROOT)
    spec = _load(SPEC_PATH)
    bank.validate_generator_spec(spec, plan, ROOT)
    if spec.get("frozen_before_generation") is not True:
        raise GenerationError("the generator spec is not frozen")

    nonce_record = _load(NONCE_PATH)
    nonce = nonce_record.get("bank_nonce")
    if not isinstance(nonce, str) or len(nonce) != 64:
        raise GenerationError("the committed bank nonce is not a 64-character value")
    if nonce_record.get("bank_nonce_sha256") != sha256_hex(nonce.encode("ascii")):
        raise GenerationError("the committed bank nonce does not match its own digest")
    if freeze["bound_commitments"]["bank_nonce_sha256"] != nonce_record["bank_nonce_sha256"]:
        raise GenerationError("the freeze was taken against a different bank nonce")

    body = spec["canonical_request_body"]
    if sha256_hex(canonical_bytes(body)) != spec["canonical_request_body_sha256"]:
        raise GenerationError("the canonical request body does not match its frozen digest")
    hits = contamination_hits(canonical_bytes(body).decode("utf-8"))
    if hits:
        raise GenerationError("the request body carries project context: %s" % ", ".join(hits))
    only = (body.get("provider") or {}).get("only")
    if not isinstance(only, list) or len(only) != 1:
        raise GenerationError("the frozen request body must name exactly one provider")
    fixed.assert_is_the_fixed_route(body.get("model"), only[0])
    if RESPONSE_PATH.exists() or ADMISSION_PATH.exists() or ADEQUACY_PATH.exists():
        raise GenerationError("an H65 generation record already exists; a bank is never redrawn")
    return plan, spec, nonce, permission


def deliver() -> int:
    plan, spec, nonce, permission = _preflight()
    body = spec["canonical_request_body"]
    request_digest = spec["canonical_request_body_sha256"]

    ledger: dict[str, Any] = {
        "schema": LEDGER_SCHEMA, "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "request_body_sha256": request_digest,
        "delivery_semantics_inherited_unchanged_from": "M114",
        "route_version": fixed.ROUTE_VERSION,
        "chronology": permission,
        "bank_materialization_index": None,
        "attempts": [],
    }
    attempts: list[dict[str, Any]] = []
    observed: dict[str, Any] | None = None
    served: dict[str, Any] = {}

    while True:
        position = len(attempts) + 1
        waited = 0 if position == 1 else delivery.RETRY_WAIT_SECONDS
        if waited:
            print("waiting %d seconds before delivery attempt %d" % (waited, position))
            time.sleep(waited)
        observed, failure = None, None
        started = _now()
        try:
            observed = _request(spec["generator_identity"]["endpoint"], body=body)
        except Exception as exc:  # noqa: BLE001 -- ambiguity is terminal evidence, not a crash
            failure = type(exc).__name__

        served = (observed or {}).get("body") or {}
        evidence = _evidence(observed, failure)
        attestation = fixed.identity_holds(served) if evidence["completion_present"] else None
        safe_error = None if evidence["completion_present"] else _safe_error(served)
        attempt = {
            "attempt_index": position,
            "started_at": started,
            "finished_at": (observed or {}).get("finished_at") or _now(),
            "status": (observed or {}).get("status"),
            "requested_provider": fixed.PROVIDER,
            "served_provider": served.get("provider"),
            "requested_model": fixed.REQUESTED_MODEL,
            "served_model": served.get("model"),
            "response_headers": (observed or {}).get("response_headers") or {},
            "error_body": safe_error,
            "response_sha256": (sha256_hex(canonical_bytes(safe_error))
                                if safe_error is not None else None),
            "request_body_sha256": request_digest,
            "completion_present": evidence["completion_present"],
            "model_execution_cannot_be_excluded": evidence["model_execution_cannot_be_excluded"],
            "waited_seconds_before_this_attempt": waited,
            "identity_attestation": attestation,
            "finish_reason": _finish_reason(served),
            "transport_failure_class": failure,
            "raw_response_digest_was_intentionally_not_persisted": True,
            "outcome": None,
            "retry_permitted_by_the_frozen_rule": None,
        }
        attempt["outcome"] = delivery.classify_attempt(attempt)
        attempt["retry_permitted_by_the_frozen_rule"] = delivery.retry_permitted(
            attempt["outcome"], position)
        attempts.append(attempt)
        ledger["attempts"] = attempts
        ledger["bank_materialization_index"] = next(
            (a["attempt_index"] for a in attempts if a["outcome"] == "materialized"), None)
        LEDGER_PATH.write_bytes(canonical_bytes(ledger) + b"\n")
        _validate_ledger(ledger, request_body_sha256=request_digest)
        print("delivery attempt %d: %s" % (position, attempt["outcome"]))
        if attempt["outcome"] == "materialized" or not attempt[
                "retry_permitted_by_the_frozen_rule"]:
            break

    final = attempts[-1]
    if final["outcome"] != "materialized":
        print("H65 delivery ended without a completion. The hypothesis is untested, not refuted.")
        return 1

    # ---- machine-only admission, before anything is called a bank -----------------------------
    #
    # A pure predicate over the one completion. It parses, validates, decodes, envelopes and
    # digests, and it produces booleans, counts and digests only. It may not repair, strip,
    # extract, reformat, regenerate or choose among outputs, and no carrier content reaches this
    # record or the terminal.
    reasons: list[str] = []
    if not (isinstance(final["identity_attestation"], Mapping)
            and final["identity_attestation"].get("holds") is True):
        reasons.append("runtime identity was not exactly the fixed route")
    if final["finish_reason"] != "stop":
        reasons.append("the completion did not finish cleanly (finish_reason %r)"
                       % final["finish_reason"])

    raw = (observed or {}).get("raw") or b""
    verdict = admission.evaluate(
        raw, candidate_schema=bank.output_schema(ROOT), bank_nonce=nonce,
        request_body_sha256=request_digest)
    if verdict["admitted"] is not True:
        reasons.append("admission refused the completion at stage %r" % verdict["failure_stage"])

    record = {
        "schema": ADMISSION_RECORD_SCHEMA, "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "admitted": not reasons,
        "refusal_reasons": reasons,
        "identity_attestation": final["identity_attestation"],
        "finish_reason": final["finish_reason"],
        "admission": verdict,
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "delivery_attempt_index": final["attempt_index"],
        "the_single_generation_opportunity_is_spent": True,
        "no_completion_content_is_recorded_here": True,
    }
    ADMISSION_PATH.write_bytes(canonical_bytes(record) + b"\n")
    print("wrote %s" % ADMISSION_PATH.name)

    if reasons:
        print("REFUSED: the one completion was not admissible.")
        for reason in reasons:
            print("  - %s" % reason)
        print("The single generation opportunity is spent. Nothing is redrawn, repaired or "
              "regenerated. H65 ends instrument_aborted, which is not a result about the "
              "hypothesis.")
        return 1

    # ---- machine-only adequacy, before anything is sealed --------------------------------------
    #
    # M119's completion reached exactly this point and was sealed. It was admissible and it was not
    # testable, and the one authorized reveal was spent finding that out. The gate below asks the
    # question that was missing, on the same bank, at the same moment, and returns counts only.
    completion = json.loads(
        json.loads(raw.decode("utf-8"))["choices"][0]["message"]["content"])
    payload = admission.envelope_payload(completion, nonce)
    gate = adequacy.evaluate(admission.carriers_of(payload), plan)
    adequacy.validate_record(gate)
    ADEQUACY_PATH.write_bytes(canonical_bytes(gate) + b"\n")
    print("wrote %s" % ADEQUACY_PATH.name)

    if gate["adequate"] is not True:
        print("REFUSED: the bank is admissible and not scientifically adequate.")
        for shortfall in gate["shortfalls"]:
            print("  - %s" % shortfall)
        print("  qualifying carriers %d (minimum %d), distinct structures %d (minimum %d), "
              "paired demands %d (minimum %d)"
              % (gate["qualifying_carriers"], gate["minimum_qualifying_carriers"],
                 gate["distinct_qualifying_structures"],
                 gate["minimum_distinct_qualifying_structures"],
                 gate["paired_demands_available"],
                 gate["minimum_paired_demands_for_attainable_significance"]))
        print("The bank is not filtered, repaired, resampled or regenerated, and no reveal is "
              "authorized. H65 ends instrument_aborted, which is not a result about the "
              "hypothesis. Seal the response for custody and close the milestone.")
        RESPONSE_PATH.write_bytes(canonical_bytes(_response_record(spec, request_digest, nonce,
                                                                  final, served)) + b"\n")
        print("wrote %s for custody; seal it, and do not authorize a reveal." % RESPONSE_PATH.name)
        return 1

    RESPONSE_PATH.write_bytes(canonical_bytes(_response_record(spec, request_digest, nonce,
                                                              final, served)) + b"\n")
    print("wrote %s" % RESPONSE_PATH.name)
    print("qualifying carriers %d, distinct structures %d, paired demands %d"
          % (gate["qualifying_carriers"], gate["distinct_qualifying_structures"],
             gate["paired_demands_available"]))
    print("Seal it before any scientific process reads the carrier content.")
    return 0


def _response_record(spec: Mapping[str, Any], request_digest: str, nonce: str,
                     final: Mapping[str, Any], served: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m120-generation-response-v1", "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "request_body_sha256": request_digest,
        "bank_nonce_sha256": sha256_hex(nonce.encode("ascii")),
        "delivery_attempt_index": final["attempt_index"],
        "status": final["status"],
        "served_model": final["served_model"], "served_provider": final["served_provider"],
        "runtime_identity_attestation": final["identity_attestation"],
        "started_at": final["started_at"], "finished_at": final["finished_at"],
        "body": _safe_body(served),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deliver", action="store_true", required=True,
                        help="send the one qualifying request")
    parser.parse_args()
    try:
        return deliver()
    except (GenerationError, adequacy.AdequacyError, admission.AdmissionError,
            admission.PurityError, bank.BankError, chronology.ChronologyError,
            delivery.DeliveryError, fixed.RouteError) as exc:
        print("REFUSED: %s" % exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
