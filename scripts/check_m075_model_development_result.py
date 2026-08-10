"""Independently verify the preserved, non-scientific M075 public model-development result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_calibration_bridge import calibrate_run  # noqa: E402
from metamorphosis.m075_development_bank import TASKS, task_by_id  # noqa: E402
from metamorphosis.m075_model_development_runner import CONDITIONS  # noqa: E402
from mira_core.calibration import (  # noqa: E402
    CapabilityCertificate, ProbeVerdict, Solvability, TaskLabel, calibration_digest,
)
from mira_core.memory import MemoryLedger  # noqa: E402
from mira_core.probing import label_task  # noqa: E402
from check_m075_model_development_protocol import (  # noqa: E402
    PROTOCOL_PATH, verify as verify_protocol,
)


RESULT_PATH = ROOT / "experiments" / "M075" / "MODEL_DEVELOPMENT_RESULT.json"
RESULT_RAW_SHA256 = "dadd202886e866e31be5cefb130e9e231f7739a0b49166f8d0c1dd2766acf949"


class M075ModelDevelopmentResultVerificationError(ValueError):
    """Raised when preserved M075 public development evidence no longer recomputes."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _load(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M075ModelDevelopmentResultVerificationError(
            f"{path.name} is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise M075ModelDevelopmentResultVerificationError(
            f"{path.name} must contain one JSON object"
        )
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
        raise M075ModelDevelopmentResultVerificationError(
            "malformed capability certificate"
        ) from exc


def _verify_boundary(value: object, task_id: str) -> None:
    if not isinstance(value, Mapping):
        raise M075ModelDevelopmentResultVerificationError(
            f"{task_id}: security boundary is absent"
        )
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
        "pids_limit": task.environment.pids_limit,
        "workspace_tmpfs": "rw,nosuid,nodev,noexec,size=16777216",
        "agent_exec_user": f"{task.environment.agent_uid}:{task.environment.agent_gid}",
        "matches_declaration": True,
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise M075ModelDevelopmentResultVerificationError(
                f"{task_id}: security boundary field {field} drifted"
            )


def _verify_memory(episode: Mapping[str, object]) -> None:
    raw_memory = episode.get("memory")
    manifest = episode.get("manifest")
    if not isinstance(raw_memory, Mapping) or not isinstance(manifest, Mapping):
        raise M075ModelDevelopmentResultVerificationError(
            "episode memory or manifest is absent"
        )
    try:
        memory = MemoryLedger.restore(_canonical_json(raw_memory))
    except (TypeError, ValueError) as exc:
        raise M075ModelDevelopmentResultVerificationError(
            "episode memory chain does not verify"
        ) from exc
    if manifest.get("memory_digest") != memory.digest:
        raise M075ModelDevelopmentResultVerificationError("manifest memory digest drifted")
    expected_transcript = [{"kind": event.kind, **dict(event.payload)} for event in memory.events]
    if episode.get("transcript") != expected_transcript:
        raise M075ModelDevelopmentResultVerificationError(
            "episode transcript differs from its ledger"
        )


def _verify_epistemic_state(value: object, decision_index: int) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "schema", "step_index", "max_steps", "remaining_steps_including_current",
        "observed_command_count", "successful_command_count", "failed_command_count",
        "consecutive_nonzero_count", "last_returncode", "last_failure_class",
        "proposed_action_count", "distinct_action_count", "repeated_action_count",
        "last_action_sha256", "prior_refusal_decisions",
    }:
        raise M075ModelDevelopmentResultVerificationError("epistemic state schema drifted")
    if (
        value.get("schema") != "m075-epistemic-state-v1"
        or value.get("step_index") != decision_index
        or value.get("max_steps") != 4
        or value.get("remaining_steps_including_current") != 5 - decision_index
    ):
        raise M075ModelDevelopmentResultVerificationError(
            "epistemic state budget accounting drifted"
        )
    numeric = (
        "observed_command_count", "successful_command_count", "failed_command_count",
        "consecutive_nonzero_count", "proposed_action_count", "distinct_action_count",
        "repeated_action_count", "prior_refusal_decisions",
    )
    if any(
        not isinstance(value.get(field), int) or isinstance(value.get(field), bool)
        or int(value[field]) < 0
        for field in numeric
    ):
        raise M075ModelDevelopmentResultVerificationError("epistemic counters are malformed")


