"""Executable, result-neutral observations for the M092 adoption controls.

This module turns real runtime/adoption behaviour into the narrow causal facts accepted by
``m092_control_runner``.  Candidate-dependent observations are gated on an already completed,
independent reproduction.  The caller supplies the accepted program/certificate dynamically; no
canonical candidate, hidden qualification value, or post-result configuration is embedded here.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import object as _object  # type: ignore[attr-defined]

from metamorphosis.m092_adoption import (
    AdoptionError,
    build_extended_bundle,
    commit_adoption_transaction,
    downstream_body,
    execute_downstream,
    extend_substrate,
    load_committed_bundle,
    validate_candidate_for_adoption,
)
from metamorphosis.m092_control_runner import evaluate_control_evidence
from metamorphosis.m092_kernel import Machine, Program, execute_program, program_digest
from metamorphosis.m092_runtime import RefusalCode, RuntimeLanguage, SubstrateError
from metamorphosis.m092_substrate_state import SubstrateState


class ControlObservationError(ValueError):
    """An executable control observation could not establish its frozen causal facts."""


def _require_reproduction(reproduction_status: str) -> None:
    if reproduction_status != "reproduced":
        raise ControlObservationError(
            "candidate-dependent control observation requires independent reproduction"
        )


def _validated_bundle(
    *,
    program: Program,
    certificate: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
    base_language: RuntimeLanguage,
    base_substrate: SubstrateState,
    source_bundle_sha256: str,
) -> tuple[dict[str, object], dict[str, object]]:
    receipt = validate_candidate_for_adoption(
        program,
        certificate,
        expected_postcondition=expected_postcondition,
    )
    bundle = build_extended_bundle(
        base_language,
        base_substrate,
        program,
        receipt=receipt,
        source_bundle_sha256=source_bundle_sha256,
    )
    return receipt, bundle


def observe_evolvable_adoption(
    *,
    reproduction_status: str,
    program: Program,
    certificate: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
    base_language: RuntimeLanguage,
    base_substrate: SubstrateState,
    source_bundle_sha256: str,
    bundle_path: Path,
    journal_path: Path,
    probe_value: int = 0,
) -> dict[str, object]:
    """Observe the complete registered adoption path without running qualification."""

    _require_reproduction(reproduction_status)
    receipt, bundle = _validated_bundle(
        program=program,
        certificate=certificate,
        expected_postcondition=expected_postcondition,
        base_language=base_language,
        base_substrate=base_substrate,
        source_bundle_sha256=source_bundle_sha256,
    )
    committed = commit_adoption_transaction(bundle_path, journal_path, bundle)
    language, substrate = load_committed_bundle(bundle_path, journal_path)

    key = str(receipt["operation_key"])
    primitive_id = str(receipt["primitive_id"])
    operation = substrate.operation(key)
    primitive = language.definition(primitive_id)
    dependency_bound = primitive is not None and any(step[0] == key for step in primitive.body)
    execution_succeeded = False
    if operation is not None and primitive is not None and dependency_bound:
        execute_downstream(language, substrate, primitive_id, int(probe_value))
        execution_succeeded = True

    raw = {
        "facts": {
            "complete_causal_chain_enabled": (
                committed.get("phase") == "COMMITTED" and execution_succeeded
            ),
            "qualification_scoring_allowed": committed.get("phase") == "COMMITTED",
            "acquired_substrate_operation_registered": operation is not None,
            "downstream_primitive_registered": primitive is not None,
            "downstream_primitive_references_acquired_operation": dependency_bound,
        },
        "metrics": {"complete_qualifying_families": 0},
    }
    return evaluate_control_evidence("evolvable_substrate", raw)


def observe_extension_built_but_not_registered(
    *,
    reproduction_status: str,
    program: Program,
    certificate: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
    base_language: RuntimeLanguage,
    base_substrate: SubstrateState,
    source_bundle_sha256: str,
    frozen_substrate_digest: str,
    evolvable_program_digest: str,
    evolvable_receipt_digest: str,
) -> dict[str, object]:
    """Build the same accepted extension while keeping the frozen checkpoint authoritative."""

    _require_reproduction(reproduction_status)
    receipt, bundle = _validated_bundle(
        program=program,
        certificate=certificate,
        expected_postcondition=expected_postcondition,
        base_language=base_language,
        base_substrate=base_substrate,
        source_bundle_sha256=source_bundle_sha256,
    )
    primitive_id = str(receipt["primitive_id"])
    extended = SubstrateState.from_dict(bundle["substrate"])  # type: ignore[arg-type]
    built = extended.operation(str(receipt["operation_key"])) is not None
    frozen_authority = base_substrate.digest() == frozen_substrate_digest

    # A built-but-unregistered downstream primitive must remain unreachable from the frozen language.
    inaccessible = False
    try:
        execute_downstream(base_language, base_substrate, primitive_id, 0)
    except SubstrateError as error:
        inaccessible = error.code == RefusalCode.UNDEFINED_PRIMITIVE

    raw = {
        "facts": {
            "same_accepted_program_as_evolvable": program_digest(program) == evolvable_program_digest,
            "same_validation_receipt_as_evolvable": receipt.get("receipt_digest") == evolvable_receipt_digest,
            "extended_state_built": built,
            "executing_substrate_is_frozen_checkpoint": frozen_authority,
            "extended_substrate_becomes_execution_authority": not inaccessible,
            "qualification_scoring_as_evolvable": False,
        },
        "metrics": {"complete_qualifying_families": 0},
    }
    return evaluate_control_evidence("extension_built_but_not_registered", raw)


def observe_substrate_registered_downstream_not_registered(
    *,
    reproduction_status: str,
    program: Program,
    certificate: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
    base_language: RuntimeLanguage,
    base_substrate: SubstrateState,
    probe_value: int = 0,
) -> dict[str, object]:
    """Register only the acquired operation and prove it executes before language registration."""

    _require_reproduction(reproduction_status)
    receipt = validate_candidate_for_adoption(
        program,
        certificate,
        expected_postcondition=expected_postcondition,
    )
    substrate = extend_substrate(base_substrate, program, receipt=receipt)
    operation = substrate.operation(str(receipt["operation_key"]))

    operation_executable = False
    if operation is not None:
        machine = Machine(
            stack=[int(probe_value)],
            slots=[0] * substrate.slot_count,
            inputs=[int(probe_value)] * substrate.input_count,
            argument=0,
        )
        execute_program(operation.program, machine)
        operation_executable = True

    primitive_id = str(receipt["primitive_id"])
    body_built = bool(downstream_body(program)) and primitive_id.startswith("M092_USE_")
    downstream_registered = base_language.definition(primitive_id) is not None

    raw = {
        "facts": {
            "acquired_substrate_operation_registered": operation is not None,
            "acquired_substrate_operation_executable": operation_executable,
            "downstream_primitive_built": body_built,
            "downstream_primitive_registered": downstream_registered,
            "qualification_scoring_as_evolvable": False,
        },
        "metrics": {"complete_qualifying_families": 0},
    }
    return evaluate_control_evidence("substrate_registered_downstream_not_registered", raw)


__all__ = [
    "ControlObservationError",
    "observe_evolvable_adoption",
    "observe_extension_built_but_not_registered",
    "observe_substrate_registered_downstream_not_registered",
]
