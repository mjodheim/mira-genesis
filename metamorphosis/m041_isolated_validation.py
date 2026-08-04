"""M041 — independent resource-limited validation for passive DFA candidates.

The candidate is canonical data, never executable source. A fixed evaluator runs in a fresh
subprocess workspace and independently checks schema, observations, regressions, strict
improvement and exact equivalence before an M041 release body may adopt it.

This is a bounded passive-data isolation boundary. It is not permission to execute arbitrary
code and is not a general container or micro-VM sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Mapping, Sequence

from .m012b_dfa import DFA

try:  # POSIX CI is the intended evaluator.
    import resource
except ImportError:  # pragma: no cover - non-POSIX hosts cannot enforce the limits
    resource = None  # type: ignore[assignment]

Word = tuple[int, ...]
_CANDIDATE_DOMAIN = b"m041-passive-dfa-candidate-v1"
_CASE_DOMAIN = b"m041-passive-dfa-cases-v1"
_WORKSPACE_DOMAIN = b"m041-passive-dfa-workspace-v1"

_RUNNER_SOURCE = r'''from __future__ import annotations
from collections import deque
import hashlib
import json
from pathlib import Path

CANDIDATE_DOMAIN = b"m041-passive-dfa-candidate-v1"
CASE_DOMAIN = b"m041-passive-dfa-cases-v1"


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_dfa(value, maximum_states):
    if not isinstance(value, dict):
        raise ValueError("dfa_not_mapping")
    alphabet = value.get("alphabet")
    transitions = value.get("transitions")
    accepting = value.get("accepting")
    initial = value.get("initial", 0)
    if alphabet != [0, 1]:
        raise ValueError("invalid_alphabet")
    if not isinstance(transitions, list) or not transitions:
        raise ValueError("invalid_transitions")
    if len(transitions) > maximum_states:
        raise ValueError("state_limit_exceeded")
    if not isinstance(accepting, list) or len(accepting) != len(transitions):
        raise ValueError("invalid_accepting")
    if type(initial) is not int or not 0 <= initial < len(transitions):
        raise ValueError("invalid_initial")
    frozen_rows = []
    for row in transitions:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("invalid_transition_width")
        frozen = []
        for target in row:
            if type(target) is not int or not 0 <= target < len(transitions):
                raise ValueError("invalid_transition_target")
            frozen.append(target)
        frozen_rows.append(tuple(frozen))
    if any(type(value) is not bool for value in accepting):
        raise ValueError("invalid_accepting_value")
    return (tuple(frozen_rows), tuple(accepting), initial)


def accepts(dfa, word):
    transitions, accepting, state = dfa
    for symbol in word:
        if symbol not in (0, 1):
            raise ValueError("invalid_word_symbol")
        state = transitions[state][symbol]
    return accepting[state]


def exact_equivalence(left, right):
    left_transitions, left_accepting, left_initial = left
    right_transitions, right_accepting, right_initial = right
    queue = deque([(left_initial, right_initial, [])])
    seen = {(left_initial, right_initial)}
    while queue:
        left_state, right_state, word = queue.popleft()
        if left_accepting[left_state] != right_accepting[right_state]:
            return False, word
        for symbol in (0, 1):
            pair = (
                left_transitions[left_state][symbol],
                right_transitions[right_state][symbol],
            )
            if pair not in seen:
                seen.add(pair)
                queue.append((pair[0], pair[1], word + [symbol]))
    return True, None


root = Path(__file__).resolve().parent
candidate_value = json.loads((root / "candidate.json").read_text(encoding="utf-8"))
parent_value = json.loads((root / "parent.json").read_text(encoding="utf-8"))
target_value = json.loads((root / "target.json").read_text(encoding="utf-8"))
evaluation = json.loads((root / "evaluation.json").read_text(encoding="utf-8"))
maximum_states = int(evaluation["limits"]["maximum_states"])

try:
    candidate = load_dfa(candidate_value, maximum_states)
    parent = load_dfa(parent_value, maximum_states)
    target = load_dfa(target_value, maximum_states)
except ValueError as error:
    print(json.dumps({
        "status": "invalid_candidate_data",
        "schema_valid": False,
        "error": str(error),
    }, sort_keys=True))
    raise SystemExit(0)

candidate_digest = hashlib.sha256(
    CANDIDATE_DOMAIN + canonical_bytes(candidate_value)
).hexdigest()
case_digest = hashlib.sha256(
    CASE_DOMAIN + canonical_bytes({
        "cases": evaluation["cases"],
        "regressions": evaluation["regressions"],
    })
).hexdigest()

def score(dfa, rows):
    passed = 0
    failures = []
    for index, row in enumerate(rows):
        word = row["word"]
        expected = row["expected"]
        actual = accepts(dfa, word)
        if actual == expected:
            passed += 1
        else:
            failures.append({
                "index": index,
                "word": word,
                "expected": expected,
                "actual": actual,
            })
    return passed, failures

candidate_passed, task_failures = score(candidate, evaluation["cases"])
parent_passed, _ = score(parent, evaluation["cases"])
regression_passed, regression_failures = score(candidate, evaluation["regressions"])
exact, witness = exact_equivalence(candidate, target)

payload = {
    "status": "completed",
    "schema_valid": True,
    "candidate_digest": candidate_digest,
    "candidate_digest_matches": candidate_digest == evaluation["candidate_digest"],
    "case_digest": case_digest,
    "case_digest_matches": case_digest == evaluation["case_digest"],
    "candidate_passed": candidate_passed,
    "parent_passed": parent_passed,
    "task_total": len(evaluation["cases"]),
    "regression_passed": regression_passed,
    "regression_total": len(evaluation["regressions"]),
    "task_failures": task_failures,
    "regression_failures": regression_failures,
    "task_passed": candidate_passed == len(evaluation["cases"]),
    "regressions_passed": regression_passed == len(evaluation["regressions"]),
    "strict_improvement": candidate_passed > parent_passed,
    "exact": exact,
    "equivalence_witness": witness,
}
print(json.dumps(payload, sort_keys=True))
'''


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def dfa_candidate_digest(dfa: DFA) -> str:
    return hashlib.sha256(_CANDIDATE_DOMAIN + _canonical_bytes(dfa.to_dict())).hexdigest()


def _case_rows(observations: Mapping[Word, bool]) -> list[dict[str, object]]:
    return [
        {"word": list(word), "expected": bool(expected)}
        for word, expected in sorted(observations.items())
    ]


def _case_digest(
    cases: Sequence[Mapping[str, object]],
    regressions: Sequence[Mapping[str, object]],
) -> str:
    return hashlib.sha256(
        _CASE_DOMAIN
        + _canonical_bytes({"cases": list(cases), "regressions": list(regressions)})
    ).hexdigest()


@dataclass(frozen=True)
class DFAWorkspaceLimits:
    cpu_seconds: int = 2
    memory_bytes: int = 128 * 1024 * 1024
    file_size_bytes: int = 2 * 1024 * 1024
    process_count: int = 1
    open_files: int = 32
    wall_seconds: int = 5
    output_bytes: int = 128 * 1024
    maximum_states: int = 64
    maximum_observations: int = 4_096
    maximum_input_bytes: int = 4 * 1024 * 1024

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")

    def mapping(self) -> dict[str, int]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class IsolatedDFAValidation:
    status: str
    schema_valid: bool
    candidate_digest_matches: bool
    case_digest_matches: bool
    task_passed: bool
    regressions_passed: bool
    strict_improvement: bool
    exact: bool
    candidate_passed: int
    parent_passed: int
    task_total: int
    regression_passed: int
    regression_total: int
    task_failures: tuple[Mapping[str, object], ...]
    regression_failures: tuple[Mapping[str, object], ...]
    equivalence_witness: tuple[int, ...] | None
    return_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    candidate_digest: str
    parent_digest: str
    target_digest: str
    case_digest: str
    workspace_digest: str
    limits: Mapping[str, int]

    @property
    def perfect(self) -> bool:
        return all(
            (
                self.status == "completed",
                self.schema_valid,
                self.candidate_digest_matches,
                self.case_digest_matches,
                self.task_passed,
                self.regressions_passed,
                self.strict_improvement,
                self.exact,
                not self.timed_out,
                self.return_code == 0,
            )
        )

    def mapping(self) -> dict[str, object]:
        return {
            "status": self.status,
            "schema_valid": self.schema_valid,
            "candidate_digest_matches": self.candidate_digest_matches,
            "case_digest_matches": self.case_digest_matches,
            "task_passed": self.task_passed,
            "regressions_passed": self.regressions_passed,
            "strict_improvement": self.strict_improvement,
            "exact": self.exact,
            "candidate_passed": self.candidate_passed,
            "parent_passed": self.parent_passed,
            "task_total": self.task_total,
            "regression_passed": self.regression_passed,
            "regression_total": self.regression_total,
            "task_failures": [dict(row) for row in self.task_failures],
            "regression_failures": [dict(row) for row in self.regression_failures],
            "equivalence_witness": (
                None if self.equivalence_witness is None else list(self.equivalence_witness)
            ),
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "candidate_digest": self.candidate_digest,
            "parent_digest": self.parent_digest,
            "target_digest": self.target_digest,
            "case_digest": self.case_digest,
            "workspace_digest": self.workspace_digest,
            "limits": dict(self.limits),
            "passive_candidate_data": True,
            "candidate_execution_authority": False,
        }


def _limit_process(limits: DFAWorkspaceLimits) -> None:
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
    resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (limits.file_size_bytes, limits.file_size_bytes),
    )
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (limits.process_count, limits.process_count),
        )
    os.setsid()


class IsolatedDFAWorkspace:
    """Evaluate passive DFA data in a fresh fixed-runner subprocess."""

    def __init__(self, limits: DFAWorkspaceLimits | None = None) -> None:
        self.limits = limits or DFAWorkspaceLimits()

    def evaluate(
        self,
        *,
        parent: DFA,
        candidate: DFA,
        target: DFA,
        observations: Mapping[Word, bool],
        expected_candidate_digest: str | None = None,
    ) -> IsolatedDFAValidation:
        if not observations:
            raise ValueError("observations must not be empty")
        if len(observations) > self.limits.maximum_observations:
            raise ValueError("observation limit exceeded")
        if max(parent.n_states, candidate.n_states, target.n_states) > self.limits.maximum_states:
            raise ValueError("state limit exceeded")

        cases = _case_rows(observations)
        regressions = [
            row
            for row in cases
            if parent.accepts(tuple(int(symbol) for symbol in row["word"]))
            == bool(row["expected"])
        ]
        candidate_digest = dfa_candidate_digest(candidate)
        expected_digest = expected_candidate_digest or candidate_digest
        case_digest = _case_digest(cases, regressions)
        evaluation = {
            "candidate_digest": expected_digest,
            "case_digest": case_digest,
            "cases": cases,
            "regressions": regressions,
            "limits": self.limits.mapping(),
        }
        files = {
            "candidate.json": candidate.to_dict(),
            "parent.json": parent.to_dict(),
            "target.json": target.to_dict(),
            "evaluation.json": evaluation,
        }
        total_input_bytes = sum(len(_canonical_bytes(value)) for value in files.values())
        if total_input_bytes > self.limits.maximum_input_bytes:
            raise ValueError("input byte limit exceeded")
        workspace_digest = hashlib.sha256(
            _WORKSPACE_DOMAIN
            + _canonical_bytes(files)
            + hashlib.sha256(_RUNNER_SOURCE.encode("utf-8")).digest()
        ).hexdigest()

        with tempfile.TemporaryDirectory(prefix="mira-m041-") as raw_directory:
            directory = Path(raw_directory)
            for name, value in files.items():
                (directory / name).write_text(
                    json.dumps(value, sort_keys=True),
                    encoding="utf-8",
                )
            (directory / "runner.py").write_text(_RUNNER_SOURCE, encoding="utf-8")
            environment = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
                "NO_PROXY": "*",
                "no_proxy": "*",
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
                return self._failure(
                    status="timed_out",
                    parent=parent,
                    candidate=candidate,
                    target=target,
                    candidate_digest=candidate_digest,
                    case_digest=case_digest,
                    workspace_digest=workspace_digest,
                    return_code=None,
                    timed_out=True,
                    stdout=str(error.stdout or "")[: self.limits.output_bytes],
                    stderr=str(error.stderr or "")[: self.limits.output_bytes],
                    task_total=len(cases),
                    regression_total=len(regressions),
                )

            stdout = completed.stdout[: self.limits.output_bytes]
            stderr = completed.stderr[: self.limits.output_bytes]
            if completed.returncode != 0:
                return self._failure(
                    status="subprocess_failed",
                    parent=parent,
                    candidate=candidate,
                    target=target,
                    candidate_digest=candidate_digest,
                    case_digest=case_digest,
                    workspace_digest=workspace_digest,
                    return_code=completed.returncode,
                    timed_out=False,
                    stdout=stdout,
                    stderr=stderr,
                    task_total=len(cases),
                    regression_total=len(regressions),
                )
            try:
                payload = json.loads(stdout.strip())
            except json.JSONDecodeError:
                return self._failure(
                    status="invalid_runner_output",
                    parent=parent,
                    candidate=candidate,
                    target=target,
                    candidate_digest=candidate_digest,
                    case_digest=case_digest,
                    workspace_digest=workspace_digest,
                    return_code=completed.returncode,
                    timed_out=False,
                    stdout=stdout,
                    stderr=stderr,
                    task_total=len(cases),
                    regression_total=len(regressions),
                )

            witness = payload.get("equivalence_witness")
            return IsolatedDFAValidation(
                status=str(payload.get("status", "invalid_runner_output")),
                schema_valid=bool(payload.get("schema_valid", False)),
                candidate_digest_matches=bool(payload.get("candidate_digest_matches", False)),
                case_digest_matches=bool(payload.get("case_digest_matches", False)),
                task_passed=bool(payload.get("task_passed", False)),
                regressions_passed=bool(payload.get("regressions_passed", False)),
                strict_improvement=bool(payload.get("strict_improvement", False)),
                exact=bool(payload.get("exact", False)),
                candidate_passed=int(payload.get("candidate_passed", 0)),
                parent_passed=int(payload.get("parent_passed", 0)),
                task_total=int(payload.get("task_total", len(cases))),
                regression_passed=int(payload.get("regression_passed", 0)),
                regression_total=int(payload.get("regression_total", len(regressions))),
                task_failures=tuple(dict(row) for row in payload.get("task_failures", ())),
                regression_failures=tuple(
                    dict(row) for row in payload.get("regression_failures", ())
                ),
                equivalence_witness=(
                    None if witness is None else tuple(int(symbol) for symbol in witness)
                ),
                return_code=completed.returncode,
                timed_out=False,
                stdout=stdout,
                stderr=stderr,
                candidate_digest=candidate_digest,
                parent_digest=dfa_candidate_digest(parent),
                target_digest=dfa_candidate_digest(target),
                case_digest=case_digest,
                workspace_digest=workspace_digest,
                limits=self.limits.mapping(),
            )

    def _failure(
        self,
        *,
        status: str,
        parent: DFA,
        candidate: DFA,
        target: DFA,
        candidate_digest: str,
        case_digest: str,
        workspace_digest: str,
        return_code: int | None,
        timed_out: bool,
        stdout: str,
        stderr: str,
        task_total: int,
        regression_total: int,
    ) -> IsolatedDFAValidation:
        return IsolatedDFAValidation(
            status=status,
            schema_valid=False,
            candidate_digest_matches=False,
            case_digest_matches=False,
            task_passed=False,
            regressions_passed=False,
            strict_improvement=False,
            exact=False,
            candidate_passed=0,
            parent_passed=0,
            task_total=task_total,
            regression_passed=0,
            regression_total=regression_total,
            task_failures=(),
            regression_failures=(),
            equivalence_witness=None,
            return_code=return_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            candidate_digest=candidate_digest,
            parent_digest=dfa_candidate_digest(parent),
            target_digest=dfa_candidate_digest(target),
            case_digest=case_digest,
            workspace_digest=workspace_digest,
            limits=self.limits.mapping(),
        )


@dataclass
class VersionedDFARelease:
    active: DFA
    archive: list[DFA] = field(default_factory=list)

    def adopt(self, candidate: DFA) -> None:
        self.archive.append(self.active)
        self.active = candidate

    def rollback(self) -> None:
        if not self.archive:
            raise ValueError("rollback requested with an empty archive")
        self.active = self.archive.pop()


@dataclass(frozen=True)
class IsolatedAdoptionDecision:
    adopted: bool
    reason: str
    validation: IsolatedDFAValidation


class IsolatedDFAAdoptionGate:
    """Validate outside the search process before changing the M041 release body."""

    def __init__(self, workspace: IsolatedDFAWorkspace | None = None) -> None:
        self.workspace = workspace or IsolatedDFAWorkspace()

    def evaluate_and_adopt(
        self,
        *,
        release: VersionedDFARelease,
        expected_parent_digest: str,
        candidate: DFA,
        target: DFA,
        observations: Mapping[Word, bool],
        expected_candidate_digest: str,
    ) -> IsolatedAdoptionDecision:
        if dfa_candidate_digest(release.active) != expected_parent_digest:
            raise ValueError("candidate is stale for the active release parent")
        validation = self.workspace.evaluate(
            parent=release.active,
            candidate=candidate,
            target=target,
            observations=observations,
            expected_candidate_digest=expected_candidate_digest,
        )
        if not validation.perfect:
            return IsolatedAdoptionDecision(False, "isolated_validation_failed", validation)
        release.adopt(candidate)
        return IsolatedAdoptionDecision(
            True,
            "isolated_validation_passed_before_release_adoption",
            validation,
        )
