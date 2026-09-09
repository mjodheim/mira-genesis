"""Probes the lineage composes and runs, rather than oracles it consults.

This module exists to close the third authored ceiling named in
`docs/GENESIS_PRIMITIVE_AUDIT.md`, and the ceiling is subtler than the first two.

The module this replaces (`genesis/diagnosis.py`, deleted with this one's arrival) already let a
lineage exhaust its registry and name a component class it did not have. But the question "does
extending this component resolve the demand?" was answered by a `speculate` callable the host
supplied, and the confusable pair behind a vocabulary extension was found through a host-written
`feature_row`. The host therefore decided both findings, and the certificates recorded the lineage
agreeing with it. Every certificate produced that way is the host's conclusion wearing the lineage's
name, which is why the old module was removed rather than kept alongside: leaving an oracle-backed
path available is leaving a way back to certificates that mean nothing.

Here the same questions are answered by **experiment**:

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

**The vocabulary side.** `measure`, `find_confusable_pair_by_experiment` and
`vocabulary_certificate_from_experiment` do the same for the second ceiling. A demand's row through
the lineage's per-component vocabulary is measured by probing; its cause is which held component the
resolving composition mostly lives in, also measured; and the separating feature is read out of the
two measurements — an operation one resolving composition needs and the other does not — rather than
chosen and then justified.
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


class BatchProbeBody:
    """Every composition in one search, evaluated in a single isolated run.

    A process per composition is the obvious implementation and it makes a search cost more in
    interpreter startup than in thought. Batching changes nothing that matters: the compositions are
    all the same lineage's untrusted code, they run under the same limits, and the verdict is still
    read off raw per-task rows — one row per (composition, task) pair — rather than off anything the
    body reports about itself.

    Each task carries the index of the composition it belongs to, so grouping the rows afterwards is
    arithmetic on the outcomes rather than trust in the body's bookkeeping.
    """

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
                # This was called an equivalent mutant: deleting the raise makes the next line fail
                # with a TypeError, which the sandbox records as the same `error` row. The
                # equivalence was only ever true *through the sandbox*. Called directly the two
                # differ — `ProbeError` against `TypeError` — and the direct behaviour is part of
                # this class's contract, so the round-two suite exercises it and the mutant is
                # killed. An equivalence claim has to name the observation window it holds in.
                raise ProbeError("this composition uses %r, which the registry does not have" % name)
            value = operation(value)
        return value


def batch_probe_body(registry_reference: str, compositions: Sequence[Sequence[str]]):
    """Picklable factory. `run_candidate` calls this in the child to build the probe."""
    return BatchProbeBody(registry_reference, compositions)


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


def grade_probe(task: Mapping[str, Any], answer: Any) -> str:
    """Judge a composition's output here, in the parent, against what the task expects.

    A probe that decided for itself whether it had solved the demand would be a candidate marking
    its own paper, and every certificate resting on it would inherit that. The composition returns
    the value it computed and nothing else — and the sandbox withholds `expected` on the way in, so
    a composition cannot reach the value it is supposed to produce.
    """
    return "solved" if answer == task.get("expected") else "unsolved"


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

    cross = [
        {
            "task_id": "c%d::%s" % (index, task["task_id"]),
            "composition": index,
            "input": task["input"],
            "expected": task["expected"],
        }
        for index, composition in enumerate(affordable)
        for task in tasks
    ]
    run = run_candidate(
        functools.partial(
            batch_probe_body,
            registry_reference,
            [composition.operations for composition in affordable],
        ),
        cross,
        isolation,
        grade=grade_probe,
        # The composition would otherwise be handed the value it is meant to compute.
        withhold=("expected",),
    )
    if not run["completed"]:
        # A probe that never ran is not evidence that its composition fails.
        return {
            "resolved": False,
            "composition": None,
            "attempts": [],
            "search_exhausted": False,
            "budget_exhausted": budget_exhausted,
            "instrument_failure": True,
            "reason": run.get("reason", ""),
        }

    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for row in run["outcomes"]:
        index = int(str(row["task_id"]).split("::", 1)[0][1:])
        grouped.setdefault(index, []).append(row)

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
            # Shortest-first ordering means the first solving composition is the simplest one, and
            # the attempts after it are reported as run because they were: the batch paid for them.
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
    # Derived from the lineage's own state where it can be. A diagnosis that read a host mapping for
    # every component could never see an acquisition the lineage had just made: the certificate
    # licensed a name and the machinery stayed outside, so the same demand kept coming back
    # unresolved until a human edited the mapping.
    machinery = lineage_state.held_operations(state, component_operations)

    probes: list[dict[str, Any]] = []
    resolved_by = None
    for component in held:
        operations = list(machinery.get(component) or [])
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

    # This was described as unreachable — probes run in separate processes and nothing above writes
    # to `state`. That reasoning skipped a collaborator: `component_operations` is an arbitrary
    # `Mapping`, and a `Mapping` whose `.get()` mutates the state being diagnosed reaches this guard
    # from inside the call it is supposed to be observing. The round-two suite does exactly that, so
    # the guard is exercised rather than merely asserted.
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


#: A feature that asks whether some composition over one held component's own operations resolves
#: the demand. The component it names is the rest of the feature name.
RESOLVABLE_PREFIX = "resolvable_by_"
#: A feature that asks whether the measured resolving composition uses a particular operation. This
#: is the shape `vocabulary_certificate_from_experiment` emits, so a lineage that extends its
#: vocabulary produces features later measurements can actually evaluate.
REQUIRES_PREFIX = "requires_"


def evaluate_feature(
    feature: str,
    *,
    resolvable_by: Mapping[str, bool],
    resolving_operations: Sequence[str],
) -> bool:
    """Evaluate one diagnostic feature against a measurement, or refuse to invent a value.

    A vocabulary was a list of names. `measure()` emitted one boolean per held *component* and never
    looked at `LineageState.vocabulary`, so an extension added a feature to the record while every
    later row stayed the old width — the representation grew in the history and not in the
    computation, and a second extension could not build on the first. Features have semantics here,
    and a name whose semantics this runtime does not know is refused rather than defaulted: a made-up
    boolean in a diagnostic row is worse than a missing one, because everything downstream reads it
    as a measurement.
    """
    if feature.startswith(RESOLVABLE_PREFIX):
        component = feature[len(RESOLVABLE_PREFIX) :]
        if component not in resolvable_by:
            raise ProbeError(
                "the vocabulary contains %r, and this lineage holds no component %r to measure it "
                "against" % (feature, component)
            )
        return bool(resolvable_by[component])
    if feature.startswith(REQUIRES_PREFIX):
        return feature[len(REQUIRES_PREFIX) :] in set(resolving_operations)
    raise ProbeError(
        "the vocabulary contains %r, whose semantics this runtime cannot evaluate; a feature that "
        "cannot be measured is a label, and a row built from labels is not a measurement" % feature
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
    """Read a demand through the lineage's **current** diagnostic vocabulary, by experiment.

    The row has one entry per feature in `LineageState.vocabulary`, in that order, and each entry is
    evaluated from measurement: the per-component searches for `resolvable_by_*`, the measured
    resolving composition for `requires_*`. Extending the vocabulary therefore widens later rows,
    which is what makes an extension a change to the lineage's diagnostic resolution rather than an
    entry in its history.

    `limiting_component` is the held component the resolving composition mostly lives in — the one
    that would have to be extended. It is reported only when a single component strictly supplies
    most of the composition; a tie means the demand does not sit in one component more than another
    and saying otherwise would be inventing a cause.
    """
    registry = resolve_registry(registry_reference)
    machinery = lineage_state.held_operations(state, component_operations)
    resolvable_by: dict[str, bool] = {}
    for component in lineage_state.component_names(state):
        outcome = search(
            registry_reference=registry_reference,
            operations=list(machinery.get(component) or []),
            tasks=tasks,
            isolation=isolation,
            budget=budget,
            max_length=max_length,
        )
        resolvable_by[component] = bool(outcome["resolved"])

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
        evaluate_feature(
            feature, resolvable_by=resolvable_by, resolving_operations=operations
        )
        for feature in lineage_state.vocabulary_names(state)
    ]
    shares = {
        component: sum(1 for name in operations if name in set(machinery.get(component) or []))
        for component in lineage_state.component_names(state)
    }
    ranked = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
    limiting = None
    if operations and len(ranked) > 1 and ranked[0][1] > ranked[1][1]:
        limiting = ranked[0][0]
    return {
        "row": row,
        "vocabulary": lineage_state.vocabulary_names(state),
        "resolvable_by_component": resolvable_by,
        "resolved_anywhere": bool(wider["resolved"]),
        "resolving_operations": operations,
        "limiting_component": limiting,
        "component_shares": shares,
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
    """Two demands the current vocabulary reads identically, whose measured causes differ.

    Nothing here is declared. The rows come from probes, the causes come from which component the
    resolving composition mostly lives in, and both are read off raw outcomes. Without such a pair a
    new feature is decoration, and `state.vocabulary_extension_certificate` refuses it.
    """
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
                "limiting_components": [
                    left["limiting_component"],
                    right["limiting_component"],
                ],
                "measurements": [left, right],
            }
    return None


def vocabulary_certificate_from_experiment(
    state: Mapping[str, Any], pair: Mapping[str, Any]
) -> dict[str, Any]:
    """Turn a measured confusable pair into the certificate `state.extend_vocabulary` demands.

    The separating feature is not chosen and then justified. It is read out of the measurements: an
    operation one demand's resolving composition needs and the other's does not, named
    ``requires_<operation>``, with each demand's value taken from its own measured composition.
    """
    prior = lineage_state.vocabulary_names(state)
    row = list(pair["shared_prior_row"])
    if len(row) != len(prior):
        raise ProbeError(
            "the measured row has %d entries and this lineage's vocabulary has %d features; the "
            "certificate cannot be built until they describe the same thing" % (len(row), len(prior))
        )
    left, right = pair["measurements"]
    difference = sorted(
        set(left["resolving_operations"]) ^ set(right["resolving_operations"])
    )
    if not difference:
        raise ProbeError(
            "both demands resolve through the same operations, so no measured feature separates them"
        )
    operation = difference[0]
    values = [
        operation in set(left["resolving_operations"]),
        operation in set(right["resolving_operations"]),
    ]
    # Defensive, and deliberately untested: `operation` comes from the symmetric difference, so it
    # is in exactly one of the two sets and the values cannot agree. It stays because the property
    # it asserts is the one that makes the feature a separator rather than a decoration.
    # `scripts/check_genesis_guards_are_tested.py` reports it as a surviving mutant; that is correct
    # and expected.
    if values[0] == values[1]:  # pragma: no cover
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
                "search_exhausted": bool(record.get("search_exhausted")),
                "budget_exhausted": bool(record.get("budget_exhausted")),
                "instrument_failure": bool(record.get("instrument_failure")),
            }
            for record in diagnosis["probes"]
        ],
        resolves_with_new_component=True,
        # The composition that actually reached the demand travels with the certificate. Discarding
        # it and passing a boolean threw away the positive half of the argument.
        resolving_composition=diagnosis.get("resolving_composition"),
    )
