from __future__ import annotations

from dataclasses import replace

import pytest

from metamorphosis.m074_task_bank import (
    ALPINE, PYTHON3, READONLY_WORKSPACE_ALPINE, READ_REQUIRED_FILE, TASKS, WRITABLE_ALPINE,
    WRITE_WORKSPACE, BankTask, EnvironmentSpec, FixtureFile, TaskBankError, matched_pairs,
    task_by_id, validate_bank,
)
from mira_core.calibration import CapabilityProbe, ProbeVerdict, Solvability
from mira_core.probing import label_task, probe_environment


def test_the_seed_bank_is_balanced_and_paired() -> None:
    validate_bank()
    pairs = matched_pairs()
    assert len(pairs) == 3
    assert len(TASKS) == 6
    feasible = [task for task in TASKS if task.expected_solvability is Solvability.FEASIBLE]
    impossible = [
        task for task in TASKS
        if task.expected_solvability is Solvability.CAPABILITY_IMPOSSIBLE
    ]
    assert len(feasible) == len(impossible) == 3


def test_each_pair_changes_environment_not_task_contract() -> None:
    for pair_id, members in matched_pairs().items():
        assert len(members) == 2, pair_id
        first, second = members
        assert {member.expected_solvability for member in members} == {
            Solvability.FEASIBLE, Solvability.CAPABILITY_IMPOSSIBLE,
        }
        assert first.instruction == second.instruction
        assert first.solve_script == second.solve_script
        assert first.evaluator_script == second.evaluator_script
        assert [p.public_dict() for p in first.required_capabilities] == [
            p.public_dict() for p in second.required_capabilities
        ]
        assert first.environment_digest() != second.environment_digest()


def test_the_permission_pair_changes_only_workspace_writability() -> None:
    members = {task.task_id: task for task in matched_pairs()["write-release-note"]}
    writable = members["write-release-note-writable"]
    readonly = members["write-release-note-readonly"]
    assert writable.environment.image == readonly.environment.image == ALPINE
    assert writable.fixture_files == readonly.fixture_files == ()
    assert writable.environment.workspace_writable is True
    assert readonly.environment.workspace_writable is False


def test_every_agent_phase_is_networkless_and_non_root() -> None:
    for task in TASKS:
        public = task.environment.public_dict()
        assert task.environment.network == "none"
        assert task.environment.agent_uid != 0 and task.environment.agent_gid != 0
        assert public["root_filesystem_read_only"] is True
        assert public["capabilities"] == "drop_all"
        assert public["no_new_privileges"] is True


def test_images_and_environment_contracts_fail_closed() -> None:
    with pytest.raises(TaskBankError, match="pinned by repository digest"):
        EnvironmentSpec("floating", "alpine:3.20")
    with pytest.raises(TaskBankError, match="identifier"):
        EnvironmentSpec("", ALPINE)
    with pytest.raises(TaskBankError, match="networkless"):
        EnvironmentSpec("bad-net", ALPINE, network="bridge")
    with pytest.raises(TaskBankError, match="normalized"):
        FixtureFile("../escape", "x")
    with pytest.raises(TaskBankError, match="normalized"):
        FixtureFile("nested\\windows-path", "x")


def test_docker_start_argv_realizes_the_declared_security_boundary() -> None:
    argv = WRITABLE_ALPINE.docker_start_argv("mira-test")
    assert argv[:6] == ("docker", "run", "--detach", "--rm", "--name", "mira-test")
    assert "--network=none" in argv
    assert "--read-only" in argv
    assert "--cap-drop=ALL" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "--tmpfs" in argv
    assert "/workspace:rw,nosuid,nodev,noexec,size=16777216" in argv
    assert argv[-3:] == (ALPINE, "sleep", "infinity")


def test_environment_digest_binds_fixture_bytes_modes_and_container_config() -> None:
    readable = task_by_id("read-manifest-readable")
    unreadable = task_by_id("read-manifest-unreadable")
    assert readable.environment_digest() != unreadable.environment_digest()
    changed_content = replace(
        readable,
        fixture_files=(FixtureFile("manifest.json", '{"version":"changed"}\n', 0o444),),
    )
    assert changed_content.environment_digest() != readable.environment_digest()
    assert len(readable.environment_digest()) == 64
    assert len(readable.task_digest()) == 64


def test_an_engine_failure_is_never_certified_as_absence() -> None:
    task = task_by_id("run-analysis-python-absent")

    def engine_failure(probe: CapabilityProbe) -> tuple[int | None, bool]:
        return None, False

    certificates = probe_environment(
        (PYTHON3,), engine_failure, task.environment.environment_id,
        task.environment_digest(),
    )
    assert certificates[0].verdict is ProbeVerdict.INCONCLUSIVE
    assert label_task("t", (PYTHON3,), certificates).solvability is Solvability.UNLABELLED


def test_probed_labels_match_the_bank_expectation_under_recorded_return_codes() -> None:
    observed = {
        "run-analysis-python-present": 0,
        "run-analysis-python-absent": 127,
        "write-release-note-writable": 0,
        "write-release-note-readonly": 1,
        "read-manifest-readable": 0,
        "read-manifest-unreadable": 1,
    }
    for task in TASKS:
        certificates = probe_environment(
            task.required_capabilities,
            lambda probe, task=task: (observed[task.task_id], True),
            task.environment.environment_id, task.environment_digest(),
        )
        label = label_task(task.task_id, task.required_capabilities, certificates)
        assert label.solvability is task.expected_solvability, task.task_id


def test_bank_validation_uses_the_supplied_bank_not_the_global_default() -> None:
    source = task_by_id("write-release-note-writable")
    lonely = replace(source, task_id="solo", pair_id="solo-pair")
    with pytest.raises(TaskBankError, match="exactly two"):
        validate_bank((lonely,))
    with pytest.raises(TaskBankError, match="capabilities it requires"):
        BankTask(
            "bad", "p", "x", (), WRITABLE_ALPINE, (), "true", "true",
            Solvability.FEASIBLE,
        )


def test_declared_probes_target_the_actual_task_boundary() -> None:
    assert "/workspace" in " ".join(WRITE_WORKSPACE.argv)
    assert "/workspace/manifest.json" in " ".join(READ_REQUIRED_FILE.argv)
    assert "/tmp" not in " ".join(WRITE_WORKSPACE.argv)
