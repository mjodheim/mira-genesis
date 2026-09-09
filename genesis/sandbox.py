"""Isolated execution with inert JSON transport.

Candidate-controlled Python objects never cross the evaluator boundary. The parent launches a fixed
``python -m genesis.sandbox --worker`` process, sends JSON, and receives JSON. The worker installs
resource/audit limits before resolving the candidate artifact. This closes the executable pickle
boundary of the former ``multiprocessing`` implementation.

The boundary remains DEVELOPMENT-grade for arbitrary native extensions: Python audit hooks do not
interpose on direct libc calls from C code, and every result records that limitation.
"""
from __future__ import annotations

import functools
import hashlib
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

from genesis.trust_root import TASK_OUTCOMES, Isolation, TrustRootError, digest_of

SANDBOX_SCHEMA = "genesis-sandbox-result-v1"
ISOLATED_CALL_SCHEMA = "genesis-isolated-call-result-v1"
WORKER_REQUEST_SCHEMA = "genesis-sandbox-worker-request-v2"
WIRE_ARTIFACT_SCHEMA = "genesis-sandbox-wire-artifact-v1"


class SandboxError(RuntimeError):
    """Raised when an executable cannot cross or run under the admitted boundary."""


_MUTATING_FILESYSTEM_EVENTS = frozenset({
    "os.remove", "os.rename", "os.mkdir", "os.rmdir", "os.truncate", "os.chmod",
    "os.chown", "os.link", "os.symlink", "shutil.copyfile", "shutil.copymode",
    "shutil.copystat", "shutil.move", "shutil.rmtree",
})
_NETWORK_EVENTS = frozenset({
    "socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname", "socket.sendto",
})


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
    blocked_writes = not isolation.filesystem_writes_permitted
    blocked_network = not isolation.network_permitted
    blocked_subprocesses = not isolation.subprocess_permitted
    if not (blocked_writes or blocked_network or blocked_subprocesses):
        return []
    if blocked_writes:
        sys.dont_write_bytecode = True

    def guard(event: str, arguments) -> None:
        if blocked_network and event in _NETWORK_EVENTS:
            raise PermissionError("this candidate may not reach the network")
        if blocked_subprocesses and event in ("subprocess.Popen", "os.exec", "os.posix_spawn"):
            raise PermissionError("this candidate may not start a subprocess")
        if blocked_writes and (
            event in _MUTATING_FILESYSTEM_EVENTS
            or (event == "open" and _opens_for_writing(arguments))
        ):
            raise PermissionError("this candidate may not change the filesystem")

    sys.addaudithook(guard)
    applied = []
    if blocked_writes:
        applied.append("filesystem_writes_permitted")
    if blocked_network:
        applied.append("network_permitted")
    if blocked_subprocesses:
        applied.append("subprocess_permitted")
    return applied


def _apply_limits(isolation: Isolation) -> tuple[list[str], list[str]]:
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
    for name in _install_audit_guard(isolation):
        if name in unenforced:
            unenforced.remove(name)
        if name not in enforced:
            enforced.append(name)
    return enforced, unenforced


def _module_source_sha256(target: Any) -> str:
    try:
        path = inspect.getsourcefile(target)
        if not path:
            return ""
        raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    except (OSError, TypeError):
        return ""
    return hashlib.sha256(raw).hexdigest()


def _symbol_descriptor(target: Any) -> dict[str, Any]:
    module = str(getattr(target, "__module__", ""))
    qualname = str(getattr(target, "__qualname__", getattr(target, "__name__", "")))
    if not module or not qualname or "<locals>" in qualname or "<lambda>" in qualname:
        raise SandboxError("candidate artifact is not an importable module-level symbol")
    if getattr(target, "__closure__", None):
        raise SandboxError("candidate artifact closes over live values and is not reconstructible")
    return {
        "schema": WIRE_ARTIFACT_SCHEMA,
        "kind": "symbol",
        "module": module,
        "qualname": qualname,
        "module_source_sha256": _module_source_sha256(target),
    }


def _wire_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SandboxError("non-finite floats cannot cross the inert JSON boundary")
        return value
    if isinstance(value, bytes):
        return {"__bytes__": value.hex()}
    if isinstance(value, Path):
        return {"__path__": str(value)}
    if isinstance(value, (list, tuple)):
        return {"__sequence__": [_wire_value(v) for v in value], "tuple": isinstance(value, tuple)}
    if isinstance(value, (set, frozenset)):
        items = [_wire_value(v) for v in value]
        items.sort(key=lambda v: json.dumps(v, sort_keys=True, separators=(",", ":")))
        return {"__set__": items, "frozen": isinstance(value, frozenset)}
    if isinstance(value, Mapping):
        pairs = [[_wire_value(k), _wire_value(v)] for k, v in value.items()]
        pairs.sort(key=lambda p: json.dumps(p[0], sort_keys=True, separators=(",", ":")))
        return {"__mapping__": pairs}
    if inspect.isfunction(value) or inspect.isclass(value) or inspect.isbuiltin(value):
        return {"__artifact__": _wire_descriptor(value)}
    raise SandboxError(
        "candidate configuration contains %s, which cannot cross the inert JSON boundary"
        % type(value).__name__
    )


