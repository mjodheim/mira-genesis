"""Run a DEVELOPMENT-only matrix over plausible OpenRouter generator routes.

This script is intentionally outside every Genesis milestone. It uses the tiny smoke defined in
``scripts.audit_generator_routes`` and NEVER sends M113/M114 qualifying input. The purpose is to
measure transport/provider suitability before a successor hypothesis is opened.

The default candidate set is the set that the preserved M113 provider discovery reported as
supporting both strict structured outputs and the predecessor request's ``seed`` parameter. The
set is historical input to this DEVELOPMENT tool, not a claim about current availability; each run
re-discovers every provider before deciding whether it is safe to smoke.

Every eligible provider gets at most one smoke request. There is no retry, no fallback, no output
selection and no scientific claim. A 429, malformed response, or isolated transport exception is
simply a route observation and the matrix continues to the next independent DEVELOPMENT candidate.

The recommendation rule below is deliberately written into source before the first matrix is run:
only routes that actually pass the smoke and carry complete reliability measurements are rankable;
then prefer 1-day uptime, 30-minute uptime, p50 latency and finally stable provider name. BYOK and
quantization are recorded observations but are not ranking inputs. This is an instrumental
DEVELOPMENT recommendation, not a scientific or milestone provider-selection rule.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.blind_bank_protocol import canonical_bytes  # noqa: E402
from scripts import audit_generator_routes as routes  # noqa: E402

REPORT_SCHEMA = "genesis-generator-route-matrix-development-v3"
RECOMMENDATION_POLICY = {
    "schema": "generator-route-development-recommendation-v1",
    "defined_before_first_matrix_run": True,
    "requires_route_viable": True,
    "requires_complete_metrics": ["uptime_last_1d", "uptime_last_30m", "latency_last_30m.p50"],
    "ordering": [
        "uptime_last_1d_desc",
        "uptime_last_30m_desc",
        "latency_last_30m_p50_asc",
        "provider_name_asc",
    ],
    "byok_is_a_ranking_input": False,
    "quantization_is_a_ranking_input": False,
    "is_a_milestone_provider_selection_rule": False,
}

# Frozen from experiments/M113/PROVIDER_DISCOVERY_DEVELOPMENT.json as the providers that both
# supported structured outputs and advertised seed at that observation. The live discovery below
# is authoritative for the current run.
DEFAULT_CANDIDATES = (
    "AkashML",
    "Alibaba",
    "Ambient",
    "AtlasCloud",
    "Cloudflare",
    "DeepInfra",
    "Inceptron",
    "Makora",
    "Mancer 2",
    "Morph",
    "OpenInference",
    "Parasail",
    "Phala",
    "Wafer",
)


def discovery_is_predecessor_compatible(report: Mapping[str, Any]) -> bool:
    """Whether a route positively advertises every parameter the predecessor smoke sends."""
    endpoint_status = report.get("endpoint_status")
    live_endpoint = (
        isinstance(endpoint_status, (int, float))
        and not isinstance(endpoint_status, bool)
        and endpoint_status == 0
    )
    return bool(
        report.get("provider_found") is True
        and report.get("status") == 200
        and report.get("supports_structured_outputs") is True
        and report.get("supports_seed") is True
        and live_endpoint
    )


def _failed_discovery(provider: str) -> dict[str, Any]:
    """Return a fail-closed, sanitized observation for an isolated discovery exception."""
    return {
        "requested_provider": provider,
        "provider_found": False,
        "status": None,
        "supports_structured_outputs": False,
        "supports_seed": False,
        "endpoint_status": None,
        "discovery_failed": True,
        "failure_class": "discovery_exception",
    }


def _failed_smoke(provider: str) -> dict[str, Any]:
    """Return a fail-closed, sanitized observation for an isolated smoke exception.

    A low-level transport exception can happen either before or after request bytes leave the
    process, so this record deliberately does not claim whether a physical request was sent.
    """
    return {
        "schema": routes.REPORT_SCHEMA,
        "mode": "smoke",
        "development": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "requested_model": routes.MODEL,
        "requested_provider": provider,
        "status": None,
        "served_model": None,
        "served_provider": None,
        "finish_reason": None,
        "structured_output_parsed": False,
        "router_metadata": None,
        "error": None,
        "response_sha256": None,
        "response_bytes": None,
        "observed_at": None,
        "route_checks": {},
        "route_viable": False,
        "failed_route_checks": ["smoke_exception"],
        "byok_runtime_attested": False,
        "byok_route_qualified": False,
        "smoke_failed": True,
        "failure_class": "smoke_exception",
        "physical_request_sent": None,
    }


def _metric(report: Mapping[str, Any], key: str) -> float | None:
    value = report.get(key)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _latency_p50(report: Mapping[str, Any]) -> float | None:
    latency = report.get("latency_last_30m")
    if not isinstance(latency, Mapping):
        return None
    value = latency.get("p50")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def has_complete_recommendation_metrics(report: Mapping[str, Any]) -> bool:
    return (
        _metric(report, "uptime_last_1d") is not None
        and _metric(report, "uptime_last_30m") is not None
        and _latency_p50(report) is not None
    )


def rank_viable_routes(
    smokes: Iterable[Mapping[str, Any]], discoveries: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Apply the predeclared DEVELOPMENT recommendation rule to measured viable routes only."""
    viable = {
        str(item.get("requested_provider"))
        for item in smokes
        if item.get("route_viable") is True and isinstance(item.get("requested_provider"), str)
    }
    rankable = [
        provider
        for provider in viable
        if provider in discoveries and has_complete_recommendation_metrics(discoveries[provider])
    ]

    def key(provider: str) -> tuple[float, float, float, str]:
        discovery = discoveries[provider]
        uptime_1d = _metric(discovery, "uptime_last_1d")
        uptime_30m = _metric(discovery, "uptime_last_30m")
        latency = _latency_p50(discovery)
        assert uptime_1d is not None and uptime_30m is not None and latency is not None
        return (-uptime_1d, -uptime_30m, latency, provider)

    return sorted(rankable, key=key)


