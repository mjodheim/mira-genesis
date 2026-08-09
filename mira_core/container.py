"""OS-isolated Docker body for post-design external software tasks.

Unlike :mod:`mira_core.terminal`, policy-supplied commands run inside a separately created Linux
container.  The host repository, Docker socket, network, credentials and ambient environment are
not mounted.  Task success is deliberately left to an evaluator outside the agent loop.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
from typing import Mapping, Protocol, Sequence

from mira_core.contracts import Action, Goal, JsonValue, Observation
from mira_core.safety import Authority


class ContainerBodyError(RuntimeError):
    """Raised when the isolated container contract cannot be upheld."""


_DIGEST_IMAGE = re.compile(r"^[a-zA-Z0-9._/-]+@sha256:[0-9a-f]{64}$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class ContainerLimits:
    max_steps: int = 64
    max_script_bytes: int = 16_384
    max_output_bytes: int = 65_536
    timeout_seconds: float = 120.0
    memory_bytes: int = 1_073_741_824
    cpus: float = 1.0
    pids_limit: int = 256
    tmpfs_bytes: int = 134_217_728

    def __post_init__(self) -> None:
        if min(
            self.max_steps, self.max_script_bytes, self.max_output_bytes,
            self.timeout_seconds, self.memory_bytes, self.cpus, self.pids_limit,
            self.tmpfs_bytes,
        ) <= 0:
            raise ContainerBodyError("container resource limits must be positive")


@dataclass(frozen=True)
class ContainerSpec:
    image: str
    shell: tuple[str, ...] = ("/bin/sh", "-lc")
    working_directory: str = "/workspace"
    user: str | None = None

    def __post_init__(self) -> None:
        if not _DIGEST_IMAGE.fullmatch(self.image):
            raise ContainerBodyError("container image must be pinned by sha256 repository digest")
        if not self.shell or any(not item or "\0" in item for item in self.shell):
            raise ContainerBodyError("container shell argv must be explicit and non-empty")
        if not self.working_directory.startswith("/") or "\0" in self.working_directory:
            raise ContainerBodyError("container working directory must be absolute")
        if self.user is not None and (not self.user or "\0" in self.user):
            raise ContainerBodyError("container user must be null or a non-empty identifier")


@dataclass(frozen=True)
class ContainerExecResult:
    returncode: int | None
    output: bytes
    timed_out: bool = False
    output_truncated: bool = False


class ContainerEngine(Protocol):
    @property
    def engine_id(self) -> str: ...

    def verify_image(self, image: str) -> str: ...

    def create(
        self, spec: ContainerSpec, workspace: Path, limits: ContainerLimits,
    ) -> str: ...

    def start(self, container_id: str) -> None: ...

    def inspect_isolation(self, container_id: str) -> Mapping[str, JsonValue]: ...

    def execute(
        self, container_id: str, argv: Sequence[str], *, timeout_seconds: float,
        max_output_bytes: int,
    ) -> ContainerExecResult: ...

    def remove(self, container_id: str) -> None: ...


@dataclass(frozen=True)
class DockerCliEngine:
    """Docker CLI implementation with no host shell and bounded untrusted output."""

    executable: Path
    engine_id: str = "docker-cli-isolation-v1"

    def __post_init__(self) -> None:
        path = Path(self.executable)
        if not path.is_absolute() or not path.exists():
            raise ContainerBodyError("Docker engine requires an existing absolute CLI executable")

    def verify_image(self, image: str) -> str:
        completed = self._trusted((
            "image", "inspect", image, "--format", "{{index .RepoDigests 0}}",
        ))
        resolved = completed.stdout.strip()
        if resolved != image:
            raise ContainerBodyError(
                f"local image digest mismatch: expected {image!r}, observed {resolved!r}"
            )
        return resolved

    def create(
        self, spec: ContainerSpec, workspace: Path, limits: ContainerLimits,
    ) -> str:
        mount = f"type=bind,source={workspace.resolve()},target={spec.working_directory}"
        argv = [
            "create", "--init", "--network", "none", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--read-only",
            "--pids-limit", str(limits.pids_limit), "--memory", str(limits.memory_bytes),
            "--cpus", str(limits.cpus), "--tmpfs",
            f"/tmp:rw,nosuid,nodev,size={limits.tmpfs_bytes}", "--mount", mount,
            "--workdir", spec.working_directory,
        ]
        if spec.user is not None:
            argv.extend(("--user", spec.user))
        argv.extend((
            "--entrypoint", spec.shell[0], spec.image,
            *spec.shell[1:], "trap : TERM INT; sleep infinity & wait",
        ))
        completed = self._trusted(tuple(argv))
        container_id = completed.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{12,64}", container_id):
            raise ContainerBodyError("Docker did not return a valid container identifier")
        return container_id

    def start(self, container_id: str) -> None:
        self._trusted(("start", container_id))

    def inspect_isolation(self, container_id: str) -> Mapping[str, JsonValue]:
        completed = self._trusted(("inspect", container_id))
        try:
            value = json.loads(completed.stdout)
            record = value[0]
            host = record["HostConfig"]
            mounts = record["Mounts"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ContainerBodyError("Docker isolation inspection returned an invalid record") from exc
        return {
            "network_mode": host.get("NetworkMode"),
            "cap_drop": sorted(host.get("CapDrop") or []),
            "security_opt": sorted(host.get("SecurityOpt") or []),
            "read_only_rootfs": host.get("ReadonlyRootfs"),
            "memory_bytes": host.get("Memory"),
            "nano_cpus": host.get("NanoCpus"),
            "pids_limit": host.get("PidsLimit"),
            "mounts": [
                {
                    "type": mount.get("Type"),
                    "destination": mount.get("Destination"),
                    "rw": mount.get("RW"),
                }
                for mount in mounts
            ],
        }

    def execute(
        self, container_id: str, argv: Sequence[str], *, timeout_seconds: float,
        max_output_bytes: int,
    ) -> ContainerExecResult:
        command = [str(self.executable), "exec", container_id, *argv]
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = bytearray()
        truncated = False

        def drain() -> None:
            nonlocal truncated
            assert process.stdout is not None
            while True:
                chunk = process.stdout.read(8_192)
                if not chunk:
                    break
                remaining = max_output_bytes - len(output)
                if remaining > 0:
                    output.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated = True

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait(timeout=10)
            self._trusted(("kill", container_id), check=False)
        reader.join(timeout=10)
        if reader.is_alive():
            process.kill()
            raise ContainerBodyError("Docker output reader did not terminate")
        return ContainerExecResult(
            process.returncode, bytes(output), timed_out=timed_out,
            output_truncated=truncated,
        )

    def remove(self, container_id: str) -> None:
        self._trusted(("rm", "--force", container_id), check=False)

    def _trusted(
        self, args: Sequence[str], *, check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                [str(self.executable), *args], stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=60, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ContainerBodyError(f"Docker control command failed: {type(exc).__name__}") from exc
        if check and completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-2_000:]
            raise ContainerBodyError(
                f"Docker control command exited {completed.returncode}: {detail}"
            )
        return completed


class IsolatedContainerBody:
    """A bounded policy interface to one disposable, networkless task container."""

    EXEC_AUTHORITIES = (
        Authority.COMPUTE.value, Authority.FILESYSTEM_READ.value,
        Authority.FILESYSTEM_WRITE.value,
    )

    def __init__(
        self, body_id: str, workspace_root: Path, spec: ContainerSpec,
        engine: ContainerEngine, *, limits: ContainerLimits | None = None,
    ) -> None:
        if not body_id:
            raise ContainerBodyError("container body requires an identifier")
        workspace = Path(workspace_root)
        if not workspace.exists() or not workspace.is_dir() or workspace.is_symlink():
            raise ContainerBodyError("container workspace must be an existing non-symlink directory")
        self.body_id = body_id
        self.workspace_root = workspace.resolve(strict=True)
        self.spec = spec
        self.engine = engine
        self.limits = limits or ContainerLimits()
        self._container_id: str | None = None
        self._goal_id: str | None = None
        self._step = 0
        self._closed = False

    def required_authorities(self, action: Action) -> tuple[str, ...]:
        if action.kind == "container_exec":
            if set(action.payload) != {"script"}:
                raise ContainerBodyError("container exec action has a closed payload schema")
            script = action.payload.get("script")
            if not isinstance(script, str) or not script or "\0" in script:
                raise ContainerBodyError("container exec requires a non-empty text script")
            if len(script.encode("utf-8")) > self.limits.max_script_bytes:
                raise ContainerBodyError("container script exceeds its byte budget")
            return self.EXEC_AUTHORITIES
        if action.kind == "container_submit":
            if action.payload:
                raise ContainerBodyError("container submission accepts no policy payload")
            return ()
        raise ContainerBodyError(f"container body does not support {action.kind!r}")

    def reset(self, goal: Goal) -> Observation:
        if self._closed:
            raise ContainerBodyError("closed container bodies cannot be reset")
        if self._container_id is not None:
            raise ContainerBodyError("container body supports one episode only")
        resolved = self.engine.verify_image(self.spec.image)
        container_id = self.engine.create(self.spec, self.workspace_root, self.limits)
        try:
            self.engine.start(container_id)
            isolation = self.engine.inspect_isolation(container_id)
            self._verify_isolation(isolation)
        except Exception:
            self.engine.remove(container_id)
            raise
        self._container_id = container_id
        self._goal_id = goal.goal_id
        self._step = 0
        return self._observation("reset", {
            "event": "isolated_container_started",
            "engine_id": self.engine.engine_id,
            "image": resolved,
            "network": "none",
            "capabilities": [],
            "no_new_privileges": True,
            "read_only_rootfs": True,
            "workspace_mount": "read_write_task_only",
            "host_repository_mounted": False,
            "docker_socket_mounted": False,
            "success_decided_externally": True,
            "isolation_evidence_digest": _sha256(_canonical_json(isolation)),
        })

    def act(self, action: Action) -> Observation:
        if self._container_id is None or self._goal_id is None or self._closed:
            raise ContainerBodyError("container body must be active before acting")
        self._step += 1
        if self._step > self.limits.max_steps:
            return self._observation(
                "budget", {"event": "container_action_budget_exhausted"},
                terminal=True, error="container action budget exhausted",
            )
        if action.kind == "container_submit":
            return self._observation(
                "submitted", {
                    "event": "workspace_submitted_for_external_evaluation",
                    "agent_claimed_success": False,
                }, terminal=True, success=False,
            )
        if action.kind != "container_exec":
            raise ContainerBodyError(f"container body does not support {action.kind!r}")
        script = action.payload.get("script")
        if not isinstance(script, str):
            raise ContainerBodyError("container exec requires a text script")
        result = self.engine.execute(
            self._container_id, (*self.spec.shell, script),
            timeout_seconds=self.limits.timeout_seconds,
            max_output_bytes=self.limits.max_output_bytes,
        )
        normal = not result.timed_out and not result.output_truncated
        output = result.output.decode("utf-8", "replace").replace("\r\n", "\n")
        detail: dict[str, JsonValue] = {
            "event": "isolated_command_finished",
            "returncode": result.returncode,
            "timed_out": result.timed_out,
            "output_truncated": result.output_truncated,
            "output_bytes": len(result.output),
            "output_sha256": _sha256(result.output),
            "output": output,
        }
        if not normal:
            return self._observation(
                "command_stopped", detail, terminal=True, success=False,
                error=(
                    "isolated command exceeded its time budget" if result.timed_out
                    else "isolated command exceeded its output budget"
                ),
            )
        return self._observation("command", detail)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._container_id is not None:
            self.engine.remove(self._container_id)

    def __enter__(self) -> "IsolatedContainerBody":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _observation(
        self, suffix: str, detail: Mapping[str, JsonValue], *, terminal: bool = False,
        success: bool = False, error: str | None = None,
    ) -> Observation:
        state: dict[str, JsonValue] = {
            **dict(detail), "body_id": self.body_id, "goal_id": self._goal_id,
            "step": self._step,
        }
        state["state_digest"] = _sha256(_canonical_json(state))
        return Observation(
            f"{self.body_id}:{self._step}:{suffix}", state,
            terminal=terminal, success=success, error=error,
        )

    def _verify_isolation(self, observed: Mapping[str, JsonValue]) -> None:
        expected = {
            "network_mode": "none",
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "read_only_rootfs": True,
            "memory_bytes": self.limits.memory_bytes,
            "nano_cpus": int(self.limits.cpus * 1_000_000_000),
            "pids_limit": self.limits.pids_limit,
            "mounts": [{
                "type": "bind", "destination": self.spec.working_directory, "rw": True,
            }],
        }
        if observed != expected:
            raise ContainerBodyError("Docker did not realize the required isolation contract")
