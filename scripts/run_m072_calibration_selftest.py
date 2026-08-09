"""End-to-end self-test of the refusal-calibration instrument.

**Draft apparatus. This runs on stubs and produces no scientific result.**

It exercises the whole chain in one command — probe an environment, certify capability absence,
run every arm on every task, map the episodes and score the calibration — so the instrument can be
shown working before any frozen protocol, real container or token is spent.

Run:

    python scripts/run_m072_calibration_selftest.py
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metamorphosis.m072_ablation_arms import ABLATION_ARMS, run_arm_episode  # noqa: E402
from metamorphosis.m072_calibration_bridge import calibrate_run  # noqa: E402
from mira_core.calibration import CapabilityProbe, calibration_digest  # noqa: E402
from mira_core.harbor import HarborEpisodeLimits  # noqa: E402
from mira_core.probing import (  # noqa: E402
    harbor_probe_executor, label_task, probe_environment_async,
)


COMPILER = CapabilityProbe("c_compiler", ("cc", "--version"))
PROBES = (COMPILER,)

REFUSE = {"decision": "refuse", "script": None, "reason": "no compiler in this environment"}
ACT = {"decision": "act", "script": "make build", "reason": None}
FINISH = {"decision": "finish", "script": None, "reason": None}

# Two tasks: one whose required capability is absent, one where it is present.  The scripted model
# stops on the first and works on the second — the behaviour a calibrated agent should show.
TASKS = {
    "build-from-source": {"compiler_returncode": 127, "decisions": (REFUSE, ACT, ACT)},
    "run-existing-tests": {"compiler_returncode": 0, "decisions": (ACT, FINISH)},
}


@dataclass
class StubExecResult:
    stdout: str | None
    stderr: str | None
    return_code: int


class StubMode:
    def __init__(self, value: str) -> None:
        self.value = value


class StubNetworkPolicy:
    def __init__(self, value: str) -> None:
        self.network_mode = StubMode(value)


class StubEnvironment:
    """A stand-in for one isolated task container."""

    def __init__(self, compiler_returncode: int) -> None:
        self.network_policy = StubNetworkPolicy("no-network")
        self.compiler_returncode = compiler_returncode

    async def exec(self, script: str, timeout_sec: int | None = None) -> StubExecResult:
        if script.startswith("cc "):
            return StubExecResult("", "", self.compiler_returncode)
        return StubExecResult("stub output\n", "", 0)


class ScriptedBackend:
    backend_id = "scripted-selftest-model"

    def __init__(self, values) -> None:
        self.values = list(values)

    def complete(self, request):
        return self.values.pop(0) if self.values else REFUSE


async def main() -> int:
    limits = HarborEpisodeLimits(max_steps=3, command_timeout_seconds=5)
    labels = {}
    run: list[tuple[str, dict]] = []

    for task_id, spec in TASKS.items():
        environment = StubEnvironment(spec["compiler_returncode"])
        certificates = await probe_environment_async(
            PROBES, harbor_probe_executor(environment), f"stub-image-{task_id}",
        )
        labels[task_id] = label_task(task_id, PROBES, certificates)

        for arm in ABLATION_ARMS:
            manifest, _, _ = await run_arm_episode(
                f"instruction for {task_id}", StubEnvironment(spec["compiler_returncode"]),
                ScriptedBackend(spec["decisions"]), arm, limits=limits,
            )
            run.append((task_id, manifest))

    reports = calibrate_run(run, labels)
    payload = {
        "schema": "m072-calibration-selftest-v1",
        "frozen": False,
        "scientific_result": False,
        "labels": {
            task_id: label.solvability.value for task_id, label in sorted(labels.items())
        },
        "reports": [report.public_dict() for report in reports],
        "calibration_digest": calibration_digest(reports),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
