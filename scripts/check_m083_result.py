"""Independently re-verify the preserved M083 desktop result.

Checked unconditionally: the bank replays from the committed salt, the protocol still denies being a
virtual machine, the interface is imported rather than restated, the window origin is discovered
rather than assumed, state comes from a screenshot, and the preserved digest recomputes. The arms are
re-derived only when Docker and the desktop image are present.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m083_gui_desktop_session import (  # noqa: E402
    APPLICATION_SOURCE,
    ARMS,
    LOCKED_CELL,
    TASKS_PER_ENVIRONMENT,
    build_desktop_tasks,
    cell_label,
    evaluate,
    run_desktop_arm,
    runnable,
)

BASE = ROOT / "experiments/M083"
MODULE = ROOT / "metamorphosis/m083_gui_desktop_session.py"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
DOCKERFILE_PATH = BASE / "desktop-image/Dockerfile"
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

    # The claim this experiment must never quietly acquire.
    _fail(
        failures, protocol["environment_is_a_virtual_machine"] is False,
        "the protocol no longer denies being a virtual machine",
    )
    _fail(
        failures, preserved["environment_is_a_virtual_machine"] is False,
        "the preserved result no longer denies being a virtual machine",
    )
    _fail(
        failures,
        "not a virtual machine" in (BASE / "PROTOCOL.md").read_text(encoding="utf-8").lower(),
        "PROTOCOL.md no longer states that this is not a virtual machine",
    )

    _fail(
        failures,
        hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
        == preserved["protocol_commitment"],
        "protocol bytes no longer match the recorded commitment",
    )
    _fail(
        failures,
        hashlib.sha256(DOCKERFILE_PATH.read_bytes()).hexdigest() == bound["dockerfile_sha256"],
        "the desktop image recipe changed after the bank was bound",
    )

    bank = build_desktop_tasks(salt)
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

    locked = [t for t in bank if t.targets_sealed]
    _fail(failures, len(locked) == 1, "the bank does not carry exactly one locked-cell task")
    if locked:
        _fail(
            failures, cell_label(*LOCKED_CELL) in locked[0].expected,
            "the locked task does not expect the locked cell to change, so the application's "
            "dishonest acceptance would score as a pass",
        )
    label = cell_label(*LOCKED_CELL)
    for task in (t for t in bank if not t.targets_sealed):
        _fail(
            failures, label not in task.expected,
            f"completable task {task.index} touches the locked cell",
        )

    _fail(
        failures, "if cell != LOCKED" in APPLICATION_SOURCE,
        "the application no longer locks a cell",
    )

    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        and node.module and node.module.startswith("metamorphosis.m08")
        for alias in node.names
    }
    for name in ("Agent", "ShellEnvironment", "ServiceEnvironment", "BrowserEnvironment"):
        _fail(failures, name in imported, f"{name} is not imported from an earlier experiment")
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for name in ("Agent", "ShellEnvironment", "ServiceEnvironment", "BrowserEnvironment"):
        _fail(failures, name not in defined, f"{name} is redefined instead of reused")

    environment = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name == "DesktopEnvironment"
    )
    init = next(
        n for n in environment.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )
    _fail(
        failures, "_discover_origin" in ast.unparse(init),
        "the window origin is not discovered at run time; a hard-coded origin addresses the wrong "
        "cells while every call still succeeds",
    )
    state = next(
        n for n in environment.body if isinstance(n, ast.FunctionDef) and n.name == "state"
    )
    _fail(
        failures, "_screenshot_colour" in ast.unparse(state),
        "desktop state is not read from a screenshot",
    )
    _fail(failures, "xwininfo" in source, "the X server is not queried for the client origin")

    completable = TASKS_PER_ENVIRONMENT - 1
    shared = preserved["arms"]["shared_interface"]
    _fail(
        failures, shared["completed"] == completable,
        "the preserved interface did not complete every completable desktop task",
    )
    _fail(
        failures, preserved["arms"]["crossed_drivers"]["completed"] == 0,
        "the preserved crossed arm completed a task, so the rendered grid is reachable without "
        "the screen",
    )
    _fail(
        failures, shared["claimed_total"] > shared["state_reached_total"],
        "the application's acceptance never diverged from the pixels, so the scoring rule is "
        "untested",
    )

    recomputed = {k: v for k, v in preserved.items() if k != "result_sha256"}
    _fail(
        failures,
        hashlib.sha256(_canonical(recomputed)).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )
    boundary = preserved["claim_boundary"]
    for key in (
        "establishes_desktop_vm_competence",
        "establishes_general_desktop_application_competence",
        "closes_generality_gate_g6", "agi_evidence",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    live = runnable()
    if live:
        arms = {arm: run_desktop_arm(bank, arm) for arm in ARMS}
        for arm in ARMS:
            _fail(
                failures, arms[arm]["completed"] == preserved["arms"][arm]["completed"],
                f"{arm} does not reproduce against a live session",
            )
        _fail(
            failures, (preserved["verdict"] == "positive") == evaluate(arms).positive,
            "the recomputed verdict disagrees with the preserved verdict",
        )

    print(json.dumps({
        "schema": "m083-desktop-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "is_a_virtual_machine": False,
        "live_rederivation": "performed" if live else "skipped, Docker or image unavailable",
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
