"""Target-neutral post-adoption qualification mechanics for M092-H.

The sealed task generator is intentionally not imported here.  This module receives already
materialized tasks from its caller and only after a committed extended runtime has been loaded.
Every extended and control attempt is recorded individually.  A control multiplier therefore means
actual executions; multiplying a reported counter cannot satisfy the closed ledger.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m092_runtime import RuntimeLanguage, SubstrateError, canonical_bytes
from metamorphosis.m092_substrate_state import SubstrateState, execute_from_state

QUALIFICATION_LEDGER_SCHEMA = "m092-qualification-ledger/1"
CANONICAL_RESULT_SCHEMA = "m092-canonical-criterion-search-result/2"
REPRODUCTION_RESULT_SCHEMA = "m092-independent-reproduction-result/1"
MIN_FAMILIES = 2
MIN_TASKS_PER_FAMILY = 10
CONTROL_BUDGET_MULTIPLIER = 10

CANONICAL_RESULT_FIELDS = {
    "schema", "status", "arming_head_sha", "frozen_parent_sha", "canonical_search_attempt",
    "canonical_transport_mode", "transport_segments", "terminal_segment_index",
    "terminal_segment_digest", "terminal_segment", "first_run_only",
    "reruns_are_reproductions_only", "qualification_forbidden",
    "independent_reproduction_required", "qualification_may_begin_before_reproduction",
    "target_search_executed", "qualification_loaded", "candidate_executed_for_selection",
    "program_limit_requested", "terminal_search_status", "candidate_selected",
    "generated_programs", "certificate_policy_attempts", "certificates_constructed",
    "surviving_candidates", "marker_digest", "marker", "search_state", "result_digest",
}
REPRODUCTION_RESULT_FIELDS = {
    "schema", "status", "arming_head_sha", "arming_parent_sha", "source_canonical_run_id",
    "source_canonical_artifact_id", "source_canonical_artifact_digest",
    "source_canonical_result_digest", "terminal_reproduction_segment_index",
    "terminal_reproduction_segment_digest",
    "canonical_result_content_loaded_only_after_reproduction_terminal",
    "reproduction_from_genesis", "reproduction_only", "target_search_rerolled",
    "qualification_loaded", "candidate_executed_for_selection", "canonical_terminal_status",
    "reproduced_terminal_status", "canonical_state_digest", "reproduced_state_digest",
    "state_byte_identical", "qualification_gate_open", "reproduced_search_state", "result_digest",
}


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


def _validate_result_digest(value: Mapping[str, object], label: str) -> str:
    claimed = value.get("result_digest")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise QualificationError(f"{label} result digest is malformed")
    payload = {key: item for key, item in value.items() if key != "result_digest"}
    if claimed != _digest(payload):
        raise QualificationError(f"{label} result digest differs from recomputation")
    return claimed


def validate_reproduction_gate(
    canonical_result: Mapping[str, object],
    reproduction_result: Mapping[str, object],
) -> dict[str, object]:
    """Open qualification only for an exact independently reproduced candidate-selected result."""

    if set(canonical_result) != CANONICAL_RESULT_FIELDS or canonical_result.get("schema") != CANONICAL_RESULT_SCHEMA:
        raise QualificationError("canonical result schema or fields differ")
    if set(reproduction_result) != REPRODUCTION_RESULT_FIELDS or reproduction_result.get("schema") != REPRODUCTION_RESULT_SCHEMA:
        raise QualificationError("reproduction result schema or fields differ")
    canonical_digest = _validate_result_digest(canonical_result, "canonical")
    _validate_result_digest(reproduction_result, "reproduction")

    if canonical_result.get("terminal_search_status") != "candidate_selected":
        raise QualificationError("qualification requires a selected canonical candidate")
    if canonical_result.get("candidate_selected") is not True:
        raise QualificationError("canonical result does not contain a selected candidate")
    if canonical_result.get("target_search_executed") is not True:
        raise QualificationError("canonical target search was not executed")
    if canonical_result.get("qualification_loaded") is not False:
        raise QualificationError("canonical search crossed the qualification boundary")
    if canonical_result.get("independent_reproduction_required") is not True:
        raise QualificationError("canonical result does not require independent reproduction")
    if canonical_result.get("qualification_may_begin_before_reproduction") is not False:
        raise QualificationError("canonical result weakens the reproduction-before-qualification order")

    if reproduction_result.get("status") != "independent-reproduction-match":
        raise QualificationError("independent reproduction did not match")
    if reproduction_result.get("source_canonical_result_digest") != canonical_digest:
        raise QualificationError("reproduction is not bound to the exact canonical result")
    if reproduction_result.get("canonical_result_content_loaded_only_after_reproduction_terminal") is not True:
        raise QualificationError("canonical content was exposed before reproduction became terminal")
    if reproduction_result.get("reproduction_from_genesis") is not True:
        raise QualificationError("independent reproduction did not start from genesis")
    if reproduction_result.get("reproduction_only") is not True or reproduction_result.get("target_search_rerolled") is not False:
        raise QualificationError("reproduction result claims a search reroll")
    if reproduction_result.get("qualification_loaded") is not False:
        raise QualificationError("reproduction crossed the qualification boundary")
    if reproduction_result.get("candidate_executed_for_selection") is not False:
        raise QualificationError("reproduction executed the candidate for selection")
    if reproduction_result.get("canonical_terminal_status") != "candidate_selected":
        raise QualificationError("canonical terminal status differs from candidate_selected")
    if reproduction_result.get("reproduced_terminal_status") != "candidate_selected":
        raise QualificationError("reproduced terminal status differs from candidate_selected")
    if reproduction_result.get("state_byte_identical") is not True:
        raise QualificationError("reproduced search state is not byte-identical")
    if reproduction_result.get("qualification_gate_open") is not True:
        raise QualificationError("reproduction result keeps the qualification gate closed")
    if reproduction_result.get("canonical_state_digest") != reproduction_result.get("reproduced_state_digest"):
        raise QualificationError("canonical and reproduced state digests differ")

    return {
        "canonical_result_digest": canonical_digest,
        "reproduction_result_digest": reproduction_result["result_digest"],
        "state_digest": reproduction_result["canonical_state_digest"],
        "qualification_gate_open": True,
    }


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
    "CANONICAL_RESULT_FIELDS", "CANONICAL_RESULT_SCHEMA", "CONTROL_BUDGET_MULTIPLIER",
    "MIN_FAMILIES", "MIN_TASKS_PER_FAMILY", "QUALIFICATION_LEDGER_SCHEMA",
    "REPRODUCTION_RESULT_FIELDS", "REPRODUCTION_RESULT_SCHEMA", "QualificationError",
    "QualificationTask", "run_qualification_ledger", "validate_reproduction_gate",
]
