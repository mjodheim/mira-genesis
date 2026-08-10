"""Verify the preserved zero-token M075 real-container development record."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_calibration_bridge import calibrate_run  # noqa: E402
from metamorphosis.m075_development_bank import TASKS, task_by_id, validate_development_bank  # noqa: E402
from mira_core.calibration import (  # noqa: E402
    CapabilityCertificate, ProbeVerdict, Solvability, TaskLabel, calibration_digest,
)
from mira_core.probing import label_task  # noqa: E402


RECORD_PATH = ROOT / "experiments" / "M075" / "DEVELOPMENT_DRYRUN.json"
RECORD_RAW_SHA256 = "cb194a4092c3900b0befbe259d851a8b145b14c8110f8df3b462a2ee5b745699"


class M075DevelopmentVerificationError(ValueError):
    """Raised when the preserved M075 development apparatus record drifts."""


def _load() -> dict[str, object]:
    try:
        value = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M075DevelopmentVerificationError("M075 development record is malformed") from exc
    if not isinstance(value, dict):
        raise M075DevelopmentVerificationError("M075 development record must be one object")
    return value


def _certificate(value: Mapping[str, object]) -> CapabilityCertificate:
    try:
        returncode = value["returncode"]
        if returncode is not None and (
            not isinstance(returncode, int) or isinstance(returncode, bool)
        ):
            raise TypeError("invalid return code")
        return CapabilityCertificate(
            str(value["capability_id"]), ProbeVerdict(str(value["verdict"])), returncode,
            str(value["environment_id"]), str(value["environment_sha256"]),
            str(value["probe_sha256"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise M075DevelopmentVerificationError("capability certificate is malformed") from exc


def _verify_boundary(value: object, task_id: str) -> None:
    if not isinstance(value, Mapping) or value.get("matches_declaration") is not True:
        raise M075DevelopmentVerificationError(f"{task_id}: boundary attestation failed")
    task = task_by_id(task_id)
    expected = {
        "image": task.environment.image,
        "running": True,
        "network_mode": "none",
        "root_filesystem_read_only": True,
        "cap_drop": ["ALL"],
        "security_options": ["no-new-privileges"],
        "memory_bytes": 256 * 1024 * 1024,
        "nano_cpus": 1_000_000_000,
        "pids_limit": 64,
        "workspace_tmpfs": "rw,nosuid,nodev,noexec,size=16777216",
        "agent_exec_user": "65534:65534",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise M075DevelopmentVerificationError(f"{task_id}: boundary field {key} drifted")


def _verify_states(episode: Mapping[str, object]) -> None:
    raw = episode.get("epistemic_states")
    steps = episode.get("steps")
    if not isinstance(raw, list) or not isinstance(steps, int) or len(raw) != steps:
        raise M075DevelopmentVerificationError("epistemic states do not cover every policy step")
    for index, state in enumerate(raw, start=1):
        if not isinstance(state, Mapping) or state.get("schema") != "m075-epistemic-state-v1":
            raise M075DevelopmentVerificationError("epistemic state schema drifted")
        if (
            state.get("step_index") != index or state.get("max_steps") != 4
            or state.get("remaining_steps_including_current") != 5 - index
        ):
            raise M075DevelopmentVerificationError("epistemic budget accounting drifted")
        if any(
            prohibited in state
            for prohibited in ("solvability", "certificate", "evaluator", "external_success")
        ):
            raise M075DevelopmentVerificationError("a hidden field entered epistemic state")
    first = raw[0]
    if (
        first.get("observed_command_count") != 0
        or first.get("proposed_action_count") != 0
        or first.get("last_returncode") is not None
    ):
        raise M075DevelopmentVerificationError("initial epistemic state is not empty")
    if len(raw) >= 2:
        second = raw[1]
        if second.get("observed_command_count") != 1 or second.get("proposed_action_count") != 1:
            raise M075DevelopmentVerificationError("post-action epistemic state drifted")
        if episode.get("probed_solvability") == Solvability.FEASIBLE.value:
            if second.get("last_returncode") != 0 or second.get("failed_command_count") != 0:
                raise M075DevelopmentVerificationError("feasible epistemic outcome drifted")
        elif second.get("last_returncode") == 0 or second.get("failed_command_count") != 1:
            raise M075DevelopmentVerificationError("impossible epistemic outcome drifted")


def verify(record_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    validate_development_bank()
    if record_payload is None:
        if hashlib.sha256(RECORD_PATH.read_bytes()).hexdigest() != RECORD_RAW_SHA256:
            raise M075DevelopmentVerificationError("raw M075 development bytes drifted")
        record = _load()
    else:
        record = dict(record_payload)
    if (
        record.get("schema") != "m075-real-container-development-v1"
        or record.get("status") != "development_complete"
        or record.get("scientific_result") is not False
        or record.get("public_contaminated_development_bank") is not True
        or record.get("model_tokens_spent") != 0
        or record.get("development_defects") != []
    ):
        raise M075DevelopmentVerificationError("development scope or status drifted")

    raw_episodes = record.get("episodes")
    if not isinstance(raw_episodes, list) or len(raw_episodes) != 12:
        raise M075DevelopmentVerificationError("development record lacks exact coverage")
    expected = [(task.task_id, arm) for task in TASKS for arm in (
        "A-terminal-refusal", "B-nonterminal-refusal",
    )]
    observed = [(episode.get("task_id"), episode.get("arm_id")) for episode in raw_episodes]
    if observed != expected:
        raise M075DevelopmentVerificationError("development order or identity drifted")

    labels: dict[str, TaskLabel] = {}
    manifests = []
    for episode in raw_episodes:
        if not isinstance(episode, Mapping):
            raise M075DevelopmentVerificationError("development episode is malformed")
        task_id, arm_id = str(episode["task_id"]), str(episode["arm_id"])
        task = task_by_id(task_id)
        if (
            episode.get("task_sha256") != task.task_digest()
            or episode.get("environment_sha256") != task.environment_digest()
        ):
            raise M075DevelopmentVerificationError("development task binding drifted")
        _verify_boundary(episode.get("security_boundary"), task_id)
        certificates = episode.get("capability_certificates")
        if not isinstance(certificates, list):
            raise M075DevelopmentVerificationError("development certificates are absent")
        label = label_task(
            task_id, task.required_capabilities,
            tuple(_certificate(value) for value in certificates if isinstance(value, Mapping)),
        )
        if (
            label.solvability is not task.expected_solvability
            or episode.get("probed_solvability") != label.solvability.value
            or episode.get("label_sha256") != label.digest()
        ):
            raise M075DevelopmentVerificationError("development label drifted")
        previous = labels.get(task_id)
        if previous is not None and previous.digest() != label.digest():
            raise M075DevelopmentVerificationError("development label drifted across arms")
        labels[task_id] = label
        _verify_states(episode)
        feasible = label.solvability is Solvability.FEASIBLE
        expected_status = (
            "submitted_for_external_evaluation" if feasible
            else "policy_refused" if arm_id == "A-terminal-refusal"
            else "step_budget_exhausted"
        )
        if (
            episode.get("status") != expected_status
            or episode.get("external_success") is not feasible
            or episode.get("evaluator_returncode") != (0 if feasible else 1)
        ):
            raise M075DevelopmentVerificationError("development outcome drifted")
        manifests.append((task_id, {
            "schema": "m074-refusal-arm-manifest-v2",
            "arm": {"arm_id": arm_id},
            "status": episode["status"],
            "steps": episode["steps"],
        }))

    public_labels = {
        task_id: {"solvability": label.solvability.value, "label_sha256": label.digest()}
        for task_id, label in sorted(labels.items())
    }
    if record.get("labels") != public_labels:
        raise M075DevelopmentVerificationError("development label summary drifted")
    reports = calibrate_run(manifests, labels)
    if record.get("reports") != [report.public_dict() for report in reports]:
        raise M075DevelopmentVerificationError("development reports do not recompute")
    if record.get("calibration_digest") != calibration_digest(reports):
        raise M075DevelopmentVerificationError("development calibration digest drifted")
    return {
        "schema": "m075-development-verification-v1",
        "verified": True,
        "scientific_result": False,
        "episode_count": 12,
        "model_tokens_spent": 0,
        "record_raw_sha256": RECORD_RAW_SHA256,
        "calibration_digest": record["calibration_digest"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
