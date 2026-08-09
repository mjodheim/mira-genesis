"""Locale-independent subprocess transport with whole-tree termination.

All policy-adjacent host processes are started without a shell in a distinct process group.
Text transport is encoded and decoded explicitly as UTF-8 so the ambient Windows code page cannot
change behaviour.  Timeouts terminate the process tree rather than only its visible parent.
"""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
from typing import Mapping, Sequence


class ProcessSupervisorError(RuntimeError):
    """Raised when a supervised process tree cannot be started or stopped safely."""


def start_process_tree(
    argv: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None,
    stdin: int = subprocess.DEVNULL, stdout: int = subprocess.PIPE,
    stderr: int = subprocess.PIPE,
) -> subprocess.Popen[bytes]:
    """Start one shell-free process in a separately terminable operating-system process tree."""

    if not argv or any(not isinstance(item, str) or not item or "\0" in item for item in argv):
        raise ProcessSupervisorError("process argv must contain explicit non-empty strings")
    options: dict[str, object] = {
        "cwd": cwd,
        "env": dict(env) if env is not None else None,
        "stdin": stdin,
        "stdout": stdout,
        "stderr": stderr,
        "shell": False,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    try:
        return subprocess.Popen(list(argv), **options)  # type: ignore[arg-type]
    except OSError as exc:
        raise ProcessSupervisorError(
            f"process could not start: {type(exc).__name__}"
        ) from exc


def _windows_taskkill_path() -> Path:
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not system_root:
        raise ProcessSupervisorError("Windows process-tree termination lacks SystemRoot")
    executable = (Path(system_root) / "System32" / "taskkill.exe").resolve()
    if not executable.is_file():
        raise ProcessSupervisorError("Windows process-tree terminator is unavailable")
    return executable


def terminate_process_tree(
    process: subprocess.Popen[bytes], *, timeout_seconds: float = 10.0,
) -> None:
    """Force-stop a supervised process and every descendant that still belongs to its tree."""

    if timeout_seconds <= 0:
        raise ValueError("process-tree termination timeout must be positive")
    if os.name == "nt":
        if process.poll() is not None:
            return
        try:
            completed = subprocess.run(
                [str(_windows_taskkill_path()), "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=False, timeout=timeout_seconds, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProcessSupervisorError(
                f"Windows process tree could not be terminated: {type(exc).__name__}"
            ) from exc
        if completed.returncode != 0 and process.poll() is None:
            detail = (completed.stderr or completed.stdout)[-500:].decode("utf-8", "replace")
            raise ProcessSupervisorError(
                f"Windows process-tree termination failed with exit code "
                f"{completed.returncode}: {detail}"
            )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            if process.poll() is None:
                raise ProcessSupervisorError("POSIX process tree disappeared before termination")
        except OSError as exc:
            raise ProcessSupervisorError(
                f"POSIX process tree could not be terminated: {type(exc).__name__}"
            ) from exc
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise ProcessSupervisorError("process tree did not stop within its cleanup budget") from exc


def run_utf8_process(
    argv: Sequence[str], *, input_text: str | None = None, timeout_seconds: float,
    cwd: Path | None = None, env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a supervised process using bytes transport and strict, explicit UTF-8 text decoding."""

    if timeout_seconds <= 0:
        raise ValueError("process timeout must be positive")
    input_bytes = input_text.encode("utf-8") if input_text is not None else None
    process = start_process_tree(
        argv, cwd=cwd, env=env,
        stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(input=input_bytes, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        terminate_process_tree(process)
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(
            list(argv), timeout_seconds, output=stdout, stderr=stderr,
        ) from exc
    return subprocess.CompletedProcess(
        list(argv), int(process.returncode), stdout.decode("utf-8"), stderr.decode("utf-8"),
    )


__all__ = [
    "ProcessSupervisorError", "run_utf8_process", "start_process_tree",
    "terminate_process_tree",
]
