"""Isolated candidate execution, and an honest record of what isolation was actually obtained.

A candidate body is untrusted: it is a transformation the lineage produced, and the whole point of
running it is that nobody yet knows whether it is any good. It must not be able to reach the parent,
the evaluator, the journal or the task oracle.

This module runs candidates in a **separate process** with resource limits applied where the platform
supplies them, and it reports precisely which limits were enforced. That last part matters more than
the limits themselves. Claiming isolation one did not obtain is how a result comes to rest on a
boundary that was never there, and M083 already recorded the honest version of this problem: a
container shares the host kernel, so it is not a desktop VM no matter how convenient that would be.

So `enforced` in the returned record lists what was really applied on this platform, and
`unenforced` lists what was asked for and could not be. A caller that needs a guarantee must read
those fields rather than the request.
"""
from __future__ import annotations

import multiprocessing
import os
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

from genesis.trust_root import Isolation, TrustRootError, digest_of

SANDBOX_SCHEMA = "genesis-sandbox-result-v1"


class SandboxError(RuntimeError):
    """Raised when a candidate could not be run under the limits it was supposed to run under."""


def _apply_limits(isolation: Isolation) -> tuple[list[str], list[str]]:
    """Apply what this platform can enforce; report honestly on the rest."""
    enforced: list[str] = []
    unenforced: list[str] = []
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return [], ["cpu_seconds", "memory_bytes", "wall_clock_seconds"]

    try:
        seconds = max(1, int(isolation.cpu_seconds))
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
        enforced.append("cpu_seconds")
    except (ValueError, OSError):  # pragma: no cover - platform dependent
        unenforced.append("cpu_seconds")

    try:
        limit = int(isolation.memory_bytes)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        enforced.append("memory_bytes")
    except (ValueError, OSError):  # pragma: no cover - platform dependent
        unenforced.append("memory_bytes")

    if not isolation.subprocess_permitted:
        # This call succeeds and does not reliably prevent a fork — a candidate ran /bin/true
        # straight through it. It is kept because it costs nothing and helps where it does work,
        # but the audit guard below is what actually enforces the limit, and the "enforced" entry
        # is added there rather than here so the record does not testify to this call alone.
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
        except (ValueError, OSError):
            unenforced.append("subprocess_permitted")

    # The guard can enforce what `resource` could not: if RLIMIT_NPROC was refused but the audit
    # hook blocks process creation, the honest record is enforced, not unenforced.
    for limit in _install_audit_guard(isolation):
        if limit in unenforced:
            unenforced.remove(limit)
        if limit not in enforced:
            enforced.append(limit)
    return enforced, unenforced


#: Audit events that mutate the filesystem without ever going through `open`.
_MUTATING_FILESYSTEM_EVENTS = frozenset(
    {
        "os.remove",
        "os.rename",
        "os.mkdir",
        "os.rmdir",
        "os.truncate",
        "os.chmod",
        "os.chown",
        "os.link",
        "os.symlink",
        "shutil.copyfile",
        "shutil.copymode",
        "shutil.copystat",
        "shutil.move",
        "shutil.rmtree",
    }
)

#: Audit events that reach the network. `socket.connect` alone catches urllib and http.client.
_NETWORK_EVENTS = frozenset(
    {
        "socket.connect",
        "socket.bind",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.sendto",
    }
)


def _opens_for_writing(arguments) -> bool:
    """Decide write intent from an `open` audit event, whichever way the caller opened the file.

    `open(path, "w")` reports a string mode, but `os.open(path, os.O_WRONLY | os.O_CREAT)` reports
    mode `None` and carries the intent in the flags. A guard that only reads the string mode lets
    the second form straight through, which is how a limit comes to be enforced against the
    convenient spelling and nothing else.
    """
    mode = arguments[1] if len(arguments) > 1 else None
    if isinstance(mode, str):
        return any(flag in mode for flag in "wxa+")
    flags = arguments[2] if len(arguments) > 2 else 0
    if not isinstance(flags, int) or flags < 0:
        # Unreadable intent: refuse rather than guess in the candidate's favour.
        return True
    writing = 0
    for name in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_APPEND", "O_TRUNC"):
        writing |= getattr(os, name, 0)
    return bool(flags & writing)


