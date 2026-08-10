"""Probe the seed task bank in real containers and emit certified solvability labels.

**Draft apparatus. This produces labels, not a scientific result.**

Requires a working Docker engine and the bank's digest-pinned images. Each task is probed in the
exact environment its agent phase would receive. A probed label that contradicts the bank's own
expectation is reported as a bank defect and fails the run: a bank that disagrees with its
containers cannot ground any rate.

Run:

    python scripts/run_m074_probe_bank.py [--output labels.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metamorphosis.m074_docker_environment import DockerTaskEnvironment  # noqa: E402
from metamorphosis.m074_task_bank import TASKS, validate_bank  # noqa: E402
from mira_core.calibration import Solvability  # noqa: E402
from mira_core.probing import label_task, probe_environment  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    validate_bank()
    records: list[dict[str, object]] = []
    defects: list[str] = []

    for task in TASKS:
        with DockerTaskEnvironment(task) as environment:
            certificates = probe_environment(
                task.required_capabilities, environment.execute_probe,
                task.environment.environment_id, environment.environment_sha256,
            )
        label = label_task(task.task_id, task.required_capabilities, certificates)
        observed = label.solvability
        if observed is not task.expected_solvability:
            defects.append(
                f"{task.task_id}: expected {task.expected_solvability.value}, "
                f"probed {observed.value}"
            )
        records.append({
            "task_id": task.task_id,
            "pair_id": task.pair_id,
            "task_sha256": task.task_digest(),
            "environment_id": task.environment.environment_id,
            "environment_sha256": task.environment_digest(),
            "image": task.environment.image,
            "workspace_writable": task.environment.workspace_writable,
            "network": task.environment.network,
            "expected_solvability": task.expected_solvability.value,
            "probed_solvability": observed.value,
            "certificates": [certificate.public_dict() for certificate in certificates],
            "label_digest": label.digest(),
        })

    payload = {
        "schema": "m074-probed-task-labels-v1",
        "frozen": False,
        "scientific_result": False,
        "task_count": len(records),
        "impossible_count": sum(
            1 for record in records
            if record["probed_solvability"] == Solvability.CAPABILITY_IMPOSSIBLE.value
        ),
        "feasible_count": sum(
            1 for record in records
            if record["probed_solvability"] == Solvability.FEASIBLE.value
        ),
        "bank_defects": defects,
        "labels": records,
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if defects:
        print(f"\nBANK DEFECT: {len(defects)} task(s) contradict their probe", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
