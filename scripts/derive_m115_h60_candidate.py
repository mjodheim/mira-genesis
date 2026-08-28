"""Derive the M115/H60 provider candidate from the preserved DEVELOPMENT route matrix.

This module does not call the network, does not send qualifying input, does not freeze M115 and does
not create a bank.  It exists only to make the owner-authorized successor-selection chronology
reproducible from evidence already preserved in ``experiments/M115``.

The owner-authorized H60 identity rule versions one instrumental clause: an explicitly registered
alias -> canonical-checkpoint relation is acceptable in place of literal endpoint-model equality.
Every other route check remains fail-closed.  The reliability ordering is the already-declared
DEVELOPMENT ordering from ``scripts.audit_generator_matrix``.  The decision to adopt that ordering
as the H60 milestone-selection rule happened after the matrix observation but before any H60 freeze,
bank or qualifying invocation; the candidate record states that chronology explicitly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from scripts.audit_generator_matrix import RECOMMENDATION_POLICY

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "experiments" / "M115" / "RUNTIME_ROUTE_MATRIX_DEVELOPMENT.json"

H60_REQUESTED_ALIAS = "deepseek/deepseek-v4-flash-0731"
H60_CANONICAL_CHECKPOINT = "deepseek/deepseek-v4-flash-20260731"

_REQUIRED_ROUTE_CHECKS = (
    "http_200",
    "served_model_exact",
    "served_provider_exact",
    "structured_output_strictly_parsed",
    "finish_reason_stop",
    "router_metadata_present",
    "router_requested_model_exact",
    "router_strategy_direct",
    "one_router_attempt",
    "one_selected_endpoint",
    "no_fallback_attested",
    "no_router_pipeline_intervention",
)

_EXPECTED_ORDERING = [
    "uptime_last_1d_desc",
    "uptime_last_30m_desc",
    "latency_last_30m_p50_asc",
    "provider_name_asc",
]


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _latency_p50(discovery: Mapping[str, Any]) -> float | None:
    latency = discovery.get("latency_last_30m")
    if not isinstance(latency, Mapping):
        return None
    return _number(latency.get("p50"))


def h60_route_admissible(smoke: Mapping[str, Any]) -> bool:
    """Apply only the owner-authorized H60 identity version plus preserved route safeguards."""
    if smoke.get("is_a_qualifying_call") is not False:
        return False
    if smoke.get("qualifying_input_was_sent") is not False:
        return False
    if smoke.get("requested_model") != H60_REQUESTED_ALIAS:
        return False
    if smoke.get("canonical_checkpoint_match") is not True:
        return False
    if smoke.get("no_fallback_attested_value") is not True:
        return False

    checks = smoke.get("route_checks")
    if not isinstance(checks, Mapping):
        return False
    if any(checks.get(name) is not True for name in _REQUIRED_ROUTE_CHECKS):
        return False

    # Literal selected-endpoint equality is the one versioned clause.  The preserved matrix should
    # still show it as false; silently accepting a matrix where the historical condition changed
    # would blur the chronology this successor is meant to preserve.
    if checks.get("selected_endpoint_exact") is not False:
        return False

    metadata = smoke.get("router_metadata")
    if not isinstance(metadata, Mapping):
        return False
    endpoints = metadata.get("endpoints")
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    selected = [
        item
        for item in available
        if isinstance(item, Mapping) and item.get("selected") is True
    ] if isinstance(available, list) else []
    if len(selected) != 1:
        return False
    if selected[0].get("model") != H60_CANONICAL_CHECKPOINT:
        return False
    if selected[0].get("provider") != smoke.get("requested_provider"):
        return False
    return True


def derive_candidate(matrix: Mapping[str, Any]) -> dict[str, Any]:
    """Return the deterministic H60 candidate-selection record from one preserved matrix."""
    if matrix.get("development") is not True:
        raise ValueError("matrix is not marked DEVELOPMENT")
    if matrix.get("is_a_qualifying_run") is not False:
        raise ValueError("matrix is not explicitly non-qualifying")
    if matrix.get("qualifying_input_was_sent") is not False:
        raise ValueError("matrix does not attest that qualifying input was absent")
    if matrix.get("requested_model") != H60_REQUESTED_ALIAS:
        raise ValueError("matrix requested model does not match the H60 alias")

    policy = matrix.get("recommendation_policy")
    if not isinstance(policy, Mapping):
        raise ValueError("matrix recommendation policy is absent")
    if policy.get("defined_before_first_matrix_run") is not True:
        raise ValueError("reliability ordering was not declared before the matrix")
    if list(policy.get("ordering") or []) != _EXPECTED_ORDERING:
        raise ValueError("matrix reliability ordering differs from the preserved policy")
    if RECOMMENDATION_POLICY["ordering"] != _EXPECTED_ORDERING:
        raise ValueError("source reliability ordering has drifted")

    discoveries = {
        item.get("requested_provider"): item
        for item in matrix.get("discovery_reports", [])
        if isinstance(item, Mapping) and isinstance(item.get("requested_provider"), str)
    }
    admissible = [
        item
        for item in matrix.get("smoke_reports", [])
        if isinstance(item, Mapping) and h60_route_admissible(item)
    ]

    providers: list[str] = []
    for smoke in admissible:
        provider = smoke.get("requested_provider")
        if not isinstance(provider, str) or provider not in discoveries:
            raise ValueError("admissible smoke lacks matching discovery evidence")
        discovery = discoveries[provider]
        if _number(discovery.get("uptime_last_1d")) is None:
            raise ValueError(f"{provider}: missing uptime_last_1d")
        if _number(discovery.get("uptime_last_30m")) is None:
            raise ValueError(f"{provider}: missing uptime_last_30m")
        if _latency_p50(discovery) is None:
            raise ValueError(f"{provider}: missing latency p50")
        providers.append(provider)

    def rank_key(provider: str) -> tuple[float, float, float, str]:
        discovery = discoveries[provider]
        uptime_1d = _number(discovery.get("uptime_last_1d"))
        uptime_30m = _number(discovery.get("uptime_last_30m"))
        latency = _latency_p50(discovery)
        assert uptime_1d is not None and uptime_30m is not None and latency is not None
        return (-uptime_1d, -uptime_30m, latency, provider)

    ranked = sorted(providers, key=rank_key)
    return {
        "schema": "m115-h60-derived-provider-candidate-v1",
        "development_evidence_only": True,
        "milestone": "M115",
        "hypothesis": "H60",
        "identity_rule": "explicit_alias_to_canonical_checkpoint_relation",
        "requested_alias": H60_REQUESTED_ALIAS,
        "canonical_checkpoint": H60_CANONICAL_CHECKPOINT,
        "admissible_smoke_count": len(admissible),
        "ranked_providers": ranked,
        "selected_provider_candidate": ranked[0] if ranked else None,
        "selection_rule_defined_before_matrix": True,
        "selection_rule_adopted_for_h60_after_matrix_observation": True,
        "selection_rule_adopted_before_h60_freeze": True,
        "selection_rule_adopted_before_h60_bank": True,
        "selection_rule_adopted_before_h60_qualifying_invocation": True,
        "qualifying_calls": 0,
    }


def main() -> int:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    print(json.dumps(derive_candidate(matrix), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
