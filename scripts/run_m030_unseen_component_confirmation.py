"""Run M030's untouched-seed component-uniform development confirmation."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import platform
import subprocess

from metamorphosis.m028_adaptive_evaluation import DEFAULT_POLICY_BUDGET
from metamorphosis.m030_unseen_confirmation import (
    CONFIRMATION_SEED_COUNT,
    CONFIRMATION_SEED_START,
    PROTOCOL_VERSION,
    STRATEGIES,
    run_trial,
    summarize_runs,
)


ROOT = Path(__file__).resolve().parents[1]


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _run_task(task: tuple[str, str, int, int]) -> dict[str, object]:
    rig, strategy, seed, policy_budget = task
    return run_trial(rig, strategy, seed, policy_budget=policy_budget)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=CONFIRMATION_SEED_COUNT)
    parser.add_argument("--seed-start", type=int, default=CONFIRMATION_SEED_START)
    parser.add_argument("--policy-budget", type=int, default=DEFAULT_POLICY_BUDGET)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "M030_unseen_component_development.json",
    )
    arguments = parser.parse_args()
    if arguments.seeds < 1:
        parser.error("--seeds must be positive")
    if arguments.seed_start < 0:
        parser.error("--seed-start must be non-negative")
    if arguments.policy_budget < 1:
        parser.error("--policy-budget must be positive")
    if arguments.workers < 1:
        parser.error("--workers must be positive")

    tasks = [
        (rig, strategy, seed, arguments.policy_budget)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
        for seed in range(arguments.seed_start, arguments.seed_start + arguments.seeds)
    ]
    with ProcessPoolExecutor(max_workers=arguments.workers) as pool:
        runs = list(pool.map(_run_task, tasks))
    payload = {
        "provenance": {
            "implementation_commit": _git_commit(),
            "protocol_version": PROTOCOL_VERSION,
            "python_version": platform.python_version(),
        },
        "summary": summarize_runs(runs),
        "runs": runs,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
