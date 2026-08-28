"""Adversarial tests for audit_generator_routes.py — model identity and fallback attestation.

These tests verify the instrument's honesty, not OpenRouter's behaviour. They use
synthetic metadata to ensure the checks fail closed on ambiguity and succeed only
on positive, verifiable evidence.
"""

from __future__ import annotations

from scripts.audit_generator_routes import (
    evaluate_smoke,
    _canonical_slug,
    _selected_endpoints,
    _CANONICAL_SLUGS,
    ROUTER_METADATA_HEADER,
    SMOKE_INPUT,
    SMOKE_SCHEMA,
    MODEL,
    QUALIFYING_INPUT_PATHS,
    smoke_provider,
    _assert_smoke_is_not_qualifying_input,
    RouteAuditError,
)


# ── Helpers ──────────────────────────────────────────────────────────────

MODEL_ALIAS = "deepseek/deepseek-v4-flash-0731"
MODEL_CANONICAL = "deepseek/deepseek-v4-flash-20260731"
PROVIDER = "Morph"


def _smoke_report(
    status: int = 200,
    served_model: str | None = MODEL_ALIAS,
    served_provider: str | None = PROVIDER,
    finish_reason: str = "stop",
    structured_output_parsed: bool = True,
    requested_model: str = MODEL_ALIAS,
    requested_provider: str = PROVIDER,
    router_metadata: dict | None = None,
) -> dict:
    """Build a synthetic smoke report for testing evaluate_smoke()."""
    return {
        "status": status,
        "served_model": served_model,
        "served_provider": served_provider,
        "finish_reason": finish_reason,
        "structured_output_parsed": structured_output_parsed,
        "requested_model": requested_model,
        "requested_provider": requested_provider,
        "router_metadata": router_metadata,
    }


def _metadata(
    strategy: str = "direct",
    attempt: int = 1,
    attempts: list[dict] | None = None,
    selected_model: str = MODEL_CANONICAL,
    selected_provider: str = PROVIDER,
    pipeline: list | None = None,
    is_byok: bool = False,
    requested: str = MODEL_ALIAS,
) -> dict:
    """Build synthetic OpenRouter router metadata."""
    available = [{"provider": selected_provider, "model": selected_model, "selected": True}]
    return {
        "requested": requested,
        "strategy": strategy,
        "attempt": attempt,
        "is_byok": is_byok,
        "endpoints": {"total": 29, "available": available},
        "attempts": attempts if attempts is not None else [],
        "pipeline": pipeline if pipeline is not None else [],
    }


# ── _canonical_slug ─────────────────────────────────────────────────────


def test_canonical_slug_known():
    """Known alias returns the canonical slug from the explicit mapping."""
    assert _canonical_slug(MODEL_ALIAS) == MODEL_CANONICAL


def test_canonical_slug_unknown():
    """Unknown alias returns None — no inference from string patterns."""
    assert _canonical_slug("unknown/unknown-model") is None


def test_canonical_slug_different_suffix():
    """A different model with the same prefix is NOT in the mapping."""
    # This model has a different date suffix — it must NOT be treated as
    # the same canonical checkpoint.
    assert _canonical_slug("deepseek/deepseek-v4-flash-0423") is None
    # The mapping contains only the exact verified alias.
    assert MODEL_ALIAS in _CANONICAL_SLUGS


# ── selected_endpoint_exact (strict comparison) ──────────────────────────


def test_selected_endpoint_exact_matches_when_identical():
    """selected_endpoint_exact is true only when endpoint model == requested model."""
    meta = _metadata(selected_model=MODEL_ALIAS)  # same as alias
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["route_checks"]["selected_endpoint_exact"] is True


def test_selected_endpoint_exact_fails_on_canonical_slug():
    """Canonical checkpoint slug != alias — selected_endpoint_exact is false."""
    meta = _metadata(selected_model=MODEL_CANONICAL)  # the canonical slug
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["route_checks"]["selected_endpoint_exact"] is False


def test_selected_endpoint_exact_fails_on_different_model():
    """A different model with the same prefix is not accepted as exact."""
    meta = _metadata(selected_model="deepseek/deepseek-v4-flash-0423")
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["route_checks"]["selected_endpoint_exact"] is False


def test_selected_endpoint_exact_fails_on_wrong_canonical_checkpoint():
    """Different canonical checkpoint with same prefix — not exact."""
    meta = _metadata(selected_model="deepseek/deepseek-v4-flash-0423")
    report = _smoke_report(
        requested_model=MODEL_ALIAS,
        served_model=MODEL_ALIAS,
        router_metadata=meta,
    )
    result = evaluate_smoke(report)
    assert result["route_checks"]["selected_endpoint_exact"] is False
    assert result["canonical_checkpoint_match"] is False


def test_selected_endpoint_exact_fails_on_unknown_alias():
    """An alias without a verified canonical relation has endpoint matching the alias → exact OK."""
    # When the endpoint model matches the alias it's still exact — the issue is
    # that canonical_checkpoint_match is false (no verified slug).
    meta = _metadata(selected_model="some/other-model-v1")
    report = _smoke_report(
        requested_model="some/other-model-v1",
        router_metadata=meta,
    )
    result = evaluate_smoke(report)
    assert result["route_checks"]["selected_endpoint_exact"] is True
    assert result["canonical_checkpoint_match"] is False


# ── canonical_checkpoint_match ───────────────────────────────────────────


def test_canonical_checkpoint_match_known_alias():
    """When alias is known, the canonical slug matches the endpoint model."""
    meta = _metadata(selected_model=MODEL_CANONICAL)
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["canonical_checkpoint_match"] is True


