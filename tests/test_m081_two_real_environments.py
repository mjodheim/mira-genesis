"""Regressions for M081 one interface across two real isolated environments.

Everything that needs a live container is gated behind MIRA_RUN_DOCKER_TESTS=1, the same opt-in the
repository already uses. The structural tests below run everywhere and cover the parts that decide
whether the result means anything: the bank construction, the frozen boundaries and the preserved
artifacts.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from metamorphosis.m081_two_real_environments import (
    ACTIONS,
    ALPINE_IMAGE,
    ARMS,
    ENVIRONMENTS,
    PYTHON_IMAGE,
    TASKS_PER_ENVIRONMENT,
    Action,
    EnvironmentError_,
    Task,
    build_bank,
    build_tasks,
    docker_available,
    evaluate,
    run_arm,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M081"
MODULE = ROOT / "metamorphosis/m081_two_real_environments.py"

requires_docker = pytest.mark.skipif(
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
    return build_bank(salt)


def test_bank_shape_and_determinism(salt: bytes, bank: tuple[Task, ...]) -> None:
    assert len(bank) == TASKS_PER_ENVIRONMENT * len(ENVIRONMENTS)
    assert [t.commitment() for t in build_bank(salt)] == [t.commitment() for t in bank]


def test_bank_matches_the_bound_commitment(bank: tuple[Task, ...]) -> None:
    bound = json.loads((BASE / "BANK_COMMITMENT.json").read_text(encoding="utf-8"))
    assert [t.commitment() for t in bank] == [r["commitment"] for r in bound["tasks"]]


def test_both_environments_receive_the_same_task_count(bank: tuple[Task, ...]) -> None:
    for kind in ENVIRONMENTS:
        assert sum(1 for t in bank if t.environment == kind) == TASKS_PER_ENVIRONMENT


def test_exactly_one_sealed_task_per_environment(bank: tuple[Task, ...]) -> None:
    for kind in ENVIRONMENTS:
        sealed = [t for t in bank if t.environment == kind and t.targets_sealed]
        assert len(sealed) == 1


def test_the_sealed_task_expects_its_resource(bank: tuple[Task, ...]) -> None:
    """Otherwise the silent discard is scored as a pass and the self-report clause is untested."""

    for task in (t for t in bank if t.targets_sealed):
        assert task.expected
        assert all(name.startswith("sealed-") for name in task.expected)


def test_the_action_vocabulary_is_identical_across_environments(salt: bytes) -> None:
    """One interface means one vocabulary; the drivers differ, the actions do not."""

    vocabularies = {
        kind: {action.kind for task in build_tasks(salt, kind) for action in task.actions}
        for kind in ENVIRONMENTS
    }
    assert vocabularies["shell"] == vocabularies["service"]
    assert vocabularies["shell"] <= set(ACTIONS)


def test_the_agent_cannot_branch_on_the_environment() -> None:
    """The agent must not name an environment or inspect a driver's kind."""

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    agent = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "Agent"
    )
    source = ast.unparse(agent)
    assert "shell" not in source
    assert "service" not in source
    assert ".kind" not in source


def test_images_are_digest_pinned(protocol: dict) -> None:
    for image in (ALPINE_IMAGE, PYTHON_IMAGE):
        assert "@sha256:" in image
    assert protocol["environments"]["shell"]["image"] == ALPINE_IMAGE
    assert protocol["environments"]["service"]["image"] == PYTHON_IMAGE


def test_isolation_declarations_are_present(protocol: dict) -> None:
    isolation = protocol["isolation"]
    assert isolation["network_disabled_for_shell_environment"] is True
    assert isolation["service_environment_publishes_loopback_only"] is True
    assert isolation["host_repository_mounted"] is False
    assert isolation["docker_socket_mounted"] is False
    assert isolation["credentials_mounted"] is False


def test_unknown_action_and_arm_are_rejected(bank: tuple[Task, ...]) -> None:
    with pytest.raises(EnvironmentError_):
        Action("teleport", "x")
    with pytest.raises(EnvironmentError_):
        run_arm(bank, "hopeful")


def test_amendment_is_recorded_as_pre_materialization(protocol: dict) -> None:
    amendments = protocol["amendments"]
    assert amendments
    for amendment in amendments:
        assert amendment["applied_before_bank_materialization"] is True
        assert amendment["applied_before_any_recorded_result"] is True
        assert amendment["reason"]
        assert amendment["direction"].startswith("strengthens")


def test_evaluation_rejects_a_crossing_that_still_completes() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    degraded = {arm: dict(preserved["arms"][arm]) for arm in ARMS}
    degraded["crossed_drivers"]["completed_total"] = 3
    verdict = evaluate(degraded)
    assert verdict.positive is False
    assert any("genuinely distinct" in reason for reason in verdict.reasons)


def test_evaluation_rejects_a_self_report_arm_that_never_diverges() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    degraded = {arm: dict(preserved["arms"][arm]) for arm in ARMS}
    degraded["self_report_scored"]["overcount"] = 0
    verdict = evaluate(degraded)
    assert verdict.positive is False


def test_preserved_result_records_the_divergence() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert preserved["verdict"] == "positive"
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False
    assert preserved["arms"]["crossed_drivers"]["completed_total"] == 0
    assert preserved["arms"]["self_report_scored"]["overcount"] >= len(ENVIRONMENTS)
    assert preserved["arms"]["shared_interface"]["state_reached_total"] == (
        (TASKS_PER_ENVIRONMENT - 1) * len(ENVIRONMENTS)
    )


def test_preserved_result_shows_self_report_exceeding_state() -> None:
    """The point of the whole scoring clause, pinned as a number."""

    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    shared = preserved["arms"]["shared_interface"]
    assert shared["claimed_total"] > shared["state_reached_total"]


def test_construction_fixes_stay_visible() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert len(preserved["construction_fixes_before_materialization"]) == 2


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["establishes_browser_competence"] is False
    assert boundary["establishes_desktop_or_vm_competence"] is False
    assert boundary["closes_generality_gate_g6"] is False
    assert boundary["agi_evidence"] is False
    assert "browser competence" in protocol["explicitly_not_addressed"]


@requires_docker
def test_docker_is_reachable_when_opted_in() -> None:
    assert docker_available()


@requires_docker
def test_shared_interface_reaches_state_in_both_environments(bank: tuple[Task, ...]) -> None:
    record = run_arm(bank, "shared_interface")
    completable = TASKS_PER_ENVIRONMENT - 1
    for kind in ENVIRONMENTS:
        assert record["completed_per_environment"][kind] == completable


@requires_docker
def test_crossed_drivers_complete_nothing(bank: tuple[Task, ...]) -> None:
    assert run_arm(bank, "crossed_drivers")["completed_total"] == 0
