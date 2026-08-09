from __future__ import annotations

import asyncio
import subprocess

import pytest

from metamorphosis import m072_docker_environment as module
from metamorphosis.m072_docker_environment import DockerEnvironmentError, DockerTaskEnvironment
from metamorphosis.m072_task_bank import ALPINE, READONLY_ALPINE, WRITABLE_ALPINE


class Recorder:
    """Stands in for mira_core.process.run_utf8_process."""

    def __init__(self, results) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.results = list(results)

    def __call__(self, argv, *, timeout_seconds, **kwargs):
        self.calls.append(tuple(argv))
        outcome = self.results.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        returncode, stdout, stderr = outcome
        return subprocess.CompletedProcess(list(argv), returncode, stdout, stderr)


def _patch(monkeypatch: pytest.MonkeyPatch, recorder: Recorder) -> None:
    monkeypatch.setattr(module, "run_utf8_process", recorder)


def test_the_container_is_persistent_for_the_whole_episode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh container per command would discard the agent's work and fake impossibility."""

    recorder = Recorder([(0, "", ""), (0, "one\n", ""), (0, "two\n", ""), (0, "", "")])
    _patch(monkeypatch, recorder)

    with DockerTaskEnvironment(WRITABLE_ALPINE) as environment:
        first = asyncio.run(environment.exec("echo one", timeout_sec=5))
        second = asyncio.run(environment.exec("echo two", timeout_sec=5))
        container = environment.container_id

    assert first.stdout == "one\n" and second.stdout == "two\n"
    run_calls = [call for call in recorder.calls if call[1] == "run"]
    exec_calls = [call for call in recorder.calls if call[1] == "exec"]
    assert len(run_calls) == 1
    assert len(exec_calls) == 2
    assert all(call[2] == container for call in exec_calls)
    assert recorder.calls[-1][:3] == ("docker", "rm", "--force")


def test_start_argv_reflects_the_declared_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder([(0, "", ""), (0, "", ""), (0, "", ""), (0, "", "")])
    _patch(monkeypatch, recorder)

    with DockerTaskEnvironment(WRITABLE_ALPINE):
        pass
    with DockerTaskEnvironment(READONLY_ALPINE):
        pass

    writable, readonly = [call for call in recorder.calls if call[1] == "run"]
    assert "--read-only" not in writable
    assert "--read-only" in readonly
    for call in (writable, readonly):
        assert "--detach" in call and "--network=none" in call
        assert call[-3:] == (ALPINE, "sleep", "infinity")


def test_network_mode_is_reported_in_harbor_vocabulary() -> None:
    assert DockerTaskEnvironment(WRITABLE_ALPINE).network_policy.network_mode.value == "no-network"


def test_a_timeout_is_reported_as_a_command_result_not_an_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder([
        (0, "", ""), subprocess.TimeoutExpired(["docker"], 5), (0, "", ""),
    ])
    _patch(monkeypatch, recorder)

    with DockerTaskEnvironment(WRITABLE_ALPINE) as environment:
        result = asyncio.run(environment.exec("sleep 99", timeout_sec=5))
    assert result.return_code == 124
    assert "time budget" in result.stderr


def test_a_failed_start_is_reported_and_leaves_no_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, Recorder([(125, "", "no such image")]))
    environment = DockerTaskEnvironment(WRITABLE_ALPINE)
    with pytest.raises(DockerEnvironmentError, match="failed to start"):
        environment.start()
    with pytest.raises(DockerEnvironmentError, match="not running"):
        _ = environment.container_id


def test_exec_requires_a_running_container_and_a_real_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, Recorder([(0, "", ""), (0, "", "")]))
    environment = DockerTaskEnvironment(WRITABLE_ALPINE)
    with pytest.raises(DockerEnvironmentError, match="not running"):
        asyncio.run(environment.exec("echo hi"))
    environment.start()
    with pytest.raises(DockerEnvironmentError, match="non-empty script"):
        asyncio.run(environment.exec(""))
    environment.stop()


def test_double_start_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, Recorder([(0, "", ""), (0, "", "")]))
    environment = DockerTaskEnvironment(WRITABLE_ALPINE)
    environment.start()
    with pytest.raises(DockerEnvironmentError, match="already running"):
        environment.start()
    environment.stop()
