from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from mira_core.harbor import HarborEpisodeLimits, run_harbor_episode


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
    def __init__(self, mode: str = "no-network") -> None:
        self.network_policy = FakePolicy(mode)
        self.commands: list[tuple[str, int | None]] = []

    async def exec(self, command: str, timeout_sec: int | None = None):
        self.commands.append((command, timeout_sec))
        return FakeExecResult("inspected workspace\n", "", 0)


class SequencedBackend:
    backend_id = "sequenced-fake-model"

    def __init__(self, values) -> None:
        self.values = list(values)

    def complete(self, request):
        return self.values.pop(0)


def test_harbor_bridge_executes_then_submits_without_claiming_success() -> None:
    environment = FakeEnvironment()
    backend = SequencedBackend((
        {"decision": "act", "script": "find /app -maxdepth 2 -type f", "reason": None},
        {"decision": "finish", "script": None, "reason": None},
    ))
    manifest, memory = asyncio.run(run_harbor_episode(
        "repair the external task", environment, backend,
        limits=HarborEpisodeLimits(max_steps=3, command_timeout_seconds=7),
    ))
    assert manifest["status"] == "submitted_for_external_evaluation"
    assert manifest["agent_claimed_success"] is False
    assert manifest["success_decided_externally"] is True
    assert environment.commands == [("find /app -maxdepth 2 -type f", 7)]
    assert memory.digest == manifest["memory_digest"]
    assert [event.kind for event in memory.events][-2:] == [
        "workspace_submitted", "episode_finished",
    ]


def test_harbor_bridge_refuses_any_agent_network_access() -> None:
    with pytest.raises(RuntimeError, match="network_mode=no-network"):
        asyncio.run(run_harbor_episode(
            "do not run", FakeEnvironment("public"), SequencedBackend(()),
        ))


def test_harbor_bridge_bounds_output_and_preserves_policy_failure() -> None:
    environment = FakeEnvironment()
    backend = SequencedBackend((
        {"decision": "act", "script": "printf long", "reason": None},
        {"decision": "other", "script": None, "reason": None},
    ))
    manifest, memory = asyncio.run(run_harbor_episode(
        "bound observations", environment, backend,
        limits=HarborEpisodeLimits(max_steps=3, max_output_chars=4),
    ))
    assert manifest["status"] == "policy_error"
    observation = next(event for event in memory.events if event.kind == "observation")
    assert observation.payload["output_truncated"] is True
    assert "policy_error" in [event.kind for event in memory.events]
