from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from metamorphosis.m074_ablation_arms import (
    ABLATION_ARMS, ARM_A_TERMINAL_REFUSAL, ARM_B_NONTERMINAL_REFUSAL, AblationArmError,
    arm_by_id, run_arm_episode,
)
from mira_core.harbor import HarborEpisodeLimits, run_harbor_episode
from mira_core.safety import Authority


@dataclass
class FakeExecResult:
    stdout: str | None
    stderr: str | None
    return_code: int


class FakeMode:
    def __init__(self, value: str) -> None:
        self.value = value


class FakePolicy:
    def __init__(self, value: str) -> None:
        self.network_mode = FakeMode(value)


class FakeEnvironment:
    def __init__(self, mode: str = "no-network", *, fail: bool = False) -> None:
        self.network_policy = FakePolicy(mode)
        self.commands: list[tuple[str, int | None]] = []
        self.fail = fail

    async def exec(self, command: str, timeout_sec: int | None = None):
        self.commands.append((command, timeout_sec))
        if self.fail:
            raise OSError("container exec failed")
        return FakeExecResult("inspected workspace\n", "", 0)


class SequencedBackend:
    backend_id = "sequenced-fake-model"

    def __init__(self, values) -> None:
        self.values = list(values)

    def complete(self, request):
        return self.values.pop(0)


ACT = {"decision": "act", "script": "ls /app", "reason": None}
FINISH = {"decision": "finish", "script": None, "reason": None}
REFUSE = {"decision": "refuse", "script": None, "reason": "no compiler available"}
MALFORMED = {"decision": "other", "script": None, "reason": None}

EQUIVALENCE_SCENARIOS = {
    "exec_then_submit": ((ACT, FINISH), 4, False),
    "immediate_refusal": ((REFUSE,), 4, False),
    "malformed_decision": ((MALFORMED,), 4, False),
    "budget_exhaustion": ((ACT, ACT), 2, False),
    "body_error": ((ACT,), 4, True),
}


@pytest.mark.parametrize("scenario", sorted(EQUIVALENCE_SCENARIOS))
def test_arm_a_preserves_m071_decision_and_command_semantics(scenario: str) -> None:
    """The descendant may fix accounting, but not terminal decisions or executed commands."""

    decisions, max_steps, fail = EQUIVALENCE_SCENARIOS[scenario]
    limits = HarborEpisodeLimits(max_steps=max_steps, command_timeout_seconds=7)

    frozen_environment = FakeEnvironment(fail=fail)
    frozen_manifest, frozen_memory = asyncio.run(run_harbor_episode(
        "repair the external task", frozen_environment,
        SequencedBackend(decisions), limits=limits,
    ))

    arm_environment = FakeEnvironment(fail=fail)
    arm_manifest, arm_memory, transcript = asyncio.run(run_arm_episode(
        "repair the external task", arm_environment,
        SequencedBackend(decisions), ARM_A_TERMINAL_REFUSAL, limits=limits,
    ))

    assert arm_manifest["status"] == frozen_manifest["status"]
    assert arm_environment.commands == frozen_environment.commands
    assert [event.kind for event in arm_memory.events] == [
        event.kind for event in frozen_memory.events
    ]
    assert len(transcript) == len(frozen_memory.events)
    assert arm_manifest["steps"] >= 1


def test_refusal_terminates_arm_a_but_not_the_ablated_arms() -> None:
    limits = HarborEpisodeLimits(max_steps=3)

    governed_manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE,)), ARM_A_TERMINAL_REFUSAL,
        limits=limits,
    ))
    assert governed_manifest["status"] == "policy_refused"
    assert governed_manifest["steps"] == 1
    assert governed_manifest["refusals"] == 1

    ablated_manifest, ablated_memory, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE, REFUSE, REFUSE)),
        ARM_B_NONTERMINAL_REFUSAL, limits=limits,
    ))
    assert ablated_manifest["status"] == "step_budget_exhausted"
    assert ablated_manifest["steps"] == 3
    assert ablated_manifest["refusals"] == 3
    assert "refusal_not_terminal" in [event.kind for event in ablated_memory.events]


def test_narrowed_grant_is_enforced_identically_in_both_arms() -> None:
    """Only refusal termination may differ; authority admission cannot become a confound."""

    read_only = frozenset({Authority.COMPUTE, Authority.FILESYSTEM_READ})
    limits = HarborEpisodeLimits(max_steps=3)

    for arm in ABLATION_ARMS:
        environment = FakeEnvironment()
        manifest, memory, _ = asyncio.run(run_arm_episode(
            "task", environment, SequencedBackend((ACT,)), arm,
            limits=limits, granted_authorities=read_only,
        ))
        assert manifest["status"] == "safety_refused"
        assert manifest["steps"] == 1
        assert manifest["executed_commands"] == 0
        assert environment.commands == []
        assert "authority_not_enforced" not in [event.kind for event in memory.events]


def test_default_grant_leaves_the_authority_gate_inert() -> None:
    """Recorded so the draft cannot silently rely on an ablation that cannot fire."""

    for arm in ABLATION_ARMS:
        manifest, _, _ = asyncio.run(run_arm_episode(
            "task", FakeEnvironment(), SequencedBackend((ACT, FINISH)), arm,
            limits=HarborEpisodeLimits(max_steps=3),
        ))
        assert manifest["status"] == "submitted_for_external_evaluation"


def test_both_arms_preserve_the_same_tamper_evident_record_type() -> None:
    for arm in ABLATION_ARMS:
        manifest, _, transcript = asyncio.run(run_arm_episode(
            "task", FakeEnvironment(), SequencedBackend((FINISH,)), arm,
        ))
        assert manifest["audit_record"] == "hash_chained_ledger"
        assert isinstance(manifest["memory_digest"], str)
        assert transcript[0]["kind"] == "episode_started"


def test_arms_differ_only_in_declared_governance_fields() -> None:
    """Falsifier 5: an undeclared difference between arms invalidates the contrast."""

    fields = {arm.arm_id: arm.public_dict() for arm in ABLATION_ARMS}
    assert set(fields) == {"A-terminal-refusal", "B-nonterminal-refusal"}
    for values in fields.values():
        assert set(values) == {"arm_id", "refusal_terminates_episode"}
    assert fields["A-terminal-refusal"]["refusal_terminates_episode"] is True
    assert fields["B-nonterminal-refusal"]["refusal_terminates_episode"] is False


def test_arms_refuse_any_network_enabled_environment() -> None:
    for arm in ABLATION_ARMS:
        with pytest.raises(AblationArmError, match="no-network"):
            asyncio.run(run_arm_episode(
                "task", FakeEnvironment("public"), SequencedBackend(()), arm,
            ))


def test_unknown_arm_identifier_fails_closed() -> None:
    assert arm_by_id("A-terminal-refusal") is ARM_A_TERMINAL_REFUSAL
    with pytest.raises(AblationArmError, match="unknown ablation arm"):
        arm_by_id("D-nop")
