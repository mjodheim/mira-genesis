"""Probes the lineage composes and runs, rather than oracles it consults.

This module closes the authored component/vocabulary ceilings by making discoveries reusable. A
certificate is not merely a historical label: an acquired component's measured resolving
composition becomes its executable probe semantics, and an acquired `requires_<operation>` feature
is evaluated on later demands from the resolving composition measured for those demands.

Seed component operation sets remain host apparatus. Acquired machinery, however, is reconstructed
from lineage state rather than from a host edit to the component-operation table.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from importlib import import_module
from itertools import permutations
from typing import Any, Iterator, Mapping, Sequence

from genesis import state as lineage_state
from genesis.sandbox import run_candidate
from genesis.trust_root import BudgetExhausted, Isolation, canonical_bytes, digest_of

COMPOSITION_SCHEMA = "genesis-composed-probe-v1"
EXPERIMENTAL_DIAGNOSIS_SCHEMA = "genesis-experimental-diagnosis-v1"


class ProbeError(RuntimeError):
    """Raised when a probe cannot be trusted or a stored diagnostic concept has no semantics."""


def resolve_registry(reference: str) -> Mapping[str, Any]:
    module_name, _, attribute = str(reference).partition(":")
    if not module_name or not attribute:
        raise ProbeError("an operation registry reference must look like 'module:attribute'")
    registry = getattr(import_module(module_name), attribute)
    if not isinstance(registry, Mapping):
        raise ProbeError("%r does not name a mapping of operations" % reference)
    return registry


class BatchProbeBody:
    def __init__(self, registry_reference: str, compositions: Sequence[Sequence[str]]) -> None:
        self.registry_reference = str(registry_reference)
        self.compositions = tuple(tuple(str(name) for name in item) for item in compositions)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        from genesis.probe import resolve_registry

        registry = resolve_registry(self.registry_reference)
        operations = self.compositions[int(task["composition"])]
        value = task["input"]
        for name in operations:
            operation = registry.get(name)
            if operation is None:
                raise ProbeError("this composition uses %r, which the registry does not have" % name)
            value = operation(value)
        return value


def batch_probe_body(registry_reference: str, compositions: Sequence[Sequence[str]]):
    return BatchProbeBody(registry_reference, compositions)


@dataclass(frozen=True)
class Composition:
    operations: tuple[str, ...]

    def record(self) -> dict[str, Any]:
        payload = {"schema": COMPOSITION_SCHEMA, "operations": list(self.operations)}
        return {**payload, "composition_digest": digest_of(payload)}


def compositions(operations: Sequence[str], *, max_length: int) -> Iterator[Composition]:
    available = list(dict.fromkeys(str(name) for name in operations))
    for length in range(1, max(1, int(max_length)) + 1):
        for candidate in permutations(available, length):
            yield Composition(operations=tuple(candidate))


def grade_probe(task: Mapping[str, Any], answer: Any) -> str:
    return "solved" if answer == task.get("expected") else "unsolved"


def _solves_every_task(outcomes: Sequence[Mapping[str, Any]]) -> bool:
    rows = list(outcomes)
    return bool(rows) and all(row.get("outcome") == "solved" for row in rows)


def _run_compositions(
    *,
    registry_reference: str,
    candidates: Sequence[Composition],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
) -> dict[str, Any]:
    """Run already-budgeted compositions as one inert-data sandbox batch."""
    cross = [
        {
            "task_id": "c%d::%s" % (index, task["task_id"]),
            "composition": index,
            "input": task["input"],
            "expected": task["expected"],
        }
        for index, composition in enumerate(candidates)
        for task in tasks
    ]
    run = run_candidate(
        functools.partial(
            batch_probe_body,
            registry_reference,
            [composition.operations for composition in candidates],
        ),
        cross,
        isolation,
        grade=grade_probe,
        withhold=("expected",),
    )
    if not run["completed"]:
        return {"completed": False, "run": run, "grouped": {}}
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for row in run["outcomes"]:
        index = int(str(row["task_id"]).split("::", 1)[0][1:])
        grouped.setdefault(index, []).append(row)
    return {"completed": True, "run": run, "grouped": grouped}


def search(
    *,
    registry_reference: str,
    operations: Sequence[str],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
    budget,
    max_length: int = 2,
    probe_dimension: str = "probes",
) -> dict[str, Any]:
    planned = list(compositions(operations, max_length=max_length))
    affordable: list[Composition] = []
    budget_exhausted = False
    for composition in planned:
        try:
            budget.spend(probe_dimension)
        except BudgetExhausted:
            budget_exhausted = True
            break
        affordable.append(composition)

    if not affordable:
        return {
            "resolved": False,
            "composition": None,
            "attempts": [],
            "search_exhausted": not budget_exhausted and not planned,
            "budget_exhausted": budget_exhausted,
            "reason": "the budget refused the first probe" if budget_exhausted else "",
        }

    executed = _run_compositions(
        registry_reference=registry_reference,
        candidates=affordable,
        tasks=tasks,
        isolation=isolation,
    )
    if not executed["completed"]:
        run = executed["run"]
        return {
            "resolved": False,
            "composition": None,
            "attempts": [],
            "search_exhausted": False,
            "budget_exhausted": budget_exhausted,
            "instrument_failure": True,
            "reason": run.get("reason", ""),
        }

    grouped = executed["grouped"]
    run = executed["run"]
    attempts = []
    resolved = None
    for index, composition in enumerate(affordable):
        solved = _solves_every_task(grouped.get(index, []))
        attempts.append(
            {
                **composition.record(),
                "solved_every_task": solved,
                "sandbox_digest": run["result_digest"],
            }
        )
        if solved and resolved is None:
            resolved = composition
    if resolved is not None:
        return {
            "resolved": True,
            "composition": resolved.record(),
            "attempts": attempts,
            "search_exhausted": False,
            "budget_exhausted": budget_exhausted,
            "reason": "",
        }
    return {
        "resolved": False,
        "composition": None,
        "attempts": attempts,
        "search_exhausted": not budget_exhausted,
        "budget_exhausted": budget_exhausted,
        "reason": "the budget ran out before the search finished"
        if budget_exhausted
        else "no composition over these operations solves the demand",
    }


def _component_entry(state: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    for entry in state.get("components") or []:
        if entry.get("name") == name:
            return entry
    raise ProbeError("component %r is not present in lineage state" % name)


def component_operations_from_state(
    state: Mapping[str, Any],
    component: str,
    seed_component_operations: Mapping[str, Sequence[str]],
) -> list[str]:
    """Reconstruct the operation semantics of a held component.

    Seed components use the admitted host apparatus. Acquired components use exactly the resolving
    composition preserved by their certificate, so they remain usable even when the host's original
    component table knows nothing about the new name.
    """
    entry = _component_entry(state, component)
    if entry.get("origin") == "acquired":
        certificate = entry.get("certificate") or {}
        operations = list((certificate.get("resolving_composition") or {}).get("operations") or [])
        if not operations:
            raise ProbeError(
                "acquired component %r has no executable resolving composition" % component
            )
        return [str(name) for name in operations]
    return [str(name) for name in (seed_component_operations.get(component) or [])]


def _evaluate_component(
    state: Mapping[str, Any],
    component: str,
    *,
    registry_reference: str,
    seed_component_operations: Mapping[str, Sequence[str]],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
    budget,
    max_length: int,
) -> dict[str, Any]:
    """Evaluate one held component according to the semantics actually stored for it."""
    entry = _component_entry(state, component)
    operations = component_operations_from_state(state, component, seed_component_operations)
    if entry.get("origin") != "acquired":
        return search(
            registry_reference=registry_reference,
            operations=operations,
            tasks=tasks,
            isolation=isolation,
            budget=budget,
            max_length=max_length,
        )

    # An acquired component is the exact measured composition, not a new search space assembled
    # from its primitive names. Recombining them would silently give the acquisition more semantics
    # than its certificate established.
    try:
        budget.spend("probes")
    except BudgetExhausted:
        return {
            "resolved": False,
            "composition": None,
            "attempts": [],
            "search_exhausted": False,
            "budget_exhausted": True,
            "reason": "the budget refused the acquired-component probe",
        }
    composition = Composition(tuple(operations))
    executed = _run_compositions(
        registry_reference=registry_reference,
        candidates=[composition],
        tasks=tasks,
        isolation=isolation,
    )
    if not executed["completed"]:
        return {
            "resolved": False,
            "composition": None,
            "attempts": [],
            "search_exhausted": False,
            "budget_exhausted": False,
            "instrument_failure": True,
            "reason": executed["run"].get("reason", ""),
        }
    solved = _solves_every_task(executed["grouped"].get(0, []))
    attempt = {
        **composition.record(),
        "solved_every_task": solved,
        "sandbox_digest": executed["run"]["result_digest"],
    }
    return {
        "resolved": solved,
        "composition": composition.record() if solved else None,
        "attempts": [attempt],
        "search_exhausted": not solved,
        "budget_exhausted": False,
        "reason": "" if solved else "the acquired component's stored composition does not solve this demand",
    }


def diagnose_by_experiment(
    state: Mapping[str, Any],
    *,
    registry_reference: str,
    component_operations: Mapping[str, Sequence[str]],
    tasks: Sequence[Mapping[str, Any]],
    isolation: Isolation,
    budget,
    max_length: int = 2,
) -> dict[str, Any]:
    before = canonical_bytes(dict(state))
    registry = resolve_registry(registry_reference)
    held = lineage_state.component_names(state)

    probes: list[dict[str, Any]] = []
    resolved_by = None
    for component in held:
        operations = component_operations_from_state(state, component, component_operations)
        outcome = _evaluate_component(
            state,
            component,
            registry_reference=registry_reference,
            seed_component_operations=component_operations,
            tasks=tasks,
            isolation=isolation,
            budget=budget,
            max_length=max_length,
        )
        probes.append(
            {
                "component": component,
                "operations_available": operations,
                "resolved": outcome["resolved"],
                "attempts": len(outcome["attempts"]),
                "search_exhausted": outcome["search_exhausted"],
                "budget_exhausted": outcome.get("budget_exhausted", False),
                "instrument_failure": outcome.get("instrument_failure", False),
                "composition": outcome["composition"],
            }
        )
        if outcome["resolved"]:
            resolved_by = component
            break
        if outcome.get("budget_exhausted") or outcome.get("instrument_failure"):
            break

    complete = len(probes) == len(held) and all(record["search_exhausted"] for record in probes)
    exhausted = resolved_by is None and complete

    reachable = {"resolved": False, "composition": None}
    if exhausted:
        reachable = search(
            registry_reference=registry_reference,
            operations=list(registry),
            tasks=tasks,
            isolation=isolation,
            budget=budget,
            max_length=max_length,
        )

    after = canonical_bytes(dict(state))
    if before != after:
        raise ProbeError("diagnosis mutated the lineage state; a probe must leave it untouched")

    licenses = bool(exhausted and reachable["resolved"])
    return {
        "schema": EXPERIMENTAL_DIAGNOSIS_SCHEMA,
        "demand_digest": digest_of([dict(task) for task in tasks]),
        "registry": held,
        "probes": probes,
        "resolved_by": resolved_by,
        "registry_exhausted": exhausted,
        "reachable_with_wider_operations": bool(reachable["resolved"]),
        "resolving_composition": reachable["composition"],
        "licenses_naming_a_new_component": licenses,
        "why_not": ""
        if licenses
        else (
            "an existing component resolves the demand"
            if resolved_by
            else "the registry was not fully probed"
            if not complete
            else "no composition solves the demand at all, so nothing shows a representation is missing rather than the demand being unreachable here"
        ),
    }


def _feature_value(
    feature: Mapping[str, Any],
    *,
    component_resolved: Mapping[str, bool],
    resolving_operations: Sequence[str],
) -> bool:
    """Execute the persistent semantics of one diagnostic feature."""
    name = str(feature.get("name", ""))
    if name.startswith("resolvable_by_"):
        component = name[len("resolvable_by_") :]
        return bool(component_resolved.get(component, False))
    if feature.get("origin") == "acquired" and name.startswith("requires_"):
        operation = name[len("requires_") :]
        if not operation:
            raise ProbeError("acquired diagnostic feature names no required operation")
        return operation in set(resolving_operations)
    raise ProbeError(
        "diagnostic feature %r has no executable semantics; a stored label is not a vocabulary" % name
    )


def measure(
    state: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    *,
    registry_reference: str,
    component_operations: Mapping[str, Sequence[str]],
    isolation: Isolation,
    budget,
    max_length: int = 3,
) -> dict[str, Any]:
    """Measure a demand through the lineage's persistent diagnostic vocabulary."""
    registry = resolve_registry(registry_reference)
    held = lineage_state.component_names(state)
    component_resolved: dict[str, bool] = {}
    component_ops: dict[str, list[str]] = {}
    component_records: dict[str, dict[str, Any]] = {}
    for component in held:
        component_ops[component] = component_operations_from_state(
            state, component, component_operations
        )
        outcome = _evaluate_component(
            state,
            component,
            registry_reference=registry_reference,
            seed_component_operations=component_operations,
            tasks=tasks,
            isolation=isolation,
            budget=budget,
            max_length=max_length,
        )
        component_records[component] = outcome
        component_resolved[component] = bool(outcome["resolved"])
        if outcome.get("budget_exhausted") or outcome.get("instrument_failure"):
            return {
                "row": [],
                "resolved_anywhere": False,
                "resolving_operations": [],
                "limiting_component": None,
                "component_shares": {},
                "component_measurement_incomplete": True,
                "demand_digest": digest_of([dict(task) for task in tasks]),
            }

    wider = search(
        registry_reference=registry_reference,
        operations=list(registry),
        tasks=tasks,
        isolation=isolation,
        budget=budget,
        max_length=max_length,
    )
    operations = list((wider["composition"] or {}).get("operations") or [])
    row = [
        _feature_value(
            feature,
            component_resolved=component_resolved,
            resolving_operations=operations,
        )
        for feature in state.get("vocabulary") or []
    ]
    shares = {
        component: sum(1 for name in operations if name in set(component_ops[component]))
        for component in held
    }
    ranked = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
    limiting = None
    if operations and ranked:
        if len(ranked) == 1 or (len(ranked) > 1 and ranked[0][1] > ranked[1][1]):
            limiting = ranked[0][0]
    return {
        "row": row,
        "resolved_anywhere": bool(wider["resolved"]),
        "resolving_operations": operations,
        "limiting_component": limiting,
        "component_shares": shares,
        "component_measurement_incomplete": False,
        "demand_digest": digest_of([dict(task) for task in tasks]),
    }


