"""M113 generator phase -- discovery, a development smoke test, and one qualifying invocation.

This is the only program in the milestone permitted to reach a network, and it is deliberately
separate from `run_m113_qualification.py`, which measures its own silence inside a sealed scope.
`P15` reads both halves of that boundary and neither is a number a runner chooses.

**Nothing here has ever been executed.** The environment it was written in has no Hermes client, no
OpenRouter credential and no route to `openrouter.ai` -- the egress policy refuses the host with a
403 on the CONNECT tunnel -- so the discovery step that pins a provider could not run and the spec
is a candidate rather than a freeze. The file exists so that the freeze, when the instrument is
available, consumes a contract written before the identity it pins was known.

Three modes, and only the third is a gate:

`--discover`   DEVELOPMENT. Asks the endpoint which providers serve the exact model and what
               parameters each supports. Reads only; writes no artifact the freeze depends on.
`--smoke`      DEVELOPMENT. One structured-output probe on a throwaway input, to prove the
               transport, the pinned provider and strict decoding work before anything is frozen.
               It refuses the qualifying input by digest, so a smoke test can never become a bank.
`--qualify`    The single invocation, against a frozen spec, once.

On retries. There are none, at any layer, and that is enforced rather than requested: the client is
`http.client` from the standard library, which does not retry, driven directly rather than through
`urllib`'s opener stack. No third-party client library is imported -- `requests`, `httpx` and the
vendor SDKs all carry retry behaviour of their own that would have to be disabled correctly, and
the way to disable it correctly is not to have it. A physical request that fails is a failed
attempt, it is written to the ledger as one, and the frozen spec then admits no further
materialization.

On the secret. It is read from the environment at the moment of use and never stored, logged,
printed, digested or written. The recorded request body is the body without its headers, which is
what the spec commits to and what the ledger and the public record can carry safely.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m113_carrier_bank as bank  # noqa: E402
from metamorphosis.blind_bank_protocol import (  # noqa: E402
    canonical_bytes,
    contamination_hits,
    sha256_hex,
)

EXPERIMENT = ROOT / "experiments" / "M113"
SPEC_PATH = EXPERIMENT / "GENERATOR_SPEC.json"
CANDIDATE_SPEC_PATH = EXPERIMENT / "GENERATOR_SPEC_CANDIDATE.json"
PLAN_PATH = EXPERIMENT / "ANALYSIS_PLAN.json"
LEDGER_PATH = EXPERIMENT / "GENERATION_LEDGER.json"
RAW_RESPONSE_PATH = EXPERIMENT / "GENERATION_RESPONSE.json"
DISCOVERY_PATH = EXPERIMENT / "PROVIDER_DISCOVERY_DEVELOPMENT.json"
SMOKE_PATH = EXPERIMENT / "TRANSPORT_SMOKE_DEVELOPMENT.json"

SECRET_VARIABLE = "OPENROUTER_API_KEY"
LEDGER_SCHEMA = "mira-blind-bank-generation-ledger-v1"

# A throwaway input for the smoke test. It shares no sentence with the qualifying input, asks for a
# shape the experiment has no use for, and is checked against the qualifying digest before it is
# sent so that a mistake here cannot quietly become the bank.
SMOKE_INPUT = (
    'Emit a JSON object with a single key "colours" whose value is a list of exactly 2 entries.\n'
    "Each entry is an object with one key, \"name\", whose value is a lowercase English word.\n"
)
SMOKE_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "colours": {
            "items": {
                "additionalProperties": False,
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "type": "object",
            },
            "maxItems": 2,
            "minItems": 2,
            "type": "array",
        }
    },
    "required": ["colours"],
    "type": "object",
}


class GenerationError(RuntimeError):
    """Raised whenever the instrument cannot do exactly what was frozen."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    value = os.environ.get(SECRET_VARIABLE)
    if not value:
        raise GenerationError(
            "%s is not set. The credential is read from the environment at the moment of use and "
            "is never stored in this repository." % SECRET_VARIABLE
        )
    return value


