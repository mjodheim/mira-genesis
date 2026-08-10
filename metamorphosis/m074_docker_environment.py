"""Persistent, materialized and externally evaluated M074 Docker environment.

**Draft apparatus. Nothing here is frozen and no result may cite it.**

The agent receives a read-only root filesystem, a bounded tmpfs workspace, no network, no Linux
capabilities, ``no-new-privileges`` and a non-root identity.  The harness writes fixtures as root,
sets their final modes, then drops the workspace mode before any probe or agent action.  Capability
probes and the episode therefore observe the same persistent container state.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
import shlex
import subprocess
import uuid

from metamorphosis.m074_task_bank import BankTask, FixtureFile
from mira_core.calibration import CapabilityProbe
from mira_core.process import ProcessSupervisorError, run_utf8_process


class DockerEnvironmentError(RuntimeError):
    """Raised when a task container cannot be started, materialized, used or removed."""


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
    """One disposable task container, alive through probe, episode and external evaluation."""

    def __init__(self, task: BankTask, *, startup_timeout_seconds: int = 120) -> None:
        self.task = task
        self.spec = task.environment
        self.network_policy = _NetworkPolicy("no-network")
        self._startup_timeout = startup_timeout_seconds
        self._container_id: str | None = None

    @property
    def container_id(self) -> str:
        if self._container_id is None:
            raise DockerEnvironmentError("task container is not running")
        return self._container_id

    @property
    def environment_sha256(self) -> str:
        return self.task.environment_digest()

    def _run(
        self, argv: list[str], *, timeout_seconds: float,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return run_utf8_process(
                argv, timeout_seconds=timeout_seconds, input_text=input_text,
            )
        except (ProcessSupervisorError, subprocess.TimeoutExpired, UnicodeError) as exc:
            raise DockerEnvironmentError(
                f"container transport failed: {type(exc).__name__}"
            ) from exc

    def _root_exec(
        self, script: str, *, input_text: str | None = None, timeout_seconds: float = 60,
    ) -> DockerExecResult:
        argv = ["docker", "exec", "--user", "0:0", "--workdir", "/workspace"]
        if input_text is not None:
            argv.append("--interactive")
        argv.extend([self.container_id, "sh", "-lc", script])
        completed = self._run(argv, timeout_seconds=timeout_seconds, input_text=input_text)
        return DockerExecResult(completed.stdout, completed.stderr, int(completed.returncode))

    @staticmethod
    def _fixture_path(fixture: FixtureFile) -> str:
        path = PurePosixPath(fixture.relative_path)
        # FixtureFile already validates this; retaining the check at the command boundary makes a
        # future caller error fail closed instead of becoming a shell path.
        if path.is_absolute() or ".." in path.parts:
            raise DockerEnvironmentError("fixture escaped /workspace")
        return f"/workspace/{path}"

    def _materialize(self) -> None:
        for fixture in self.task.fixture_files:
            destination = self._fixture_path(fixture)
            parent = str(PurePosixPath(destination).parent)
            script = (
                f"mkdir -p {shlex.quote(parent)} && "
                f"cat > {shlex.quote(destination)} && "
                f"chmod {fixture.mode:04o} {shlex.quote(destination)}"
            )
            outcome = self._root_exec(script, input_text=fixture.content)
            if outcome.return_code != 0:
                raise DockerEnvironmentError(
                    f"fixture {fixture.relative_path!r} could not be materialized: "
                    f"{(outcome.stderr or outcome.stdout).strip()[-300:]}"
                )
        workspace_mode = "0777" if self.spec.workspace_writable else "0555"
        outcome = self._root_exec(f"chmod {workspace_mode} /workspace")
        if outcome.return_code != 0:
            raise DockerEnvironmentError("workspace permissions could not be finalized")

    def start(self) -> str:
        if self._container_id is not None:
            raise DockerEnvironmentError("task container is already running")
        name = f"mira-m074-{uuid.uuid4().hex[:12]}"
        try:
            completed = self._run(
                list(self.spec.docker_start_argv(name)),
                timeout_seconds=self._startup_timeout,
            )
        except DockerEnvironmentError:
            self._container_id = None
            raise
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-500:]
            raise DockerEnvironmentError(f"task container failed to start: {detail}")
        self._container_id = name
        try:
            self._materialize()
        except Exception:
            self.stop()
            raise
        return name

    def stop(self) -> None:
        if self._container_id is None:
            return
        container = self._container_id
        try:
            run_utf8_process(
                ["docker", "rm", "--force", container], timeout_seconds=60,
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

    def _agent_argv(self, *command: str) -> list[str]:
        return [
            "docker", "exec", "--user", f"{self.spec.agent_uid}:{self.spec.agent_gid}",
            "--workdir", "/workspace", self.container_id, *command,
        ]

    def execute_probe(self, probe: CapabilityProbe) -> tuple[int | None, bool]:
        """Run a probe as the exact non-root identity used by the agent."""

        try:
            completed = self._run(
                self._agent_argv(*probe.argv), timeout_seconds=30,
            )
        except DockerEnvironmentError:
            return None, False
        if completed.returncode == 125:
            return None, False
        return int(completed.returncode), True

    def inspect_security_boundary(self) -> dict[str, object]:
        """Attest Docker's realized boundary before a scientific model decision.

        The start argv is only an intention.  This read-back makes a daemon-side discrepancy a
        fail-closed protocol defect and records the concrete fields needed for later verification.
        """

        completed = self._run(
            ["docker", "inspect", self.container_id], timeout_seconds=30,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-500:]
            raise DockerEnvironmentError(f"container boundary could not be inspected: {detail}")
        try:
            decoded = json.loads(completed.stdout)
            value = decoded[0]
            config = value["Config"]
            host = value["HostConfig"]
            state = value["State"]
        except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise DockerEnvironmentError("container inspection response is malformed") from exc
        tmpfs = host.get("Tmpfs") or {}
        security_options = host.get("SecurityOpt") or []
        cap_drop = host.get("CapDrop") or []
        observed = {
            "image": config.get("Image"),
            "running": state.get("Running"),
            "network_mode": host.get("NetworkMode"),
            "root_filesystem_read_only": host.get("ReadonlyRootfs"),
            "cap_drop": list(cap_drop) if isinstance(cap_drop, list) else cap_drop,
            "security_options": (
                list(security_options) if isinstance(security_options, list) else security_options
            ),
            "memory_bytes": host.get("Memory"),
            "nano_cpus": host.get("NanoCpus"),
            "pids_limit": host.get("PidsLimit"),
            "workspace_tmpfs": tmpfs.get("/workspace") if isinstance(tmpfs, dict) else None,
            "agent_exec_user": f"{self.spec.agent_uid}:{self.spec.agent_gid}",
        }
        expected_tmpfs_tokens = {
            "rw", "nosuid", "nodev", "noexec", "size=16777216",
        }
        raw_tmpfs = observed["workspace_tmpfs"]
        tmpfs_tokens = set(str(raw_tmpfs).split(",")) if isinstance(raw_tmpfs, str) else set()
        observed["matches_declaration"] = all((
            observed["image"] == self.spec.image,
            observed["running"] is True,
            observed["network_mode"] == "none",
            observed["root_filesystem_read_only"] is True,
            isinstance(observed["cap_drop"], list) and "ALL" in observed["cap_drop"],
            isinstance(observed["security_options"], list)
            and any(str(option).startswith("no-new-privileges") for option in observed["security_options"]),
            observed["memory_bytes"] == 256 * 1024 * 1024,
            observed["nano_cpus"] == 1_000_000_000,
            observed["pids_limit"] == self.spec.pids_limit,
            tmpfs_tokens == expected_tmpfs_tokens,
            observed["agent_exec_user"] == "65534:65534",
        ))
        return observed

    async def exec(self, script: str, timeout_sec: int | None = None) -> DockerExecResult:
        """Run one agent-proposed shell script as the non-root task identity."""

        if not isinstance(script, str) or not script:
            raise DockerEnvironmentError("container exec requires a non-empty script")
        try:
            completed = self._run(
                self._agent_argv("sh", "-lc", script),
                timeout_seconds=float(timeout_sec or 60),
            )
        except DockerEnvironmentError as exc:
            if isinstance(exc.__cause__, subprocess.TimeoutExpired):
                return DockerExecResult("", "command exceeded its time budget", 124)
            raise
        return DockerExecResult(
            completed.stdout, completed.stderr, int(completed.returncode),
        )

    def evaluate(self, *, timeout_seconds: int = 30) -> DockerExecResult:
        """Inspect final state as harness-owned code after the agent stops."""

        return self._root_exec(self.task.evaluator_script, timeout_seconds=timeout_seconds)


__all__ = ["DockerEnvironmentError", "DockerExecResult", "DockerTaskEnvironment"]
