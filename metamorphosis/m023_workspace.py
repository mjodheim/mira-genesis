"""M023 — disposable multi-file evaluation for self-rewrite candidates.

M020 searches and validates bounded policy source in memory. M023 adds an independent
execution boundary before adoption: source, cases and a fixed evaluator are written to a
temporary workspace and executed by an isolated Python subprocess under explicit
resource limits.

This is not a complete operating-system sandbox. The candidate language still forbids
imports, calls, attributes and loops, so the subprocess boundary is defence in depth,
not permission to execute arbitrary Python. Network and syscall isolation require a
later container or micro-VM layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Sequence

from .m020_self_rewrite import (
    Case,
    RewriteResult,
    VersionedCodeBody,
    source_digest,
    validate_source,
)

try:  # `resource` is POSIX-only; CI and the intended evaluator run on Linux.
    import resource
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    resource = None  # type: ignore[assignment]


_RUNNER_SOURCE = r'''from __future__ import annotations
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parent
config = json.loads((root / "cases.json").read_text(encoding="utf-8"))
spec = importlib.util.spec_from_file_location("candidate", root / "candidate.py")
if spec is None or spec.loader is None:
    raise SystemExit("unable to load candidate")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
function = getattr(module, config["function_name"])
passed = 0
failures = []
for index, row in enumerate(config["cases"]):
    try:
        value = function(*row["arguments"])
    except BaseException as error:
        failures.append({"index": index, "kind": type(error).__name__})
        continue
    if type(value) is not int:
        failures.append({"index": index, "kind": "non_integer_result"})
        continue
    if value == row["expected"]:
        passed += 1
    else:
        failures.append({
            "index": index,
            "kind": "wrong_value",
            "expected": row["expected"],
            "actual": value,
        })
print(json.dumps({"passed": passed, "total": len(config["cases"]), "failures": failures}, sort_keys=True))
'''


@dataclass(frozen=True)
class SandboxLimits:
    cpu_seconds: int = 2
    memory_bytes: int = 128 * 1024 * 1024
    file_size_bytes: int = 1 * 1024 * 1024
    process_count: int = 1
    open_files: int = 32
    wall_seconds: int = 5
    output_bytes: int = 64 * 1024

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class WorkspaceEvaluation:
    status: str
    passed: int
    total: int
    failures: tuple[dict[str, object], ...]
    return_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    source_digest: str
    workspace_digest: str

    @property
    def perfect(self) -> bool:
        return self.status == "completed" and self.passed == self.total


@dataclass(frozen=True)
class AdoptionDecision:
    adopted: bool
    reason: str
    baseline_development: WorkspaceEvaluation
    candidate_development: WorkspaceEvaluation
    candidate_regression: WorkspaceEvaluation


def _workspace_digest(source: str, function_name: str, cases: Sequence[Case]) -> str:
    payload = {
        "source_digest": source_digest(source),
        "function_name": function_name,
        "cases": [
            {"arguments": list(case.arguments), "expected": case.expected}
            for case in cases
        ],
        "runner_digest": hashlib.sha256(_RUNNER_SOURCE.encode("utf-8")).hexdigest(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _limit_process(limits: SandboxLimits) -> None:
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
    resource.setrlimit(
        resource.RLIMIT_AS,
        (limits.memory_bytes, limits.memory_bytes),
    )
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (limits.file_size_bytes, limits.file_size_bytes),
    )
    resource.setrlimit(
        resource.RLIMIT_NOFILE,
        (limits.open_files, limits.open_files),
    )
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (limits.process_count, limits.process_count),
        )
    os.setsid()


class CandidateWorkspace:
    """Evaluate bounded candidate source in a fresh temporary subprocess workspace."""

    def __init__(self, limits: SandboxLimits | None = None) -> None:
        self.limits = limits or SandboxLimits()

    def evaluate(
        self,
        source: str,
        function_name: str,
        cases: Sequence[Case],
    ) -> WorkspaceEvaluation:
        validate_source(source, function_name)
        if not cases:
            raise ValueError("cases must not be empty")

        digest = _workspace_digest(source, function_name, cases)
        with tempfile.TemporaryDirectory(prefix="mira-m023-") as raw_directory:
            directory = Path(raw_directory)
            (directory / "candidate.py").write_text(source, encoding="utf-8")
            (directory / "runner.py").write_text(_RUNNER_SOURCE, encoding="utf-8")
            (directory / "cases.json").write_text(
                json.dumps(
                    {
                        "function_name": function_name,
                        "cases": [
                            {
                                "arguments": list(case.arguments),
                                "expected": case.expected,
                            }
                            for case in cases
                        ],
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            environment = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            }
            command = [sys.executable, "-I", "-S", str(directory / "runner.py")]
            try:
                completed = subprocess.run(
                    command,
                    cwd=directory,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=self.limits.wall_seconds,
                    check=False,
                    preexec_fn=(
                        (lambda: _limit_process(self.limits))
                        if os.name == "posix"
                        else None
                    ),
                )
            except subprocess.TimeoutExpired as error:
                stdout = (error.stdout or "")[: self.limits.output_bytes]
                stderr = (error.stderr or "")[: self.limits.output_bytes]
                return WorkspaceEvaluation(
                    status="timed_out",
                    passed=0,
                    total=len(cases),
                    failures=(),
                    return_code=None,
                    timed_out=True,
                    stdout=stdout,
                    stderr=stderr,
                    source_digest=source_digest(source),
                    workspace_digest=digest,
                )

            stdout = completed.stdout[: self.limits.output_bytes]
            stderr = completed.stderr[: self.limits.output_bytes]
            if completed.returncode != 0:
                return WorkspaceEvaluation(
                    status="subprocess_failed",
                    passed=0,
                    total=len(cases),
                    failures=(),
                    return_code=completed.returncode,
                    timed_out=False,
                    stdout=stdout,
                    stderr=stderr,
                    source_digest=source_digest(source),
                    workspace_digest=digest,
                )

            try:
                payload = json.loads(stdout.strip())
                failures = tuple(dict(row) for row in payload["failures"])
                passed = int(payload["passed"])
                total = int(payload["total"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                return WorkspaceEvaluation(
                    status="invalid_runner_output",
                    passed=0,
                    total=len(cases),
                    failures=(),
                    return_code=completed.returncode,
                    timed_out=False,
                    stdout=stdout,
                    stderr=stderr,
                    source_digest=source_digest(source),
                    workspace_digest=digest,
                )

            return WorkspaceEvaluation(
                status="completed",
                passed=passed,
                total=total,
                failures=failures,
                return_code=completed.returncode,
                timed_out=False,
                stdout=stdout,
                stderr=stderr,
                source_digest=source_digest(source),
                workspace_digest=digest,
            )


class WorkspaceAdoptionGate:
    """Re-evaluate a rewrite outside the search process before changing the active body."""

    def __init__(self, workspace: CandidateWorkspace | None = None) -> None:
        self.workspace = workspace or CandidateWorkspace()

    def evaluate_and_adopt(
        self,
        body: VersionedCodeBody,
        rewrite: RewriteResult,
        development_cases: Sequence[Case],
        regression_cases: Sequence[Case],
    ) -> AdoptionDecision:
        if not rewrite.adopted:
            baseline = self.workspace.evaluate(
                body.active_source,
                body.function_name,
                development_cases,
            )
            regression = self.workspace.evaluate(
                body.active_source,
                body.function_name,
                regression_cases,
            )
            return AdoptionDecision(
                False,
                "rewrite_not_selected",
                baseline,
                baseline,
                regression,
            )
        if source_digest(body.active_source) != rewrite.baseline.digest:
            raise ValueError("rewrite result is stale for the active body")

        baseline = self.workspace.evaluate(
            body.active_source,
            body.function_name,
            development_cases,
        )
        candidate = self.workspace.evaluate(
            rewrite.selected.source,
            body.function_name,
            development_cases,
        )
        regression = self.workspace.evaluate(
            rewrite.selected.source,
            body.function_name,
            regression_cases,
        )

        if baseline.status != "completed":
            return AdoptionDecision(
                False,
                "baseline_workspace_failed",
                baseline,
                candidate,
                regression,
            )
        if candidate.status != "completed" or regression.status != "completed":
            return AdoptionDecision(
                False,
                "candidate_workspace_failed",
                baseline,
                candidate,
                regression,
            )
        if candidate.passed <= baseline.passed:
            return AdoptionDecision(
                False,
                "no_independent_strict_improvement",
                baseline,
                candidate,
                regression,
            )
        if not regression.perfect:
            return AdoptionDecision(
                False,
                "regression_gate_failed",
                baseline,
                candidate,
                regression,
            )

        body.adopt(rewrite)
        return AdoptionDecision(
            True,
            "independent_workspace_gates_passed",
            baseline,
            candidate,
            regression,
        )
