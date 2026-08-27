"""The provider-route harness must fail closed without ever touching a qualifying bank.

These tests are deliberately milestone-neutral. They qualify transport facts only; no outcome here
can support H60 or any generality gate.
"""

from __future__ import annotations

import json

from scripts import audit_generator_routes as routes


def _good_report(**overrides):
    report = {
        "requested_model": routes.MODEL,
        "requested_provider": "Morph",
        "status": 200,
        "served_model": routes.MODEL,
        "served_provider": "Morph",
        "finish_reason": "stop",
        "structured_output_parsed": True,
        "router_metadata": {
            "requested": routes.MODEL,
            "strategy": "direct",
            "attempt": 1,
            "is_byok": True,
            "endpoints": {
                "total": 1,
                "available": [
                    {"provider": "Morph", "model": routes.MODEL, "selected": True}
                ],
            },
            "attempts": [
                {"provider": "Morph", "model": routes.MODEL, "status": 200}
            ],
            "pipeline": [],
        },
    }
    report.update(overrides)
    return report


def test_a_direct_byok_route_is_both_viable_and_byok_qualified():
    verdict = routes.evaluate_smoke(_good_report())
    assert verdict["route_viable"] is True
    assert verdict["byok_runtime_attested"] is True
    assert verdict["byok_route_qualified"] is True
    assert verdict["failed_route_checks"] == []


def test_shared_capacity_can_be_measured_as_viable_without_being_called_byok_qualified():
    report = _good_report()
    report["router_metadata"]["is_byok"] = False
    verdict = routes.evaluate_smoke(report)
    assert verdict["route_viable"] is True
    assert verdict["byok_runtime_attested"] is False
    assert verdict["byok_route_qualified"] is False
    assert verdict["failed_route_checks"] == []
    assert routes.qualifies_under_policy(verdict, require_byok=False) is True
    assert routes.qualifies_under_policy(verdict, require_byok=True) is False


def test_a_router_fallback_is_not_a_viable_route_even_if_the_last_attempt_succeeds():
    report = _good_report()
    report["router_metadata"]["attempt"] = 2
    report["router_metadata"]["attempts"] = [
        {"provider": "Morph", "model": routes.MODEL, "status": 429},
        {"provider": "Morph", "model": routes.MODEL, "status": 200},
    ]
    verdict = routes.evaluate_smoke(report)
    assert verdict["route_viable"] is False
    assert verdict["byok_route_qualified"] is False
    assert "one_router_attempt" in verdict["failed_route_checks"]
    assert "no_fallback_attempt" in verdict["failed_route_checks"]


def test_any_material_router_pipeline_stage_is_a_delta_not_silently_accepted():
    for stage in (
        {"type": "response_healing", "name": "response-healing"},
        {"type": "context_compression", "name": "context-compression"},
        {"type": "plugin", "name": "web-search"},
        {"type": "server_tools", "name": "server-tools"},
        {"type": "guardrail", "name": "content-filter"},
        {"type": "future-stage", "name": "unknown"},
    ):
        report = _good_report()
        report["router_metadata"]["pipeline"] = [stage]
        verdict = routes.evaluate_smoke(report)
        assert verdict["route_viable"] is False
        assert "no_router_pipeline_intervention" in verdict["failed_route_checks"]


def test_provider_and_model_identity_are_both_load_bearing():
    provider = _good_report(served_provider="Together")
    assert routes.evaluate_smoke(provider)["route_viable"] is False

    model = _good_report(served_model="deepseek/deepseek-v4-flash-latest")
    assert routes.evaluate_smoke(model)["route_viable"] is False

    selected = _good_report()
    selected["router_metadata"]["endpoints"]["available"][0]["provider"] = "Together"
    verdict = routes.evaluate_smoke(selected)
    assert verdict["route_viable"] is False
    assert "selected_endpoint_exact" in verdict["failed_route_checks"]


def test_router_metadata_is_evidence_not_an_optional_nicety():
    verdict = routes.evaluate_smoke(_good_report(router_metadata=None))
    assert verdict["route_viable"] is False
    assert verdict["byok_route_qualified"] is False
    assert "router_metadata_present" in verdict["failed_route_checks"]
    assert verdict["byok_runtime_attested"] is False


