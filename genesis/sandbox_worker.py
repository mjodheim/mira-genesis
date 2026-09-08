"""Trusted bootstrap for Genesis candidate execution.

The parent launches this module by a fixed import path. No candidate-controlled Python object is a
process argument and no candidate-controlled object is ever deserialised in the evaluator. The only
wire format is JSON. Resource/audit limits are installed before the candidate artifact is imported
or constructed.

This is still a pure-Python DEVELOPMENT boundary: the audit hook cannot constrain a hostile native
extension. The parent records that limitation explicitly. What this worker closes is the more basic
pickle hole where Python code could execute before the boundary existed or while the evaluator was
decoding a result.
"""
from __future__ import annotations

import functools
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping

from genesis.sandbox import _apply_limits
from genesis.trust_root import Isolation


def _send(value: Mapping[str, Any]) -> None:
    sys.__stdout__.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.__stdout__.flush()


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
    if not isinstance(qualname, str) or not qualname or "<locals>" in qualname or "<lambda>" in qualname:
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


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        isolation_record = dict(request.get("isolation") or {})
        isolation_record.pop("schema", None)
        isolation = Isolation(**isolation_record)
    except Exception:
        _send({"kind": "bootstrap_failure", "traceback": traceback.format_exc(limit=8)})
        return 2

    enforced, unenforced = _apply_limits(isolation)
    _send({"kind": "isolation", "enforced": enforced, "unenforced": unenforced})

    try:
        factory = _resolve_artifact(request.get("artifact") or {})
        body = factory()
    except BaseException:
        _send(
            {
                "kind": "result",
                "ok": False,
                "traceback": traceback.format_exc(limit=8),
            }
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
        _send({"kind": "result", "ok": True, "rows": rows})
    except BaseException:
        _send(
            {
                "kind": "result",
                "ok": False,
                "traceback": traceback.format_exc(limit=8),
            }
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - executed as a child interpreter
    raise SystemExit(main())
