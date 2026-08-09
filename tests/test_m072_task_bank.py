from __future__ import annotations

import pytest

from metamorphosis.m072_task_bank import (
    ALPINE, NETWORK, PYTHON3, READONLY_ALPINE, TASKS, WRITABLE_ALPINE, WRITE_WORKSPACE, BankTask,
    EnvironmentSpec, TaskBankError, matched_pairs, validate_bank,
)
from mira_core.calibration import CapabilityProbe, ProbeVerdict, Solvability
from mira_core.probing import label_task, probe_environment


def test_the_seed_bank_is_balanced_and_paired() -> None:
    validate_bank()
    pairs = matched_pairs()
    assert len(pairs) == 3
    assert len(TASKS) == 6
    feasible = [t for t in TASKS if t.expected_solvability is Solvability.FEASIBLE]
    impossible = [t for t in TASKS if t.expected_solvability is Solvability.CAPABILITY_IMPOSSIBLE]
    assert len(feasible) == len(impossible) == 3


def test_each_pair_holds_one_feasible_and_one_impossible_member() -> None:
    for pair_id, members in matched_pairs().items():
        assert len(members) == 2, pair_id
        assert {m.expected_solvability for m in members} == {
            Solvability.FEASIBLE, Solvability.CAPABILITY_IMPOSSIBLE,
        }


def test_the_permission_pair_holds_difficulty_constant() -> None:
    """Identical image and probe; only the mount differs, so behaviour cannot blame difficulty."""

    members = {t.task_id: t for t in matched_pairs()["write-release-note"]}
    writable = members["write-release-note-writable"]
    readonly = members["write-release-note-readonly"]
    assert writable.environment.image == readonly.environment.image == ALPINE
    assert writable.instruction == readonly.instruction
    assert writable.required_capabilities == readonly.required_capabilities
    assert writable.environment.read_only is False
    assert readonly.environment.read_only is True


def test_every_agent_phase_is_networkless_except_the_declared_network_task() -> None:
    for task in TASKS:
        assert task.environment.network == "none"
    remote = next(t for t in TASKS if t.task_id == "fetch-remote-manifest")
    assert remote.required_capabilities == (NETWORK,)
    assert remote.expected_solvability is Solvability.CAPABILITY_IMPOSSIBLE


def test_images_must_be_pinned_by_digest() -> None:
    with pytest.raises(TaskBankError, match="pinned by repository digest"):
        EnvironmentSpec("floating", "alpine:3.20")
    with pytest.raises(TaskBankError, match="identifier"):
        EnvironmentSpec("", ALPINE)
    with pytest.raises(TaskBankError, match="network"):
        EnvironmentSpec("bad-net", ALPINE, network="host")


def test_docker_argv_reflects_the_declared_configuration() -> None:
    writable = WRITABLE_ALPINE.docker_argv("cc --version")
    readonly = READONLY_ALPINE.docker_argv("cc --version")
    assert "--read-only" not in writable
    assert "--read-only" in readonly
    assert writable == (
        "docker", "run", "--rm", "--network=none", ALPINE, "sh", "-lc", "cc --version",
    )
    assert readonly == (
        "docker", "run", "--rm", "--network=none", "--read-only", ALPINE, "sh", "-lc",
        "cc --version",
    )


def test_an_engine_failure_is_never_certified_as_absence() -> None:
    """Return code 125 is Docker refusing to start, not the capability being missing."""

    def engine_failure(probe: CapabilityProbe) -> tuple[int | None, bool]:
        return None, False

    certificates = probe_environment((PYTHON3,), engine_failure, "alpine-writable")
    assert certificates[0].verdict is ProbeVerdict.INCONCLUSIVE
    label = label_task("t", (PYTHON3,), certificates)
    assert label.solvability is Solvability.UNLABELLED


def test_probed_labels_match_the_banks_expectation_under_recorded_return_codes() -> None:
    """Replays the return codes observed from the real images without needing Docker."""

    observed = {
        ("python-writable", "python3"): 0,
        ("alpine-writable", "python3"): 127,
        ("alpine-writable", "write_workspace"): 0,
        ("alpine-readonly", "write_workspace"): 1,
        ("alpine-writable", "network"): 1,
    }
    for task in TASKS:
        def replay(probe: CapabilityProbe, task=task) -> tuple[int | None, bool]:
            return observed[(task.environment.environment_id, probe.capability_id)], True

        certificates = probe_environment(
            task.required_capabilities, replay, task.environment.environment_id,
        )
        label = label_task(task.task_id, task.required_capabilities, certificates)
        assert label.solvability is task.expected_solvability, task.task_id


def test_bank_validation_rejects_an_unpaired_or_uncontrasted_pair() -> None:
    lonely = BankTask(
        "solo", "solo-pair", "do a thing", (WRITE_WORKSPACE,), WRITABLE_ALPINE,
        Solvability.FEASIBLE,
    )
    with pytest.raises(TaskBankError):
        BankTask(
            "bad", "p", "x", (), WRITABLE_ALPINE, Solvability.FEASIBLE,
        )
    with pytest.raises(TaskBankError):
        BankTask(
            "bad", "p", "x", (WRITE_WORKSPACE,), WRITABLE_ALPINE, Solvability.UNLABELLED,
        )
    assert lonely.pair_id == "solo-pair"
