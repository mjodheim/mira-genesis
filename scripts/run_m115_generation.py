"""M115/H60 generator lifecycle.

This is the first real entry point for the M115 apparatus.  It deliberately separates the two
owner-authorized freezes from qualifying delivery:

    --freeze-plan   promote ANALYSIS_PLAN_CANDIDATE.json once
    --freeze-spec   deterministically derive and freeze the generator spec once
    --deliver       spend the frozen M114 delivery budget against Alibaba

No DEVELOPMENT smoke lives here. Provider suitability was measured separately before H60 opened.
The qualifying request carries the M114 body byte-for-byte except for its frozen provider route.
M115 adds *headers* that ask OpenRouter to expose routing provenance and disable response caching;
those headers are not model-visible prompt content.

A completion always spends the single materialization budget. It becomes an H60 carrier bank only
when the same response positively attests the owner-authorized alias -> canonical checkpoint
identity. A completion with missing/substituted/ambiguous identity is terminal and is never redrawn.
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
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_carrier_bank as bank  # noqa: E402
from metamorphosis import m115_delivery as delivery  # noqa: E402
from metamorphosis import m115_identity as model_identity  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, contamination_hits, sha256_hex  # noqa: E402

EXPERIMENT = ROOT / bank.EXPERIMENT_DIRECTORY
PLAN_CANDIDATE_PATH = ROOT / bank.ANALYSIS_PLAN_CANDIDATE_PATH
PLAN_PATH = ROOT / bank.ANALYSIS_PLAN_PATH
SPEC_CANDIDATE_PATH = EXPERIMENT / "GENERATOR_SPEC_CANDIDATE.json"
SPEC_PATH = ROOT / bank.GENERATOR_SPEC_PATH
LEDGER_PATH = ROOT / bank.DELIVERY_LEDGER_PATH
RESPONSE_PATH = EXPERIMENT / "GENERATION_RESPONSE.json"
SECRET_VARIABLE = "OPENROUTER_API_KEY"


class GenerationError(RuntimeError):
    pass


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _shown(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise GenerationError("%s is not set; no network request was made" % SECRET_VARIABLE)
    return secret


def _request(url: str, *, body: Mapping[str, Any], timeout: int = 900) -> dict[str, Any]:
    """One physical POST, no redirect, retry or connection reuse; metadata/cache headers explicit."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise GenerationError("the generator endpoint must use https")
    context = ssl.create_default_context()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        via = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
        connection = http.client.HTTPSConnection(
            via.hostname, via.port or 80, timeout=timeout, context=context
        )
        connection.set_tunnel(parsed.hostname, parsed.port or 443)
    else:
        connection = http.client.HTTPSConnection(
            parsed.hostname, parsed.port or 443, timeout=timeout, context=context
        )
    payload = canonical_bytes(body)
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer %s" % _secret(),
        "Content-Type": "application/json",
        "X-OpenRouter-Metadata": "enabled",
        "X-OpenRouter-Cache": "false",
    }
    started = _now()
    try:
        connection.request("POST", parsed.path or "/", body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        observed_headers = {
            key.lower(): value
            for key, value in response.getheaders()
            if key.lower().startswith("x-") or key.lower() in {"date", "server", "retry-after"}
        }
    finally:
        connection.close()
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        decoded = None
    return {
        "started_at": started,
        "finished_at": _now(),
        "status": status,
        "response_headers": observed_headers,
        "raw_response_sha256": sha256_hex(raw),
        "response_bytes": len(raw),
        "body": decoded,
        "raw_text": None if decoded is not None else raw.decode("utf-8", "replace"),
    }


def _safe_error(value: Any) -> Any:
    """Allowlist operational failure evidence; account/key/provider free-text never survives."""
    if not isinstance(value, Mapping):
        return None
    error = value.get("error")
    if not isinstance(error, Mapping):
        return None
    metadata = error.get("metadata")
    safe_metadata = None
    if isinstance(metadata, Mapping):
        allowed = (
            "provider_name",
            "limit_source",
            "retry_after_seconds",
            "is_byok",
            "error_code",
        )
        safe_metadata = {key: metadata.get(key) for key in allowed if key in metadata}
    return {
        "code": error.get("code") if isinstance(error.get("code"), (str, int)) else None,
        "metadata": safe_metadata,
    }


def _safe_materialized_body(body: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve the completion while replacing router metadata with its explicit safe projection."""
    safe = dict(body)
    if "openrouter_metadata" in safe:
        safe["openrouter_metadata"] = model_identity.safe_router_metadata(
            safe.get("openrouter_metadata")
        )
    # Explicitly refuse known account/credential surfaces even if OpenRouter changes envelopes.
    for key in (
        "user_id",
        "workspace_id",
        "credential_id",
        "api_key",
        "key",
        "label",
        "account_id",
        "organization_id",
    ):
        safe.pop(key, None)
    return safe


def _evidence(observed: Mapping[str, Any] | None, failure: str | None) -> dict[str, Any]:
    if observed is None:
        return {
            "completion_present": False,
            "model_execution_cannot_be_excluded": True,
            "why": "transport failed before a response was read: %s" % (failure or "unknown"),
        }
    decoded = observed.get("body")
    body = decoded if isinstance(decoded, Mapping) else {}
    choices = body.get("choices") or []
    first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first.get("message"), Mapping) else {}
    content = message.get("content")
    completion = isinstance(content, str) and bool(content.strip())
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    tokens = usage.get("completion_tokens") if isinstance(usage, Mapping) else 0
    executed = bool(choices) or bool(tokens) or bool(first.get("finish_reason"))
    return {
        "completion_present": completion,
        "model_execution_cannot_be_excluded": bool(executed) and not completion,
        "why": (
            "a completion is present"
            if completion
            else "the response carries evidence the model executed"
            if executed
            else "HTTP %s carrying no completion and no evidence of execution" % observed.get("status")
        ),
    }


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerationError("cannot read %s: %s" % (_shown(path), exc))
    if not isinstance(value, dict):
        raise GenerationError("%s is not a JSON object" % _shown(path))
    return value


def freeze_plan() -> dict[str, Any]:
    if PLAN_PATH.is_file():
        raise GenerationError("ANALYSIS_PLAN.json already exists; the plan freeze is consumed once")
    if SPEC_PATH.is_file() or LEDGER_PATH.is_file() or RESPONSE_PATH.is_file():
        raise GenerationError("cannot freeze the plan behind a generator/delivery history")
    plan = _load_object(PLAN_CANDIDATE_PATH)
    bank.validate_analysis_plan(plan, root=ROOT)
    PLAN_PATH.write_bytes(canonical_bytes(plan) + b"\n")
    return {
        "schema": "m115-plan-freeze-v1",
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "plan_commitment_sha256": plan["plan_commitment_sha256"],
        "frozen_at": _now(),
        "note": "timestamp is the action record; frozen plan bytes are the committed candidate bytes",
    }


def prepare_spec_candidate(*, write: bool) -> dict[str, Any]:
    spec = bank.build_generator_spec_candidate(ROOT)
    bank.validate_generator_spec(spec, root=ROOT)
    if write:
        if SPEC_PATH.is_file() or LEDGER_PATH.is_file():
            raise GenerationError("cannot rewrite a candidate behind a frozen spec/delivery history")
        SPEC_CANDIDATE_PATH.write_bytes(canonical_bytes(spec) + b"\n")
    return spec


def freeze_spec() -> dict[str, Any]:
    if not PLAN_PATH.is_file():
        raise GenerationError("freeze the M115 analysis plan before the generator identity")
    if SPEC_PATH.is_file():
        raise GenerationError("GENERATOR_SPEC.json already exists; identity freeze is consumed once")
    if LEDGER_PATH.is_file() or RESPONSE_PATH.is_file():
        raise GenerationError("cannot freeze a generator identity behind delivery history")
    plan = _load_object(PLAN_PATH)
    bank.validate_analysis_plan(plan, root=ROOT)
    candidate = bank.build_generator_spec_candidate(ROOT)
    if SPEC_CANDIDATE_PATH.is_file():
        recorded = _load_object(SPEC_CANDIDATE_PATH)
        if recorded != candidate:
            raise GenerationError("recorded generator candidate differs from deterministic builder")
    spec = dict(candidate)
    for key in spec.pop("unset_before_freeze", []):
        if key != "frozen_before_generation":
            raise GenerationError("unknown freeze field %r" % key)
    spec["frozen_before_generation"] = True
    spec["frozen_at"] = _now()
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    bank.validate_generator_spec(
        spec, root=ROOT, plan_commitment_sha256=plan["plan_commitment_sha256"]
    )
    SPEC_PATH.write_bytes(canonical_bytes(spec) + b"\n")
    return {
        "schema": "m115-generator-freeze-v1",
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "frozen_at": spec["frozen_at"],
        "plan_commitment_sha256": plan["plan_commitment_sha256"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
        "provider": model_identity.SELECTED_PROVIDER,
        "requested_alias": model_identity.REQUESTED_MODEL,
        "canonical_checkpoint_required_at_runtime": model_identity.CANONICAL_CHECKPOINT,
        "identity_semantics": model_identity.IDENTITY_VERSION,
    }


def load_frozen_spec() -> dict[str, Any]:
    if not PLAN_PATH.is_file() or not SPEC_PATH.is_file():
        raise GenerationError("M115 plan and generator identity must both be frozen before delivery")
    plan = _load_object(PLAN_PATH)
    bank.validate_analysis_plan(plan, root=ROOT)
    spec = _load_object(SPEC_PATH)
    bank.validate_generator_spec(
        spec, root=ROOT, plan_commitment_sha256=plan["plan_commitment_sha256"]
    )
    if spec.get("frozen_before_generation") is not True:
        raise GenerationError("generator spec is not frozen")
    return spec


def _read_ledger() -> dict[str, Any] | None:
    return _load_object(LEDGER_PATH) if LEDGER_PATH.is_file() else None


def _write_ledger(ledger: dict[str, Any]) -> None:
    LEDGER_PATH.write_bytes(canonical_bytes(ledger) + b"\n")


def deliver(spec: Mapping[str, Any]) -> int:
    commitment = spec["spec_commitment_sha256"]
    body = spec["canonical_request_body"]
    body_bytes = canonical_bytes(body)
    if sha256_hex(body_bytes) != spec["canonical_request_body_sha256"]:
        raise GenerationError("canonical request body does not match its frozen digest")
    if contamination_hits(body_bytes.decode("utf-8")):
        raise GenerationError("canonical request body carries project context")
    if RESPONSE_PATH.is_file():
        raise GenerationError("GENERATION_RESPONSE.json already exists; a bank is never redrawn")

    ledger = _read_ledger() or {
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "spec_commitment_sha256": commitment,
        "request_body_sha256": spec["canonical_request_body_sha256"],
        "delivery_semantics_inherited_unchanged_from": "M114",
        "identity_semantics": model_identity.IDENTITY_VERSION,
        "bank_materialization_index": None,
        "attempts": [],
    }
    if ledger.get("spec_commitment_sha256") != commitment:
        raise GenerationError("existing delivery ledger belongs to another frozen spec")
    attempts = list(ledger.get("attempts") or [])
    if attempts:
        last = attempts[-1]
        if not delivery.retry_permitted(last.get("outcome"), len(attempts)):
            raise GenerationError("delivery sequence is terminal under the frozen M114 rule")

    while True:
        position = len(attempts) + 1
        waited = 0 if position == 1 else delivery.RETRY_WAIT_SECONDS
        if waited:
            print("waiting %d seconds before delivery attempt %d" % (waited, position))
            time.sleep(waited)
        observed: dict[str, Any] | None = None
        failure: str | None = None
        started = _now()
        try:
            observed = _request(spec["generator_identity"]["endpoint"], body=body)
        except Exception as exc:  # noqa: BLE001 -- ambiguity is terminal evidence, not a crash
            failure = "%s" % type(exc).__name__

        decoded = (observed or {}).get("body")
        served = decoded if isinstance(decoded, Mapping) else {}
        evidence = _evidence(observed, failure)
        identity_attestation = (
            model_identity.attest_completion_response(served)
            if evidence["completion_present"]
            else None
        )
        safe_error = None if evidence["completion_present"] else _safe_error(served)
        safe_response_digest = sha256_hex(canonical_bytes(safe_error)) if safe_error is not None else None
        attempt = {
            "attempt_index": position,
            "started_at": started,
            "finished_at": (observed or {}).get("finished_at") or _now(),
            "status": (observed or {}).get("status"),
            "requested_provider": model_identity.SELECTED_PROVIDER,
            "served_provider": served.get("provider"),
            "requested_model": model_identity.REQUESTED_MODEL,
            "served_model": served.get("model"),
            "response_headers": (observed or {}).get("response_headers") or {},
            "error_body": safe_error,
            "response_sha256": safe_response_digest,
            "request_body_sha256": spec["canonical_request_body_sha256"],
            "completion_present": evidence["completion_present"],
            "model_execution_cannot_be_excluded": evidence["model_execution_cannot_be_excluded"],
            "outcome": None,
            "retry_permitted_by_the_frozen_rule": None,
            "waited_seconds_before_this_attempt": waited,
            "identity_attestation": identity_attestation,
            "raw_response_digest_was_intentionally_not_persisted": True,
            "transport_failure_class": failure,
        }
        attempt["outcome"] = delivery.classify_attempt(attempt)
        attempt["retry_permitted_by_the_frozen_rule"] = delivery.retry_permitted(
            attempt["outcome"], position
        )
        attempts.append(attempt)
        ledger["attempts"] = attempts
        ledger["bank_materialization_index"] = next(
            (item["attempt_index"] for item in attempts if item["outcome"] == "materialized"), None
        )
        _write_ledger(ledger)
        delivery.validate_delivery_ledger(
            ledger,
            spec_commitment_sha256=commitment,
            request_body_sha256=spec["canonical_request_body_sha256"],
        )
        print("delivery attempt %d: %s" % (position, attempt["outcome"]))

        if attempt["outcome"] == "materialized":
            break
        if not attempt["retry_permitted_by_the_frozen_rule"]:
            break

    final = attempts[-1]
    if final["outcome"] != "materialized":
        print("M115 delivery ended without a bank; H60 remains untested unless downstream science ran.")
        return 1

    attestation = final.get("identity_attestation")
    if not isinstance(attestation, Mapping) or attestation.get("holds") is not True:
        print("REFUSED: a completion materialized but M115 runtime identity was not attested.")
        print("The single bank budget is spent. Nothing is redrawn.")
        return 1

    safe_served = _safe_materialized_body(served)
    RESPONSE_PATH.write_bytes(
        canonical_bytes(
            {
                "schema": "m115-generation-response-v1",
                "milestone": bank.MILESTONE,
                "hypothesis": bank.HYPOTHESIS,
                "spec_commitment_sha256": commitment,
                "delivery_attempt_index": final["attempt_index"],
                "delivery_attempts_made": len(attempts),
                "request_body_sha256": spec["canonical_request_body_sha256"],
                "status": final["status"],
                "served_model": final["served_model"],
                "served_provider": final["served_provider"],
                "runtime_identity_attestation": attestation,
                "started_at": final["started_at"],
                "finished_at": final["finished_at"],
                "body": safe_served,
            }
        )
        + b"\n"
    )
    print("wrote %s" % _shown(RESPONSE_PATH))
    print("Seal it before any scientific process reads the carrier content.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-spec", action="store_true")
    mode.add_argument("--freeze-plan", action="store_true")
    mode.add_argument("--freeze-spec", action="store_true")
    mode.add_argument("--deliver", action="store_true")
    parser.add_argument("--write", action="store_true", help="with --prepare-spec, record the candidate")
    args = parser.parse_args()
    try:
        if args.prepare_spec:
            report = prepare_spec_candidate(write=args.write)
        elif args.freeze_plan:
            report = freeze_plan()
        elif args.freeze_spec:
            report = freeze_spec()
        else:
            return deliver(load_frozen_spec())
    except (GenerationError, bank.CarrierBankError, delivery.DeliveryError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
