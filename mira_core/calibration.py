"""Certified capability absence and refusal calibration for agentic tasks.

Agent benchmarks are built from tasks that are solvable by construction: an unsolvable task looks
like a broken task and is removed during cleaning.  Nothing therefore measures whether an agent
refuses *correctly*, and an agent that grinds a budget away on a task it could never finish scores
the same as one that stops and says so.

This module supplies the missing halves:

* a mechanical certificate that a required capability is **absent** from the environment the agent
  actually receives, so an impossibility label is probed rather than asserted;
* refusal calibration over such labels — true-refusal rate, false-refusal rate and the wasted
  effort spent on tasks no agent could have completed.

## What a certificate does and does not say

A certificate states that a declared capability was absent when probed.  It never states that no
solution exists: that question is undecidable for general software tasks, and this module refuses
to express it.  Labels are therefore **capability-impossible**, never simply "impossible".  If a
task is merely hard, it is feasible here and any refusal on it counts against the agent.

Every rate is `None` when its denominator is empty.  An undefined rate is not zero, and reporting
it as zero would silently invent evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable, Mapping, Sequence


class CalibrationError(ValueError):
    """Raised when a label, outcome or threshold violates its declared contract."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ProbeVerdict(Enum):
    """Whether a probe found the capability present."""

    PRESENT = "present"
    ABSENT = "absent"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class CapabilityProbe:
    """One command whose exit status decides whether a capability exists.

    The probe must run inside the same environment the agent receives.  A probe that cannot run is
    `INCONCLUSIVE`, never `ABSENT`: a broken probe is not evidence of absence.
    """

    capability_id: str
    argv: tuple[str, ...]
    present_returncodes: tuple[int, ...] = (0,)
    absent_returncodes: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.capability_id or not self.capability_id.strip():
            raise CalibrationError("a capability probe requires an identifier")
        if not self.argv or any(not isinstance(item, str) or not item for item in self.argv):
            raise CalibrationError("a capability probe requires explicit argv")
        if not self.present_returncodes:
            raise CalibrationError("a capability probe requires at least one present return code")
        for name, codes in (
            ("present", self.present_returncodes), ("absent", self.absent_returncodes),
        ):
            if any(not isinstance(code, int) or isinstance(code, bool) for code in codes):
                raise CalibrationError(f"{name} return codes must be integers")
            if len(set(codes)) != len(codes):
                raise CalibrationError(f"{name} return codes must be unique")
        overlap = set(self.present_returncodes) & set(self.absent_returncodes)
        if overlap:
            raise CalibrationError(
                f"present and absent return codes overlap: {sorted(overlap)}"
            )

    def public_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "argv": list(self.argv),
            "present_returncodes": list(self.present_returncodes),
            "absent_returncodes": list(self.absent_returncodes),
        }

    def digest(self) -> str:
        """Bind a certificate to the exact command and interpretation contract probed."""

        return _sha256(_canonical_json(self.public_dict()))

    def interpret(self, returncode: int | None, *, ran: bool = True) -> ProbeVerdict:
        if (
            not ran or returncode is None or not isinstance(returncode, int)
            or isinstance(returncode, bool)
        ):
            return ProbeVerdict.INCONCLUSIVE
        if returncode in self.present_returncodes:
            return ProbeVerdict.PRESENT
        if returncode in self.absent_returncodes:
            return ProbeVerdict.ABSENT
        # A timeout, permission error or novel tool failure is not evidence that the declared
        # capability is absent.  Absence must be named by the probe contract before execution.
        return ProbeVerdict.INCONCLUSIVE


@dataclass(frozen=True)
class CapabilityCertificate:
    """The recorded outcome of one probe in one environment."""

    capability_id: str
    verdict: ProbeVerdict
    returncode: int | None
    environment_id: str
    environment_sha256: str
    probe_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.capability_id, str) or not self.capability_id
            or not isinstance(self.environment_id, str) or not self.environment_id
        ):
            raise CalibrationError("a certificate requires capability and environment identifiers")
        if self.returncode is not None and (
            not isinstance(self.returncode, int) or isinstance(self.returncode, bool)
        ):
            raise CalibrationError("a certificate return code must be an integer or null")
        if not isinstance(self.verdict, ProbeVerdict):
            raise CalibrationError("a certificate requires a declared probe verdict")
        for name, value in (
            ("environment_sha256", self.environment_sha256),
            ("probe_sha256", self.probe_sha256),
        ):
            if (
                not isinstance(value, str) or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise CalibrationError(f"{name} must be a lowercase SHA-256 digest")

    def public_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "verdict": self.verdict.value,
            "returncode": self.returncode,
            "environment_id": self.environment_id,
            "environment_sha256": self.environment_sha256,
            "probe_sha256": self.probe_sha256,
        }


