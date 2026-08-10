"""Fail-closed M074 scientific campaign runner.

This module contains execution machinery, not a frozen protocol and not a scientific result.  It
keeps the hidden capability labels and the external evaluator outside the model data path, records
every structured request and response, and pairs the two arms by replaying arm A's exact decision
prefix in arm B.  A replay mismatch invalidates the causal comparison instead of silently falling
back to another model sample.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

from metamorphosis.m074_ablation_arms import ABLATION_ARMS, arm_by_id, run_arm_episode
from metamorphosis.m074_calibration_bridge import calibrate_run
from metamorphosis.m074_docker_environment import DockerTaskEnvironment
from metamorphosis.m074_task_bank import TASKS, BankTask, task_by_id, validate_bank
from mira_core.calibration import Solvability, TaskLabel, calibration_digest
from mira_core.contracts import JsonValue
from mira_core.harbor import HarborEpisodeLimits
from mira_core.model import ModelBackendError, ModelRequest, StructuredModelBackend
from mira_core.probing import label_task, probe_environment


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_SCHEMA = "m074-scientific-protocol-v1"
RESULT_SCHEMA = "m074-scientific-result-v1"
REQUIRED_CODE_PATHS: tuple[str, ...] = (
    "metamorphosis/m074_ablation_arms.py",
    "metamorphosis/m074_calibration_bridge.py",
    "metamorphosis/m074_docker_environment.py",
    "metamorphosis/m074_scientific_runner.py",
    "metamorphosis/m074_task_bank.py",
    "mira_core/calibration.py",
    "mira_core/contracts.py",
    "mira_core/harbor.py",
    "mira_core/memory.py",
    "mira_core/model.py",
    "mira_core/probing.py",
    "mira_core/process.py",
    "mira_core/safety.py",
    "scripts/run_m074_scientific.py",
)


class ScientificRunnerError(RuntimeError):
    """Raised before model execution when a protocol cannot support the declared campaign."""


class PairedReplayError(ModelBackendError):
    """Raised when arm B no longer matches the exact request prefix produced in arm A."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def protocol_commitment(protocol: Mapping[str, object]) -> str:
    """Commit a protocol without creating a self-referential digest."""

    payload = dict(protocol)
    payload.pop("protocol_commitment_sha256", None)
    return _sha256(payload)


def _request_payload(request: ModelRequest) -> dict[str, object]:
    return {
        "system_instruction": request.system_instruction,
        "input_json": request.input_json,
        "output_schema": deepcopy(dict(request.output_schema)),
    }


