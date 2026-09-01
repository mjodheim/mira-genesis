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
    # An absent field must stay absent. This projection previously initialised both lists to []
    # and filled them only when the source key was a list, so a field the API never emitted was
    # rendered as one observed to be empty -- turning "no evidence" into "evidence that nothing
    # happened", in exactly the direction that makes a route look better than it was shown to be.
    # M117 established that this API emits neither key at all, on success or failure.
    attempts = value.get("attempts")
    safe_attempts: list[dict[str, Any]] | None = None
    if isinstance(attempts, list):
        safe_attempts = [
            {"provider": item.get("provider"), "model": item.get("model"),
             "status": item.get("status")}
            for item in attempts if isinstance(item, Mapping)
        ]
    pipeline = value.get("pipeline")
    safe_pipeline: list[dict[str, Any]] | None = None
    if isinstance(pipeline, list):
        safe_pipeline = [
            {"type": item.get("type"), "name": item.get("name")}
            for item in pipeline if isinstance(item, Mapping)
        ]
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

    # Where explicit attempt records exist, exactly one successful record is required.
    #
    # Where they do not -- this API emits no `attempts` key at all -- the same fact rests on the
    # evidence it does emit: a direct strategy, routing attempt 1, and exactly one selected
    # endpoint. That is the inference the previous code reached, but it reached it by testing a
    # list the projection had fabricated, so a route with no routing evidence whatsoever passed
    # the same way as one with positive evidence. The verdict is unchanged; its basis is now real.
    if isinstance(attempts, list) and attempts:
        explicit_no_fallback = (
            len(attempts) == 1
            and isinstance(attempts[0], Mapping)
            and attempts[0].get("provider") == SELECTED_PROVIDER
            and attempts[0].get("model") in {REQUESTED_MODEL, CANONICAL_CHECKPOINT}
            and attempts[0].get("status") == 200
        )
    else:
        explicit_no_fallback = (
            metadata.get("strategy") == "direct"
            and metadata.get("attempt") == 1
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
        # A pipeline the API never reports cannot have intervened; one it reports must be empty.
        "pipeline_present_as_list": pipeline is None or isinstance(pipeline, list),
        "no_pipeline_intervention": pipeline is None or (
            isinstance(pipeline, list) and len(pipeline) == 0),
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
        # Whether the router reported these fields at all is visible in the projection itself,
        # where absent is None and observed-empty is []. It is deliberately NOT added here: the
        # attestation dict is compared for full equality against M115's committed record, so any
        # new key would break the recomputation of a closed milestone.
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
