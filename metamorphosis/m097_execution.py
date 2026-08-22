"""Fresh-subprocess behavioural confirmation for M097-generated real Python methods."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m097_language import DerivedRequirement

EXECUTION_SCHEMA = "m097-execution-v1"

_PROBE = r'''
import importlib, json, sys

payload = json.loads(sys.stdin.read())
sys.path.insert(0, ".")
module = importlib.import_module(payload["module"])
cls = getattr(module, payload["class"])
requirement = payload["requirement"]
methods = sorted(
    name for name in dir(cls)
    if not name.startswith("_") and callable(getattr(cls, name, None))
)
agreeing = []
for method in methods:
    passed = 0
    for case in payload["cases"]:
        try:
            instance = cls(**case["arguments"])
            produced = getattr(instance, method)()
            left = case["arguments"][requirement["left_field"]]
            right = case["arguments"][requirement["right_field"]]
            if requirement["operator"] == "sub":
                expected = left - right
            elif requirement["operator"] == "add":
                expected = left + right
            elif requirement["operator"] == "mul":
                expected = left * right
            else:
                break
            if produced != {requirement["key"]: expected}:
                break
            passed += 1
        except Exception:
            break
    if passed == len(payload["cases"]):
        agreeing.append(method)
print(json.dumps({
    "schema": "m097-execution-probe-v1",
    "cases": len(payload["cases"]),
    "methods_examined": len(methods),
    "agreeing_methods": agreeing,
    "confirmed": bool(agreeing) and bool(payload["cases"]),
}, sort_keys=True))
'''


def probe_source(
    root: Path,
    component: str,
    source: str,
    requirement: DerivedRequirement,
    cases: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    path = root / component
    original = path.read_bytes()
    path.write_text(source, encoding="utf-8", newline="\n")
    payload = {
        "module": component.replace("/", ".").removesuffix(".py"),
        "class": requirement.class_name,
        "requirement": requirement.to_dict(),
        "cases": list(cases),
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", _PROBE],
            cwd=root,
            input=json.dumps(payload, sort_keys=True),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    finally:
        path.write_bytes(original)
    if completed.returncode != 0:
        return {
            "schema": EXECUTION_SCHEMA,
            "confirmed": False,
            "returncode": completed.returncode,
            "error": completed.stderr[-1000:],
        }
    result = json.loads(completed.stdout)
    result["schema"] = EXECUTION_SCHEMA
    result["returncode"] = completed.returncode
    return result


def confirm_search(
    root: Path,
    component: str,
    sources: Sequence[str],
    requirement: DerivedRequirement,
    cases: Sequence[Mapping[str, object]],
) -> tuple[int, str | None, dict[str, object] | None]:
    executed = 0
    for source in sources:
        executed += 1
        record = probe_source(root, component, source, requirement, cases)
        if record.get("confirmed") is True:
            return executed, source, record
    return executed, None, None


__all__ = ["EXECUTION_SCHEMA", "confirm_search", "probe_source"]