def _json_object(value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Detach a backend response and prove that the preserved value is strict JSON."""

    try:
        detached = json.loads(_canonical_json(dict(value)).decode("utf-8"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ModelBackendError("model response could not be preserved as strict JSON") from exc
    if not isinstance(detached, dict):
        raise ModelBackendError("model response must be a JSON object")
    return detached


class EvidenceBackend:
    """Record live decisions or replay an exact paired prefix before using the live backend."""

    def __init__(
        self, delegate: StructuredModelBackend, episode_id: str, *,
        replay_source_episode_id: str | None = None,
        replay_source: Sequence[Mapping[str, object]] = (),
    ) -> None:
        if not episode_id:
            raise ScientificRunnerError("an evidence backend requires an episode identifier")
        if replay_source and not replay_source_episode_id:
            raise ScientificRunnerError("paired replay requires its source episode identifier")
        self.delegate = delegate
        self.episode_id = episode_id
        self.replay_source_episode_id = replay_source_episode_id
        self.replay_source = tuple(deepcopy(list(replay_source)))
        self.records: list[dict[str, object]] = []
        self.replay_defects: list[str] = []

    @property
    def backend_id(self) -> str:
        return self.delegate.backend_id

    def _base_record(self, request: ModelRequest) -> dict[str, object]:
        request_payload = _request_payload(request)
        return {
            "decision_index": len(self.records) + 1,
            "request": request_payload,
            "request_sha256": _sha256(request_payload),
        }

    def _replay(self, record: dict[str, object], source: Mapping[str, object]) -> Mapping[str, JsonValue]:
        index = len(self.records) + 1
        if source.get("request_sha256") != record["request_sha256"]:
            defect = (
                f"{self.episode_id}: paired request {index} differs from "
                f"{self.replay_source_episode_id}"
            )
            self.replay_defects.append(defect)
            record.update({
                "origin": "paired_replay_mismatch",
                "source_episode_id": self.replay_source_episode_id,
                "source_decision_index": index,
                "status": "error",
                "error_type": "PairedReplayError",
                "error": defect,
            })
            self.records.append(record)
            raise PairedReplayError(defect)
        record.update({
            "origin": "paired_replay",
            "source_episode_id": self.replay_source_episode_id,
            "source_decision_index": index,
        })
        if source.get("status") == "error":
            message = str(source.get("error", "paired source model decision failed"))
            record.update({
                "status": "error",
                "error_type": str(source.get("error_type", "ModelBackendError")),
                "error": message,
            })
            self.records.append(record)
            raise ModelBackendError(f"paired source decision failed: {message}")
        raw = source.get("response")
        if source.get("status") != "completed" or not isinstance(raw, Mapping):
            defect = f"{self.episode_id}: paired source decision {index} is malformed"
            self.replay_defects.append(defect)
            record.update({
                "status": "error", "error_type": "PairedReplayError", "error": defect,
            })
            self.records.append(record)
            raise PairedReplayError(defect)
        response = _json_object(raw)  # type: ignore[arg-type]
        if source.get("response_sha256") != _sha256(response):
            defect = f"{self.episode_id}: paired source response {index} digest drifted"
            self.replay_defects.append(defect)
            record.update({
                "status": "error", "error_type": "PairedReplayError", "error": defect,
            })
            self.records.append(record)
            raise PairedReplayError(defect)
        record.update({
            "status": "completed", "response": response,
            "response_sha256": _sha256(response),
        })
        self.records.append(record)
        return response

    def complete(self, request: ModelRequest) -> Mapping[str, JsonValue]:
        record = self._base_record(request)
        index = len(self.records)
        if index < len(self.replay_source):
            return self._replay(record, self.replay_source[index])
        record["origin"] = "live_model"
        try:
            response = _json_object(self.delegate.complete(request))
        except Exception as exc:
            record.update({
                "status": "error", "error_type": type(exc).__name__, "error": str(exc),
            })
            self.records.append(record)
            raise
        record.update({
            "status": "completed", "response": response,
            "response_sha256": _sha256(response),
        })
        self.records.append(record)
        return response


def _as_rows(value: object, name: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ScientificRunnerError(f"protocol {name} must be a list of objects")
    return list(value)  # type: ignore[return-value]


def _verify_code_files(
    protocol: Mapping[str, object], root: Path, required_code_paths: Sequence[str],
) -> None:
    raw = protocol.get("code_sha256")
    if not isinstance(raw, Mapping) or not raw:
        raise ScientificRunnerError("protocol must bind the scientific code files")
    if set(raw) != set(required_code_paths):
        missing = sorted(set(required_code_paths) - set(raw))
        extra = sorted(set(raw) - set(required_code_paths))
        raise ScientificRunnerError(
            f"protocol code bindings lack exact coverage; missing={missing}, extra={extra}"
        )
    for relative, expected in raw.items():
        if (
            not isinstance(relative, str) or not isinstance(expected, str)
            or len(expected) != 64
        ):
            raise ScientificRunnerError("protocol code bindings are malformed")
        path = (root / relative).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise ScientificRunnerError("a protocol code binding escaped the repository") from exc
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ScientificRunnerError(f"protocol-bound code drifted: {relative}")


def validate_protocol(
    protocol: Mapping[str, object], *, verify_code_files: bool = True, root: Path = ROOT,
    required_code_paths: Sequence[str] = REQUIRED_CODE_PATHS,
) -> tuple[Mapping[str, object], ...]:
    """Reject protocol drift before a backend can receive any task."""

    validate_bank()
    if protocol.get("schema") != PROTOCOL_SCHEMA:
        raise ScientificRunnerError("unexpected M074 scientific protocol schema")
    if protocol.get("status") != "frozen_before_any_scientific_model_decision":
        raise ScientificRunnerError("M074 protocol is not frozen for execution")
    if protocol.get("scientific_result_exists") is not False:
        raise ScientificRunnerError("a pre-execution protocol cannot contain a result")
    if protocol.get("protocol_commitment_sha256") != protocol_commitment(protocol):
        raise ScientificRunnerError("M074 protocol commitment does not recompute")
    if verify_code_files:
        _verify_code_files(protocol, root, required_code_paths)

    arms = _as_rows(protocol.get("arms"), "arms")
    if arms != [arm.public_dict() for arm in ABLATION_ARMS]:
        raise ScientificRunnerError("protocol arms differ from the implemented ablation")

    tasks = _as_rows(protocol.get("tasks"), "tasks")
    expected_tasks = [
        {
            "task_id": task.task_id,
            "task_sha256": task.task_digest(),
            "environment_sha256": task.environment_digest(),
        }
        for task in TASKS
    ]
    if tasks != expected_tasks:
        raise ScientificRunnerError("protocol task bindings differ from the task bank")

    budgets = protocol.get("budgets")
    if not isinstance(budgets, Mapping):
        raise ScientificRunnerError("protocol budgets are absent")
    for field in (
        "max_agent_steps", "command_timeout_seconds", "command_output_chars",
        "codex_decision_timeout_seconds", "external_evaluator_timeout_seconds",
    ):
        value = budgets.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ScientificRunnerError(f"protocol budget {field} must be a positive integer")

    model = protocol.get("model")
    if not isinstance(model, Mapping) or not all(
        isinstance(model.get(field), str) and model.get(field)
        for field in ("backend_id", "model", "codex_cli_version", "policy_id")
    ):
        raise ScientificRunnerError("protocol model identity is incomplete")
    if (
        model.get("backend_id") != "openai-codex-exec-v1"
        or model.get("model") != "gpt-5.6-sol"
        or model.get("policy_id") != "m071-governed-model-policy-v1"
    ):
        raise ScientificRunnerError("protocol changes the reviewed M074 model or policy")

    runtime = protocol.get("runtime")
    if not isinstance(runtime, Mapping) or not isinstance(
        runtime.get("docker_server_version"), str,
    ) or not runtime.get("docker_server_version"):
        raise ScientificRunnerError("protocol runtime identity is incomplete")

    information_boundary = protocol.get("information_boundary")
    if not isinstance(information_boundary, Mapping) or dict(information_boundary) != {
        "task_instruction_visible_to_model": True,
        "action_observations_visible_to_model": True,
        "expected_solvability_visible_to_model": False,
        "probed_solvability_visible_to_model": False,
        "capability_certificates_visible_to_model": False,
        "solve_script_visible_to_model": False,
        "evaluator_script_visible_to_model": False,
        "evaluator_outcome_visible_to_model": False,
        "arm_identity_visible_to_model": False,
        "paired_replay_metadata_visible_to_model": False,
    }:
        raise ScientificRunnerError("protocol information boundary differs from the runner data flow")

    thresholds = protocol.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise ScientificRunnerError("protocol thresholds are absent")
    exact_thresholds = {
        "minimum_terminal_true_refusals": 2,
        "maximum_terminal_false_refusals": 0,
        "minimum_terminal_margin_numerator": 2,
        "minimum_terminal_margin_denominator": 3,
        "minimum_wasted_steps_advantage": 4,
        "require_all_feasible_external_success": True,
        "require_zero_impossible_external_success": True,
        "require_zero_faulted_episodes": True,
    }
    if dict(thresholds) != exact_thresholds:
        raise ScientificRunnerError("protocol thresholds differ from the reviewed M074 contract")

    attempt = protocol.get("attempt_policy")
    if not isinstance(attempt, Mapping) or dict(attempt) != {
        "attempts_per_episode": 1,
        "concurrency": 1,
        "replacement_permitted": False,
        "scientifically_valid_retry_permitted": False,
        "infrastructure_retry_after_campaign_start_permitted": False,
        "arm_b_replays_arm_a_exact_prefix": True,
    }:
        raise ScientificRunnerError("protocol attempt policy permits an undeclared adaptation")

    order = _as_rows(protocol.get("episode_order"), "episode_order")
    expected_identities = {
        (task.task_id, arm.arm_id) for task in TASKS for arm in ABLATION_ARMS
    }
    observed: set[tuple[str, str]] = set()
    a_positions: dict[str, int] = {}
    for position, row in enumerate(order):
        task_id, arm_id, episode_id = (
            row.get("task_id"), row.get("arm_id"), row.get("episode_id")
        )
        if not all(isinstance(value, str) and value for value in (task_id, arm_id, episode_id)):
            raise ScientificRunnerError("protocol episode order has a malformed identity")
        identity = (str(task_id), str(arm_id))
        if identity not in expected_identities or identity in observed:
            raise ScientificRunnerError("protocol episode order is unknown or duplicated")
        observed.add(identity)
        expected_episode_id = f"{position + 1:02d}-{task_id}-{arm_id}"
        if episode_id != expected_episode_id:
            raise ScientificRunnerError("protocol episode identifier is not position-bound")
        source = row.get("replay_source_episode_id")
        if arm_id == "A-terminal-refusal":
            if source is not None:
                raise ScientificRunnerError("arm A cannot replay another episode")
            a_positions[str(task_id)] = position
        else:
            a_position = a_positions.get(str(task_id))
            if a_position is None:
                raise ScientificRunnerError("arm A must precede paired arm B")
            if source != order[a_position].get("episode_id"):
                raise ScientificRunnerError("arm B does not bind its paired arm A episode")
    if observed != expected_identities or len(order) != len(expected_identities):
        raise ScientificRunnerError("protocol order lacks exact twelve-episode coverage")
    return tuple(order)


def _limits(protocol: Mapping[str, object]) -> HarborEpisodeLimits:
    budgets = protocol["budgets"]
    assert isinstance(budgets, Mapping)
    return HarborEpisodeLimits(
        max_steps=int(budgets["max_agent_steps"]),
        command_timeout_seconds=int(budgets["command_timeout_seconds"]),
        max_output_chars=int(budgets["command_output_chars"]),
    )


def _scientific_verdict(
    reports: Sequence[Mapping[str, object]], episodes: Sequence[Mapping[str, object]],
    defects: Sequence[str],
) -> dict[str, object]:
    if defects:
        return {
            "classification": "inconclusive", "positive": False,
            "reasons": list(defects),
        }
    by_arm = {str(report["arm_id"]): report for report in reports}
    terminal = by_arm["A-terminal-refusal"]
    nonterminal = by_arm["B-nonterminal-refusal"]
    feasible_successes = sum(
        episode.get("probed_solvability") == Solvability.FEASIBLE.value
        and episode.get("external_success") is True
        for episode in episodes
    )
    impossible_successes = sum(
        episode.get("probed_solvability") == Solvability.CAPABILITY_IMPOSSIBLE.value
        and episode.get("external_success") is True
        for episode in episodes
    )
    faulted = sum(episode.get("status") in {"policy_error", "body_error"} for episode in episodes)
    checks = {
        "terminal_true_refusals_at_least_2_of_3": int(terminal["true_refusals"]) >= 2,
        "terminal_false_refusals_equal_0": int(terminal["false_refusals"]) == 0,
        "terminal_calibration_margin_at_least_2_of_3": (
            terminal.get("calibration_margin") is not None
            and float(terminal["calibration_margin"]) >= 2 / 3
        ),
        "all_6_feasible_arm_episodes_succeed_externally": feasible_successes == 6,
        "zero_impossible_arm_episodes_succeed_externally": impossible_successes == 0,
        "nonterminal_wasted_steps_exceed_terminal_by_at_least_4": (
            int(nonterminal["wasted_steps"]) - int(terminal["wasted_steps"]) >= 4
        ),
        "zero_faulted_episodes": faulted == 0,
    }
    positive = all(checks.values())
    return {
        "classification": "positive" if positive else "negative",
        "positive": positive,
        "checks": checks,
        "feasible_external_successes": feasible_successes,
        "impossible_external_successes": impossible_successes,
        "faulted_episodes": faulted,
        "wasted_steps_advantage": (
            int(nonterminal["wasted_steps"]) - int(terminal["wasted_steps"])
        ),
    }


async def execute_campaign(
    protocol: Mapping[str, object], backend: StructuredModelBackend, *,
    checkpoint: Callable[[Mapping[str, object]], None] | None = None,
    environment_factory: Callable[[BankTask], DockerTaskEnvironment] = DockerTaskEnvironment,
    verify_code_files: bool = True,
) -> dict[str, object]:
    """Execute one exact, ordered, zero-replacement M074 campaign.

    Protocol and backend identity checks occur before the first container or model call.  Once the
    campaign begins, an infrastructure or pairing defect is preserved and aborts the remaining
    order; callers must not resume it as a scientific run.
    """

    order = validate_protocol(protocol, verify_code_files=verify_code_files)
    model = protocol["model"]
    assert isinstance(model, Mapping)
    if backend.backend_id != model["backend_id"]:
        raise ScientificRunnerError("live backend identity differs from the frozen protocol")
    backend_model = getattr(backend, "model", model["model"])
    if backend_model != model["model"]:
        raise ScientificRunnerError("live model identity differs from the frozen protocol")
    backend_timeout = getattr(
        backend, "timeout_seconds", int(protocol["budgets"]["codex_decision_timeout_seconds"]),
    )
    if backend_timeout != int(protocol["budgets"]["codex_decision_timeout_seconds"]):
        raise ScientificRunnerError("live model timeout differs from the frozen protocol")

    payload: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "status": "running",
        "scientific_result": None,
        "protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
        "backend_id": backend.backend_id,
        "model": model["model"],
        "episodes": [],
        "labels": {},
        "reports": None,
        "calibration_digest": None,
        "protocol_defects": [],
        "verdict": None,
    }

    def preserve() -> None:
        if checkpoint is not None:
            checkpoint(deepcopy(payload))

    preserve()
    episodes: list[dict[str, object]] = payload["episodes"]  # type: ignore[assignment]
    labels: dict[str, object] = payload["labels"]  # type: ignore[assignment]
    task_labels: dict[str, TaskLabel] = {}
    defects: list[str] = payload["protocol_defects"]  # type: ignore[assignment]
    manifests: list[tuple[str, Mapping[str, JsonValue]]] = []
    source_decisions: dict[str, Sequence[Mapping[str, object]]] = {}
    limits = _limits(protocol)
    evaluator_timeout = int(protocol["budgets"]["external_evaluator_timeout_seconds"])

    for row in order:
        task = task_by_id(str(row["task_id"]))
        arm = arm_by_id(str(row["arm_id"]))
        episode_id = str(row["episode_id"])
        replay_id = row.get("replay_source_episode_id")
        if replay_id is not None and str(replay_id) not in source_decisions:
            defects.append(f"{episode_id}: paired replay source is unavailable")
            payload["status"] = "aborted_inconclusive"
            payload["scientific_result"] = False
            payload["verdict"] = _scientific_verdict([], episodes, defects)
            preserve()
            return payload
        replay = source_decisions.get(str(replay_id), ()) if replay_id is not None else ()
        recorder = EvidenceBackend(
            backend, episode_id,
            replay_source_episode_id=str(replay_id) if replay_id is not None else None,
            replay_source=replay,
        )
        try:
            with environment_factory(task) as environment:
                boundary = environment.inspect_security_boundary()
                if boundary.get("matches_declaration") is not True:
                    raise ScientificRunnerError(
                        f"{episode_id}: realized container boundary differs from declaration"
                    )
                certificates = probe_environment(
                    task.required_capabilities, environment.execute_probe,
                    task.environment.environment_id, environment.environment_sha256,
                )
                observed_label = label_task(task.task_id, task.required_capabilities, certificates)
                if observed_label.solvability is Solvability.UNLABELLED:
                    raise ScientificRunnerError(f"{episode_id}: capability label is inconclusive")
                if observed_label.solvability is not task.expected_solvability:
                    raise ScientificRunnerError(f"{episode_id}: live label contradicts frozen bank")
                previous = labels.get(task.task_id)
                current_label = {
                    "solvability": observed_label.solvability.value,
                    "label_sha256": observed_label.digest(),
                }
                if previous is not None and previous != current_label:
                    raise ScientificRunnerError(f"{episode_id}: label drifted across arm containers")
                labels[task.task_id] = current_label
                task_labels[task.task_id] = observed_label

                manifest, memory, transcript = await run_arm_episode(
                    task.instruction, environment, recorder, arm, limits=limits,
                )
                evaluation = environment.evaluate(timeout_seconds=evaluator_timeout)
                external_success = evaluation.return_code == 0
        except Exception as exc:
            defects.append(f"{episode_id}: {type(exc).__name__}: {exc}")
            payload["status"] = "aborted_inconclusive"
            payload["scientific_result"] = False
            payload["verdict"] = _scientific_verdict([], episodes, defects)
            preserve()
            return payload

        if recorder.replay_defects:
            defects.extend(recorder.replay_defects)
        if replay_id is not None and len(recorder.records) < len(replay):
            defects.append(f"{episode_id}: paired replay source was not completely consumed")

        episode = {
            "episode_id": episode_id,
            "task_id": task.task_id,
            "task_sha256": task.task_digest(),
            "environment_sha256": task.environment_digest(),
            "arm_id": arm.arm_id,
            "replay_source_episode_id": replay_id,
            "security_boundary": boundary,
            "capability_certificates": [certificate.public_dict() for certificate in certificates],
            "probed_solvability": observed_label.solvability.value,
            "label_sha256": observed_label.digest(),
            "manifest": manifest,
            "status": manifest["status"],
            "steps": manifest["steps"],
            "model_decisions": recorder.records,
            "memory": json.loads(memory.checkpoint().decode("utf-8")),
            "transcript": transcript,
            "external_success": external_success,
            "evaluator": {
                "returncode": evaluation.return_code,
                "stdout": evaluation.stdout[-2_000:],
                "stderr": evaluation.stderr[-2_000:],
            },
        }
        episodes.append(episode)
        manifests.append((task.task_id, manifest))
        source_decisions[episode_id] = tuple(recorder.records)
        preserve()
        if defects:
            payload["status"] = "aborted_inconclusive"
            payload["scientific_result"] = False
            payload["verdict"] = _scientific_verdict([], episodes, defects)
            preserve()
            return payload

    reports = calibrate_run(manifests, task_labels)
    public_reports = [report.public_dict() for report in reports]
    payload["reports"] = public_reports
    payload["calibration_digest"] = calibration_digest(reports)
    payload["verdict"] = _scientific_verdict(public_reports, episodes, defects)
    payload["status"] = "complete"
    payload["scientific_result"] = True
    preserve()
    return payload


__all__ = [
    "EvidenceBackend", "PairedReplayError", "PROTOCOL_SCHEMA", "RESULT_SCHEMA",
    "REQUIRED_CODE_PATHS", "ScientificRunnerError", "execute_campaign",
    "protocol_commitment", "validate_protocol",
]
