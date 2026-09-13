from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / "docs" / "free-metamorphosis-v5" / "preregistration.json"


def _keys(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _keys(nested)


def test_v5_preregistration_is_prospective_and_fixes_success_boundary() -> None:
    payload = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    assert payload["schema"] == "genesis-free-metamorphosis-v5-preregistration-v1"
    assert payload["prospective"] is True
    assert payload["v4_results_rescored"] is False
    assert payload["private_control_merge"] == "5f6f874394bee26bd18515cfe1deffd686108b95"
    assert payload["proposer"]["attempt_specific_human_guidance_allowed"] is False
    assert payload["frontier"]["promotion_is_champion_relative"] is True
    assert payload["selection"]["protected_regression_allowed"] is False
    assert payload["selection"]["cross_runner_elapsed_time_is_fitness"] is False
    assert payload["success_criterion"] == {
        "minimum_champion_promotions": 2,
        "requires_promotion_through_prior_neutral_ancestor": True,
        "requires_later_bundle_inheriting_resulting_champion": True,
        "requires_hard_boundary_and_no_protected_regression": True,
    }


def test_v5_public_preregistration_does_not_publish_private_authority_fields() -> None:
    payload = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    keys = set(_keys(payload))
    forbidden = {
        "required_all",
        "required_any",
        "forbidden_tools",
        "case_message",
        "expected_label",
        "observed_label",
        "api_log_tail",
        "stdout_tail",
        "stderr_tail",
        "evaluator_image_id",
        "evaluation_commands",
        "fixture_request",
        "fixture_response",
    }
    assert keys.isdisjoint(forbidden)
    assert all(value is False for value in payload["claim_boundary"].values() if isinstance(value, bool) and value is not payload["claim_boundary"]["bounded_mira_task_surface_only"])
    assert payload["redaction"] == {
        "private_source_published": False,
        "raw_proposals_published": False,
        "proposer_bundles_published": False,
        "campaign_state_archives_published": False,
        "evaluator_cases_published": False,
        "execution_fixture_details_published": False,
        "private_paths_published": False,
        "raw_logs_published": False,
        "credentials_or_environment_values_published": False,
    }
