"""Independently recompute the preserved M078 refusal result from its frozen inputs.

The checker rebuilds the bank from the committed salt, re-derives all three arms, re-verifies that
every incompatible body still admits a public-fitting candidate — without which refusal would be a
trivial empty search — and recomputes the preserved digest. It fails closed on any drift.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m078_incompatible_refusal import (  # noqa: E402
    ARMS,
    BODIES_PER_CLASS,
    REFUSED_UNDERDETERMINED,
    SKILL_NAMES,
    _fitting_commands,
    _injective_assignment,
    build_bank,
    evaluate,
    run_arm,
)

BASE = ROOT / "experiments/M078"
MODULE = ROOT / "metamorphosis/m078_incompatible_refusal.py"
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
        [body.commitment() for body in bank] == [r["commitment"] for r in bound["bodies"]],
        "replayed bank does not match the bound commitment",
    )
    recomputed_bank = {k: v for k, v in bound.items() if k != "bank_commitment"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed_bank)).hexdigest() == bound["bank_commitment"],
        "bank commitment does not recompute",
    )
    _fail(
        failures,
        bound["bank_commitment"] == preserved["bank_commitment"],
        "the preserved result is bound to a different bank",
    )

    # Refusal must never be reducible to an exhausted search.
    for body in (b for b in bank if b.body_class == "incompatible"):
        viable = [
            mask for mask in range(256)
            if all(_fitting_commands(body, mask, name) for name in SKILL_NAMES)
        ]
        _fail(
            failures, bool(viable),
            f"incompatible body {body.index} offered no public fit, making refusal trivial",
        )
        if viable:
            fits = {name: _fitting_commands(body, viable[0], name) for name in SKILL_NAMES}
            _fail(
                failures, _injective_assignment(fits) is None,
                f"incompatible body {body.index} admits an injective assignment; the "
                "construction is wrong rather than the discoverer",
            )

    # The information boundary that post-hoc disqualified M069.
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    function = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "discover"
    )
    attributes = {n.attr for n in ast.walk(function) if isinstance(n, ast.Attribute)}
    for forbidden in ("hidden", "body_class", "aliased_pair", "_operations"):
        _fail(
            failures, forbidden not in attributes,
            f"the discoverer reads {forbidden}, breaking the information boundary",
        )

    arms = {arm: run_arm(bank, arm) for arm in ARMS}
    for arm in ARMS:
        _fail(
            failures, preserved["arms"][arm]["records"] == arms[arm]["records"],
            f"{arm} does not reproduce",
        )

    main_arm = arms["discoverer"]
    _fail(
        failures, main_arm["compatible_adapters"] == BODIES_PER_CLASS,
        "the discoverer no longer adapts every compatible body",
    )
    _fail(
        failures, main_arm["compatible_hidden_perfect"] == BODIES_PER_CLASS,
        "an accepted adapter no longer passes every hidden observation",
    )
    _fail(failures, main_arm["false_refusals"] == 0, "the discoverer produced a false refusal")
    _fail(
        failures, main_arm["true_refusals"] == BODIES_PER_CLASS,
        "the discoverer no longer refuses every incompatible body",
    )
    _fail(
        failures, main_arm["empty_set_refusals"] == 0,
        "a refusal came from an empty candidate set, which is not calibrated",
    )
    for record in main_arm["records"]:
        if record["refused"]:
            _fail(
                failures, record["refusal_kind"] == REFUSED_UNDERDETERMINED,
                "a refusal was recorded with a non-calibrated kind",
            )
    _fail(
        failures, arms["always_refuse"]["adapters_recovered"] == 0,
        "the always-refuse control recovered an adapter",
    )
    _fail(
        failures, arms["never_refuse"]["incompatible_hidden_failures"] >= 1,
        "the never-refuse control passed hidden validation, so the public evidence was "
        "sufficient and the refusal claim is empty",
    )

    verdict = evaluate(arms)
    _fail(
        failures, (preserved["verdict"] == "positive") == verdict.positive,
        "the recomputed verdict disagrees with the preserved verdict",
    )
    _fail(failures, list(verdict.reasons) == preserved["failed_conditions"],
          "the recorded failed conditions no longer match")

    recomputed = {k: v for k, v in preserved.items() if k != "result_sha256"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )
    boundary = preserved["claim_boundary"]
    for key in (
        "closes_generality_gate_g1", "establishes_general_epistemic_humility", "agi_evidence",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    print(json.dumps({
        "schema": "m078-refusal-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
