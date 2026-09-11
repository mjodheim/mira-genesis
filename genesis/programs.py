"""Bounded executable programs represented as canonical data rather than generated Python code.

The current integrated controller can select an importable body the host already installed in a
``World``. That is useful orchestration and it is not transformation generation. This module provides
the first deliberately small generated-body language: a program is an ordered composition of named
primitive operations over one task input field.

The *program* is data. A fixed interpreter is host apparatus and runs inside the existing candidate
sandbox only after its isolation limits exist. No pickle, ``eval``, ``exec`` or generated import is
needed. ``ConfiguredBody`` binds the interpreter target plus the canonical program configuration, so
two different generated programs are different executable artifacts and structural ablation remains
available when dependencies are declared.

A migrated generated body may use another compatible interpreter target. The integrated runtime can
scope candidate construction to the target of the currently executing configured program, so body,
policy and MetaPolicy evaluations all see the same form without a process-global mutable default.
The target remains executable apparatus and is not chosen by the trust root; this only keeps a form
change from being silently undone by the next generated descendant.

This is DEVELOPMENT machinery, not a claim that this tiny language is general or open-ended.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from itertools import product
from typing import Any, Iterable, Mapping, Sequence

from genesis.artifacts import ConfiguredBody
from genesis.probe import resolve_registry

PROGRAM_SCHEMA = "genesis-generated-program-v1"
PROGRAM_TARGET = "genesis.programs:program_body"
_ACTIVE_INTERPRETER_TARGET: ContextVar[str] = ContextVar(
    "genesis_program_interpreter_target", default=PROGRAM_TARGET
)


class ProgramError(RuntimeError):
    """Raised when a generated program or search space is not reconstructible."""


class ProgramBody:
    """Interpret one canonical operation sequence over a task field."""

    def __init__(
        self,
        *,
        program_schema: str,
        registry_reference: str,
        operations: Sequence[str],
        input_field: str,
        capabilities: Iterable[str] = (),
    ) -> None:
        if program_schema != PROGRAM_SCHEMA:
            raise ProgramError("generated program uses an unrecognised schema")
        if not isinstance(registry_reference, str) or not registry_reference:
            raise ProgramError("generated program names no operation registry")
        if not isinstance(input_field, str) or not input_field:
            raise ProgramError("generated program names no input field")
        names = tuple(str(name) for name in operations)
        if not names:
            raise ProgramError("generated program contains no operation")
        registry = resolve_registry(registry_reference)
        missing = [name for name in names if name not in registry]
        if missing:
            raise ProgramError(
                "generated program names operations outside the admitted registry: %s"
                % ", ".join(sorted(set(missing)))
            )
        self.registry_reference = registry_reference
        self.operations = names
        self.input_field = input_field
        self.capabilities = frozenset(str(name) for name in capabilities)
        self._registry = registry

    def attempt(self, task: Mapping[str, Any]) -> Any:
        value = task[self.input_field]
        for name in self.operations:
            value = self._registry[name](value)
        return value


def program_body(
    *,
    program_schema: str,
    registry_reference: str,
    operations: Sequence[str],
    input_field: str = "input",
    capabilities: Iterable[str] = (),
) -> ProgramBody:
    """Importable fixed interpreter target used by ``ConfiguredBody``."""
    return ProgramBody(
        program_schema=program_schema,
        registry_reference=registry_reference,
        operations=operations,
        input_field=input_field,
        capabilities=capabilities,
    )


def interpreter_target_of(body_factory: Any) -> str:
    """Return the generated-program interpreter form currently embodied by a lineage.

    Only a ``ConfiguredBody`` whose immutable configuration is recognisably a generated program can
    propagate its target. An unrelated configured artifact does not get to redefine how future
    program candidates are built. If a migrated target cannot actually interpret the same canonical
    configuration, candidate execution fails closed in the ordinary sandbox; there is no fallback to
    the old target after seeing the failure.
    """
    if isinstance(body_factory, ConfiguredBody):
        configuration = body_factory.configuration
        if (
            configuration.get("program_schema") == PROGRAM_SCHEMA
            and isinstance(configuration.get("registry_reference"), str)
            and configuration.get("operations")
            and isinstance(configuration.get("input_field"), str)
        ):
            return str(body_factory.target)
    return PROGRAM_TARGET


@contextmanager
def inherit_interpreter_form(body_factory: Any):
    """Use one lineage body's program form for every nested generated candidate construction.

    ``ContextVar`` keeps the binding scoped to this runtime call and safe across independent async
    contexts. It is reset unconditionally on exit, so evaluating one migrated lineage cannot change
    the default form later used by another lineage in the same process.
    """
    token = _ACTIVE_INTERPRETER_TARGET.set(interpreter_target_of(body_factory))
    try:
        yield _ACTIVE_INTERPRETER_TARGET.get()
    finally:
        _ACTIVE_INTERPRETER_TARGET.reset(token)


def artifact(
    *,
    registry_reference: str,
    operations: Sequence[str],
    input_field: str = "input",
    dependencies: Iterable[str] = (),
    interpreter_target: str | None = None,
) -> ConfiguredBody:
    """Build one generated executable artifact from canonical program data."""
    names = tuple(str(name) for name in operations)
    if not names:
        raise ProgramError("cannot build an empty generated program")
    return ConfiguredBody(
        target=str(interpreter_target or _ACTIVE_INTERPRETER_TARGET.get()),
        configuration={
            "program_schema": PROGRAM_SCHEMA,
            "registry_reference": str(registry_reference),
            "operations": list(names),
            "input_field": str(input_field),
        },
        dependencies=frozenset(str(name) for name in dependencies),
    )


def descendant_artifact(
    current_body_factory: Any,
    *,
    registry_reference: str,
    operations: Sequence[str],
    input_field: str = "input",
    dependencies: Iterable[str] = (),
) -> ConfiguredBody:
    """Build a generated descendant explicitly in the current generated body's executable form."""
    return artifact(
        registry_reference=registry_reference,
        operations=operations,
        input_field=input_field,
        dependencies=dependencies,
        interpreter_target=interpreter_target_of(current_body_factory),
    )


def enumerate_artifacts(
    *,
    registry_reference: str,
    operation_names: Sequence[str],
    max_length: int,
    max_candidates: int,
    input_field: str = "input",
    dependencies: Iterable[str] = (),
    interpreter_target: str | None = None,
):
    """Deterministically enumerate a bounded generated-program search space.

    The order is part of the search record: caller-supplied operation order, then increasing program
    length, then lexical product order induced by that sequence. The function yields at most
    ``max_candidates`` artifacts even when the cartesian space is larger.
    """
    if max_length <= 0:
        raise ProgramError("generated search max_length must be positive")
    if max_candidates <= 0:
        raise ProgramError("generated search max_candidates must be positive")
    names = tuple(str(name) for name in operation_names)
    if not names:
        raise ProgramError("generated search contains no admitted operation")
    if len(set(names)) != len(names):
        raise ProgramError("generated search operation list contains a duplicate")
    registry = resolve_registry(registry_reference)
    missing = [name for name in names if name not in registry]
    if missing:
        raise ProgramError(
            "generated search names operations outside the admitted registry: %s"
            % ", ".join(sorted(missing))
        )

    emitted = 0
    for length in range(1, int(max_length) + 1):
        for operations in product(names, repeat=length):
            if emitted >= int(max_candidates):
                return
            yield artifact(
                registry_reference=registry_reference,
                operations=operations,
                input_field=input_field,
                dependencies=dependencies,
                interpreter_target=interpreter_target,
            )
            emitted += 1
