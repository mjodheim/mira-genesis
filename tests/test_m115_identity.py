"""Adversarial tests for M115's prospective alias->canonical checkpoint identity rule."""

from __future__ import annotations

from metamorphosis import m115_identity as identity


def _metadata():
    return {
        "requested": identity.REQUESTED_MODEL,
        "strategy": "direct",
        "attempt": 1,
        "is_byok": False,
        "endpoints": {
            "total": 29,
            "available": [
                {
                    "provider": identity.SELECTED_PROVIDER,
                    "model": identity.CANONICAL_CHECKPOINT,
                    "selected": True,
                }
            ],
        },
        "attempts": [],
        "pipeline": [],
    }


def _body():
    return {
        "model": identity.REQUESTED_MODEL,
        "provider": identity.SELECTED_PROVIDER,
        "openrouter_metadata": _metadata(),
        "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
    }


def test_exact_alias_to_explicit_canonical_checkpoint_holds():
    result = identity.attest_completion_response(_body())
    assert result["holds"] is True
    assert result["failed_checks"] == []
    assert result["router_attestation"]["canonical_checkpoint"] == identity.CANONICAL_CHECKPOINT


def test_mutable_or_pattern_similar_checkpoint_is_refused():
    for wrong in (
        "deepseek/deepseek-v4-flash-latest",
        "deepseek/deepseek-v4-flash-20260730",
        "deepseek/deepseek-v4-flash-0731",
        "deepseek/deepseek-v4-flash-20260731:free",
    ):
        body = _body()
        body["openrouter_metadata"]["endpoints"]["available"][0]["model"] = wrong
        result = identity.attest_completion_response(body)
        assert result["holds"] is False
        assert "selected_checkpoint_exact" in result["failed_checks"]


def test_provider_substitution_is_refused_even_on_the_same_checkpoint():
    body = _body()
    body["provider"] = "Morph"
    body["openrouter_metadata"]["endpoints"]["available"][0]["provider"] = "Morph"
    result = identity.attest_completion_response(body)
    assert result["holds"] is False
    assert "served_provider_exact" in result["failed_checks"]
    assert "selected_provider_exact" in result["failed_checks"]


def test_top_level_alias_must_still_be_the_requested_dated_alias():
    body = _body()
    body["model"] = identity.CANONICAL_CHECKPOINT
    result = identity.attest_completion_response(body)
    assert result["holds"] is False
    assert "served_model_alias_exact" in result["failed_checks"]


def test_no_metadata_no_attestation():
    body = _body()
    body.pop("openrouter_metadata")
    result = identity.attest_completion_response(body)
    assert result["holds"] is False
    assert "router_metadata_present" in result["failed_checks"]


def test_multiple_or_unselected_endpoints_are_refused():
    body = _body()
    body["openrouter_metadata"]["endpoints"]["available"].append(
        {"provider": "Morph", "model": identity.CANONICAL_CHECKPOINT, "selected": True}
    )
    assert identity.attest_completion_response(body)["holds"] is False

    body = _body()
    body["openrouter_metadata"]["endpoints"]["available"][0]["selected"] = False
    assert identity.attest_completion_response(body)["holds"] is False


def test_fallback_attempt_is_refused():
    body = _body()
    body["openrouter_metadata"]["attempt"] = 2
    body["openrouter_metadata"]["attempts"] = [
        {"provider": "Morph", "model": identity.REQUESTED_MODEL, "status": 429},
        {"provider": identity.SELECTED_PROVIDER, "model": identity.REQUESTED_MODEL, "status": 200},
    ]
    result = identity.attest_completion_response(body)
    assert result["holds"] is False
    assert "one_router_attempt" in result["failed_checks"]
    assert "no_fallback_attested" in result["failed_checks"]


def test_pipeline_intervention_is_refused():
    body = _body()
    body["openrouter_metadata"]["pipeline"] = [
        {"type": "response_healing", "name": "response-healing"}
    ]
    result = identity.attest_completion_response(body)
    assert result["holds"] is False
    assert "no_pipeline_intervention" in result["failed_checks"]


def test_safe_projection_drops_account_and_credential_fields():
    raw = _metadata()
    raw.update(
        {
            "user_id": "private-user",
            "workspace_id": "private-workspace",
            "label": "sk-private-fragment",
            "credential_id": "provider-secret-id",
        }
    )
    raw["endpoints"]["available"][0]["credential_id"] = "private-provider-key"
    safe = identity.safe_router_metadata(raw)
    rendered = repr(safe)
    for private in (
        "private-user",
        "private-workspace",
        "sk-private-fragment",
        "provider-secret-id",
        "private-provider-key",
    ):
        assert private not in rendered


def test_byok_is_observed_but_does_not_change_identity_verdict():
    body = _body()
    body["openrouter_metadata"]["is_byok"] = False
    shared = identity.attest_completion_response(body)
    body["openrouter_metadata"]["is_byok"] = True
    byok = identity.attest_completion_response(body)
    assert shared["holds"] is True
    assert byok["holds"] is True
    assert shared["router_attestation"]["is_byok_observed"] is False
    assert byok["router_attestation"]["is_byok_observed"] is True
