"""Development-only qualification harness for generator routes.

This tool exists to keep transport/provider debugging OUTSIDE scientific milestones.
It never uses the qualifying carrier input and never consumes a Genesis owner gate.

It can:

* inspect OpenRouter's endpoint catalogue for the exact M114 model;
* run a tiny, non-qualifying strict-json-schema smoke request against one explicitly named provider;
* opt into OpenRouter router metadata so BYOK use, fallback attempts and request/response pipeline
  stages are measured rather than inferred;
* emit only an allowlisted, publication-safe report. Raw credentials, account identifiers, raw
  provider error bodies and BYOK key metadata are never written.

Two verdicts are deliberately separated:

* ``route_viable`` means the exact model/provider route really served the strict-schema smoke with
  one direct attempt, no fallback and no material router intervention;
* ``byok_route_qualified`` additionally requires runtime ``is_byok=true``.

That distinction lets DEVELOPMENT compare backup providers without pretending that shared capacity
already fixes M113/M114. A successful report is permission to DESIGN a later milestone, never
scientific evidence about Genesis and never permission to send the qualifying input.
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

from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

MODEL = "deepseek/deepseek-v4-flash-0731"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
CATALOGUE_ENDPOINT = "https://openrouter.ai/api/v1/models/%s/endpoints" % MODEL
SECRET_VARIABLE = "OPENROUTER_API_KEY"
ROUTER_METADATA_HEADER = "X-OpenRouter-Metadata"
REPORT_SCHEMA = "genesis-generator-route-audit-v2"

# Deliberately unrelated to carrier generation. The qualifying input is checked by digest before
# every network smoke so this text cannot become the bank by accident.
SMOKE_INPUT = (
    'Return a JSON object with exactly one key "samples". Its value is a list of exactly two '
    'objects, each containing exactly one integer key "value" between 10 and 99. No prose.'
)
SMOKE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "samples": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "value": {"type": "integer", "minimum": 10, "maximum": 99}
                },
                "required": ["value"],
            },
        }
    },
    "required": ["samples"],
}

QUALIFYING_INPUT_PATHS = (
    ROOT / "experiments" / "M113" / "QUALIFYING_INPUT.txt",
    ROOT / "experiments" / "M114" / "QUALIFYING_INPUT.txt",
)


class RouteAuditError(RuntimeError):
    """The route could not be assessed without guessing or leaking information."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise RouteAuditError(
            "%s is not set; no network request was made" % SECRET_VARIABLE
        )
    return secret


def _assert_smoke_is_not_qualifying_input() -> None:
    smoke = SMOKE_INPUT.encode("utf-8")
    smoke_digest = sha256_hex(smoke)
    for path in QUALIFYING_INPUT_PATHS:
        if not path.is_file():
            continue
        qualifying = path.read_bytes()
        if smoke_digest == sha256_hex(qualifying):
            raise RouteAuditError("the route smoke input is a qualifying input")
        if SMOKE_INPUT.strip() in qualifying.decode("utf-8", "replace"):
            raise RouteAuditError("the route smoke input occurs inside a qualifying input")


def _connection(url: str, timeout: int) -> tuple[http.client.HTTPSConnection, urllib.parse.SplitResult]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RouteAuditError("route audit endpoints must use https")
    context = ssl.create_default_context()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        via = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
        conn = http.client.HTTPSConnection(
            via.hostname, via.port or 80, timeout=timeout, context=context
        )
        conn.set_tunnel(parsed.hostname, parsed.port or 443)
    else:
        conn = http.client.HTTPSConnection(
            parsed.hostname, parsed.port or 443, timeout=timeout, context=context
        )
    return conn, parsed


