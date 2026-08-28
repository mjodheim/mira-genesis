from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts import derive_m115_h60_candidate as candidate


ROOT = Path(__file__).resolve().parents[1]
MATRIX = json.loads(
    (ROOT / "experiments" / "M115" / "RUNTIME_ROUTE_MATRIX_DEVELOPMENT.json").read_text(
        encoding="utf-8"
    )
)


def _alibaba_smoke() -> dict:
    return copy.deepcopy(
        next(
            item
            for item in MATRIX["smoke_reports"]
            if item["requested_provider"] == "Alibaba"
        )
    )


def test_preserved_matrix_derives_alibaba_without_qualifying_activity() -> None:
    derived = candidate.derive_candidate(MATRIX)
    assert derived["admissible_smoke_count"] == 13
    assert derived["selected_provider_candidate"] == "Alibaba"
    assert derived["ranked_providers"][0] == "Alibaba"
    assert derived["qualifying_calls"] == 0
    assert derived["selection_rule_adopted_for_h60_after_matrix_observation"] is True
    assert derived["selection_rule_adopted_before_h60_freeze"] is True


def test_literal_alias_equality_is_not_silently_reintroduced() -> None:
    smoke = _alibaba_smoke()
    smoke["route_checks"]["selected_endpoint_exact"] = True
    assert candidate.h60_route_admissible(smoke) is False


def test_unknown_or_different_checkpoint_fails_closed() -> None:
    smoke = _alibaba_smoke()
    smoke["router_metadata"]["endpoints"]["available"][0]["model"] = (
        "deepseek/deepseek-v4-flash-20260801"
    )
    assert candidate.h60_route_admissible(smoke) is False


def test_provider_substitution_fails_closed() -> None:
    smoke = _alibaba_smoke()
    smoke["router_metadata"]["endpoints"]["available"][0]["provider"] = "Other"
    assert candidate.h60_route_admissible(smoke) is False


def test_no_fallback_must_be_positively_attested() -> None:
    smoke = _alibaba_smoke()
    smoke["no_fallback_attested_value"] = None
    assert candidate.h60_route_admissible(smoke) is False


def test_every_preserved_route_safeguard_remains_required() -> None:
    for name in candidate._REQUIRED_ROUTE_CHECKS:
        smoke = _alibaba_smoke()
        smoke["route_checks"][name] = False
        assert candidate.h60_route_admissible(smoke) is False, name


def test_qualifying_markers_fail_closed() -> None:
    smoke = _alibaba_smoke()
    smoke["qualifying_input_was_sent"] = True
    assert candidate.h60_route_admissible(smoke) is False

    matrix = copy.deepcopy(MATRIX)
    matrix["is_a_qualifying_run"] = True
    with pytest.raises(ValueError):
        candidate.derive_candidate(matrix)


def test_reliability_ordering_drift_is_rejected() -> None:
    matrix = copy.deepcopy(MATRIX)
    matrix["recommendation_policy"]["ordering"] = list(
        reversed(matrix["recommendation_policy"]["ordering"])
    )
    with pytest.raises(ValueError, match="ordering"):
        candidate.derive_candidate(matrix)


def test_missing_reliability_metric_is_rejected() -> None:
    matrix = copy.deepcopy(MATRIX)
    discovery = next(
        item for item in matrix["discovery_reports"] if item["requested_provider"] == "Alibaba"
    )
    discovery["uptime_last_1d"] = None
    with pytest.raises(ValueError, match="Alibaba"):
        candidate.derive_candidate(matrix)