def test_canonical_checkpoint_match_wrong_model():
    """When endpoint model is NOT the canonical slug, match fails."""
    meta = _metadata(selected_model="deepseek/deepseek-v4-flash-0423")
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["canonical_checkpoint_match"] is False


def test_canonical_checkpoint_match_unknown_alias():
    """When alias is unknown, canonical_checkpoint_match is false (not None)."""
    meta = _metadata(selected_model="some/other-model-v1")
    report = _smoke_report(
        requested_model="some/other-model-v1",
        router_metadata=meta,
    )
    result = evaluate_smoke(report)
    assert result["canonical_checkpoint_match"] is False


# ── no_fallback_attested ─────────────────────────────────────────────────


def test_no_fallback_attested_empty_attempts_direct():
    """Empty attempts list + strategy=direct + one endpoint = attested (no fallback by construction)."""
    meta = _metadata(attempts=[])
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["no_fallback_attested_value"] is True
    assert result["route_checks"]["no_fallback_attested"] is True


def test_no_fallback_attested_empty_attempts_no_direct():
    """Empty attempts list WITHOUT strategy=direct is unknown (not false)."""
    meta = _metadata(strategy="route", attempts=[])
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["no_fallback_attested_value"] is None
    assert result["route_checks"]["no_fallback_attested"] is False


def test_no_fallback_attested_single_exact_attempt():
    """Single attempt that matches the provider is accepted."""
    attempt = [{"provider": PROVIDER, "model": MODEL_ALIAS, "status": 200}]
    meta = _metadata(attempts=attempt)
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["no_fallback_attested_value"] is True
    assert result["route_checks"]["no_fallback_attested"] is True


def test_no_fallback_attested_multiple_attempts():
    """Multiple attempts = fallback occurred → attested is false."""
    attempts = [
        {"provider": PROVIDER, "model": MODEL_ALIAS, "status": 200},
        {"provider": "Other", "model": MODEL_ALIAS, "status": 200},
    ]
    meta = _metadata(attempts=attempts)
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["no_fallback_attested_value"] is False
    assert result["route_checks"]["no_fallback_attested"] is False


def test_no_fallback_attested_wrong_provider_in_attempt():
    """Attempt from a different provider is not accepted as no-fallback."""
    attempt = [{"provider": "Other", "model": MODEL_ALIAS, "status": 200}]
    meta = _metadata(attempts=attempt)
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["no_fallback_attested_value"] is False
    assert result["route_checks"]["no_fallback_attested"] is False


# ── route_viable — requires all checks including no_fallback_attested ────


def test_route_viable_requires_no_fallback_attested():
    """route_viable is false when no_fallback_attested is unknown or false."""
    # Unknown no_fallback
    meta = _metadata(strategy="route", attempts=[])
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    assert result["route_viable"] is False
    assert "no_fallback_attested" in result["failed_route_checks"]

    # False no_fallback (multiple attempts)
    meta2 = _metadata(attempts=[{"provider": "A", "model": MODEL_ALIAS, "status": 200},
                                 {"provider": "B", "model": MODEL_ALIAS, "status": 200}])
    report2 = _smoke_report(router_metadata=meta2)
    result2 = evaluate_smoke(report2)
    assert result2["route_viable"] is False


def test_route_viable_smoke_morph():
    """A typical Morph smoke with canonical checkpoint should be viable (selected_endpoint_exact=false but canonical_match=true)."""
    meta = _metadata(
        selected_model=MODEL_CANONICAL,  # canonical slug, not alias
    )
    report = _smoke_report(router_metadata=meta)
    result = evaluate_smoke(report)
    # selected_endpoint_exact is false (alias != canonical slug)
    # no_fallback_attested is true (strategy=direct, one endpoint)
    # canonical_checkpoint_match is true
    # route_viable requires no_fallback_attested to be true
    assert result["route_checks"]["http_200"] is True
    assert result["route_checks"]["served_model_exact"] is True
    assert result["route_checks"]["served_provider_exact"] is True
    assert result["route_checks"]["structured_output_strictly_parsed"] is True
    assert result["route_checks"]["finish_reason_stop"] is True
    assert result["route_checks"]["router_strategy_direct"] is True
    assert result["route_checks"]["one_router_attempt"] is True
    assert result["route_checks"]["one_selected_endpoint"] is True
    assert result["route_checks"]["selected_endpoint_exact"] is False
    assert result["route_checks"]["no_fallback_attested"] is True
    assert result["route_checks"]["no_router_pipeline_intervention"] is True
    # route_viable is false because selected_endpoint_exact is false
    # This is correct — the contract says exact, and canonical != alias
    assert result["route_viable"] is False
    assert result["canonical_checkpoint_match"] is True


# ── POST requirement for smoke_provider ──────────────────────────────────


def test_smoke_provider_has_post():
    """smoke_provider must call _request with method='POST', not default GET."""
    # Smoke body is a chat completion — only POST works
    import inspect
    source = inspect.getsource(smoke_provider)
    assert "_request(ENDPOINT, method=\"POST\", body=body, timeout=300)" in source, (
        "smoke_provider must call _request with explicit method='POST'"
    )


# ── _assert_smoke_is_not_qualifying_input ────────────────────────────────


def test_smoke_input_is_not_qualifying_input():
    """The smoke input must differ from any qualifying input by digest."""
    # This should not raise — it means the smoke is safe
    _assert_smoke_is_not_qualifying_input()