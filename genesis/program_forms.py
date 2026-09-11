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
from genesis.programs import PROGRAM_SCHEMA, program_operations_of
from genesis.probe import resolve_registry

PORTABLE_PROGRAM_TARGET = "genesis.program_forms:portable_program_body"
REBIND_OPERATION = "rebind_program"
_POLICY_TOOL_NAME = "generated_search_policy"
_POLICY_ROLE = "lineage_search_policy"


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
        parent_body_artifact: Mapping[str, Any] | None = None,
        parent_prefix_length: int = 0,
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
        self._parent_body = None
        suffix_names = names
        if parent_body_artifact is not None:
            from genesis.artifacts import reconstruct

            if len(self.required_capabilities) != 1:
                raise PortableProgramError(
                    "a composed portable descendant must name exactly one predecessor"
                )
            prefix_length = int(parent_prefix_length)
            if prefix_length <= 0 or prefix_length >= len(names):
                raise PortableProgramError("portable descendant carries an invalid parent prefix length")
            parent_factory = reconstruct(parent_body_artifact)
            parent_operations = program_operations_of(parent_factory)
            if parent_operations != names[:prefix_length]:
                raise PortableProgramError(
                    "portable descendant parent artifact is not the canonical program prefix it claims"
                )
            self._parent_body = parent_factory()
            suffix_names = names[prefix_length:]
        elif int(parent_prefix_length):
            raise PortableProgramError("portable program names a parent prefix without a parent artifact")
        # This is the executable-form difference: resolve once and retain the compiled suffix route.
        self._compiled = tuple(registry[name] for name in suffix_names)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "portable generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        if self._parent_body is None:
            value = task[self.input_field]
        else:
            value = self._parent_body.attempt(task)
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
    parent_body_artifact: Mapping[str, Any] | None = None,
    parent_prefix_length: int = 0,
    capabilities: Iterable[str] = (),
) -> PortableProgramBody:
    """Importable target used by a migrated ``ConfiguredBody``."""
    return PortableProgramBody(
        program_schema=program_schema,
        registry_reference=registry_reference,
        operations=operations,
        input_field=input_field,
        required_capabilities=required_capabilities,
        parent_body_artifact=parent_body_artifact,
        parent_prefix_length=parent_prefix_length,
        capabilities=capabilities,
    )


def portable_target_for(source_form: str) -> str:
    """Substrate capability mapping an admitted generated-program form to this form.

    The function deliberately returns a literal. ``CapabilitySet`` severs module globals before a
    discovered operation is invoked, so a migration cannot obtain this result by reaching through a
    module registry it never discovered.
    """
    if not isinstance(source_form, str) or not source_form:
        raise PortableProgramError("source generated-program form is missing")
    return "genesis.program_forms:portable_program_body"


def _held_policy(departure: Mapping[str, Any]) -> Mapping[str, Any]:
    tools = [
        tool
        for tool in departure.get("tools", [])
        if isinstance(tool, Mapping)
        and tool.get("name") == _POLICY_TOOL_NAME
        and tool.get("role") == _POLICY_ROLE
    ]
    if len(tools) != 1 or not isinstance(tools[0].get("artifact"), Mapping):
        raise PortableProgramError("departure carries no unique generated-search policy")
    policy = tools[0]["artifact"]
    registry_reference = policy.get("registry_reference")
    input_field = policy.get("input_field")
    if not isinstance(registry_reference, str) or not registry_reference:
        raise PortableProgramError("departure policy carries no operation registry")
    if not isinstance(input_field, str) or not input_field:
        raise PortableProgramError("departure policy carries no input field")
    return policy


def _latest_generated_operations(departure: Mapping[str, Any]) -> tuple[str, ...]:
    acquisitions = list(departure.get("acquisitions") or [])
    if not acquisitions or not isinstance(acquisitions[-1], Mapping):
        raise PortableProgramError("departure carries no adopted generated body")
    name = str(acquisitions[-1].get("name") or "")
    if not name.startswith("policy-program:") or ":" not in name:
        raise PortableProgramError("latest acquisition is not a policy-generated body")
    encoded = name.rpartition(":")[2]
    operations = tuple(part for part in encoded.split("+") if part)
    if not operations:
        raise PortableProgramError("latest generated-body acquisition names no operations")
    return operations


def translate_current_program(departure: Mapping[str, Any], operations: Mapping[str, Any]):
    """Rebuild the lineage's held generated body in a discovered alternate executable form.

    The translator derives program operations from the lineage's accepted generated-body record and
    derives registry/input identity from its held search policy. It does not receive a host-authored
    replacement program. The one substrate-dependent fact — which executable form to use — comes
    only through the discovered ``rebind_program`` capability.

    This remains host-written translation apparatus. Capability preservation is separately measured
    by ``migration.migrate`` before the new body becomes current.
    """
    policy = _held_policy(departure)
    program_operations = _latest_generated_operations(departure)
    handle = operations["rebind_program"]
    target = handle("canonical-generated-program")
    if target != "genesis.program_forms:portable_program_body":
        raise PortableProgramError("discovered rebind capability returned an unsupported form")
    return ConfiguredBody(
        target=target,
        configuration={
            "program_schema": PROGRAM_SCHEMA,
            "registry_reference": str(policy["registry_reference"]),
            "operations": list(program_operations),
            "input_field": str(policy["input_field"]),
        },
        dependencies=frozenset(),
    )
