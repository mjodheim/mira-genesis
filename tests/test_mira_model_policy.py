from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pytest

from mira_core import (
    CodexExecBackend, Goal, ModelBackendError, ModelPolicyLimits, ModelRequest, Observation,
    StructuredModelPolicy,
)
from mira_core.contracts import JsonValue


class FakeBackend:
    backend_id = "fake-structured-backend"

    def __init__(self, value: Mapping[str, JsonValue]) -> None:
        self.value = value
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> Mapping[str, JsonValue]:
        self.requests.append(request)
        return self.value


def test_structured_policy_emits_only_the_fixed_container_action() -> None:
    backend = FakeBackend({"decision": "act", "script": "printf ready", "reason": None})
    policy = StructuredModelPolicy(backend)
    action = policy.propose(
        Goal("external-task", "repair the isolated workspace", {"external_tests": True}),
        Observation("container-0", {"output": "failing"}),
        ({"kind": "episode_started"},),
    )
    assert action is not None
    assert action.kind == "container_exec"
    assert action.payload == {"script": "printf ready"}
    assert action.required_authorities == ("compute", "filesystem_read", "filesystem_write")
    request = backend.requests[0]
    value = json.loads(request.input_json)
    assert value["goal"]["goal_id"] == "external-task"
    assert value["observation"]["state"] == {"output": "failing"}
    assert "host" in request.system_instruction


def test_finish_submits_without_claiming_success_and_refusal_returns_none() -> None:
    finish = StructuredModelPolicy(FakeBackend({
        "decision": "finish", "script": None, "reason": None,
    })).propose(Goal("finish", "submit"), Observation("o", {}), ())
    assert finish is not None
    assert finish.kind == "container_submit"
    assert finish.required_authorities == ()

    refusing = StructuredModelPolicy(FakeBackend({
        "decision": "refuse", "script": None, "reason": "unsupported protocol",
    }))
    assert refusing.propose(Goal("refuse", "unsupported"), Observation("o", {}), ()) is None
    assert refusing.last_refusal_reason == "unsupported protocol"


@pytest.mark.parametrize("value", [
    {"decision": "act", "script": None, "reason": None},
    {"decision": "act", "script": "ok", "reason": "extra"},
    {"decision": "finish", "script": "claim success", "reason": None},
    {"decision": "refuse", "script": None, "reason": None},
    {"decision": "other", "script": None, "reason": None},
    {"decision": "finish", "script": None, "reason": None, "extra": True},
])
def test_malformed_or_self_inconsistent_model_decisions_fail_closed(value) -> None:
    policy = StructuredModelPolicy(FakeBackend(value))
    with pytest.raises(ModelBackendError):
        policy.propose(Goal("closed", "stay closed"), Observation("o", {}), ())


def test_model_policy_bounds_goal_observation_history_script_and_refusal() -> None:
    limits = ModelPolicyLimits(
        max_instruction_chars=4, max_observation_chars=8, max_history_events=2,
        max_script_chars=3, max_refusal_chars=4,
    )
    with pytest.raises(ModelBackendError, match="instruction"):
        StructuredModelPolicy(FakeBackend({}), limits=limits).propose(
            Goal("large", "12345"), Observation("o", {}), (),
        )
    with pytest.raises(ModelBackendError, match="observation"):
        StructuredModelPolicy(FakeBackend({}), limits=limits).propose(
            Goal("large", "1234"), Observation("o", {"long": "value"}), (),
        )
    with pytest.raises(ModelBackendError, match="bounded action"):
        StructuredModelPolicy(FakeBackend({
            "decision": "act", "script": "1234", "reason": None,
        }), limits=limits).propose(Goal("large", "1234"), Observation("o", {}), ())
    with pytest.raises(ModelBackendError, match="bounded response"):
        StructuredModelPolicy(FakeBackend({
            "decision": "refuse", "script": None, "reason": "12345",
        }), limits=limits).propose(Goal("large", "1234"), Observation("o", {}), ())


def test_codex_backend_rejects_relative_or_missing_executable(tmp_path: Path) -> None:
    with pytest.raises(ModelBackendError, match="absolute executable"):
        CodexExecBackend(Path("codex"), tmp_path, "explicit-model")
    with pytest.raises(ModelBackendError, match="absolute executable"):
        CodexExecBackend(tmp_path / "missing-codex", tmp_path, "explicit-model")
