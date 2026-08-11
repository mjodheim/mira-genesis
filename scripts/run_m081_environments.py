"""Bind the M081 task bank and preserve the first two-environment result.

Requires a reachable Docker daemon and the two digest-pinned images. Without them the experiment is
inconclusive rather than negative, and this script says so instead of recording a failure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m081_two_real_environments import (  # noqa: E402
    ALPINE_IMAGE,
    ARMS,
    ENVIRONMENTS,
    GENERATOR_VERSION,
    PYTHON_IMAGE,
    TASKS_PER_ENVIRONMENT,
    build_bank,
    docker_available,
    evaluate,
    run_arm,
)

BASE = ROOT / "experiments/M081"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
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
    if not docker_available():
        print("INCONCLUSIVE: Docker is unavailable, so M081 is not runnable rather than negative")
        return 3

    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])
    bank = build_bank(salt)
    if len(bank) != TASKS_PER_ENVIRONMENT * len(ENVIRONMENTS):
        raise SystemExit("bank size drifted from the frozen protocol")

    for environment in ENVIRONMENTS:
        sealed = [t for t in bank if t.environment == environment and t.targets_sealed]
        if len(sealed) != 1:
            raise SystemExit(f"{environment} must carry exactly one sealed task")
        if not sealed[0].expected:
            raise SystemExit(
                "the sealed task must expect its resource, otherwise its silent discard is "
                "scored as a success and the self-report clause is untested"
            )

    bank_payload = {
        "schema": "m081-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "images": {"shell": ALPINE_IMAGE, "service": PYTHON_IMAGE},
        "task_count": len(bank),
        "tasks": [
            {
                "environment": task.environment, "index": task.index,
                "commitment": task.commitment(), "actions": len(task.actions),
                "expected": len(task.expected), "targets_sealed": task.targets_sealed,
            }
            for task in bank
        ],
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    verdict = evaluate(arms)

    result_payload = {
        "schema": "m081-two-real-environments-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": bank_payload["bank_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "python": platform.python_version(),
        "docker_server": True,
        "environments": list(ENVIRONMENTS),
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
        "construction_fixes_before_materialization": [
            "the crossed arm now sends actions through the other environment's driver while state "
            "is read from the environment under test; the first version swapped both and crossed "
            "nothing",
            "the sealed task now expects its resource to exist, so a silent discard is a failure; "
            "the first version expected nothing and scored the discard as a pass",
        ],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:20} completed={record['completed_per_environment']}"
            f" state_reached={record['state_reached_total']}"
            f" claimed={record['claimed_total']}"
            f" overcount={record['overcount']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
