"""Runtime identity attestation for M115/H60.

M113/M114 compared the requested model alias literally with provider identity assumptions made
before the request. M115 is prospective and different: the owner authorized one explicit alias to
canonical-checkpoint relation, and the qualifying response itself must attest that OpenRouter chose
that checkpoint on the selected provider.

This module does not generate carriers and never decides a scientific verdict. It is a gate on
whether a response is allowed to become M115's *single* bank materialization.
"""

from __future__ import annotations

from typing import Any, Mapping

REQUESTED_MODEL = "deepseek/deepseek-v4-flash-0731"
CANONICAL_CHECKPOINT = "deepseek/deepseek-v4-flash-20260731"
SELECTED_PROVIDER = "Alibaba"
IDENTITY_VERSION = "m115-alias-canonical-checkpoint-v1"


class IdentityError(RuntimeError):
    pass


def safe_router_metadata(value: Any) -> dict[str, Any] | None:
    """Allowlist only evidence needed to reconstruct the M115 routing identity.

    Account, workspace, key, credential and arbitrary provider metadata never survive this
    projection. Unknown future fields are dropped rather than published.
    """
    if not isinstance(value, Mapping):
        return None
    endpoints = value.get("endpoints")
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    safe_available: list[dict[str, Any]] = []
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
    safe_attempts: list[dict[str, Any]] = []
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
    safe_pipeline: list[dict[str, Any]] = []
    if isinstance(pipeline, list):
        for item in pipeline:
            if isinstance(item, Mapping):
                safe_pipeline.append({"type": item.get("type"), "name": item.get("name")})
    return {
        "requested": value.get("requested"),
        "strategy": value.get("strategy"),
        "attempt": value.get("attempt"),
        "is_byok": value.get("is_byok"),
        "endpoints": {
            "total": endpoints.get("total") if isinstance(endpoints, Mapping) else None,
            "available": safe_available,
        },
        "attempts": safe_attempts,
        "pipeline": safe_pipeline,
    }


def attest_router_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a recomputed attestation; every required fact must be positive evidence."""
    if not isinstance(metadata, Mapping):
        return {
            "identity_version": IDENTITY_VERSION,
            "holds": False,
            "failed_checks": ["router_metadata_present"],
        }
    endpoints = metadata.get("endpoints")
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    selected = [
        item for item in available or []
        if isinstance(item, Mapping) and item.get("selected") is True
    ]
    attempts = metadata.get("attempts")
    pipeline = metadata.get("pipeline")

    # OpenRouter may return an empty attempts list while still positively attesting a direct route
    # with exactly one selected endpoint. In that shape there is no alternative endpoint inside the
    # direct selection, so fallback is excluded by the routing record. If explicit attempt records
    # exist, exactly one successful record is required.
    if isinstance(attempts, list) and len(attempts) > 0:
        explicit_no_fallback = (
            len(attempts) == 1
            and isinstance(attempts[0], Mapping)
            and attempts[0].get("provider") == SELECTED_PROVIDER
            and attempts[0].get("model") in {REQUESTED_MODEL, CANONICAL_CHECKPOINT}
            and attempts[0].get("status") == 200
        )
    else:
        explicit_no_fallback = (
            isinstance(attempts, list)
            and len(attempts) == 0
            and metadata.get("strategy") == "direct"
            and len(selected) == 1
        )

    checks = {
        "router_metadata_present": True,
        "requested_alias_exact": metadata.get("requested") == REQUESTED_MODEL,
        "direct_strategy": metadata.get("strategy") == "direct",
        "one_router_attempt": metadata.get("attempt") == 1,
        "one_selected_endpoint": len(selected) == 1,
        "selected_provider_exact": len(selected) == 1
        and selected[0].get("provider") == SELECTED_PROVIDER,
        "selected_checkpoint_exact": len(selected) == 1
        and selected[0].get("model") == CANONICAL_CHECKPOINT,
        "no_fallback_attested": explicit_no_fallback,
        "pipeline_present_as_list": isinstance(pipeline, list),
        "no_pipeline_intervention": isinstance(pipeline, list) and len(pipeline) == 0,
    }
    return {
        "identity_version": IDENTITY_VERSION,
        "requested_model": REQUESTED_MODEL,
        "canonical_checkpoint": CANONICAL_CHECKPOINT,
        "selected_provider": SELECTED_PROVIDER,
        "checks": checks,
        "failed_checks": sorted(key for key, value in checks.items() if value is not True),
        "holds": all(value is True for value in checks.values()),
        # BYOK is an observation, not a criterion for this selected route. It was explicitly not a
        # ranking input in the preserved DEVELOPMENT policy.
        "is_byok_observed": metadata.get("is_byok") if isinstance(metadata.get("is_byok"), bool) else None,
    }


def attest_completion_response(body: Mapping[str, Any] | None) -> dict[str, Any]:
    """Bind top-level served identity and router checkpoint identity in one verdict."""
    if not isinstance(body, Mapping):
        return {
            "identity_version": IDENTITY_VERSION,
            "holds": False,
            "failed_checks": ["response_is_object"],
        }
    metadata = safe_router_metadata(body.get("openrouter_metadata"))
    router = attest_router_metadata(metadata)
    top_checks = {
        "served_model_alias_exact": body.get("model") == REQUESTED_MODEL,
        "served_provider_exact": body.get("provider") == SELECTED_PROVIDER,
    }
    failed = sorted(
        list(router.get("failed_checks") or [])
        + [key for key, value in top_checks.items() if value is not True]
    )
    return {
        "identity_version": IDENTITY_VERSION,
        "holds": router.get("holds") is True and all(top_checks.values()),
        "failed_checks": failed,
        "top_level_checks": top_checks,
        "router_attestation": router,
        "safe_router_metadata": metadata,
    }


def require_completion_identity(body: Mapping[str, Any] | None) -> dict[str, Any]:
    attestation = attest_completion_response(body)
    if attestation.get("holds") is not True:
        raise IdentityError(
            "M115 runtime model identity is not attested: %s"
            % ", ".join(attestation.get("failed_checks") or ["unknown failure"])
        )
    return attestation
