"""Bind the M079 task bank and preserve the first planning result.

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

from metamorphosis.m079_planning_clarification import (  # noqa: E402
    ARMS,
    EPISODES_PER_FAMILY,
    FAMILIES,
    GENERATOR_VERSION,
    State,
    evaluate,
    materialize_bank,
    run_arm,
    satisfying_plans,
)

BASE = ROOT / "experiments/M079"
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

    bank = materialize_bank(salt)
    if len(bank) != protocol["episode_generation"]["episode_count"]:
        raise SystemExit("episode count drifted from the frozen protocol")

    # The construction claim the whole experiment rests on, verified before any arm runs.
    ambiguity: list[dict[str, object]] = []
    for episode in bank:
        options = satisfying_plans(
            episode, State(episode.start, None, frozenset(), frozenset()), episode.budget,
        )
        labels = {episode.is_unsafe(terminal) for _, _, terminal in options}
        genuinely_ambiguous = len(labels) > 1
        if (episode.family == "ambiguous") != genuinely_ambiguous:
            raise SystemExit(
                f"{episode.family} episode {episode.index} does not match its declared "
                "ambiguity; the construction is wrong rather than the planner"
            )
        ambiguity.append({
            "family": episode.family, "commitment": episode.commitment(),
            "satisfying_terminal_states": len(options),
            "safety_labels_present": sorted(str(label) for label in labels),
            "blocked_edge_present": episode.blocked_edge is not None,
        })

    bank_payload = {
        "schema": "m079-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "episode_count": len(bank),
        "episodes": ambiguity,
    }
    _write_once(BANK_PATH, bank_payload, "bank_commitment")

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    verdict = evaluate(arms)

    result_payload = {
        "schema": "m079-planning-clarification-result-v1",
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
        "construction_fixes_before_materialization": [
            "sealed states are terminal in the search; every goal requires a seal, so expanding "
            "them made the state space intractable",
            "the revision family blocks an edge the initial optimal plan traverses and verifies a "
            "detour remains feasible; an arbitrary block was routed around in three of eight "
            "episodes and forced no revision",
        ],
    }
    _write_once(RESULT_PATH, result_payload, "result_sha256")

    print(f"\nverdict: {result_payload['verdict']}")
    for arm in ARMS:
        record = arms[arm]
        solved = "/".join(f"{record['solved'][f]}" for f in FAMILIES)
        asked = "/".join(f"{record['clarifications'][f]}" for f in FAMILIES)
        print(
            f"  {arm:12} solved={solved} (of {EPISODES_PER_FAMILY} each)"
            f"  asked={asked}  unsafe={record['unsafe_terminal_states']}"
            f"  replanned={record['replanned']}"
        )
    for reason in verdict.reasons:
        print(f"  FAILED: {reason}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
