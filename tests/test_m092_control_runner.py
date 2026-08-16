from __future__ import annotations

from collections.abc import Mapping

import pytest

from metamorphosis.m092_control_contract import arm_spec
from metamorphosis.m092_control_runner import (
    CONTROL_ARM_EVIDENCE_SCHEMA,
    CONTROL_SUITE_EVIDENCE_SCHEMA,
    ControlRunnerError,
    evaluate_control_evidence,
    run_control_suite,
)
from metamorphosis.m092_qualification_contract import ARMS, EVOLVABLE_ARM


def _passing_evidence(arm: str) -> dict[str, object]:
    spec = arm_spec(arm)
    required = list(spec["required"])
    forbidden = list(spec["forbidden"])
    metrics: dict[str, int] = {"complete_qualifying_families": 0}
    if "complete_search_repetitions" in spec:
        metrics["complete_search_repetitions"] = int(spec["complete_search_repetitions"])
    return {
        "facts": {
            **{name: True for name in required},
            **{name: False for name in forbidden},
        },
        "metrics": metrics,
    }


def _passing_executor(arm: str, spec: Mapping[str, object]) -> Mapping[str, object]:
    assert spec == arm_spec(arm)
    return _passing_evidence(arm)


def test_runner_executes_all_frozen_arms_in_frozen_order() -> None:
    executors = {arm: _passing_executor for arm in reversed(ARMS)}
    result = run_control_suite(executors)

    assert result["schema"] == CONTROL_SUITE_EVIDENCE_SCHEMA
    assert result["arms"] == list(ARMS)
    assert result["only_scoring_arm"] == EVOLVABLE_ARM
    assert [item["arm"] for item in result["arm_evidence"]] == list(ARMS)
    assert all(item["schema"] == CONTROL_ARM_EVIDENCE_SCHEMA for item in result["arm_evidence"])
    assert result["all_arms_passed"] is True
    assert result["result_dependent_configuration"] is False
    assert result["candidate_or_hidden_value_embedded"] is False
    assert len(result["suite_digest"]) == 64


def test_runner_is_deterministic_for_identical_causal_evidence() -> None:
    first = run_control_suite({arm: _passing_executor for arm in ARMS})
    second = run_control_suite({arm: _passing_executor for arm in ARMS})
    assert first == second
    assert first["suite_digest"] == second["suite_digest"]


def test_well_formed_failed_required_fact_is_preserved_not_reinterpreted() -> None:
    arm = "fixed_substrate"
    evidence = _passing_evidence(arm)
    required = list(arm_spec(arm)["required"])
    evidence["facts"][required[0]] = False

    result = evaluate_control_evidence(arm, evidence)
    assert result["required_obligations_satisfied"] is False
    assert result["passed"] is False
    assert result["facts"][required[0]] is False
    assert len(result["evidence_digest"]) == 64


def test_well_formed_forbidden_fact_violation_is_preserved() -> None:
    arm = "proof_certificate_ablated"
    evidence = _passing_evidence(arm)
    forbidden = list(arm_spec(arm)["forbidden"])
    evidence["facts"][forbidden[0]] = True

    result = evaluate_control_evidence(arm, evidence)
    assert result["forbidden_obligations_absent"] is False
    assert result["passed"] is False


def test_quantitative_family_bound_is_enforced_without_hiding_the_observation() -> None:
    evidence = _passing_evidence(EVOLVABLE_ARM)
    maximum = int(arm_spec(EVOLVABLE_ARM)["complete_qualifying_families_maximum"])
    evidence["metrics"]["complete_qualifying_families"] = maximum + 1

    result = evaluate_control_evidence(EVOLVABLE_ARM, evidence)
    assert result["metrics"]["complete_qualifying_families"] == maximum + 1
    assert result["complete_qualifying_families_within_bound"] is False
    assert result["passed"] is False


def test_more_budget_requires_exact_precommitted_repetition_count() -> None:
    arm = "more_budget_same_substrate"
    evidence = _passing_evidence(arm)
    expected = int(arm_spec(arm)["complete_search_repetitions"])
    evidence["metrics"]["complete_search_repetitions"] = expected - 1

    result = evaluate_control_evidence(arm, evidence)
    assert result["complete_search_repetitions_exact"] is False
    assert result["passed"] is False


def test_suite_does_not_short_circuit_after_a_failed_arm() -> None:
    visited: list[str] = []

    def executor(arm: str, spec: Mapping[str, object]) -> Mapping[str, object]:
        visited.append(arm)
        evidence = _passing_evidence(arm)
        if arm == "fixed_substrate":
            evidence["facts"][list(spec["required"])[0]] = False
        return evidence

    result = run_control_suite({arm: executor for arm in ARMS})
    assert visited == list(ARMS)
    assert result["all_arms_passed"] is False
    assert len(result["arm_evidence"]) == len(ARMS)


def test_missing_or_unexpected_executor_is_refused_before_execution() -> None:
    missing = {arm: _passing_executor for arm in ARMS if arm != ARMS[-1]}
    with pytest.raises(ControlRunnerError, match="executor set differs"):
        run_control_suite(missing)

    unexpected = {arm: _passing_executor for arm in ARMS}
    unexpected["post_result_arm"] = _passing_executor
    with pytest.raises(ControlRunnerError, match="executor set differs"):
        run_control_suite(unexpected)


def test_evidence_shape_cannot_carry_candidate_or_hidden_payloads() -> None:
    evidence = _passing_evidence("fixed_substrate")
    evidence["hidden_values"] = [1, 2, 3]
    with pytest.raises(ControlRunnerError, match="exactly facts and metrics"):
        evaluate_control_evidence("fixed_substrate", evidence)


def test_fact_and_metric_contract_drift_is_refused() -> None:
    arm = "fresh_agent"
    missing_fact = _passing_evidence(arm)
    del missing_fact["facts"][next(iter(missing_fact["facts"]))]
    with pytest.raises(ControlRunnerError, match="facts differ"):
        evaluate_control_evidence(arm, missing_fact)

    extra_metric = _passing_evidence(arm)
    extra_metric["metrics"]["post_result_score"] = 1
    with pytest.raises(ControlRunnerError, match="metrics differ"):
        evaluate_control_evidence(arm, extra_metric)


def test_boolean_and_counter_types_are_strict() -> None:
    arm = "fixed_substrate"
    bad_fact = _passing_evidence(arm)
    bad_fact["facts"][next(iter(bad_fact["facts"]))] = 1
    with pytest.raises(ControlRunnerError, match="must be boolean"):
        evaluate_control_evidence(arm, bad_fact)

    bad_counter = _passing_evidence(arm)
    bad_counter["metrics"]["complete_qualifying_families"] = True
    with pytest.raises(ControlRunnerError, match="non-negative integer"):
        evaluate_control_evidence(arm, bad_counter)
