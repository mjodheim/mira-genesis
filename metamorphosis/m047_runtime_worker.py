"""Disposable batch execution worker for M047 modular software bodies."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import os
import sys
import tempfile
from types import ModuleType
from typing import Mapping, Sequence

from metamorphosis.m047_software_body import (
    SoftwareBody,
    SoftwareBodyError,
    SoftwareCase,
    render_generated_tests,
)


REQUEST_SCHEMA = "m047-runtime-batch-request-v1"
RESULT_SCHEMA = "m047-runtime-batch-result-v1"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"m047_runtime_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated module {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_cases(raw: object) -> tuple[SoftwareCase, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise SoftwareBodyError("runtime cases must be a sequence")
    cases: list[SoftwareCase] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise SoftwareBodyError("runtime case must be an object")
        cases.append(SoftwareCase.from_dict(item))
    return tuple(cases)


def _execute(body: SoftwareBody, cases: tuple[SoftwareCase, ...]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="m047-software-body-") as directory:
        root = Path(directory)
        for source_module in body.modules:
            (root / f"{source_module.name}.py").write_text(
                source_module.source, encoding="utf-8"
            )
        generated_path = root / "generated_tests.py"
        generated_path.write_text(
            render_generated_tests(body.regression_cases), encoding="utf-8"
        )

        modules: dict[str, ModuleType] = {}
        for source_module in body.modules:
            modules[source_module.name] = _load_module(
                source_module.name, root / f"{source_module.name}.py"
            )
        generated_tests = _load_module("generated_tests", generated_path)

        tools: dict[str, object] = {}
        for name, module in modules.items():
            if name == "tool_core" or name.startswith("tool_"):
                registry = getattr(module, "TOOLS", None)
                if not isinstance(registry, dict):
                    raise RuntimeError(f"tool module {name} lacks a TOOLS dictionary")
                for tool_name, tool in registry.items():
                    if tool_name in tools:
                        raise RuntimeError(f"duplicate tool registration: {tool_name}")
                    if not callable(tool):
                        raise RuntimeError(f"registered tool {tool_name} is not callable")
                    tools[str(tool_name)] = tool

        orchestrator = modules["orchestration"]

        def direct_run(request: str) -> object:
            result = orchestrator.run(request, modules, tools)
            if not result["ok"]:
                raise RuntimeError(
                    f"{result['error_stage']}:{result['error_type']}:"
                    f"{result['error_message']}"
                )
            return result["output"]

        generated_tests_passed = False
        generated_tests_count = 0
        generated_tests_error: str | None = None
        try:
            generated_tests_count = int(generated_tests.run_tests(direct_run))
            generated_tests_passed = True
        except Exception as exc:
            generated_tests_error = f"{type(exc).__name__}:{exc}"

        case_results: list[dict[str, object]] = []
        for case in cases:
            result = orchestrator.run(case.request, modules, tools)
            passed = bool(result["ok"] and result["output"] == case.expected)
            case_results.append(
                {
                    "case_id": case.case_id,
                    "request": case.request,
                    "expected": case.expected,
                    "passed": passed,
                    "result": result,
                }
            )

        return {
            "body_digest": body.digest(),
            "module_count": len(body.modules),
            "regression_case_count": len(body.regression_cases),
            "generated_tests_passed": generated_tests_passed,
            "generated_tests_count": generated_tests_count,
            "generated_tests_error": generated_tests_error,
            "case_results": case_results,
        }


def _execute_job(raw: Mapping[str, object]) -> dict[str, object]:
    if set(raw) != {"job_id", "body", "cases"}:
        raise SoftwareBodyError("invalid runtime job fields")
    job_id = str(raw["job_id"])
    raw_body = raw["body"]
    if not isinstance(raw_body, Mapping):
        raise SoftwareBodyError("runtime body must be an object")
    body = SoftwareBody.from_dict(raw_body)
    cases = _parse_cases(raw["cases"])
    return {"job_id": job_id, "result": _execute(body, cases)}


def main() -> None:
    try:
        raw = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(raw, Mapping) or set(raw) != {"schema", "jobs"}:
            raise SoftwareBodyError("invalid runtime batch request fields")
        if raw["schema"] != REQUEST_SCHEMA:
            raise SoftwareBodyError("unsupported runtime request schema")
        raw_jobs = raw["jobs"]
        if not isinstance(raw_jobs, Sequence) or isinstance(raw_jobs, (str, bytes)):
            raise SoftwareBodyError("runtime jobs must be a sequence")
        jobs = []
        for raw_job in raw_jobs:
            if not isinstance(raw_job, Mapping):
                raise SoftwareBodyError("runtime job must be an object")
            jobs.append(_execute_job(raw_job))
        result = {
            "schema": RESULT_SCHEMA,
            "worker_pid": os.getpid(),
            "jobs": jobs,
        }
    except Exception as exc:
        result = {
            "schema": RESULT_SCHEMA,
            "worker_pid": os.getpid(),
            "fatal_error": f"{type(exc).__name__}:{exc}",
        }
    sys.stdout.write(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
