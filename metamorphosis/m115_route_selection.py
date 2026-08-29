"""M115 route selection from the preserved DEVELOPMENT matrix.

The scientific target is not observed here.  The matrix used a throwaway input, sent zero
qualifying calls and was merged before the owner authorized M115/H60 to proceed.

The ordering below is NOT invented from the observed provider table.  It is the exact ordering
committed in ``scripts/audit_generator_matrix.py`` before the first matrix was run:

1. 1-day uptime descending;
2. 30-minute uptime descending;
3. p50 latency ascending;
4. stable provider name ascending.

The original DEVELOPMENT rule required ``route_viable``.  That verdict was false for every
successful smoke only because the predecessor contract compared the requested alias
``deepseek/deepseek-v4-flash-0731`` byte-for-byte with the endpoint catalogue's canonical slug
``deepseek/deepseek-v4-flash-20260731``.  PR #229 preserved, separately and without normalising
strings, an explicit ``canonical_checkpoint_match`` observation for that relation.

On 2026-08-28 the owner authorized a *new M115 contract* to accept that explicitly attested
alias->canonical-checkpoint relation.  M113 and M114 remain closed and keep their literal identity
rules.  This module therefore derives the M115 provider from the already-preserved matrix under the
already-written reliability ordering.  It never edits the matrix, re-smokes a provider, or observes
carrier data.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

REQUESTED_MODEL = "deepseek/deepseek-v4-flash-0731"
CANONICAL_CHECKPOINT = "deepseek/deepseek-v4-flash-20260731"
PRESERVED_MATRIX_PATH = Path("experiments/M115/RUNTIME_ROUTE_MATRIX_DEVELOPMENT.json")
# Bind the exact preserved DEVELOPMENT evidence by its Git blob identity.  This is stronger than
# a moving branch/commit reference for the selection input itself and avoids laundering provenance
# through a later commit: any byte change to the matrix fails closed before ranking.
PRESERVED_MATRIX_BLOB = "3fac411f749e75f60a2dc9d31d8a92fc81563908"

RELIABILITY_ORDERING = (
    "uptime_last_1d_desc",
    "uptime_last_30m_desc",
    "latency_last_30m_p50_asc",
    "provider_name_asc",
)

EXPECTED_SELECTED_PROVIDER = "Alibaba"


class RouteSelectionError(RuntimeError):
    pass


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _p50(discovery: Mapping[str, Any]) -> float | None:
    latency = discovery.get("latency_last_30m")
    if not isinstance(latency, Mapping):
        return None
    return _number(latency.get("p50"))


def _all_predecessor_checks_except_literal_identity_hold(smoke: Mapping[str, Any]) -> bool:
    checks = smoke.get("route_checks")
    if not isinstance(checks, Mapping):
        return False
    required = {key: value for key, value in checks.items() if key != "selected_endpoint_exact"}
    return bool(required) and all(value is True for value in required.values())


def canonical_successor_eligible(
    discovery: Mapping[str, Any], smoke: Mapping[str, Any]
) -> bool:
    """The M115 pre-freeze route boundary; scientific carrier output is not involved."""
    provider = discovery.get("requested_provider")
    if not isinstance(provider, str) or smoke.get("requested_provider") != provider:
        return False
    if discovery.get("status") != 200 or discovery.get("provider_found") is not True:
        return False
    if discovery.get("endpoint_status") != 0 or isinstance(discovery.get("endpoint_status"), bool):
        return False
    if discovery.get("supports_structured_outputs") is not True:
        return False
    if discovery.get("supports_seed") is not True:
        return False
    if smoke.get("requested_model") != REQUESTED_MODEL:
        return False
    if smoke.get("served_model") != REQUESTED_MODEL:
        return False
    if smoke.get("served_provider") != provider:
        return False
    if smoke.get("canonical_checkpoint_match") is not True:
        return False
    if smoke.get("no_fallback_attested_value") is not True:
        return False
    if not _all_predecessor_checks_except_literal_identity_hold(smoke):
        return False
    metadata = smoke.get("router_metadata")
    if not isinstance(metadata, Mapping):
        return False
    endpoints = metadata.get("endpoints")
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    selected = [
        item for item in available or []
        if isinstance(item, Mapping) and item.get("selected") is True
    ]
    if len(selected) != 1:
        return False
    return (
        selected[0].get("provider") == provider
        and selected[0].get("model") == CANONICAL_CHECKPOINT
        and metadata.get("requested") == REQUESTED_MODEL
        and metadata.get("strategy") == "direct"
        and metadata.get("attempt") == 1
        and isinstance(metadata.get("pipeline"), list)
        and len(metadata.get("pipeline")) == 0
    )


def rank_key(discovery: Mapping[str, Any], provider: str) -> tuple[float, float, float, str]:
    one_day = _number(discovery.get("uptime_last_1d"))
    thirty = _number(discovery.get("uptime_last_30m"))
    latency = _p50(discovery)
    if one_day is None or thirty is None or latency is None:
        raise RouteSelectionError("provider %s has incomplete reliability evidence" % provider)
    return (-one_day, -thirty, latency, provider)


def derive_selection(matrix: Mapping[str, Any]) -> dict[str, Any]:
    if matrix.get("development") is not True:
        raise RouteSelectionError("the preserved route matrix is not marked DEVELOPMENT")
    if matrix.get("is_a_qualifying_run") is not False:
        raise RouteSelectionError("provider selection may not consume a qualifying matrix")
    if matrix.get("qualifying_input_was_sent") is not False:
        raise RouteSelectionError("the provider matrix claims the qualifying input was sent")
    summary = matrix.get("summary")
    if not isinstance(summary, Mapping) or summary.get("qualifying_calls") != 0:
        raise RouteSelectionError("the matrix does not positively attest zero qualifying calls")
    policy = matrix.get("recommendation_policy")
    if not isinstance(policy, Mapping):
        raise RouteSelectionError("the matrix has no preserved recommendation policy")
    if policy.get("defined_before_first_matrix_run") is not True:
        raise RouteSelectionError("the reliability ordering was not declared before measurement")
    if tuple(policy.get("ordering") or ()) != RELIABILITY_ORDERING:
        raise RouteSelectionError("the preserved reliability ordering differs from M115's")
    if policy.get("byok_is_a_ranking_input") is not False:
        raise RouteSelectionError("BYOK unexpectedly became a ranking input")
    if policy.get("quantization_is_a_ranking_input") is not False:
        raise RouteSelectionError("quantization unexpectedly became a ranking input")

    discoveries = {
        item.get("requested_provider"): item
        for item in matrix.get("discovery_reports") or []
        if isinstance(item, Mapping) and isinstance(item.get("requested_provider"), str)
    }
    smokes = {
        item.get("requested_provider"): item
        for item in matrix.get("smoke_reports") or []
        if isinstance(item, Mapping) and isinstance(item.get("requested_provider"), str)
    }
    eligible = [
        provider for provider, discovery in discoveries.items()
        if provider in smokes and canonical_successor_eligible(discovery, smokes[provider])
    ]
    ranked = sorted(eligible, key=lambda provider: rank_key(discoveries[provider], provider))
    if not ranked:
        raise RouteSelectionError("no provider satisfies the canonical-checkpoint successor boundary")
    selected = ranked[0]
    selected_discovery = discoveries[selected]
    return {
        "selected_provider": selected,
        "ranked_providers": ranked,
        "requested_model": REQUESTED_MODEL,
        "canonical_checkpoint": CANONICAL_CHECKPOINT,
        "selection_ordering": list(RELIABILITY_ORDERING),
        "selected_metrics": {
            "uptime_last_1d": selected_discovery.get("uptime_last_1d"),
            "uptime_last_30m": selected_discovery.get("uptime_last_30m"),
            "latency_last_30m_p50": _p50(selected_discovery),
        },
        "selected_quantization": selected_discovery.get("quantization"),
        "qualifying_calls_observed_during_selection": 0,
    }


def _git_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324 - Git object identity is SHA-1


def load_preserved_matrix(root: Path | None = None) -> dict[str, Any]:
    base = Path.cwd() if root is None else Path(root)
    path = base / PRESERVED_MATRIX_PATH
    if not path.is_file():
        raise RouteSelectionError("preserved route matrix is missing: %s" % path)
    raw = path.read_bytes()
    observed_blob = _git_blob_sha(raw)
    if observed_blob != PRESERVED_MATRIX_BLOB:
        raise RouteSelectionError(
            "preserved route matrix blob changed: expected %s, got %s"
            % (PRESERVED_MATRIX_BLOB, observed_blob)
        )
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise RouteSelectionError("preserved route matrix is not an object")
    return value


def derive_preserved_selection(root: Path | None = None) -> dict[str, Any]:
    selection = derive_selection(load_preserved_matrix(root))
    if selection["selected_provider"] != EXPECTED_SELECTED_PROVIDER:
        raise RouteSelectionError(
            "preserved matrix no longer derives the committed M115 provider: expected %s, got %s"
            % (EXPECTED_SELECTED_PROVIDER, selection["selected_provider"])
        )
    return selection
