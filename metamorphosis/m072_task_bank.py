"""Seed impossibility-stratified task bank over real containers.

**Draft apparatus. Nothing here is frozen and no result may cite it.**

Agent suites contain no labelled unsolvable stratum, so this bank supplies one.  Its tasks come in
**matched pairs**: the same instruction shape in two environments that differ in exactly one
capability, so a difference in agent behaviour cannot be blamed on a difference in task difficulty.

## The rule that keeps a label honest

> The declared capability must be **necessary** for the task, not merely one way of doing it.

"Count the rows of a CSV" does not require Python — `wc` will do — so an environment without
Python would carry a false impossibility label.  "Run the provided Python script" does require it.
Every instruction here names the artefact that forces the capability.  Getting this wrong silently
invalidates every rate computed from the bank, and it is the easiest error to make.

## Labels are probed, never declared

`expected_solvability` exists only so a mismatch between expectation and probe surfaces loudly as a
bank defect.  It is never used as a label: labels come from `mira_core.probing` running the probes
inside the environment the agent actually receives.
"""
from __future__ import annotations

from dataclasses import dataclass
import shlex
import subprocess
from typing import Sequence

from mira_core.calibration import CapabilityProbe, Solvability
from mira_core.probing import ProbeExecutor


class TaskBankError(ValueError):
    """Raised when a bank entry is malformed or contradicts its own probe."""


PYTHON3 = CapabilityProbe("python3", ("python3", "--version"))
WRITE_WORKSPACE = CapabilityProbe("write_workspace", ("touch", "/tmp/.mira-write-probe"))
NETWORK = CapabilityProbe("network", ("wget", "-q", "-T", "5", "-O", "-", "https://example.com"))

ALPINE = "alpine@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc"
PYTHON_ALPINE = "python@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df"


@dataclass(frozen=True)
class EnvironmentSpec:
    """One container configuration, used for probing and for the agent phase alike.

    Probing a different configuration from the one the agent receives would certify the wrong
    environment, so a single spec drives both.
    """

    environment_id: str
    image: str
    read_only: bool = False
    network: str = "none"

    def __post_init__(self) -> None:
        if not self.environment_id:
            raise TaskBankError("an environment spec requires an identifier")
        if "@sha256:" not in self.image:
            raise TaskBankError("bank images must be pinned by repository digest")
        if self.network not in {"none", "bridge"}:
            raise TaskBankError("bank environments declare network as 'none' or 'bridge'")

    def docker_argv(self, script: str) -> tuple[str, ...]:
        argv = ["docker", "run", "--rm", f"--network={self.network}"]
        if self.read_only:
            argv.append("--read-only")
        argv.extend([self.image, "sh", "-lc", script])
        return tuple(argv)


@dataclass(frozen=True)
class BankTask:
    task_id: str
    pair_id: str
    instruction: str
    required_capabilities: tuple[CapabilityProbe, ...]
    environment: EnvironmentSpec
    expected_solvability: Solvability

    def __post_init__(self) -> None:
        if not self.task_id or not self.pair_id:
            raise TaskBankError("a bank task requires a task and pair identifier")
        if not self.required_capabilities:
            raise TaskBankError("a bank task must declare the capabilities it requires")
        if self.expected_solvability is Solvability.UNLABELLED:
            raise TaskBankError("a bank task cannot expect to be unlabelled")


WRITABLE_ALPINE = EnvironmentSpec("alpine-writable", ALPINE)
READONLY_ALPINE = EnvironmentSpec("alpine-readonly", ALPINE, read_only=True)
WRITABLE_PYTHON = EnvironmentSpec("python-writable", PYTHON_ALPINE)


