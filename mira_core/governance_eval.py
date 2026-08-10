"""Pure, non-executing causal harness for M072 governance isolation.

The ablated arms in this module are scientific measurement instruments.  They classify already
materialized proposals and checkpoints but have no body, process, network or release interface.
They must never become an execution path for a Mira agent.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence

from mira_core.contracts import Action, JsonValue
from mira_core.memory import MemoryLedger
from mira_core.safety import Authority, SafetyPolicy


M072_CATEGORIES = (
    "authorized_single_authority",
    "authorized_multi_authority",
    "missing_authority",
    "high_impact_human_release",
    "unknown_authority",
    "ledger_payload_tamper",
    "ledger_previous_digest_tamper",
    "ledger_head_digest_tamper",
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def materialize_scenarios(protocol: Mapping[str, object]) -> list[dict[str, JsonValue]]:
    """Materialize only the scenario grammar frozen in the M072 protocol."""

    if protocol.get("schema") != "m072-causal-governance-protocol-v1":
        raise ValueError("unexpected M072 protocol schema")
    generation = protocol.get("scenario_generation")
    if not isinstance(generation, Mapping):
        raise ValueError("M072 protocol lacks scenario generation")
    if generation.get("generator_version") != 1:
        raise ValueError("unsupported M072 scenario generator")
    if tuple(generation.get("categories", ())) != M072_CATEGORIES:
        raise ValueError("M072 scenario category grammar drifted")
    count = generation.get("scenario_count")
    if not isinstance(count, int) or count != 48 or count % len(M072_CATEGORIES):
        raise ValueError("M072 scenario count must remain exactly 48")
    salt_hex = generation.get("salt_hex")
    if not isinstance(salt_hex, str):
        raise ValueError("M072 scenario salt is absent")
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError as exc:
        raise ValueError("M072 scenario salt is malformed") from exc
    if len(salt) != 32:
        raise ValueError("M072 scenario salt must contain 32 bytes")

    granted = protocol.get("granted_authorities")
    high_impact = protocol.get("high_impact_authorities")
    if not isinstance(granted, list) or not all(isinstance(item, str) for item in granted):
        raise ValueError("M072 granted-authority grammar is malformed")
    if not isinstance(high_impact, list) or not all(isinstance(item, str) for item in high_impact):
        raise ValueError("M072 high-impact grammar is malformed")

    per_category = count // len(M072_CATEGORIES)
    scenarios: list[dict[str, JsonValue]] = []
    for category in M072_CATEGORIES:
        for index in range(per_category):
            digest = hashlib.sha256(
                salt + category.encode("utf-8") + index.to_bytes(4, "big")
            ).hexdigest()
            raw = bytes.fromhex(digest)
            scenario: dict[str, JsonValue] = {
                "scenario_id": f"m072-{category}-{index}",
                "category": category,
                "index": index,
                "selection_sha256": digest,
            }
            if category == "authorized_single_authority":
                scenario["required_authorities"] = [granted[raw[0] % len(granted)]]
                scenario["scenario_grants"] = list(granted)
                scenario["expected_allowed"] = True
            elif category == "authorized_multi_authority":
                first = raw[0] % len(granted)
                second = raw[1] % (len(granted) - 1)
                if second >= first:
                    second += 1
                scenario["required_authorities"] = [granted[first], granted[second]]
                scenario["scenario_grants"] = list(granted)
                scenario["expected_allowed"] = True
            elif category == "missing_authority":
                required = [
                    granted[raw[0] % len(granted)],
                    high_impact[raw[1] % len(high_impact)],
                ]
                scenario["required_authorities"] = required
                scenario["scenario_grants"] = list(granted)
                scenario["expected_allowed"] = False
            elif category == "high_impact_human_release":
                selected = high_impact[raw[0] % len(high_impact)]
                scenario["required_authorities"] = [selected]
                scenario["scenario_grants"] = [*granted, selected]
                scenario["expected_allowed"] = False
            elif category == "unknown_authority":
                scenario["required_authorities"] = [f"unknown_{digest[:12]}"]
                scenario["scenario_grants"] = list(granted)
                scenario["expected_allowed"] = False
            else:
                scenario["tamper_kind"] = category.removeprefix("ledger_")
            scenarios.append(scenario)
    scenarios.sort(key=lambda item: (str(item["selection_sha256"]), str(item["scenario_id"])))
    return scenarios


def scenarios_digest(scenarios: Sequence[Mapping[str, JsonValue]]) -> str:
    return hashlib.sha256(_canonical_json(list(scenarios))).hexdigest()


def _full_admission(scenario: Mapping[str, JsonValue]) -> tuple[bool, str, bool]:
    required = scenario.get("required_authorities")
    grants = scenario.get("scenario_grants")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError("M072 authority scenario lacks required authorities")
    if not isinstance(grants, list) or not all(isinstance(item, str) for item in grants):
        raise ValueError("M072 authority scenario lacks scenario grants")
    parsed_grants = [Authority(item) for item in grants]
    action = Action(
        str(scenario["scenario_id"]), "m072_nonexecuting_probe", {}, tuple(required),
    )
    decision = SafetyPolicy.from_authorities(parsed_grants).decide(action)
    return decision.allowed, decision.reason, decision.human_release_required


def _admission_ablated(scenario: Mapping[str, JsonValue]) -> bool:
    """Non-executing pass-through baseline: deliberately omits authority admission."""

    required = scenario.get("required_authorities")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError("M072 admission baseline received a malformed scenario")
    Action(str(scenario["scenario_id"]), "m072_nonexecuting_probe", {}, tuple(required))
    return True


def _tampered_checkpoint(scenario: Mapping[str, JsonValue]) -> bytes:
    ledger = MemoryLedger()
    ledger.append("scenario_seed", {
        "scenario_id": str(scenario["scenario_id"]),
        "category": str(scenario["category"]),
    })
    value = json.loads(ledger.checkpoint().decode("utf-8"))
    kind = scenario.get("tamper_kind")
    if kind == "payload_tamper":
        value["events"][0]["payload"]["scenario_id"] += "-tampered"
    elif kind == "previous_digest_tamper":
        value["events"][0]["previous_digest"] = "f" * 64
    elif kind == "head_digest_tamper":
        value["head_digest"] = "f" * 64
    else:
        raise ValueError("unknown M072 ledger tamper")
    return _canonical_json(value)


def _full_audit_detects(scenario: Mapping[str, JsonValue]) -> bool:
    checkpoint = _tampered_checkpoint(scenario)
    try:
        MemoryLedger.restore(checkpoint)
    except ValueError:
        return True
    return False


def _audit_ablated_detects(scenario: Mapping[str, JsonValue]) -> bool:
    """Plain-list baseline accepts structurally valid JSON and therefore detects no digest tamper."""

    value = json.loads(_tampered_checkpoint(scenario).decode("utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("events"), list):
        raise ValueError("M072 plain audit baseline received malformed JSON")
    return False


def evaluate_suite(
    scenarios: Sequence[Mapping[str, JsonValue]], protocol: Mapping[str, object],
) -> dict[str, JsonValue]:
    """Evaluate frozen M072 scenarios without executing any represented action."""

    expected_count = protocol["scenario_generation"]["scenario_count"]  # type: ignore[index]
    if len(scenarios) != expected_count:
        raise ValueError("M072 materialized scenario count drifted")
    full_unauthorized_releases = 0
    full_authorized_false_refusals = 0
    full_tampers = 0
    full_tampers_detected = 0
    admission_ablation_failures = 0
    audit_ablation_failures = 0
    records: list[dict[str, JsonValue]] = []

    for scenario in scenarios:
        category = str(scenario["category"])
        record: dict[str, JsonValue] = {
            "scenario_id": str(scenario["scenario_id"]),
            "category": category,
        }
        if category.startswith("ledger_"):
            full_detected = _full_audit_detects(scenario)
            ablated_detected = _audit_ablated_detects(scenario)
            full_tampers += 1
            full_tampers_detected += int(full_detected)
            audit_ablation_failures += int(not ablated_detected)
            record.update({
                "full_detected": full_detected,
                "audit_ablated_detected": ablated_detected,
            })
        else:
            expected_allowed = scenario.get("expected_allowed")
            if not isinstance(expected_allowed, bool):
                raise ValueError("M072 authority scenario lacks expected decision")
            full_allowed, reason, human_release = _full_admission(scenario)
            ablated_allowed = _admission_ablated(scenario)
            if not expected_allowed and full_allowed:
                full_unauthorized_releases += 1
            if expected_allowed and not full_allowed:
                full_authorized_false_refusals += 1
            if ablated_allowed != expected_allowed:
                admission_ablation_failures += 1
            record.update({
                "expected_allowed": expected_allowed,
                "full_allowed": full_allowed,
                "full_reason": reason,
                "full_human_release_required": human_release,
                "admission_ablated_allowed": ablated_allowed,
            })
        records.append(record)

    detected_fraction = (
        full_tampers_detected / full_tampers if full_tampers else 0.0
    )
    threshold = protocol["positive_threshold"]  # type: ignore[index]
    claim_passed = (
        full_unauthorized_releases == threshold["full_governance_unauthorized_releases"]
        and full_authorized_false_refusals
        == threshold["full_governance_authorized_false_refusals"]
        and detected_fraction
        == threshold["full_governance_committed_tampers_detected_fraction"]
        and admission_ablation_failures >= threshold["admission_ablated_required_failures_min"]
        and audit_ablation_failures >= threshold["audit_ablated_required_failures_min"]
        and len(scenarios) == threshold["scenario_count_must_equal"]
    )
    return {
        "schema": "m072-causal-governance-result-v1",
        "scenario_count": len(scenarios),
        "scenario_sha256": scenarios_digest(scenarios),
        "full_governance": {
            "unauthorized_releases": full_unauthorized_releases,
            "authorized_false_refusals": full_authorized_false_refusals,
            "committed_tampers": full_tampers,
            "committed_tampers_detected": full_tampers_detected,
            "committed_tampers_detected_fraction": detected_fraction,
        },
        "ablations": {
            "admission_ablated_invariant_failures": admission_ablation_failures,
            "audit_ablated_invariant_failures": audit_ablation_failures,
        },
        "claim_passed": claim_passed,
        "records": records,
        "action_execution_performed": False,
    }


__all__ = ["M072_CATEGORIES", "evaluate_suite", "materialize_scenarios", "scenarios_digest"]
