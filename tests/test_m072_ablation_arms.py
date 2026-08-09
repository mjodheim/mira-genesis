from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from metamorphosis.m072_ablation_arms import (
    ABLATION_ARMS, ARM_A_GOVERNED, ARM_B_RAW, ARM_C_NO_REFUSAL, AblationArmError, arm_by_id,
    run_arm_episode,
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
def test_arm_a_reproduces_the_frozen_m071_loop_exactly(scenario: str) -> None:
    """Arm A must be the frozen composition, not a refactored descendant of it."""

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
        SequencedBackend(decisions), ARM_A_GOVERNED, limits=limits,
    ))

    assert arm_manifest["status"] == frozen_manifest["status"]
    assert arm_manifest["steps"] == frozen_manifest["steps"]
    assert arm_manifest["memory_digest"] == frozen_manifest["memory_digest"]
    assert arm_environment.commands == frozen_environment.commands
    assert [event.kind for event in arm_memory.events] == [
        event.kind for event in frozen_memory.events
    ]
    assert [event.payload for event in arm_memory.events] == [
        event.payload for event in frozen_memory.events
    ]
    assert len(transcript) == len(frozen_memory.events)


def test_refusal_terminates_arm_a_but_not_the_ablated_arms() -> None:
    limits = HarborEpisodeLimits(max_steps=3)

    governed_manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE,)), ARM_A_GOVERNED, limits=limits,
    ))
    assert governed_manifest["status"] == "policy_refused"
    assert governed_manifest["refusals"] == 1

    ablated_manifest, ablated_memory, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE, REFUSE, REFUSE)),
        ARM_C_NO_REFUSAL, limits=limits,
    ))
    assert ablated_manifest["status"] == "step_budget_exhausted"
    assert ablated_manifest["refusals"] == 3
    assert "refusal_not_terminal" in [event.kind for event in ablated_memory.events]


def test_narrowed_grant_blocks_arm_a_and_is_only_recorded_in_arm_b() -> None:
    """The authority dimension is measurable only when the grant is narrower than the action."""

    read_only = frozenset({Authority.COMPUTE, Authority.FILESYSTEM_READ})
    limits = HarborEpisodeLimits(max_steps=3)

    governed_manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((ACT,)), ARM_A_GOVERNED,
        limits=limits, granted_authorities=read_only,
    ))
    assert governed_manifest["status"] == "safety_refused"
    assert governed_manifest["executed_commands"] == 0

    raw_environment = FakeEnvironment()
    raw_manifest, raw_memory, _ = asyncio.run(run_arm_episode(
        "task", raw_environment, SequencedBackend((ACT, FINISH)), ARM_B_RAW,
        limits=limits, granted_authorities=read_only,
    ))
    assert raw_manifest["status"] == "submitted_for_external_evaluation"
    assert raw_manifest["unenforced_blocked_actions"] == 1
    assert raw_manifest["executed_commands"] == 1
    assert raw_environment.commands == [("ls /app", 120)]
    assert "authority_not_enforced" in [event.kind for event in raw_memory.events]


def test_default_grant_leaves_the_authority_gate_inert() -> None:
    """Recorded so the draft cannot silently rely on an ablation that cannot fire."""

    for arm in (ARM_A_GOVERNED, ARM_B_RAW):
        manifest, _, _ = asyncio.run(run_arm_episode(
            "task", FakeEnvironment(), SequencedBackend((ACT, FINISH)), arm,
            limits=HarborEpisodeLimits(max_steps=3),
        ))
        assert manifest["status"] == "submitted_for_external_evaluation"
        assert manifest["unenforced_blocked_actions"] == 0


def test_only_governed_arms_claim_a_tamper_evident_record() -> None:
    raw_manifest, _, raw_transcript = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((FINISH,)), ARM_B_RAW,
    ))
    assert raw_manifest["audit_record"] == "plain_transcript"
    assert raw_manifest["memory_digest"] is None
    assert raw_transcript[0]["kind"] == "episode_started"

    governed_manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((FINISH,)), ARM_A_GOVERNED,
    ))
    assert governed_manifest["audit_record"] == "hash_chained_ledger"
    assert isinstance(governed_manifest["memory_digest"], str)


def test_arms_differ_only_in_declared_governance_fields() -> None:
    """Falsifier 5: an undeclared difference between arms invalidates the contrast."""

    fields = {arm.arm_id: arm.public_dict() for arm in ABLATION_ARMS}
    assert set(fields) == {"A-governed", "B-raw", "C-governed-no-refusal"}
    for values in fields.values():
        assert set(values) == {
            "arm_id", "enforce_authorities", "refusal_terminates_episode",
            "tamper_evident_ledger",
        }
    assert fields["C-governed-no-refusal"]["enforce_authorities"] is True
    assert fields["C-governed-no-refusal"]["refusal_terminates_episode"] is False
    assert fields["B-raw"]["enforce_authorities"] is False


def test_arms_refuse_any_network_enabled_environment() -> None:
    for arm in ABLATION_ARMS:
        with pytest.raises(AblationArmError, match="no-network"):
            asyncio.run(run_arm_episode(
                "task", FakeEnvironment("public"), SequencedBackend(()), arm,
            ))


def test_unknown_arm_identifier_fails_closed() -> None:
    assert arm_by_id("A-governed") is ARM_A_GOVERNED
    with pytest.raises(AblationArmError, match="unknown ablation arm"):
        arm_by_id("D-nop")
