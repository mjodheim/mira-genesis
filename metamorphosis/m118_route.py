"""The H63 generation route, fixed before any H63 observation exists.

M118 begins with an already-calibrated route and an apparatus that will not be modified after its
prospective freeze. The route below is fixed **here**, in code, by the preregistration -- not chosen
at run time, not ranked, not selected from a universe. There is no second route in this module and
no code path that could substitute one.

Why this route: it is the sole candidate that qualified in M117's Stage 1 calibration, on the
milestone's final apparatus revision, at the earliest qualifying position of an order frozen before
that attempt's probing began. It passed all twelve qualification clauses, enforcing every schema
feature class the carrier design depends on, and emitted 68,368 conforming completion tokens against
the census-dominating stress schema with `finish_reason: stop`.

That justification is **prior DEVELOPMENT calibration evidence**. It is not an H63 result: no H63
carrier exists, no H63 qualifying input has been sent, and nothing about H63 informed this choice --
it could not have, because H63 had not begun when the calibration ran.

M117 disclosed that five apparatus revisions occurred inside it and that some followed real endpoint
observations. M118 does not inherit a claim that route selection was prospectively clean; it inherits
only a route, fixed here, before H63 observes anything.

**No provider substitution. No fallback. No second route.** If this route becomes unavailable or
fails the frozen readiness gate, H63 stops before scientific generation. It does not fall back to a
next-best route -- there is no next-best route to fall back to.
"""

from __future__ import annotations

from typing import Any, Mapping

# ---------------------------------------------------------------------------------------------
# The route. Fixed by preregistration.
# ---------------------------------------------------------------------------------------------

REQUESTED_MODEL = "deepseek/deepseek-v4-flash-0731"
PROVIDER = "OpenInference"
CANONICAL_CHECKPOINT = "deepseek/deepseek-v4-flash-20260731"

ROUTE_VERSION = "m118-fixed-openinference-v1"

# The calibration evidence this fixing rests on, recorded so the justification travels with the
# route rather than living only in a commit message.
CALIBRATION_PROVENANCE = {
    "milestone": "M117",
    "phase": "DEVELOPMENT calibration",
    "attempt": 5,
    "plan_sha256": "b3b345907221081b260a8eb7da01aa692d018f18d31b4e35c60cf1b564e73168",
    "universe_sha256": "94b8819432a0880a2db3184418fde35f53b16044157c63f20923d04d5d6a5821",
    "selected_at_order": 16,
    "candidates_probed": 16,
    "requests_spent": 144,
    "qualified_clauses": 12,
    "feature_classes_unenforced": 0,
    "stress_completion_tokens": 68368,
    "stress_finish_reason": "stop",
    "stress_schema_conformed": True,
    "selection_used_any_h63_observation": False,
    "h63_carrier_existed_at_selection": False,
    "m117_disclosed_five_apparatus_revisions": True,
    "m117_route_selection_claimed_prospective": False,
}


class RouteError(RuntimeError):
    """The fixed route is not the route in hand. Every path fails closed."""


def route() -> dict[str, Any]:
    """The one route H63 may use."""
    return {
        "route_version": ROUTE_VERSION,
        "requested_model": REQUESTED_MODEL,
        "provider": PROVIDER,
        "canonical_checkpoint": CANONICAL_CHECKPOINT,
        "allow_fallbacks": False,
        "provider_substitution_permitted": False,
        "second_route_exists": False,
        "calibration_provenance": CALIBRATION_PROVENANCE,
    }


def provider_block() -> dict[str, Any]:
    """The routing directive sent on every H63 request. One provider, no fallbacks."""
    return {"only": [PROVIDER], "allow_fallbacks": False, "require_parameters": True}


def assert_is_the_fixed_route(model: Any, provider: Any) -> None:
    """Refuse anything that is not exactly the preregistered route."""
    if model != REQUESTED_MODEL:
        raise RouteError(
            "H63 is fixed to a single requested model and does not substitute: %r is not %r"
            % (model, REQUESTED_MODEL))
    if provider != PROVIDER:
        raise RouteError(
            "H63 is fixed to a single provider and does not substitute: %r is not %r"
            % (provider, PROVIDER))


def identity_holds(body: Mapping[str, Any] | None) -> dict[str, Any]:
    """Did the response come from exactly the fixed route, on a direct single-attempt path?

    Read from the raw response. `attempts` and `pipeline` are not fields this API emits -- M117
    established that they are absent on successful and rejected requests alike -- so exactly one
    routing attempt is established from what it does emit: a direct strategy, routing attempt 1,
    and exactly one selected endpoint, alongside the `allow_fallbacks: false` every request carries.
    Where the router *does* report those fields they are judged on their contents, and a single
    failed attempt record is not a clean single attempt.
    """
    if not isinstance(body, Mapping):
        return {"holds": False, "failed_checks": ["response_is_object"], "checks": {}}
    metadata = body.get("openrouter_metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    endpoints = metadata.get("endpoints") if isinstance(metadata.get("endpoints"), Mapping) else {}
    available = endpoints.get("available") if isinstance(endpoints.get("available"), list) else []
    selected = [e for e in available if isinstance(e, Mapping) and e.get("selected") is True]
    attempts = metadata.get("attempts")
    pipeline = metadata.get("pipeline")

    if isinstance(attempts, list):
        one_attempt = len(attempts) <= 1 and all(
            isinstance(a, Mapping) and a.get("status") == 200 for a in attempts)
    else:
        one_attempt = (metadata.get("strategy") == "direct"
                       and metadata.get("attempt") == 1
                       and len(selected) == 1)

    checks = {
        "router_metadata_present": bool(metadata),
        "served_model_exact": body.get("model") == REQUESTED_MODEL,
        "served_provider_exact": body.get("provider") == PROVIDER,
        "canonical_checkpoint_exact": len(selected) == 1
        and selected[0].get("model") == CANONICAL_CHECKPOINT,
        "direct_strategy": metadata.get("strategy") == "direct",
        "one_router_attempt": metadata.get("attempt") == 1,
        "one_selected_endpoint": len(selected) == 1,
        "no_fallback": one_attempt,
        "no_pipeline_intervention": pipeline is None or (
            isinstance(pipeline, list) and len(pipeline) == 0),
    }
    return {
        "route_version": ROUTE_VERSION,
        "checks": checks,
        "failed_checks": sorted(k for k, v in checks.items() if v is not True),
        "holds": all(v is True for v in checks.values()),
        # Observations, never criteria: making them criteria would fail a verdict on evidence this
        # API has never emitted.
        "observed_attempts_reported": attempts is not None,
        "observed_pipeline_reported": pipeline is not None,
    }
