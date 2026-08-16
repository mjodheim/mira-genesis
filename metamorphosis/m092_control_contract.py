"""Pre-result causal contract for all eleven frozen M092 qualification arms.

The protocol names every arm before result reveal.  This module removes the remaining implementation
freedom by recording, in machine-checkable form, the facts that must be demonstrated or forbidden for
each arm.  It contains no candidate program, canonical result, reproduction result, extended-state
digest, or qualification value.

These are obligations, not outcomes.  A later control runner must produce evidence satisfying the
relevant obligations; it may not reinterpret a failed control after seeing qualification results.
"""
from __future__ import annotations

import hashlib
from typing import Mapping

from metamorphosis.m092_qualification_contract import ARMS, EVOLVABLE_ARM
from metamorphosis.m092_runtime import canonical_bytes

CONTROL_CONTRACT_SCHEMA = "m092-control-causal-contract/1"


class ControlContractError(ValueError):
    """A control-arm definition or later evidence contract drifted."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _obligations(*items: str) -> list[str]:
    if len(items) != len(set(items)):
        raise ControlContractError("duplicate control obligation")
    return list(items)


def control_contract() -> dict[str, object]:
    """Return the complete result-independent causal configuration for all frozen arms."""

    specs: dict[str, dict[str, object]] = {
        "evolvable_substrate": {
            "required": _obligations(
                "complete_causal_chain_enabled",
                "qualification_scoring_allowed",
                "acquired_substrate_operation_registered",
                "downstream_primitive_registered",
                "downstream_primitive_references_acquired_operation",
            ),
            "forbidden": _obligations(),
            "complete_qualifying_families_maximum": 2,
        },
        "fixed_substrate": {
            "required": _obligations(
                "exact_m092a_checkpoint_executes",
                "executing_substrate_is_frozen_checkpoint",
            ),
            "forbidden": _obligations(
                "substrate_operation_addition",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "substrate_acquisition_ablated": {
            "required": _obligations("candidate_generation_disabled", "certification_disabled"),
            "forbidden": _obligations(
                "validation_receipt_creation",
                "substrate_operation_registration",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "proof_certificate_ablated": {
            "required": _obligations(
                "generated_program_present",
                "valid_exact_program_global_certificate_absent",
            ),
            "forbidden": _obligations(
                "validation_receipt_creation",
                "substrate_operation_registration",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "extension_built_but_not_registered": {
            "required": _obligations(
                "same_accepted_program_as_evolvable",
                "same_validation_receipt_as_evolvable",
                "extended_state_built",
                "executing_substrate_is_frozen_checkpoint",
            ),
            "forbidden": _obligations(
                "extended_substrate_becomes_execution_authority",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "substrate_registered_downstream_not_registered": {
            "required": _obligations(
                "acquired_substrate_operation_registered",
                "acquired_substrate_operation_executable",
                "downstream_primitive_built",
            ),
            "forbidden": _obligations(
                "downstream_primitive_registered",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "registered_but_dependency_ablated": {
            "required": _obligations(
                "acquired_substrate_operation_registered",
                "downstream_builder_runs_with_acquired_reference_forbidden",
            ),
            "forbidden": _obligations(
                "downstream_primitive_references_acquired_operation",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "qualification_use_ablated": {
            "required": _obligations(
                "acquired_substrate_operation_registered",
                "downstream_primitive_registered",
                "qualifying_program_executes_without_downstream_primitive_call",
            ),
            "forbidden": _obligations(
                "qualifying_program_calls_downstream_primitive",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "more_budget_same_substrate": {
            "required": _obligations(
                "exact_m092a_checkpoint_executes",
                "ten_complete_independent_searches_executed",
                "state_reset_between_every_repetition",
                "m092p_impossibility_proof_is_reach_authority",
            ),
            "forbidden": _obligations(
                "reported_counter_multiplier_without_execution",
                "substrate_operation_addition",
                "search_failure_used_as_impossibility_proof",
                "qualification_scoring_as_evolvable",
            ),
            "complete_search_repetitions": 10,
            "complete_qualifying_families_maximum": 0,
        },
        "macro_only_substrate_extension": {
            "required": _obligations(
                "macro_operation_has_valid_certificate",
                "macro_operation_semantically_equivalent_to_registered_m091_semantics",
                "search_cost_measurement_recorded",
            ),
            "forbidden": _obligations(
                "macro_operation_adds_registered_semantic_reach",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
        "fresh_agent": {
            "required": _obligations(
                "fresh_process_created",
                "fresh_process_receives_only_frozen_checkpoint_language_and_substrate",
            ),
            "forbidden": _obligations(
                "extended_state_injected",
                "development_module_reconstruction_of_extension",
                "qualification_scoring_as_evolvable",
            ),
            "complete_qualifying_families_maximum": 0,
        },
    }
    if tuple(specs) != ARMS:
        raise ControlContractError("control-arm order differs from the frozen qualification contract")

    contract: dict[str, object] = {
        "schema": CONTROL_CONTRACT_SCHEMA,
        "arms": list(ARMS),
        "only_scoring_arm": EVOLVABLE_ARM,
        "control_complete_qualifying_families_maximum": 0,
        "arm_specs": specs,
        "result_dependent_configuration": False,
        "candidate_or_hidden_value_embedded": False,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def validate_control_contract(value: Mapping[str, object]) -> str:
    expected = control_contract()
    if dict(value) != expected:
        raise ControlContractError("control causal contract differs from the frozen pre-result contract")
    return str(expected["contract_digest"])


def arm_spec(arm: str) -> Mapping[str, object]:
    contract = control_contract()
    specs = contract["arm_specs"]
    if not isinstance(specs, Mapping) or arm not in specs:
        raise ControlContractError(f"unknown M092 arm {arm!r}")
    spec = specs[arm]
    if not isinstance(spec, Mapping):
        raise ControlContractError("control arm spec is malformed")
    return spec


__all__ = [
    "CONTROL_CONTRACT_SCHEMA", "ControlContractError", "arm_spec", "control_contract",
    "validate_control_contract",
]