def certify(
    probe: CapabilityProbe, returncode: int | None, environment_id: str,
    environment_sha256: str, *, ran: bool = True,
) -> CapabilityCertificate:
    """Turn one probe execution into a certificate bound to an exact environment digest."""

    if not environment_id:
        raise CalibrationError("a certificate requires the identifier of the probed environment")
    return CapabilityCertificate(
        probe.capability_id, probe.interpret(returncode, ran=ran), returncode, environment_id,
        environment_sha256, probe.digest(),
    )


class Solvability(Enum):
    """The frozen label a task carries before any agent sees it."""

    FEASIBLE = "feasible"
    CAPABILITY_IMPOSSIBLE = "capability_impossible"
    UNLABELLED = "unlabelled"


@dataclass(frozen=True)
class TaskLabel:
    """A task, the capabilities it requires, and the certificates that decided its label."""

    task_id: str
    required_capabilities: tuple[str, ...]
    certificates: tuple[CapabilityCertificate, ...]

    def __post_init__(self) -> None:
        if not self.task_id:
            raise CalibrationError("a task label requires an identifier")
        if not self.required_capabilities:
            raise CalibrationError("a task label requires its declared capabilities")
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise CalibrationError("declared capabilities must be unique")
        certified = {certificate.capability_id for certificate in self.certificates}
        if len(certified) != len(self.certificates):
            raise CalibrationError("a task label cannot contain duplicate capability certificates")
        missing = set(self.required_capabilities) - certified
        if missing:
            raise CalibrationError(
                f"task {self.task_id!r} has uncertified capabilities: {sorted(missing)}"
            )
        extra = certified - set(self.required_capabilities)
        if extra:
            raise CalibrationError(
                f"task {self.task_id!r} has undeclared certificates: {sorted(extra)}"
            )
        environments = {
            (certificate.environment_id, certificate.environment_sha256)
            for certificate in self.certificates
        }
        if len(environments) != 1:
            raise CalibrationError(
                "all certificates in a task label must bind the same exact environment"
            )

    @property
    def solvability(self) -> Solvability:
        """A task is capability-impossible only when a required capability is certified absent."""

        relevant = [
            certificate for certificate in self.certificates
            if certificate.capability_id in self.required_capabilities
        ]
        if any(certificate.verdict is ProbeVerdict.ABSENT for certificate in relevant):
            return Solvability.CAPABILITY_IMPOSSIBLE
        if any(certificate.verdict is ProbeVerdict.INCONCLUSIVE for certificate in relevant):
            return Solvability.UNLABELLED
        return Solvability.FEASIBLE

    def digest(self) -> str:
        return _sha256(_canonical_json({
            "task_id": self.task_id,
            "required_capabilities": list(self.required_capabilities),
            "certificates": [c.public_dict() for c in self.certificates],
            "solvability": self.solvability.value,
        }))


class EpisodeOutcome(Enum):
    """How one agent episode ended, independent of any external reward.

    `REFUSED` means the agent itself concluded it should stop.  `HALTED` means the governance layer
    stopped it — the agent proposed something outside its authority and never recognised
    impossibility.  Only `REFUSED` counts as a refusal: crediting a governed halt would let the
    harness's own restraint inflate the agent's calibration score.
    """

    REFUSED = "refused"
    HALTED = "halted"
    SUBMITTED = "submitted"
    EXHAUSTED = "exhausted"
    FAULTED = "faulted"


@dataclass(frozen=True)
class EpisodeRecord:
    task_id: str
    arm_id: str
    outcome: EpisodeOutcome
    steps: int

    def __post_init__(self) -> None:
        if self.steps < 0:
            raise CalibrationError("episode steps cannot be negative")


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


