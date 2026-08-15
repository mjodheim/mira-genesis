from __future__ import annotations

import pytest

from metamorphosis.m092_qualification_contract import (
    ARMS,
    EVOLVABLE_ARM,
    FAMILY_ALTERNATING,
    FAMILY_COMPLEMENTARY,
    FAMILIES,
    MORE_BUDGET_REPETITIONS,
    QualificationContractError,
    execution_contract,
    expected_slot0,
    family_program,
    validate_contract,
)


PARITY_PRIMITIVE = "M092_USE_" + "a" * 64


def test_family_programs_reuse_one_dynamic_parity_primitive() -> None:
    alternating = family_program(FAMILY_ALTERNATING, PARITY_PRIMITIVE)
    complementary = family_program(FAMILY_COMPLEMENTARY, PARITY_PRIMITIVE)

    assert alternating == ((PARITY_PRIMITIVE, (0, 0)),)
    assert complementary == (
        (PARITY_PRIMITIVE, (0, 0)),
        ("APPLY_UNARY", (0, "neg")),
        ("APPLY_UNARY", (0, "inc")),
    )
    assert sum(step[0] == PARITY_PRIMITIVE for step in alternating) == 1
    assert sum(step[0] == PARITY_PRIMITIVE for step in complementary) == 1
    assert all(step[0] != "M092_USE_SECOND_TARGET" for step in complementary)


def test_empirical_family_scoring_is_exact_and_complementary() -> None:
    for value in range(32):
        parity = expected_slot0(FAMILY_ALTERNATING, value)
        complement = expected_slot0(FAMILY_COMPLEMENTARY, value)
        assert parity == value % 2
        assert complement == 1 - parity
        assert parity + complement == 1


def test_contract_contains_every_precommitted_arm_once() -> None:
    assert len(ARMS) == 11
    assert len(set(ARMS)) == len(ARMS)
    assert ARMS == (
        "evolvable_substrate",
        "fixed_substrate",
        "substrate_acquisition_ablated",
        "proof_certificate_ablated",
        "extension_built_but_not_registered",
        "substrate_registered_downstream_not_registered",
        "registered_but_dependency_ablated",
        "qualification_use_ablated",
        "more_budget_same_substrate",
        "macro_only_substrate_extension",
        "fresh_agent",
    )
    assert EVOLVABLE_ARM == ARMS[0]
    assert MORE_BUDGET_REPETITIONS == 10


def test_contract_is_result_independent_and_digest_bound() -> None:
    first = execution_contract()
    second = execution_contract()
    assert first == second
    assert first["families"] == list(FAMILIES)
    assert first["candidate_result_or_hidden_values_embedded"] is False
    assert first["new_operation_registration_during_qualification_forbidden"] is True
    assert first["same_acquired_operation_reused_across_families"] is True
    assert first["second_target_specific_operation_forbidden"] is True
    assert first["only_arm_allowed_to_score_a_qualifying_world"] == EVOLVABLE_ARM
    assert first["evolvable_required_complete_families"] == 2
    assert first["each_control_maximum_complete_families"] == 0
    assert first["model_calls_during_qualification"] == 0
    assert first["network_calls_during_qualification"] == 0
    assert isinstance(first["contract_digest"], str) and len(first["contract_digest"]) == 64
    assert validate_contract(first) == first["contract_digest"]


def test_contract_refuses_drift() -> None:
    drifted = execution_contract()
    drifted["more_budget_same_substrate_complete_search_repetitions"] = 9
    with pytest.raises(QualificationContractError):
        validate_contract(drifted)


def test_unknown_family_and_bad_values_refuse() -> None:
    with pytest.raises(QualificationContractError):
        family_program("third-family", PARITY_PRIMITIVE)
    with pytest.raises(QualificationContractError):
        expected_slot0("third-family", 3)
    with pytest.raises(QualificationContractError):
        expected_slot0(FAMILY_ALTERNATING, -1)
    with pytest.raises(QualificationContractError):
        expected_slot0(FAMILY_ALTERNATING, True)


def test_inherited_identifier_cannot_impersonate_acquired_downstream_primitive() -> None:
    for inherited in ("APPLY_UNARY", "SET_CONST", "COPY_INPUT", ""):
        with pytest.raises(QualificationContractError):
            family_program(FAMILY_ALTERNATING, inherited)