def _decode_wire_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if not isinstance(value, dict):
        raise ValueError("wire value is not inert data")
    if "__bytes__" in value:
        return bytes.fromhex(str(value["__bytes__"]))
    if "__path__" in value:
        return Path(str(value["__path__"]))
    if "__sequence__" in value:
        items = [_decode_wire_value(v) for v in value["__sequence__"]]
        return tuple(items) if value.get("tuple") else items
    if "__set__" in value:
        items = [_decode_wire_value(v) for v in value["__set__"]]
        return frozenset(items) if value.get("frozen") else set(items)
    if "__mapping__" in value:
        return {_decode_wire_value(k): _decode_wire_value(v) for k, v in value["__mapping__"]}
    if "__artifact__" in value:
        return _resolve_descriptor(value["__artifact__"])
    raise ValueError("unrecognised inert wire value")


def _wire_descriptor(factory: Any) -> dict[str, Any]:
    from genesis.artifacts import ConfiguredBody

    if isinstance(factory, ConfiguredBody):
        target = factory.artifact_configuration().get("target_artifact") or {}
        return {
            "schema": WIRE_ARTIFACT_SCHEMA,
            "kind": "configured_body",
            "target": str(factory.target),
            "target_artifact_digest": str(target.get("artifact_digest", "")),
            "target_module_source_sha256": str(target.get("module_source_sha256", "")),
            "configuration": _wire_value(dict(factory.configuration)),
            "dependencies": sorted(factory.dependencies),
            "dependency_keyword": str(factory.dependency_keyword),
        }
    if isinstance(factory, functools.partial):
        return {
            "schema": WIRE_ARTIFACT_SCHEMA,
            "kind": "partial",
            "callable": _wire_descriptor(factory.func),
            "args": [_wire_value(v) for v in factory.args],
            "keywords": {str(k): _wire_value(v) for k, v in sorted((factory.keywords or {}).items())},
        }
    if inspect.isfunction(factory) or inspect.isclass(factory) or inspect.isbuiltin(factory):
        return _symbol_descriptor(factory)
    raise SandboxError(
        "candidate factory is a live callable object; this sandbox refuses to pickle executable state"
    )


def _resolve_symbol(descriptor: Mapping[str, Any]) -> Any:
    module_name = descriptor.get("module")
    qualname = descriptor.get("qualname")
    if not isinstance(module_name, str) or not module_name:
        raise ValueError("artifact names no module")
    if not isinstance(qualname, str) or not qualname or "<locals>" in qualname or "<lambda>" in qualname:
        raise ValueError("artifact names no importable symbol")
    target: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        target = getattr(target, part)
    expected = str(descriptor.get("module_source_sha256") or "")
    if expected and _module_source_sha256(target) != expected:
        raise ValueError("artifact module source changed after admission")
    return target


def _resolve_descriptor(descriptor: Mapping[str, Any]) -> Any:
    if descriptor.get("schema") != WIRE_ARTIFACT_SCHEMA:
        raise ValueError("unrecognised wire artifact schema")
    kind = descriptor.get("kind")
    if kind == "symbol":
        return _resolve_symbol(descriptor)
    if kind == "partial":
        target = _resolve_descriptor(descriptor.get("callable") or {})
        args = [_decode_wire_value(v) for v in descriptor.get("args") or []]
        keywords = {str(k): _decode_wire_value(v) for k, v in (descriptor.get("keywords") or {}).items()}
        return functools.partial(target, *args, **keywords)
    if kind == "configured_body":
        from genesis.artifacts import ConfiguredBody
        from genesis.trust_root import artifact_digest_of

        configured = ConfiguredBody(
            target=str(descriptor.get("target", "")),
            configuration=_decode_wire_value(descriptor.get("configuration") or {"__mapping__": []}),
            dependencies=frozenset(str(v) for v in descriptor.get("dependencies") or []),
            dependency_keyword=str(descriptor.get("dependency_keyword", "capabilities")),
        )
        actual = artifact_digest_of(configured.resolve())
        expected_digest = str(descriptor.get("target_artifact_digest") or "")
        expected_source = str(descriptor.get("target_module_source_sha256") or "")
        if expected_digest and actual["artifact_digest"] != expected_digest:
            raise ValueError("configured body target changed after admission")
        if expected_source and actual.get("module_source_sha256") != expected_source:
            raise ValueError("configured body target module source changed after admission")
        return configured
    raise ValueError("unsupported wire artifact kind %r" % kind)


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _worker_send(value: Mapping[str, Any]) -> None:
    sys.__stdout__.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.__stdout__.flush()


