from __future__ import annotations

from metamorphosis.m074_task_bank import TASKS as M074_TASKS, matched_pairs
from metamorphosis.m075_development_bank import (
    NODE_ALPINE, NODE_RUNTIME, TASKS, validate_development_bank,
)
from mira_core.calibration import Solvability


def test_public_development_bank_is_balanced_and_matched() -> None:
    validate_development_bank()
    pairs = matched_pairs(TASKS)
    assert len(pairs) == 3
    for members in pairs.values():
        assert {task.expected_solvability for task in members} == {
            Solvability.FEASIBLE, Solvability.CAPABILITY_IMPOSSIBLE,
        }
        assert members[0].instruction == members[1].instruction
        assert members[0].solve_script == members[1].solve_script
        assert members[0].evaluator_script == members[1].evaluator_script


def test_bank_is_distinct_from_m074_and_declared_public_development_only() -> None:
    assert {task.task_id for task in TASKS}.isdisjoint(task.task_id for task in M074_TASKS)
    assert {task.task_digest() for task in TASKS}.isdisjoint(
        task.task_digest() for task in M074_TASKS
    )


def test_node_pair_binds_the_official_digest_and_explicit_absence_code() -> None:
    assert NODE_ALPINE == (
        "node@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32"
    )
    assert NODE_RUNTIME.present_returncodes == (0,)
    assert NODE_RUNTIME.absent_returncodes == (127,)


def test_every_development_environment_retains_the_closed_boundary() -> None:
    for task in TASKS:
        environment = task.environment.public_dict()
        assert environment["network"] == "none"
        assert environment["root_filesystem_read_only"] is True
        assert environment["capabilities"] == "drop_all"
        assert environment["no_new_privileges"] is True
        assert environment["agent_uid"] == environment["agent_gid"] == 65534
