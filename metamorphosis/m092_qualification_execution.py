"""Result-neutral empirical family execution for the later M092-I qualification phase.

This module does not import the hidden qualification generator, canonical-search packager, or
independent-reproduction runner.  It cannot choose a candidate and cannot materialize a hidden world.
A caller supplies one already-materialized world only after the independently reproduced canonical
result has opened the qualification gate.

The executor binds that world to the separately frozen pre-result qualification contract, verifies
that the dynamic downstream primitive is truly an acquired language primitive with exactly one live
acquired-substrate dependency, executes the frozen family program, and records immutable digests
before and after execution.  Runtime registration is forbidden here.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping

from metamorphosis.m092_qualification_contract import (
    FAMILIES,
    QualificationContractError,
    expected_slot0,
    family_program,
    validate_contract,
)
from metamorphosis.m092_runtime import RuntimeLanguage, SubstrateError, canonical_bytes
from metamorphosis.m092_substrate_state import SubstrateState, execute_from_state

QUALIFICATION_ATTEMPT_SCHEMA = "m092-qualification-family-attempt/1"
_DOWNSTREAM_ID = re.compile(r"\AM092_USE_[0-9a-f]{64}\Z")


class QualificationExecutionError(ValueError):
    """The frozen qualification execution boundary was crossed or malformed."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class QualificationWorld:
    family: str
    task_id: str
    value: int

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise QualificationExecutionError(f"unknown qualification family {self.family!r}")
        if not self.task_id:
            raise QualificationExecutionError("qualification task id is empty")
        if not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 0:
            raise QualificationExecutionError("qualification world value must be a non-negative integer")


def _acquired_dependency(
    language: RuntimeLanguage,
    substrate: SubstrateState,
    downstream_primitive_id: str,
) -> str:
    if _DOWNSTREAM_ID.fullmatch(downstream_primitive_id) is None:
        raise QualificationExecutionError("downstream primitive id is not the frozen content-addressed shape")
    primitive = language.definition(downstream_primitive_id)
    if primitive is None:
        raise QualificationExecutionError("downstream primitive is not registered in the executing language")
    if primitive.origin != "acquired":
        raise QualificationExecutionError("downstream primitive is not marked acquired")
    if primitive.parameter_kinds != ("slot", "input"):
        raise QualificationExecutionError("downstream primitive signature differs from the frozen contract")

    acquired_steps: list[str] = []
    for operation_name, _ in primitive.body:
        operation = substrate.operation(operation_name)
        if operation is not None and operation.origin == "acquired":
            acquired_steps.append(operation_name)
    if len(acquired_steps) != 1:
        raise QualificationExecutionError(
            "downstream primitive must reference exactly one live acquired substrate operation"
        )
    key = acquired_steps[0]
    if not key.startswith("ACQUIRED_"):
        raise QualificationExecutionError("live acquired substrate dependency is not content-addressed")
    return key


def execute_qualification_world(
    world: QualificationWorld,
    *,
    downstream_primitive_id: str,
    language: RuntimeLanguage,
    substrate: SubstrateState,
    qualification_contract: Mapping[str, object],
    reproduction_gate_open: bool,
    adoption_committed: bool,
    fresh_process_loaded: bool,
) -> dict[str, object]:
    """Execute one already-materialized world under the frozen post-reproduction gate."""

    if reproduction_gate_open is not True:
        raise QualificationExecutionError("qualification cannot execute before independent reproduction opens the gate")
    if adoption_committed is not True:
        raise QualificationExecutionError("qualification cannot execute before committed adoption")
    if fresh_process_loaded is not True:
        raise QualificationExecutionError("qualification cannot execute before fresh-process reload")
    try:
        contract_digest = validate_contract(qualification_contract)
    except QualificationContractError as error:
        raise QualificationExecutionError("qualification contract validation failed") from error

    dependency = _acquired_dependency(language, substrate, downstream_primitive_id)
    language_before = language.digest()
    substrate_before = substrate.digest()
    program = family_program(world.family, downstream_primitive_id)
    expected = expected_slot0(world.family, world.value)

    refusal_code: str | None = None
    state: tuple[int, ...] | None
    try:
        state = execute_from_state(program, (world.value,), language, substrate)
    except SubstrateError as error:
        state = None
        refusal_code = error.code.value

    language_after = language.digest()
    substrate_after = substrate.digest()
    if language_after != language_before or substrate_after != substrate_before:
        raise QualificationExecutionError("qualification execution mutated registered runtime state")

    actual = state[0] if state is not None else None
    result: dict[str, object] = {
        "schema": QUALIFICATION_ATTEMPT_SCHEMA,
        "contract_digest": contract_digest,
        "family": world.family,
        "task_id": world.task_id,
        "value": world.value,
        "program": [[name, list(arguments)] for name, arguments in program],
        "downstream_primitive_id": downstream_primitive_id,
        "acquired_dependency_key": dependency,
        "expected_slot0": expected,
        "actual_slot0": actual,
        "success": refusal_code is None and actual == expected,
        "refusal_code": refusal_code,
        "state_after": list(state) if state is not None else None,
        "state_digest": _digest(list(state)) if state is not None else None,
        "language_digest_before": language_before,
        "language_digest_after": language_after,
        "substrate_digest_before": substrate_before,
        "substrate_digest_after": substrate_after,
        "reproduction_gate_open": True,
        "adoption_committed": True,
        "fresh_process_loaded": True,
        "operation_registration_during_attempt": False,
        "model_calls": 0,
        "network_calls": 0,
    }
    result["attempt_digest"] = _digest(result)
    return result


__all__ = [
    "QUALIFICATION_ATTEMPT_SCHEMA", "QualificationExecutionError", "QualificationWorld",
    "execute_qualification_world",
]
