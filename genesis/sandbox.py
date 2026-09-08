"""Isolated candidate execution, and an honest record of what isolation was actually obtained.

A candidate body is untrusted: it is a transformation the lineage produced, and the whole point of
running it is that nobody yet knows whether it is any good. It must not be able to reach the parent,
the evaluator, the journal or the task oracle.

Candidates are launched through this module's fixed bootstrap entry point. The candidate artifact
and task values cross the boundary only as JSON data; Python pickle is never used at either edge.
This closes two authority inversions in the former multiprocessing path: process arguments were
unpickled before child limits existed, and candidate answers were unpickled in the evaluator.

The boundary remains explicitly DEVELOPMENT-grade for arbitrary hostile native extensions: Python
audit hooks cover Python-visible operations, not direct libc/syscall activity from native code. The
result records that limitation rather than silently promoting the apparatus into a stronger sandbox.
"""
from __future__ import annotations

import functools
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

from genesis.trust_root import (
    TASK_OUTCOMES,
    Isolation,
    TrustRootError,
    artifact_digest_of,
    digest_of,
)

SANDBOX_SCHEMA = "genesis-sandbox-result-v1"
WORKER_REQUEST_SCHEMA = "genesis-sandbox-worker-request-v1"


class SandboxError(RuntimeError):
    """Raised when a candidate could not be run under the limits it was supposed to run under."""


def _apply_limits(isolation: Isolation) -> tuple[list[str], list[str]]:
    """Apply what this platform can enforce; report honestly on the rest."""
    enforced: list[str] = []
    unenforced: list[str] = []
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        resource = None
        unenforced.extend(["cpu_seconds", "memory_bytes"])

    if resource is not None:
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
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
            except (ValueError, OSError):
                unenforced.append("subprocess_permitted")

    # Audit enforcement is still useful where POSIX resource limits do not exist. The earlier
    # implementation returned on ImportError and accidentally turned all these limits into labels.
    for limit in _install_audit_guard(isolation):
        if limit in unenforced:
            unenforced.remove(limit)
        if limit not in enforced:
            enforced.append(limit)
    return enforced, unenforced


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
    mode = arguments[1] if len(arguments) > 1 else None
    if isinstance(mode, str):
        return any(flag in mode for flag in "wxa+")
    flags = arguments[2] if len(arguments) > 2 else 0
    if not isinstance(flags, int) or flags < 0:
        return True
    writing = 0
    for name in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_APPEND", "O_TRUNC"):
        writing |= getattr(os, name, 0)
    return bool(flags & writing)


def _install_audit_guard(isolation: Isolation) -> list[str]:
    """Apply the limits Python's audit mechanism can express.

    This is intentionally not claimed as a native-code sandbox. A real self-generated mechanism
    must either be restricted to the admitted Python subset or execute inside an OS/container
    boundary whose kernel policy, filesystem and network namespace are outside candidate authority.
    """
    blocked_writes = not isolation.filesystem_writes_permitted
    blocked_network = not isolation.network_permitted
    blocked_subprocesses = not isolation.subprocess_permitted
    if not (blocked_writes or blocked_network or blocked_subprocesses):
        return []

    if blocked_writes:
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


def _candidate_descriptor(factory: Any) -> dict[str, Any]:
    """Admit only descriptors the fixed bootstrap can reconstruct without pickle."""
    target = factory
    while isinstance(target, functools.partial):
        target = target.func
    if not (inspect.isfunction(target) or inspect.isclass(target) or inspect.isbuiltin(target)):
        raise SandboxError(
            "candidate factory is a live callable object rather than a reconstructible artifact; "
            "the sandbox will not pickle it across the process boundary"
        )
    descriptor = artifact_digest_of(factory)

    def check(record: Mapping[str, Any]) -> None:
        kind = record.get("kind")
        if kind == "partial":
            check(record.get("callable") or {})
            return
        if kind != "importable_symbol":
            raise SandboxError("candidate artifact kind %r is not supported" % kind)
        module = record.get("module")
        qualname = record.get("qualname")
        if not isinstance(module, str) or not module:
            raise SandboxError("candidate artifact names no importable module")
        if (
            not isinstance(qualname, str)
            or not qualname
            or "<locals>" in qualname
            or "<lambda>" in qualname
        ):
            raise SandboxError("candidate artifact is not a reconstructible importable symbol")

    check(descriptor)
    return descriptor