def find_confusable_pair_by_experiment(
    state: Mapping[str, Any],
    demands: Sequence[Sequence[Mapping[str, Any]]],
    *,
    registry_reference: str,
    component_operations: Mapping[str, Sequence[str]],
    isolation: Isolation,
    budget,
    max_length: int = 3,
) -> dict[str, Any] | None:
    measured = [
        measure(
            state,
            tasks,
            registry_reference=registry_reference,
            component_operations=component_operations,
            isolation=isolation,
            budget=budget,
            max_length=max_length,
        )
        for tasks in demands
    ]
    for first in range(len(measured)):
        for second in range(first + 1, len(measured)):
            left, right = measured[first], measured[second]
            if left.get("component_measurement_incomplete") or right.get(
                "component_measurement_incomplete"
            ):
                continue
            if left["row"] != right["row"]:
                continue
            if not (left["resolved_anywhere"] and right["resolved_anywhere"]):
                continue
            if left["limiting_component"] is None or right["limiting_component"] is None:
                continue
            if left["limiting_component"] == right["limiting_component"]:
                continue
            if left["demand_digest"] == right["demand_digest"]:
                continue
            return {
                "shared_prior_row": list(left["row"]),
                "demand_digests": [left["demand_digest"], right["demand_digest"]],
                "limiting_components": [left["limiting_component"], right["limiting_component"]],
                "measurements": [left, right],
            }
    return None


