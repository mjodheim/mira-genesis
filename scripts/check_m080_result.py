"""Independently recompute the preserved M080 retention result from its frozen inputs.

The checker rebuilds the skill bank from the committed salt, re-verifies the interference the claim
rests on — that later skills reuse an earlier rule and genuinely conflict with it — re-derives all
four arms, confirms the rollback check can still fail, and recomputes the preserved digest. Replay
dependence is reported, never asserted in either direction.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m080_continual_retention import (  # noqa: E402
    ARMS,
    IRREGULARS_PER_SKILL,
    SKILL_COUNT,
    TABLE_SLOTS,
    build_bank,
    evaluate,
    induce,
    run_arm,
)

BASE = ROOT / "experiments/M080"
MODULE = ROOT / "metamorphosis/m080_continual_retention.py"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    bound = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["episode_generation"]["salt_hex"])

    _fail(
        failures,
        hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
        == preserved["protocol_commitment"],
        "protocol bytes no longer match the recorded commitment",
    )

    bank = build_bank(salt)
    _fail(
        failures,
        [s.commitment() for s in bank] == [r["commitment"] for r in bound["skills"]],
        "replayed bank does not match the bound commitment",
    )
    recomputed_bank = {k: v for k, v in bound.items() if k != "bank_commitment"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed_bank)).hexdigest() == bound["bank_commitment"],
        "bank commitment does not recompute",
    )
    _fail(
        failures, bound["bank_commitment"] == preserved["bank_commitment"],
        "the preserved result is bound to a different bank",
    )

    # The interference. Without it, retention is guaranteed by construction and measures nothing.
    for skill in bank[3:]:
        donor = bank[skill.shares_rule_with] if skill.shares_rule_with is not None else None
        _fail(failures, donor is not None, f"skill {skill.index} shares no rule")
        if donor is None:
            continue
        _fail(
            failures, (skill.slope, skill.offset) == (donor.slope, donor.offset),
            f"skill {skill.index} does not actually reuse its donor's rule",
        )
        key = skill.conflicts_on_key
        _fail(
            failures,
            key is not None and key in donor.irregulars
            and donor.expected(key) != skill.expected(key),
            f"skill {skill.index} does not conflict with its donor; the construction is wrong "
            "rather than the lineage",
        )
    for skill in bank:
        _fail(
            failures, all(key in skill.examples for key in skill.irregulars),
            f"skill {skill.index} hides an irregular from its examples, making it unlearnable",
        )
        _fail(
            failures, induce(skill)[0] == (skill.slope, skill.offset),
            f"skill {skill.index} rule is not recoverable from its examples alone",
        )

    # The information boundary.
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    lineage_class = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "Lineage"
    )
    attributes = {n.attr for n in ast.walk(lineage_class) if isinstance(n, ast.Attribute)}
    _fail(failures, "holdouts" not in attributes, "the lineage reads holdouts")

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    for arm in ARMS:
        _fail(
            failures, preserved["arms"][arm]["timeline"] == json.loads(
                json.dumps(arms[arm]["timeline"]),
            ),
            f"{arm} does not reproduce",
        )
        _fail(
            failures, arms[arm]["slots_used_final"] <= TABLE_SLOTS,
            f"{arm} exceeded the bounded table",
        )

    main_arm = arms["lineage"]
    ceiling = SKILL_COUNT * (1 + IRREGULARS_PER_SKILL)
    _fail(
        failures,
        main_arm["capabilities_lost"] == 0 and main_arm["final_retention_failures"] == 0,
        "the lineage no longer retains every earlier capability",
    )
    _fail(
        failures, main_arm["own_holdout_perfect"] == SKILL_COUNT,
        "the lineage no longer generalises on every skill",
    )
    _fail(
        failures, main_arm["slots_used_final"] < ceiling,
        f"memory growth is not sublinear against the private-slot ceiling of {ceiling}",
    )
    _fail(failures, main_arm["rules_reused"] >= 1, "no positive transfer was observed")
    _fail(
        failures, main_arm["rollbacks"] >= 1 and main_arm["rollback_mismatches"] == 0,
        "the lineage did not roll back exactly",
    )
    _fail(
        failures, arms["no_consolidation"]["capabilities_lost"] >= 1,
        "the consolidation ablation lost nothing, so the interference is not real",
    )
    _fail(
        failures, arms["no_rollback"]["rollback_mismatches"] >= 1,
        "the rollback ablation produced no mismatch, so the rollback check may be vacuous",
    )

    verdict = evaluate(arms, bank)
    _fail(
        failures, (preserved["verdict"] == "positive") == verdict.positive,
        "the recomputed verdict disagrees with the preserved verdict",
    )
    _fail(
        failures, preserved["replay_dependence"] == verdict.replay_dependence,
        "the recorded replay dependence no longer matches what the arms show",
    )
    _fail(
        failures, not any("replay" in reason for reason in verdict.reasons),
        "replay dependence became a pass/fail condition; the protocol forbids a direction",
    )
    _fail(
        failures, len(preserved["instrument_fixes_before_materialization"]) == 3,
        "the recorded instrument fixes were removed",
    )

    recomputed = {k: v for k, v in preserved.items() if k != "result_sha256"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )
    boundary = preserved["claim_boundary"]
    for key in ("closes_generality_gate_g5", "establishes_weight_learning", "agi_evidence"):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    print(json.dumps({
        "schema": "m080-retention-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "replay_dependence": preserved["replay_dependence"],
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
