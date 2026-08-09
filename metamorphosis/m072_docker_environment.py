"""A Harbor-shaped environment over one real Docker container.

**Draft apparatus. Nothing here is frozen and no result may cite it.**

The M072 arms expect a Harbor environment: `network_policy.network_mode.value` and an awaitable
`exec(script, timeout_sec)`.  This supplies that over a container started from an
`EnvironmentSpec`, so an arm episode can run on the same container its capability probes certified.

The container is **persistent for the episode**.  A fresh `docker run` per command would discard
every file the agent wrote, which would make multi-step work impossible and quietly turn every
task into a false impossibility.

All subprocess work goes through `mira_core.process`: bytes transport, explicit UTF-8, and
whole-tree termination on timeout.
"""
from __future__ import annotations

from dataclasses import dataclass
import subprocess
import uuid

from metamorphosis.m072_task_bank import EnvironmentSpec
from mira_core.process import ProcessSupervisorError, run_utf8_process


class DockerEnvironmentError(RuntimeError):
    """Raised when a task container cannot be started, used or removed."""


@dataclass(frozen=True)
class DockerExecResult:
    stdout: str
    stderr: str
    return_code: int


class _Mode:
    def __init__(self, value: str) -> None:
        self.value = value


class _NetworkPolicy:
    def __init__(self, value: str) -> None:
        self.network_mode = _Mode(value)


class DockerTaskEnvironment:
    """One disposable container, alive for the length of one episode."""

    def __init__(self, spec: EnvironmentSpec, *, startup_timeout_seconds: int = 120) -> None:
        self.spec = spec
        self.network_policy = _NetworkPolicy(
            "no-network" if spec.network == "none" else spec.network
        )
        self._startup_timeout = startup_timeout_seconds
        self._container_id: str | None = None

    @property
    def container_id(self) -> str:
        if self._container_id is None:
            raise DockerEnvironmentError("task container is not running")
        return self._container_id

    def start(self) -> str:
        if self._container_id is not None:
            raise DockerEnvironmentError("task container is already running")
        name = f"mira-m072-{uuid.uuid4().hex[:12]}"
        argv = ["docker", "run", "--detach", "--rm", "--name", name,
                f"--network={self.spec.network}"]
        if self.spec.read_only:
            argv.append("--read-only")
        argv.extend([self.spec.image, "sleep", "infinity"])
        try:
            completed = run_utf8_process(argv, timeout_seconds=self._startup_timeout)
        except (ProcessSupervisorError, subprocess.TimeoutExpired, UnicodeError) as exc:
            raise DockerEnvironmentError(
                f"task container could not start: {type(exc).__name__}"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-500:]
            raise DockerEnvironmentError(f"task container failed to start: {detail}")
        self._container_id = name
        return name

    def stop(self) -> None:
        if self._container_id is None:
            return
        try:
            run_utf8_process(
                ["docker", "rm", "--force", self._container_id], timeout_seconds=60,
            )
        except (ProcessSupervisorError, subprocess.TimeoutExpired, UnicodeError):
            pass
        finally:
            self._container_id = None

    def __enter__(self) -> "DockerTaskEnvironment":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    async def exec(self, script: str, timeout_sec: int | None = None) -> DockerExecResult:
        """Run one shell script inside the live container."""

        if not isinstance(script, str) or not script:
            raise DockerEnvironmentError("container exec requires a non-empty script")
        argv = ["docker", "exec", self.container_id, "sh", "-lc", script]
        try:
            completed = run_utf8_process(
                argv, timeout_seconds=float(timeout_sec or 60),
            )
        except subprocess.TimeoutExpired:
            return DockerExecResult("", "command exceeded its time budget", 124)
        except (ProcessSupervisorError, UnicodeError) as exc:
            raise DockerEnvironmentError(
                f"container exec transport failed: {type(exc).__name__}"
            ) from exc
        return DockerExecResult(
            completed.stdout, completed.stderr, int(completed.returncode),
        )


__all__ = ["DockerEnvironmentError", "DockerExecResult", "DockerTaskEnvironment"]
