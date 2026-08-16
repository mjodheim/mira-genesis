"""Result-neutral runner for the frozen M092 causal control contract.

The contract was frozen before the canonical result.  This module only checks evidence supplied by
control executors against that contract: every required causal fact must be observed, every forbidden
fact must be absent, and the frozen quantitative bounds must be respected.  It does not import the
canonical search, independent reproduction, qualification-material generator, or hidden oracle.

A well-formed failed control is returned as ``passed=False`` rather than being reinterpreted or
discarded.  Structural drift is refused with ``ControlRunnerError``.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from metamorphosis.m092_control_contract import (
    ControlContractError,
    arm_spec,
    control_contract,
    validate_control_contract,
)
from metamorphosis.m092_qualification_contract import ARMS, EVOLVABLE_ARM
from metamorphosis.m092_runtime import canonical_bytes

CONTROL_ARM_EVIDENCE_SCHEMA = "m092-control-arm-evidence/1"
CONTROL_SUITE_EVIDENCE_SCHEMA = "m092-control-suite-evidence/1"


class ControlRunnerError(ValueError):
    """Control evidence is malformed or the frozen execution boundary drifted."""


ControlExecutor = Callable[[str, Mapping[str, object]], Mapping[str, object]]


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _as_string_list(value: object, *, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ControlRunnerError(f"{field} must be a list of strings")
    return list(value)


def _as_non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ControlRunnerError(f"{field} must be a non-negative integer")
    return value


def evaluate_control_evidence(arm: str, evidence: Mapping[str, object]) -> dict[str, object]:
    """Bind one executor's causal observations to the precommitted arm specification.

    ``evidence`` intentionally has only two fields:
    - ``facts``: one boolean for every required/forbidden causal obligation;
    - ``metrics``: the frozen quantitative counters for this arm.

    This narrow shape prevents arbitrary candidate programs, hidden qualification values, or
    post-result configuration from being smuggled into the control receipt.
    """

    try:
        spec = arm_spec(arm)
    except ControlContractError as error:
        raise ControlRunnerError(f"unknown M092 control arm {arm!r}") from error

    if set(evidence) != {"facts", "metrics"}:
        raise ControlRunnerError("control evidence must contain exactly facts and metrics")

    facts = evidence["facts"]
    metrics = evidence["metrics"]
    if not isinstance(facts, Mapping):
        raise ControlRunnerError("control facts must be a mapping")
    if not isinstance(metrics, Mapping):
        raise ControlRunnerError("control metrics must be a mapping")

    required = _as_string_list(spec.get("required"), field="required obligations")
    forbidden = _as_string_list(spec.get("forbidden"), field="forbidden obligations")
    obligation_order = required + forbidden
    if len(obligation_order) != len(set(obligation_order)):
        raise ControlRunnerError("a causal obligation appears in both required and forbidden sets")
    if set(facts) != set(obligation_order):
        raise ControlRunnerError("control facts differ from the frozen causal obligations")
    if any(not isinstance(facts[name], bool) for name in obligation_order):
        raise ControlRunnerError("every causal control fact must be boolean")

    expected_metric_names = {"complete_qualifying_families"}
    if "complete_search_repetitions" in spec:
        expected_metric_names.add("complete_search_repetitions")
    if set(metrics) != expected_metric_names:
        raise ControlRunnerError("control metrics differ from the frozen quantitative contract")

    complete_families = _as_non_negative_int(
        metrics["complete_qualifying_families"],
        field="complete_qualifying_families",
    )
    maximum = _as_non_negative_int(
        spec.get("complete_qualifying_families_maximum"),
        field="complete_qualifying_families_maximum",
    )

    required_satisfied = all(facts[name] is True for name in required)
    forbidden_absent = all(facts[name] is False for name in forbidden)
    family_bound_satisfied = complete_families <= maximum

    normalized_metrics: dict[str, int] = {
        "complete_qualifying_families": complete_families,
    }
    repetition_bound_satisfied = True
    if "complete_search_repetitions" in spec:
        observed_repetitions = _as_non_negative_int(
            metrics["complete_search_repetitions"],
            field="complete_search_repetitions",
        )
        expected_repetitions = _as_non_negative_int(
            spec["complete_search_repetitions"],
            field="frozen complete_search_repetitions",
        )
        normalized_metrics["complete_search_repetitions"] = observed_repetitions
        repetition_bound_satisfied = observed_repetitions == expected_repetitions

    normalized_facts = {name: bool(facts[name]) for name in obligation_order}
    result: dict[str, object] = {
        "schema": CONTROL_ARM_EVIDENCE_SCHEMA,
        "arm": arm,
        "required_obligations": required,
        "forbidden_obligations": forbidden,
        "facts": normalized_facts,
        "metrics": normalized_metrics,
        "required_obligations_satisfied": required_satisfied,
        "forbidden_obligations_absent": forbidden_absent,
        "complete_qualifying_families_within_bound": family_bound_satisfied,
        "complete_search_repetitions_exact": repetition_bound_satisfied,
        "passed": (
            required_satisfied
            and forbidden_absent
            and family_bound_satisfied
            and repetition_bound_satisfied
        ),
        "result_dependent_configuration": False,
        "candidate_or_hidden_value_embedded": False,
    }
    result["evidence_digest"] = _digest(result)
    return result


def run_control_suite(executors: Mapping[str, ControlExecutor]) -> dict[str, object]:
    """Execute every frozen M092 arm once, in frozen order, and bind its causal evidence.

    Executor configuration must cover exactly the eleven precommitted arms.  The suite deliberately
    does not short-circuit on a failed arm so the complete negative or positive scientific record is
    retained.
    """

    if set(executors) != set(ARMS):
        missing = [arm for arm in ARMS if arm not in executors]
        unexpected = sorted(set(executors) - set(ARMS))
        raise ControlRunnerError(
            f"control executor set differs from frozen arms: missing={missing!r}, unexpected={unexpected!r}"
        )

    contract = control_contract()
    try:
        contract_digest = validate_control_contract(contract)
    except ControlContractError as error:
        raise ControlRunnerError("frozen control contract validation failed") from error

    arm_evidence: list[dict[str, object]] = []
    for arm in ARMS:
        executor = executors[arm]
        if not callable(executor):
            raise ControlRunnerError(f"control executor for {arm!r} is not callable")
        raw = executor(arm, arm_spec(arm))
        if not isinstance(raw, Mapping):
            raise ControlRunnerError(f"control executor for {arm!r} did not return a mapping")
        arm_evidence.append(evaluate_control_evidence(arm, raw))

    result: dict[str, object] = {
        "schema": CONTROL_SUITE_EVIDENCE_SCHEMA,
        "contract_digest": contract_digest,
        "arms": list(ARMS),
        "only_scoring_arm": EVOLVABLE_ARM,
        "arm_evidence": arm_evidence,
        "all_arms_passed": all(bool(item["passed"]) for item in arm_evidence),
        "result_dependent_configuration": False,
        "candidate_or_hidden_value_embedded": False,
    }
    result["suite_digest"] = _digest(result)
    return result


__all__ = [
    "CONTROL_ARM_EVIDENCE_SCHEMA",
    "CONTROL_SUITE_EVIDENCE_SCHEMA",
    "ControlExecutor",
    "ControlRunnerError",
    "evaluate_control_evidence",
    "run_control_suite",
]
