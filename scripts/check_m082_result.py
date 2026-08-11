"""Independently re-verify the preserved M082 browser result.

Everything that does not need a container is checked unconditionally: the bank replays from the
committed salt, the interface is imported rather than restated, the browser store has no HTTP route,
state is read from the rendered DOM, the profile is persistent, and the preserved digest recomputes.
The arms are re-derived only when Docker and the browser image are present; otherwise the checker
reports that the live re-derivation was skipped.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m081_two_real_environments import TASKS_PER_ENVIRONMENT  # noqa: E402
from metamorphosis.m082_browser_environment import (  # noqa: E402
    ARMS,
    BROWSER_BASE_DIGEST,
    DRIVER_SOURCE,
    ENVIRONMENTS,
    PAGE_SOURCE,
    build_bank,
    evaluate,
    run_arm,
    runnable,
)

BASE = ROOT / "experiments/M082"
MODULE = ROOT / "metamorphosis/m082_browser_environment.py"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
DOCKERFILE_PATH = BASE / "browser-image/Dockerfile"
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
    _fail(
        failures,
        hashlib.sha256(DOCKERFILE_PATH.read_bytes()).hexdigest()
        == bound["dockerfile_sha256"],
        "the browser image recipe changed after the bank was bound",
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

    # One interface, imported rather than restated.
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        and node.module == "metamorphosis.m081_two_real_environments"
        for alias in node.names
    }
    for name in ("Agent", "ShellEnvironment", "ServiceEnvironment", "Action"):
        _fail(failures, name in imported, f"{name} is not imported from M081")
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for name in ("Agent", "ShellEnvironment", "ServiceEnvironment"):
        _fail(failures, name not in defined, f"{name} is redefined instead of reused")

    # The browser must not be the service in a costume.
    _fail(failures, "localStorage" in PAGE_SOURCE, "the page does not use localStorage")
    _fail(
        failures, DRIVER_SOURCE.count("createServer") == 1,
        "the driver exposes more than a static page server",
    )
    _fail(
        failures, "$$eval('li'" in DRIVER_SOURCE,
        "browser state is not read from the rendered DOM",
    )
    _fail(
        failures, "launchPersistentContext" in DRIVER_SOURCE,
        "the browser profile is not persistent, so the harness would hold the state",
    )
    _fail(
        failures, "chromium.launch()" not in DRIVER_SOURCE,
        "a non-persistent browser launch remains in the driver",
    )
    _fail(
        failures, BROWSER_BASE_DIGEST.split("@")[1] in DOCKERFILE_PATH.read_text(encoding="utf-8"),
        "the browser image does not derive from the pinned base",
    )

    shared = preserved["arms"]["shared_interface"]
    completable = TASKS_PER_ENVIRONMENT - 1
    for kind in ENVIRONMENTS:
        _fail(
            failures, shared["completed_per_environment"][kind] == completable,
            f"the preserved interface did not complete every completable {kind} task",
        )
    _fail(
        failures, shared["environments_covered"] == len(ENVIRONMENTS),
        "the preserved result does not cover all three environments",
    )
    _fail(
        failures, preserved["arms"]["crossed_drivers"]["completed_total"] == 0,
        "the preserved crossed arm completed a task, so the browser store is reachable "
        "without the DOM",
    )
    _fail(
        failures, shared["browser_overcount"] >= 1,
        "the browser confirmation never diverged from the DOM, so the scoring rule is untested",
    )
    _fail(
        failures, len(preserved["transport_defects_found_and_fixed"]) == 3,
        "the recorded transport defects were removed",
    )

    recomputed = {k: v for k, v in preserved.items() if k != "result_sha256"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )
    boundary = preserved["claim_boundary"]
    for key in (
        "establishes_desktop_or_vm_competence", "establishes_general_web_competence",
        "closes_generality_gate_g6", "agi_evidence",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    live = runnable()
    if live:
        arms = {arm: run_arm(bank, arm) for arm in ARMS}
        for arm in ARMS:
            _fail(
                failures,
                arms[arm]["completed_per_environment"]
                == preserved["arms"][arm]["completed_per_environment"],
                f"{arm} does not reproduce against live containers",
            )
        _fail(
            failures, (preserved["verdict"] == "positive") == evaluate(arms).positive,
            "the recomputed verdict disagrees with the preserved verdict",
        )

    print(json.dumps({
        "schema": "m082-browser-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "live_rederivation": "performed" if live else "skipped, Docker or image unavailable",
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
