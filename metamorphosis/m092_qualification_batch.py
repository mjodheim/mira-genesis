"""Verified 2x6 empirical batch for the M092 evolvable qualification arm.

This module is inert until the caller explicitly supplies all chronology gates as true.  It never
imports the hidden-world generator.  Once permitted, it independently verifies already-materialized
qualification material against the exact executing runtime digests, converts the verified receipt to
world records, and executes exactly six worlds in each of the two frozen families through the gated
family executor.

The output is empirical evidence only.  It neither replaces the global theorem/certificate nor
computes the final H38 verdict, because the frozen control arms must be executed separately.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Mapping

from metamorphosis.m092_qualification_contract import (
    FAMILIES,
    HIDDEN_INSTANCES_PER_FAMILY,
    QualificationContractError,
    validate_contract,
)
from metamorphosis.m092_qualification_execution import (
    QualificationExecutionError,
    QualificationWorld,
    execute_qualification_world,
)
from metamorphosis.m092_qualification_material_verifier import (
    QualificationMaterialVerificationError,
    verify_qualification_material,
)
from metamorphosis.m092_runtime import RuntimeLanguage, canonical_bytes
from metamorphosis.m092_substrate_state import SubstrateState

EVOLVABLE_BATCH_SCHEMA = "m092-evolvable-qualification-batch/1"


class QualificationBatchError(ValueError):
    """The post-reproduction 2x6 qualification batch is malformed or out of order."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def run_evolvable_qualification_batch(
    material: Mapping[str, object],
    *,
    protocol_blob: bytes,
    downstream_primitive_id: str,
    language: RuntimeLanguage,
    substrate: SubstrateState,
    qualification_contract: Mapping[str, object],
    reproduction_gate_open: bool,
    adoption_committed: bool,
    fresh_process_loaded: bool,
) -> dict[str, object]:
    """Verify then execute the complete hidden 2x6 evolvable arm without control interpretation."""

    # Refuse before looking inside supplied material.  The caller may hold bytes early, but this
    # executor must not turn them into qualification information before the chronology gates open.
    if reproduction_gate_open is not True:
        raise QualificationBatchError("qualification batch is closed before independent reproduction")
    if adoption_committed is not True:
        raise QualificationBatchError("qualification batch is closed before committed adoption")
    if fresh_process_loaded is not True:
        raise QualificationBatchError("qualification batch is closed before fresh-process reload")
    try:
        contract_digest = validate_contract(qualification_contract)
    except QualificationContractError as error:
        raise QualificationBatchError("qualification execution contract differs") from error

    language_digest = language.digest()
    substrate_digest = substrate.digest()
    try:
        verified = verify_qualification_material(
            material,
            protocol_blob=protocol_blob,
            extended_substrate_digest=substrate_digest,
            extended_language_digest=language_digest,
        )
    except QualificationMaterialVerificationError as error:
        raise QualificationBatchError("independent qualification material verification failed") from error

    raw_worlds = verified.get("worlds")
    if not isinstance(raw_worlds, list):
        raise QualificationBatchError("verified qualification receipt has no ordered world list")
    counts = Counter(str(world.get("family")) for world in raw_worlds if isinstance(world, Mapping))
    if counts != Counter({family: HIDDEN_INSTANCES_PER_FAMILY for family in FAMILIES}):
        raise QualificationBatchError("verified qualification world family counts differ")

    attempts: list[dict[str, object]] = []
    for raw in raw_worlds:
        if not isinstance(raw, Mapping):
            raise QualificationBatchError("verified qualification world is malformed")
        try:
            world = QualificationWorld(
                family=str(raw["family"]),
                task_id=str(raw["task_id"]),
                value=int(raw["value"]),
            )
            attempt = execute_qualification_world(
                world,
                downstream_primitive_id=downstream_primitive_id,
                language=language,
                substrate=substrate,
                qualification_contract=qualification_contract,
                reproduction_gate_open=True,
                adoption_committed=True,
                fresh_process_loaded=True,
            )
        except (KeyError, TypeError, ValueError, QualificationExecutionError) as error:
            raise QualificationBatchError("verified qualification world could not execute") from error
        if attempt.get("contract_digest") != contract_digest:
            raise QualificationBatchError("qualification attempt is bound to a different execution contract")
        attempts.append(attempt)

    summaries: list[dict[str, object]] = []
    complete_families = 0
    for family in FAMILIES:
        records = [attempt for attempt in attempts if attempt["family"] == family]
        successes = sum(attempt.get("success") is True for attempt in records)
        complete = len(records) == HIDDEN_INSTANCES_PER_FAMILY and successes == HIDDEN_INSTANCES_PER_FAMILY
        complete_families += int(complete)
        summaries.append({
            "family": family,
            "attempts": len(records),
            "successes": successes,
            "complete_family_pass": complete,
        })

    result: dict[str, object] = {
        "schema": EVOLVABLE_BATCH_SCHEMA,
        "arm": "evolvable_substrate",
        "contract_digest": contract_digest,
        "qualification_material_verification_digest": verified["verification_digest"],
        "materialization_digest": verified["materialization_digest"],
        "protocol_sha256": verified["protocol_sha256"],
        "extended_substrate_digest": substrate_digest,
        "extended_language_digest": language_digest,
        "downstream_primitive_id": downstream_primitive_id,
        "families": list(FAMILIES),
        "attempts_expected": len(FAMILIES) * HIDDEN_INSTANCES_PER_FAMILY,
        "attempts_executed": len(attempts),
        "attempts": attempts,
        "family_summaries": summaries,
        "complete_families": complete_families,
        "evolvable_passes_frozen_empirical_rule": complete_families == len(FAMILIES),
        "global_certificate_remains_separate": True,
        "final_h38_verdict_computed_here": False,
        "control_arms_executed_here": False,
        "reproduction_gate_open": True,
        "adoption_committed": True,
        "fresh_process_loaded": True,
        "model_calls": 0,
        "network_calls": 0,
    }
    result["batch_digest"] = _digest(result)
    return result


__all__ = [
    "EVOLVABLE_BATCH_SCHEMA", "QualificationBatchError", "run_evolvable_qualification_batch",
]