def test_allowlist_sanitizer_drops_account_and_credential_shaped_fields():
    raw = {
        "requested": routes.MODEL,
        "strategy": "direct",
        "attempt": 1,
        "is_byok": True,
        "user_id": "SHOULD_NOT_SURVIVE",
        "workspace_id": "SHOULD_NOT_SURVIVE",
        "label": "SHOULD_NOT_SURVIVE",
        "api_key_hash": "SHOULD_NOT_SURVIVE",
        "endpoints": {
            "total": 1,
            "available": [
                {
                    "provider": "Morph",
                    "model": routes.MODEL,
                    "selected": True,
                    "credential_id": "SHOULD_NOT_SURVIVE",
                }
            ],
        },
        "attempts": [
            {
                "provider": "Morph",
                "model": routes.MODEL,
                "status": 200,
                "message": "SHOULD_NOT_SURVIVE",
            }
        ],
        "pipeline": [
            {
                "type": "guardrail",
                "name": "content-filter",
                "data": {"private": "SHOULD_NOT_SURVIVE"},
            }
        ],
    }
    safe = routes._safe_router_metadata(raw)
    encoded = json.dumps(safe, sort_keys=True)
    assert "SHOULD_NOT_SURVIVE" not in encoded
    assert safe["is_byok"] is True
    assert safe["attempts"] == [
        {"provider": "Morph", "model": routes.MODEL, "status": 200}
    ]


def test_error_sanitizer_keeps_only_a_code():
    safe = routes._safe_error(
        {
            "error": {
                "code": 429,
                "message": "account user_private is rate limited",
                "metadata": {"user_id": "user_private"},
            }
        }
    )
    assert safe == {"code": 429}


def test_public_performance_metric_sanitizer_keeps_numbers_only():
    safe = routes._safe_percentiles(
        {"p50": 0.25, "p75": 0.35, "p90": 0.48, "p99": 0.85, "private": "drop"}
    )
    assert safe == {"p50": 0.25, "p75": 0.35, "p90": 0.48, "p99": 0.85}
    assert routes._safe_percentiles({"p50": True, "p90": "0.48"}) is None
    assert routes._safe_percentiles("not-a-record") is None


def test_smoke_schema_is_checked_as_structure_not_merely_json_parseability():
    assert routes._structured_output_holds('{"samples":[{"value":10},{"value":99}]}') is True
    assert routes._structured_output_holds('{"samples":[{"value":9},{"value":99}]}') is False
    assert routes._structured_output_holds('{"samples":[{"value":10}]}') is False
    assert (
        routes._structured_output_holds(
            '{"samples":[{"value":10},{"value":99}],"extra":1}'
        )
        is False
    )
    assert routes._structured_output_holds("not json") is False


def test_route_smoke_is_not_any_existing_qualifying_input():
    # This reads predecessor bytes but does not print them and makes no network request.
    routes._assert_smoke_is_not_qualifying_input()


def test_a_non_200_never_qualifies_even_with_forged_positive_metadata():
    verdict = routes.evaluate_smoke(_good_report(status=429))
    assert verdict["route_viable"] is False
    assert verdict["byok_route_qualified"] is False
    assert "http_200" in verdict["failed_route_checks"]


def test_missing_attempts_array_fails_closed_for_no_fallback_evidence():
    report = _good_report()
    report["router_metadata"]["attempts"] = None
    verdict = routes.evaluate_smoke(report)
    assert verdict["route_viable"] is False
    assert "no_fallback_attempt" in verdict["failed_route_checks"]


def test_empty_attempts_array_is_not_mistaken_for_one_successful_attempt():
    report = _good_report()
    report["router_metadata"]["attempts"] = []
    verdict = routes.evaluate_smoke(report)
    assert verdict["route_viable"] is False
    assert "no_fallback_attempt" in verdict["failed_route_checks"]


def test_byok_policy_is_strictly_additive_to_generic_route_viability():
    shared = routes.evaluate_smoke(
        {
            **_good_report(),
            "router_metadata": {**_good_report()["router_metadata"], "is_byok": False},
        }
    )
    byok = routes.evaluate_smoke(_good_report())
    assert shared["route_checks"] == byok["route_checks"]
    assert shared["route_viable"] is True
    assert byok["route_viable"] is True
    assert shared["byok_route_qualified"] is False
    assert byok["byok_route_qualified"] is True
