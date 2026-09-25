"""DEVELOPMENT executor for content-addressed cognitive architectures.

The executor is deliberately small and deterministic.  It executes only primitives supplied by an
explicit registry, keeps recurrent state outside the architecture genome, and records observations
from the actual execution.  CPU process time is reported only as a compute proxy; energy is never
inferred from it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .cognitive_architecture import (
    CognitiveArchitectureError,
    architecture_digest,
    canonical_architecture,
)

Primitive = Callable[[tuple[Any, ...], Any, Mapping[str, Any]], tuple[Any, Any]]


@dataclass(frozen=True)
class ExecutionResult:
    architecture_digest: str
    outputs: dict[str, Any]
    recurrent_state: dict[str, Any]
    observations: dict[str, Any]


class CognitiveExecutionError(RuntimeError):
    """Raised when an admitted architecture cannot be executed safely."""


def _identity(values: tuple[Any, ...], previous: Any, config: Mapping[str, Any]) -> tuple[Any, Any]:
    del previous, config
    if len(values) != 1:
        raise CognitiveExecutionError("identity expects exactly one input")
    return values[0], None


def _sum(values: tuple[Any, ...], previous: Any, config: Mapping[str, Any]) -> tuple[Any, Any]:
    del previous, config
    if not values:
        raise CognitiveExecutionError("sum expects at least one input")
    try:
        return sum(values), None
    except TypeError as exc:
        raise CognitiveExecutionError("sum accepts additive values only") from exc


def _state_cell(values: tuple[Any, ...], previous: Any, config: Mapping[str, Any]) -> tuple[Any, Any]:
    del config
    if len(values) != 1:
        raise CognitiveExecutionError("state_cell expects exactly one feedforward input")
    current = values[0] if previous is None else previous
    return current, values[0]


def _threshold_router(values: tuple[Any, ...], previous: Any, config: Mapping[str, Any]) -> tuple[Any, Any]:
    del previous
    if len(values) != 3:
        raise CognitiveExecutionError("threshold_router expects selector, low and high inputs")
    threshold = config.get("threshold", 0)
    try:
        return (values[2] if values[0] >= threshold else values[1]), None
    except TypeError as exc:
        raise CognitiveExecutionError("threshold_router selector and threshold are not comparable") from exc


DEVELOPMENT_PRIMITIVES: dict[str, Primitive] = {
    "identity": _identity,
    "sink": _identity,
    "sum": _sum,
    "state_cell": _state_cell,
    "threshold_router": _threshold_router,
}


def execute_architecture(
    architecture: Any,
    inputs: Mapping[str, Any],
    *,
    registry: Mapping[str, Primitive] | None = None,
    recurrent_state: Mapping[str, Any] | None = None,
    max_node_executions: int | None = None,
) -> ExecutionResult:
    """Execute one logical step under an externally supplied node-execution ceiling.

    Input nodes are values supplied by the caller and are not executed as primitives.  Recurrent
    edges read the *previous* step's state for their target; they never alter within-step ordering.
    Primitive callables receive ``(feedforward_values, previous_state, config)`` and return
    ``(output, next_state)``.  Only nodes with recurrent incoming edges persist next state.
    """
    active_registry = dict(DEVELOPMENT_PRIMITIVES if registry is None else registry)
    canonical = canonical_architecture(
        architecture,
        admitted_primitives=set(active_registry) | {"source"},
    )
    node_by_id = {node["id"]: node for node in canonical["nodes"]}
    declared_inputs = set(canonical["inputs"])
    supplied_inputs = set(inputs)
    if supplied_inputs != declared_inputs:
        raise CognitiveExecutionError(
            "supplied inputs must exactly match architecture inputs: expected %s, got %s"
            % (sorted(declared_inputs), sorted(supplied_inputs))
        )
    for node_id in declared_inputs:
        if node_by_id[node_id]["primitive"] != "source":
            raise CognitiveExecutionError("input node %r must use primitive 'source'" % node_id)

    feedforward_in: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}
    recurrent_in: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}
    indegree = {node_id: 0 for node_id in node_by_id}
    for edge in canonical["edges"]:
        if edge["kind"] == "feedforward":
            feedforward_in[edge["target"]].append(edge["source"])
            outgoing[edge["source"]].append(edge["target"])
            indegree[edge["target"]] += 1
        else:
            recurrent_in[edge["target"]].append(edge["source"])

    ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for target in sorted(outgoing[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()

    executable = [node_id for node_id in order if node_id not in declared_inputs]
    if max_node_executions is not None:
        if max_node_executions < 0:
            raise CognitiveExecutionError("max_node_executions must be non-negative")
        if len(executable) > max_node_executions:
            raise CognitiveExecutionError("architecture exceeds admitted node-execution budget")

    previous = dict(recurrent_state or {})
    unknown_state = set(previous) - set(node_by_id)
    if unknown_state:
        raise CognitiveExecutionError("recurrent state contains unknown nodes: %s" % sorted(unknown_state))

    values: dict[str, Any] = dict(inputs)
    next_state: dict[str, Any] = {}
    started = time.process_time_ns()
    primitive_calls = 0
    for node_id in executable:
        node = node_by_id[node_id]
        primitive = active_registry.get(node["primitive"])
        if primitive is None:
            raise CognitiveExecutionError("primitive %r is not executable" % node["primitive"])
        args = tuple(values[source] for source in sorted(feedforward_in[node_id]))
        old_state = previous.get(node_id)
        try:
            output, proposed_state = primitive(args, old_state, node["config"])
        except CognitiveExecutionError:
            raise
        except Exception as exc:
            raise CognitiveExecutionError(
                "primitive %r failed at node %r" % (node["primitive"], node_id)
            ) from exc
        primitive_calls += 1
        values[node_id] = output
        if recurrent_in[node_id]:
            next_state[node_id] = proposed_state

    cpu_ns = time.process_time_ns() - started
    return ExecutionResult(
        architecture_digest=architecture_digest(canonical),
        outputs={node_id: values[node_id] for node_id in canonical["outputs"]},
        recurrent_state=next_state,
        observations={
            "primitive_calls": primitive_calls,
            "cpu_process_time_ns": cpu_ns,
            "cpu_time_is_compute_proxy": True,
            "energy_joules": None,
            "energy_measurement_available": False,
        },
    )
