from __future__ import annotations

import asyncio
import json
import subprocess

import pytest

from metamorphosis import m074_docker_environment as module
from metamorphosis.m074_docker_environment import DockerEnvironmentError, DockerTaskEnvironment
from metamorphosis.m074_task_bank import ALPINE, task_by_id


WRITABLE_TASK = task_by_id("write-release-note-writable")
READONLY_TASK = task_by_id("write-release-note-readonly")
FIXTURE_TASK = task_by_id("run-analysis-python-present")


class Recorder:
    """Stands in for mira_core.process.run_utf8_process."""

    def __init__(self, results) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.inputs: list[str | None] = []
        self.results = list(results)

    def __call__(self, argv, *, timeout_seconds, input_text=None, **kwargs):
        self.calls.append(tuple(argv))
        self.inputs.append(input_text)
        outcome = self.results.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        returncode, stdout, stderr = outcome
        return subprocess.CompletedProcess(list(argv), returncode, stdout, stderr)


def _patch(monkeypatch: pytest.MonkeyPatch, recorder: Recorder) -> None:
    monkeypatch.setattr(module, "run_utf8_process", recorder)


def test_the_container_is_persistent_from_probe_through_episode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([
        (0, "container\n", ""), (0, "", ""), (0, "one\n", ""),
        (0, "two\n", ""), (0, "", ""),
    ])
    _patch(monkeypatch, recorder)

    with DockerTaskEnvironment(WRITABLE_TASK) as environment:
        first = asyncio.run(environment.exec("echo one", timeout_sec=5))
        second = asyncio.run(environment.exec("echo two", timeout_sec=5))
        container = environment.container_id

    assert first.stdout == "one\n" and second.stdout == "two\n"
    run_calls = [call for call in recorder.calls if call[1] == "run"]
    agent_calls = [
        call for call in recorder.calls
        if call[1] == "exec" and "65534:65534" in call
    ]
    assert len(run_calls) == 1
    assert len(agent_calls) == 2
    assert all(container in call for call in agent_calls)
    assert recorder.calls[-1][:3] == ("docker", "rm", "--force")


def test_start_argv_realizes_read_only_root_and_bounded_tmpfs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([(0, "", ""), (0, "", ""), (0, "", "")])
    _patch(monkeypatch, recorder)

    with DockerTaskEnvironment(WRITABLE_TASK):
        pass

    start = next(call for call in recorder.calls if call[1] == "run")
    assert "--read-only" in start
    assert "--network=none" in start
    assert "--cap-drop=ALL" in start
    assert "--security-opt=no-new-privileges" in start
    assert "/workspace:rw,nosuid,nodev,noexec,size=16777216" in start
    assert start[-3:] == (ALPINE, "sleep", "infinity")


def test_fixtures_are_materialized_as_root_before_permissions_are_finalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([
        (0, "", ""), (0, "", ""), (0, "", ""), (0, "", ""),
    ])
    _patch(monkeypatch, recorder)

    with DockerTaskEnvironment(FIXTURE_TASK):
        pass

    root_execs = [call for call in recorder.calls if call[1] == "exec"]
    assert len(root_execs) == 2
    assert all("0:0" in call for call in root_execs)
    assert "analyse.py" in " ".join(root_execs[0])
    assert FIXTURE_TASK.fixture_files[0].content in recorder.inputs
    assert "chmod 0777 /workspace" in " ".join(root_execs[1])


def test_readonly_workspace_mode_is_applied_after_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([(0, "", ""), (0, "", ""), (0, "", "")])
    _patch(monkeypatch, recorder)
    with DockerTaskEnvironment(READONLY_TASK):
        pass
    assert any("chmod 0555 /workspace" in " ".join(call) for call in recorder.calls)


