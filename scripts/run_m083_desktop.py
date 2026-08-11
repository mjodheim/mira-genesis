"""Bind the M083 desktop task bank and preserve the first result.

Requires Docker and the locally built desktop image. Without either the experiment is inconclusive
rather than negative, and this script says so instead of recording a failure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m083_gui_desktop_session import (  # noqa: E402
    ARMS,
    DESKTOP_IMAGE,
    GENERATOR_VERSION,
    LOCKED_CELL,
    TASKS_PER_ENVIRONMENT,
    build_desktop_tasks,
    cell_label,
    evaluate,
    run_desktop_arm,
    runnable,
)

BASE = ROOT / "experiments/M083"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
DOCKERFILE_PATH = BASE / "desktop-image/Dockerfile"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _write_once(path: Path, payload: dict, digest_key: str) -> None:
    payload[digest_key] = hashlib.sha256(_canonical({
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
        return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"bound {path.name}: {payload[digest_key]}")


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["episode_generation"]["generator_version"] != GENERATOR_VERSION:
        raise SystemExit("generator version drifted from the frozen protocol")
    if protocol["environment_is_a_virtual_machine"] is not False:
        raise SystemExit("the protocol must continue to state that this is not a virtual machine")
    if not runnable():
        print(
            "INCONCLUSIVE: Docker or the desktop image is unavailable, so M083 is not runnable "
            "rather than negative"
        )
        return 3

    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])
    bank = build_desktop_tasks(salt)
    locked = [task for task in bank if task.targets_sealed]
    if len(locked) != 1 or not locked[0].expected:
        raise SystemExit(
            "the bank must carry exactly one locked-cell task that expects the cell to change, "
            "otherwise the application's dishonest acceptance is scored as a pass"
        )
    if cell_label(*LOCKED_CELL) not in locked[0].expected:
        raise SystemExit("the locked task does not target the locked cell")

    bank_payload = {
        "schema": "m083-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "desktop_image": DESKTOP_IMAGE,
        "dockerfile_sha256": hashlib.sha256(DOCKERFILE_PATH.read_bytes()).hexdigest(),
        "locked_cell": list(LOCKED_CELL),
        "task_count": len(bank),
        "tasks": [
            {
                "index": task.index, "commitment": task.commitment(),
                "expected": dict(task.expected), "targets_locked_cell": task.targets_sealed,
            }
            for task in bank
        ],
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms = {arm: run_desktop_arm(bank, arm) for arm in ARMS}
    verdict = evaluate(arms)

    result_payload = {
        "schema": "m083-gui-desktop-session-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": bank_payload["bank_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "python": platform.python_version(),
        "environment_is_a_virtual_machine": False,
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    completable = TASKS_PER_ENVIRONMENT - 1
    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:20} completed={record['completed']}/{completable}"
            f" state_reached={record['state_reached_total']}"
            f" claimed={record['claimed_total']}"
            f" overcount={record['overcount']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
