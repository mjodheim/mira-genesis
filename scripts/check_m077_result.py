"""Independently recompute the preserved M077 result, including its negative verdict.

The checker rebuilds every fault schedule from the committed salt, re-derives all four arms,
re-verifies the bound schedule and the preserved digest, and confirms that the recorded verdict
still matches what the frozen thresholds produce. A negative result must stay negative: silently
turning it positive is treated as drift, not as progress.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m077_long_horizon_recovery import (  # noqa: E402
    ARMS,
    FAULT_KINDS,
    HORIZONS,
    build_schedule,
    canonical_json,
    evaluate,
    run_arm,
)

BASE = ROOT / "experiments/M077"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
SCHEDULE_PATH = BASE / "SCHEDULE_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    bound = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    _fail(
        failures,
        hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
        == preserved["protocol_commitment"],
        "protocol bytes no longer match the recorded commitment",
    )

    for horizon in HORIZONS:
        replay = {str(k): v for k, v in build_schedule(salt, horizon).items()}
        _fail(
            failures,
            replay == bound["schedules"][str(horizon)],
            f"horizon {horizon} schedule does not reproduce",
        )
        _fail(
            failures,
            set(replay.values()) == set(FAULT_KINDS),
            f"horizon {horizon} lost a fault kind",
        )

    recomputed_schedule = dict(bound)
    recomputed_schedule.pop("schedule_commitment", None)
    _fail(
        failures,
        hashlib.sha256(canonical_json(recomputed_schedule)).hexdigest()
        == bound["schedule_commitment"],
        "schedule commitment does not recompute",
    )
    _fail(
        failures,
        bound["schedule_commitment"] == preserved["schedule_commitment"],
        "the preserved result is bound to a different schedule",
    )

    arms = {arm: run_arm(salt, arm) for arm in ARMS}
    for arm in ARMS:
        _fail(
            failures,
            preserved["arms"][arm]["horizons"] == arms[arm]["horizons"],
            f"{arm} does not reproduce",
        )

    # The two positive sub-results.
    for horizon in HORIZONS:
        key = str(horizon)
        full = arms["full"]["horizons"][key]
        _fail(
            failures,
            full["unrecovered_faults"] == 0 and full["undetected_faults"] == 0
            and full["residual_violations"] == 0 and full["interventions"] == 0,
            f"full arm no longer clean at horizon {horizon}",
        )
        _fail(
            failures,
            arms["no_checkpoint"]["horizons"][key]["restoration_rate_on_detected"] == 0.0
            and arms["no_checkpoint"]["horizons"][key]["detections"] == full["detections"],
            f"no_checkpoint no longer isolates restoration at horizon {horizon}",
        )

    verdict = evaluate(arms)
    _fail(
        failures,
        (preserved["verdict"] == "positive") == verdict.positive,
        "the recomputed verdict disagrees with the preserved verdict",
    )
    _fail(
        failures,
        verdict.positive is False,
        "the preserved negative silently became positive; that requires a new experiment number",
    )
    _fail(
        failures,
        list(verdict.reasons) == preserved["failed_conditions"],
        "the recorded failed conditions no longer match",
    )
    _fail(
        failures,
        len(preserved["instrument_corrections_before_materialization"]) == 2,
        "the recorded instrument corrections were removed",
    )

    recomputed = dict(preserved)
    recomputed.pop("result_sha256", None)
    _fail(
        failures,
        hashlib.sha256(canonical_json(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )

    boundary = preserved["claim_boundary"]
    for key in (
        "establishes_human_equivalent_time_horizon",
        "closes_generality_gate_g7",
        "agi_evidence",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    print(json.dumps({
        "schema": "m077-recovery-check-v1",
        "schedule_commitment": bound["schedule_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "failed_conditions": preserved["failed_conditions"],
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
