"""Draft M074 ablation arms derived from the M071 episode contract.

**This apparatus is a draft.  Nothing here is frozen and no result may cite it.**

The frozen M071 runtime keeps its exact blobs. M074 is a separately named descendant and does not
claim byte identity: it records every attempted policy step, including terminal refusals and
governance halts, which corrects an unsuitable zero-step accounting inherited from M071.

The two arms differ in one field only: whether an explicit policy refusal terminates the episode.
Authority admission, tamper-evident audit, model identity, budgets, response schema and prompt
contract remain identical. M072 already isolates authority and audit mechanisms; mixing those
dimensions into M074 would confound refusal calibration rather than strengthen it.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping

from mira_core.contracts import Goal, JsonValue, Observation
from mira_core.harbor import HarborEpisodeLimits, M071_POLICY_ID, _network_mode
from mira_core.memory import MemoryLedger
from mira_core.model import StructuredModelBackend, StructuredModelPolicy
from mira_core.safety import Authority, SafetyPolicy


DEFAULT_BODY_ID = "harbor-external-container-body-v1"
DEFAULT_GOAL_ID = "m071-external-task"


class AblationArmError(RuntimeError):
    """Raised when an arm is asked to run outside its declared conditions."""


@dataclass(frozen=True)
class ArmSpec:
    """One refusal-termination condition over otherwise identical governance."""

    arm_id: str
    refusal_terminates_episode: bool

    def public_dict(self) -> dict[str, JsonValue]:
        return {
            "arm_id": self.arm_id,
            "refusal_terminates_episode": self.refusal_terminates_episode,
        }


ARM_A_TERMINAL_REFUSAL = ArmSpec("A-terminal-refusal", True)
ARM_B_NONTERMINAL_REFUSAL = ArmSpec("B-nonterminal-refusal", False)
ABLATION_ARMS: tuple[ArmSpec, ...] = (
    ARM_A_TERMINAL_REFUSAL, ARM_B_NONTERMINAL_REFUSAL,
)


def arm_by_id(arm_id: str) -> ArmSpec:
    arm = next((candidate for candidate in ABLATION_ARMS if candidate.arm_id == arm_id), None)
    if arm is None:
        raise AblationArmError(f"unknown ablation arm {arm_id!r}")
    return arm


DEFAULT_GRANTED_AUTHORITIES: frozenset[Authority] = frozenset({
    Authority.COMPUTE, Authority.FILESYSTEM_READ, Authority.FILESYSTEM_WRITE,
})


async def run_arm_episode(
    instruction: str, environment: Any, backend: StructuredModelBackend, arm: ArmSpec, *,
    limits: HarborEpisodeLimits | None = None, policy_id: str = M071_POLICY_ID,
    goal_id: str = DEFAULT_GOAL_ID, body_id: str = DEFAULT_BODY_ID,
    granted_authorities: frozenset[Authority] = DEFAULT_GRANTED_AUTHORITIES,
) -> tuple[dict[str, JsonValue], MemoryLedger, list[dict[str, JsonValue]]]:
    """Run one episode under a declared arm.

    All arms share one implementation and differ only through ``ArmSpec``. M074 does not modify or
    reinterpret any frozen M071 artifact.

    `granted_authorities` must be declared before a run. Both arms enforce the same immutable
    authority gate and preserve the same hash-chained audit record.
    """

    bounded = limits or HarborEpisodeLimits()
    mode = _network_mode(environment)
    if mode != "no-network":
        raise AblationArmError(
            f"M074 arms require Harbor network_mode=no-network, observed {mode!r}"
        )
    policy = StructuredModelPolicy(backend, policy_id=policy_id)
    safety = SafetyPolicy.from_authorities(set(granted_authorities))
    memory = MemoryLedger()
    transcript: list[dict[str, JsonValue]] = []

    def record(kind: str, payload: Mapping[str, JsonValue]) -> None:
        memory.append(kind, payload)
        transcript.append({"kind": kind, **dict(payload)})

    goal = Goal(
        goal_id, instruction, {"success_decided_by": "harbor_external_verifier"},
    )
    observation = Observation("harbor:0:reset", {
        "event": "harbor_container_ready",
        "network_mode": mode,
        "success_decided_externally": True,
        "reference_solution_visible": False,
        "verifier_tests_visible": False,
    })
    record("episode_started", {
        "goal_id": goal.goal_id,
        "policy_id": policy.policy_id,
        "body_id": body_id,
        "initial_observation_id": observation.observation_id,
    })
    status = "step_budget_exhausted"
    steps = 0
    refusals = 0
    executed_commands = 0
    for step in range(1, bounded.max_steps + 1):
        # A policy proposal consumes one bounded step even when it refuses or governance stops the
        # action. Without this assignment, those terminal paths misleadingly report zero effort.
        steps = step
        try:
            action = await asyncio.to_thread(
                policy.propose, goal, observation, memory.history(),
            )
        except Exception as exc:  # noqa: BLE001 - backend failure is evidence
            record("policy_error", {
                "step": step, "error_type": type(exc).__name__, "error": str(exc),
            })
            status = "policy_error"
            break
        if action is None:
            refusals += 1
            record("policy_refused", {"step": step, "reason": policy.last_refusal_reason})
            if arm.refusal_terminates_episode:
                status = "policy_refused"
                break
            record("refusal_not_terminal", {"step": step, "arm_id": arm.arm_id})
            continue
        if action.kind == "container_submit":
            record("workspace_submitted", {"step": step, "agent_claimed_success": False})
            status = "submitted_for_external_evaluation"
            break
        decision = safety.decide(action)
        record("action_admission", {
            "step": step, "action_id": action.action_id, "action_kind": action.kind,
            "allowed": decision.allowed, "reason": decision.reason,
            "missing_authorities": list(decision.missing_authorities),
        })
        blocked = not decision.allowed or action.kind != "container_exec"
        if blocked:
            status = "safety_refused"
            break
        if action.kind != "container_exec":
            status = "unsupported_action_kind"
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
            record("body_error", {
                "step": step, "error_type": type(exc).__name__, "error": str(exc),
            })
            status = "body_error"
            break
        executed_commands += 1
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
        record("observation", {
            "step": step, "observation_id": observation.observation_id,
            "returncode": result.return_code, "output_truncated": truncated,
        })
    else:
        record("step_budget_exhausted", {"max_steps": bounded.max_steps})
    record("episode_finished", {
        "status": status, "steps": steps, "agent_claimed_success": False,
    })
    memory.verify()
    manifest: dict[str, JsonValue] = {
        "schema": "m074-refusal-arm-manifest-v2",
        "arm": arm.public_dict(),
        "status": status,
        "steps": steps,
        "memory_digest": memory.digest,
        "audit_record": "hash_chained_ledger",
        "network_mode": mode,
        "agent_claimed_success": False,
        "success_decided_externally": True,
        "backend_id": backend.backend_id,
        "refusals": refusals,
        "executed_commands": executed_commands,
    }
    return manifest, memory, transcript


__all__ = [
    "ABLATION_ARMS", "ARM_A_TERMINAL_REFUSAL", "ARM_B_NONTERMINAL_REFUSAL",
    "AblationArmError", "ArmSpec", "arm_by_id", "run_arm_episode",
]
