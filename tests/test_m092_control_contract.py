from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m092_control_contract import (
    ControlContractError,
    arm_spec,
    control_contract,
    validate_control_contract,
)
from metamorphosis.m092_qualification_contract import ARMS, EVOLVABLE_ARM


PROTOCOL = Path("experiments/M092/PROTOCOL.json")


def test_control_contract_covers_protocol_arms_in_exact_order() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    contract = control_contract()
    assert contract["arms"] == protocol["arms"] == list(ARMS)
    assert list(contract["arm_specs"]) == list(ARMS)
    assert contract["only_scoring_arm"] == EVOLVABLE_ARM
    assert contract["result_dependent_configuration"] is False
    assert contract["candidate_or_hidden_value_embedded"] is False
    assert validate_control_contract(contract) == contract["contract_digest"]


def test_every_control_is_precommitted_to_zero_complete_qualifying_families() -> None:
    contract = control_contract()
    for arm in ARMS:
        spec = contract["arm_specs"][arm]
        if arm == EVOLVABLE_ARM:
            assert spec["complete_qualifying_families_maximum"] == 2
        else:
            assert spec["complete_qualifying_families_maximum"] == 0
            assert "qualification_scoring_as_evolvable" in spec["forbidden"]


def test_more_budget_requires_real_tenfold_execution_and_resets() -> None:
    spec = arm_spec("more_budget_same_substrate")
    assert spec["complete_search_repetitions"] == 10
    assert "ten_complete_independent_searches_executed" in spec["required"]
    assert "state_reset_between_every_repetition" in spec["required"]
    assert "reported_counter_multiplier_without_execution" in spec["forbidden"]
    assert "search_failure_used_as_impossibility_proof" in spec["forbidden"]
    assert "m092p_impossibility_proof_is_reach_authority" in spec["required"]


def test_registration_and_dependency_ablations_are_distinct() -> None:
    built = arm_spec("extension_built_but_not_registered")
    substrate_only = arm_spec("substrate_registered_downstream_not_registered")
    dependency = arm_spec("registered_but_dependency_ablated")
    use_ablated = arm_spec("qualification_use_ablated")

    assert "executing_substrate_is_frozen_checkpoint" in built["required"]
    assert "acquired_substrate_operation_registered" in substrate_only["required"]
    assert "downstream_primitive_registered" in substrate_only["forbidden"]
    assert "downstream_builder_runs_with_acquired_reference_forbidden" in dependency["required"]
    assert "downstream_primitive_references_acquired_operation" in dependency["forbidden"]
    assert "downstream_primitive_registered" in use_ablated["required"]
    assert "qualifying_program_calls_downstream_primitive" in use_ablated["forbidden"]


def test_proof_ablation_can_neither_receipt_nor_register() -> None:
    spec = arm_spec("proof_certificate_ablated")
    assert "generated_program_present" in spec["required"]
    assert "valid_exact_program_global_certificate_absent" in spec["required"]
    assert "validation_receipt_creation" in spec["forbidden"]
    assert "substrate_operation_registration" in spec["forbidden"]


def test_fresh_agent_cannot_receive_or_reconstruct_extension() -> None:
    spec = arm_spec("fresh_agent")
    assert "fresh_process_receives_only_frozen_checkpoint_language_and_substrate" in spec["required"]
    assert "extended_state_injected" in spec["forbidden"]
    assert "development_module_reconstruction_of_extension" in spec["forbidden"]


def test_contract_drift_and_unknown_arm_refuse() -> None:
    drifted = control_contract()
    drifted["only_scoring_arm"] = "fixed_substrate"
    with pytest.raises(ControlContractError):
        validate_control_contract(drifted)
    with pytest.raises(ControlContractError):
        arm_spec("not-an-arm")