def _worker_main() -> int:  # pragma: no cover - child interpreter
    try:
        request = json.loads(sys.stdin.read())
        if request.get("schema") != WORKER_REQUEST_SCHEMA:
            raise ValueError("unrecognised worker request")
        nonce = str(request.get("nonce") or "")
        if not nonce:
            raise ValueError("worker request carries no nonce")
        raw = dict(request.get("isolation") or {})
        raw.pop("schema", None)
        isolation = Isolation(**raw)
    except Exception:
        _worker_send({"kind": "bootstrap_failure", "nonce": "", "traceback": traceback.format_exc(limit=8)})
        return 2

    enforced, unenforced = _apply_limits(isolation)
    _worker_send({"kind": "isolation", "nonce": nonce, "enforced": enforced, "unenforced": unenforced})
    sys.stdout = sys.stderr

    try:
        executable = _resolve_descriptor(request.get("artifact") or {})
    except BaseException:
        _worker_send({"kind": "result", "nonce": nonce, "ok": False, "stage": "resolve", "traceback": traceback.format_exc(limit=8)})
        return 0

    if request.get("mode") == "callable":
        try:
            value = _json_value(executable(_decode_wire_value(request.get("argument"))))
        except BaseException:
            _worker_send({"kind": "value", "nonce": nonce, "ok": False, "traceback": traceback.format_exc(limit=8)})
            return 0
        _worker_send({"kind": "value", "nonce": nonce, "ok": True, "value": value})
        return 0

    try:
        body = executable()
        tasks = _decode_wire_value(request.get("tasks") or {"__sequence__": []})
        graded = bool(request.get("graded"))
        rows = []
        for task in tasks:
            task_id = str(task["task_id"])
            try:
                returned = body.attempt(task)
                if graded:
                    returned = _json_value(returned)
            except Exception:
                rows.append({"task_id": task_id, "failed": True})
                continue
            if graded:
                rows.append({"task_id": task_id, "answer": returned})
            elif returned in TASK_OUTCOMES:
                rows.append({"task_id": task_id, "outcome": returned})
            else:
                rows.append({"task_id": task_id, "failed": True})
        _worker_send({"kind": "result", "nonce": nonce, "ok": True, "rows": rows})
    except BaseException:
        _worker_send({"kind": "result", "nonce": nonce, "ok": False, "stage": "run", "traceback": traceback.format_exc(limit=8)})
    return 0


