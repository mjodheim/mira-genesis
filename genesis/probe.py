"""Probes the lineage composes and runs, rather than oracles it consults.

This module exists to close the third authored ceiling named in
`docs/GENESIS_PRIMITIVE_AUDIT.md`, and the ceiling is subtler than the first two.

`diagnosis.py` already lets a lineage exhaust its registry and name a component class it did not
have. But the question "does extending this component resolve the demand?" was answered by a
`speculate` callable the host supplied. The host therefore decided the finding, and the certificate
recorded the lineage agreeing with it. Every exhaustion certificate produced that way is the host's
conclusion wearing the lineage's name.

Here the same question is answered by **experiment**:

1. the lineage *composes* a probe — an ordered sequence of primitive operations — rather than
   selecting one from a prepared list;
2. the composition runs as an untrusted body in the sandbox, at budget cost;
3. the verdict comes from raw per-task outcomes tallied by the trust root, not from any callable's
   return value and not from anything the probe reports about itself.

Something is still host-supplied, and pretending otherwise would be the same error one level down.
What the host supplies is the **substrate of composition**: a registry of primitive operations, a
task set, and which operations each held component gives access to. What the host does **not** supply
is the answer. It cannot know which composition will work, and it cannot make a composition work by
declaring that it does — the composition either maps the inputs to the expected outputs when it runs,
or it does not.

That difference is testable rather than asserted, and `tests/test_genesis_probe.py` tests it: the
same code, over the same components, licenses a new component class for one task set and refuses to
for another. An apparatus whose finding does not depend on the data decides nothing.

**Exhaustion, restated.** A component is probed by searching the compositions its operations can
express. The registry is exhausted when no held component's operations admit a composition that
solves the demand. That licenses naming a new class only in company with the second half: a
composition drawn from the wider operation set *does* solve it. "Nothing I have works" plus "something
outside what I have works" is a finding about the lineage's representation. "Nothing I have works"
alone is only a failed search.
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
    """Raised when a probe cannot be trusted — most importantly when its rollback is not exact."""


def resolve_registry(reference: str) -> Mapping[str, Any]:
    """Look up an operation registry from a ``module:attribute`` reference.

    Probes cross a process boundary, so a body may carry only picklable data. It carries the
    reference and rebinds the callables in the child, exactly as the migrated bodies do.
    """
    module_name, _, attribute = str(reference).partition(":")
    if not module_name or not attribute:
        raise ProbeError("an operation registry reference must look like 'module:attribute'")
    registry = getattr(import_module(module_name), attribute)
    if not isinstance(registry, Mapping):
        raise ProbeError("%r does not name a mapping of operations" % reference)
    return registry


class ComposedProbeBody:
    """A body the lineage composed: apply these operations, in this order, to each task's input.

    Holds names only, never callables, so it survives the pickle into the sandbox's spawned
    interpreter. An operation the registry does not have makes the probe report `error` for that
    task rather than raising — an unrunnable composition is an observation, not a crash.
    """

    def __init__(self, registry_reference: str, operations: Sequence[str]) -> None:
        self.registry_reference = str(registry_reference)
        self.operations = tuple(str(name) for name in operations)

    def attempt(self, task: Mapping[str, Any]) -> str:
        from genesis.probe import resolve_registry

        try:
            registry = resolve_registry(self.registry_reference)
        except Exception:
            return "error"
        value = task["input"]
        for name in self.operations:
            operation = registry.get(name)
            if operation is None:
                return "error"
            try:
                value = operation(value)
            except Exception:
                return "error"
        return "solved" if value == task["expected"] else "unsolved"


def composed_probe_body(registry_reference: str, operations: Sequence[str]):
    """Picklable factory. `run_candidate` calls this in the child to build the probe."""
    return ComposedProbeBody(registry_reference, operations)


@dataclass(frozen=True)
class Composition:
    """One probe the lineage built. Its digest is what the certificate records."""

    operations: tuple[str, ...]

    def record(self) -> dict[str, Any]:
        payload = {"schema": COMPOSITION_SCHEMA, "operations": list(self.operations)}
        return {**payload, "composition_digest": digest_of(payload)}


def compositions(operations: Sequence[str], *, max_length: int) -> Iterator[Composition]:
    """Every ordered composition of the available operations, shortest first.

    Order matters and repetition is excluded: a lineage searching `double then increment` must not
    have to spend its budget on `double then double` to reach it. Shortest-first means the budget
    buys the simplest explanations before the elaborate ones.
    """
    available = list(dict.fromkeys(str(name) for name in operations))
    for length in range(1, max(1, int(max_length)) + 1):
        for candidate in permutations(available, length):
            yield Composition(operations=tuple(candidate))


def _solves_every_task(outcomes: Sequence[Mapping[str, Any]]) -> bool:
    """Read the raw rows. Never a score, never anything the probe said about itself."""
    rows = list(outcomes)
    return bool(rows) and all(row.get("outcome") == "solved" for row in rows)


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
    """Compose probes from these operations and run them until one solves the demand.

    Returns the first composition that solves every task, or reports the search exhausted. Each
    trial costs budget and runs in its own isolated process; the budget refusing is a legitimate
    outcome and is reported as `budget_exhausted` rather than being confused with exhaustion of the
    search space.
    """
    attempts: list[dict[str, Any]] = []
    for composition in compositions(operations, max_length=max_length):
        try:
            budget.spend(probe_dimension)
        except BudgetExhausted as exhausted:
            return {
                "resolved": False,
                "composition": None,
                "attempts": attempts,
                "search_exhausted": False,
                "budget_exhausted": True,
                "reason": str(exhausted),
            }
        run = run_candidate(
            functools.partial(composed_probe_body, registry_reference, composition.operations),
            tasks,
            isolation,
        )
        if not run["completed"]:
            # A probe that never ran is not evidence that its composition fails.
            return {
                "resolved": False,
                "composition": None,
                "attempts": attempts,
                "search_exhausted": False,
                "budget_exhausted": False,
                "instrument_failure": True,
                "reason": run.get("reason", ""),
            }
        solved = _solves_every_task(run["outcomes"])
        attempts.append(
            {
                **composition.record(),
                "solved_every_task": solved,
                "sandbox_digest": run["result_digest"],
            }
        )
        if solved:
            return {
                "resolved": True,
                "composition": composition.record(),
                "attempts": attempts,
                "search_exhausted": False,
                "budget_exhausted": False,
                "reason": "",
            }
    return {
        "resolved": False,
        "composition": None,
        "attempts": attempts,
        "search_exhausted": True,
        "budget_exhausted": False,
        "reason": "no composition over these operations solves the demand",
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
    """Probe every held component by experiment, then ask whether anything outside them works.

    Two findings, and the second is what stops the first from being a failed search:

    * **exhaustion** — no held component's operations admit a composition that solves the demand;
    * **reachability** — a composition drawn from the wider operation set does solve it.

    Only both together license naming a component class. Exhaustion alone says the lineage could not
    do it; exhaustion plus reachability says the thing that is missing is a *representation*, which
    is a claim about the lineage rather than about its luck.

    The lineage state is serialized before and after and compared byte for byte, because a diagnosis
    that quietly changed the thing it was diagnosing has measured nothing.
    """
    before = canonical_bytes(dict(state))
    registry = resolve_registry(registry_reference)
    held = lineage_state.component_names(state)

    probes: list[dict[str, Any]] = []
    resolved_by = None
    for component in held:
        operations = list(component_operations.get(component) or [])
        outcome = search(
            registry_reference=registry_reference,
            operations=operations,
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
                "composition": outcome["composition"],
            }
        )
        if outcome["resolved"]:
            resolved_by = component
            break
        if outcome.get("budget_exhausted") or outcome.get("instrument_failure"):
            break

    complete = len(probes) == len(held) and all(
        record["search_exhausted"] for record in probes
    )
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
            else "no composition solves the demand at all, so nothing shows a representation is "
            "missing rather than the demand being unreachable here"
        ),
    }


def certificate_from_experiment(
    diagnosis: Mapping[str, Any], *, new_component: str
) -> dict[str, Any]:
    """Turn an experimental diagnosis into the certificate `state.extend_components` demands.

    The probe records carry the composition digests actually run, so the certificate names the
    experiments rather than merely asserting they happened.
    """
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
            }
            for record in diagnosis["probes"]
        ],
        resolves_with_new_component=True,
    )
