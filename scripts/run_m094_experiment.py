"""M094 development probe — structural diagnosis, then repair synthesis.

**This is not the M094 experiment.** It exercises the two mechanisms that exist —
`m094_diagnosis.diagnose` and `m094_synthesis.suggest_operations` — and stops. It
applies the winning operation to an in-memory copy of the component's source and
reports the size change.

What it deliberately does **not** do, and what the protocol at
`experiments/M094/PROTOCOL.json` still requires before a qualification run:

* it does not write the modified source anywhere;
* it does not execute the candidate in a sandbox;
* it does not compare the candidate against the original;
* it does not submit the candidate to an independent validator;
* it does not adopt, persist, restart or roll back;
* it does not run any control arm;
* it does not produce `RESULT.json`, `QUALIFICATION.json` or `REGISTER_CLAIM.json`.

An earlier revision of this docstring claimed this script "connects the structural
diagnosis with the generic synthesis mechanism and the existing M093 transformation
infrastructure (sandbox, comparison, adoption, rollback)". It imports none of that
infrastructure and never did. The claim is withdrawn here rather than repaired by
quietly wiring something in: the pipeline is a blocker recorded in
`docs/REPOSITORY_AUDIT_2026_08_18.md` §G, and building it is the next scientific step,
not a documentation fix.

The eligible component set is read from the frozen protocol rather than copied, so this
probe cannot drift away from what M094 committed to.

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
PROTOCOL_PATH = REPO_ROOT / "experiments" / "M094" / "PROTOCOL.json"


def eligible_components() -> tuple[str, ...]:
    """The eligible set, as the frozen protocol enumerates it.

    Read rather than copied. Three other places in the repository hold this list; the
    checker's copy is compared against the protocol by `check_p1`, and this one used to
    be the unguarded fourth.
    """

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    return tuple(protocol["eligible_components"]["enumerated"])


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def main() -> int:
    """Diagnose, synthesise, and apply the winner to an in-memory copy."""
    report: dict = {}
    start = time.time()

    components = eligible_components()

    # 1. Diagnosis
    step("1. Structural diagnosis")
    result = diagnose(REPO_ROOT, components)
    report["diagnosis"] = {
        "eligible_components": list(components),
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

        # 3. Apply the winning operation — in memory only. Nothing is written.
        if ops:
            step("3. Apply candidate (in memory; nothing is written)")
            target_path = REPO_ROOT / ins.component_path
            original = target_path.read_text(encoding="utf-8")
            modified = ops[0].apply(original)
            print(f"  Source: {len(original)} bytes -> {len(modified)} bytes")
            report["application"] = {
                "file": ins.component_path,
                "original_bytes": len(original),
                "modified_bytes": len(modified),
                "written_to_disk": False,
            }
    else:
        print("  Nothing to repair — no unmet insufficiency found")
        report["synthesis"] = {"operation_count": 0}

    elapsed = time.time() - start
    report["elapsed_seconds"] = round(elapsed, 1)
    report["schema"] = "m094-development-probe-report-v1"
    report["is_a_qualification_run"] = False

    print(f"\n{'='*50}")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
