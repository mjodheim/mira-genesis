"""M115 provider selection must be derived from preserved DEVELOPMENT evidence only."""

from __future__ import annotations

import copy

import pytest

from metamorphosis import m115_route_selection as selection


def _preserved():
    return selection.load_preserved_matrix()


def test_preserved_matrix_selects_alibaba_under_the_predeclared_ordering():
    result = selection.derive_preserved_selection()
    assert result["selected_provider"] == "Alibaba"
    assert result["canonical_checkpoint"] == "deepseek/deepseek-v4-flash-20260731"
    assert result["requested_model"] == "deepseek/deepseek-v4-flash-0731"
    assert result["qualifying_calls_observed_during_selection"] == 0
    assert result["selected_metrics"]["uptime_last_1d"] == pytest.approx(99.98945871422205)
    assert result["selected_quantization"] == "unknown"


def test_literal_alias_equality_is_not_smuggled_back_into_the_new_boundary():
    matrix = _preserved()
    result = selection.derive_selection(matrix)
    assert result["selected_provider"] == "Alibaba"
    alibaba = next(
        item for item in matrix["smoke_reports"] if item["requested_provider"] == "Alibaba"
    )
    assert alibaba["route_checks"]["selected_endpoint_exact"] is False
    assert alibaba["canonical_checkpoint_match"] is True


def test_unknown_or_pattern_inferred_checkpoint_never_qualifies():
    matrix = copy.deepcopy(_preserved())
    smoke = next(item for item in matrix["smoke_reports"] if item["requested_provider"] == "Alibaba")
    smoke["router_metadata"]["endpoints"]["available"][0]["model"] = (
        "deepseek/deepseek-v4-flash-20260730"
    )
    with pytest.raises(selection.RouteSelectionError):
        # Break every other eligible smoke too, so there is no accidental successor.
        for item in matrix["smoke_reports"]:
            item["canonical_checkpoint_match"] = item["requested_provider"] == "Alibaba"
        selection.derive_selection(matrix)


def test_provider_substitution_is_not_a_canonical_checkpoint_match():
    matrix = copy.deepcopy(_preserved())
    smoke = next(item for item in matrix["smoke_reports"] if item["requested_provider"] == "Alibaba")
    discovery = next(
        item for item in matrix["discovery_reports"] if item["requested_provider"] == "Alibaba"
    )
    smoke["served_provider"] = "Morph"
    assert selection.canonical_successor_eligible(discovery, smoke) is False


def test_fallback_or_pipeline_intervention_disqualifies_a_route():
    matrix = copy.deepcopy(_preserved())
    smoke = next(item for item in matrix["smoke_reports"] if item["requested_provider"] == "Alibaba")
    discovery = next(
        item for item in matrix["discovery_reports"] if item["requested_provider"] == "Alibaba"
    )
    smoke["no_fallback_attested_value"] = False
    assert selection.canonical_successor_eligible(discovery, smoke) is False

    smoke = copy.deepcopy(
        next(item for item in matrix["smoke_reports"] if item["requested_provider"] == "OpenInference")
    )
    discovery = next(
        item for item in matrix["discovery_reports"] if item["requested_provider"] == "OpenInference"
    )
    smoke["router_metadata"]["pipeline"] = [{"type": "plugin", "name": "something"}]
    smoke["route_checks"]["no_router_pipeline_intervention"] = False
    assert selection.canonical_successor_eligible(discovery, smoke) is False


def test_reliability_order_is_not_rewritten_after_observation():
    matrix = copy.deepcopy(_preserved())
    matrix["recommendation_policy"]["ordering"] = [
        "latency_last_30m_p50_asc",
        "uptime_last_1d_desc",
        "uptime_last_30m_desc",
        "provider_name_asc",
    ]
    with pytest.raises(selection.RouteSelectionError, match="ordering"):
        selection.derive_selection(matrix)


def test_byok_and_quantization_cannot_become_posthoc_ranking_inputs():
    for key in ("byok_is_a_ranking_input", "quantization_is_a_ranking_input"):
        matrix = copy.deepcopy(_preserved())
        matrix["recommendation_policy"][key] = True
        with pytest.raises(selection.RouteSelectionError):
            selection.derive_selection(matrix)


def test_any_qualifying_observation_poisoning_selection_fails_closed():
    matrix = copy.deepcopy(_preserved())
    matrix["summary"]["qualifying_calls"] = 1
    with pytest.raises(selection.RouteSelectionError, match="zero qualifying"):
        selection.derive_selection(matrix)

    matrix = copy.deepcopy(_preserved())
    matrix["qualifying_input_was_sent"] = True
    with pytest.raises(selection.RouteSelectionError, match="qualifying input"):
        selection.derive_selection(matrix)


def test_missing_reliability_data_cannot_be_silently_ranked():
    matrix = copy.deepcopy(_preserved())
    for item in matrix["discovery_reports"]:
        if item["requested_provider"] == "Alibaba":
            item["uptime_last_1d"] = None
    with pytest.raises(selection.RouteSelectionError, match="incomplete reliability evidence"):
        selection.derive_selection(matrix)
