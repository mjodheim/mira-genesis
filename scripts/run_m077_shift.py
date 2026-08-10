"""Bind the M077 fault schedule and preserve the first shift result, positive or negative.

The script refuses to overwrite either artifact. The frozen protocol forbids retrying the first
materialized schedule, so a second observation must be a separately named experiment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m077_long_horizon_recovery import (  # noqa: E402
    ARMS,
    FAULT_KINDS,
    GENERATOR_VERSION,
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


def _write_once(path: Path, payload: dict, digest_key: str) -> bool:
    payload[digest_key] = hashlib.sha256(canonical_json({
        key: value for key, value in payload.items() if key != digest_key
    })).hexdigest()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get(digest_key) != payload[digest_key]:
            raise SystemExit(
                f"refusing to overwrite {path.name} with a different {digest_key}; "
                "the frozen protocol forbids replacing a materialized artifact"
            )
        print(f"{path.name} already bound and identical: {payload[digest_key]}")
        return False
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"bound {path.name}: {payload[digest_key]}")
    return True


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["episode_generation"]["generator_version"] != GENERATOR_VERSION:
        raise SystemExit("generator version drifted from the frozen protocol")
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    schedules = {}
    for horizon in HORIZONS:
        schedule = build_schedule(salt, horizon)
        missing = set(FAULT_KINDS) - set(schedule.values())
        if missing:
            raise SystemExit(f"horizon {horizon} omitted fault kinds {sorted(missing)}")
        schedules[str(horizon)] = {str(index): kind for index, kind in schedule.items()}

    schedule_payload = {
        "schema": "m077-schedule-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "horizons": list(HORIZONS),
        "schedules": schedules,
    }
    _write_once(SCHEDULE_PATH, schedule_payload, "schedule_commitment")

    arms = {arm: run_arm(salt, arm) for arm in ARMS}
    verdict = evaluate(arms)

    result_payload = {
        "schema": "m077-long-horizon-recovery-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "schedule_commitment": schedule_payload["schedule_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "network_used": False,
        "python": platform.python_version(),
        "horizon_unit": "episode_count_not_human_equivalent_time",
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
        "instrument_corrections_before_materialization": [
            "per-unique-fault accounting replaced raw detection events, which could exceed the "
            "number of injected faults because an unrepaired fault re-triggers every episode",
            "the outstanding-fault tracker became a set, because faults land on adjacent episodes "
            "and a single slot silently dropped the earlier one",
        ],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        cells = "  ".join(
            f"h{h}: det={arms[arm]['horizons'][str(h)]['detections']}"
            f"/{arms[arm]['horizons'][str(h)]['faults_injected']}"
            f" rate={arms[arm]['horizons'][str(h)]['restoration_rate_on_detected']:.2f}"
            for h in HORIZONS
        )
        print(f"  {arm:24} {cells}")
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
