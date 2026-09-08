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

This is DEVELOPMENT machinery, not a claim that this tiny language is general or open-ended.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Iterable, Mapping, Sequence

from genesis.artifacts import ConfiguredBody
from genesis.probe import resolve_registry

PROGRAM_SCHEMA = "genesis-generated-program-v1"
PROGRAM_TARGET = "genesis.programs:program_body"


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


def artifact(
    *,
    registry_reference: str,
    operations: Sequence[str],
    input_field: str = "input",
    dependencies: Iterable[str] = (),
) -> ConfiguredBody:
    """Build one generated executable artifact from canonical program data."""
    names = tuple(str(name) for name in operations)
    if not names:
        raise ProgramError("cannot build an empty generated program")
    return ConfiguredBody(
        target=PROGRAM_TARGET,
        configuration={
            "program_schema": PROGRAM_SCHEMA,
            "registry_reference": str(registry_reference),
            "operations": list(names),
            "input_field": str(input_field),
        },
        dependencies=frozenset(str(name) for name in dependencies),
    )


def enumerate_artifacts(
    *,
    registry_reference: str,
    operation_names: Sequence[str],
    max_length: int,
    max_candidates: int,
    input_field: str = "input",
    dependencies: Iterable[str] = (),
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
            )
            emitted += 1
