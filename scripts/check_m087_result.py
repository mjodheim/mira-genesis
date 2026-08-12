"""Decisive checker for M087: chronology, leakage, single materialization, register agreement.

M086-A recorded a positive verdict partly because a scientific checker existed without being
decisive in CI. Every property this script tests is one the registers claim, and a failure here
turns the repository red.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m087_evidence import digest_of, leak_problems  # noqa: E402
from metamorphosis.m087_families import qualified_family  # noqa: E402
from metamorphosis.m087_lineage import (  # noqa: E402
    QUALIFICATION_FAMILIES,
    CONDITIONS,
    evaluate,
)

RESULT = ROOT / "experiments/M087/RESULT.json"
PROTOCOL = ROOT / "experiments/M087/PROTOCOL.json"
SALT = "m087-qualification-salt-2026-08-12"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-result", action="store_true")
    arguments = parser.parse_args()

    if not RESULT.exists():
        print("no M087 result is present", file=sys.stderr)
        return 2 if arguments.require_result else 0

    result = json.loads(RESULT.read_text(encoding="utf-8"))
    problems: list[str] = []

    if result["protocol_raw_sha256"] != hashlib.sha256(PROTOCOL.read_bytes()).hexdigest():
        problems.append("the result does not bind the committed protocol blob")
    if result["attempt"] != 1 or result["retry_used"] is not False:
        problems.append("the result is not a single unretried attempt")
    if result["model_calls"] != 0 or result["network_calls"] != 0:
        problems.append("the scientific run recorded a model or network call")
    if set(result["conditions_declared"]) != set(CONDITIONS):
        problems.append("the declared conditions differ from the frozen list")
    if set(result["evaluation"]["conditions"]) != set(CONDITIONS):
        problems.append("the verdict does not compute every frozen condition")

    order = result["chronology"]["order"]
    if order.index("T6_policy_adopted_and_serialized") >= order.index(
        "T7_qualification_materialized"
    ):
        problems.append("qualification was materialized before the adopted policy was digested")
    if result["chronology"]["ordered"] is not True:
        problems.append("the recorded chronology is out of order")

    if result["leak_findings"]:
        problems.append("the result carries evidence-leak findings")
    for arm, record in result["arms"].items():
        for family_id, log in zip(QUALIFICATION_FAMILIES, record["acquisition_logs"]):
            fam = qualified_family(family_id, SALT)
            problems += [
                f"{arm}/{family_id}: {item}"
                for item in leak_problems(log, fam.spaces, [c.request for c in fam.hidden_cases])
            ]
        if arm != "evolvable_selection_evidence" and record["total_acquisitions"]:
            problems.append(f"{arm} acquired evidence it was not entitled to")

    recomputed = evaluate(
        result["development"], result["arms"], result["rollback"],
        result["leak_findings"], result["chronology"],
    )
    if recomputed != result["evaluation"]:
        problems.append("the recorded verdict does not reproduce from the preserved arms")

    body = {key: value for key, value in result.items() if key != "result_digest"}
    if digest_of(body) != result["result_digest"]:
        problems.append("the result digest does not cover the preserved result")

    state = json.loads((ROOT / "experiments/M087/REGISTER_CLAIM.json").read_text("utf-8"))
    if state["result_digest"] != result["result_digest"]:
        problems.append("the register claim and the result disagree on the digest")
    if state["verdict"] != result["evaluation"]["verdict"]:
        problems.append("the register claim and the result disagree on the verdict")
    if state["gate_advanced"] is not False:
        problems.append("a generality gate was recorded as advanced")

    for problem in problems:
        print(f"blocking: {problem}", file=sys.stderr)
    if problems:
        return 2
    print(f"M087 result verified: {result['evaluation']['verdict']}, "
          f"{len(CONDITIONS)} conditions, digest {result['result_digest'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
