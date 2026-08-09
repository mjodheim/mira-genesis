"""Map M072 arm episodes onto refusal-calibration records.

**Draft apparatus. Nothing here is frozen and no result may cite it.**

The arm loop reports a terminal status; calibration needs an outcome that distinguishes an agent
that decided to stop from a harness that stopped it.  The mapping is explicit and total: an
unrecognised status raises rather than defaulting, because a silent default would quietly file
unknown behaviour under a known outcome.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from mira_core.calibration import (
    CalibrationReport, EpisodeOutcome, EpisodeRecord, TaskLabel, measure_calibration,
)
from mira_core.contracts import JsonValue


class CalibrationBridgeError(ValueError):
    """Raised when an arm manifest cannot be mapped onto a calibration record."""


STATUS_OUTCOMES: Mapping[str, EpisodeOutcome] = {
    # The agent itself concluded it should stop.
    "policy_refused": EpisodeOutcome.REFUSED,
    # The agent finished acting and handed the workspace to the external verifier.
    "submitted_for_external_evaluation": EpisodeOutcome.SUBMITTED,
    # The budget ran out with no conclusion either way.
    "step_budget_exhausted": EpisodeOutcome.EXHAUSTED,
    # Governance stopped the episode; the agent did not recognise impossibility.
    "safety_refused": EpisodeOutcome.HALTED,
    "action_contract_refused": EpisodeOutcome.HALTED,
    "unsupported_action_kind": EpisodeOutcome.HALTED,
    # Infrastructure or backend failure; carries no information about the agent's judgement.
    "policy_error": EpisodeOutcome.FAULTED,
    "body_error": EpisodeOutcome.FAULTED,
}


def outcome_for_status(status: str) -> EpisodeOutcome:
    outcome = STATUS_OUTCOMES.get(status)
    if outcome is None:
        raise CalibrationBridgeError(f"no calibration outcome declared for status {status!r}")
    return outcome


def record_from_manifest(manifest: Mapping[str, JsonValue], task_id: str) -> EpisodeRecord:
    """Turn one arm manifest into one calibration record."""

    if manifest.get("schema") != "m072-ablation-arm-manifest-v1":
        raise CalibrationBridgeError("unexpected arm manifest schema")
    arm = manifest.get("arm")
    if not isinstance(arm, Mapping) or not isinstance(arm.get("arm_id"), str):
        raise CalibrationBridgeError("arm manifest lacks its declared arm identity")
    status = manifest.get("status")
    steps = manifest.get("steps")
    if not isinstance(status, str) or not isinstance(steps, int) or isinstance(steps, bool):
        raise CalibrationBridgeError("arm manifest lacks a usable status and step count")
    return EpisodeRecord(task_id, str(arm["arm_id"]), outcome_for_status(status), steps)


def records_from_run(
    run: Iterable[tuple[str, Mapping[str, JsonValue]]],
) -> tuple[EpisodeRecord, ...]:
    """Map an iterable of `(task_id, manifest)` pairs onto records."""

    return tuple(record_from_manifest(manifest, task_id) for task_id, manifest in run)


def calibrate_run(
    run: Iterable[tuple[str, Mapping[str, JsonValue]]], labels: Mapping[str, TaskLabel],
) -> tuple[CalibrationReport, ...]:
    """Produce one report per arm present in the run, ordered by arm identifier."""

    records = records_from_run(run)
    if not records:
        raise CalibrationBridgeError("a calibration run requires at least one episode")
    arms: Sequence[str] = sorted({record.arm_id for record in records})
    return tuple(measure_calibration(records, labels, arm) for arm in arms)


__all__ = [
    "STATUS_OUTCOMES", "CalibrationBridgeError", "calibrate_run", "outcome_for_status",
    "record_from_manifest", "records_from_run",
]
