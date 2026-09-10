"""A second executable form for generated Genesis programs.

This module exists to make substrate/form continuation a real executable distinction instead of a
renamed route to the original interpreter. ``PortableProgramBody`` consumes the same canonical
program data as ``genesis.programs.ProgramBody`` but compiles the named operation sequence into an
immutable tuple of callables at construction time and executes that compiled tuple thereafter.

The form is intentionally tiny and host-written DEVELOPMENT apparatus. It is not a claim of a new
learning algorithm, portability across arbitrary machines, or open-ended synthesis. Its purpose is
to let the migration boundary change the executable artifact and then test whether later descendants
remain in that changed form after process death.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from genesis.artifacts import ConfiguredBody
from genesis.programs import PROGRAM_SCHEMA
from genesis.probe import resolve_registry

PORTABLE_PROGRAM_TARGET = "genesis.program_forms:portable_program_body"
REBIND_OPERATION = "rebind_program"


class PortableProgramError(RuntimeError):
    """Raised when the alternate form cannot reconstruct an admitted canonical program."""


class PortableProgramBody:
    """Execute a canonical program after compiling its operation names once at construction."""

    def __init__(
        self,
        *,
        program_schema: str,
        registry_reference: str,
        operations: Sequence[str],
        input_field: str,
        required_capabilities: Sequence[str] = (),
        capabilities: Iterable[str] = (),
    ) -> None:
        if program_schema != PROGRAM_SCHEMA:
            raise PortableProgramError("portable form uses an unrecognised program schema")
        if not isinstance(registry_reference, str) or not registry_reference:
            raise PortableProgramError("portable form names no operation registry")
        if not isinstance(input_field, str) or not input_field:
            raise PortableProgramError("portable form names no input field")
        names = tuple(str(name) for name in operations)
        if not names:
            raise PortableProgramError("portable form contains no operation")
        registry = resolve_registry(registry_reference)
        missing = [name for name in names if name not in registry]
        if missing:
            raise PortableProgramError(
                "portable form names operations outside the admitted registry: %s"
                % ", ".join(sorted(set(missing)))
            )
        self.operations = names
        self.input_field = input_field
        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.capabilities = frozenset(str(name) for name in capabilities)
        # This is the executable-form difference: resolve once and retain the compiled route rather
        # than looking up every operation by name on every task attempt.
        self._compiled = tuple(registry[name] for name in names)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "portable generated program is missing retained capabilities: %s"
                % ", ".join(sorted(missing))
            )
        value = task[self.input_field]
        for operation in self._compiled:
            value = operation(value)
        return value


def portable_program_body(
    *,
    program_schema: str,
    registry_reference: str,
    operations: Sequence[str],
    input_field: str = "input",
    required_capabilities: Sequence[str] = (),
    capabilities: Iterable[str] = (),
) -> PortableProgramBody:
    """Importable target used by a migrated ``ConfiguredBody``."""
    return PortableProgramBody(
        program_schema=program_schema,
        registry_reference=registry_reference,
        operations=operations,
        input_field=input_field,
        required_capabilities=required_capabilities,
        capabilities=capabilities,
    )


def portable_target_for(source_target: str) -> str:
    """Substrate capability mapping an admitted generated-program target to this form.

    The function deliberately returns a literal. ``CapabilitySet`` severs module globals before a
    discovered operation is invoked, so a migration cannot obtain this result by reaching through a
    module registry it never discovered.
    """
    if not isinstance(source_target, str) or not source_target:
        raise PortableProgramError("source generated-program target is missing")
    return "genesis.program_forms:portable_program_body"


def _configured_record(departure: Mapping[str, Any]) -> Mapping[str, Any]:
    artifact = departure.get("departure_body_artifact")
    if not isinstance(artifact, Mapping) or artifact.get("kind") != "configured_artifact":
        raise PortableProgramError("departure carries no configured executable artifact")
    configured = artifact.get("configuration")
    if not isinstance(configured, Mapping) or configured.get("schema") != "genesis-configured-body-v1":
        raise PortableProgramError("departure configured artifact cannot be reconstructed")
    program = configured.get("configuration")
    if not isinstance(program, Mapping) or program.get("program_schema") != PROGRAM_SCHEMA:
        raise PortableProgramError("departure body is not a generated canonical program")
    return configured


def translate_current_program(departure: Mapping[str, Any], operations: Mapping[str, Any]):
    """Rebuild the departing generated body in a discovered alternate executable form.

    No program operation, registry, dependency or input-field value is supplied by this translator.
    They are copied from the authenticated departure artifact. The only changed field is the target
    returned by the discovered ``rebind_program`` capability.
    """
    configured = _configured_record(departure)
    program = configured["configuration"]
    handle = operations["rebind_program"]
    target = handle(str(configured.get("target") or ""))
    if target != "genesis.program_forms:portable_program_body":
        raise PortableProgramError("discovered rebind capability returned an unsupported form")
    dependencies = configured.get("dependencies") or []
    if not isinstance(dependencies, list):
        raise PortableProgramError("departure dependencies are not canonical data")
    return ConfiguredBody(
        target=target,
        configuration=dict(program),
        dependencies=frozenset(str(name) for name in dependencies),
        dependency_keyword=str(configured.get("dependency_keyword") or "capabilities"),
    )
