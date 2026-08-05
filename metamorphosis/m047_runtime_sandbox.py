"""Client for disposable batch execution of M047 software bodies."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m047_software_body import SoftwareBody, SoftwareCase


class SoftwareSandboxError(RuntimeError):
    """Raised when the disposable M047 runtime cannot be trusted."""


REQUEST_SCHEMA = "m047-runtime-batch-request-v1"
RESULT_SCHEMA = "m047-runtime-batch-result-v1"
MAX_RUNTIME_REQUEST_BYTES = 1_048_576
DEFAULT_RUNTIME_TIMEOUT_SECONDS = 15.0


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


@dataclass(frozen=True)
class CaseExecution:
    case_id: str
    request: str
    expected: object
    passed: bool
    ok: bool
    output: object
    error_stage: str | None
    error_type: str | None
    error_message: str | None
    trace: tuple[Mapping[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "request": self.request,
            "expected": self.expected,
            "passed": self.passed,
            "ok": self.ok,
            "output": self.output,
            "error_stage": self.error_stage,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "trace": [dict(item) for item in self.trace],
        }

    @property
    def used_tools(self) -> tuple[str, ...]:
        for item in self.trace:
            if item.get("stage") == "execution":
                value = item.get("value")
                if isinstance(value, Mapping):
                    raw = value.get("used_tools")
                    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
                        return tuple(str(tool) for tool in raw)
        return ()


@dataclass(frozen=True)
class SoftwareSandboxResult:
    worker_pid: int
    body_digest: str
    module_count: int
    regression_case_count: int
    generated_tests_passed: bool
    generated_tests_count: int
    generated_tests_error: str | None
    cases: tuple[CaseExecution, ...]

    @property
    def disposable_process(self) -> bool:
        return self.worker_pid != os.getpid()

    @property
    def passed_cases(self) -> int:
        return sum(case.passed for case in self.cases)

    @property
    def all_cases_passed(self) -> bool:
        return all(case.passed for case in self.cases)

    def case(self, case_id: str) -> CaseExecution:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise SoftwareSandboxError(f"sandbox result lacks case {case_id}")


@dataclass(frozen=True)
class SoftwareSandboxJob:
    job_id: str
    body: SoftwareBody
    cases: tuple[SoftwareCase, ...]


def _request_bytes(jobs: Sequence[SoftwareSandboxJob]) -> bytes:
    request = {
        "schema": REQUEST_SCHEMA,
        "jobs": [
            {
                "job_id": job.job_id,
                "body": job.body.to_dict(),
                "cases": [case.to_dict() for case in job.cases],
            }
            for job in jobs
        ],
    }
    encoded = _canonical_json(request)
    if len(encoded) > MAX_RUNTIME_REQUEST_BYTES:
        raise SoftwareSandboxError("runtime batch request exceeds the fixed byte bound")
    return encoded


def _parse_result(
    worker_pid: int,
    body: SoftwareBody,
    raw: object,
) -> SoftwareSandboxResult:
    if not isinstance(raw, Mapping):
        raise SoftwareSandboxError("runtime job result must be an object")
    required = {
        "body_digest",
        "module_count",
        "regression_case_count",
        "generated_tests_passed",
        "generated_tests_count",
        "generated_tests_error",
        "case_results",
    }
    if set(raw) != required:
        raise SoftwareSandboxError("runtime job result fields are incomplete")
    if raw["body_digest"] != body.digest():
        raise SoftwareSandboxError("runtime result is bound to the wrong body")
    raw_cases = raw["case_results"]
    if not isinstance(raw_cases, Sequence) or isinstance(raw_cases, (str, bytes)):
        raise SoftwareSandboxError("runtime case results must be a sequence")
    parsed_cases: list[CaseExecution] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, Mapping):
            raise SoftwareSandboxError("runtime case result must be an object")
        result = raw_case.get("result")
        if not isinstance(result, Mapping):
            raise SoftwareSandboxError("runtime case lacks its pipeline result")
        trace = result.get("trace")
        if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
            raise SoftwareSandboxError("runtime trace must be a sequence")
        trace_items: list[Mapping[str, object]] = []
        for item in trace:
            if not isinstance(item, Mapping):
                raise SoftwareSandboxError("runtime trace entry must be an object")
            trace_items.append(dict(item))
        parsed_cases.append(
            CaseExecution(
                case_id=str(raw_case.get("case_id")),
                request=str(raw_case.get("request")),
                expected=raw_case.get("expected"),
                passed=bool(raw_case.get("passed")),
                ok=bool(result.get("ok")),
                output=result.get("output"),
                error_stage=(
                    None
                    if result.get("error_stage") is None
                    else str(result.get("error_stage"))
                ),
                error_type=(
                    None
                    if result.get("error_type") is None
                    else str(result.get("error_type"))
                ),
                error_message=(
                    None
                    if result.get("error_message") is None
                    else str(result.get("error_message"))
                ),
                trace=tuple(trace_items),
            )
        )
    return SoftwareSandboxResult(
        worker_pid=worker_pid,
        body_digest=str(raw["body_digest"]),
        module_count=int(raw["module_count"]),
        regression_case_count=int(raw["regression_case_count"]),
        generated_tests_passed=bool(raw["generated_tests_passed"]),
        generated_tests_count=int(raw["generated_tests_count"]),
        generated_tests_error=(
            None
            if raw["generated_tests_error"] is None
            else str(raw["generated_tests_error"])
        ),
        cases=tuple(parsed_cases),
    )


def run_bodies_in_sandbox(
    jobs: Sequence[SoftwareSandboxJob],
    *,
    timeout_seconds: float = DEFAULT_RUNTIME_TIMEOUT_SECONDS,
) -> dict[str, SoftwareSandboxResult]:
    if not jobs:
        raise SoftwareSandboxError("sandbox batch requires at least one job")
    if len({job.job_id for job in jobs}) != len(jobs):
        raise SoftwareSandboxError("sandbox job identities must be unique")
    if timeout_seconds <= 0:
        raise SoftwareSandboxError("sandbox timeout must be positive")
    request = _request_bytes(jobs)
    try:
        with tempfile.TemporaryDirectory(prefix="m047-runtime-client-") as directory:
            request_path = Path(directory) / "request.json"
            stdout_path = Path(directory) / "stdout.json"
            stderr_path = Path(directory) / "stderr.log"
            request_path.write_bytes(request)
            with (
                request_path.open("rb") as stdin_file,
                stdout_path.open("wb") as stdout_file,
                stderr_path.open("wb") as stderr_file,
            ):
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "-c",
                        (
                            "import sys;"
                            f"sys.path.insert(0,{str(Path(__file__).resolve().parents[1])!r});"
                            "from metamorphosis.m047_runtime_worker import main;main()"
                        ),
                    ],
                    stdin=stdin_file,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    cwd=directory,
                    start_new_session=True,
                )
                try:
                    returncode = process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired as exc:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        process.kill()
                    process.wait(timeout=5.0)
                    raise SoftwareSandboxError(
                        "disposable runtime exceeded its fixed timeout"
                    ) from exc
            completed = subprocess.CompletedProcess(
                process.args,
                returncode,
                stdout_path.read_bytes(),
                stderr_path.read_bytes(),
            )
    except OSError as exc:
        raise SoftwareSandboxError(
            f"disposable runtime failed: {type(exc).__name__}"
        ) from exc
    if completed.returncode != 0:
        raise SoftwareSandboxError("disposable runtime exited unsuccessfully")
    try:
        raw = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SoftwareSandboxError("disposable runtime returned malformed JSON") from exc
    if not isinstance(raw, Mapping) or raw.get("schema") != RESULT_SCHEMA:
        raise SoftwareSandboxError("disposable runtime returned an invalid result")
    if "fatal_error" in raw:
        raise SoftwareSandboxError(str(raw["fatal_error"]))
    if set(raw) != {"schema", "worker_pid", "jobs"}:
        raise SoftwareSandboxError("runtime batch result fields are incomplete")
    worker_pid = int(raw["worker_pid"])
    raw_jobs = raw["jobs"]
    if not isinstance(raw_jobs, Sequence) or isinstance(raw_jobs, (str, bytes)):
        raise SoftwareSandboxError("runtime batch jobs must be a sequence")
    by_id = {job.job_id: job for job in jobs}
    results: dict[str, SoftwareSandboxResult] = {}
    for raw_job in raw_jobs:
        if not isinstance(raw_job, Mapping) or set(raw_job) != {"job_id", "result"}:
            raise SoftwareSandboxError("invalid runtime batch job result")
        job_id = str(raw_job["job_id"])
        if job_id not in by_id or job_id in results:
            raise SoftwareSandboxError("runtime returned an unknown or duplicate job")
        results[job_id] = _parse_result(
            worker_pid,
            by_id[job_id].body,
            raw_job["result"],
        )
    if set(results) != set(by_id):
        raise SoftwareSandboxError("runtime omitted a requested job")
    return results


def run_body_in_sandbox(
    body: SoftwareBody,
    cases: Sequence[SoftwareCase],
    *,
    timeout_seconds: float = DEFAULT_RUNTIME_TIMEOUT_SECONDS,
) -> SoftwareSandboxResult:
    job = SoftwareSandboxJob("single", body, tuple(cases))
    return run_bodies_in_sandbox(
        (job,), timeout_seconds=timeout_seconds
    )["single"]


__all__ = [
    "CaseExecution",
    "DEFAULT_RUNTIME_TIMEOUT_SECONDS",
    "MAX_RUNTIME_REQUEST_BYTES",
    "SoftwareSandboxError",
    "SoftwareSandboxJob",
    "SoftwareSandboxResult",
    "run_bodies_in_sandbox",
    "run_body_in_sandbox",
]
