"""DEVELOPMENT regressions for the bounded cognitive architecture executor."""
from __future__ import annotations

import pytest

from genesis import cognitive_architecture as ca
from genesis import cognitive_executor as ce


def _architecture(*, primitive="state_cell"):
    return {
        "schema": ca.COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": [
            {"id": "input", "primitive": "source", "config": {}},
            {"id": "memory", "primitive": primitive, "config": {}},
            {"id": "output", "primitive": "sink", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "memory", "kind": "feedforward"},
            {"source": "memory", "target": "memory", "kind": "recurrent"},
            {"source": "memory", "target": "output", "kind": "feedforward"},
        ],
        "inputs": ["input"],
        "outputs": ["output"],
    }


def test_executor_carries_declared_recurrent_state_across_steps():
    architecture = _architecture()
    first = ce.execute_architecture(architecture, {"input": 7}, max_node_executions=2)
    second = ce.execute_architecture(
        architecture,
        {"input": 99},
        recurrent_state=first.recurrent_state,
        max_node_executions=2,
    )

    assert first.outputs == {"output": 7}
    assert first.recurrent_state == {"memory": 7}
    assert second.outputs == {"output": 7}
    assert second.recurrent_state == {"memory": 99}
    assert first.architecture_digest == ca.architecture_digest(architecture)


def test_executor_fails_closed_on_input_registry_and_budget_mismatch():
    architecture = _architecture()
    with pytest.raises(ce.CognitiveExecutionError, match="exactly match"):
        ce.execute_architecture(architecture, {})
    with pytest.raises(ce.CognitiveExecutionError, match="node-execution budget"):
        ce.execute_architecture(architecture, {"input": 1}, max_node_executions=1)

    unknown = _architecture(primitive="unadmitted_machine")
    with pytest.raises(ca.CognitiveArchitectureError, match="outside the admitted registry"):
        ce.execute_architecture(unknown, {"input": 1})


def test_executor_reports_observed_cpu_proxy_without_inventing_energy():
    result = ce.execute_architecture(_architecture(), {"input": 3})
    observations = result.observations

    assert observations["primitive_calls"] == 2
    assert isinstance(observations["cpu_process_time_ns"], int)
    assert observations["cpu_process_time_ns"] >= 0
    assert observations["cpu_time_is_compute_proxy"] is True
    assert observations["energy_joules"] is None
    assert observations["energy_measurement_available"] is False


def test_external_registry_can_admit_a_new_deterministic_primitive():
    architecture = _architecture(primitive="double")

    def double(values, previous, config):
        del previous, config
        return values[0] * 2, None

    registry = dict(ce.DEVELOPMENT_PRIMITIVES)
    registry["double"] = double
    result = ce.execute_architecture(architecture, {"input": 4}, registry=registry)

    assert result.outputs == {"output": 8}


def test_recurrent_edge_uses_previous_state_of_its_declared_source():
    architecture = {
        "schema": ca.COGNITIVE_ARCHITECTURE_SCHEMA,
        "nodes": [
            {"id": "input", "primitive": "source", "config": {}},
            {"id": "relay", "primitive": "identity", "config": {}},
            {"id": "memory", "primitive": "state_cell", "config": {}},
            {"id": "output", "primitive": "sink", "config": {}},
        ],
        "edges": [
            {"source": "input", "target": "relay", "kind": "feedforward"},
            {"source": "input", "target": "memory", "kind": "feedforward"},
            {"source": "relay", "target": "memory", "kind": "recurrent"},
            {"source": "memory", "target": "output", "kind": "feedforward"},
        ],
        "inputs": ["input"],
        "outputs": ["output"],
    }

    first = ce.execute_architecture(architecture, {"input": 5})
    second = ce.execute_architecture(
        architecture,
        {"input": 9},
        recurrent_state=first.recurrent_state,
    )

    assert first.outputs == {"output": 5}
    assert first.recurrent_state == {"relay": 5}
    assert second.outputs == {"output": 5}
    assert second.recurrent_state == {"relay": 9}


def test_recurrent_state_for_non_source_node_fails_closed():
    with pytest.raises(ce.CognitiveExecutionError, match="without outgoing recurrent edges"):
        ce.execute_architecture(
            _architecture(),
            {"input": 1},
            recurrent_state={"output": 1},
        )