def _verify_response(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != {"decision", "script", "reason"}:
        raise M075ModelDevelopmentResultVerificationError("model response schema drifted")
    decision, script, reason = value.get("decision"), value.get("script"), value.get("reason")
    valid = (
        decision == "act" and isinstance(script, str) and bool(script) and reason is None
    ) or (
        decision == "finish" and script is None and reason is None
    ) or (
        decision == "refuse" and script is None and isinstance(reason, str) and bool(reason)
    )
    if not valid:
        raise M075ModelDevelopmentResultVerificationError("model response is invalid")


def _verify_decisions(episode: Mapping[str, object], condition_id: str) -> int:
    raw = episode.get("model_decisions")
    steps = episode.get("steps")
    states = episode.get("epistemic_states")
    if not isinstance(raw, list) or not raw or len(raw) != steps:
        raise M075ModelDevelopmentResultVerificationError(
            "episode decisions do not equal its policy steps"
        )
    context_condition = condition_id == "epistemic-context-request"
    if context_condition:
        if not isinstance(states, list) or len(states) != len(raw):
            raise M075ModelDevelopmentResultVerificationError(
                "epistemic states do not cover every decision"
            )
    elif states is not None:
        raise M075ModelDevelopmentResultVerificationError(
            "baseline episode unexpectedly carries epistemic states"
        )
    prohibited = (
        "expected_solvability", "probed_solvability", "capability_certificates",
        "solve_script", "evaluator_script", "external_success", "condition_id",
    )
    for index, decision in enumerate(raw, start=1):
        if not isinstance(decision, Mapping) or decision.get("decision_index") != index:
            raise M075ModelDevelopmentResultVerificationError("decision indexes are discontinuous")
        request = decision.get("request")
        if not isinstance(request, Mapping) or decision.get("request_sha256") != _sha256(request):
            raise M075ModelDevelopmentResultVerificationError("model request digest drifted")
        input_json = request.get("input_json")
        if not isinstance(input_json, str) or any(field in input_json for field in prohibited):
            raise M075ModelDevelopmentResultVerificationError(
                "model request crossed the development information boundary"
            )
        try:
            payload = json.loads(input_json)
        except json.JSONDecodeError as exc:
            raise M075ModelDevelopmentResultVerificationError(
                "model request input is malformed"
            ) from exc
        if not isinstance(payload, dict):
            raise M075ModelDevelopmentResultVerificationError("model request input is not an object")
        state = payload.get("epistemic_state")
        system_instruction = request.get("system_instruction")
        augmented_prompt = isinstance(system_instruction, str) and "audited epistemic_state" in system_instruction
        if context_condition:
            expected_state = states[index - 1]  # type: ignore[index]
            if state != expected_state or not augmented_prompt:
                raise M075ModelDevelopmentResultVerificationError(
                    "recorded epistemic request drifted"
                )
            _verify_epistemic_state(state, index)
        elif "epistemic_state" in payload or augmented_prompt:
            raise M075ModelDevelopmentResultVerificationError(
                "baseline request received the epistemic treatment"
            )
        if decision.get("origin") != "live_model" or decision.get("status") != "completed":
            raise M075ModelDevelopmentResultVerificationError(
                "development decision is not one completed live sample"
            )
        response = decision.get("response")
        if decision.get("response_sha256") != _sha256(response):
            raise M075ModelDevelopmentResultVerificationError("model response digest drifted")
        _verify_response(response)
    return len(raw)


def verify(result_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    protocol_report = verify_protocol()
    protocol = _load(PROTOCOL_PATH)
    if result_payload is None:
        if hashlib.sha256(RESULT_PATH.read_bytes()).hexdigest() != RESULT_RAW_SHA256:
            raise M075ModelDevelopmentResultVerificationError(
                "raw M075 model-development result bytes drifted"
            )
        result = _load(RESULT_PATH)
    else:
        result = dict(result_payload)
    if (
        result.get("schema") != "m075-public-model-development-result-v1"
        or result.get("status") != "development_complete"
        or result.get("scientific_result") is not False
        or result.get("public_contaminated_development") is not True
        or result.get("independent_model_samples") is not True
        or result.get("development_defects") != []
    ):
        raise M075ModelDevelopmentResultVerificationError(
            "M075 public model-development result is incomplete or defective"
        )
    if result.get("protocol_commitment_sha256") != protocol_report[
        "protocol_commitment_sha256"
    ]:
        raise M075ModelDevelopmentResultVerificationError(
            "result is not bound to the committed development protocol"
        )

    raw_episodes = result.get("episodes")
    order = protocol.get("episode_order")
    if not isinstance(raw_episodes, list) or not isinstance(order, list) or len(raw_episodes) != 12:
        raise M075ModelDevelopmentResultVerificationError(
            "result lacks exact twelve-episode coverage"
        )
    task_labels: dict[str, TaskLabel] = {}
    manifests = []
    live_decisions = 0
    for raw_episode, raw_order in zip(raw_episodes, order, strict=True):
        if not isinstance(raw_episode, Mapping) or not isinstance(raw_order, Mapping):
            raise M075ModelDevelopmentResultVerificationError("result episode row is malformed")
        task_id = str(raw_order["task_id"])
        condition_id = str(raw_order["condition_id"])
        task = task_by_id(task_id)
        condition = next(value for value in CONDITIONS if value.arm_id == condition_id)
        if (
            raw_episode.get("episode_id") != raw_order.get("episode_id")
            or raw_episode.get("task_id") != task_id
            or raw_episode.get("condition_id") != condition_id
            or raw_episode.get("task_sha256") != task.task_digest()
            or raw_episode.get("environment_sha256") != task.environment_digest()
        ):
            raise M075ModelDevelopmentResultVerificationError("episode binding drifted")
        _verify_boundary(raw_episode.get("security_boundary"), task_id)
        raw_certificates = raw_episode.get("capability_certificates")
        if not isinstance(raw_certificates, list):
            raise M075ModelDevelopmentResultVerificationError("episode certificates are absent")
        label = label_task(
            task_id, task.required_capabilities,
            tuple(_certificate(value) for value in raw_certificates if isinstance(value, Mapping)),
        )
        if (
            label.solvability is not task.expected_solvability
            or raw_episode.get("probed_solvability") != label.solvability.value
            or raw_episode.get("label_sha256") != label.digest()
        ):
            raise M075ModelDevelopmentResultVerificationError("episode live label drifted")
        previous = task_labels.get(task_id)
        if previous is not None and previous.digest() != label.digest():
            raise M075ModelDevelopmentResultVerificationError(
                "label drifted across development conditions"
            )
        task_labels[task_id] = label
        manifest = raw_episode.get("manifest")
        if not isinstance(manifest, Mapping) or manifest.get("arm") != condition.public_dict():
            raise M075ModelDevelopmentResultVerificationError("episode condition manifest drifted")
        if (
            raw_episode.get("status") != manifest.get("status")
            or raw_episode.get("steps") != manifest.get("steps")
        ):
            raise M075ModelDevelopmentResultVerificationError("episode terminal accounting drifted")
        _verify_memory(raw_episode)
        evaluator = raw_episode.get("evaluator")
        if not isinstance(evaluator, Mapping) or raw_episode.get("external_success") is not (
            evaluator.get("returncode") == 0
        ):
            raise M075ModelDevelopmentResultVerificationError(
                "external evaluation record drifted"
            )
        live_decisions += _verify_decisions(raw_episode, condition_id)
        manifests.append((task_id, manifest))

    public_labels = {
        task_id: {"solvability": label.solvability.value, "label_sha256": label.digest()}
        for task_id, label in sorted(task_labels.items())
    }
    if result.get("labels") != public_labels:
        raise M075ModelDevelopmentResultVerificationError("result label summary drifted")
    reports = calibrate_run(manifests, task_labels)
    public_reports = [report.public_dict() for report in reports]
    if result.get("reports") != public_reports:
        raise M075ModelDevelopmentResultVerificationError(
            "development calibration reports do not recompute"
        )
    if result.get("calibration_digest") != calibration_digest(reports):
        raise M075ModelDevelopmentResultVerificationError(
            "development calibration digest does not recompute"
        )
    if result.get("live_model_decisions") != live_decisions:
        raise M075ModelDevelopmentResultVerificationError("live model decision count drifted")
    by_condition = {report["arm_id"]: report for report in public_reports}
    feasible_successes = {
        condition.arm_id: sum(
            episode.get("condition_id") == condition.arm_id
            and episode.get("probed_solvability") == Solvability.FEASIBLE.value
            and episode.get("external_success") is True
            for episode in raw_episodes
            if isinstance(episode, Mapping)
        )
        for condition in CONDITIONS
    }
    return {
        "schema": "m075-public-model-development-result-verification-v1",
        "verified": True,
        "scientific_result": False,
        "public_contaminated_development": True,
        "episode_count": len(raw_episodes),
        "live_model_decisions": live_decisions,
        "development_defects": 0,
        "feasible_external_successes": feasible_successes,
        "baseline_true_refusals": by_condition["baseline-structured-request"]["true_refusals"],
        "context_true_refusals": by_condition["epistemic-context-request"]["true_refusals"],
        "context_false_refusals": by_condition["epistemic-context-request"]["false_refusals"],
        "result_raw_sha256": RESULT_RAW_SHA256,
        "calibration_digest": result["calibration_digest"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
