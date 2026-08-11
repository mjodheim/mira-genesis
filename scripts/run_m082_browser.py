"""Bind the M082 task bank and preserve the first browser result.

Requires Docker and the locally built browser image. Without either the experiment is inconclusive
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

from metamorphosis.m081_two_real_environments import TASKS_PER_ENVIRONMENT  # noqa: E402
from metamorphosis.m082_browser_environment import (  # noqa: E402
    ARMS,
    BROWSER_BASE_DIGEST,
    BROWSER_IMAGE,
    ENVIRONMENTS,
    GENERATOR_VERSION,
    build_bank,
    evaluate,
    run_arm,
    runnable,
)

BASE = ROOT / "experiments/M082"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
DOCKERFILE_PATH = BASE / "browser-image/Dockerfile"
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
    if not runnable():
        print(
            "INCONCLUSIVE: Docker or the browser image is unavailable, so M082 is not runnable "
            "rather than negative"
        )
        return 3

    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])
    bank = build_bank(salt)
    browser_sealed = [
        t for t in bank if t.environment == "browser" and t.targets_sealed
    ]
    if len(browser_sealed) != 1 or not browser_sealed[0].expected:
        raise SystemExit(
            "the browser must carry exactly one sealed task that expects its resource, otherwise "
            "the page's dishonest confirmation is scored as a pass"
        )

    bank_payload = {
        "schema": "m082-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "environments": list(ENVIRONMENTS),
        "browser_image": BROWSER_IMAGE,
        "browser_base_digest": BROWSER_BASE_DIGEST,
        "dockerfile_sha256": hashlib.sha256(DOCKERFILE_PATH.read_bytes()).hexdigest(),
        "task_count": len(bank),
        "tasks": [
            {
                "environment": task.environment, "index": task.index,
                "commitment": task.commitment(), "targets_sealed": task.targets_sealed,
            }
            for task in bank
        ],
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    verdict = evaluate(arms)

    result_payload = {
        "schema": "m082-browser-environment-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": bank_payload["bank_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "python": platform.python_version(),
        "environments": list(ENVIRONMENTS),
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
        "transport_defects_found_and_fixed": [
            "docker exec arguments beginning with a slash are rewritten by MSYS path conversion on "
            "Windows, so every container command is wrapped in sh -c; this is the defect class that "
            "produced the negative M070",
            "a fresh browser profile per action discarded localStorage, which would have left the "
            "harness holding the state instead of the browser; a persistent profile now keeps it",
            "passing the page through an environment variable required flattening it to one line, "
            "which turned a // comment into a comment over the whole script and disabled the save "
            "handler; the page is now written to a file",
        ],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    completable = TASKS_PER_ENVIRONMENT - 1
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:20} completed={record['completed_per_environment']}"
            f" (of {completable} completable each)"
            f" covered={record['environments_covered']}"
            f" browser_overcount={record['browser_overcount']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
