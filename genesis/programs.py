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
_ACTIVE_PARENT_PROGRAM_OPERATIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "genesis_parent_program_operations", default=()
)
_ACTIVE_PARENT_DEPENDENCY: ContextVar[str] = ContextVar(
    "genesis_parent_program_dependency", default=""
)
_ACTIVE_PARENT_ARTIFACT: ContextVar[Mapping[str, Any] | None] = ContextVar(
    "genesis_parent_program_artifact", default=None
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
        required_capabilities: Sequence[str] = (),
        parent_body_artifact: Mapping[str, Any] | None = None,
        parent_prefix_length: int = 0,
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
        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.capabilities = frozenset(str(name) for name in capabilities)
        self._registry = registry
        self._parent_body = None
        self._suffix_names = names
        if parent_body_artifact is not None:
            from genesis.artifacts import reconstruct

            if len(self.required_capabilities) != 1:
                raise ProgramError("a composed generated descendant must name exactly one predecessor")
            prefix_length = int(parent_prefix_length)
            if prefix_length <= 0 or prefix_length >= len(names):
                raise ProgramError("generated descendant carries an invalid parent prefix length")
            parent_factory = reconstruct(parent_body_artifact)
            parent_operations = program_operations_of(parent_factory)
            if parent_operations != names[:prefix_length]:
                raise ProgramError(
                    "generated descendant parent artifact is not the canonical program prefix it claims"
                )
            self._parent_body = parent_factory()
            self._suffix_names = names[prefix_length:]
        elif int(parent_prefix_length):
            raise ProgramError("generated program names a parent prefix without a parent artifact")

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        if self._parent_body is None:
            value = task[self.input_field]
        else:
            value = self._parent_body.attempt(task)
        for name in self._suffix_names:
            value = self._registry[name](value)
        return value


def program_body(
    *,
    program_schema: str,
    registry_reference: str,
    operations: Sequence[str],
    input_field: str = "input",
    required_capabilities: Sequence[str] = (),
    parent_body_artifact: Mapping[str, Any] | None = None,
    parent_prefix_length: int = 0,
    capabilities: Iterable[str] = (),
) -> ProgramBody:
    """Importable fixed interpreter target used by ``ConfiguredBody``."""
    return ProgramBody(
        program_schema=program_schema,
        registry_reference=registry_reference,
        operations=operations,
        input_field=input_field,
        required_capabilities=required_capabilities,
        parent_body_artifact=parent_body_artifact,
        parent_prefix_length=parent_prefix_length,
        capabilities=capabilities,
    )


def program_operations_of(body_factory: Any) -> tuple[str, ...]:
    """Return canonical operations only for a reconstructible generated-program body."""
    if not isinstance(body_factory, ConfiguredBody):
        return ()
    configuration = body_factory.configuration
    operations = configuration.get("operations")
    if (
        configuration.get("program_schema") != PROGRAM_SCHEMA
        or not isinstance(configuration.get("registry_reference"), str)
        or not isinstance(configuration.get("input_field"), str)
        or not isinstance(operations, (list, tuple))
        or not operations
    ):
        return ()
    return tuple(str(name) for name in operations)


def interpreter_target_of(body_factory: Any) -> str:
    """Return the generated-program interpreter form currently embodied by a lineage.

    Only a ``ConfiguredBody`` whose immutable configuration is recognisably a generated program can
    propagate its target. An unrelated configured artifact does not get to redefine how future
    program candidates are built. If a migrated target cannot actually interpret the same canonical
    configuration, candidate execution fails closed in the ordinary sandbox; there is no fallback to
    the old target after seeing the failure.
    """
    if isinstance(body_factory, ConfiguredBody) and program_operations_of(body_factory):
        return str(body_factory.target)
    return PROGRAM_TARGET


@contextmanager
def inherit_interpreter_form(body_factory: Any, *, dependency: str = ""):
    """Scope generated descendants to the current form and, for strict extensions, predecessor.

    The dependency is inert lineage identity supplied by the runtime from its current acquisition
    history. It is inherited only when a candidate's canonical operation sequence is a *strict
    extension* of the current generated program. A sibling or replacement program therefore cannot
    manufacture causal ancestry merely because a predecessor exists.
    """
    from genesis.trust_root import artifact_digest_of

    parent_operations = program_operations_of(body_factory)
    dependency_name = str(dependency or "") if parent_operations else ""
    parent_artifact = artifact_digest_of(body_factory) if dependency_name else None
    target_token = _ACTIVE_INTERPRETER_TARGET.set(interpreter_target_of(body_factory))
    operations_token = _ACTIVE_PARENT_PROGRAM_OPERATIONS.set(parent_operations)
    dependency_token = _ACTIVE_PARENT_DEPENDENCY.set(dependency_name)
    artifact_token = _ACTIVE_PARENT_ARTIFACT.set(parent_artifact)
    try:
        yield _ACTIVE_INTERPRETER_TARGET.get()
    finally:
        _ACTIVE_PARENT_ARTIFACT.reset(artifact_token)
        _ACTIVE_PARENT_DEPENDENCY.reset(dependency_token)
        _ACTIVE_PARENT_PROGRAM_OPERATIONS.reset(operations_token)
        _ACTIVE_INTERPRETER_TARGET.reset(target_token)


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

    dependency_names = frozenset(str(name) for name in dependencies)
    parent_operations = _ACTIVE_PARENT_PROGRAM_OPERATIONS.get()
    parent_dependency = _ACTIVE_PARENT_DEPENDENCY.get()
    inherited_parent = bool(
        not dependency_names
        and parent_dependency
        and parent_operations
        and len(names) > len(parent_operations)
        and names[: len(parent_operations)] == parent_operations
    )
    if inherited_parent:
        dependency_names = frozenset((parent_dependency,))

    configuration: dict[str, Any] = {
        "program_schema": PROGRAM_SCHEMA,
        "registry_reference": str(registry_reference),
        "operations": list(names),
        "input_field": str(input_field),
    }
    if dependency_names:
        configuration["required_capabilities"] = sorted(dependency_names)
    if inherited_parent:
        parent_artifact = _ACTIVE_PARENT_ARTIFACT.get()
        if not isinstance(parent_artifact, Mapping):
            raise ProgramError("generated descendant lost the executable artifact of its predecessor")
        configuration["parent_body_artifact"] = dict(parent_artifact)
        configuration["parent_prefix_length"] = len(parent_operations)

    return ConfiguredBody(
        target=str(interpreter_target or _ACTIVE_INTERPRETER_TARGET.get()),
        configuration=configuration,
        dependencies=dependency_names,
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
