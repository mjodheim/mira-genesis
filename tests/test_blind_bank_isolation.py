"""The technical boundary a blind generator runs behind, attacked the ways it would really fail.

Not "does the checker read a boolean" — the attestation carries `repository_mounted: false` and a
dishonest one would too. These tests attack the argv, which is the thing that actually determined
what the container could see.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from metamorphosis.blind_bank_isolation import (
    CONTAINER_OUTPUT_DIRECTORY,
    IsolationError,
    PERMITTED_ENVIRONMENT_KEYS,
    audit_environment,
    audit_invocation_argv,
    audit_mounts,
    build_attestation,
    plan_invocation,
    validate_attestation,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> dict[str, Path]:
    repository = tmp_path / "repository"
    (repository / "experiments").mkdir(parents=True)
    (repository / "experiments" / "note.txt").write_text("content", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    request = outside / "request.json"
    request.write_text("{}", encoding="utf-8")
    output = outside / "out"
    output.mkdir()
    return {"repository": repository, "request": request, "output": output, "outside": outside}


def _environment() -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "BLIND_BANK_INPUT": "/blind/input/request.json",
        "BLIND_BANK_OUTPUT": str(CONTAINER_OUTPUT_DIRECTORY),
    }


def _plan(workspace: dict[str, Path], **overrides: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "repository_root": workspace["repository"],
        "image_reference": "localhost/blind-generator",
        "image_digest_sha256": "0" * 64,
        "input_path": workspace["request"],
        "output_directory": workspace["output"],
        "environment": _environment(),
        "command": ["/usr/local/bin/emit-bank"],
    }
    arguments.update(overrides)
    return plan_invocation(**arguments)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------------------------


def test_a_clean_environment_passes(workspace: dict[str, Path]) -> None:
    assert audit_environment(_environment(), repository_root=workspace["repository"]) == []


def test_a_non_allowlisted_environment_key_is_reported(workspace: dict[str, Path]) -> None:
    environment = _environment() | {"OPENAI_API_KEY": "value"}
    problems = audit_environment(environment, repository_root=workspace["repository"])
    assert any("not on the allowlist" in problem for problem in problems)


def test_an_allowlisted_key_pointing_at_the_repository_is_reported(
    workspace: dict[str, Path],
) -> None:
    # `HOME` is on the allowlist. `HOME` pointing at the checkout is the same leak as a variable
    # called `MIRA_ROOT`, and a name-only allowlist would not catch it.
    environment = _environment() | {"HOME": str(workspace["repository"])}
    problems = audit_environment(environment, repository_root=workspace["repository"])
    assert any("resolves inside the repository" in problem for problem in problems)


def test_a_path_entry_reaching_into_the_repository_is_reported(
    workspace: dict[str, Path],
) -> None:
    import os

    environment = _environment()
    environment["PATH"] = os.pathsep.join(
        ["/usr/bin", str(workspace["repository"] / "experiments")]
    )
    problems = audit_environment(environment, repository_root=workspace["repository"])
    assert any("resolves inside the repository" in problem for problem in problems)


def test_an_environment_value_naming_the_project_is_reported(
    workspace: dict[str, Path],
) -> None:
    environment = _environment() | {"TZ": "the m075 refusal study"}
    problems = audit_environment(environment, repository_root=workspace["repository"])
    assert any("names project context" in problem for problem in problems)


def test_the_allowlist_carries_no_credential_shaped_key() -> None:
    for key in PERMITTED_ENVIRONMENT_KEYS:
        assert not any(
            marker in key.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD", "CRED")
        )


# ---------------------------------------------------------------------------------------------
# mounts
# ---------------------------------------------------------------------------------------------


def test_a_mount_of_the_repository_is_reported(workspace: dict[str, Path]) -> None:
    mounts = [{"source": str(workspace["repository"]), "target": "/repo", "mode": "ro"}]
    problems = audit_mounts(mounts, repository_root=workspace["repository"])
    assert any("resolves into or above the repository" in problem for problem in problems)


def test_a_mount_of_a_repository_subdirectory_is_reported(workspace: dict[str, Path]) -> None:
    mounts = [{
        "source": str(workspace["repository"] / "experiments"), "target": "/x", "mode": "ro",
    }]
    problems = audit_mounts(mounts, repository_root=workspace["repository"])
    assert any("resolves into or above the repository" in problem for problem in problems)


def test_a_relative_mount_escaping_into_the_repository_is_reported(
    workspace: dict[str, Path],
) -> None:
    # A substring test on the source string would pass this. Resolution does not.
    escaping = str(workspace["outside"] / ".." / "repository" / "experiments")
    problems = audit_mounts(
        [{"source": escaping, "target": "/x", "mode": "ro"}],
        repository_root=workspace["repository"],
    )
    assert any("resolves into or above the repository" in problem for problem in problems)


def test_a_mount_of_the_repository_parent_is_reported(workspace: dict[str, Path]) -> None:
    mounts = [{"source": str(workspace["repository"].parent), "target": "/x", "mode": "ro"}]
    problems = audit_mounts(mounts, repository_root=workspace["repository"])
    assert any("resolves into or above the repository" in problem for problem in problems)


# ---------------------------------------------------------------------------------------------
# the planner
# ---------------------------------------------------------------------------------------------


def test_a_clean_plan_is_produced(workspace: dict[str, Path]) -> None:
    plan = _plan(workspace)
    assert plan["argv"][:3] == ["docker", "run", "--rm"]
    assert "--network=none" in plan["argv"]
    assert audit_invocation_argv(
        plan["argv"], repository_root=workspace["repository"],  # type: ignore[arg-type]
    ) == []


def test_the_planner_refuses_an_input_inside_the_repository(
    workspace: dict[str, Path],
) -> None:
    intruder = workspace["repository"] / "request.json"
    intruder.write_text("{}", encoding="utf-8")
    with pytest.raises(IsolationError, match="resolves into or above the repository"):
        _plan(workspace, input_path=intruder)


def test_the_planner_refuses_a_non_allowlisted_environment(
    workspace: dict[str, Path],
) -> None:
    with pytest.raises(IsolationError, match="not on the allowlist"):
        _plan(workspace, environment=_environment() | {"GITHUB_TOKEN": "value"})


def test_the_planner_refuses_a_non_empty_output_directory(
    workspace: dict[str, Path],
) -> None:
    (workspace["output"] / "previous.json").write_text("{}", encoding="utf-8")
    with pytest.raises(IsolationError, match="output directory is not empty"):
        _plan(workspace)


def test_the_plan_pins_the_image_by_digest(workspace: dict[str, Path]) -> None:
    plan = _plan(workspace)
    assert plan["argv"][-2].endswith("@sha256:" + "0" * 64)  # type: ignore[index]


# ---------------------------------------------------------------------------------------------
# argv audit, independent of the planner
# ---------------------------------------------------------------------------------------------


def test_a_hand_written_argv_mounting_the_repository_is_reported(
    workspace: dict[str, Path],
) -> None:
    argv = [
        "docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=512",
        "--mount", f"type=bind,source={workspace['repository']},target=/repo,readonly",
        "image@sha256:" + "0" * 64, "run",
    ]
    problems = audit_invocation_argv(argv, repository_root=workspace["repository"])
    assert any("from the repository" in problem for problem in problems)


def test_a_posix_style_volume_of_the_repository_is_reported(
    workspace: dict[str, Path],
) -> None:
    argv = [
        "docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=512",
        "-v", f"{workspace['repository']}:/repo:ro",
        "image@sha256:" + "0" * 64, "run",
    ]
    problems = audit_invocation_argv(argv, repository_root=workspace["repository"])
    assert any("from the repository" in problem for problem in problems)


def test_an_argv_enabling_a_network_is_reported(workspace: dict[str, Path]) -> None:
    plan = _plan(workspace)
    argv = ["--network=bridge" if token == "--network=none" else token
            for token in plan["argv"]]  # type: ignore[union-attr]
    problems = audit_invocation_argv(argv, repository_root=workspace["repository"])
    assert any("enables a network" in problem for problem in problems)
    assert any("missing --network=none" in problem for problem in problems)


def test_an_argv_raising_privileges_is_reported(workspace: dict[str, Path]) -> None:
    plan = _plan(workspace)
    argv = list(plan["argv"]) + ["--privileged"]  # type: ignore[arg-type]
    problems = audit_invocation_argv(argv, repository_root=workspace["repository"])
    assert any("raises container privileges" in problem for problem in problems)


def test_an_argv_smuggling_a_credential_is_reported(workspace: dict[str, Path]) -> None:
    plan = _plan(workspace)
    argv = list(plan["argv"]) + ["--env", "GH_TOKEN=value"]  # type: ignore[arg-type]
    problems = audit_invocation_argv(argv, repository_root=workspace["repository"])
    assert any("non-allowlisted environment key" in problem for problem in problems)


# ---------------------------------------------------------------------------------------------
# attestation
# ---------------------------------------------------------------------------------------------


def _attestation(workspace: dict[str, Path]) -> dict[str, object]:
    return build_attestation(
        plan=_plan(workspace),
        repository_root=workspace["repository"],
        input_sha256="1" * 64,
        output_sha256="2" * 64,
        stdout_sha256="3" * 64,
        stderr_sha256="4" * 64,
        started_at="2026-08-12T00:00:00Z",
        finished_at="2026-08-12T00:10:00Z",
        exit_status=0,
        runtime_name="containerd",
        runtime_version="1.7.0",
    )


def test_an_attestation_validates(workspace: dict[str, Path]) -> None:
    validate_attestation(_attestation(workspace), repository_root=workspace["repository"])


def test_an_edited_attestation_breaks_its_digest(workspace: dict[str, Path]) -> None:
    attestation = _attestation(workspace)
    attestation["output_sha256"] = "9" * 64
    with pytest.raises(IsolationError, match="digest drifted"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_an_attestation_claiming_isolation_while_its_argv_mounts_the_repository_is_refused(
    workspace: dict[str, Path],
) -> None:
    # The honest-looking boolean and the dishonest argv, side by side. The argv wins.
    attestation = _attestation(workspace)
    attestation["argv"] = list(attestation["argv"]) + [  # type: ignore[arg-type]
        "--mount", f"type=bind,source={workspace['repository']},target=/repo,readonly",
    ]
    assert attestation["repository_mounted"] is False
    with pytest.raises(IsolationError, match="from the repository"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_an_attestation_admitting_a_repository_mount_is_refused(
    workspace: dict[str, Path],
) -> None:
    attestation = _attestation(workspace)
    attestation["repository_mounted"] = True
    with pytest.raises(IsolationError, match="repository_mounted"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_an_attestation_recording_a_network_is_refused(workspace: dict[str, Path]) -> None:
    attestation = _attestation(workspace)
    attestation["network"] = "bridge"
    with pytest.raises(IsolationError, match="network access"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_an_attestation_with_a_non_zero_exit_is_refused(workspace: dict[str, Path]) -> None:
    attestation = _attestation(workspace)
    attestation["exit_status"] = 1
    with pytest.raises(IsolationError, match="did not exit cleanly"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_an_attestation_omitting_captured_output_is_refused(
    workspace: dict[str, Path],
) -> None:
    attestation = _attestation(workspace)
    attestation["stderr_sha256"] = None
    with pytest.raises(IsolationError, match="stderr_sha256 is malformed"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_an_attestation_on_a_reused_filesystem_is_refused(
    workspace: dict[str, Path],
) -> None:
    attestation = _attestation(workspace)
    attestation["working_filesystem"] = "host-bind"
    with pytest.raises(IsolationError, match="fresh working filesystem"):
        validate_attestation(attestation, repository_root=workspace["repository"])


def test_the_builder_refuses_a_plan_whose_argv_already_leaks(
    workspace: dict[str, Path],
) -> None:
    plan = _plan(workspace)
    plan["argv"] = list(plan["argv"]) + [  # type: ignore[arg-type]
        "--env", f"HOME={workspace['repository']}",
    ]
    with pytest.raises(IsolationError):
        build_attestation(
            plan=plan, repository_root=workspace["repository"],
            input_sha256="1" * 64, output_sha256="2" * 64, stdout_sha256="3" * 64,
            stderr_sha256="4" * 64, started_at="2026-08-12T00:00:00Z",
            finished_at="2026-08-12T00:10:00Z", exit_status=0,
            runtime_name="containerd", runtime_version="1.7.0",
        )
