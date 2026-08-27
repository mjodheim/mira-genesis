"""Run a DEVELOPMENT-only matrix over plausible OpenRouter generator routes.

This script is intentionally outside every Genesis milestone.  It uses the tiny smoke defined in
``scripts.audit_generator_routes`` and NEVER sends M113/M114 qualifying input.  The purpose is to
measure transport/provider suitability before a successor hypothesis is opened.

The default candidate set is the set that the preserved M113 provider discovery reported as
supporting both strict structured outputs and the predecessor request's ``seed`` parameter.  The
set is historical input to this DEVELOPMENT tool, not a claim about current availability; each run
re-discovers every provider before deciding whether it is safe to smoke.

Every eligible provider gets at most one smoke request.  There is no retry, no fallback, no output
selection and no scientific claim.  A 429 or malformed response is simply a route observation and
the matrix continues to the next independent DEVELOPMENT candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.blind_bank_protocol import canonical_bytes  # noqa: E402
from scripts import audit_generator_routes as routes  # noqa: E402

REPORT_SCHEMA = "genesis-generator-route-matrix-development-v1"

# Frozen from experiments/M113/PROVIDER_DISCOVERY_DEVELOPMENT.json as the providers that both
# supported structured outputs and advertised seed at that observation.  The live discovery below
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
    return bool(
        report.get("provider_found") is True
        and report.get("status") == 200
        and report.get("supports_structured_outputs") is True
        and report.get("supports_seed") is True
        and report.get("endpoint_status") == 0
    )


def _number(value: Any, default: float = -1.0) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def rank_viable_routes(
    smokes: Iterable[Mapping[str, Any]], discoveries: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Development ranking only: viability first, then observed reliability, then stable name.

    The ranking is explicitly NOT a milestone provider-selection rule.  It is a convenience for the
    owner/researcher to see which already-successful routes currently look least likely to reproduce
    M114's capacity failure.  Quantization is intentionally not used here: M114 demonstrated that
    a theoretically preferable weight representation is useless when the route cannot materialize.
    """
    viable = [
        str(item.get("requested_provider"))
        for item in smokes
        if item.get("route_viable") is True and isinstance(item.get("requested_provider"), str)
    ]

    def key(provider: str) -> tuple[float, float, float, str]:
        discovery = discoveries.get(provider, {})
        return (
            -_number(discovery.get("uptime_last_30m")),
            -_number(discovery.get("uptime_last_1d")),
            _number((discovery.get("latency_last_30m") or {}).get("p50"), default=1e18),
            provider,
        )

    return sorted(set(viable), key=key)


def summarize(
    discoveries: list[Mapping[str, Any]], smokes: list[Mapping[str, Any]]
) -> dict[str, Any]:
    by_provider = {
        str(item.get("requested_provider")): item
        for item in discoveries
        if isinstance(item.get("requested_provider"), str)
    }
    ranked = rank_viable_routes(smokes, by_provider)
    return {
        "providers_discovered": len(discoveries),
        "providers_predecessor_compatible": sorted(
            provider for provider, item in by_provider.items() if discovery_is_predecessor_compatible(item)
        ),
        "smokes_sent": len(smokes),
        "route_viable": sorted(
            str(item.get("requested_provider"))
            for item in smokes
            if item.get("route_viable") is True
        ),
        "byok_route_qualified": sorted(
            str(item.get("requested_provider"))
            for item in smokes
            if item.get("byok_route_qualified") is True
        ),
        "ranked_viable_routes_by_current_reliability": ranked,
        "ranking_is_a_milestone_selection_rule": False,
        "qualifying_calls": 0,
    }


def run_matrix(candidates: Iterable[str]) -> dict[str, Any]:
    routes._assert_smoke_is_not_qualifying_input()
    unique = list(dict.fromkeys(str(provider) for provider in candidates))
    discoveries: list[dict[str, Any]] = []
    smokes: list[dict[str, Any]] = []

    for provider in unique:
        discovery = routes.discover_provider(provider)
        discoveries.append(discovery)

    for discovery in discoveries:
        if not discovery_is_predecessor_compatible(discovery):
            continue
        provider = str(discovery["requested_provider"])
        # smoke_provider itself performs the qualifying-input guard again. One physical request,
        # no retry. A failed route does not authorize another request to that same provider.
        smokes.append(routes.smoke_provider(provider))

    return {
        "schema": REPORT_SCHEMA,
        "development": True,
        "is_a_qualifying_run": False,
        "qualifying_input_was_sent": False,
        "requested_model": routes.MODEL,
        "candidate_source": "M113 discovery: structured_outputs + seed capable providers",
        "candidates": unique,
        "discovery_reports": discoveries,
        "smoke_reports": smokes,
        "summary": summarize(discoveries, smokes),
        "interpretation_boundary": (
            "This report qualifies transport/provider routes only. It does not test H58/H59/H60, "
            "does not advance G1-G10, and does not select or freeze a successor milestone provider."
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
