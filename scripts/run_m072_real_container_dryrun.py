"""Run the whole calibration chain on the real bank containers with a scripted policy.

**Draft apparatus. This is a dry run: it spends no model tokens and produces no result.**

Every earlier self-test used stub environments.  This runs the real thing — probe the pinned
images, certify, start a live container per episode, drive all three arms through it, map the
episodes and score the calibration — with a *scripted* decision sequence standing in for the model
backend.  It therefore validates the instrument end to end on real infrastructure without
committing tokens or claiming anything about an agent.

Requires Docker and the bank's pinned images.

Run:

    python scripts/run_m072_real_container_dryrun.py
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metamorphosis.m072_ablation_arms import ABLATION_ARMS, run_arm_episode  # noqa: E402
from metamorphosis.m072_calibration_bridge import calibrate_run  # noqa: E402
from metamorphosis.m072_docker_environment import DockerTaskEnvironment  # noqa: E402
from metamorphosis.m072_task_bank import (  # noqa: E402
    TASKS, docker_probe_executor, validate_bank,
)
from mira_core.calibration import Solvability, calibration_digest  # noqa: E402
from mira_core.harbor import HarborEpisodeLimits  # noqa: E402
from mira_core.probing import label_task, probe_environment  # noqa: E402


REFUSE = {"decision": "refuse", "script": None, "reason": "a required capability is unavailable"}
FINISH = {"decision": "finish", "script": None, "reason": None}


def _probe(capability_id: str) -> dict:
    """A scripted 'act' that inspects the environment the way a careful agent would."""

    return {"decision": "act", "script": f"command -v {capability_id} || echo missing", "reason": None}


class ScriptedBackend:
    """Stands in for the model. A calibrated agent probes, then stops or proceeds."""

    backend_id = "scripted-dryrun-policy"

    def __init__(self, values) -> None:
        self.values = list(values)

    def complete(self, request):
        return self.values.pop(0) if self.values else FINISH


def _decisions_for(solvability: Solvability, capability_id: str) -> tuple[dict, ...]:
    inspect = _probe("python3" if capability_id == "python3" else "sh")
    if solvability is Solvability.CAPABILITY_IMPOSSIBLE:
        return (inspect, REFUSE)
    return (inspect, FINISH)


async def main() -> int:
    validate_bank()
    limits = HarborEpisodeLimits(max_steps=4, command_timeout_seconds=30)
    labels = {}
    run: list[tuple[str, dict]] = []

    for task in TASKS:
        certificates = probe_environment(
            task.required_capabilities, docker_probe_executor(task.environment),
            task.environment.environment_id,
        )
        label = label_task(task.task_id, task.required_capabilities, certificates)
        labels[task.task_id] = label
        capability_id = task.required_capabilities[0].capability_id
        decisions = _decisions_for(label.solvability, capability_id)

        for arm in ABLATION_ARMS:
            with DockerTaskEnvironment(task.environment) as environment:
                manifest, _, _ = await run_arm_episode(
                    task.instruction, environment, ScriptedBackend(decisions), arm, limits=limits,
                )
            run.append((task.task_id, manifest))

    reports = calibrate_run(run, labels)
    payload = {
        "schema": "m072-real-container-dryrun-v1",
        "frozen": False,
        "scientific_result": False,
        "model_tokens_spent": 0,
        "episodes": len(run),
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
