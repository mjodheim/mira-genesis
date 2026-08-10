"""Bind the M078 body bank and preserve the first refusal result.

Both artifacts are written once. The frozen protocol forbids retrying the first materialized bank,
so a second observation must be a separately named experiment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m078_incompatible_refusal import (  # noqa: E402
    ARMS,
    BODIES_PER_CLASS,
    BODY_CLASSES,
    GENERATOR_VERSION,
    HIDDEN_OBSERVATIONS_PER_BODY,
    build_bank,
    evaluate,
    run_arm,
)

BASE = ROOT / "experiments/M078"
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
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    bank = build_bank(salt)
    for body_class in BODY_CLASSES:
        members = [body for body in bank if body.body_class == body_class]
        if len(members) != BODIES_PER_CLASS:
            raise SystemExit(f"class {body_class} count drifted")
        commitments = [body.commitment() for body in members]
        if commitments != sorted(commitments):
            raise SystemExit(f"class {body_class} is not in ascending commitment order")

    bank_payload = {
        "schema": "m078-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "body_count": len(bank),
        "hidden_observations_per_body": HIDDEN_OBSERVATIONS_PER_BODY,
        "bodies": [
            {"body_class": body.body_class, "index": body.index,
             "commitment": body.commitment()}
            for body in bank
        ],
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    verdict = evaluate(arms)

    result_payload = {
        "schema": "m078-incompatible-refusal-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": bank_payload["bank_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "network_used": False,
        "python": platform.python_version(),
        "arms": arms,
        "verdict": "positive" if verdict.positive else "negative",
        "failed_conditions": list(verdict.reasons),
        "claim_boundary": protocol["claim_boundary"],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:15} compatible={record['compatible_adapters']}/{BODIES_PER_CLASS}"
            f" hidden_perfect={record['compatible_hidden_perfect']}/{BODIES_PER_CLASS}"
            f" false_refusals={record['false_refusals']}"
            f" true_refusals={record['true_refusals']}/{BODIES_PER_CLASS}"
            f" invented={record['invented_adapters']}"
            f" hidden_failures={record['incompatible_hidden_failures']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
