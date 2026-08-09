"""Governed real-filesystem and subprocess body for Mira.

This module deliberately calls itself a governed workspace, not an operating-system security
sandbox.  File actions are confined to one resolved root and policies can only select immutable
commands registered by the human/evaluator.  Registered processes are still trusted host code;
strong isolation requires a separate container or VM boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from typing import Mapping, Sequence

from mira_core.contracts import Action, Goal, JsonValue, Observation
from mira_core.safety import Authority


class TerminalBodyError(ValueError):
    """Raised when a terminal action violates its governed workspace contract."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class TerminalLimits:
    max_files: int = 256
    max_workspace_bytes: int = 1_048_576
    max_read_bytes: int = 65_536
    max_write_bytes: int = 65_536
    max_output_bytes: int = 65_536

    def __post_init__(self) -> None:
        if min(
            self.max_files, self.max_workspace_bytes, self.max_read_bytes,
            self.max_write_bytes, self.max_output_bytes,
        ) < 1:
            raise TerminalBodyError("terminal resource limits must be positive")


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    argv: tuple[str, ...]
    required_authorities: tuple[str, ...] = (
        Authority.COMPUTE.value, Authority.FILESYSTEM_READ.value,
    )
    working_directory: str = "."
    timeout_seconds: float = 10.0
    terminal_on_success: bool = False
    expose_output: bool = True

    def __post_init__(self) -> None:
        if not self.command_id or not self.argv or any(not isinstance(item, str) or not item for item in self.argv):
            raise TerminalBodyError("a registered command requires an identifier and argv")
        executable = Path(self.argv[0])
        if not executable.is_absolute():
            raise TerminalBodyError("registered command executables must use absolute paths")
        if self.timeout_seconds <= 0:
            raise TerminalBodyError("registered command timeout must be positive")
        if len(set(self.required_authorities)) != len(self.required_authorities):
            raise TerminalBodyError("registered command authorities must be unique")
        if Authority.COMPUTE.value not in self.required_authorities:
            raise TerminalBodyError("registered commands require compute authority")
        if Path(self.working_directory).is_absolute():
            raise TerminalBodyError("registered command working directories must be relative")

    def public_dict(self) -> dict[str, JsonValue]:
        return {
            "command_id": self.command_id,
            "required_authorities": list(self.required_authorities),
            "terminal_on_success": self.terminal_on_success,
            "output_visible": self.expose_output,
        }


@dataclass(frozen=True)
class _ProcessResult:
    returncode: int
    output: bytes
    timed_out: bool
    output_truncated: bool