def _request(
    url: str,
    *,
    method: str = "GET",
    body: Mapping[str, Any] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Exactly one HTTP request, no retry, redirect following or response-cache replay.

    The decoded response exists only in memory. Reports are built from explicit allowlists below;
    neither this function nor its callers persist raw bodies or request headers. Response caching is
    explicitly disabled because OpenRouter intentionally strips router metadata from cache hits.
    """
    conn, parsed = _connection(url, timeout)
    payload = canonical_bytes(body) if body is not None else None
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer %s" % _secret(),
        "Content-Type": "application/json",
        ROUTER_METADATA_HEADER: "enabled",
        "X-OpenRouter-Cache": "false",
    }
    started = _now()
    try:
        conn.request(method, parsed.path or "/", body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
    finally:
        conn.close()
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        decoded = None
    return {
        "started_at": started,
        "finished_at": _now(),
        "status": status,
        "body": decoded,
        "response_sha256": sha256_hex(raw),
        "response_bytes": len(raw),
    }


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _safe_percentiles(value: Any) -> dict[str, int | float] | None:
    if not isinstance(value, Mapping):
        return None
    safe = {
        key: number
        for key in ("p50", "p75", "p90", "p99")
        if (number := _safe_number(value.get(key))) is not None
    }
    return safe or None


def _safe_router_metadata(value: Any) -> dict[str, Any] | None:
    """Allowlist only fields needed to decide whether the route is scientifically usable."""
    if not isinstance(value, Mapping):
        return None
    endpoints = value.get("endpoints") if isinstance(value.get("endpoints"), Mapping) else {}
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else []
    safe_available = []
    if isinstance(available, list):
        for item in available:
            if isinstance(item, Mapping):
                safe_available.append(
                    {
                        "provider": item.get("provider"),
                        "model": item.get("model"),
                        "selected": item.get("selected") is True,
                    }
                )
    attempts = value.get("attempts")
    safe_attempts = []
    if isinstance(attempts, list):
        for item in attempts:
            if isinstance(item, Mapping):
                safe_attempts.append(
                    {
                        "provider": item.get("provider"),
                        "model": item.get("model"),
                        "status": item.get("status"),
                    }
                )
    pipeline = value.get("pipeline")
    safe_pipeline = []
    if isinstance(pipeline, list):
        for item in pipeline:
            if isinstance(item, Mapping):
                safe_pipeline.append({"type": item.get("type"), "name": item.get("name")})
    return {
        "requested": value.get("requested"),
        "strategy": value.get("strategy"),
        "attempt": value.get("attempt"),
        "is_byok": value.get("is_byok"),
        "endpoints": {"total": endpoints.get("total"), "available": safe_available},
        "attempts": safe_attempts,
        "pipeline": safe_pipeline,
    }


def _safe_error(body: Any) -> dict[str, Any] | None:
    """Never persist provider messages or metadata blobs; only the public numeric/string code."""
    if not isinstance(body, Mapping):
        return None
    error = body.get("error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("code")
    return {"code": code} if isinstance(code, (int, str)) and not isinstance(code, bool) else None


def _structured_output_holds(content: Any) -> bool:
    if not isinstance(content, str):
        return False
    try:
        decoded = json.loads(content)
    except ValueError:
        return False
    if not isinstance(decoded, dict) or set(decoded) != {"samples"}:
        return False
    samples = decoded.get("samples")
    if not isinstance(samples, list) or len(samples) != 2:
        return False
    return all(
        isinstance(item, dict)
        and set(item) == {"value"}
        and isinstance(item["value"], int)
        and not isinstance(item["value"], bool)
        and 10 <= item["value"] <= 99
        for item in samples
    )


def _selected_endpoints(metadata: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(metadata, Mapping):
        return []
    endpoints = metadata.get("endpoints")
    if not isinstance(endpoints, Mapping):
        return []
    available = endpoints.get("available")
    if not isinstance(available, list):
        return []
    return [item for item in available if isinstance(item, dict) and item.get("selected") is True]


def evaluate_smoke(report: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute route viability from safe observations, never from a self-declared verdict."""
    metadata = report.get("router_metadata")
    selected = _selected_endpoints(metadata if isinstance(metadata, Mapping) else None)
    attempts = metadata.get("attempts") if isinstance(metadata, Mapping) else None
    pipeline = metadata.get("pipeline") if isinstance(metadata, Mapping) else None
    requested_provider = report.get("requested_provider")
    requested_model = report.get("requested_model")

    route_checks = {
        "http_200": report.get("status") == 200,
        "served_model_exact": report.get("served_model") == requested_model,
        "served_provider_exact": report.get("served_provider") == requested_provider,
        "structured_output_strictly_parsed": report.get("structured_output_parsed") is True,
        "finish_reason_stop": report.get("finish_reason") == "stop",
        "router_metadata_present": isinstance(metadata, Mapping),
        "router_requested_model_exact": isinstance(metadata, Mapping)
        and metadata.get("requested") == requested_model,
        "router_strategy_direct": isinstance(metadata, Mapping) and metadata.get("strategy") == "direct",
        "one_router_attempt": isinstance(metadata, Mapping) and metadata.get("attempt") == 1,
        "one_selected_endpoint": len(selected) == 1,
        "selected_endpoint_exact": len(selected) == 1
        and selected[0].get("provider") == requested_provider
        and selected[0].get("model") == requested_model,
        "no_fallback_attempt": isinstance(attempts, list)
        and len(attempts) == 1
        and all(
            item.get("provider") == requested_provider
            and item.get("model") == requested_model
            and item.get("status") == 200
            for item in attempts
            if isinstance(item, Mapping)
        ),
        # Router metadata defines pipeline entries as material interventions. A qualification smoke
        # is intentionally tiny, so any intervention is a delta that a later milestone would own.
        "no_router_pipeline_intervention": isinstance(pipeline, list) and len(pipeline) == 0,
    }
    byok_runtime_attested = isinstance(metadata, Mapping) and metadata.get("is_byok") is True
    route_viable = bool(route_checks) and all(route_checks.values())
    return {
        "route_checks": route_checks,
        "route_viable": route_viable,
        "failed_route_checks": sorted(name for name, holds in route_checks.items() if not holds),
        "byok_runtime_attested": byok_runtime_attested,
        "byok_route_qualified": bool(route_viable and byok_runtime_attested),
    }


def discover_provider(provider: str) -> dict[str, Any]:
    observed = _request(CATALOGUE_ENDPOINT, method="GET", timeout=120)
    body = observed.get("body")
    endpoints = ((body or {}).get("data") or {}).get("endpoints") if isinstance(body, Mapping) else None
    match = None
    if isinstance(endpoints, list):
        for item in endpoints:
            if isinstance(item, Mapping) and item.get("provider_name") == provider:
                match = item
                break
    if observed["status"] != 200 or match is None:
        return {
            "schema": REPORT_SCHEMA,
            "mode": "discovery",
            "development": True,
            "requested_model": MODEL,
            "requested_provider": provider,
            "status": observed["status"],
            "provider_found": False,
            "error": _safe_error(body),
            "observed_at": observed["finished_at"],
        }
    params = sorted(str(value) for value in (match.get("supported_parameters") or []))
    return {
        "schema": REPORT_SCHEMA,
        "mode": "discovery",
        "development": True,
        "requested_model": MODEL,
        "requested_provider": provider,
        "status": observed["status"],
        "provider_found": True,
        "supported_parameters": params,
        "supports_structured_outputs": "structured_outputs" in params,
        "supports_seed": "seed" in params,
        "quantization": match.get("quantization"),
        "endpoint_status": match.get("status"),
        "context_length": match.get("context_length"),
        "max_completion_tokens": match.get("max_completion_tokens"),
        "uptime_last_5m": _safe_number(match.get("uptime_last_5m")),
        "uptime_last_30m": _safe_number(match.get("uptime_last_30m")),
        "uptime_last_1d": _safe_number(match.get("uptime_last_1d")),
        "latency_last_30m": _safe_percentiles(match.get("latency_last_30m")),
        "throughput_last_30m": _safe_percentiles(match.get("throughput_last_30m")),
        "tag": match.get("tag") if isinstance(match.get("tag"), str) else None,
        "observed_at": observed["finished_at"],
    }


def smoke_provider(provider: str) -> dict[str, Any]:
    _assert_smoke_is_not_qualifying_input()
    body = {
        "max_tokens": 128,
        "messages": [{"role": "user", "content": SMOKE_INPUT}],
        "model": MODEL,
        "provider": {
            "only": [provider],
            "allow_fallbacks": False,
            "require_parameters": True,
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "samples", "schema": SMOKE_SCHEMA, "strict": True},
        },
        "seed": 0,
        "stream": False,
        "temperature": 1.0,
    }
    observed = _request(ENDPOINT, body=body, timeout=300)
    response = observed.get("body")
    metadata = _safe_router_metadata(
        response.get("openrouter_metadata") if isinstance(response, Mapping) else None
    )
    choices = response.get("choices") if isinstance(response, Mapping) else None
    first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], Mapping) else {}
    message = first.get("message") if isinstance(first.get("message"), Mapping) else {}
    report = {
        "schema": REPORT_SCHEMA,
        "mode": "smoke",
        "development": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "requested_model": MODEL,
        "requested_provider": provider,
        "request_body_sha256": sha256_hex(canonical_bytes(body)),
        "status": observed["status"],
        "served_model": response.get("model") if isinstance(response, Mapping) else None,
        "served_provider": response.get("provider") if isinstance(response, Mapping) else None,
        "finish_reason": first.get("finish_reason") if isinstance(first, Mapping) else None,
        "structured_output_parsed": _structured_output_holds(message.get("content")),
        "router_metadata": metadata,
        "error": _safe_error(response),
        "response_sha256": observed["response_sha256"],
        "response_bytes": observed["response_bytes"],
        "observed_at": observed["finished_at"],
    }
    report.update(evaluate_smoke(report))
    return report


