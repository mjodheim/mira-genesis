"""Bounded, auditable perception-action loop shared by future Mira bodies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from mira_core.contracts import AuthorityAwareBody, Body, Goal, JsonValue, Observation, Policy
from mira_core.memory import MemoryLedger
from mira_core.safety import SafetyPolicy


@dataclass(frozen=True)
class AgentResult:
    status: str
    steps: int
    final_observation: Observation
    memory_digest: str
    policy_id: str
    body_id: str

    @property
    def succeeded(self) -> bool:
        return self.status == "completed" and self.final_observation.success


class MiraAgent:
    def __init__(
        self, policy: Policy, body: Body, *, safety: SafetyPolicy | None = None,
        memory: MemoryLedger | None = None, max_steps: int = 64,
    ) -> None:
        if max_steps < 1:
            raise ValueError("Mira max_steps must be positive")
        if not isinstance(body, Body) or not isinstance(policy, Policy):
            raise TypeError("Mira requires objects satisfying the Body and Policy protocols")
        self.policy = policy
        self.body = body
        self.safety = safety or SafetyPolicy()
        self.memory = memory or MemoryLedger()
        self.max_steps = max_steps

    def run(self, goal: Goal) -> AgentResult:
        observation = self.body.reset(goal)
        self.memory.append("episode_started", {
            "goal_id": goal.goal_id,
            "policy_id": self.policy.policy_id,
            "body_id": self.body.body_id,
            "initial_observation_id": observation.observation_id,
        })
        if observation.terminal:
            status = "completed" if observation.success else "body_stopped"
            return self._finish(status, 0, observation)

        for step in range(1, self.max_steps + 1):
            action = self.policy.propose(goal, observation, self.memory.history())
            if action is None:
                self.memory.append("policy_refused", {
                    "step": step,
                    "observation_id": observation.observation_id,
                })
                return self._finish("policy_refused", step - 1, observation)
            if isinstance(self.body, AuthorityAwareBody):
                try:
                    body_required = tuple(self.body.required_authorities(action))
                except Exception as exc:  # noqa: BLE001 - broken authority contracts fail closed
                    self.memory.append("body_contract_error", {
                        "step": step,
                        "action_id": action.action_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    })
                    failed = Observation(
                        f"body-contract-error-{step}", {"step": step}, terminal=True,
                        success=False, error=f"{type(exc).__name__}: {exc}",
                    )
                    return self._finish("body_contract_error", step - 1, failed)
                missing_declarations = tuple(sorted(
                    set(body_required) - set(action.required_authorities)
                ))
                if missing_declarations:
                    self.memory.append("action_contract_refused", {
                        "step": step,
                        "action_id": action.action_id,
                        "action_kind": action.kind,
                        "missing_authority_declarations": list(missing_declarations),
                    })
                    failed = Observation(
                        f"action-contract-refusal-{step}", {
                            "step": step,
                            "missing_authority_declarations": list(missing_declarations),
                        }, terminal=True, success=False,
                        error="action omitted an authority required by the body contract",
                    )
                    return self._finish("action_contract_refused", step - 1, failed)
            decision = self.safety.decide(action)
            self.memory.append("action_admission", {
                "step": step,
                "action_id": action.action_id,
                "action_kind": action.kind,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "human_release_required": decision.human_release_required,
                "missing_authorities": list(decision.missing_authorities),
            })
            if not decision.allowed:
                return self._finish("safety_refused", step - 1, observation)
            try:
                next_observation = self.body.act(action)
            except Exception as exc:  # noqa: BLE001 - body failure is evidence, never hidden
                self.memory.append("body_error", {
                    "step": step,
                    "action_id": action.action_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
                failed = Observation(
                    f"body-error-{step}", {"step": step}, terminal=True, success=False,
                    error=f"{type(exc).__name__}: {exc}",
                )
                return self._finish("body_error", step, failed)
            observation = next_observation
            self.memory.append("observation", {
                "step": step,
                "observation_id": observation.observation_id,
                "terminal": observation.terminal,
                "success": observation.success,
                "error": observation.error,
            })
            if observation.terminal:
                status = "completed" if observation.success else "body_stopped"
                return self._finish(status, step, observation)

        self.memory.append("step_budget_exhausted", {"max_steps": self.max_steps})
        return self._finish("step_budget_exhausted", self.max_steps, observation)

    def _finish(self, status: str, steps: int, observation: Observation) -> AgentResult:
        payload: Mapping[str, JsonValue] = {
            "status": status,
            "steps": steps,
            "final_observation_id": observation.observation_id,
            "success": observation.success,
        }
        self.memory.append("episode_finished", payload)
        return AgentResult(
            status, steps, observation, self.memory.digest,
            self.policy.policy_id, self.body.body_id,
        )
