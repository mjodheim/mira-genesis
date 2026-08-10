"""Verify the preserved non-scientific M074 container development records."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_calibration_bridge import outcome_for_status  # noqa: E402
from metamorphosis.m074_task_bank import TASKS, validate_bank  # noqa: E402
from mira_core.calibration import (  # noqa: E402
    CapabilityCertificate, EpisodeRecord, ProbeVerdict, Solvability, calibration_digest,
    measure_calibration,
)
from mira_core.probing import label_task  # noqa: E402


PROBE_RECORD = ROOT / "experiments" / "M074" / "DEVELOPMENT_PROBE_BANK.json"
DRYRUN_RECORD = ROOT / "experiments" / "M074" / "DEVELOPMENT_DRYRUN.json"
PROBE_RECORD_SHA256 = "51a82ca7a8ecec1a2ce43d55de87a3871c358e6bb3f427682ec98756e1ad0827"
DRYRUN_RECORD_SHA256 = "2abbf79444e37c38b1f2fb6c17ef764c281d98579c54dbfd2511211914ee114f"


class DevelopmentVerificationError(ValueError):
    """Raised when a preserved M074 development record no longer matches the apparatus."""


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DevelopmentVerificationError(f"{path.name} must contain a JSON object")
    return value


def _certificate(value: Mapping[str, object]) -> CapabilityCertificate:
    try:
        verdict = ProbeVerdict(str(value["verdict"]))
        returncode = value["returncode"]
        if returncode is not None and (
            not isinstance(returncode, int) or isinstance(returncode, bool)
        ):
            raise TypeError("return code is not an integer or null")
        return CapabilityCertificate(
            str(value["capability_id"]), verdict, returncode,
            str(value["environment_id"]), str(value["environment_sha256"]),
            str(value["probe_sha256"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DevelopmentVerificationError("malformed capability certificate") from exc


def verify(
    probe_payload: Mapping[str, object] | None = None,
    dryrun_payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Rebuild labels and calibration reports from current task contracts and preserved rows."""

    validate_bank()
    if probe_payload is None and hashlib.sha256(PROBE_RECORD.read_bytes()).hexdigest() != PROBE_RECORD_SHA256:
        raise DevelopmentVerificationError("preserved probe-bank bytes drifted")
    if dryrun_payload is None and hashlib.sha256(DRYRUN_RECORD.read_bytes()).hexdigest() != DRYRUN_RECORD_SHA256:
        raise DevelopmentVerificationError("preserved dry-run bytes drifted")
    probe = dict(probe_payload) if probe_payload is not None else _load(PROBE_RECORD)
    dryrun = dict(dryrun_payload) if dryrun_payload is not None else _load(DRYRUN_RECORD)
    if probe.get("schema") != "m074-probed-task-labels-v1":
        raise DevelopmentVerificationError("unexpected probe-bank schema")
    if dryrun.get("schema") != "m074-real-container-dryrun-v2":
        raise DevelopmentVerificationError("unexpected dry-run schema")
    if probe.get("scientific_result") is not False or dryrun.get("scientific_result") is not False:
        raise DevelopmentVerificationError("development records must not claim a scientific result")
    if probe.get("bank_defects") != [] or dryrun.get("apparatus_defects") != []:
        raise DevelopmentVerificationError("a preserved development record contains defects")
    if dryrun.get("model_tokens_spent") != 0 or dryrun.get("label_blind_scripted_policy") is not True:
        raise DevelopmentVerificationError("dry run is not the declared zero-token label-blind run")
    if (
        dryrun.get("fresh_container_per_episode") is not True
        or dryrun.get("same_container_probed_and_acted_in") is not True
    ):
        raise DevelopmentVerificationError("dry run lost its container-boundary attestations")

    tasks = {task.task_id: task for task in TASKS}
    raw_labels = probe.get("labels")
    if not isinstance(raw_labels, list) or len(raw_labels) != len(tasks):
        raise DevelopmentVerificationError("probe bank does not cover every task exactly once")
    labels = {}
    for raw in raw_labels:
        if not isinstance(raw, Mapping):
            raise DevelopmentVerificationError("probe-bank label row is not an object")
        task_id = raw.get("task_id")
        if not isinstance(task_id, str) or task_id not in tasks or task_id in labels:
            raise DevelopmentVerificationError("probe-bank task identity is missing or duplicated")
        task = tasks[task_id]
        if raw.get("task_sha256") != task.task_digest():
            raise DevelopmentVerificationError(f"{task_id}: task digest drifted")
        if raw.get("environment_sha256") != task.environment_digest():
            raise DevelopmentVerificationError(f"{task_id}: environment digest drifted")
        raw_certificates = raw.get("certificates")
        if not isinstance(raw_certificates, list):
            raise DevelopmentVerificationError(f"{task_id}: certificates are missing")
        label = label_task(
            task_id, task.required_capabilities,
            tuple(_certificate(certificate) for certificate in raw_certificates),
        )
        if raw.get("label_digest") != label.digest():
            raise DevelopmentVerificationError(f"{task_id}: label digest drifted")
        if raw.get("probed_solvability") != label.solvability.value:
            raise DevelopmentVerificationError(f"{task_id}: probed solvability drifted")
        if label.solvability is not task.expected_solvability:
            raise DevelopmentVerificationError(f"{task_id}: live label contradicts the bank")
        labels[task_id] = label

    if probe.get("feasible_count") != 3 or probe.get("impossible_count") != 3:
        raise DevelopmentVerificationError("probe bank is not balanced 3/3")

    dry_labels = dryrun.get("labels")
    if not isinstance(dry_labels, Mapping) or set(dry_labels) != set(tasks):
        raise DevelopmentVerificationError("dry-run labels do not cover the task bank")
    for task_id, label in labels.items():
        row = dry_labels[task_id]
        if not isinstance(row, Mapping) or row.get("label_sha256") != label.digest():
            raise DevelopmentVerificationError(f"{task_id}: dry-run label binding drifted")
        if row.get("solvability") != label.solvability.value:
            raise DevelopmentVerificationError(f"{task_id}: dry-run solvability drifted")

    raw_episodes = dryrun.get("episodes")
    expected_arms = {"A-terminal-refusal", "B-nonterminal-refusal"}
    if not isinstance(raw_episodes, list) or len(raw_episodes) != len(tasks) * len(expected_arms):
        raise DevelopmentVerificationError("dry run does not contain the exact 12 episodes")
    records: list[EpisodeRecord] = []
    coverage: set[tuple[str, str]] = set()
    for raw in raw_episodes:
        if not isinstance(raw, Mapping):
            raise DevelopmentVerificationError("dry-run episode is not an object")
        task_id, arm_id = raw.get("task_id"), raw.get("arm_id")
        if not isinstance(task_id, str) or task_id not in tasks or arm_id not in expected_arms:
            raise DevelopmentVerificationError("dry-run episode has an unknown task or arm")
        identity = (task_id, str(arm_id))
        if identity in coverage:
            raise DevelopmentVerificationError("dry-run episode identity is duplicated")
        coverage.add(identity)
        task = tasks[task_id]
        if raw.get("task_sha256") != task.task_digest():
            raise DevelopmentVerificationError(f"{task_id}: episode task digest drifted")
        if raw.get("environment_sha256") != task.environment_digest():
            raise DevelopmentVerificationError(f"{task_id}: episode environment digest drifted")
        status, steps = raw.get("status"), raw.get("steps")
        if not isinstance(status, str) or not isinstance(steps, int) or isinstance(steps, bool):
            raise DevelopmentVerificationError("dry-run episode status or steps are malformed")
        record = EpisodeRecord(task_id, str(arm_id), outcome_for_status(status), steps)
        records.append(record)
        feasible = labels[task_id].solvability is Solvability.FEASIBLE
        if raw.get("external_success") is not feasible:
            raise DevelopmentVerificationError(f"{task_id}/{arm_id}: external state check drifted")
        expected_status = (
            "submitted_for_external_evaluation" if feasible
            else "policy_refused" if arm_id == "A-terminal-refusal"
            else "step_budget_exhausted"
        )
        if status != expected_status:
            raise DevelopmentVerificationError(f"{task_id}/{arm_id}: terminal status drifted")

    reports = [measure_calibration(records, labels, arm) for arm in sorted(expected_arms)]
    if dryrun.get("reports") != [report.public_dict() for report in reports]:
        raise DevelopmentVerificationError("preserved calibration reports do not recompute")
    digest = calibration_digest(reports)
    if dryrun.get("calibration_digest") != digest:
        raise DevelopmentVerificationError("preserved calibration digest does not recompute")
    return {
        "schema": "m074-development-verification-v1",
        "verified": True,
        "scientific_result": False,
        "task_count": len(tasks),
        "episode_count": len(records),
        "calibration_digest": digest,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
