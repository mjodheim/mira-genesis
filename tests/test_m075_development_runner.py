from __future__ import annotations

import json

from metamorphosis.m075_development_bank import TASKS
from mira_core.model import DECISION_SCHEMA, ModelRequest
from run_m075_development import ScriptedEpistemicDevelopmentBackend


def _request(state):
    return ModelRequest(
        "system", json.dumps({"epistemic_state": state}), DECISION_SCHEMA,
    )


def test_scripted_development_policy_branches_only_on_visible_epistemic_state() -> None:
    backend = ScriptedEpistemicDevelopmentBackend(TASKS[0])
    initial = {
        "observed_command_count": 0, "last_returncode": None,
    }
    assert backend.complete(_request(initial)) == {
        "decision": "act", "script": TASKS[0].solve_script, "reason": None,
    }
    success = {"observed_command_count": 1, "last_returncode": 0}
    assert backend.complete(_request(success))["decision"] == "finish"
    failure = {"observed_command_count": 1, "last_returncode": 127}
    assert backend.complete(_request(failure))["decision"] == "refuse"


def test_scripted_development_policy_rejects_hidden_label_fields() -> None:
    backend = ScriptedEpistemicDevelopmentBackend(TASKS[0])
    request = ModelRequest(
        "system",
        json.dumps({
            "epistemic_state": {"observed_command_count": 0, "last_returncode": None},
            "expected_solvability": "feasible",
        }),
        DECISION_SCHEMA,
    )
    try:
        backend.complete(request)
    except ValueError as exc:
        assert "hidden field" in str(exc)
    else:
        raise AssertionError("hidden development label was accepted")
