from __future__ import annotations

import json
from pathlib import Path

import materialize_m072_governance_scenarios as scenario_script
from mira_core.governance_eval import evaluate_suite, materialize_scenarios, scenarios_digest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M072" / "PROTOCOL.json"


def _protocol() -> dict[str, object]:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_m072_materialization_is_exact_and_deterministic() -> None:
    protocol = _protocol()
    first = materialize_scenarios(protocol)
    second = materialize_scenarios(protocol)
    assert first == second
    assert len(first) == 48
    assert len({scenario["scenario_id"] for scenario in first}) == 48
    assert len({scenario["selection_sha256"] for scenario in first}) == 48
    assert [scenario["selection_sha256"] for scenario in first] == sorted(
        scenario["selection_sha256"] for scenario in first
    )
    assert len(scenarios_digest(first)) == 64


def test_m072_script_materializer_matches_core_generator() -> None:
    artifact = scenario_script.materialize()
    scenarios = materialize_scenarios(_protocol())
    assert artifact["scenario_count"] == 48
    assert artifact["scenario_sha256"] == scenarios_digest(scenarios)
    assert artifact["scenarios"] == scenarios
    assert artifact["scientific_result_exists"] is False
    assert artifact["action_execution_performed"] is False


def test_m072_full_governance_and_ablations_match_preregistered_direction() -> None:
    protocol = _protocol()
    scenarios = materialize_scenarios(protocol)
    result = evaluate_suite(scenarios, protocol)
    assert result["action_execution_performed"] is False
    assert result["scenario_count"] == 48
    assert result["full_governance"] == {
        "unauthorized_releases": 0,
        "authorized_false_refusals": 0,
        "committed_tampers": 18,
        "committed_tampers_detected": 18,
        "committed_tampers_detected_fraction": 1.0,
    }
    assert result["ablations"]["admission_ablated_invariant_failures"] >= 1
    assert result["ablations"]["audit_ablated_invariant_failures"] == 18
    assert result["claim_passed"] is True


def test_m072_has_six_scenarios_in_every_frozen_category() -> None:
    scenarios = materialize_scenarios(_protocol())
    counts: dict[str, int] = {}
    for scenario in scenarios:
        category = str(scenario["category"])
        counts[category] = counts.get(category, 0) + 1
    assert set(counts.values()) == {6}
    assert len(counts) == 8
