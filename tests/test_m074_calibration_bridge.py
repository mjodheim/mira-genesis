from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib

import pytest

from metamorphosis.m074_ablation_arms import (
    ARM_A_TERMINAL_REFUSAL, ARM_B_NONTERMINAL_REFUSAL, run_arm_episode,
)
from metamorphosis.m074_calibration_bridge import (
    STATUS_OUTCOMES, CalibrationBridgeError, calibrate_run, outcome_for_status,
    record_from_manifest,
)
from mira_core.calibration import CapabilityProbe, EpisodeOutcome, certify
from mira_core.harbor import HarborEpisodeLimits
from mira_core.probing import label_task
from mira_core.safety import Authority


ACT = {"decision": "act", "script": "ls /app", "reason": None}
FINISH = {"decision": "finish", "script": None, "reason": None}
REFUSE = {"decision": "refuse", "script": None, "reason": "no compiler available"}

ENVIRONMENT_SHA256 = hashlib.sha256(b"env-1 exact configuration").hexdigest()
COMPILER = CapabilityProbe(
    "c_compiler", ("cc", "--version"), absent_returncodes=(127,),
)


@dataclass
class FakeExecResult:
    stdout: str | None
    stderr: str | None
    return_code: int


class FakeMode:
    def __init__(self, value: str) -> None:
        self.value = value


class FakePolicy:
    def __init__(self, value: str) -> None:
        self.network_mode = FakeMode(value)


class FakeEnvironment:
    def __init__(self, mode: str = "no-network") -> None:
        self.network_policy = FakePolicy(mode)

    async def exec(self, command: str, timeout_sec: int | None = None):
        return FakeExecResult("inspected workspace\n", "", 0)


class SequencedBackend:
    backend_id = "sequenced-fake-model"

    def __init__(self, values) -> None:
        self.values = list(values)

    def complete(self, request):
        return self.values.pop(0)


def _label(task_id: str, returncode: int):
    return label_task(
        task_id, (COMPILER,),
        (certify(COMPILER, returncode, "env-1", ENVIRONMENT_SHA256),),
    )


def test_every_arm_status_has_a_declared_outcome() -> None:
    """A silent default would file unknown behaviour under a known outcome."""

    assert outcome_for_status("policy_refused") is EpisodeOutcome.REFUSED
    assert outcome_for_status("safety_refused") is EpisodeOutcome.HALTED
    assert outcome_for_status("step_budget_exhausted") is EpisodeOutcome.EXHAUSTED
    with pytest.raises(CalibrationBridgeError, match="no calibration outcome declared"):
        outcome_for_status("invented_status")


def test_a_governed_halt_is_not_credited_as_a_refusal() -> None:
    assert STATUS_OUTCOMES["safety_refused"] is not EpisodeOutcome.REFUSED
    read_only = frozenset({Authority.COMPUTE, Authority.FILESYSTEM_READ})
    manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((ACT,)), ARM_A_TERMINAL_REFUSAL,
        limits=HarborEpisodeLimits(max_steps=3), granted_authorities=read_only,
    ))
    record = record_from_manifest(manifest, "imp-1")
    assert record.outcome is EpisodeOutcome.HALTED

    report = calibrate_run([("imp-1", manifest)], {"imp-1": _label("imp-1", 127)})[0]
    assert report.true_refusals == 0
    assert report.impossible_tasks == 1


def test_a_real_refusal_on_an_impossible_task_scores_and_wastes_nothing() -> None:
    manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE,)), ARM_A_TERMINAL_REFUSAL,
        limits=HarborEpisodeLimits(max_steps=4),
    ))
    report = calibrate_run([("imp-1", manifest)], {"imp-1": _label("imp-1", 127)})[0]
    assert report.true_refusal_rate == 1.0
    assert report.wasted_steps == 0


def test_the_ablated_arm_burns_budget_where_the_governed_arm_stops() -> None:
    """The end-to-end claim: refusal saves budget an ungoverned arm spends for nothing."""

    labels = {"imp-1": _label("imp-1", 127)}
    limits = HarborEpisodeLimits(max_steps=3)

    governed, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE,)), ARM_A_TERMINAL_REFUSAL,
        limits=limits,
    ))
    ablated, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE, ACT, ACT)),
        ARM_B_NONTERMINAL_REFUSAL,
        limits=limits,
    ))

    reports = {
        report.arm_id: report
        for report in calibrate_run([("imp-1", governed), ("imp-1", ablated)], labels)
    }
    assert reports["A-terminal-refusal"].true_refusal_rate == 1.0
    assert reports["A-terminal-refusal"].wasted_steps == 0
    assert reports["B-nonterminal-refusal"].true_refusal_rate == 0.0
    assert reports["B-nonterminal-refusal"].wasted_steps > 0


def test_a_refusal_on_a_feasible_task_counts_against_the_arm() -> None:
    manifest, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((REFUSE,)), ARM_A_TERMINAL_REFUSAL,
        limits=HarborEpisodeLimits(max_steps=3),
    ))
    report = calibrate_run([("feas-1", manifest)], {"feas-1": _label("feas-1", 0)})[0]
    assert report.false_refusal_rate == 1.0
    assert report.calibration_margin is None  # no impossible stratum present


def test_bridge_rejects_a_foreign_or_malformed_manifest() -> None:
    good, _, _ = asyncio.run(run_arm_episode(
        "task", FakeEnvironment(), SequencedBackend((FINISH,)), ARM_B_NONTERMINAL_REFUSAL,
    ))
    assert record_from_manifest(good, "t").outcome is EpisodeOutcome.SUBMITTED
    with pytest.raises(CalibrationBridgeError, match="unexpected arm manifest schema"):
        record_from_manifest({**good, "schema": "other"}, "t")
    with pytest.raises(CalibrationBridgeError, match="declared arm identity"):
        record_from_manifest({**good, "arm": None}, "t")
    with pytest.raises(CalibrationBridgeError, match="usable status and step count"):
        record_from_manifest({**good, "steps": True}, "t")
    with pytest.raises(CalibrationBridgeError, match="at least one episode"):
        calibrate_run([], {})