def _install_audit_guard(isolation: Isolation) -> list[str]:
    """Apply the limits that `Isolation` declares but `resource` cannot express.

    Filesystem writes, network access and subprocesses were declared on `Isolation` and checked by
    `assert_no_wider_than`, and nothing ever applied them: the record said the candidate ran without
    them while the candidate could do all three. An audit hook closes that for pure-Python
    candidates.

    It is deliberately **not** complete, and the result record says so through
    `audit_hook_covers_pure_python_only`. A C extension calls libc directly and never raises an
    audit event, so a candidate that ships one is outside this boundary. Anyone relying on the
    limit for a real claim has to read that field rather than the request.
    """
    blocked_writes = not isolation.filesystem_writes_permitted
    blocked_network = not isolation.network_permitted
    blocked_subprocesses = not isolation.subprocess_permitted
    if not (blocked_writes or blocked_network or blocked_subprocesses):
        return []

    if blocked_writes:
        # Importing a module for the first time would otherwise try to write a .pyc and be refused,
        # turning an ordinary import into what looks like a candidate fault. Exempting __pycache__
        # would be a hole any candidate could drive through by choosing that path, so the bytecode
        # writing is switched off instead.
        sys.dont_write_bytecode = True

    def _guard(event: str, arguments) -> None:
        if blocked_network and event in _NETWORK_EVENTS:
            raise PermissionError("this candidate may not reach the network")
        if blocked_subprocesses and event in ("subprocess.Popen", "os.exec", "os.posix_spawn"):
            raise PermissionError("this candidate may not start a subprocess")
        if blocked_writes:
            if event in _MUTATING_FILESYSTEM_EVENTS:
                raise PermissionError("this candidate may not change the filesystem")
            if event == "open" and _opens_for_writing(arguments):
                raise PermissionError("this candidate may not write to the filesystem")

    sys.addaudithook(_guard)
    applied = []
    if blocked_writes:
        applied.append("filesystem_writes_permitted")
    if blocked_network:
        applied.append("network_permitted")
    if blocked_subprocesses:
        applied.append("subprocess_permitted")
    return applied


def _child(connection, body_factory, tasks, isolation):  # pragma: no cover - runs in a child
    enforced, unenforced = _apply_limits(isolation)
    try:
        body = body_factory()
        rows = []
        for task in tasks:
            task_id = str(task["task_id"])
            try:
                outcome = body.attempt(task)
            except Exception:
                rows.append({"task_id": task_id, "outcome": "error"})
                continue
            if outcome not in ("solved", "unsolved", "refused", "error"):
                rows.append({"task_id": task_id, "outcome": "error"})
            else:
                rows.append({"task_id": task_id, "outcome": outcome})
        connection.send(
            {"ok": True, "outcomes": rows, "enforced": enforced, "unenforced": unenforced}
        )
    except BaseException:
        connection.send(
            {
                "ok": False,
                "traceback": traceback.format_exc(limit=8),
                "enforced": enforced,
                "unenforced": unenforced,
            }
        )
    finally:
        connection.close()


def run_candidate(
    body_factory: Callable[[], Any],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
    *,
    admitted_isolation: Isolation | None = None,
) -> dict[str, Any]:
    """Run a body over the tasks in a separate process and return raw per-task outcomes.

    The result carries only outcomes, never a score: scoring belongs to the trust root, which
    recomputes it. A candidate that crashes yields `error` rows rather than an exception, because
    a body that breaks is an observation the lineage keeps.
    """
    if admitted_isolation is not None:
        isolation.assert_no_wider_than(admitted_isolation)
    if isolation.network_permitted:
        raise TrustRootError("candidate execution may not be granted network access")

    identifiers = [str(task["task_id"]) for task in tasks]
    if len(set(identifiers)) != len(identifiers):
        raise SandboxError("the task set repeats a task id")

    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_child, args=(child_connection, body_factory, list(tasks), isolation)
    )
    process.start()
    child_connection.close()

    timeout = max(1.0, float(isolation.wall_clock_seconds))
    payload: dict[str, Any] | None = None
    if parent_connection.poll(timeout):
        try:
            payload = parent_connection.recv()
        except EOFError:
            payload = None
    process.join(timeout=1.0)
    timed_out = payload is None
    if process.is_alive():  # pragma: no cover - only on a genuine overrun
        process.terminate()
        process.join(timeout=5.0)
    parent_connection.close()

    # An infrastructure failure must never look like a candidate failure. If the child never ran,
    # its rows are not evidence about the body and the caller must abort the comparison rather than
    # score a candidate on outcomes the sandbox invented for it. This is the same distinction M124
    # had to learn between a delivery outcome and a scientific one.
    if timed_out:
        result = {
            "completed": False,
            "instrument_failure": True,
            "reason": "wall clock exceeded, or the child process never reported",
            "outcomes": [],
            "enforced": [],
            "unenforced": ["cpu_seconds", "memory_bytes", "subprocess_permitted"],
        }
    elif not payload.get("ok"):
        result = {
            "completed": False,
            "instrument_failure": True,
            "reason": "the candidate body could not be constructed in the child process",
            "traceback": payload.get("traceback", ""),
            "outcomes": [],
            "enforced": list(payload.get("enforced") or []),
            "unenforced": list(payload.get("unenforced") or []),
        }
    else:
        result = {
            "completed": True,
            "instrument_failure": False,
            "reason": "",
            "outcomes": list(payload["outcomes"]),
            "enforced": list(payload.get("enforced") or []),
            "unenforced": list(payload.get("unenforced") or []),
        }

    result.update(
        {
            "schema": SANDBOX_SCHEMA,
            "isolation_requested": isolation.record(),
            "separate_process": True,
            "network_permitted": False,
            "audit_hook_covers_pure_python_only": True,
            "platform": sys.platform,
            "carries_a_score": False,
        }
    )
    if result["completed"] and set(row["task_id"] for row in result["outcomes"]) != set(identifiers):
        raise SandboxError("the candidate did not report the task set it was given")
    result["result_digest"] = digest_of({k: v for k, v in result.items()})
    return result


def isolation_is_complete(result: Mapping[str, Any]) -> bool:
    """True only when every requested limit was actually applied on this platform."""
    return bool(result.get("separate_process")) and not list(result.get("unenforced") or [])
