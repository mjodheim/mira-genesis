"""Provider-neutral structured model policy for bounded Mira bodies.

The model never receives host authority.  It sees a JSON projection of the current goal and
observation and may only return one schema-validated action, an explicit refusal or a submission.
Concrete backends are responsible only for producing the structured decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Mapping, Protocol, Sequence

from mira_core.contracts import Action, Goal, JsonValue, Observation


class ModelBackendError(RuntimeError):
    """Raised when a model backend cannot produce a trustworthy structured decision."""


@dataclass(frozen=True)
class ModelRequest:
    """Canonical provider-neutral request passed to a structured model backend."""

    system_instruction: str
    input_json: str
    output_schema: Mapping[str, JsonValue]


class StructuredModelBackend(Protocol):
    @property
    def backend_id(self) -> str: ...

    def complete(self, request: ModelRequest) -> Mapping[str, JsonValue]: ...


@dataclass(frozen=True)
class ModelPolicyLimits:
    max_instruction_chars: int = 16_384
    max_observation_chars: int = 65_536
    max_history_events: int = 16
    max_script_chars: int = 16_384
    max_refusal_chars: int = 1_024

    def __post_init__(self) -> None:
        if min(
            self.max_instruction_chars, self.max_observation_chars, self.max_history_events,
            self.max_script_chars, self.max_refusal_chars,
        ) < 1:
            raise ValueError("model policy limits must be positive")


DECISION_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["act", "finish", "refuse"]},
        "script": {"type": ["string", "null"]},
        "reason": {"type": ["string", "null"]},
    },
    "required": ["decision", "script", "reason"],
    "additionalProperties": False,
}


class StructuredModelPolicy:
    """Translate one strict model decision into the fixed container action language."""

    EXEC_AUTHORITIES = ("compute", "filesystem_read", "filesystem_write")

    def __init__(
        self, backend: StructuredModelBackend, *, policy_id: str = "structured-model-policy-v1",
        limits: ModelPolicyLimits | None = None,
    ) -> None:
        if not policy_id:
            raise ValueError("model policy requires an identifier")
        self.backend = backend
        self.policy_id = policy_id
        self.limits = limits or ModelPolicyLimits()
        self._decision_index = 0
        self.last_refusal_reason: str | None = None

    def propose(
        self, goal: Goal, observation: Observation,
        history: Sequence[Mapping[str, JsonValue]],
    ) -> Action | None:
        request = self._request(goal, observation, history)
        raw = self.backend.complete(request)
        decision, script, reason = self._validate_decision(raw)
        self._decision_index += 1
        if decision == "refuse":
            self.last_refusal_reason = reason
            return None
        if decision == "finish":
            return Action(
                f"model-{self._decision_index}-submit", "container_submit", {}, (),
            )
        return Action(
            f"model-{self._decision_index}-exec", "container_exec", {"script": script},
            self.EXEC_AUTHORITIES,
        )

    def _request(
        self, goal: Goal, observation: Observation,
        history: Sequence[Mapping[str, JsonValue]],
    ) -> ModelRequest:
        if len(goal.instruction) > self.limits.max_instruction_chars:
            raise ModelBackendError("goal instruction exceeds the model policy limit")
        observation_json = json.dumps(
            observation.state, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        if len(observation_json) > self.limits.max_observation_chars:
            raise ModelBackendError("observation exceeds the model policy limit")
        payload = {
            "goal": {
                "goal_id": goal.goal_id,
                "instruction": goal.instruction,
                "success_criteria": goal.success_criteria,
            },
            "observation": {
                "observation_id": observation.observation_id,
                "state": observation.state,
                "terminal": observation.terminal,
                "success": observation.success,
                "error": observation.error,
            },
            "recent_evidence": list(history[-self.limits.max_history_events:]),
            "allowed_decisions": {
                "act": "run one shell script inside the isolated task container",
                "finish": "stop acting and submit the workspace for external evaluation",
                "refuse": "stop without claiming success when the task is unsafe or unsupported",
            },
        }
        return ModelRequest(
            system_instruction=(
                "You are the decision component of a bounded software agent. You have no host, "
                "network, credential, repository or deployment authority. Return exactly one JSON "
                "object matching the supplied schema. Set every unused field to null: act requires "
                "a non-empty script and reason=null; finish requires script=null and reason=null; "
                "refuse requires script=null and a non-empty reason. Use finish only when the "
                "workspace should be externally evaluated. Never claim that your own output proves "
                "success."
            ),
            input_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
            output_schema=DECISION_SCHEMA,
        )

    def _validate_decision(
        self, raw: Mapping[str, JsonValue],
    ) -> tuple[str, str | None, str | None]:
        if not isinstance(raw, Mapping) or set(raw) != {"decision", "script", "reason"}:
            raise ModelBackendError("model decision does not match the closed response schema")
        decision = raw.get("decision")
        script = raw.get("script")
        reason = raw.get("reason")
        if decision not in {"act", "finish", "refuse"}:
            raise ModelBackendError("model returned an unknown decision")
        if script is not None and not isinstance(script, str):
            raise ModelBackendError("model script must be a string or null")
        if reason is not None and not isinstance(reason, str):
            raise ModelBackendError("model reason must be a string or null")
        if decision == "act":
            if not script or reason is not None:
                raise ModelBackendError("act requires a script and forbids a reason")
            if "\0" in script or len(script) > self.limits.max_script_chars:
                raise ModelBackendError("model script violates the bounded action contract")
        elif decision == "finish":
            if script is not None or reason is not None:
                raise ModelBackendError("finish forbids script and reason fields")
        else:
            if script is not None or not reason:
                raise ModelBackendError("refuse requires a reason and forbids a script")
            if "\0" in reason or len(reason) > self.limits.max_refusal_chars:
                raise ModelBackendError("model refusal violates the bounded response contract")
        return decision, script, reason


@dataclass(frozen=True)
class CodexExecBackend:
    """Use the official Codex CLI as a schema-constrained, read-only decision backend."""

    executable: Path
    neutral_workspace: Path
    model: str
    timeout_seconds: float = 180.0
    backend_id: str = "openai-codex-exec-v1"

    def __post_init__(self) -> None:
        executable = Path(self.executable)
        workspace = Path(self.neutral_workspace)
        if not executable.is_absolute() or not executable.exists():
            raise ModelBackendError("Codex backend requires an existing absolute executable")
        if not workspace.exists() or not workspace.is_dir():
            raise ModelBackendError("Codex backend requires an existing neutral workspace")
        if not self.model or self.timeout_seconds <= 0:
            raise ModelBackendError("Codex backend model and timeout must be explicit")

    def complete(self, request: ModelRequest) -> Mapping[str, JsonValue]:
        prompt = f"{request.system_instruction}\n\nINPUT_JSON\n{request.input_json}\n"
        with tempfile.TemporaryDirectory(prefix="mira-codex-output-") as raw_temp:
            temp = Path(raw_temp)
            schema_path = temp / "decision.schema.json"
            output_path = temp / "decision.json"
            schema_path.write_text(
                json.dumps(request.output_schema, sort_keys=True), encoding="utf-8",
            )
            argv = [
                str(self.executable), "exec", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--skip-git-repo-check", "--sandbox", "read-only",
                "--model", self.model, "--cd", str(Path(self.neutral_workspace).resolve()),
                "--output-schema", str(schema_path), "--output-last-message", str(output_path), "-",
            ]
            try:
                completed = subprocess.run(
                    argv, input=prompt, text=True, capture_output=True,
                    timeout=self.timeout_seconds, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ModelBackendError("Codex decision exceeded its time budget") from exc
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout)[-2_000:]
                raise ModelBackendError(
                    f"Codex decision failed with exit code {completed.returncode}: {detail}"
                )
            if not output_path.exists():
                raise ModelBackendError("Codex decision did not produce its declared output")
            try:
                value = json.loads(output_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ModelBackendError("Codex decision output is not valid JSON") from exc
            if not isinstance(value, dict):
                raise ModelBackendError("Codex decision output must be a JSON object")
            return value


def find_codex_executable() -> Path | None:
    """Return a separately installed Codex launcher when one is available on PATH."""

    value = shutil.which("codex.cmd" if os.name == "nt" else "codex")
    return Path(value).resolve() if value else None
