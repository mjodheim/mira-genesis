"""Draft M072 ablation arms over the frozen M071 episode loop.

**This apparatus is a draft.  Nothing here is frozen and no result may cite it.**

`mira_core` is left untouched.  The frozen M071 runtime keeps its exact blobs, so arm A can be
shown byte-identical to the composition that earned the recorded external reward instead of being
argued equivalent to a refactored descendant.

The three arms differ only in declared governance flags, so any behavioural difference is
attributable to a field of `ArmSpec` rather than to a second implementation.  Model identity,
budgets, response schema and prompt contract are shared by construction: they are supplied by the
caller and never varied here.
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
    """One declared governance composition.

    Every field is a governance element, never a capability or budget difference.  Falsifier 5 of
    the draft design requires that arms differ in nothing else.
    """

    arm_id: str
    enforce_authorities: bool
    refusal_terminates_episode: bool
    tamper_evident_ledger: bool

    def public_dict(self) -> dict[str, JsonValue]:
        return {
            "arm_id": self.arm_id,
            "enforce_authorities": self.enforce_authorities,
            "refusal_terminates_episode": self.refusal_terminates_episode,
            "tamper_evident_ledger": self.tamper_evident_ledger,
        }


ARM_A_GOVERNED = ArmSpec("A-governed", True, True, True)
ARM_B_RAW = ArmSpec("B-raw", False, False, False)
ARM_C_NO_REFUSAL = ArmSpec("C-governed-no-refusal", True, False, True)
ABLATION_ARMS: tuple[ArmSpec, ...] = (ARM_A_GOVERNED, ARM_B_RAW, ARM_C_NO_REFUSAL)


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

    Arm A reproduces the frozen M071 loop exactly, including every recorded event payload, so its
    ledger digest matches.  Arms that relax a governance element emit their own additional events
    and never alter arm A's recorded shape.

    `granted_authorities` must be declared before a run.  Under the default grant the policy can
    only emit actions whose declared authorities are already held, so the authority gate never
    fires and `enforce_authorities` is inert.  Measuring that dimension requires a narrower grant
    than the action language declares; see the draft design.
    """

    bounded = limits or HarborEpisodeLimits()
    mode = _network_mode(environment)
    if mode != "no-network":
        raise AblationArmError(
            f"M072 arms require Harbor network_mode=no-network, observed {mode!r}"
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
    unenforced_blocks = 0
    executed_commands = 0
    for step in range(1, bounded.max_steps + 1):
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
            steps = step
            break
        decision = safety.decide(action)
        record("action_admission", {
            "step": step, "action_id": action.action_id, "action_kind": action.kind,
            "allowed": decision.allowed, "reason": decision.reason,
            "missing_authorities": list(decision.missing_authorities),
        })
        blocked = not decision.allowed or action.kind != "container_exec"
        if blocked and arm.enforce_authorities:
            status = "safety_refused"
            break
        if blocked:
            unenforced_blocks += 1
            record("authority_not_enforced", {
                "step": step, "arm_id": arm.arm_id, "action_kind": action.kind,
                "allowed": decision.allowed,
            })
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
            steps = step
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
        steps = step
    else:
        record("step_budget_exhausted", {"max_steps": bounded.max_steps})
    record("episode_finished", {
        "status": status, "steps": steps, "agent_claimed_success": False,
    })
    if arm.tamper_evident_ledger:
        memory.verify()
    manifest: dict[str, JsonValue] = {
        "schema": "m072-ablation-arm-manifest-v1",
        "arm": arm.public_dict(),
        "status": status,
        "steps": steps,
        "memory_digest": memory.digest if arm.tamper_evident_ledger else None,
        "audit_record": "hash_chained_ledger" if arm.tamper_evident_ledger else "plain_transcript",
        "network_mode": mode,
        "agent_claimed_success": False,
        "success_decided_externally": True,
        "backend_id": backend.backend_id,
        "refusals": refusals,
        "unenforced_blocked_actions": unenforced_blocks,
        "executed_commands": executed_commands,
    }
    return manifest, memory, transcript


__all__ = [
    "ABLATION_ARMS", "ARM_A_GOVERNED", "ARM_B_RAW", "ARM_C_NO_REFUSAL",
    "AblationArmError", "ArmSpec", "arm_by_id", "run_arm_episode",
]
