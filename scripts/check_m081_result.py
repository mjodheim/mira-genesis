"""Independently re-verify the preserved M081 two-environment result.

Everything that does not need a container is checked unconditionally: the bank replays from the
committed salt, the sealed tasks expect their resource, the agent cannot branch on the environment,
the images are digest-pinned, and the preserved digest recomputes. The arms are re-derived only when
Docker is reachable; without it the checker reports that the live re-derivation was skipped rather
than silently passing or failing.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m081_two_real_environments import (  # noqa: E402
    ALPINE_IMAGE,
    ARMS,
    ENVIRONMENTS,
    PYTHON_IMAGE,
    TASKS_PER_ENVIRONMENT,
    build_bank,
    docker_available,
    evaluate,
    run_arm,
)

BASE = ROOT / "experiments/M081"
MODULE = ROOT / "metamorphosis/m081_two_real_environments.py"
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
        [t.commitment() for t in bank] == [r["commitment"] for r in bound["tasks"]],
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

    for kind in ENVIRONMENTS:
        sealed = [t for t in bank if t.environment == kind and t.targets_sealed]
        _fail(failures, len(sealed) == 1, f"{kind} does not carry exactly one sealed task")
        if sealed:
            _fail(
                failures, bool(sealed[0].expected),
                f"the {kind} sealed task expects nothing, so its silent discard would score as a "
                "pass and the self-report clause would be untested",
            )

    # One interface: the agent must not name or inspect an environment.
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    agent = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "Agent"
    )
    source = ast.unparse(agent)
    for forbidden in ("shell", "service", ".kind"):
        _fail(
            failures, forbidden not in source,
            f"the agent branches on the environment via {forbidden!r}",
        )

    for image in (ALPINE_IMAGE, PYTHON_IMAGE):
        _fail(failures, "@sha256:" in image, f"image {image} is not digest-pinned")

    for amendment in protocol.get("amendments", []):
        _fail(
            failures,
            amendment["applied_before_bank_materialization"] is True
            and amendment["applied_before_any_recorded_result"] is True,
            f"amendment {amendment.get('id')} claims a post-materialization change",
        )

    shared = preserved["arms"]["shared_interface"]
    completable = TASKS_PER_ENVIRONMENT - 1
    for kind in ENVIRONMENTS:
        _fail(
            failures, shared["completed_per_environment"][kind] == completable,
            f"the preserved shared interface did not complete every completable {kind} task",
        )
    _fail(
        failures, preserved["arms"]["crossed_drivers"]["completed_total"] == 0,
        "the preserved crossed arm completed a task, so the environments are not distinct",
    )
    _fail(
        failures,
        preserved["arms"]["self_report_scored"]["overcount"] >= len(ENVIRONMENTS),
        "the preserved self-report arm did not over-report once per environment",
    )
    _fail(
        failures, shared["claimed_total"] > shared["state_reached_total"],
        "self-report did not exceed environment state, so the scoring rule is untested",
    )
    _fail(
        failures, len(preserved["construction_fixes_before_materialization"]) == 2,
        "the recorded construction fixes were removed",
    )

    recomputed = {k: v for k, v in preserved.items() if k != "result_sha256"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )
    boundary = preserved["claim_boundary"]
    for key in (
        "establishes_browser_competence", "establishes_desktop_or_vm_competence",
        "closes_generality_gate_g6", "agi_evidence",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    live = docker_available()
    if live:
        arms = {arm: run_arm(bank, arm) for arm in ARMS}
        for arm in ARMS:
            _fail(
                failures,
                arms[arm]["completed_per_environment"]
                == preserved["arms"][arm]["completed_per_environment"],
                f"{arm} does not reproduce against live containers",
            )
        verdict = evaluate(arms)
        _fail(
            failures, (preserved["verdict"] == "positive") == verdict.positive,
            "the recomputed verdict disagrees with the preserved verdict",
        )

    print(json.dumps({
        "schema": "m081-environments-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "live_rederivation": "performed" if live else "skipped, Docker unavailable",
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
