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


def _validate(
    probes: Sequence[CapabilityProbe], environment_id: str, environment_sha256: str,
) -> None:
    if not probes:
        raise ProbeExecutionError("probing requires at least one capability probe")
    identifiers = [probe.capability_id for probe in probes]
    if len(set(identifiers)) != len(identifiers):
        raise ProbeExecutionError("capability probes must have unique identifiers")
    if not environment_id:
        raise ProbeExecutionError("probing requires the identifier of the probed environment")
    if (
        not isinstance(environment_sha256, str) or len(environment_sha256) != 64
        or any(character not in "0123456789abcdef" for character in environment_sha256)
    ):
        raise ProbeExecutionError("probing requires an exact lowercase environment SHA-256")


def probe_environment(
    probes: Sequence[CapabilityProbe], execute: ProbeExecutor, environment_id: str,
    environment_sha256: str,
) -> tuple[CapabilityCertificate, ...]:
    """Run every probe once and certify the outcome.

    `execute` returns `(returncode, ran)`.  Any exception it raises is caught and recorded as a
    probe that did not run, so infrastructure faults degrade to `INCONCLUSIVE`.
    """

    _validate(probes, environment_id, environment_sha256)
    certificates: list[CapabilityCertificate] = []
    for probe in probes:
        try:
            returncode, ran = execute(probe)
        except Exception:  # noqa: BLE001 - an environment fault is not evidence of absence
            returncode, ran = None, False
        certificates.append(
            certify(probe, returncode, environment_id, environment_sha256, ran=ran)
        )
    return tuple(certificates)


async def probe_environment_async(
    probes: Sequence[CapabilityProbe], execute: AsyncProbeExecutor, environment_id: str,
    environment_sha256: str,
) -> tuple[CapabilityCertificate, ...]:
    """Asynchronous counterpart for Harbor-style environments."""

    _validate(probes, environment_id, environment_sha256)
    certificates: list[CapabilityCertificate] = []
    for probe in probes:
        try:
            returncode, ran = await execute(probe)
        except Exception:  # noqa: BLE001 - an environment fault is not evidence of absence
            returncode, ran = None, False
        certificates.append(
            certify(probe, returncode, environment_id, environment_sha256, ran=ran)
        )
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
    supplied = tuple(certificates)
    expected_probe_digests = {probe.capability_id: probe.digest() for probe in probes}
    for certificate in supplied:
        expected = expected_probe_digests.get(certificate.capability_id)
        if expected is not None and certificate.probe_sha256 != expected:
            raise ProbeExecutionError(
                f"task {task_id!r} certificate does not bind its declared probe"
            )
    try:
        return TaskLabel(task_id, required, supplied)
    except CalibrationError as exc:
        raise ProbeExecutionError(f"task {task_id!r} could not be labelled: {exc}") from exc


__all__ = [
    "AsyncProbeExecutor", "ProbeExecutionError", "ProbeExecutor", "harbor_probe_executor",
    "label_task", "probe_environment", "probe_environment_async",
]