def test_agent_runs_non_root_and_external_evaluator_runs_as_harness_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([
        (0, "", ""), (0, "", ""), (0, "", ""), (0, "", ""), (0, "", ""),
    ])
    _patch(monkeypatch, recorder)
    with DockerTaskEnvironment(WRITABLE_TASK) as environment:
        asyncio.run(environment.exec("true"))
        evaluation = environment.evaluate()
    assert evaluation.return_code == 0
    exec_calls = [call for call in recorder.calls if call[1] == "exec"]
    assert any("65534:65534" in call for call in exec_calls)
    assert sum("0:0" in call for call in exec_calls) == 2  # setup and evaluator


def test_network_mode_is_reported_in_harbor_vocabulary() -> None:
    assert DockerTaskEnvironment(WRITABLE_TASK).network_policy.network_mode.value == "no-network"


def test_scientific_boundary_is_read_back_from_the_live_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = [{
        "Config": {"Image": WRITABLE_TASK.environment.image},
        "State": {"Running": True},
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "Memory": 256 * 1024 * 1024,
            "NanoCpus": 1_000_000_000,
            "PidsLimit": 64,
            "Tmpfs": {"/workspace": "rw,nosuid,nodev,noexec,size=16777216"},
        },
    }]
    recorder = Recorder([
        (0, "container\n", ""), (0, "", ""),
        (0, json.dumps(inspection), ""), (0, "", ""),
    ])
    _patch(monkeypatch, recorder)
    with DockerTaskEnvironment(WRITABLE_TASK) as environment:
        attestation = environment.inspect_security_boundary()
    assert attestation["matches_declaration"] is True
    assert attestation["agent_exec_user"] == "65534:65534"
    assert any(call[1] == "inspect" for call in recorder.calls)


def test_scientific_boundary_mismatch_is_reported_not_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = [{
        "Config": {"Image": WRITABLE_TASK.environment.image},
        "State": {"Running": True},
        "HostConfig": {
            "NetworkMode": "bridge",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "Memory": 256 * 1024 * 1024,
            "NanoCpus": 1_000_000_000,
            "PidsLimit": 64,
            "Tmpfs": {"/workspace": "rw,nosuid,nodev,noexec,size=16777216"},
        },
    }]
    recorder = Recorder([
        (0, "container\n", ""), (0, "", ""),
        (0, json.dumps(inspection), ""), (0, "", ""),
    ])
    _patch(monkeypatch, recorder)
    with DockerTaskEnvironment(WRITABLE_TASK) as environment:
        attestation = environment.inspect_security_boundary()
    assert attestation["network_mode"] == "bridge"
    assert attestation["matches_declaration"] is False


def test_a_timeout_is_reported_as_a_command_result_not_an_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([
        (0, "", ""), (0, "", ""), subprocess.TimeoutExpired(["docker"], 5),
        (0, "", ""),
    ])
    _patch(monkeypatch, recorder)
    with DockerTaskEnvironment(WRITABLE_TASK) as environment:
        result = asyncio.run(environment.exec("sleep 99", timeout_sec=5))
    assert result.return_code == 124
    assert "time budget" in result.stderr


def test_a_failed_start_is_reported_and_leaves_no_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, Recorder([(125, "", "no such image")]))
    environment = DockerTaskEnvironment(WRITABLE_TASK)
    with pytest.raises(DockerEnvironmentError, match="failed to start"):
        environment.start()
    with pytest.raises(DockerEnvironmentError, match="not running"):
        _ = environment.container_id


def test_exec_requires_a_running_container_and_a_real_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, Recorder([(0, "", ""), (0, "", ""), (0, "", "")]))
    environment = DockerTaskEnvironment(WRITABLE_TASK)
    with pytest.raises(DockerEnvironmentError, match="not running"):
        asyncio.run(environment.exec("echo hi"))
    environment.start()
    with pytest.raises(DockerEnvironmentError, match="non-empty script"):
        asyncio.run(environment.exec(""))
    environment.stop()


def test_double_start_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, Recorder([(0, "", ""), (0, "", ""), (0, "", "")]))
    environment = DockerTaskEnvironment(WRITABLE_TASK)
    environment.start()
    with pytest.raises(DockerEnvironmentError, match="already running"):
        environment.start()
    environment.stop()
