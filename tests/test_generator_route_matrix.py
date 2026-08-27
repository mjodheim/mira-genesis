"""Tests for the DEVELOPMENT-only provider route matrix."""

from __future__ import annotations

from scripts import audit_generator_matrix as matrix


def _discovery(provider: str, **overrides):
    report = {
        "provider_found": True,
        "status": 200,
        "requested_provider": provider,
        "supports_structured_outputs": True,
        "supports_seed": True,
        "endpoint_status": 0,
        "uptime_last_30m": 0.99,
        "uptime_last_1d": 0.98,
        "latency_last_30m": {"p50": 0.5},
    }
    report.update(overrides)
    return report


def _smoke(provider: str, viable: bool = True, byok: bool = False):
    return {
        "requested_provider": provider,
        "route_viable": viable,
        "byok_route_qualified": byok,
    }


def test_predecessor_compatibility_requires_structure_seed_and_positive_live_endpoint():
    assert matrix.discovery_is_predecessor_compatible(_discovery("DeepInfra")) is True
    assert matrix.discovery_is_predecessor_compatible(_discovery("Together", supports_seed=False)) is False
    assert matrix.discovery_is_predecessor_compatible(_discovery("Broken", supports_structured_outputs=False)) is False
    assert matrix.discovery_is_predecessor_compatible(_discovery("Down", endpoint_status=-2)) is False
    assert matrix.discovery_is_predecessor_compatible(_discovery("Unknown", endpoint_status=None)) is False
    assert matrix.discovery_is_predecessor_compatible(_discovery("BooleanFalse", endpoint_status=False)) is False
    assert matrix.discovery_is_predecessor_compatible(_discovery("BooleanTrue", endpoint_status=True)) is False


def test_predeclared_policy_prioritizes_one_day_uptime_before_short_window():
    discoveries = {
        "ShortWindowWinner": _discovery(
            "ShortWindowWinner", uptime_last_1d=0.97, uptime_last_30m=1.0, latency_last_30m={"p50": 0.1}
        ),
        "LongWindowWinner": _discovery(
            "LongWindowWinner", uptime_last_1d=0.999, uptime_last_30m=0.98, latency_last_30m={"p50": 1.0}
        ),
    }
    ranked = matrix.rank_viable_routes(
        [_smoke("ShortWindowWinner"), _smoke("LongWindowWinner")], discoveries
    )
    assert ranked == ["LongWindowWinner", "ShortWindowWinner"]


def test_missing_reliability_measurements_make_a_viable_route_unrankable():
    discoveries = {
        "Complete": _discovery("Complete"),
        "Missing1d": _discovery("Missing1d", uptime_last_1d=None),
        "Missing30m": _discovery("Missing30m", uptime_last_30m=None),
        "MissingLatency": _discovery("MissingLatency", latency_last_30m=None),
    }
    smokes = [_smoke(provider) for provider in discoveries]
    assert matrix.rank_viable_routes(smokes, discoveries) == ["Complete"]
    summary = matrix.summarize(list(discoveries.values()), smokes)
    assert summary["development_recommended_successor_route"] == "Complete"
    assert summary["viable_but_unrankable_missing_metrics"] == [
        "Missing1d",
        "Missing30m",
        "MissingLatency",
    ]


def test_reliability_ranking_only_contains_routes_that_actually_smoked_viable():
    discoveries = {
        "Morph": _discovery(
            "Morph", uptime_last_30m=0.25, uptime_last_1d=0.4, latency_last_30m={"p50": 0.1}
        ),
        "DeepInfra": _discovery(
            "DeepInfra", uptime_last_30m=0.999, uptime_last_1d=0.998, latency_last_30m={"p50": 0.4}
        ),
        "Cloudflare": _discovery(
            "Cloudflare", uptime_last_30m=0.999, uptime_last_1d=0.999, latency_last_30m={"p50": 0.8}
        ),
    }
    ranked = matrix.rank_viable_routes(
        [_smoke("Morph", viable=False), _smoke("DeepInfra"), _smoke("Cloudflare")],
        discoveries,
    )
    assert ranked == ["Cloudflare", "DeepInfra"]


