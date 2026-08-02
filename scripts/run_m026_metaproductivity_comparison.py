"""Run the paired M026 decidable metaproductivity development comparison."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import platform
import subprocess

from metamorphosis.m026_metaproductivity import (
    DEFAULT_BUDGET,
    DEVELOPMENT_MIN_SEEDS,
    PROTOCOL_VERSION,
    STRATEGIES,
    run_trial,
    summarize_runs,
    verify_structural_controls,
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
    rig, strategy, seed, budget = task
    return run_trial(rig, strategy, seed, budget=budget)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=DEVELOPMENT_MIN_SEEDS)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument(
        "--workers",
        type=int,
        default=min(4, os.cpu_count() or 1),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "M026_metaproductivity_development.json",
    )
    arguments = parser.parse_args()
    if arguments.seeds < 1:
        parser.error("--seeds must be positive")
    if arguments.seed_start < 0:
        parser.error("--seed-start must be non-negative")
    if arguments.budget < 1:
        parser.error("--budget must be positive")
    if arguments.workers < 1:
        parser.error("--workers must be positive")

    controls = verify_structural_controls(arguments.seed_start)
    if not all(controls.values()):
        raise SystemExit(f"structural control failed: {controls}")

    tasks = [
        (rig, strategy, seed, arguments.budget)
        for rig in ("mismatch", "aligned")
        for strategy in STRATEGIES
        for seed in range(arguments.seed_start, arguments.seed_start + arguments.seeds)
    ]
    with ProcessPoolExecutor(max_workers=arguments.workers) as pool:
        runs = list(pool.map(_run_task, tasks))
    summary = summarize_runs(runs)
    payload = {
        "provenance": {
            "implementation_commit": _git_commit(),
            "protocol_version": PROTOCOL_VERSION,
            "python_version": platform.python_version(),
        },
        "summary": summary,
        "structural_controls": controls,
        "runs": runs,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
