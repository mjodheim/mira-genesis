"""Bind the M080 skill bank and preserve the first continual-retention result.

Both artifacts are written once. The frozen protocol forbids retrying the first materialized bank.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m080_continual_retention import (  # noqa: E402
    ARMS,
    GENERATOR_VERSION,
    IRREGULARS_PER_SKILL,
    SKILL_COUNT,
    build_bank,
    evaluate,
    run_arm,
)

BASE = ROOT / "experiments/M080"
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
    if len(bank) != SKILL_COUNT:
        raise SystemExit("skill count drifted from the frozen protocol")

    # The interference the whole claim rests on, verified before any arm runs.
    for skill in bank[3:]:
        if skill.shares_rule_with is None or skill.conflicts_on_key is None:
            raise SystemExit(
                f"skill {skill.index} carries no conflict; the construction is wrong rather "
                "than the lineage"
            )
        donor = bank[skill.shares_rule_with]
        key = skill.conflicts_on_key
        if donor.expected(key) == skill.expected(key):
            raise SystemExit(f"skill {skill.index} does not actually conflict with its donor")

    bank_payload = {
        "schema": "m080-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "skill_count": len(bank),
        "skills": [
            {
                "index": skill.index, "commitment": skill.commitment(),
                "rule": [skill.slope, skill.offset],
                "shares_rule_with": skill.shares_rule_with,
                "conflicts_on_key": skill.conflicts_on_key,
                "keys": len(skill.keys), "examples": len(skill.examples),
                "holdouts": len(skill.holdouts), "irregulars": len(skill.irregulars),
            }
            for skill in bank
        ],
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    verdict = evaluate(arms, bank)

    result_payload = {
        "schema": "m080-continual-retention-result-v1",
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
        "replay_dependence": verdict.replay_dependence,
        "private_slot_ceiling": SKILL_COUNT * (1 + IRREGULARS_PER_SKILL),
        "claim_boundary": protocol["claim_boundary"],
        "instrument_fixes_before_materialization": [
            "interference moved from capacity pressure alone to rule sharing with a conflicting "
            "exception key, because capacity never actually bound and no arm ever evicted",
            "retention is measured over a skill's complete key set; damage lands on exception keys "
            "that the split forces into examples, so holdout-only scoring hid it",
            "the rollback check compared the checkpoint against its own digest and could never "
            "fail; it now compares the live table after the rejection is handled",
        ],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    print(f"replay dependence (measured, not thresholded): {verdict.replay_dependence}")
    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:17} lost={record['capabilities_lost']}"
            f" final_failures={record['final_retention_failures']}"
            f" slots={record['slots_used_final']}"
            f" reused={record['rules_reused']}"
            f" rollbacks={record['rollbacks']}"
            f" mismatches={record['rollback_mismatches']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