def _decode_bound(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if not isinstance(value, dict):
        raise ValueError("bound artifact configuration is not canonical data")
    kind = value.get("type")
    if kind == "bytes":
        return bytes.fromhex(str(value.get("hex", "")))
    if kind in ("list", "tuple", "set", "frozenset"):
        items = [_decode_bound(item) for item in value.get("items") or []]
        if kind == "list":
            return items
        if kind == "tuple":
            return tuple(items)
        if kind == "set":
            return set(items)
        return frozenset(items)
    if kind == "mapping":
        return {
            _decode_bound(pair[0]): _decode_bound(pair[1])
            for pair in value.get("items") or []
        }
    if kind == "path":
        return Path(str(value.get("value", "")))
    raise ValueError("unrecognised bound artifact value %r" % kind)


def _resolve_artifact(descriptor: Mapping[str, Any]):
    """Resolve one admitted descriptor only after the worker installed its limits."""
    kind = descriptor.get("kind")
    if kind == "partial":
        target = _resolve_artifact(descriptor.get("callable") or {})
        args = [_decode_bound(value) for value in descriptor.get("args") or []]
        keywords = {
            str(key): _decode_bound(value)
            for key, value in (descriptor.get("keywords") or {}).items()
        }
        return functools.partial(target, *args, **keywords)

    if kind != "importable_symbol":
        raise ValueError("candidate artifact kind %r is not executable by this bootstrap" % kind)
    module_name = descriptor.get("module")
    qualname = descriptor.get("qualname")
    if not isinstance(module_name, str) or not module_name:
        raise ValueError("candidate artifact names no importable module")
    if (
        not isinstance(qualname, str)
        or not qualname
        or "<locals>" in qualname
        or "<lambda>" in qualname
    ):
        raise ValueError("candidate artifact is not an importable qualified symbol")

    module = importlib.import_module(module_name)
    target: Any = module
    for part in qualname.split("."):
        target = getattr(target, part)

    expected_source = str(descriptor.get("module_source_sha256") or "")
    if expected_source:
        source_file = inspect.getsourcefile(target)
        if not source_file:
            raise ValueError("candidate artifact source cannot be verified")
        raw = Path(source_file).read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected_source:
            raise ValueError("candidate artifact module source does not match its admitted identity")
    return target


def _json_answer(value: Any) -> Any:
    """Require inert JSON data; never invoke pickle/reduce/custom reconstruction."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return json.loads(encoded)


def _worker_send(value: Mapping[str, Any]) -> None:
    sys.__stdout__.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.__stdout__.flush()


def _worker_main() -> int:  # pragma: no cover - executed in child interpreter
    """Fixed worker: parse inert request, install limits, then resolve candidate artifact."""
    try:
        request = json.loads(sys.stdin.read())
        if request.get("schema") != WORKER_REQUEST_SCHEMA:
            raise ValueError("unrecognised sandbox worker request")
        isolation_record = dict(request.get("isolation") or {})
        isolation_record.pop("schema", None)
        isolation = Isolation(**isolation_record)
    except Exception:
        _worker_send({"kind": "bootstrap_failure", "traceback": traceback.format_exc(limit=8)})
        return 2

    enforced, unenforced = _apply_limits(isolation)
    # This line is emitted before any candidate-controlled module is imported.
    _worker_send({"kind": "isolation", "enforced": enforced, "unenforced": unenforced})

    try:
        factory = _resolve_artifact(request.get("artifact") or {})
        body = factory()
    except BaseException:
        _worker_send(
            {"kind": "result", "ok": False, "traceback": traceback.format_exc(limit=8)}
        )
        return 0

    rows = []
    graded = bool(request.get("graded"))
    try:
        for task in request.get("tasks") or []:
            task_id = str(task["task_id"])
            try:
                returned = body.attempt(task)
                if graded:
                    returned = _json_answer(returned)
            except Exception:
                rows.append({"task_id": task_id, "failed": True})
                continue
            if graded:
                rows.append({"task_id": task_id, "answer": returned})
            elif returned not in ("solved", "unsolved", "refused", "error"):
                rows.append({"task_id": task_id, "failed": True})
            else:
                rows.append({"task_id": task_id, "outcome": returned})
        _worker_send({"kind": "result", "ok": True, "rows": rows})
    except BaseException:
        _worker_send(
            {"kind": "result", "ok": False, "traceback": traceback.format_exc(limit=8)}
        )
    return 0


def _outcomes_from(rows, by_identifier, grade) -> list[dict[str, Any]]:
    """Turn inert JSON rows into outcomes, grading only in the evaluator process."""
    outcomes = []
    for row in rows:
        if not isinstance(row, Mapping):
            outcomes.append({"task_id": "", "outcome": "error"})
            continue
        task_id = str(row.get("task_id"))
        if row.get("failed"):
            outcomes.append({"task_id": task_id, "outcome": "error"})
            continue
        if grade is None:
            outcomes.append({"task_id": task_id, "outcome": row.get("outcome", "error")})
            continue
        task = by_identifier.get(task_id)
        try:
            verdict = grade(task, row.get("answer"))
        except Exception:
            verdict = "error"
        if verdict not in TASK_OUTCOMES:
            verdict = "error"
        outcomes.append({"task_id": task_id, "outcome": verdict})
    return outcomes


def _parse_worker_output(stdout: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    isolation_report: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except Exception:
            continue
        if not isinstance(value, dict):
            continue
        if not isolation_report and value.get("kind") == "isolation":
            isolation_report = value
        elif value.get("kind") == "result":
            result = value
        elif not isolation_report and value.get("kind") == "bootstrap_failure":
            result = value
    return isolation_report, result


def run_candidate(
    body_factory: Callable[[], Any],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
    *,
    admitted_isolation: Isolation | None = None,
    grade: Callable[[Mapping[str, Any], Any], str] | None = None,
    withhold: Sequence[str] = ("expected",),
) -> dict[str, Any]:
    """Run one reconstructible candidate artifact through the fixed JSON bootstrap."""
    if admitted_isolation is not None:
        isolation.assert_no_wider_than(admitted_isolation)
    if isolation.network_permitted:
        raise TrustRootError("candidate execution may not be granted network access")

    identifiers = [str(task["task_id"]) for task in tasks]
    if len(set(identifiers)) != len(identifiers):
        raise SandboxError("the task set repeats a task id")
    by_identifier = {str(task["task_id"]): task for task in tasks}

    withheld = tuple(str(key) for key in withhold)
    asked = [
        {key: value for key, value in task.items() if key not in withheld} for task in tasks
    ]
    descriptor = _candidate_descriptor(body_factory)
    request = {
        "schema": WORKER_REQUEST_SCHEMA,
        "isolation": isolation.record(),
        "artifact": descriptor,
        "tasks": asked,
        "graded": grade is not None,
    }
    try:
        request_text = json.dumps(
            request, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as problem:
        raise SandboxError(
            "candidate task/configuration payload is not inert JSON data: %s" % problem
        ) from problem

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    python_path = [entry for entry in sys.path if isinstance(entry, str) and entry]
    if python_path:
        environment["PYTHONPATH"] = os.pathsep.join(python_path)

    process = subprocess.Popen(
        [sys.executable, "-m", "genesis.sandbox"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    timeout = max(1.0, float(isolation.wall_clock_seconds))
    timed_out = False
    try:
        stdout, stderr = process.communicate(request_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate(timeout=5.0)

    isolation_report, payload = _parse_worker_output(stdout)
    enforced = list(isolation_report.get("enforced") or [])
    unenforced = list(isolation_report.get("unenforced") or [])
    if "wall_clock_seconds" not in enforced:
        enforced.append("wall_clock_seconds")
    if "wall_clock_seconds" in unenforced:
        unenforced.remove("wall_clock_seconds")

    if timed_out or payload is None:
        result = {
            "completed": False,
            "instrument_failure": True,
            "reason": "wall clock exceeded, or the fixed worker never reported",
            "outcomes": [],
            "enforced": enforced,
            "unenforced": unenforced,
        }
    elif payload.get("kind") == "bootstrap_failure" or not payload.get("ok"):
        result = {
            "completed": False,
            "instrument_failure": True,
            "reason": "the candidate artifact could not be resolved or constructed after isolation",
            "traceback": payload.get("traceback", "") or stderr[-4000:],
            "outcomes": [],
            "enforced": enforced,
            "unenforced": unenforced,
        }
    else:
        result = {
            "completed": True,
            "instrument_failure": False,
            "reason": "",
            "outcomes": _outcomes_from(payload.get("rows") or [], by_identifier, grade),
            "enforced": enforced,
            "unenforced": unenforced,
        }

    result.update(
        {
            "schema": SANDBOX_SCHEMA,
            "isolation_requested": isolation.record(),
            "separate_process": True,
            "network_permitted": False,
            "audit_hook_covers_pure_python_only": True,
            "outcomes_are_self_reported": grade is None,
            "withheld_from_the_candidate": list(withheld),
            "platform": sys.platform,
            "carries_a_score": False,
            "transport_format": "canonical-json",
            "uses_executable_deserialization": False,
            "candidate_artifact_digest": descriptor["artifact_digest"],
            "candidate_loaded_after_limits": bool(isolation_report),
        }
    )
    if result["completed"] and set(row["task_id"] for row in result["outcomes"]) != set(identifiers):
        raise SandboxError("the candidate did not report the task set it was given")
    result["result_digest"] = digest_of({k: v for k, v in result.items()})
    return result


def isolation_is_complete(result: Mapping[str, Any]) -> bool:
    """True only when every requested limit was actually applied on this platform."""
    return bool(result.get("separate_process")) and not list(result.get("unenforced") or [])


if __name__ == "__main__":  # pragma: no cover - fixed child bootstrap
    raise SystemExit(_worker_main())
