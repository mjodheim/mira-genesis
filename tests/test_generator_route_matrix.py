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
    assert (
        matrix.discovery_is_predecessor_compatible(
            _discovery("Broken", supports_structured_outputs=False)
        )
        is False
    )
    assert matrix.discovery_is_predecessor_compatible(_discovery("Down", endpoint_status=-2)) is False
    assert matrix.discovery_is_predecessor_compatible(_discovery("Unknown", endpoint_status=None)) is False


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


def test_default_candidates_preserve_morph_as_continuity_control_and_deepinfra_as_reliable_option():
    assert "Morph" in matrix.DEFAULT_CANDIDATES
    assert "DeepInfra" in matrix.DEFAULT_CANDIDATES
    assert len(matrix.DEFAULT_CANDIDATES) == len(set(matrix.DEFAULT_CANDIDATES))
