"""Public, contaminated model-development comparison for M075.

This runner compares the existing structured request with the same request augmented by M075's
epistemic state.  Independent model samples and authored public tasks make every outcome
development-only; no result from this module may support H21.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Callable, Mapping

from metamorphosis.m074_ablation_arms import ArmSpec, run_arm_episode
from metamorphosis.m074_calibration_bridge import calibrate_run
from metamorphosis.m074_docker_environment import DockerTaskEnvironment
from metamorphosis.m074_scientific_runner import (
    EvidenceBackend, portable_file_sha256, protocol_commitment,
)
from metamorphosis.m075_development_bank import TASKS, BankTask, task_by_id, validate_development_bank
from metamorphosis.m075_epistemic_context import EpistemicContextBackend
from mira_core.calibration import Solvability, TaskLabel, calibration_digest
from mira_core.contracts import JsonValue
from mira_core.harbor import HarborEpisodeLimits
from mira_core.model import StructuredModelBackend
from mira_core.probing import label_task, probe_environment


PROTOCOL_SCHEMA = "m075-public-model-development-protocol-v1"
RESULT_SCHEMA = "m075-public-model-development-result-v1"
ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CODE_PATHS: tuple[str, ...] = (
    "metamorphosis/m074_ablation_arms.py",
    "metamorphosis/m074_calibration_bridge.py",
    "metamorphosis/m074_docker_environment.py",
    "metamorphosis/m074_scientific_runner.py",
    "metamorphosis/m075_development_bank.py",
    "metamorphosis/m075_epistemic_context.py",
    "metamorphosis/m075_model_development_runner.py",
    "mira_core/calibration.py",
    "mira_core/contracts.py",
    "mira_core/harbor.py",
    "mira_core/memory.py",
    "mira_core/model.py",
    "mira_core/probing.py",
    "mira_core/process.py",
    "mira_core/safety.py",
    "scripts/run_m075_model_development.py",
)

BASELINE = ArmSpec("baseline-structured-request", True)
EPISTEMIC = ArmSpec("epistemic-context-request", True)
CONDITIONS = (BASELINE, EPISTEMIC)


class M075ModelDevelopmentError(RuntimeError):
    """Raised when a public model-development run differs from its committed contract."""


def _validate_code_bindings(protocol: Mapping[str, object], root: Path) -> None:
    raw = protocol.get("code_sha256")
    if not isinstance(raw, Mapping) or set(raw) != set(REQUIRED_CODE_PATHS):
        raise M075ModelDevelopmentError("M075 development code bindings lack exact coverage")
    for relative, expected in raw.items():
        if not isinstance(relative, str) or not isinstance(expected, str) or len(expected) != 64:
            raise M075ModelDevelopmentError("M075 development code binding is malformed")
        path = (root / relative).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise M075ModelDevelopmentError("M075 development code binding escaped the repository") from exc
        if not path.is_file() or portable_file_sha256(path) != expected:
            raise M075ModelDevelopmentError(f"M075 development code drifted: {relative}")


def _request_scope_defects(
    episode_id: str, condition_id: str, records: list[dict[str, object]],
    states: list[dict[str, JsonValue]] | None,
) -> list[str]:
    """Prove that the recorded model path respected the declared information boundary."""

    defects: list[str] = []
    if states is not None and len(states) != len(records):
        defects.append(f"{episode_id}: epistemic state does not cover every decision")
    prohibited_keys = {
        "capability_certificates", "environment_sha256", "evaluator", "external_success",
        "expected_solvability", "label_sha256", "probed_solvability", "solve_script",
    }
    for index, record in enumerate(records):
        request = record.get("request")
        raw_input = request.get("input_json") if isinstance(request, Mapping) else None
        try:
            payload = json.loads(raw_input) if isinstance(raw_input, str) else None
        except json.JSONDecodeError:
            payload = None
        if not isinstance(payload, dict):
            defects.append(f"{episode_id}: decision {index + 1} has malformed recorded input")
            continue
        leaked = sorted(prohibited_keys.intersection(payload))
        if leaked:
            defects.append(f"{episode_id}: decision {index + 1} leaked hidden keys {leaked}")
        observed_state = payload.get("epistemic_state")
        if condition_id == EPISTEMIC.arm_id:
            expected_state = states[index] if states is not None and index < len(states) else None
            if observed_state != expected_state:
                defects.append(f"{episode_id}: decision {index + 1} epistemic state drifted")
        elif "epistemic_state" in payload:
            defects.append(f"{episode_id}: baseline decision {index + 1} received epistemic state")
        if record.get("origin") != "live_model" or record.get("status") != "completed":
            defects.append(f"{episode_id}: decision {index + 1} is not a completed live sample")
    return defects


def validate_protocol(
    protocol: Mapping[str, object], *, root: Path = ROOT,
) -> tuple[Mapping[str, object], ...]:
    validate_development_bank()
    if (
        protocol.get("schema") != PROTOCOL_SCHEMA
        or protocol.get("status") != "committed_before_public_model_development"
        or protocol.get("scientific_result") is not False
        or protocol.get("public_contaminated_development") is not True
    ):
        raise M075ModelDevelopmentError("M075 model-development scope is malformed")
    if protocol.get("protocol_commitment_sha256") != protocol_commitment(protocol):
        raise M075ModelDevelopmentError("M075 model-development commitment drifted")
    apparatus_commit = protocol.get("apparatus_commit")
    if not isinstance(apparatus_commit, str) or len(apparatus_commit) != 40:
        raise M075ModelDevelopmentError("M075 model-development apparatus commit is malformed")
    _validate_code_bindings(protocol, root)
    model = protocol.get("model")
    if not isinstance(model, Mapping) or dict(model) != {
        "backend_id": "openai-codex-exec-v1",
        "model": "gpt-5.6-sol",
        "codex_cli_version": "codex-cli 0.147.0",
    }:
        raise M075ModelDevelopmentError("M075 model-development identity drifted")
    budgets = protocol.get("budgets")
    if not isinstance(budgets, Mapping) or dict(budgets) != {
        "max_agent_steps": 4,
        "command_timeout_seconds": 30,
        "command_output_chars": 65_536,
        "codex_decision_timeout_seconds": 180,
        "external_evaluator_timeout_seconds": 30,
    }:
        raise M075ModelDevelopmentError("M075 model-development budgets drifted")
    if protocol.get("conditions") != [condition.public_dict() for condition in CONDITIONS]:
        raise M075ModelDevelopmentError("M075 development conditions drifted")
    expected_tasks = [
        {
            "task_id": task.task_id,
            "task_sha256": task.task_digest(),
            "environment_sha256": task.environment_digest(),
        }
        for task in TASKS
    ]
    if protocol.get("tasks") != expected_tasks:
        raise M075ModelDevelopmentError("M075 public development task bindings drifted")
    attempt = protocol.get("attempt_policy")
    if not isinstance(attempt, Mapping) or dict(attempt) != {
        "attempts_per_condition_task": 1,
        "concurrency": 1,
        "replacement_permitted": False,
        "development_retry_permitted": False,
        "independent_model_samples_make_comparison_noncausal": True,
    }:
        raise M075ModelDevelopmentError("M075 public development attempt policy drifted")
    if protocol.get("information_boundary") != {
        "task_instruction_visible_to_model": True,
        "action_observations_visible_to_model": True,
        "epistemic_self_evidence_visible_only_in_context_condition": True,
        "expected_or_probed_solvability_visible_to_model": False,
        "capability_certificates_visible_to_model": False,
        "solve_script_visible_to_model": False,
        "evaluator_or_outcome_visible_to_model": False,
        "condition_identity_visible_to_model": False,
    }:
        raise M075ModelDevelopmentError("M075 public development information boundary drifted")
    if protocol.get("claim_boundary") != {
        "agi": False,
        "scientific_evidence": False,
        "causal_comparison": False,
        "public_project_authored_bank": True,
        "private_cross_domain_transfer": False,
        "m074_tasks_reused": False,
    }:
        raise M075ModelDevelopmentError("M075 public development claim boundary drifted")
    runtime = protocol.get("runtime")
    if not isinstance(runtime, Mapping) or set(runtime) != {
        "docker_server_version", "host_system", "python_version",
    } or any(not isinstance(value, str) or not value for value in runtime.values()):
        raise M075ModelDevelopmentError("M075 public development runtime identity is malformed")
    if protocol.get("raw_evidence_boundary") != (
        "Preserves each complete ModelRequest and the structured JSON mapping returned by "
        "CodexExecBackend; provider transport envelopes, token accounting, sampling seed and "
        "pre-parse output whitespace are unavailable."
    ):
        raise M075ModelDevelopmentError("M075 public development evidence boundary drifted")
    order = protocol.get("episode_order")
    if not isinstance(order, list) or len(order) != 12:
        raise M075ModelDevelopmentError("M075 public development order lacks exact coverage")
    expected_order = []
    for task in TASKS:
        for condition in CONDITIONS:
            expected_order.append({
                "episode_id": f"{len(expected_order) + 1:02d}-{task.task_id}-{condition.arm_id}",
                "task_id": task.task_id,
                "condition_id": condition.arm_id,
            })
    if order != expected_order:
        raise M075ModelDevelopmentError("M075 public development episode order drifted")
    return tuple(order)


async def execute_public_development(
    protocol: Mapping[str, object], backend: StructuredModelBackend, *,
    checkpoint: Callable[[Mapping[str, object]], None] | None = None,
    environment_factory: Callable[[BankTask], DockerTaskEnvironment] = DockerTaskEnvironment,
) -> dict[str, object]:
    order = validate_protocol(protocol)
    if backend.backend_id != "openai-codex-exec-v1" or getattr(
        backend, "model", "gpt-5.6-sol",
    ) != "gpt-5.6-sol":
        raise M075ModelDevelopmentError("live development backend identity drifted")
    limits = HarborEpisodeLimits(max_steps=4, command_timeout_seconds=30, max_output_chars=65_536)
    payload: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "status": "running",
        "scientific_result": False,
        "public_contaminated_development": True,
        "independent_model_samples": True,
        "protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
        "episodes": [],
        "labels": {},
        "reports": None,
        "calibration_digest": None,
        "development_defects": [],
    }

    def preserve() -> None:
        if checkpoint is not None:
            checkpoint(deepcopy(payload))

    preserve()
    episodes: list[dict[str, object]] = payload["episodes"]  # type: ignore[assignment]
    labels: dict[str, object] = payload["labels"]  # type: ignore[assignment]
    task_labels: dict[str, TaskLabel] = {}
    defects: list[str] = payload["development_defects"]  # type: ignore[assignment]
    manifests = []

    for row in order:
        task = task_by_id(str(row["task_id"]))
        condition_id = str(row["condition_id"])
        condition = next(value for value in CONDITIONS if value.arm_id == condition_id)
        episode_id = str(row["episode_id"])
        with environment_factory(task) as environment:
            boundary = environment.inspect_security_boundary()
            if boundary.get("matches_declaration") is not True:
                defects.append(f"{episode_id}: realized boundary mismatch")
            certificates = probe_environment(
                task.required_capabilities, environment.execute_probe,
                task.environment.environment_id, environment.environment_sha256,
            )
            label = label_task(task.task_id, task.required_capabilities, certificates)
            if label.solvability is not task.expected_solvability:
                defects.append(f"{episode_id}: public development label mismatch")
            public_label = {
                "solvability": label.solvability.value,
                "label_sha256": label.digest(),
            }
            if task.task_id in labels and labels[task.task_id] != public_label:
                defects.append(f"{episode_id}: label drifted across development conditions")
            labels[task.task_id] = public_label
            task_labels[task.task_id] = label

            recorder = EvidenceBackend(backend, episode_id)
            epistemic: EpistemicContextBackend | None = None
            policy_backend: StructuredModelBackend = recorder
            if condition is EPISTEMIC:
                epistemic = EpistemicContextBackend(recorder, max_steps=limits.max_steps)
                policy_backend = epistemic
            manifest, memory, transcript = await run_arm_episode(
                task.instruction, environment, policy_backend, condition, limits=limits,
                policy_id=(
                    "m075-public-baseline-policy-v1" if condition is BASELINE
                    else "m075-public-epistemic-policy-v1"
                ),
                goal_id="m075-public-model-development-task",
                body_id="m075-public-development-container-v1",
            )
            evaluation = environment.evaluate(timeout_seconds=30)
            external_success = evaluation.return_code == 0

        if recorder.replay_defects:
            defects.extend(recorder.replay_defects)
        if len(recorder.records) != manifest["steps"]:
            defects.append(f"{episode_id}: recorded decisions do not equal policy steps")
        if manifest["status"] not in {
            "submitted_for_external_evaluation", "policy_refused", "step_budget_exhausted",
        }:
            defects.append(f"{episode_id}: policy ended in {manifest['status']}")
        defects.extend(_request_scope_defects(
            episode_id, condition_id, recorder.records,
            epistemic.states if epistemic is not None else None,
        ))
        episodes.append({
            "episode_id": episode_id,
            "task_id": task.task_id,
            "task_sha256": task.task_digest(),
            "environment_sha256": task.environment_digest(),
            "condition_id": condition_id,
            "security_boundary": boundary,
            "capability_certificates": [certificate.public_dict() for certificate in certificates],
            "probed_solvability": label.solvability.value,
            "label_sha256": label.digest(),
            "manifest": manifest,
            "status": manifest["status"],
            "steps": manifest["steps"],
            "model_decisions": recorder.records,
            "epistemic_states": epistemic.states if epistemic is not None else None,
            "memory": json.loads(memory.checkpoint().decode("utf-8")),
            "transcript": transcript,
            "external_success": external_success,
            "evaluator": {
                "returncode": evaluation.return_code,
                "stdout": evaluation.stdout[-2_000:],
                "stderr": evaluation.stderr[-2_000:],
            },
        })
        manifests.append((task.task_id, manifest))
        preserve()

    reports = calibrate_run(manifests, task_labels)
    payload["reports"] = [report.public_dict() for report in reports]
    payload["calibration_digest"] = calibration_digest(reports)
    payload["status"] = "development_complete" if not defects else "development_defective"
    payload["live_model_decisions"] = sum(
        len(episode["model_decisions"]) for episode in episodes
    )
    preserve()
    return payload


__all__ = [
    "BASELINE", "CONDITIONS", "EPISTEMIC", "M075ModelDevelopmentError", "PROTOCOL_SCHEMA",
    "REQUIRED_CODE_PATHS", "RESULT_SCHEMA", "execute_public_development", "validate_protocol",
]