def request(
    url: str,
    *,
    method: str = "POST",
    body: dict[str, Any] | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    """One physical request. No retry, no redirect following, no connection reuse.

    The return value carries the response metadata the record needs -- status, the identifying
    headers, and the decoded body -- and never the request headers, one of which is the credential.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        raise GenerationError("the generator endpoint must be https")
    payload = canonical_bytes(body) if body is not None else None

    connection = http.client.HTTPSConnection(
        parsed.hostname,
        parsed.port or 443,
        timeout=timeout,
        context=ssl.create_default_context(),
    )
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer %s" % _secret(),
        "Content-Type": "application/json",
    }
    started = _now()
    try:
        connection.request(method, parsed.path or "/", body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        # `X-Request-Id` and the rest are the only handle a third party has on this call later.
        observed_headers = {
            key.lower(): value
            for key, value in response.getheaders()
            if key.lower().startswith("x-") or key.lower() in {"date", "server"}
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
        "response_sha256": sha256_hex(raw),
        "response_bytes": len(raw),
        "body": decoded,
        "raw_text": None if decoded is not None else raw.decode("utf-8", "replace"),
    }


def load_spec(*, frozen_required: bool) -> dict[str, Any]:
    path = SPEC_PATH if frozen_required else (
        SPEC_PATH if SPEC_PATH.is_file() else CANDIDATE_SPEC_PATH
    )
    if not path.is_file():
        raise GenerationError("no generator spec at %s" % path.relative_to(ROOT))
    spec = json.loads(path.read_text(encoding="utf-8"))
    if frozen_required:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        bank.validate_generator_spec(
            spec, root=ROOT, plan_commitment_sha256=plan.get("plan_commitment_sha256")
        )
    return spec


# ----------------------------------------------------------------------------------------
# DEVELOPMENT: which providers actually serve the exact model, and with what parameters
# ----------------------------------------------------------------------------------------


def discover(spec: dict[str, Any], *, write: bool) -> dict[str, Any]:
    model = spec["generator_identity"]["model"]
    endpoint = urllib.parse.urlsplit(spec["generator_identity"]["endpoint"])
    base = "%s://%s" % (endpoint.scheme, endpoint.netloc)

    catalogue = request("%s/api/v1/models" % base, method="GET", body=None, timeout=120)
    entries = ((catalogue.get("body") or {}).get("data")) or []
    exact = [item for item in entries if item.get("id") == model]

    endpoints = request(
        "%s/api/v1/models/%s/endpoints" % (base, urllib.parse.quote(model, safe="/")),
        method="GET",
        body=None,
        timeout=120,
    )
    served = ((endpoints.get("body") or {}).get("data") or {}).get("endpoints") or []

    report = {
        "schema": "m113-provider-discovery-development-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "milestone": "M113",
        "requested_model": model,
        "model_is_in_the_catalogue": bool(exact),
        "catalogue_entry": exact[0] if exact else None,
        "providers": [
            {
                "name": item.get("provider_name"),
                "context_length": item.get("context_length"),
                "supported_parameters": sorted(item.get("supported_parameters") or []),
                "supports_structured_outputs": "structured_outputs"
                in (item.get("supported_parameters") or []),
                "quantization": item.get("quantization"),
                "status": item.get("status"),
            }
            for item in served
        ],
        "observed_at": _now(),
    }
    report["providers_that_can_serve_the_frozen_request"] = sorted(
        entry["name"]
        for entry in report["providers"]
        if entry["supports_structured_outputs"] and entry["name"]
    )
    if write:
        DISCOVERY_PATH.write_bytes(canonical_bytes(report) + b"\n")
    return report


# ----------------------------------------------------------------------------------------
# DEVELOPMENT: does the frozen transport, provider and strict decoding actually work
# ----------------------------------------------------------------------------------------


def smoke(spec: dict[str, Any], *, write: bool) -> dict[str, Any]:
    identity = spec["generator_identity"]
    provider = identity.get("provider")
    if not provider:
        raise GenerationError(
            "the smoke test exists to exercise a chosen provider; run --discover and choose one"
        )

    qualifying_digest = sha256_hex(
        (ROOT / spec["qualifying_input"]["path"]).read_bytes()
    )
    if sha256_hex(SMOKE_INPUT.encode("utf-8")) == qualifying_digest:
        raise GenerationError("the smoke input is the qualifying input")
    if SMOKE_INPUT.strip() in (ROOT / spec["qualifying_input"]["path"]).read_text(encoding="utf-8"):
        raise GenerationError("the smoke input is drawn from the qualifying input")

    body = {
        "max_tokens": 256,
        "messages": [{"content": SMOKE_INPUT, "role": "user"}],
        "model": identity["model"],
        "provider": {
            "allow_fallbacks": False,
            "only": [provider],
            "require_parameters": bool(spec["routing"].get("require_parameters")),
        },
        "response_format": {
            "json_schema": {"name": "colours", "schema": SMOKE_SCHEMA, "strict": True},
            "type": "json_schema",
        },
        "stream": False,
        "temperature": spec["sampling"]["temperature"],
    }
    observed = request(identity["endpoint"], body=body)
    served = (observed.get("body") or {})

    report = {
        "schema": "m113-transport-smoke-development-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "milestone": "M113",
        "request_body_sha256": sha256_hex(canonical_bytes(body)),
        "status": observed["status"],
        "served_model": served.get("model"),
        "served_provider": served.get("provider"),
        "id": served.get("id"),
        "finish_reason": (
            (served.get("choices") or [{}])[0].get("finish_reason") if served.get("choices") else None
        ),
        "usage": served.get("usage"),
        "response_headers": observed["response_headers"],
        "structured_output_parsed": None,
        "observed_at": observed["finished_at"],
    }
    if served.get("choices"):
        content = (served["choices"][0].get("message") or {}).get("content")
        try:
            report["structured_output_parsed"] = isinstance(json.loads(content), dict)
        except (TypeError, ValueError):
            report["structured_output_parsed"] = False

    report["identity_served_matches_identity_requested"] = bool(
        report["served_model"] == identity["model"]
        and (report["served_provider"] in (None, provider) or report["served_provider"] == provider)
    )
    if write:
        SMOKE_PATH.write_bytes(canonical_bytes(report) + b"\n")
    return report


# ----------------------------------------------------------------------------------------
# The single qualifying invocation
# ----------------------------------------------------------------------------------------


def _read_ledger() -> dict[str, Any]:
    if not LEDGER_PATH.is_file():
        return {"schema": LEDGER_SCHEMA, "entries": []}
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _append_ledger(entry: dict[str, Any]) -> None:
    """Append-only. A failed attempt stays, which is what makes a retry impossible to hide."""
    ledger = _read_ledger()
    ledger["entries"] = list(ledger.get("entries") or []) + [entry]
    LEDGER_PATH.write_bytes(canonical_bytes(ledger) + b"\n")


def qualify(spec: dict[str, Any]) -> int:
    identity = spec["generator_identity"]
    commitment = spec["spec_commitment_sha256"]

    ledger = _read_ledger()
    prior = [
        item for item in (ledger.get("entries") or [])
        if item.get("spec_commitment_sha256") == commitment
    ]
    if any(item.get("outcome") == "materialized" for item in prior):
        raise GenerationError(
            "this frozen spec has already materialized a bank. One frozen spec admits one "
            "materialization, and a second is the retry the contract exists to refuse."
        )
    attempt_index = len(prior) + 1

    # The body is the one the spec committed to, byte for byte, rather than one rebuilt here.
    body = spec["canonical_request_body"]
    if sha256_hex(canonical_bytes(body)) != spec["canonical_request_body_sha256"]:
        raise GenerationError("the request body does not match the digest the spec froze")
    if contamination_hits(canonical_bytes(body).decode("utf-8")):
        raise GenerationError("the request body carries project context")

    started = _now()
    failure: str | None = None
    observed: dict[str, Any] | None = None
    try:
        observed = request(identity["endpoint"], body=body)
    except Exception as exc:  # noqa: BLE001 - a failed attempt is a recorded outcome, not a crash
        failure = "%s: %s" % (type(exc).__name__, exc)

    if observed is None or observed["status"] != 200:
        _append_ledger({
            "attempt_index": attempt_index,
            "spec_commitment_sha256": commitment,
            "started_at": started,
            "outcome": "failed",
            "payload_sha256": None,
            "isolation_attestation_sha256": None,
            "note": failure or "HTTP %s" % (observed or {}).get("status"),
        })
        print("the invocation failed and is recorded as a failed attempt; no retry is permitted")
        return 1

    served = observed["body"] or {}
    served_model = served.get("model")
    served_provider = served.get("provider")
    # Fail closed on a served identity that is not the frozen one. This is the whole reason
    # fallbacks and automatic routing are disabled in the spec: if something answered anyway, the
    # bank did not come from the generator the record names.
    if served_model != identity["model"] or (
        served_provider is not None and served_provider != identity["provider"]
    ):
        _append_ledger({
            "attempt_index": attempt_index,
            "spec_commitment_sha256": commitment,
            "started_at": started,
            "outcome": "failed",
            "payload_sha256": None,
            "isolation_attestation_sha256": None,
            "note": "served identity differs from the frozen identity",
        })
        print("REFUSED: served identity differs from the frozen identity")
        return 1

    # The raw response is preserved before anything reads it scientifically.
    RAW_RESPONSE_PATH.write_bytes(canonical_bytes({
        "schema": "m113-generation-response-v1",
        "milestone": "M113",
        "spec_commitment_sha256": commitment,
        "attempt_index": attempt_index,
        "request_body_sha256": spec["canonical_request_body_sha256"],
        "status": observed["status"],
        "response_sha256": observed["response_sha256"],
        "response_headers": observed["response_headers"],
        "id": served.get("id"),
        "served_model": served_model,
        "served_provider": served_provider,
        "usage": served.get("usage"),
        "finish_reason": (
            (served.get("choices") or [{}])[0].get("finish_reason")
            if served.get("choices") else None
        ),
        "created": served.get("created"),
        "started_at": observed["started_at"],
        "finished_at": observed["finished_at"],
        "body": served,
    }) + b"\n")

    print("wrote %s" % RAW_RESPONSE_PATH.relative_to(ROOT))
    print("The response is preserved and unread. Seal it before anything reads it scientifically,")
    print("then record the materialization in the ledger with the sealed payload's digest.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discover", action="store_true", help="DEVELOPMENT: which providers serve the model")
    mode.add_argument("--smoke", action="store_true", help="DEVELOPMENT: one non-qualifying probe")
    mode.add_argument("--qualify", action="store_true", help="the single qualifying invocation")
    parser.add_argument("--write", action="store_true", help="write the development report")
    arguments = parser.parse_args()

    try:
        if arguments.qualify:
            return qualify(load_spec(frozen_required=True))
        spec = load_spec(frozen_required=False)
        report = discover(spec, write=arguments.write) if arguments.discover else smoke(
            spec, write=arguments.write
        )
    except GenerationError as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
