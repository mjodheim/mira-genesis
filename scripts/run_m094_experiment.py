"""M094 experiment runner — autonomous diagnosis and repair pipeline.

This orchestrator connects the structural diagnosis (m094_diagnosis.py)
with the generic synthesis mechanism (m094_synthesis.py) and the
existing M093 transformation infrastructure (sandbox, comparison,
adoption, rollback).

Unlike M093, the target component and required capability are
determined by measurement, not by authored constants. The repair
is assembled from composable AST-derived operations, not from
a hand-written template.

Usage:
    python -m scripts.run_m094_experiment
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from metamorphosis.m094_diagnosis import diagnose
from metamorphosis.m094_synthesis import suggest_operations

REPO_ROOT = Path(__file__).resolve().parent.parent

ELIGIBLE_COMPONENTS = (
    "mira_core/safety.py",
    "mira_core/contracts.py",
    "mira_core/memory.py",
)


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def main() -> int:
    """Run the full M094 pipeline."""
    report = {}
    start = time.time()

    # 1. Diagnosis
    step("1. Structural diagnosis")
    result = diagnose(REPO_ROOT, ELIGIBLE_COMPONENTS)
    report["diagnosis"] = {
        "selected": result.selected,
        "unmet_count": len(result.unmet),
        "considered_count": len(result.considered),
    }
    print(f"  Selected: {result.selected}")
    if result.selected:
        ins = result.unmet[0]
        print(f"  Class: {ins.target}")
        print(f"  Capability: {ins.capability}")
        print(f"  Demand: {ins.demand}, Supplied: {ins.supplied}")
        print(f"  Detail: {ins.detail}")
        report["diagnosis"]["top_insufficiency"] = {
            "component": ins.component_path,
            "class": ins.target,
            "capability": ins.capability,
            "demand": ins.demand,
            "supplied": ins.supplied,
        }

    # 2. Synthesis
    if result.selected and result.unmet:
        ins = result.unmet[0]
        step("2. Candidate synthesis")
        ops = suggest_operations(
            REPO_ROOT, ins.component_path, ins.target,
            ins.capability, ins.target, ins.detail,
        )
        report["synthesis"] = {
            "operation_count": len(ops),
            "operations": [op.description for op in ops],
        }
        print(f"  Generated {len(ops)} candidate operation(s)")
        for op in ops:
            print(f"    - {op.description}")

        # 3. Apply the winning operation
        if ops:
            step("3. Apply candidate")
            target_path = REPO_ROOT / ins.component_path
            original = target_path.read_text(encoding="utf-8")
            modified = ops[0].apply(original)
            print(f"  Source: {len(original)} bytes -> {len(modified)} bytes")
            report["application"] = {
                "file": ins.component_path,
                "original_bytes": len(original),
                "modified_bytes": len(modified),
            }
    else:
        print("  Nothing to repair — no unmet insufficiency found")
        report["synthesis"] = {"operation_count": 0}

    elapsed = time.time() - start
    report["elapsed_seconds"] = round(elapsed, 1)
    report["schema"] = "m094-runner-report-v1"

    print(f"\n{'='*50}")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())