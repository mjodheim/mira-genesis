"""Exercise the separate M075 development bank with a zero-token epistemic policy."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_ablation_arms import ABLATION_ARMS, run_arm_episode  # noqa: E402
from metamorphosis.m074_calibration_bridge import calibrate_run  # noqa: E402
from metamorphosis.m074_docker_environment import DockerTaskEnvironment  # noqa: E402
from metamorphosis.m075_development_bank import TASKS, BankTask, validate_development_bank  # noqa: E402
from metamorphosis.m075_epistemic_context import EpistemicContextBackend  # noqa: E402
from mira_core.calibration import Solvability, TaskLabel, calibration_digest  # noqa: E402
from mira_core.harbor import HarborEpisodeLimits  # noqa: E402
from mira_core.model import ModelRequest  # noqa: E402
from mira_core.probing import label_task, probe_environment  # noqa: E402


class ScriptedEpistemicDevelopmentBackend:
    """Attempt once, finish on success and refuse on visible failure, without a hidden label."""

    backend_id = "m075-zero-token-epistemic-development-policy-v1"

    def __init__(self, task: BankTask) -> None:
        self.task = task
        self.calls = 0

    def complete(self, request: ModelRequest) -> dict[str, object]:
        payload = json.loads(request.input_json)
        if not isinstance(payload, dict) or not isinstance(payload.get("epistemic_state"), dict):
            raise ValueError("development policy requires the audited epistemic projection")
        rendered = request.input_json
        for prohibited in (
            "expected_solvability", "probed_solvability", "capability_certificates",
            "evaluator_script", "external_success",
        ):
            if prohibited in rendered:
                raise ValueError(f"hidden field crossed the development boundary: {prohibited}")
        state = payload["epistemic_state"]
        self.calls += 1
        if state["observed_command_count"] == 0:
            return {"decision": "act", "script": self.task.solve_script, "reason": None}
        if state["last_returncode"] == 0:
            return {"decision": "finish", "script": None, "reason": None}
        return {
            "decision": "refuse", "script": None,
            "reason": "the attempted required operation remained unavailable in this environment",
        }


async def main(*, output: Path | None = None) -> int:
    validate_development_bank()
    limits = HarborEpisodeLimits(max_steps=4, command_timeout_seconds=30)
    labels: dict[str, TaskLabel] = {}
    manifests = []
    episodes: list[dict[str, object]] = []
    defects: list[str] = []

    for task in TASKS:
        reference_label: TaskLabel | None = None
        for arm in ABLATION_ARMS:
            with DockerTaskEnvironment(task) as environment:
                boundary = environment.inspect_security_boundary()
                if boundary.get("matches_declaration") is not True:
                    defects.append(f"{task.task_id}/{arm.arm_id}: boundary mismatch")
                certificates = probe_environment(
                    task.required_capabilities, environment.execute_probe,
                    task.environment.environment_id, environment.environment_sha256,
                )
                observed_label = label_task(
                    task.task_id, task.required_capabilities, certificates,
                )
                if reference_label is None:
                    reference_label = observed_label
                elif reference_label.digest() != observed_label.digest():
                    defects.append(f"{task.task_id}: label drifted across arm containers")
                delegate = ScriptedEpistemicDevelopmentBackend(task)
                backend = EpistemicContextBackend(delegate, max_steps=limits.max_steps)
                manifest, memory, _ = await run_arm_episode(
                    task.instruction, environment, backend, arm, limits=limits,
                    policy_id="m075-epistemic-development-policy-v1",
                    goal_id="m075-public-development-task",
                    body_id="m075-public-development-container-v1",
                )
                evaluation = environment.evaluate(timeout_seconds=30)
                external_success = evaluation.return_code == 0

            manifests.append((task.task_id, manifest))
            episodes.append({
                "task_id": task.task_id,
                "task_sha256": task.task_digest(),
                "environment_sha256": task.environment_digest(),
                "arm_id": arm.arm_id,
                "security_boundary": boundary,
                "capability_certificates": [c.public_dict() for c in certificates],
                "probed_solvability": observed_label.solvability.value,
                "label_sha256": observed_label.digest(),
                "status": manifest["status"],
                "steps": manifest["steps"],
                "memory_digest": memory.digest,
                "epistemic_states": backend.states,
                "external_success": external_success,
                "evaluator_returncode": evaluation.return_code,
                "scripted_backend_calls": delegate.calls,
            })

        assert reference_label is not None
        labels[task.task_id] = reference_label
        if reference_label.solvability is not task.expected_solvability:
            defects.append(
                f"{task.task_id}: expected {task.expected_solvability.value}, "
                f"observed {reference_label.solvability.value}"
            )

    for episode in episodes:
        label = labels[str(episode["task_id"])]
        feasible = label.solvability is Solvability.FEASIBLE
        if episode["external_success"] is not feasible:
            defects.append(
                f"{episode['task_id']}/{episode['arm_id']}: external state contradicted label"
            )
        expected_status = (
            "submitted_for_external_evaluation" if feasible
            else "policy_refused" if episode["arm_id"] == "A-terminal-refusal"
            else "step_budget_exhausted"
        )
        if episode["status"] != expected_status:
            defects.append(
                f"{episode['task_id']}/{episode['arm_id']}: status {episode['status']} "
                f"did not match {expected_status}"
            )

    reports = calibrate_run(manifests, labels)
    payload = {
        "schema": "m075-real-container-development-v1",
        "status": "development_complete" if not defects else "development_defective",
        "scientific_result": False,
        "public_contaminated_development_bank": True,
        "model_tokens_spent": 0,
        "fresh_container_per_episode": True,
        "same_container_probed_acted_and_evaluated": True,
        "task_count": len(TASKS),
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
        "development_defects": defects,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output is not None:
        if output.exists():
            raise FileExistsError(f"development output already exists: {output}")
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    return 1 if defects else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(output=args.output)))
