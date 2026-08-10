from __future__ import annotations

import json

import pytest

from metamorphosis.m075_epistemic_context import EpistemicContextBackend, EpistemicContextError
from mira_core.model import DECISION_SCHEMA, ModelRequest


ACT = {"decision": "act", "script": "missing-tool input > output", "reason": None}
REFUSE = {"decision": "refuse", "script": None, "reason": "required tool remains unavailable"}


class FakeDelegate:
    backend_id = "fake-provider"
    model = "fake-model"
    timeout_seconds = 9

    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def request(*, history=(), returncode=None, output="") -> ModelRequest:
    state = {"event": "ready"}
    observation_id = "harbor:0:reset"
    if returncode is not None:
        state = {"event": "command", "returncode": returncode, "output": output}
        observation_id = f"harbor:{len(history)}:command"
    payload = {
        "goal": {"goal_id": "generic", "instruction": "perform task", "success_criteria": {}},
        "observation": {
            "observation_id": observation_id, "state": state,
            "terminal": False, "success": False, "error": None,
        },
        "recent_evidence": list(history),
        "allowed_decisions": {},
    }
    return ModelRequest("bounded policy", json.dumps(payload), DECISION_SCHEMA)


def observation_event(index: int, returncode: int):
    return {
        "index": index, "kind": "observation",
        "payload": {"step": index, "returncode": returncode, "output_truncated": False},
        "previous_digest": "0" * 64, "digest": "1" * 64,
    }


def test_initial_projection_names_the_complete_budget_without_hidden_data() -> None:
    delegate = FakeDelegate((ACT,))
    backend = EpistemicContextBackend(delegate, max_steps=4)
    assert backend.complete(request()) == ACT
    payload = json.loads(delegate.requests[0].input_json)
    state = payload["epistemic_state"]
    assert state == {
        "schema": "m075-epistemic-state-v1",
        "step_index": 1,
        "max_steps": 4,
        "remaining_steps_including_current": 4,
        "observed_command_count": 0,
        "successful_command_count": 0,
        "failed_command_count": 0,
        "consecutive_nonzero_count": 0,
        "last_returncode": None,
        "last_failure_class": None,
        "proposed_action_count": 0,
        "distinct_action_count": 0,
        "repeated_action_count": 0,
        "last_action_sha256": None,
        "prior_refusal_decisions": 0,
    }
    rendered = delegate.requests[0].input_json
    assert "solvability" not in rendered and "certificate" not in rendered
    assert backend.model == "fake-model" and backend.timeout_seconds == 9


def test_failed_observations_and_repeated_actions_accumulate_without_a_label() -> None:
    delegate = FakeDelegate((ACT, ACT, REFUSE))
    backend = EpistemicContextBackend(delegate, max_steps=4)
    backend.complete(request())
    history1 = (observation_event(1, 127),)
    backend.complete(request(
        history=history1, returncode=127, output="sh: missing-tool: not found",
    ))
    history2 = (*history1, observation_event(2, 127))
    backend.complete(request(
        history=history2, returncode=127, output="sh: missing-tool: not found",
    ))
    state = backend.states[-1]
    assert state["step_index"] == 3
    assert state["remaining_steps_including_current"] == 2
    assert state["failed_command_count"] == 2
    assert state["consecutive_nonzero_count"] == 2
    assert state["last_failure_class"] == "executable_or_path_unavailable"
    assert state["proposed_action_count"] == 2
    assert state["distinct_action_count"] == 1
    assert state["repeated_action_count"] == 1


@pytest.mark.parametrize(
    ("returncode", "output", "expected"),
    [
        (124, "", "command_timeout"),
        (126, "", "permission_or_immutability_barrier"),
        (1, "Read-only file system", "permission_or_immutability_barrier"),
        (2, "bad syntax", "nonzero_command_result"),
    ],
)
def test_failure_classes_are_generic_observation_summaries(
    returncode: int, output: str, expected: str,
) -> None:
    delegate = FakeDelegate((ACT, REFUSE))
    backend = EpistemicContextBackend(delegate, max_steps=2)
    backend.complete(request())
    backend.complete(request(
        history=(observation_event(1, returncode),), returncode=returncode, output=output,
    ))
    assert backend.states[-1]["last_failure_class"] == expected


def test_success_and_prior_refusal_are_reported_without_forcing_a_decision() -> None:
    delegate = FakeDelegate((REFUSE, ACT))
    backend = EpistemicContextBackend(delegate, max_steps=2)
    backend.complete(request())
    backend.complete(request(
        history=(observation_event(1, 0),), returncode=0, output="done",
    ))
    assert backend.states[-1]["successful_command_count"] == 1
    assert backend.states[-1]["prior_refusal_decisions"] == 1


def test_malformed_or_over_budget_requests_fail_closed() -> None:
    with pytest.raises(EpistemicContextError, match="positive step budget"):
        EpistemicContextBackend(FakeDelegate(()), max_steps=0)
    backend = EpistemicContextBackend(FakeDelegate((ACT,)), max_steps=1)
    backend.complete(request())
    with pytest.raises(EpistemicContextError, match="exceeds"):
        backend.complete(request())
    with pytest.raises(EpistemicContextError, match="valid JSON"):
        EpistemicContextBackend(FakeDelegate(()), max_steps=1).complete(
            ModelRequest("system", "not-json", DECISION_SCHEMA)
        )