def test_summary_separates_generic_viability_from_byok_qualification():
    discoveries = [_discovery("DeepInfra"), _discovery("Morph")]
    smokes = [_smoke("DeepInfra", viable=True, byok=False), _smoke("Morph", viable=True, byok=True)]
    summary = matrix.summarize(discoveries, smokes)
    assert summary["route_viable"] == ["DeepInfra", "Morph"]
    assert summary["byok_route_qualified"] == ["Morph"]
    assert summary["qualifying_calls"] == 0
    assert summary["ranking_is_a_milestone_selection_rule"] is False
    assert summary["recommendation_policy"]["defined_before_first_matrix_run"] is True
    assert summary["recommendation_policy"]["byok_is_a_ranking_input"] is False
    assert summary["recommendation_policy"]["quantization_is_a_ranking_input"] is False


def test_matrix_discovers_every_candidate_but_smokes_only_compatible_routes(monkeypatch):
    discovered = []
    smoked = []

    def fake_discover(provider: str):
        discovered.append(provider)
        if provider == "Together":
            return _discovery(provider, supports_seed=False)
        return _discovery(provider)

    def fake_smoke(provider: str):
        smoked.append(provider)
        return _smoke(provider)

    monkeypatch.setattr(matrix.routes, "_assert_smoke_is_not_qualifying_input", lambda: None)
    monkeypatch.setattr(matrix.routes, "discover_provider", fake_discover)
    monkeypatch.setattr(matrix.routes, "smoke_provider", fake_smoke)

    report = matrix.run_matrix(["DeepInfra", "Together", "DeepInfra", "Morph"])
    assert discovered == ["DeepInfra", "Together", "Morph"]
    assert smoked == ["DeepInfra", "Morph"]
    assert report["is_a_qualifying_run"] is False
    assert report["qualifying_input_was_sent"] is False
    assert report["summary"]["qualifying_calls"] == 0
    assert report["recommendation_policy"] == matrix.RECOMMENDATION_POLICY


def test_matrix_isolates_discovery_exception_and_continues_without_leaking_exception(monkeypatch):
    discovered = []
    smoked = []

    def fake_discover(provider: str):
        discovered.append(provider)
        if provider == "Broken":
            raise RuntimeError("private upstream diagnostic user_id=secret")
        return _discovery(provider)

    def fake_smoke(provider: str):
        smoked.append(provider)
        return _smoke(provider)

    monkeypatch.setattr(matrix.routes, "_assert_smoke_is_not_qualifying_input", lambda: None)
    monkeypatch.setattr(matrix.routes, "discover_provider", fake_discover)
    monkeypatch.setattr(matrix.routes, "smoke_provider", fake_smoke)

    report = matrix.run_matrix(["DeepInfra", "Broken", "Morph"])
    assert discovered == ["DeepInfra", "Broken", "Morph"]
    assert smoked == ["DeepInfra", "Morph"]
    broken = report["discovery_reports"][1]
    assert broken == {
        "requested_provider": "Broken",
        "provider_found": False,
        "status": None,
        "supports_structured_outputs": False,
        "supports_seed": False,
        "endpoint_status": None,
        "discovery_failed": True,
        "failure_class": "discovery_exception",
    }
    assert "private upstream diagnostic" not in str(report)
    assert "user_id" not in str(report)


def test_default_candidates_preserve_morph_as_continuity_control_and_deepinfra_as_reliable_option():
    assert "Morph" in matrix.DEFAULT_CANDIDATES
    assert "DeepInfra" in matrix.DEFAULT_CANDIDATES
    assert len(matrix.DEFAULT_CANDIDATES) == len(set(matrix.DEFAULT_CANDIDATES))
