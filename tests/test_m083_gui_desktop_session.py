"""Regressions for M083, a GUI desktop session as a fourth environment.

Container-backed tests are gated behind MIRA_RUN_DOCKER_TESTS=1. The structural tests run everywhere
and cover what decides whether the result means anything: that the interface is imported rather than
restated, that the window origin is discovered rather than assumed, that state comes from a
screenshot, and that the protocol keeps saying this is not a virtual machine.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from metamorphosis.m081_two_real_environments import Task
from metamorphosis.m083_gui_desktop_session import (
    ARMS,
    COLUMNS,
    DESKTOP_IMAGE,
    LOCKED_CELL,
    PALETTE,
    PALETTE_ORDER,
    ROWS,
    TASKS_PER_ENVIRONMENT,
    DesktopEnvironment,
    EnvironmentError_,
    build_desktop_tasks,
    cell_label,
    evaluate,
    image_present,
    open_environment,
    parse_cell,
    run_desktop_arm,
    runnable,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M083"
MODULE = ROOT / "metamorphosis/m083_gui_desktop_session.py"

requires_desktop = pytest.mark.skipif(
    os.getenv("MIRA_RUN_DOCKER_TESTS") != "1",
    reason="real Docker integration is opt-in",
)


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def bank(salt: bytes) -> tuple[Task, ...]:
    return build_desktop_tasks(salt)


def test_the_protocol_denies_being_a_virtual_machine(protocol: dict) -> None:
    """The clause this experiment must never quietly acquire."""

    assert protocol["environment_is_a_virtual_machine"] is False
    assert protocol["claim_boundary"]["establishes_desktop_vm_competence"] is False
    assert "desktop VM competence" in protocol["explicitly_not_addressed"]
    assert "virtual machine" in protocol["why_not_a_virtual_machine"]
    text = (BASE / "PROTOCOL.md").read_text(encoding="utf-8")
    assert "not a virtual machine" in text.lower()


def test_bank_shape_and_determinism(salt: bytes, bank: tuple[Task, ...]) -> None:
    assert len(bank) == TASKS_PER_ENVIRONMENT
    assert [t.commitment() for t in build_desktop_tasks(salt)] == [t.commitment() for t in bank]


def test_bank_matches_the_bound_commitment(bank: tuple[Task, ...]) -> None:
    bound = json.loads((BASE / "BANK_COMMITMENT.json").read_text(encoding="utf-8"))
    assert [t.commitment() for t in bank] == [r["commitment"] for r in bound["tasks"]]


def test_exactly_one_task_targets_the_locked_cell(bank: tuple[Task, ...]) -> None:
    locked = [t for t in bank if t.targets_sealed]
    assert len(locked) == 1
    assert cell_label(*LOCKED_CELL) in locked[0].expected


def test_no_completable_task_touches_the_locked_cell(bank: tuple[Task, ...]) -> None:
    label = cell_label(*LOCKED_CELL)
    for task in (t for t in bank if not t.targets_sealed):
        assert label not in task.expected


def test_tasks_stay_inside_the_grid(bank: tuple[Task, ...]) -> None:
    for task in bank:
        for name, colour in task.expected.items():
            row, column = parse_cell(name)
            assert 0 <= row < ROWS and 0 <= column < COLUMNS
            assert colour in PALETTE


def test_palette_colours_are_distinct_and_not_the_background() -> None:
    assert len(set(PALETTE.values())) == len(PALETTE)
    assert "#101010" not in PALETTE.values()
    assert tuple(PALETTE_ORDER) == tuple(sorted(PALETTE_ORDER, key=PALETTE_ORDER.index))


def test_the_interface_is_imported_not_restated() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        and node.module and node.module.startswith("metamorphosis.m08")
        for alias in node.names
    }
    assert {"Agent", "ShellEnvironment", "ServiceEnvironment", "BrowserEnvironment"} <= imported
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for name in ("Agent", "ShellEnvironment", "ServiceEnvironment", "BrowserEnvironment"):
        assert name not in defined


def test_the_window_origin_is_discovered_not_assumed() -> None:
    """A hard-coded origin addresses the wrong cells while every call still succeeds."""

    source = MODULE.read_text(encoding="utf-8")
    assert "xwininfo" in source
    assert "_discover_origin" in source
    tree = ast.parse(source)
    environment = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name == "DesktopEnvironment"
    )
    init = next(n for n in environment.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    assert "_discover_origin" in ast.unparse(init)


def test_state_is_read_from_a_screenshot() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    environment = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name == "DesktopEnvironment"
    )
    state = next(n for n in environment.body if isinstance(n, ast.FunctionDef) and n.name == "state")
    assert "_screenshot_colour" in ast.unparse(state)
    assert "import -window root" in source


def test_container_commands_are_wrapped_against_msys_path_conversion() -> None:
    source = MODULE.read_text(encoding="utf-8")
    assert '"sh", "-c"' in source


def test_the_application_locks_exactly_one_cell() -> None:
    from metamorphosis.m083_gui_desktop_session import APPLICATION_SOURCE

    assert "LOCKED" in APPLICATION_SOURCE
    assert "if cell != LOCKED" in APPLICATION_SOURCE


def test_parse_cell_rejects_nonsense() -> None:
    assert parse_cell("r2c3") == (2, 3)
    with pytest.raises(EnvironmentError_):
        parse_cell("somewhere")


def test_unknown_environment_and_arm_are_rejected(bank: tuple[Task, ...]) -> None:
    with pytest.raises(EnvironmentError_):
        open_environment("hologram")
    with pytest.raises(EnvironmentError_):
        run_desktop_arm(bank, "hopeful")


def test_preserved_result_is_positive_and_single_attempt() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["verdict"] == "positive"
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["environment_is_a_virtual_machine"] is False


def test_preserved_interface_completed_every_completable_task() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["arms"]["shared_interface"]["completed"] == TASKS_PER_ENVIRONMENT - 1


def test_preserved_crossed_arm_completed_nothing() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["arms"]["crossed_drivers"]["completed"] == 0


def test_preserved_self_report_diverges_from_pixels() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    shared = preserved["arms"]["shared_interface"]
    assert shared["claimed_total"] > shared["state_reached_total"]
    assert shared["overcount"] >= 1


def test_evaluation_rejects_a_crossing_that_reaches_the_grid() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    degraded = {arm: dict(preserved["arms"][arm]) for arm in ARMS}
    degraded["crossed_drivers"]["completed"] = 2
    verdict = evaluate(degraded)
    assert verdict.positive is False
    assert any("without the screen" in reason for reason in verdict.reasons)


def test_evaluation_rejects_an_honest_locked_cell() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    degraded = {arm: dict(preserved["arms"][arm]) for arm in ARMS}
    degraded["self_report_scored"] = dict(degraded["self_report_scored"])
    degraded["self_report_scored"]["overcount"] = 0
    assert evaluate(degraded).positive is False


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["establishes_general_desktop_application_competence"] is False
    assert boundary["closes_generality_gate_g6"] is False
    assert boundary["agi_evidence"] is False


@requires_desktop
def test_desktop_image_is_present() -> None:
    assert image_present()
    assert runnable()


@requires_desktop
def test_the_session_discovers_its_origin_and_the_locked_cell_never_changes() -> None:
    from metamorphosis.m081_two_real_environments import Action

    environment = DesktopEnvironment()
    try:
        assert environment.origin != (0, 0)
        assert environment.state() == {}
        assert environment.apply(Action("put", "r0c0", "cyan")) is True
        assert environment.state().get("r0c0") == "cyan"
        locked = cell_label(*LOCKED_CELL)
        assert environment.apply(Action("put", locked, "magenta")) is True
        assert locked not in environment.state()
    finally:
        environment.close()