def summarize(
    discoveries: list[Mapping[str, Any]], smokes: list[Mapping[str, Any]]
) -> dict[str, Any]:
    by_provider = {
        str(item.get("requested_provider")): item
        for item in discoveries
        if isinstance(item.get("requested_provider"), str)
    }
    ranked = rank_viable_routes(smokes, by_provider)
    viable = sorted(
        str(item.get("requested_provider"))
        for item in smokes
        if item.get("route_viable") is True
    )
    rankable = set(ranked)
    return {
        "providers_discovered": len(discoveries),
        "providers_predecessor_compatible": sorted(
            provider for provider, item in by_provider.items() if discovery_is_predecessor_compatible(item)
        ),
        "smokes_attempted": len(smokes),
        "smokes_with_http_response": sum(
            1
            for item in smokes
            if isinstance(item.get("status"), int) and not isinstance(item.get("status"), bool)
        ),
        "smokes_with_ambiguous_delivery": sum(
            1 for item in smokes if item.get("physical_request_sent") is None and item.get("smoke_failed") is True
        ),
        "route_viable": viable,
        "viable_but_unrankable_missing_metrics": sorted(set(viable) - rankable),
        "byok_route_qualified": sorted(
            str(item.get("requested_provider"))
            for item in smokes
            if item.get("byok_route_qualified") is True
        ),
        "ranked_viable_routes_by_predeclared_reliability_rule": ranked,
        "development_recommended_successor_route": ranked[0] if ranked else None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "ranking_is_a_milestone_selection_rule": False,
        "qualifying_calls": 0,
    }


def run_matrix(candidates: Iterable[str]) -> dict[str, Any]:
    routes._assert_smoke_is_not_qualifying_input()
    unique = list(dict.fromkeys(str(provider) for provider in candidates))
    discoveries: list[dict[str, Any]] = []
    smokes: list[dict[str, Any]] = []

    for provider in unique:
        try:
            discovery = routes.discover_provider(provider)
        except Exception:
            discovery = _failed_discovery(provider)
        discoveries.append(discovery)

    for discovery in discoveries:
        if not discovery_is_predecessor_compatible(discovery):
            continue
        provider = str(discovery["requested_provider"])
        # smoke_provider repeats the qualifying-input guard. One attempt, no retry. A transport
        # exception is terminal for this provider but must not suppress later independent routes.
        try:
            smoke = routes.smoke_provider(provider)
        except Exception:
            smoke = _failed_smoke(provider)
        smokes.append(smoke)

    return {
        "schema": REPORT_SCHEMA,
        "development": True,
        "is_a_qualifying_run": False,
        "qualifying_input_was_sent": False,
        "requested_model": routes.MODEL,
        "candidate_source": "M113 discovery: structured_outputs + seed capable providers",
        "candidates": unique,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "discovery_reports": discoveries,
        "smoke_reports": smokes,
        "summary": summarize(discoveries, smokes),
        "interpretation_boundary": (
            "This report qualifies transport/provider routes only. It does not test H58/H59/H60, "
            "does not advance G1-G10, and does not itself select or freeze a successor milestone provider."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        action="append",
        dest="providers",
        help="provider to include; repeat to override the default candidate set",
    )
    parser.add_argument(
        "--write",
        type=Path,
        default=None,
        help="optional path for the sanitized matrix JSON",
    )
    args = parser.parse_args()
    candidates = args.providers if args.providers else DEFAULT_CANDIDATES
    report = run_matrix(candidates)
    encoded = canonical_bytes(report) + b"\n"
    if args.write is not None:
        path = args.write if args.write.is_absolute() else ROOT / args.write
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
    sys.stdout.buffer.write(encoded)
    # A matrix is observational. Individual route failures are data, not a process failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
