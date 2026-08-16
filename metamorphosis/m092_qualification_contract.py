"""Pre-result execution contract for M092-I qualification.

This module contains no selected program, certificate, canonical-search result, reproduction result,
or hidden qualification value.  It freezes only the protocol-level execution shape that must already
be fixed before any M092 result is known.

The dynamic downstream primitive identifier is supplied later, after independent reproduction opens
the qualification gate.  Both qualification families must reuse that same primitive.  Family B then
composes only the inherited unary operations ``neg`` and ``inc``; a second acquired target operation
has no place in this contract.
"""
from __future__ import annotations

import hashlib
from typing import Mapping

from metamorphosis.m092_runtime import canonical_bytes

QUALIFICATION_CONTRACT_SCHEMA = "m092-qualification-execution-contract/1"
FAMILY_ALTERNATING = "alternating_allocation"
FAMILY_COMPLEMENTARY = "complementary_protocol_phase"
FAMILIES = (FAMILY_ALTERNATING, FAMILY_COMPLEMENTARY)

EVOLVABLE_ARM = "evolvable_substrate"
ARMS = (
    EVOLVABLE_ARM,
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
MORE_BUDGET_REPETITIONS = 10
HIDDEN_INSTANCES_PER_FAMILY = 6
REQUIRED_COMPLETE_FAMILIES_FOR_EVOLVABLE = 2
MAX_COMPLETE_FAMILIES_FOR_EACH_CONTROL = 0

# The protocol's counter-mode draw is consumed in the order in which its digest stream accepts
# candidates.  This records the pre-result interpretation explicitly; it does not materialize draws.
DRAW_ORDER_INTERPRETATION = "counter-mode digest-stream acceptance order; no post-hoc reordering"


class QualificationContractError(ValueError):
    """The frozen post-reproduction qualification execution shape was violated."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def family_program(
    family: str,
    downstream_primitive_id: str,
) -> tuple[tuple[str, tuple[object, ...]], ...]:
    """Return the exact language-level program for one qualification family.

    The acquired primitive appears exactly once in either family.  The complementary family obtains
    ``1 - parity`` through inherited language composition: parity -> neg -> inc.
    """

    if family not in FAMILIES:
        raise QualificationContractError(f"unknown qualification family {family!r}")
    if not downstream_primitive_id or downstream_primitive_id in {"APPLY_UNARY", "SET_CONST", "COPY_INPUT"}:
        raise QualificationContractError("downstream primitive identifier is absent or inherited")

    parity = (downstream_primitive_id, (0, 0))
    if family == FAMILY_ALTERNATING:
        return (parity,)
    return (
        parity,
        ("APPLY_UNARY", (0, "neg")),
        ("APPLY_UNARY", (0, "inc")),
    )


def expected_slot0(family: str, value: int) -> int:
    """Frozen empirical scoring rule, separate from the global theorem/certificate."""

    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise QualificationContractError("qualification values must be non-negative integers")
    if family == FAMILY_ALTERNATING:
        return value % 2
    if family == FAMILY_COMPLEMENTARY:
        return 1 - (value % 2)
    raise QualificationContractError(f"unknown qualification family {family!r}")


def execution_contract() -> dict[str, object]:
    """Return the immutable result-independent contract to bind into later qualification artifacts."""

    contract: dict[str, object] = {
        "schema": QUALIFICATION_CONTRACT_SCHEMA,
        "families": list(FAMILIES),
        "family_programs": {
            FAMILY_ALTERNATING: [
                ["$DOWNSTREAM_PARITY_PRIMITIVE", [0, 0]],
            ],
            FAMILY_COMPLEMENTARY: [
                ["$DOWNSTREAM_PARITY_PRIMITIVE", [0, 0]],
                ["APPLY_UNARY", [0, "neg"]],
                ["APPLY_UNARY", [0, "inc"]],
            ],
        },
        "same_acquired_operation_reused_across_families": True,
        "second_target_specific_operation_forbidden": True,
        "new_operation_registration_during_qualification_forbidden": True,
        "hidden_instances_per_family": HIDDEN_INSTANCES_PER_FAMILY,
        "arms": list(ARMS),
        "only_arm_allowed_to_score_a_qualifying_world": EVOLVABLE_ARM,
        "more_budget_same_substrate_complete_search_repetitions": MORE_BUDGET_REPETITIONS,
        "more_budget_state_reset_between_repetitions": True,
        "evolvable_required_complete_families": REQUIRED_COMPLETE_FAMILIES_FOR_EVOLVABLE,
        "each_control_maximum_complete_families": MAX_COMPLETE_FAMILIES_FOR_EACH_CONTROL,
        "theorem_certificate_empiricism_kept_separate": True,
        "model_calls_during_qualification": 0,
        "network_calls_during_qualification": 0,
        "draw_order_interpretation": DRAW_ORDER_INTERPRETATION,
        "candidate_result_or_hidden_values_embedded": False,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def validate_contract(value: Mapping[str, object]) -> str:
    """Fail closed unless a stored contract is byte-semantically identical to the frozen one."""

    expected = execution_contract()
    if dict(value) != expected:
        raise QualificationContractError("qualification execution contract differs from the frozen pre-result contract")
    return str(expected["contract_digest"])


__all__ = [
    "ARMS", "DRAW_ORDER_INTERPRETATION", "EVOLVABLE_ARM", "FAMILIES",
    "FAMILY_ALTERNATING", "FAMILY_COMPLEMENTARY", "HIDDEN_INSTANCES_PER_FAMILY",
    "MAX_COMPLETE_FAMILIES_FOR_EACH_CONTROL", "MORE_BUDGET_REPETITIONS",
    "QUALIFICATION_CONTRACT_SCHEMA", "QualificationContractError",
    "REQUIRED_COMPLETE_FAMILIES_FOR_EVOLVABLE", "execution_contract", "expected_slot0",
    "family_program", "validate_contract",
]
