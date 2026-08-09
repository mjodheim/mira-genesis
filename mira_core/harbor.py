"""Task-agnostic bridge from Mira's frozen model policy to Harbor environments.

Harbor is an optional evaluation-time dependency, loaded dynamically so the core package remains
dependency-light.  This bridge contains no benchmark identifier, threshold or task-specific rule.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import importlib
import json
from pathlib import Path
import tempfile
from typing import Any

from mira_core.contracts import Goal, JsonValue, Observation
from mira_core.memory import MemoryLedger
from mira_core.model import CodexExecBackend, StructuredModelBackend, StructuredModelPolicy, find_codex_executable
from mira_core.safety import Authority, SafetyPolicy


try:
    _HarborBaseAgent = importlib.import_module("harbor.agents.base").BaseAgent
    _HARBOR_AVAILABLE = True
except ModuleNotFoundError:
    _HARBOR_AVAILABLE = False
    class _HarborBaseAgent:  # type: ignore[no-redef]
        """Import-only fallback; construction still requires Harbor."""


@dataclass(frozen=True)
class HarborEpisodeLimits:
    max_steps: int = 16
    command_timeout_seconds: int = 120
    max_output_chars: int = 65_536

    def __post_init__(self) -> None:
        if min(self.max_steps, self.command_timeout_seconds, self.max_output_chars) < 1:
            raise ValueError("Harbor episode limits must be positive")


def _network_mode(environment: Any) -> str:
    policy = getattr(environment, "network_policy", None)
    mode = getattr(policy, "network_mode", None)
    return str(getattr(mode, "value", mode))


async def run_harbor_episode(
    instruction: str, environment: Any, backend: StructuredModelBackend, *,
    limits: HarborEpisodeLimits | None = None,
) -> tuple[dict[str, JsonValue], MemoryLedger]:
    """Run the frozen structured policy through one already-isolated Harbor body."""

    bounded = limits or HarborEpisodeLimits()
    mode = _network_mode(environment)
    if mode != "no-network":
        raise RuntimeError(
            f"M070 requires Harbor network_mode=no-network, observed {mode!r}"
        )
    policy = StructuredModelPolicy(
        backend, policy_id="m070-frozen-structured-model-policy-v1",
    )
    safety = SafetyPolicy.from_authorities({
        Authority.COMPUTE, Authority.FILESYSTEM_READ, Authority.FILESYSTEM_WRITE,
    })
    memory = MemoryLedger()
    goal = Goal(
        "m070-external-task", instruction,
        {"success_decided_by": "harbor_external_verifier"},
    )
    observation = Observation("harbor:0:reset", {
        "event": "harbor_container_ready",
        "network_mode": mode,
        "success_decided_externally": True,
        "reference_solution_visible": False,
        "verifier_tests_visible": False,
    })
    memory.append("episode_started", {
        "goal_id": goal.goal_id,
        "policy_id": policy.policy_id,
        "body_id": "harbor-external-container-body-v1",
        "initial_observation_id": observation.observation_id,
    })
    status = "step_budget_exhausted"
    steps = 0
    for step in range(1, bounded.max_steps + 1):
        try:
            action = await asyncio.to_thread(
                policy.propose, goal, observation, memory.history(),
            )
        except Exception as exc:  # noqa: BLE001 - backend failure is evidence
            memory.append("policy_error", {
                "step": step, "error_type": type(exc).__name__, "error": str(exc),
            })
            status = "policy_error"
            break
        if action is None:
            memory.append("policy_refused", {
                "step": step, "reason": policy.last_refusal_reason,
            })
            status = "policy_refused"
            break
        if action.kind == "container_submit":
            memory.append("workspace_submitted", {
                "step": step, "agent_claimed_success": False,
            })
            status = "submitted_for_external_evaluation"
            steps = step
            break
        decision = safety.decide(action)
        memory.append("action_admission", {
            "step": step, "action_id": action.action_id, "action_kind": action.kind,
            "allowed": decision.allowed, "reason": decision.reason,
            "missing_authorities": list(decision.missing_authorities),
        })
        if not decision.allowed or action.kind != "container_exec":
            status = "safety_refused"
            break
        script = action.payload.get("script")
        if not isinstance(script, str):
            status = "action_contract_refused"
            break
        try:
            result = await environment.exec(
                script, timeout_sec=bounded.command_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - environment failure is evidence
            memory.append("body_error", {
                "step": step, "error_type": type(exc).__name__, "error": str(exc),
            })
            status = "body_error"
            steps = step
            break
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        combined = stdout + (("\n" + stderr) if stderr else "")
        truncated = len(combined) > bounded.max_output_chars
        combined = combined[:bounded.max_output_chars]
        observation = Observation(f"harbor:{step}:command", {
            "event": "harbor_command_finished",
            "returncode": result.return_code,
            "output": combined,
            "output_truncated": truncated,
        })
        memory.append("observation", {
            "step": step, "observation_id": observation.observation_id,
            "returncode": result.return_code, "output_truncated": truncated,
        })
        steps = step
    else:
        memory.append("step_budget_exhausted", {"max_steps": bounded.max_steps})
    memory.append("episode_finished", {
        "status": status, "steps": steps, "agent_claimed_success": False,
    })
    memory.verify()
    manifest: dict[str, JsonValue] = {
        "schema": "m070-harbor-agent-manifest-v1",
        "status": status,
        "steps": steps,
        "memory_digest": memory.digest,
        "network_mode": mode,
        "agent_claimed_success": False,
        "success_decided_externally": True,
        "backend_id": backend.backend_id,
    }
    return manifest, memory


class HarborMiraAgent(_HarborBaseAgent):
    """Harbor custom-agent entry point for the frozen M070 structured policy."""

    SUPPORTS_ATIF = False
    SUPPORTS_RESUME = False
    SUPPORTS_WINDOWS = False

    def __init__(
        self, logs_dir: Path, model_name: str | None = None, *, max_steps: int = 16,
        command_timeout_seconds: int = 120, max_output_chars: int = 65_536,
        codex_timeout_seconds: float = 180.0, **kwargs: Any,
    ) -> None:
        if not _HARBOR_AVAILABLE:
            raise RuntimeError("HarborMiraAgent requires the optional Harbor package")
        super().__init__(logs_dir=logs_dir, model_name=model_name, **kwargs)
        self._limits = HarborEpisodeLimits(
            max_steps=max_steps, command_timeout_seconds=command_timeout_seconds,
            max_output_chars=max_output_chars,
        )
        self._codex_timeout_seconds = codex_timeout_seconds

    @staticmethod
    def name() -> str:
        return "mira-m070"

    def version(self) -> str:
        return "41ebe791605f55e7a44df8f0939d730139cf219a"

    async def setup(self, environment: Any) -> None:
        # Harbor performs setup against the task's baseline policy, then applies the explicit
        # agent-phase override immediately around run().  This adapter has no setup action.
        return None

    async def run(self, instruction: str, environment: Any, context: Any) -> None:
        if not self.model_name:
            raise ValueError("M070 Harbor adapter requires an explicit model name")
        executable = find_codex_executable()
        if executable is None:
            raise RuntimeError("M070 Harbor adapter cannot find the official Codex CLI")
        model = self.model_name.split("/", 1)[-1]
        with tempfile.TemporaryDirectory(prefix="mira-m070-neutral-") as directory:
            backend = CodexExecBackend(
                executable, Path(directory), model,
                timeout_seconds=self._codex_timeout_seconds,
            )
            manifest, memory = await run_harbor_episode(
                instruction, environment, backend, limits=self._limits,
            )
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "mira_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8",
        )
        (self.logs_dir / "mira_memory.json").write_bytes(memory.checkpoint())
        context.metadata = dict(manifest)