def vocabulary_certificate_from_experiment(
    state: Mapping[str, Any], pair: Mapping[str, Any]
) -> dict[str, Any]:
    prior = lineage_state.vocabulary_names(state)
    row = list(pair["shared_prior_row"])
    if len(row) != len(prior):
        raise ProbeError(
            "the measured row has one entry per held feature (%d) and the vocabulary has %d features; the certificate cannot be built until they describe the same thing"
            % (len(row), len(prior))
        )
    left, right = pair["measurements"]
    difference = sorted(set(left["resolving_operations"]) ^ set(right["resolving_operations"]))
    if not difference:
        raise ProbeError(
            "both demands resolve through the same operations, so no measured feature separates them"
        )
    operation = difference[0]
    values = [
        operation in set(left["resolving_operations"]),
        operation in set(right["resolving_operations"]),
    ]
    if values[0] == values[1]:  # pragma: no cover - symmetric difference establishes this
        raise ProbeError("the proposed feature gives both demands the same value")
    return lineage_state.vocabulary_extension_certificate(
        prior_vocabulary=prior,
        new_feature="requires_%s" % operation,
        demand_digests=list(pair["demand_digests"]),
        shared_prior_row=row,
        limiting_components=list(pair["limiting_components"]),
        separated_rows=[row + [values[0]], row + [values[1]]],
    )


def certificate_from_experiment(
    diagnosis: Mapping[str, Any], *, new_component: str
) -> dict[str, Any]:
    if not diagnosis.get("licenses_naming_a_new_component"):
        raise ProbeError(
            "this diagnosis does not license a new component: %s" % diagnosis.get("why_not", "")
        )
    return lineage_state.component_extension_certificate(
        prior_registry=list(diagnosis["registry"]),
        new_component=new_component,
        demand_digest=diagnosis["demand_digest"],
        probe_records=[
            {
                "component": record["component"],
                "resolved": False,
                "compositions_tried": record["attempts"],
                "search_exhausted": bool(record.get("search_exhausted")),
                "budget_exhausted": bool(record.get("budget_exhausted")),
                "instrument_failure": bool(record.get("instrument_failure")),
            }
            for record in diagnosis["probes"]
        ],
        resolves_with_new_component=True,
        resolving_composition=diagnosis.get("resolving_composition"),
    )