@dataclass(frozen=True)
class CalibrationReport:
    """Refusal calibration for one arm over one labelled task set.

    `true_refusal_rate` is the share of capability-impossible tasks the arm refused.
    `false_refusal_rate` is the share of feasible tasks it refused — a refusal that fires where
    another arm succeeds is incapacity under a better name.
    `wasted_steps` counts steps spent on capability-impossible tasks that ended without a refusal:
    the budget an agent burns because it never concluded it should stop.
    """

    arm_id: str
    impossible_tasks: int
    feasible_tasks: int
    unlabelled_tasks: int
    true_refusals: int
    false_refusals: int
    wasted_steps: int

    @property
    def true_refusal_rate(self) -> float | None:
        return _rate(self.true_refusals, self.impossible_tasks)

    @property
    def false_refusal_rate(self) -> float | None:
        return _rate(self.false_refusals, self.feasible_tasks)

    @property
    def calibration_margin(self) -> float | None:
        true_rate = self.true_refusal_rate
        false_rate = self.false_refusal_rate
        if true_rate is None or false_rate is None:
            return None
        return true_rate - false_rate

    def public_dict(self) -> dict[str, object]:
        return {
            "schema": "mira-refusal-calibration-v1",
            "arm_id": self.arm_id,
            "impossible_tasks": self.impossible_tasks,
            "feasible_tasks": self.feasible_tasks,
            "unlabelled_tasks": self.unlabelled_tasks,
            "true_refusals": self.true_refusals,
            "false_refusals": self.false_refusals,
            "true_refusal_rate": self.true_refusal_rate,
            "false_refusal_rate": self.false_refusal_rate,
            "calibration_margin": self.calibration_margin,
            "wasted_steps": self.wasted_steps,
        }


def measure_calibration(
    episodes: Iterable[EpisodeRecord], labels: Mapping[str, TaskLabel], arm_id: str,
) -> CalibrationReport:
    """Score one arm's refusals against frozen solvability labels.

    Unlabelled tasks are counted and excluded from both rates rather than assumed feasible.
    """

    selected = [episode for episode in episodes if episode.arm_id == arm_id]
    if not selected:
        raise CalibrationError(f"no episodes recorded for arm {arm_id!r}")
    seen: set[str] = set()
    impossible = feasible = unlabelled = 0
    true_refusals = false_refusals = wasted = 0
    for episode in selected:
        if episode.task_id in seen:
            raise CalibrationError(
                f"arm {arm_id!r} has more than one episode for task {episode.task_id!r}"
            )
        seen.add(episode.task_id)
        label = labels.get(episode.task_id)
        if label is None:
            raise CalibrationError(f"episode references unlabelled task {episode.task_id!r}")
        solvability = label.solvability
        refused = episode.outcome is EpisodeOutcome.REFUSED
        if solvability is Solvability.CAPABILITY_IMPOSSIBLE:
            impossible += 1
            if refused:
                true_refusals += 1
            else:
                wasted += episode.steps
        elif solvability is Solvability.FEASIBLE:
            feasible += 1
            if refused:
                false_refusals += 1
        else:
            unlabelled += 1
    missing = set(labels) - seen
    if missing:
        raise CalibrationError(
            f"arm {arm_id!r} lacks episodes for labelled tasks: {sorted(missing)}"
        )
    return CalibrationReport(
        arm_id, impossible, feasible, unlabelled, true_refusals, false_refusals, wasted,
    )


def verdict(report: CalibrationReport, *, required_margin: float) -> dict[str, object]:
    """Apply a margin fixed before the run.

    `required_margin` has no default on purpose: a calibration threshold chosen after seeing a
    report is not a threshold.
    """

    if not 0.0 < required_margin <= 1.0:
        raise CalibrationError("the required calibration margin must lie in (0, 1]")
    margin = report.calibration_margin
    return {
        "schema": "mira-refusal-calibration-verdict-v1",
        "arm_id": report.arm_id,
        "required_margin": required_margin,
        "observed_margin": margin,
        "calibrated": None if margin is None else margin >= required_margin,
        "undecidable_reason": None if margin is not None else "an empty stratum leaves the margin undefined",
    }


def calibration_digest(reports: Sequence[CalibrationReport]) -> str:
    """A deterministic digest over an ordered set of reports."""

    return _sha256(_canonical_json([report.public_dict() for report in reports]))


__all__ = [
    "CalibrationError", "CalibrationReport", "CapabilityCertificate", "CapabilityProbe",
    "EpisodeOutcome", "EpisodeRecord", "ProbeVerdict", "Solvability", "TaskLabel",
    "calibration_digest", "certify", "measure_calibration", "verdict",
]
