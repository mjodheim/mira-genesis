from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest

from mira_core import (
    Action, ContainerBodyError, ContainerExecResult, ContainerLimits, ContainerSpec, Goal,
    IsolatedContainerBody, MiraAgent, SafetyPolicy, StructuredModelPolicy,
)
from mira_core.safety import Authority


IMAGE = "example.invalid/mira-fixture@sha256:" + "a" * 64
SAFETY = SafetyPolicy.from_authorities({
    Authority.COMPUTE, Authority.FILESYSTEM_READ, Authority.FILESYSTEM_WRITE,
})


class FakeEngine:
    engine_id = "fake-container-engine"

    def __init__(self, results: Sequence[ContainerExecResult] = ()) -> None:
        self.results = list(results)
        self.created: list[tuple[ContainerSpec, Path, ContainerLimits]] = []
        self.started: list[str] = []
        self.executed: list[tuple[str, tuple[str, ...], float, int]] = []
        self.removed: list[str] = []

    def verify_image(self, image: str) -> str:
        return image

    def create(self, spec: ContainerSpec, workspace: Path, limits: ContainerLimits) -> str:
        self.created.append((spec, workspace, limits))
        return "a" * 64

    def start(self, container_id: str) -> None:
        self.started.append(container_id)

    def inspect_isolation(self, container_id: str):
        spec, _, limits = self.created[-1]
        return {
            "network_mode": "none",
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "read_only_rootfs": True,
            "memory_bytes": limits.memory_bytes,
            "nano_cpus": int(limits.cpus * 1_000_000_000),
            "pids_limit": limits.pids_limit,
            "mounts": [{
                "type": "bind", "destination": spec.working_directory, "rw": True,
            }],
        }

    def execute(
        self, container_id: str, argv: Sequence[str], *, timeout_seconds: float,
        max_output_bytes: int,
    ) -> ContainerExecResult:
        self.executed.append((container_id, tuple(argv), timeout_seconds, max_output_bytes))
        return self.results.pop(0)

    def remove(self, container_id: str) -> None:
        self.removed.append(container_id)


class FakeBackend:
    backend_id = "fake-model"

    def __init__(self) -> None:
        self.index = 0

    def complete(self, request):
        self.index += 1
        if self.index == 1:
            return {"decision": "act", "script": "python -m pytest -q", "reason": None}
        return {"decision": "finish", "script": None, "reason": None}


def test_isolated_episode_executes_then_submits_for_external_evaluation(tmp_path: Path) -> None:
    engine = FakeEngine((ContainerExecResult(0, b"2 passed\n"),))
    body = IsolatedContainerBody(
        "isolated-fixture", tmp_path, ContainerSpec(IMAGE), engine,
        limits=ContainerLimits(max_steps=4, timeout_seconds=5, max_output_bytes=100),
    )
    with body:
        result = MiraAgent(
            StructuredModelPolicy(FakeBackend()), body, safety=SAFETY, max_steps=4,
        ).run(Goal("external-evaluation", "repair, then submit for evaluator-owned tests"))
    assert result.status == "body_stopped"
    assert result.succeeded is False
    assert result.steps == 2
    assert result.final_observation.state["event"] == "workspace_submitted_for_external_evaluation"
    assert result.final_observation.state["agent_claimed_success"] is False
    assert engine.created[0][0].image == IMAGE
    assert engine.executed[0][1] == ("/bin/sh", "-lc", "python -m pytest -q")
    assert engine.removed == ["a" * 64]


def test_reset_exposes_isolation_contract_without_host_paths(tmp_path: Path) -> None:
    body = IsolatedContainerBody("isolation", tmp_path, ContainerSpec(IMAGE), FakeEngine())
    observation = body.reset(Goal("contract", "inspect isolation contract"))
    assert observation.state["network"] == "none"
    assert observation.state["capabilities"] == []
    assert observation.state["no_new_privileges"] is True
    assert observation.state["read_only_rootfs"] is True
    assert observation.state["host_repository_mounted"] is False
    assert observation.state["docker_socket_mounted"] is False
    assert observation.state["success_decided_externally"] is True
    assert len(observation.state["isolation_evidence_digest"]) == 64
    assert str(tmp_path) not in str(observation.state)
    body.close()


def test_observed_isolation_mismatch_fails_closed_and_removes_container(tmp_path: Path) -> None:
    engine = FakeEngine()
    engine.inspect_isolation = lambda container_id: {
        "network_mode": "bridge",
    }
    body = IsolatedContainerBody("mismatch", tmp_path, ContainerSpec(IMAGE), engine)
    with pytest.raises(ContainerBodyError, match="isolation contract"):
        body.reset(Goal("mismatch", "reject a weaker realized container"))
    assert engine.removed == ["a" * 64]


def test_body_authority_contract_prevents_exec_underdeclaration(tmp_path: Path) -> None:
    body = IsolatedContainerBody("authority", tmp_path, ContainerSpec(IMAGE), FakeEngine())
    action = Action("exec", "container_exec", {"script": "true"}, ())
    assert body.required_authorities(action) == (
        "compute", "filesystem_read", "filesystem_write",
    )
    with pytest.raises(ContainerBodyError, match="closed payload"):
        body.required_authorities(Action(
            "bad", "container_exec", {"script": "true", "env": {"SECRET": "x"}}, (),
        ))


def test_timeout_and_output_truncation_stop_the_episode(tmp_path: Path) -> None:
    for observed, message in (
        (ContainerExecResult(None, b"", timed_out=True), "time budget"),
        (ContainerExecResult(0, b"x" * 4, output_truncated=True), "output budget"),
    ):
        engine = FakeEngine((observed,))
        body = IsolatedContainerBody("bounded", tmp_path, ContainerSpec(IMAGE), engine)
        body.reset(Goal("bounded", "remain bounded"))
        result = body.act(Action(
            "exec", "container_exec", {"script": "generate"},
            ("compute", "filesystem_read", "filesystem_write"),
        ))
        assert result.terminal is True
        assert result.success is False
        assert message in (result.error or "")
        body.close()


def test_image_script_and_workspace_contracts_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ContainerBodyError, match="pinned"):
        ContainerSpec("python:latest")
    with pytest.raises(ContainerBodyError, match="non-symlink"):
        IsolatedContainerBody("missing", tmp_path / "missing", ContainerSpec(IMAGE), FakeEngine())
    body = IsolatedContainerBody(
        "script-limit", tmp_path, ContainerSpec(IMAGE), FakeEngine(),
        limits=ContainerLimits(max_script_bytes=3),
    )
    with pytest.raises(ContainerBodyError, match="byte budget"):
        body.required_authorities(Action(
            "large", "container_exec", {"script": "1234"},
            ("compute", "filesystem_read", "filesystem_write"),
        ))
