"""Target-neutral post-adoption qualification mechanics for M092-H.

The sealed task generator is intentionally not imported here.  This module receives already
materialized tasks from its caller and only after a committed extended runtime has been loaded.
Every extended and control attempt is recorded individually.  A control multiplier therefore means
actual executions; multiplying a reported counter cannot satisfy the closed ledger.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

from metamorphosis.m092_runtime import RuntimeLanguage, SubstrateError, canonical_bytes
from metamorphosis.m092_substrate_state import SubstrateState, execute_from_state

QUALIFICATION_LEDGER_SCHEMA = "m092-qualification-ledger/1"
MIN_FAMILIES = 2
MIN_TASKS_PER_FAMILY = 10
CONTROL_BUDGET_MULTIPLIER = 10


class QualificationError(ValueError):
    """Qualification ordering, accounting, or task-family contract failed."""


@dataclass(frozen=True)
class QualificationTask:
    family: str
    task_id: str
    value: int
    expected_slot0: int

    def __post_init__(self) -> None:
        if not self.family or not self.task_id:
            raise QualificationError("qualification tasks need family and task identifiers")


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _attempt(
    language: RuntimeLanguage,
    substrate: SubstrateState,
    primitive_id: str,
    task: QualificationTask,
) -> dict[str, object]:
    try:
        state = execute_from_state(
            ((primitive_id, (0, 0)),), (task.value,), language, substrate,
        )
    except SubstrateError as error:
        return {
            "success": False,
            "value": None,
            "state_before": [0] * substrate.slot_count,
            "state_after": None,
            "state_digest": None,
            "refusal_code": error.code.value,
        }
    return {
        "success": state[0] == task.expected_slot0,
        "value": state[0],
        "state_before": [0] * substrate.slot_count,
        "state_after": list(state),
        "state_digest": _digest(list(state)),
        "refusal_code": None,
    }


def run_qualification_ledger(
    tasks: Sequence[QualificationTask],
    *,
    primitive_id: str,
    extended_language: RuntimeLanguage,
    extended_substrate: SubstrateState,
    control_language: RuntimeLanguage,
    control_substrate: SubstrateState,
    fresh_process_loaded: bool,
    adoption_committed: bool,
    control_multiplier: int = CONTROL_BUDGET_MULTIPLIER,
) -> dict[str, object]:
    """Execute the complete task/control ledger after adoption; no hidden task source is reachable."""

    if not adoption_committed or not fresh_process_loaded:
        raise QualificationError("qualification cannot start before committed adoption and fresh reload")
    if control_multiplier != CONTROL_BUDGET_MULTIPLIER:
        raise QualificationError("control multiplier differs from the frozen value")
    families = sorted({task.family for task in tasks})
    if len(families) < MIN_FAMILIES:
        raise QualificationError("qualification needs at least two task families")
    counts = {family: sum(task.family == family for task in tasks) for family in families}
    if any(count < MIN_TASKS_PER_FAMILY for count in counts.values()):
        raise QualificationError("each qualification family needs at least ten tasks")
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise QualificationError("qualification task identifiers must be unique")

    extended_records: list[dict[str, object]] = []
    control_records: list[dict[str, object]] = []
    for task in tasks:
        result = _attempt(extended_language, extended_substrate, primitive_id, task)
        extended_records.append({
            "family": task.family,
            "task_id": task.task_id,
            "attempt": 0,
            **result,
        })
        # This loop is the accounting authority.  There is no field-only multiplication shortcut.
        for ordinal in range(control_multiplier):
            control = _attempt(control_language, control_substrate, primitive_id, task)
            control_records.append({
                "family": task.family,
                "task_id": task.task_id,
                "attempt": ordinal,
                **control,
            })

    expected_control_attempts = len(tasks) * control_multiplier
    if len(control_records) != expected_control_attempts:
        raise QualificationError("control execution ledger does not contain the frozen real budget")
    ledger: dict[str, object] = {
        "schema": QUALIFICATION_LEDGER_SCHEMA,
        "families": families,
        "tasks_per_family": counts,
        "control_budget_multiplier": control_multiplier,
        "extended_attempts_executed": len(extended_records),
        "control_attempts_executed": len(control_records),
        "extended_records": extended_records,
        "control_records": control_records,
        "qualification_materialized_after_adoption": True,
        "fresh_process_loaded_before_qualification": True,
    }
    ledger["ledger_digest"] = _digest(ledger)
    return ledger


__all__ = [
    "CONTROL_BUDGET_MULTIPLIER", "MIN_FAMILIES", "MIN_TASKS_PER_FAMILY",
    "QUALIFICATION_LEDGER_SCHEMA", "QualificationError", "QualificationTask",
    "run_qualification_ledger",
]
