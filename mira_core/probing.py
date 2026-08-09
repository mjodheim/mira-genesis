"""Execute capability probes against a real environment and certify what they found.

`mira_core.calibration` defines what a certificate means; this module obtains one.  Execution is
dependency-inverted: callers supply a function that runs one probe, so the same runner serves a
Harbor container, a governed terminal body or a test double without this module importing any of
them.

The rule from `calibration` is enforced here rather than restated: **an environment failure yields
`INCONCLUSIVE`, never `ABSENT`.**  A probe that could not run tells us nothing about the
capability, and treating it as absence would manufacture impossibility labels out of broken
infrastructure — the single most damaging error this instrument could make.
"""
from __future__ import annotations

import shlex
from typing import Awaitable, Callable, Iterable, Sequence

from mira_core.calibration import (
    CalibrationError, CapabilityCertificate, CapabilityProbe, TaskLabel, certify,
)


class ProbeExecutionError(RuntimeError):
    """Raised when a probe runner is misconfigured, never when a probe merely fails."""


ProbeExecutor = Callable[[CapabilityProbe], "tuple[int | None, bool]"]
AsyncProbeExecutor = Callable[[CapabilityProbe], Awaitable["tuple[int | None, bool]"]]


def _validate(probes: Sequence[CapabilityProbe], environment_id: str) -> None:
    if not probes:
        raise ProbeExecutionError("probing requires at least one capability probe")
    identifiers = [probe.capability_id for probe in probes]
    if len(set(identifiers)) != len(identifiers):
        raise ProbeExecutionError("capability probes must have unique identifiers")
    if not environment_id:
        raise ProbeExecutionError("probing requires the identifier of the probed environment")


def probe_environment(
    probes: Sequence[CapabilityProbe], execute: ProbeExecutor, environment_id: str,
) -> tuple[CapabilityCertificate, ...]:
    """Run every probe once and certify the outcome.

    `execute` returns `(returncode, ran)`.  Any exception it raises is caught and recorded as a
    probe that did not run, so infrastructure faults degrade to `INCONCLUSIVE`.
    """

    _validate(probes, environment_id)
    certificates: list[CapabilityCertificate] = []
    for probe in probes:
        try:
            returncode, ran = execute(probe)
        except Exception:  # noqa: BLE001 - an environment fault is not evidence of absence
            returncode, ran = None, False
        certificates.append(certify(probe, returncode, environment_id, ran=ran))
    return tuple(certificates)


async def probe_environment_async(
    probes: Sequence[CapabilityProbe], execute: AsyncProbeExecutor, environment_id: str,
) -> tuple[CapabilityCertificate, ...]:
    """Asynchronous counterpart for Harbor-style environments."""

    _validate(probes, environment_id)
    certificates: list[CapabilityCertificate] = []
    for probe in probes:
        try:
            returncode, ran = await execute(probe)
        except Exception:  # noqa: BLE001 - an environment fault is not evidence of absence
            returncode, ran = None, False
        certificates.append(certify(probe, returncode, environment_id, ran=ran))
    return tuple(certificates)


def harbor_probe_executor(environment: object, *, timeout_seconds: int = 30) -> AsyncProbeExecutor:
    """Adapt a Harbor environment, whose `exec` takes a POSIX shell script, to a probe executor."""

    exec_method = getattr(environment, "exec", None)
    if not callable(exec_method):
        raise ProbeExecutionError("a Harbor probe executor requires an environment with exec()")

    async def execute(probe: CapabilityProbe) -> tuple[int | None, bool]:
        result = await exec_method(shlex.join(probe.argv), timeout_sec=timeout_seconds)
        returncode = getattr(result, "return_code", None)
        if returncode is None:
            return None, False
        return int(returncode), True

    return execute


def label_task(
    task_id: str, probes: Sequence[CapabilityProbe],
    certificates: Iterable[CapabilityCertificate],
) -> TaskLabel:
    """Bind probed certificates to the capabilities a task declares it requires."""

    required = tuple(probe.capability_id for probe in probes)
    if not required:
        raise ProbeExecutionError("a labelled task must declare at least one capability")
    try:
        return TaskLabel(task_id, required, tuple(certificates))
    except CalibrationError as exc:
        raise ProbeExecutionError(f"task {task_id!r} could not be labelled: {exc}") from exc


__all__ = [
    "AsyncProbeExecutor", "ProbeExecutionError", "ProbeExecutor", "harbor_probe_executor",
    "label_task", "probe_environment", "probe_environment_async",
]
