#!/usr/bin/env python3
"""Verify the frozen M072 protocol, scenario commitment and preserved first result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mira_core.governance_eval import evaluate_suite, materialize_scenarios, scenarios_digest


ROOT = Path(__file__).resolve().parents[1]
M072 = ROOT / "experiments" / "M072"
PROTOCOL = M072 / "PROTOCOL.json"
COMMITMENT = M072 / "SCENARIO_COMMITMENT.json"
RESULT = M072 / "RESULT.json"
EXPECTED_RESULT_SHA256 = "ab555d2f0a7088193569053219f7edda4668a3f7b8849f03b6781eb3fe09005e"


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_result() -> dict[str, object]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    commitment = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    if protocol.get("schema") != "m072-causal-governance-protocol-v1":
        raise ValueError("unexpected M072 protocol schema")
    if protocol.get("scientific_result_exists") is not False:
        raise ValueError("M072 preregistration was rewritten after observation")
    if protocol.get("scenario_generation", {}).get("scenario_content_materialized") is not False:
        raise ValueError("M072 preregistration contains post-freeze scenarios")

    scenarios = materialize_scenarios(protocol)
    observed_scenario_digest = scenarios_digest(scenarios)
    ordered_pairs = [
        [scenario["selection_sha256"], scenario["scenario_id"]] for scenario in scenarios
    ]
    if commitment.get("schema") != "m072-governance-scenario-commitment-v1":
        raise ValueError("unexpected M072 scenario commitment schema")
    if commitment.get("protocol_commit") != "a844b10dc558a16f2609d204f886d63fd193a9d3":
        raise ValueError("M072 scenario commitment does not bind the preregistered protocol")
    if commitment.get("generator_commit") != "87a5a9bc0af47231fec45cda4c0e39250bb7491a":
        raise ValueError("M072 scenario commitment does not bind the evaluator implementation")
    if commitment.get("scenario_count") != 48 or len(scenarios) != 48:
        raise ValueError("M072 scenario count drifted")
    if commitment.get("scenario_sha256") != observed_scenario_digest:
        raise ValueError("M072 scenario digest differs from the frozen generator")
    if commitment.get("ordered_pairs") != ordered_pairs:
        raise ValueError("M072 scenario ordering differs from the commitment")
    if commitment.get("scientific_result_exists") is not False:
        raise ValueError("M072 scenario commitment was created after a result")
    if commitment.get("action_execution_performed") is not False:
        raise ValueError("M072 scenario commitment claims action execution")

    recomputed = evaluate_suite(scenarios, protocol)
    if result.get("schema") != "m072-causal-governance-result-v1":
        raise ValueError("unexpected M072 result schema")
    if result.get("status") != "positive_qualified_development_result":
        raise ValueError("M072 result status drifted")
    if result.get("claim_passed") is not True or recomputed.get("claim_passed") is not True:
        raise ValueError("M072 frozen threshold was not satisfied")
    if result.get("scenario_count") != recomputed.get("scenario_count"):
        raise ValueError("M072 result scenario count differs from recomputation")
    if result.get("scenario_sha256") != recomputed.get("scenario_sha256"):
        raise ValueError("M072 result scenario digest differs from recomputation")
    if result.get("full_governance") != recomputed.get("full_governance"):
        raise ValueError("M072 full-governance metrics differ from recomputation")
    if result.get("ablations") != recomputed.get("ablations"):
        raise ValueError("M072 ablation metrics differ from recomputation")
    if result.get("protocol_commit") != commitment.get("protocol_commit"):
        raise ValueError("M072 result does not bind the frozen protocol")
    if result.get("scenario_commitment_commit") != "59b7bdfeac75a7ab3ffa1cd87e0c6cf5050b34e8":
        raise ValueError("M072 result does not bind the pre-result scenario commitment")
    if result.get("external_model_called_for_result") is not False:
        raise ValueError("M072 unexpectedly depends on an external model result")
    if result.get("external_task_selected") is not False:
        raise ValueError("M072 unexpectedly selected an external task")

    safety = result.get("safety")
    if not isinstance(safety, dict) or any(value is not False for value in safety.values()):
        raise ValueError("M072 safety record contains an execution or authority grant")
    attribution = result.get("attribution")
    if not isinstance(attribution, dict):
        raise ValueError("M072 attribution record is malformed")
    for field in (
        "agi_evidence", "generality_gate_advanced", "genesis_gate_2_evidence",
        "genesis_gate_3_evidence", "model_competence_evidence", "safe_deployment_evidence",
    ):
        if attribution.get(field) is not False:
            raise ValueError(f"M072 improperly widens attribution field {field}")

    result_digest = _canonical_digest(result)
    if result_digest != EXPECTED_RESULT_SHA256:
        raise ValueError("M072 preserved result bytes have semantic drift")
    return {
        "status": result["status"],
        "claim_passed": True,
        "scenario_count": 48,
        "scenario_sha256": observed_scenario_digest,
        "result_sha256": result_digest,
        "action_execution_performed": False,
    }


def main() -> int:
    print(json.dumps(verify_result(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