def _run_worker(request: Mapping[str, Any], isolation: Isolation) -> tuple[dict, dict | None, str]:
    process = subprocess.Popen(
        [sys.executable, "-m", "genesis.sandbox", "--worker"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )
    try:
        stdout, stderr = process.communicate(
            json.dumps(request, sort_keys=True, separators=(",", ":"), allow_nan=False),
            timeout=max(1.0, float(isolation.wall_clock_seconds)),
        )
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return {}, None, "wall clock exceeded"
    nonce = str(request.get("nonce") or "")
    messages = []
    for line in stdout.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(message, dict) and message.get("nonce") == nonce:
            messages.append(message)
    report = next((m for m in messages if m.get("kind") == "isolation"), {})
    final = next((m for m in reversed(messages) if m.get("kind") in ("result", "value")), None)
    reason = ""
    if final is None:
        reason = "child process never reported a final inert result"
        if stderr.strip():
            reason += ": " + stderr.strip().splitlines()[-1][:300]
    return report, final, reason


def _outcomes(rows, tasks_by_id, grade) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        task_id = str(row.get("task_id"))
        if row.get("failed"):
            outcome = "error"
        elif grade is None:
            outcome = row.get("outcome", "error")
        else:
            try:
                outcome = grade(tasks_by_id.get(task_id), row.get("answer"))
            except Exception:
                outcome = "error"
            if outcome not in TASK_OUTCOMES:
                outcome = "error"
        result.append({"task_id": task_id, "outcome": outcome})
    return result


def _boundary(isolation: Isolation, report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "isolation_requested": isolation.record(),
        "separate_process": True,
        "network_permitted": False,
        "audit_hook_covers_pure_python_only": True,
        "transport_format": "canonical-json",
        "uses_executable_deserialization": False,
        "candidate_loaded_after_limits": bool(report),
        "platform": sys.platform,
    }


def run_candidate(
    body_factory: Callable[[], Any],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
    *,
    admitted_isolation: Isolation | None = None,
    grade: Callable[[Mapping[str, Any], Any], str] | None = None,
    withhold: Sequence[str] = ("expected",),
    capture_answers: bool = False,
) -> dict[str, Any]:
    """Run a candidate through the inert boundary and return per-task outcomes."""
    if admitted_isolation is not None:
        isolation.assert_no_wider_than(admitted_isolation)
    if isolation.network_permitted:
        raise TrustRootError("candidate execution may not be granted network access")
    identifiers = [str(task["task_id"]) for task in tasks]
    if len(set(identifiers)) != len(identifiers):
        raise SandboxError("the task set repeats a task id")
    by_id = {str(task["task_id"]): task for task in tasks}
    withheld = tuple(str(v) for v in withhold)
    asked = [{k: v for k, v in task.items() if k not in withheld} for task in tasks]
    request = {
        "schema": WORKER_REQUEST_SCHEMA,
        "nonce": secrets.token_hex(16),
        "mode": "body",
        "artifact": _wire_descriptor(body_factory),
        "tasks": _wire_value(asked),
        "isolation": isolation.record(),
        "graded": grade is not None,
    }
    report, payload, reason = _run_worker(request, isolation)
    enforced = list(report.get("enforced") or [])
    unenforced = list(report.get("unenforced") or [])
    if payload is None:
        result = {"completed": False, "instrument_failure": True, "reason": reason, "outcomes": [], "enforced": enforced, "unenforced": unenforced or ["cpu_seconds", "memory_bytes", "subprocess_permitted"]}
    elif not payload.get("ok"):
        result = {"completed": False, "instrument_failure": True, "reason": "the candidate artifact could not be resolved or run in the child process", "traceback": payload.get("traceback", ""), "outcomes": [], "enforced": enforced, "unenforced": unenforced}
    else:
        rows = list(payload.get("rows") or [])
        result = {"completed": True, "instrument_failure": False, "reason": "", "outcomes": _outcomes(rows, by_id, grade), "enforced": enforced, "unenforced": unenforced}
        if capture_answers:
            result["answers"] = [{"task_id": str(row.get("task_id")), "answer": row.get("answer")} for row in rows if not row.get("failed") and "answer" in row]
    result.update({
        "schema": SANDBOX_SCHEMA,
        **_boundary(isolation, report),
        "outcomes_are_self_reported": grade is None,
        "withheld_from_the_candidate": list(withheld),
        "carries_a_score": False,
    })
    if result["completed"] and [row["task_id"] for row in result["outcomes"]] != identifiers:
        raise SandboxError("the candidate did not report the task set it was given")
    result["result_digest"] = digest_of({k: v for k, v in result.items() if k != "answers"})
    return result


def run_isolated_callable(
    function: Callable[[Any], Any],
    argument: Any,
    isolation: Isolation,
    *,
    admitted_isolation: Isolation | None = None,
) -> dict[str, Any]:
    """Run one importable callable under the same inert boundary and return one JSON value."""
    if admitted_isolation is not None:
        isolation.assert_no_wider_than(admitted_isolation)
    if isolation.network_permitted:
        raise TrustRootError("isolated execution may not be granted network access")
    request = {
        "schema": WORKER_REQUEST_SCHEMA,
        "nonce": secrets.token_hex(16),
        "mode": "callable",
        "artifact": _wire_descriptor(function),
        "argument": _wire_value(argument),
        "isolation": isolation.record(),
    }
    report, payload, reason = _run_worker(request, isolation)
    completed = bool(payload and payload.get("kind") == "value" and payload.get("ok"))
    result = {
        "schema": ISOLATED_CALL_SCHEMA,
        "completed": completed,
        "instrument_failure": not completed,
        "reason": "" if completed else reason or "isolated callable failed",
        "value": payload.get("value") if completed and payload else None,
        "traceback": "" if completed or not payload else payload.get("traceback", ""),
        "enforced": list(report.get("enforced") or []),
        "unenforced": list(report.get("unenforced") or []),
        **_boundary(isolation, report),
    }
    result["result_digest"] = digest_of(result)
    return result


def isolation_is_complete(result: Mapping[str, Any]) -> bool:
    return bool(result.get("separate_process")) and not list(result.get("unenforced") or [])


def _main(argv: Sequence[str] | None = None) -> int:
    if list(sys.argv[1:] if argv is None else argv) == ["--worker"]:
        return _worker_main()
    raise SystemExit("genesis.sandbox is an internal worker; use run_candidate()")


if __name__ == "__main__":  # pragma: no cover - worker entry point
    raise SystemExit(_main())