def qualifies_under_policy(report: Mapping[str, Any], *, require_byok: bool) -> bool:
    """Select an execution policy without changing the measurements themselves."""
    return bool(report.get("byok_route_qualified") if require_byok else report.get("route_viable"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, help="exact OpenRouter provider name, e.g. Morph")
    parser.add_argument("--discover", action="store_true", help="read provider capabilities only")
    parser.add_argument("--smoke", action="store_true", help="send one non-qualifying strict-schema smoke")
    parser.add_argument(
        "--require-byok",
        action="store_true",
        help="for a smoke, return success only when runtime metadata attests BYOK",
    )
    parser.add_argument("--write", type=Path, default=None, help="optional path for the safe JSON report")
    args = parser.parse_args()
    if args.discover == args.smoke:
        parser.error("choose exactly one of --discover or --smoke")
    if args.require_byok and not args.smoke:
        parser.error("--require-byok is meaningful only with --smoke")

    report = discover_provider(args.provider) if args.discover else smoke_provider(args.provider)
    if args.smoke:
        report["qualification_policy"] = "byok" if args.require_byok else "route"
        report["instrument_qualified"] = qualifies_under_policy(
            report, require_byok=args.require_byok
        )
    encoded = canonical_bytes(report) + b"\n"
    if args.write is not None:
        path = args.write if args.write.is_absolute() else ROOT / args.write
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
    sys.stdout.buffer.write(encoded)
    return 0 if (args.discover or report.get("instrument_qualified") is True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
