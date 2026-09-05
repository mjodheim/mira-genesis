"""Locale-independent subprocess transport with whole-tree termination.

All policy-adjacent host processes are started without a shell in a distinct process group.
Text transport is encoded and decoded explicitly as UTF-8 so the ambient Windows code page cannot
change behaviour. Timeouts terminate the process tree rather than only its visible parent.
"""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
from typing import Mapping, Sequence
import weakref


class ProcessSupervisorError(RuntimeError):
    """Raised when a supervised process tree cannot be started or stopped safely."""


_WINDOWS_JOB_ATTR = "_mira_windows_job_handle"
_WINDOWS_JOB_FINALIZER_ATTR = "_mira_windows_job_finalizer"
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9


def _windows_api():
    """Return the small kernel32 surface used for Windows job-object supervision."""

    import ctypes
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return ctypes, wintypes, kernel32, JOBOBJECT_EXTENDED_LIMIT_INFORMATION


def _create_windows_job() -> int:
    ctypes, _wintypes, kernel32, info_type = _windows_api()
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ProcessSupervisorError(
            f"Windows job object could not be created: WinError {ctypes.get_last_error()}"
        )
    info = info_type()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        handle, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(info), ctypes.sizeof(info),
    ):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(handle)
        raise ProcessSupervisorError(
            f"Windows job object could not be configured: WinError {error}"
        )
    return int(handle)


def _close_windows_job_handle(handle: int) -> None:
    if not handle:
        return
    _ctypes, wintypes, kernel32, _info_type = _windows_api()
    kernel32.CloseHandle(wintypes.HANDLE(handle))


def _assign_windows_job(process: subprocess.Popen[bytes], handle: int) -> None:
    ctypes, wintypes, kernel32, _info_type = _windows_api()
    process_handle = getattr(process, "_handle", None)
    if process_handle is None or not kernel32.AssignProcessToJobObject(
        wintypes.HANDLE(handle), wintypes.HANDLE(int(process_handle)),
    ):
        error = ctypes.get_last_error()
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        _close_windows_job_handle(handle)
        raise ProcessSupervisorError(
            f"Windows process could not be attached to its supervision job: WinError {error}"
        )
    setattr(process, _WINDOWS_JOB_ATTR, handle)
    setattr(
        process, _WINDOWS_JOB_FINALIZER_ATTR,
        weakref.finalize(process, _close_windows_job_handle, handle),
    )


def _terminate_windows_job(process: subprocess.Popen[bytes]) -> bool:
    """Terminate the attached Windows job, returning False for legacy unbound processes."""

    handle = getattr(process, _WINDOWS_JOB_ATTR, None)
    if not isinstance(handle, int) or not handle:
        return False
    ctypes, wintypes, kernel32, _info_type = _windows_api()
    if not kernel32.TerminateJobObject(wintypes.HANDLE(handle), 1):
        raise ProcessSupervisorError(
            f"Windows process job could not be terminated: WinError {ctypes.get_last_error()}"
        )
    return True


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
    windows_job: int | None = None
    if os.name == "nt":
        windows_job = _create_windows_job()
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    try:
        process = subprocess.Popen(list(argv), **options)  # type: ignore[arg-type]
    except OSError as exc:
        if windows_job is not None:
            _close_windows_job_handle(windows_job)
        raise ProcessSupervisorError(
            f"process could not start: {type(exc).__name__}"
        ) from exc
    if windows_job is not None:
        _assign_windows_job(process, windows_job)
    return process


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
        if not _terminate_windows_job(process):
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
    if process.poll() is None:
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
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as cleanup_exc:
            raise ProcessSupervisorError(
                "process pipes did not close within the cleanup budget"
            ) from cleanup_exc
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
