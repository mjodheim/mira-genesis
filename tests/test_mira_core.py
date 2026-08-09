from __future__ import annotations

import json
import subprocess
import sys
from typing import Mapping, Sequence

import pytest

from mira_core import (
    Action, Authority, Goal, MemoryLedger, MiraAgent, Observation, SafetyPolicy,
)
from mira_core.contracts import JsonValue


class CounterBody:
    body_id = "counter-body"

    def __init__(self, target: int = 3) -> None:
        self.target = target
        self.value = 0

    def reset(self, goal: Goal) -> Observation:
        self.value = 0
        return Observation("counter-0", {"value": self.value})

    def act(self, action: Action) -> Observation:
        if action.kind == "explode":
            raise RuntimeError("forced body fault")
        if action.kind != "increment":
            return Observation("counter-invalid", {"value": self.value}, terminal=True, error="invalid")
        self.value += int(action.payload.get("amount", 1))
        terminal = self.value >= self.target
        return Observation(f"counter-{self.value}", {"value": self.value}, terminal, terminal)


class IncrementPolicy:
    policy_id = "increment-policy"

    def propose(
        self, goal: Goal, observation: Observation, history: Sequence[Mapping[str, JsonValue]],
    ) -> Action:
        return Action(
            f"increment-{len(history)}", "increment", {"amount": 1},
            (Authority.COMPUTE.value,),
        )


class FixedPolicy:
    policy_id = "fixed-policy"

    def __init__(self, action: Action | None) -> None:
        self.action = action

    def propose(self, goal, observation, history):
        return self.action


class AuthorityCounterBody(CounterBody):
    def required_authorities(self, action: Action) -> tuple[str, ...]:
        return (Authority.FILESYSTEM_WRITE.value,)


class BrokenAuthorityBody(CounterBody):
    def required_authorities(self, action: Action) -> tuple[str, ...]:
        raise RuntimeError("broken authority contract")


def test_agent_completes_a_goal_and_records_a_verifiable_episode() -> None:
    agent = MiraAgent(IncrementPolicy(), CounterBody(), max_steps=4)
    result = agent.run(Goal("reach-three", "increment until value is at least three"))
    assert result.succeeded is True
    assert result.steps == 3
    assert result.final_observation.state == {"value": 3}
    assert result.memory_digest == agent.memory.digest
    assert [event.kind for event in agent.memory.events] == [
        "episode_started", "action_admission", "observation", "action_admission",
        "observation", "action_admission", "observation", "episode_finished",
    ]
    agent.memory.verify()


def test_default_policy_denies_external_authority() -> None:
    action = Action("push", "git_push", {}, (Authority.REPOSITORY_WRITE.value,))
    agent = MiraAgent(FixedPolicy(action), CounterBody())
    result = agent.run(Goal("unsafe", "push a repository"))
    assert result.status == "safety_refused"
    assert result.steps == 0
    admission = next(event for event in agent.memory.events if event.kind == "action_admission")
    assert admission.payload["allowed"] is False
    assert admission.payload["missing_authorities"] == ["repository_write"]


def test_body_contract_prevents_policy_authority_underdeclaration() -> None:
    underdeclared = Action("write", "increment", {"amount": 1}, (Authority.COMPUTE.value,))
    agent = MiraAgent(FixedPolicy(underdeclared), AuthorityCounterBody())
    result = agent.run(Goal("authority-contract", "exercise an authority-aware body"))
    assert result.status == "action_contract_refused"
    assert result.steps == 0
    assert agent.body.value == 0
    assert result.final_observation.state["missing_authority_declarations"] == ["filesystem_write"]

    declared = Action("write", "increment", {"amount": 1}, (Authority.FILESYSTEM_WRITE.value,))
    denied = MiraAgent(FixedPolicy(declared), AuthorityCounterBody()).run(
        Goal("authority-envelope", "remain inside the granted authority envelope")
    )
    assert denied.status == "safety_refused"


def test_broken_body_authority_contract_fails_closed() -> None:
    action = Action("broken", "increment", {"amount": 1})
    agent = MiraAgent(FixedPolicy(action), BrokenAuthorityBody())
    result = agent.run(Goal("broken-contract", "fail closed on a broken body contract"))
    assert result.status == "body_contract_error"
    assert result.steps == 0
    assert agent.body.value == 0
    assert result.final_observation.error == "RuntimeError: broken authority contract"


def test_high_impact_authority_still_requires_human_release_when_granted() -> None:
    safety = SafetyPolicy.from_authorities({Authority.COMPUTE, Authority.NETWORK})
    decision = safety.decide(Action("request", "http", {}, (Authority.NETWORK.value,)))
    assert decision.allowed is False
    assert decision.human_release_required is True
    assert safety.can_expand_to({Authority.COMPUTE}) is True
    assert safety.can_expand_to({Authority.COMPUTE, Authority.NETWORK, Authority.DEPLOYMENT}) is False


def test_step_budget_and_policy_refusal_fail_closed() -> None:
    budgeted = MiraAgent(IncrementPolicy(), CounterBody(target=5), max_steps=2)
    assert budgeted.run(Goal("too-far", "reach five")).status == "step_budget_exhausted"
    refusing = MiraAgent(FixedPolicy(None), CounterBody())
    assert refusing.run(Goal("unknown", "do something unsupported")).status == "policy_refused"


def test_body_exception_becomes_evidence() -> None:
    action = Action("fault", "explode", {}, (Authority.COMPUTE.value,))
    result_agent = MiraAgent(FixedPolicy(action), CounterBody())
    result = result_agent.run(Goal("fault", "exercise a body fault"))
    assert result.status == "body_error"
    assert result.final_observation.error == "RuntimeError: forced body fault"
    assert "body_error" in [event.kind for event in result_agent.memory.events]


def test_memory_checkpoint_restores_exactly_and_rejects_tampering() -> None:
    ledger = MemoryLedger()
    ledger.append("one", {"value": 1})
    checkpoint = ledger.checkpoint()
    restored = MemoryLedger.restore(checkpoint)
    assert restored.checkpoint() == checkpoint
    assert restored.digest == ledger.digest

    value = json.loads(checkpoint)
    value["events"][0]["payload"]["value"] = 2
    with pytest.raises(ValueError, match="digest mismatch"):
        MemoryLedger.restore(json.dumps(value).encode())


def test_memory_restore_rejects_a_forged_head() -> None:
    ledger = MemoryLedger()
    ledger.append("one", {"value": 1})
    value = json.loads(ledger.checkpoint())
    value["head_digest"] = "f" * 64
    with pytest.raises(ValueError, match="head digest"):
        MemoryLedger.restore(json.dumps(value).encode())


def test_demo_entrypoint_is_a_real_installable_core_smoke_test() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_mira_core_demo.py"], check=True,
        capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    assert result["status"] == "completed"
    assert result["succeeded"] is True
    assert result["steps"] == 3
    assert result["final_state"] == {"value": 3}
    assert result["external_authority_granted"] is False
