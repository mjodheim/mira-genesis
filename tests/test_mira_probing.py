from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib

import pytest

from mira_core.calibration import CapabilityProbe, ProbeVerdict, Solvability, certify
from mira_core.probing import (
    ProbeExecutionError, harbor_probe_executor, label_task, probe_environment,
    probe_environment_async,
)


ENVIRONMENT_SHA256 = hashlib.sha256(b"env-1 exact configuration").hexdigest()
COMPILER = CapabilityProbe(
    "c_compiler", ("cc", "--version"), absent_returncodes=(127,),
)
NETWORK = CapabilityProbe(
    "network", ("curl", "-sS", "https://example.invalid"), absent_returncodes=(6,),
)


@dataclass
class FakeExecResult:
    return_code: int | None


class FakeEnvironment:
    def __init__(self, codes: dict[str, int | None], *, raises: str | None = None) -> None:
        self.codes = codes
        self.raises = raises
        self.scripts: list[tuple[str, int | None]] = []

    async def exec(self, script: str, timeout_sec: int | None = None):
        self.scripts.append((script, timeout_sec))
        if self.raises is not None and self.raises in script:
            raise OSError("container exec failed")
        return FakeExecResult(self.codes.get(script.split()[0]))


def test_absent_and_present_capabilities_are_certified_from_return_codes() -> None:
    def execute(probe: CapabilityProbe) -> tuple[int | None, bool]:
        return (0, True) if probe.capability_id == "c_compiler" else (6, True)

    certificates = probe_environment(
        (COMPILER, NETWORK), execute, "env-1", ENVIRONMENT_SHA256,
    )
    assert [c.verdict for c in certificates] == [ProbeVerdict.PRESENT, ProbeVerdict.ABSENT]
    assert {c.environment_id for c in certificates} == {"env-1"}
    assert {c.environment_sha256 for c in certificates} == {ENVIRONMENT_SHA256}


def test_an_environment_fault_never_becomes_evidence_of_absence() -> None:
    """The most damaging possible error: manufacturing impossibility from broken infrastructure."""

    def execute(probe: CapabilityProbe) -> tuple[int | None, bool]:
        raise OSError("environment unreachable")

    certificates = probe_environment((COMPILER,), execute, "env-1", ENVIRONMENT_SHA256)
    assert certificates[0].verdict is ProbeVerdict.INCONCLUSIVE
    assert label_task("t", (COMPILER,), certificates).solvability is Solvability.UNLABELLED


def test_a_probe_reporting_no_return_code_is_inconclusive() -> None:
    def execute(probe: CapabilityProbe) -> tuple[int | None, bool]:
        return None, True

    certificates = probe_environment((COMPILER,), execute, "env-1", ENVIRONMENT_SHA256)
    assert certificates[0].verdict is ProbeVerdict.INCONCLUSIVE


def test_harbor_executor_renders_argv_as_a_posix_script() -> None:
    environment = FakeEnvironment({"cc": 127, "curl": 0})
    certificates = asyncio.run(probe_environment_async(
        (COMPILER, NETWORK), harbor_probe_executor(environment, timeout_seconds=9), "image-a1b2",
        ENVIRONMENT_SHA256,
    ))
    assert environment.scripts == [
        ("cc --version", 9), ("curl -sS https://example.invalid", 9),
    ]
    assert certificates[0].verdict is ProbeVerdict.ABSENT
    assert certificates[1].verdict is ProbeVerdict.PRESENT


def test_harbor_executor_degrades_a_failing_environment_to_inconclusive() -> None:
    environment = FakeEnvironment({"cc": 0}, raises="cc")
    certificates = asyncio.run(probe_environment_async(
        (COMPILER,), harbor_probe_executor(environment), "image-a1b2", ENVIRONMENT_SHA256,
    ))
    assert certificates[0].verdict is ProbeVerdict.INCONCLUSIVE


def test_probe_runner_rejects_misconfiguration() -> None:
    def execute(probe: CapabilityProbe) -> tuple[int | None, bool]:
        return 0, True

    with pytest.raises(ProbeExecutionError, match="at least one capability probe"):
        probe_environment((), execute, "env-1", ENVIRONMENT_SHA256)
    with pytest.raises(ProbeExecutionError, match="unique identifiers"):
        probe_environment((COMPILER, COMPILER), execute, "env-1", ENVIRONMENT_SHA256)
    with pytest.raises(ProbeExecutionError, match="identifier of the probed environment"):
        probe_environment((COMPILER,), execute, "", ENVIRONMENT_SHA256)
    with pytest.raises(ProbeExecutionError, match="environment SHA-256"):
        probe_environment((COMPILER,), execute, "env-1", "not-a-digest")
    with pytest.raises(ProbeExecutionError, match="environment SHA-256"):
        probe_environment((COMPILER,), execute, "env-1", None)  # type: ignore[arg-type]
    with pytest.raises(ProbeExecutionError, match="environment with exec"):
        harbor_probe_executor(object())


def test_label_task_requires_certificates_for_every_declared_capability() -> None:
    certificates = probe_environment(
        (COMPILER,), lambda probe: (0, True), "env-1", ENVIRONMENT_SHA256,
    )
    with pytest.raises(ProbeExecutionError, match="could not be labelled"):
        label_task("t", (COMPILER, NETWORK), certificates)
    label = label_task("t", (COMPILER,), certificates)
    assert label.solvability is Solvability.FEASIBLE


def test_label_task_rejects_a_certificate_for_a_mutated_probe_contract() -> None:
    original = CapabilityProbe("tool", ("tool", "--version"), absent_returncodes=(127,))
    mutated = CapabilityProbe("tool", ("different-tool", "--version"), absent_returncodes=(127,))
    certificate = certify(original, 0, "env-1", ENVIRONMENT_SHA256)
    with pytest.raises(ProbeExecutionError, match="does not bind its declared probe"):
        label_task("t", (mutated,), (certificate,))
