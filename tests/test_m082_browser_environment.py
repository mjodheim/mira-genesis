"""Regressions for M082, a real browser under M081's unchanged interface.

Container-backed tests are gated behind MIRA_RUN_DOCKER_TESTS=1, the repository's existing opt-in.
The structural tests run everywhere and cover what decides whether the result means anything: that
the interface is imported rather than restated, that the browser store has no HTTP route, and that
the preserved artifacts say what they claim.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from metamorphosis import m081_two_real_environments as m081
from metamorphosis.m082_browser_environment import (
    ARMS,
    BROWSER_BASE_DIGEST,
    BROWSER_IMAGE,
    DRIVER_SOURCE,
    ENVIRONMENTS,
    PAGE_SOURCE,
    Action,
    BrowserEnvironment,
    EnvironmentError_,
    build_bank,
    evaluate,
    image_present,
    open_environment,
    run_arm,
    runnable,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M082"
MODULE = ROOT / "metamorphosis/m082_browser_environment.py"

requires_browser = pytest.mark.skipif(
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
def bank(salt: bytes) -> tuple:
    return build_bank(salt)


def test_three_environments_each_receive_a_full_task_set(bank: tuple) -> None:
    assert len(ENVIRONMENTS) == 3
    for kind in ENVIRONMENTS:
        assert sum(1 for t in bank if t.environment == kind) == m081.TASKS_PER_ENVIRONMENT


def test_bank_is_deterministic_and_matches_the_commitment(salt: bytes, bank: tuple) -> None:
    assert [t.commitment() for t in build_bank(salt)] == [t.commitment() for t in bank]
    bound = json.loads((BASE / "BANK_COMMITMENT.json").read_text(encoding="utf-8"))
    assert [t.commitment() for t in bank] == [r["commitment"] for r in bound["tasks"]]


def test_the_interface_is_imported_not_restated() -> None:
    """A three-environment claim is only meaningful if one interface object drives all three."""

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        and node.module == "metamorphosis.m081_two_real_environments"
        for alias in node.names
    }
    assert {"Agent", "ShellEnvironment", "ServiceEnvironment", "Action"} <= imported
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    assert "Agent" not in defined
    assert "ShellEnvironment" not in defined
    assert "ServiceEnvironment" not in defined


def test_the_browser_store_has_no_http_route() -> None:
    """Without this the browser is the M081 service in a costume."""

    assert "localStorage" in PAGE_SOURCE
    # The page's only server is a static handler; no route reads or writes the store.
    assert "/store" not in DRIVER_SOURCE
    assert DRIVER_SOURCE.count("createServer") == 1
    assert "res.end(PAGE)" in DRIVER_SOURCE


def test_browser_state_is_read_from_the_rendered_dom() -> None:
    assert "$$eval('li'" in DRIVER_SOURCE
    assert "localStorage.getItem" not in DRIVER_SOURCE.split("const state")[1]


def test_the_driver_uses_a_persistent_profile() -> None:
    """A fresh profile per action would leave the harness holding the state, not the browser."""

    assert "launchPersistentContext" in DRIVER_SOURCE
    assert "chromium.launch()" not in DRIVER_SOURCE


def test_container_commands_are_wrapped_against_msys_path_conversion() -> None:
    """The defect class that produced the negative M070."""

    source = MODULE.read_text(encoding="utf-8")
    assert '"sh", "-c"' in source
    tree = ast.parse(source)
    exec_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and ast.unparse(node).startswith("subprocess.run")
    ]
    for call in exec_calls:
        rendered = ast.unparse(call)
        if '"docker", "exec"' in rendered or "'docker', 'exec'" in rendered:
            assert "sh" in rendered and "-c" in rendered


def test_the_page_confirms_a_save_it_declines() -> None:
    """The browser's version of the swallowed shell write and the discarded 204."""

    assert "sealed-" in PAGE_SOURCE
    assert "'saved'" in PAGE_SOURCE


def test_the_browser_image_derives_from_a_pinned_base(protocol: dict) -> None:
    assert "@sha256:" in BROWSER_BASE_DIGEST
    dockerfile = (BASE / "browser-image/Dockerfile").read_text(encoding="utf-8")
    assert BROWSER_BASE_DIGEST.split("@")[1] in dockerfile
    assert protocol["browser_environment"]["derived_image_tag"] == BROWSER_IMAGE
    assert protocol["browser_environment"]["network_disabled_at_run_time"] is True


def test_unknown_environment_and_arm_are_rejected(bank: tuple) -> None:
    with pytest.raises(EnvironmentError_):
        open_environment("hologram")
    with pytest.raises(EnvironmentError_):
        run_arm(bank, "hopeful")


def test_preserved_result_covers_three_environments() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    shared = preserved["arms"]["shared_interface"]
    completable = m081.TASKS_PER_ENVIRONMENT - 1
    assert shared["environments_covered"] == 3
    for kind in ENVIRONMENTS:
        assert shared["completed_per_environment"][kind] == completable
    assert preserved["verdict"] == "positive"
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False


def test_preserved_crossed_arm_completes_nothing() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["arms"]["crossed_drivers"]["completed_total"] == 0


def test_preserved_browser_self_report_diverges() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["arms"]["shared_interface"]["browser_overcount"] >= 1


def test_transport_defects_stay_visible() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert len(preserved["transport_defects_found_and_fixed"]) == 3


def test_evaluation_rejects_a_crossing_that_reaches_the_browser_store() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    degraded = {arm: dict(preserved["arms"][arm]) for arm in ARMS}
    degraded["crossed_drivers"]["completed_total"] = 2
    verdict = evaluate(degraded)
    assert verdict.positive is False
    assert any("without the DOM" in reason for reason in verdict.reasons)


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["establishes_desktop_or_vm_competence"] is False
    assert boundary["establishes_general_web_competence"] is False
    assert boundary["closes_generality_gate_g6"] is False
    assert boundary["agi_evidence"] is False
    assert "desktop VM competence" in protocol["explicitly_not_addressed"]


@requires_browser
def test_browser_image_is_present() -> None:
    assert image_present()
    assert runnable()


@requires_browser
def test_the_browser_persists_state_and_lies_about_the_sealed_save() -> None:
    environment = BrowserEnvironment()
    try:
        assert environment.state() == {}
        assert environment.apply(Action("put", "alpha", "bonjour")) is True
        assert environment.state() == {"alpha": "bonjour"}
        # The page confirms this save and does not keep it.
        assert environment.apply(Action("put", "sealed-x", "nope")) is True
        assert "sealed-x" not in environment.state()
    finally:
        environment.close()
