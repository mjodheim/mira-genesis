from __future__ import annotations

import os
from pathlib import Path
import shutil

import pytest

from mira_core import (
    ContainerLimits, ContainerSpec, DockerCliEngine, Goal,
    IsolatedContainerBody, MiraAgent, SafetyPolicy, StructuredModelPolicy,
)
from mira_core.safety import Authority


PYTHON_IMAGE = (
    "python@sha256:9662417aace5ae7b8e2609cce472b72a8958e134ba372808abe9cc1a0c0125e6"
)


class SyntheticRepairBackend:
    backend_id = "synthetic-repair-backend"

    def __init__(self) -> None:
        self.step = 0

    def complete(self, request):
        self.step += 1
        if self.step == 1:
            return {
                "decision": "act",
                "script": (
                    "python -I -B -c \"from pathlib import Path; "
                    "Path('answer.txt').write_text('isolated\\n')\""
                ),
                "reason": None,
            }
        return {"decision": "finish", "script": None, "reason": None}


@pytest.mark.skipif(
    os.getenv("MIRA_RUN_DOCKER_TESTS") != "1",
    reason="real Docker integration is opt-in",
)
def test_real_networkless_container_repairs_only_the_task_workspace(tmp_path: Path) -> None:
    docker = shutil.which("docker.exe" if os.name == "nt" else "docker")
    if docker is None:
        pytest.fail("MIRA_RUN_DOCKER_TESTS=1 requires Docker on PATH")
    (tmp_path / "answer.txt").write_text("wrong\n", encoding="utf-8")
    limits = ContainerLimits(
        max_steps=4, timeout_seconds=15, memory_bytes=268_435_456,
        cpus=1.0, pids_limit=64, tmpfs_bytes=33_554_432,
    )
    body = IsolatedContainerBody(
        "real-isolated-fixture", tmp_path, ContainerSpec(PYTHON_IMAGE),
        DockerCliEngine(Path(docker).resolve()), limits=limits,
    )
    safety = SafetyPolicy.from_authorities({
        Authority.COMPUTE, Authority.FILESYSTEM_READ, Authority.FILESYSTEM_WRITE,
    })
    with body:
        result = MiraAgent(
            StructuredModelPolicy(SyntheticRepairBackend()), body,
            safety=safety, max_steps=4,
        ).run(Goal("synthetic-container-repair", "write isolated to answer.txt, then submit"))
    assert result.status == "body_stopped"
    assert result.succeeded is False
    assert result.final_observation.state["agent_claimed_success"] is False
    assert (tmp_path / "answer.txt").read_text(encoding="utf-8") == "isolated\n"
