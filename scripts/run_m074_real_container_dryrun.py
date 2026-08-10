"""Exercise M074 end to end in real containers with a label-blind scripted policy.

**Draft apparatus. This spends no model tokens and produces no scientific result.**

For every arm and task, this command starts a fresh persistent container, materializes the exact
fixture, probes it as the agent user, runs the policy in that same container and evaluates final
state externally before removal.  The scripted policy is fixed by the task contract and branches
only on live command return codes; it never receives expected or observed solvability labels.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import shlex
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metamorphosis.m074_ablation_arms import ABLATION_ARMS, run_arm_episode  # noqa: E402
from metamorphosis.m074_calibration_bridge import calibrate_run  # noqa: E402
from metamorphosis.m074_docker_environment import DockerTaskEnvironment  # noqa: E402
from metamorphosis.m074_task_bank import TASKS, BankTask, validate_bank  # noqa: E402
from mira_core.calibration import Solvability, TaskLabel, calibration_digest  # noqa: E402
from mira_core.harbor import HarborEpisodeLimits  # noqa: E402
from mira_core.model import ModelRequest  # noqa: E402
from mira_core.probing import label_task, probe_environment  # noqa: E402


def _act(script: str) -> dict[str, object]:
    return {"decision": "act", "script": script, "reason": None}


FINISH = {"decision": "finish", "script": None, "reason": None}


def _refuse(reason: str) -> dict[str, object]:
    return {"decision": "refuse", "script": None, "reason": reason}


class ScriptedCalibrationBackend:
    """Probe, solve on a present capability, otherwise refuse from live evidence only."""

    backend_id = "m074-label-blind-scripted-development-policy-v1"

    def __init__(self, task: BankTask) -> None:
        if len(task.required_capabilities) != 1:
            raise ValueError("the development backend currently requires one probe per task")
        self.task = task
        self.probe = task.required_capabilities[0]
        self.phase = "probe"

    @staticmethod
    def _returncode(request: ModelRequest) -> int | None:
        payload = json.loads(request.input_json)
        state = payload["observation"]["state"]
        value = state.get("returncode")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    def complete(self, request: ModelRequest) -> dict[str, object]:
        if self.phase == "probe":
            self.phase = "interpret_probe"
            return _act(shlex.join(self.probe.argv))
        if self.phase == "interpret_probe":
            returncode = self._returncode(request)
            if returncode in self.probe.present_returncodes:
                self.phase = "interpret_solution"
                return _act(self.task.solve_script)
            self.phase = "refused"
            return _refuse(
                f"required capability {self.probe.capability_id} was not observed as present"
            )
        if self.phase == "interpret_solution":
            self.phase = "finished"
            if self._returncode(request) == 0:
                return dict(FINISH)
            return _refuse("the declared solution command failed in this environment")
        return _refuse("the required capability remains unavailable")


async def main(*, output: Path | None = None) -> int:
    validate_bank()
    limits = HarborEpisodeLimits(max_steps=4, command_timeout_seconds=30)
    labels: dict[str, TaskLabel] = {}
    run: list[tuple[str, dict]] = []
    episodes: list[dict[str, object]] = []
    defects: list[str] = []

    for task in TASKS:
        reference_label: TaskLabel | None = None
        for arm in ABLATION_ARMS:
            with DockerTaskEnvironment(task) as environment:
                certificates = probe_environment(
                    task.required_capabilities, environment.execute_probe,
                    task.environment.environment_id, environment.environment_sha256,
                )
                observed_label = label_task(
                    task.task_id, task.required_capabilities, certificates,
                )
                if reference_label is None:
                    reference_label = observed_label
                elif observed_label.digest() != reference_label.digest():
                    defects.append(f"{task.task_id}: labels differ across fresh arm containers")

                manifest, _, _ = await run_arm_episode(
                    task.instruction, environment, ScriptedCalibrationBackend(task), arm,
                    limits=limits,
                )
                evaluation = environment.evaluate()
                external_success = evaluation.return_code == 0

            run.append((task.task_id, manifest))
            episodes.append({
                "task_id": task.task_id,
                "task_sha256": task.task_digest(),
                "environment_sha256": task.environment_digest(),
                "arm_id": arm.arm_id,
                "status": manifest["status"],
                "steps": manifest["steps"],
                "external_success": external_success,
                "evaluator_returncode": evaluation.return_code,
            })

        assert reference_label is not None
        labels[task.task_id] = reference_label
        if reference_label.solvability is not task.expected_solvability:
            defects.append(
                f"{task.task_id}: expected {task.expected_solvability.value}, "
                f"probed {reference_label.solvability.value}"
            )

    for episode in episodes:
        label = labels[str(episode["task_id"])]
        expected_success = label.solvability is Solvability.FEASIBLE
        if bool(episode["external_success"]) is not expected_success:
            defects.append(
                f"{episode['task_id']}/{episode['arm_id']}: external success "
                f"{episode['external_success']} contradicts {label.solvability.value}"
            )

    reports = calibrate_run(run, labels)
    payload = {
        "schema": "m074-real-container-dryrun-v2",
        "frozen": False,
        "scientific_result": False,
        "model_tokens_spent": 0,
        "label_blind_scripted_policy": True,
        "fresh_container_per_episode": True,
        "same_container_probed_and_acted_in": True,
        "episodes": episodes,
        "labels": {
            task_id: {
                "solvability": label.solvability.value,
                "label_sha256": label.digest(),
            }
            for task_id, label in sorted(labels.items())
        },
        "reports": [report.public_dict() for report in reports],
        "calibration_digest": calibration_digest(reports),
        "apparatus_defects": defects,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output is not None:
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if defects else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(main(output=arguments.output)))
