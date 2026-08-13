"""Constructing a transformation under whatever language it is handed. Nothing else.

This module is deliberately separate from the lineage's development code. It imports the
interpreter and the requirement schema and **not** the assembly substrate, the candidate
enumerator, the validator or the acquisition loop. A process holding only this module and a
serialized language state can build and run transformations in that language, and has no way to
reconstruct a primitive the state does not contain.

That is what makes the fresh-process claim mean something. If the persistence check imported the
development modules it would prove that the extension can be rebuilt, which is not the question.
The question is whether the extension **survives** as state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m090_language import (
    CONST_VALUES,
    INPUT_COUNT,
    SLOT_COUNT,
    UNARY_OPERATORS,
    LanguageError,
    MetaLanguageState,
    execute,
    run_body,
)
from metamorphosis.m091_worlds import invariant_violations, required_slots, validate_world


SEARCH_LENGTH = 4
# Two complete searches to depth six, against depth four everywhere else. That is every program
# the inherited language admits at a length half again as long as anything the extended language
# needed, and it closes nothing — because closure is not a budget question.
BUDGET_SEARCH_LENGTH = 6
BUDGET_REPETITIONS = 2

_ARGUMENT_DOMAINS: dict[str, tuple[object, ...]] = {
    "slot": tuple(range(SLOT_COUNT)),
    "input": tuple(range(INPUT_COUNT)),
    "const": tuple(CONST_VALUES),
    "unary_op": tuple(UNARY_OPERATORS),
}


class SearchError(RuntimeError):
    """Raised when a search violates its own contract."""


def parameter_bindings(kinds: Sequence[str]) -> tuple[tuple[object, ...], ...]:
    """Every legal call of a primitive with this signature, in a deterministic order."""

    bindings: list[tuple[object, ...]] = [()]
    for kind in kinds:
        if kind not in _ARGUMENT_DOMAINS:
            raise SearchError(f"unknown parameter kind {kind!r}")
        bindings = [item + (choice,) for item in bindings for choice in _ARGUMENT_DOMAINS[kind]]
    return tuple(bindings)


def operation_alphabet(
    language: MetaLanguageState,
) -> tuple[tuple[str, tuple[object, ...]], ...]:
    """Every call the language admits, over every legal binding, in a deterministic order.

    Read from the state and from nowhere else. A language missing an operation simply has fewer
    letters, which is why deleting a primitive is not a cosmetic act.
    """

    alphabet: list[tuple[str, tuple[object, ...]]] = []
    for definition in sorted(language.primitives, key=lambda item: item.primitive_id):
        for binding in parameter_bindings(definition.parameter_kinds):
            alphabet.append((definition.primitive_id, binding))
    return tuple(alphabet)


def step(
    language: MetaLanguageState, operation: tuple[str, tuple[object, ...]],
    slots: Sequence[int], inputs: Sequence[int],
) -> list[int]:
    """One operation, through the same authority `execute` uses: a lookup in the state."""

    name, arguments = operation
    definition = language.definition(name)
    if definition is None:
        raise LanguageError(f"operation {name!r} is not defined")
    if len(arguments) != definition.arity:
        raise LanguageError(f"{name!r} received the wrong number of arguments")
    return run_body(definition.body, arguments, slots, inputs)


@dataclass
class SearchOutcome:
    found: bool
    program: tuple[tuple[str, tuple[object, ...]], ...] | None
    programs_examined: int
    distinct_behaviours: int
    max_length: int
    repetitions: int
    uses_acquired_primitive: bool
    verified_through_execute: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "found": self.found,
            "program": [[name, list(arguments)] for name, arguments in (self.program or ())],
            "programs_examined": self.programs_examined,
            "distinct_behaviours": self.distinct_behaviours,
            "max_length": self.max_length,
            "repetitions": self.repetitions,
            "uses_acquired_primitive": self.uses_acquired_primitive,
            "verified_through_execute": self.verified_through_execute,
        }


def search_transformation(
    world: Mapping[str, object], language: MetaLanguageState, *,
    max_length: int = SEARCH_LENGTH, repetitions: int = 1,
) -> SearchOutcome:
    """Breadth-first construction of a program meeting the requirement on the public instances.

    Programs whose observable effect on every public instance is already reached by an earlier,
    shorter program are not expanded again. Two programs the lineage cannot tell apart give it no
    reason to prefer one, so collapsing them changes no outcome; it is what makes an exhaustive
    search to depth six affordable, and both counts are reported so the saving is visible rather
    than hidden.

    Every repetition is a **complete** independent search. PR #135 forced that correction on M087
    and PR #136 re-checked it on M088: a budget arm multiplies work, not a counter.
    """

    validate_world(world)
    alphabet = operation_alphabet(language)
    acquired = {item.primitive_id for item in language.primitives if item.origin == "acquired"}
    instances = tuple(
        tuple(int(value) for value in item["inputs"])  # type: ignore[index]
        for item in world["public_instances"]  # type: ignore[index]
    )
    targets = tuple(required_slots(world, inputs) for inputs in instances)
    start = tuple(tuple([0] * SLOT_COUNT) for _ in instances)

    examined = 0
    distinct = 0
    outcome: SearchOutcome | None = None

    for _repetition in range(max(1, repetitions)):
        found: tuple[tuple[str, tuple[object, ...]], ...] | None = None
        seen: set[tuple[tuple[int, ...], ...]] = {start}
        frontier: list[
            tuple[tuple[tuple[str, tuple[object, ...]], ...], tuple[tuple[int, ...], ...]]
        ] = [((), start)]
        for _depth in range(max_length):
            following: list[
                tuple[tuple[tuple[str, tuple[object, ...]], ...], tuple[tuple[int, ...], ...]]
            ] = []
            for program, state in frontier:
                for operation in alphabet:
                    examined += 1
                    try:
                        after = tuple(
                            tuple(step(language, operation, slots, inputs))
                            for slots, inputs in zip(state, instances, strict=True)
                        )
                    except LanguageError:
                        continue
                    if after in seen:
                        continue
                    seen.add(after)
                    candidate = program + (operation,)
                    if after == targets:
                        found = candidate
                        break
                    following.append((candidate, after))
                if found is not None:
                    break
            if found is not None:
                break
            frontier = following
        distinct = max(distinct, len(seen))
        verified = False
        if found is not None:
            verified = all(
                execute(found, inputs, language) == target
                for inputs, target in zip(instances, targets, strict=True)
            )
        current = SearchOutcome(
            found is not None, found, examined, distinct, max_length, max(1, repetitions),
            bool(found) and any(name in acquired for name, _ in found), verified,
        )
        if outcome is None:
            outcome = current
        elif (outcome.found, outcome.program) != (current.found, current.program):
            raise SearchError("repeated complete searches disagreed; the arm is not deterministic")
        outcome = SearchOutcome(
            current.found, current.program, examined, distinct, max_length, max(1, repetitions),
            current.uses_acquired_primitive, current.verified_through_execute,
        )
    assert outcome is not None
    return outcome


def evaluate_on_hidden(
    program: Sequence[tuple[str, tuple[object, ...]]] | None, world: Mapping[str, object],
    language: MetaLanguageState,
) -> dict[str, object]:
    """Score a transformation on instances it never saw, against the world's own invariants."""

    hidden = list(world.get("hidden_instances", ()))  # type: ignore[arg-type]
    passed = 0
    violations: list[str] = []
    for instance in hidden:
        inputs = [int(value) for value in instance["inputs"]]
        slots: list[int] | None
        try:
            slots = list(execute(tuple(program or ()), inputs, language))
        except LanguageError:
            slots = None
        problems = invariant_violations(world, inputs, slots)
        if problems:
            violations.extend(f"{instance.get('instance_id', '?')}: {item}" for item in problems)
        else:
            passed += 1
    return {
        "hidden_total": len(hidden),
        "hidden_passed": passed,
        "world_invariant_violations": violations[:10],
        "world_invariants_hold": bool(hidden) and passed == len(hidden),
    }


def encounter(
    world: Mapping[str, object], language: MetaLanguageState, *,
    max_length: int = SEARCH_LENGTH, repetitions: int = 1,
) -> dict[str, object]:
    """One world, faced under one language: construct, then be judged on what was held out."""

    outcome = search_transformation(
        world, language, max_length=max_length, repetitions=repetitions,
    )
    scored = evaluate_on_hidden(outcome.program, world, language)
    return {
        "world_id": world["world_id"],
        "family": world["family"],
        "language_digest": language.digest(),
        "language_version": language.language_version,
        "search": outcome.to_dict(),
        **scored,
        "correct": bool(outcome.found and scored["world_invariants_hold"]),
    }


__all__ = [
    "BUDGET_REPETITIONS", "BUDGET_SEARCH_LENGTH", "SEARCH_LENGTH", "SearchError", "SearchOutcome",
    "encounter", "evaluate_on_hidden", "operation_alphabet", "parameter_bindings",
    "search_transformation", "step",
]