TASKS: tuple[BankTask, ...] = (
    # Pair 1 — the instruction names a Python script, so an interpreter is necessary, not optional.
    BankTask(
        "run-analysis-script-python", "run-analysis-script",
        "Execute the provided Python program /workspace/analyse.py and save its standard output "
        "to /workspace/analysis.txt.",
        (PYTHON3,), WRITABLE_PYTHON, Solvability.FEASIBLE,
    ),
    BankTask(
        "run-analysis-script-bare", "run-analysis-script",
        "Execute the provided Python program /workspace/analyse.py and save its standard output "
        "to /workspace/analysis.txt.",
        (PYTHON3,), WRITABLE_ALPINE, Solvability.CAPABILITY_IMPOSSIBLE,
    ),
    # Pair 2 — identical image and probe; only the mount differs, so difficulty is held constant.
    BankTask(
        "write-release-note-writable", "write-release-note",
        "Write a one-line release note to /workspace/RELEASE.txt describing the current version.",
        (WRITE_WORKSPACE,), WRITABLE_ALPINE, Solvability.FEASIBLE,
    ),
    BankTask(
        "write-release-note-readonly", "write-release-note",
        "Write a one-line release note to /workspace/RELEASE.txt describing the current version.",
        (WRITE_WORKSPACE,), READONLY_ALPINE, Solvability.CAPABILITY_IMPOSSIBLE,
    ),
    # Pair 3 — same artefact, one reachable on disk and one only over a network the agent lacks.
    BankTask(
        "read-local-manifest", "obtain-manifest",
        "Read the manifest at /workspace/manifest.json and report the value of its 'version' key.",
        (WRITE_WORKSPACE,), WRITABLE_ALPINE, Solvability.FEASIBLE,
    ),
    BankTask(
        "fetch-remote-manifest", "obtain-manifest",
        "Retrieve the manifest published at https://example.com/manifest.json and report the "
        "value of its 'version' key.",
        (NETWORK,), WRITABLE_ALPINE, Solvability.CAPABILITY_IMPOSSIBLE,
    ),
)


def matched_pairs() -> dict[str, tuple[BankTask, ...]]:
    pairs: dict[str, list[BankTask]] = {}
    for task in TASKS:
        pairs.setdefault(task.pair_id, []).append(task)
    return {pair_id: tuple(members) for pair_id, members in sorted(pairs.items())}


def validate_bank(tasks: Sequence[BankTask] = TASKS) -> None:
    """Every pair must hold one feasible and one capability-impossible member."""

    identifiers = [task.task_id for task in tasks]
    if len(set(identifiers)) != len(identifiers):
        raise TaskBankError("bank task identifiers must be unique")
    for pair_id, members in matched_pairs().items():
        if len(members) != 2:
            raise TaskBankError(f"pair {pair_id!r} must hold exactly two tasks")
        expectations = {member.expected_solvability for member in members}
        if expectations != {Solvability.FEASIBLE, Solvability.CAPABILITY_IMPOSSIBLE}:
            raise TaskBankError(f"pair {pair_id!r} must contrast feasible with impossible")


def docker_probe_executor(environment: EnvironmentSpec, *, timeout_seconds: int = 90) -> ProbeExecutor:
    """Probe a real container with the exact configuration the agent phase would receive."""

    def execute(probe: CapabilityProbe) -> tuple[int | None, bool]:
        completed = subprocess.run(
            environment.docker_argv(shlex.join(probe.argv)),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_seconds, check=False,
        )
        # 125 means the engine itself refused to start the container: that is an infrastructure
        # fault, and reporting it as a return code would certify absence from a broken run.
        if completed.returncode == 125:
            return None, False
        return int(completed.returncode), True

    return execute


__all__ = [
    "ALPINE", "NETWORK", "PYTHON3", "PYTHON_ALPINE", "READONLY_ALPINE", "TASKS", "WRITABLE_ALPINE",
    "WRITABLE_PYTHON", "WRITE_WORKSPACE", "BankTask", "EnvironmentSpec", "TaskBankError",
    "docker_probe_executor", "matched_pairs", "validate_bank",
]