class GovernedTerminalBody:
    """A bounded body over a real directory and evaluator-registered host commands."""

    FILE_ACTION_AUTHORITIES = {
        "list_files": (Authority.FILESYSTEM_READ.value,),
        "read_text": (Authority.FILESYSTEM_READ.value,),
        "write_text": (Authority.FILESYSTEM_WRITE.value,),
    }

    def __init__(
        self, body_id: str, workspace_root: Path, commands: Sequence[CommandSpec] = (), *,
        limits: TerminalLimits | None = None,
    ) -> None:
        if not body_id:
            raise TerminalBodyError("terminal body requires an identifier")
        root = Path(workspace_root)
        if not root.exists() or not root.is_dir():
            raise TerminalBodyError("terminal workspace root must be an existing directory")
        if root.is_symlink():
            raise TerminalBodyError("terminal workspace root cannot be a symbolic link")
        self._root = root.resolve(strict=True)
        command_map = {command.command_id: command for command in commands}
        if len(command_map) != len(commands):
            raise TerminalBodyError("registered terminal command identifiers must be unique")
        self.body_id = body_id
        self._commands = command_map
        self.limits = limits or TerminalLimits()
        self._step = 0
        self._goal_id: str | None = None
        self._workspace_snapshot()

    @property
    def workspace_root(self) -> Path:
        return self._root

    def required_authorities(self, action: Action) -> tuple[str, ...]:
        if action.kind in self.FILE_ACTION_AUTHORITIES:
            expected_payloads = {
                "list_files": set(),
                "read_text": {"path"},
                "write_text": {"path", "content"},
            }
            if set(action.payload) != expected_payloads[action.kind]:
                raise TerminalBodyError("terminal file action payload does not match its fixed schema")
            return self.FILE_ACTION_AUTHORITIES[action.kind]
        if action.kind == "run_command":
            if set(action.payload) != {"command_id"}:
                raise TerminalBodyError("terminal commands do not accept policy-supplied arguments")
            command_id = action.payload.get("command_id")
            if not isinstance(command_id, str) or command_id not in self._commands:
                raise TerminalBodyError("terminal action names an unknown registered command")
            return self._commands[command_id].required_authorities
        raise TerminalBodyError(f"terminal body does not support action kind {action.kind!r}")

    def reset(self, goal: Goal) -> Observation:
        self._step = 0
        self._goal_id = goal.goal_id
        return self._observation("reset", {
            "event": "workspace_reset",
            "affordances": self._affordances(),
            "commands": [command.public_dict() for command in self._commands.values()],
        })

    def act(self, action: Action) -> Observation:
        if self._goal_id is None:
            raise TerminalBodyError("terminal body must be reset before acting")
        self._step += 1
        if action.kind == "list_files":
            return self._observation("list", {
                "event": "files_listed",
                "files": self._workspace_snapshot()["files"],
            })
        if action.kind == "read_text":
            return self._read_text(action)
        if action.kind == "write_text":
            return self._write_text(action)
        if action.kind == "run_command":
            return self._run_command(action)
        raise TerminalBodyError(f"terminal body does not support action kind {action.kind!r}")

    def _affordances(self) -> list[JsonValue]:
        values: list[JsonValue] = [
            {"kind": kind, "required_authorities": list(authorities)}
            for kind, authorities in self.FILE_ACTION_AUTHORITIES.items()
        ]
        values.append({
            "kind": "run_command",
            "registered_command_only": True,
            "policy_supplied_arguments": False,
        })
        return values

    def _resolve_relative(self, raw: object, *, must_exist: bool = False) -> Path:
        if not isinstance(raw, str) or not raw or "\0" in raw:
            raise TerminalBodyError("terminal path must be a non-empty string")
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise TerminalBodyError("terminal path must remain relative to the workspace")
        lexical = self._root / relative
        current = lexical
        while current != self._root:
            if current.is_symlink():
                raise TerminalBodyError("terminal actions do not follow symbolic links")
            current = current.parent
        candidate = lexical.resolve(strict=must_exist)
        if not candidate.is_relative_to(self._root):
            raise TerminalBodyError("terminal path escapes the governed workspace")
        return candidate

    def _workspace_snapshot(self) -> dict[str, JsonValue]:
        files: list[dict[str, JsonValue]] = []
        total_bytes = 0
        for path in sorted(self._root.rglob("*"), key=lambda value: value.relative_to(self._root).as_posix()):
            if path.is_symlink():
                raise TerminalBodyError("terminal workspace cannot contain symbolic links")
            if not path.is_file():
                continue
            data = path.read_bytes()
            total_bytes += len(data)
            files.append({
                "path": path.relative_to(self._root).as_posix(),
                "bytes": len(data),
                "sha256": _sha256(data),
            })
            if len(files) > self.limits.max_files or total_bytes > self.limits.max_workspace_bytes:
                raise TerminalBodyError("terminal workspace exceeds its frozen resource limits")
        digest = _sha256(_canonical_json(files))
        return {"digest": digest, "file_count": len(files), "total_bytes": total_bytes, "files": files}

    def _observation(
        self, suffix: str, detail: Mapping[str, JsonValue], *, terminal: bool = False,
        success: bool = False, error: str | None = None,
    ) -> Observation:
        state: dict[str, JsonValue] = {
            **dict(detail),
            "body_id": self.body_id,
            "goal_id": self._goal_id,
            "step": self._step,
            "workspace": self._workspace_snapshot(),
        }
        return Observation(
            f"{self.body_id}:{self._step}:{suffix}", state,
            terminal=terminal, success=success, error=error,
        )

    def _read_text(self, action: Action) -> Observation:
        path = self._resolve_relative(action.payload.get("path"), must_exist=True)
        if not path.is_file():
            raise TerminalBodyError("terminal read target is not a regular file")
        data = path.read_bytes()
        if len(data) > self.limits.max_read_bytes:
            raise TerminalBodyError("terminal read exceeds the bounded read size")
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TerminalBodyError("terminal text reads require UTF-8") from exc
        return self._observation("read", {
            "event": "text_read",
            "path": path.relative_to(self._root).as_posix(),
            "content": content,
            "content_sha256": _sha256(data),
        })

    def _write_text(self, action: Action) -> Observation:
        content = action.payload.get("content")
        if not isinstance(content, str):
            raise TerminalBodyError("terminal text writes require string content")
        data = content.encode("utf-8")
        if len(data) > self.limits.max_write_bytes:
            raise TerminalBodyError("terminal write exceeds the bounded write size")
        path = self._resolve_relative(action.payload.get("path"))
        if not path.parent.exists() or not path.parent.is_dir():
            raise TerminalBodyError("terminal write parent must already exist")
        if path.exists() and (path.is_symlink() or not path.is_file()):
            raise TerminalBodyError("terminal write target is not a regular file")
        before = _sha256(path.read_bytes()) if path.exists() else None
        descriptor, temporary_name = tempfile.mkstemp(prefix=".mira-write-", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return self._observation("write", {
            "event": "text_written",
            "path": path.relative_to(self._root).as_posix(),
            "before_sha256": before,
            "after_sha256": _sha256(data),
            "bytes": len(data),
        })

    def _run_command(self, action: Action) -> Observation:
        command_id = action.payload.get("command_id")
        if not isinstance(command_id, str) or command_id not in self._commands:
            raise TerminalBodyError("terminal action names an unknown registered command")
        command = self._commands[command_id]
        working_directory = self._resolve_relative(command.working_directory, must_exist=True)
        if not working_directory.is_dir():
            raise TerminalBodyError("registered command working directory is not a directory")
        result = self._bounded_process(command, working_directory)
        succeeded = (
            result.returncode == 0 and not result.timed_out and not result.output_truncated
        )
        terminal = command.terminal_on_success and succeeded
        output_text = result.output.decode("utf-8", "replace").replace("\r\n", "\n")
        detail: dict[str, JsonValue] = {
            "event": "command_finished",
            "command_id": command.command_id,
            "returncode": result.returncode,
            "timed_out": result.timed_out,
            "output_truncated": result.output_truncated,
            "output_bytes": len(result.output),
            "output_sha256": _sha256(result.output),
            "output": output_text if command.expose_output else None,
        }
        error = None
        if result.timed_out:
            error = "registered command exceeded its time limit"
        elif result.output_truncated:
            error = "registered command exceeded its output limit"
        return self._observation(
            "command", detail, terminal=terminal, success=terminal, error=error,
        )

    def _bounded_process(self, command: CommandSpec, cwd: Path) -> _ProcessResult:
        environment = {
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "MIRA_NETWORK_AUTHORITY": "denied",
        }
        if os.name == "nt":
            for name in ("SystemRoot", "WINDIR"):
                value = os.environ.get(name)
                if value:
                    environment[name] = value
        try:
            process = subprocess.Popen(
                command.argv,
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                close_fds=True,
            )
        except OSError as exc:
            raise TerminalBodyError(f"registered terminal command could not start: {type(exc).__name__}") from exc
        assert process.stdout is not None
        captured = bytearray()
        output_truncated = threading.Event()

        def read_output() -> None:
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    return
                remaining = self.limits.max_output_bytes - len(captured)
                if remaining <= 0:
                    output_truncated.set()
                    process.kill()
                    return
                captured.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    output_truncated.set()
                    process.kill()
                    return

        reader = threading.Thread(target=read_output, name=f"mira-output-{command.command_id}", daemon=True)
        reader.start()
        timed_out = False
        try:
            process.wait(timeout=command.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        reader.join(timeout=5.0)
        if reader.is_alive():
            process.kill()
            raise TerminalBodyError("registered terminal command output reader did not stop")
        process.stdout.close()
        return _ProcessResult(
            int(process.returncode), bytes(captured), timed_out, output_truncated.is_set(),
        )


__all__ = [
    "CommandSpec", "GovernedTerminalBody", "TerminalBodyError", "TerminalLimits",
]
