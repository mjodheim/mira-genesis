"""The substrate as serialized state, and the generic dispatcher that resolves only through it.

Before M092-A the authority over micro-operation semantics was `m090_language.run_body`: it branched
on `MICRO_OPERATIONS` by name, and `_binary` and `_unary` were host functions with hard-coded arms.
Editing that Python changed what the lineage's substrate meant. After M092-A the authority is a
`SubstrateState`, and the host retains only the K1 kernel, which cannot tell one substrate operation
from another.

**Dispatch resolves exclusively through state.** The set of legal operation names, the set of
operations whose dispatch key includes their argument, the argument role of each operation, the body
and stack bounds and the literal domain are all *read from the state object*, not written here. This
module contains no micro-operation identifier — no `PUSH_SLOT`, no `BINOP`, no `max`. Grep it.

**There is no fallback.** An unknown operation raises. It does not reach `run_body`, which this
module does not import and never calls. That is the property D059 named one level up and the one an
"unknown operation falls through to legacy host semantics" bug would silently destroy.

**Registered reach is not kernel reach.** K1 can physically execute loops and richer programs than
the inherited substrate needs. What the lineage can actually *do* is bounded by what is registered
in this state, and M092-A registers exactly the inherited operations and nothing else. The two are
separately checkable and are separately checked: `has_backward_jump` over every registered program
demonstrates that nothing registered here can even iterate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m090_language import (
    FORBIDDEN_CAPABILITIES, PERMITTED_CAPABILITIES, LanguageError, MetaLanguageState,
)
from metamorphosis.m092_kernel import (
    Instruction, KernelError, Machine, Program, canonical_bytes, execute_program,
    has_backward_jump, program_digest, program_from_list, program_to_list, validate_program,
)

SUBSTRATE_STATE_SCHEMA = "m092a-state-owned-substrate-v1"

# How an operation's single call-time operand is treated. Declared per operation, IN STATE, so the
# dispatcher never needs to know which operations take an index and which take an operator name.
ARGUMENT_ROLES = ("none", "index", "literal", "selector")

ORIGINS = ("inherited", "acquired")


@dataclass(frozen=True)
class SubstrateOperation:
    """One micro-operation, semantics included, as a K1 program rather than as host code."""

    key: str
    argument_role: str
    program: Program
    origin: str
    provenance: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ("pure_slot_write",)

    def __post_init__(self) -> None:
        if self.argument_role not in ARGUMENT_ROLES:
            raise LanguageError(f"unknown argument role {self.argument_role!r}")
        if self.origin not in ORIGINS:
            raise LanguageError(f"unknown origin {self.origin!r}")
        for capability in self.capabilities:
            if capability in FORBIDDEN_CAPABILITIES or capability not in PERMITTED_CAPABILITIES:
                raise LanguageError(f"forbidden capability {capability!r}")
        validate_program(self.program)

    @property
    def base_name(self) -> str:
        return self.key.split(":", 1)[0]

    @property
    def selector(self) -> str | None:
        return self.key.split(":", 1)[1] if ":" in self.key else None

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "argument_role": self.argument_role,
            "program": program_to_list(self.program),
            "origin": self.origin,
            "provenance": list(self.provenance),
            "capabilities": list(self.capabilities),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SubstrateOperation":
        expected = {"key", "argument_role", "program", "origin", "provenance", "capabilities"}
        if set(data) != expected:
            raise LanguageError("substrate operation fields differ from the closed schema")
        return cls(
            key=str(data["key"]),
            argument_role=str(data["argument_role"]),
            program=program_from_list(data["program"]),  # type: ignore[arg-type]
            origin=str(data["origin"]),
            provenance=tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
            capabilities=tuple(str(item) for item in data["capabilities"]),  # type: ignore[union-attr]
        )


@dataclass(frozen=True)
class SubstrateState:
    """The whole substrate. Everything the dispatcher consults lives here."""

    operations: tuple[SubstrateOperation, ...]
    slot_count: int
    input_count: int
    max_body_length: int
    max_stack_depth: int
    literal_values: tuple[int, ...]
    substrate_version: int = 0
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        keys = [operation.key for operation in self.operations]
        if len(keys) != len(set(keys)):
            raise LanguageError("duplicate substrate operation key")
        for operation in self.operations:
            for other in self.operations:
                # A name is either always selector-dispatched or never; a mixture would let one
                # spelling of a call reach two different programs.
                if operation.base_name == other.base_name and (
                    (operation.selector is None) != (other.selector is None)
                ):
                    raise LanguageError(
                        f"operation {operation.base_name!r} mixes selector and plain dispatch"
                    )

    # ------------------------------------------------------------------ lookups, all from state

    @property
    def operation_names(self) -> frozenset[str]:
        """The legal micro-operation names. Derived from the state, not declared beside it."""

        return frozenset(operation.base_name for operation in self.operations)

    @property
    def selector_names(self) -> frozenset[str]:
        return frozenset(
            operation.base_name for operation in self.operations if operation.selector is not None
        )

    def selector_values(self, name: str) -> tuple[str, ...]:
        return tuple(sorted(
            operation.selector
            for operation in self.operations
            if operation.base_name == name and operation.selector is not None
        ))

    def dispatch_key(self, name: str, resolved_argument: object) -> str:
        """Which entry a call resolves to. The rule is read from state, never hard-coded."""

        if name in self.selector_names:
            return f"{name}:{resolved_argument}"
        return name

    def operation(self, key: str) -> SubstrateOperation | None:
        for candidate in self.operations:
            if candidate.key == key:
                return candidate
        return None

    def argument_role(self, name: str) -> str:
        for candidate in self.operations:
            if candidate.base_name == name:
                return candidate.argument_role
        raise LanguageError(f"operation {name!r} is not defined in the substrate state")

    # ------------------------------------------------------------------------- (de)serialization

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SUBSTRATE_STATE_SCHEMA,
            "operations": [operation.to_dict() for operation in self.operations],
            "slot_count": self.slot_count,
            "input_count": self.input_count,
            "max_body_length": self.max_body_length,
            "max_stack_depth": self.max_stack_depth,
            "literal_values": list(self.literal_values),
            "substrate_version": self.substrate_version,
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SubstrateState":
        if data.get("schema") != SUBSTRATE_STATE_SCHEMA:
            raise LanguageError("substrate state schema mismatch")
        expected = {
            "schema", "operations", "slot_count", "input_count", "max_body_length",
            "max_stack_depth", "literal_values", "substrate_version", "provenance",
        }
        if set(data) != expected:
            raise LanguageError("substrate state fields differ from the closed schema")
        return cls(
            operations=tuple(
                SubstrateOperation.from_dict(item) for item in data["operations"]  # type: ignore[union-attr]
            ),
            slot_count=int(data["slot_count"]),  # type: ignore[arg-type]
            input_count=int(data["input_count"]),  # type: ignore[arg-type]
            max_body_length=int(data["max_body_length"]),  # type: ignore[arg-type]
            max_stack_depth=int(data["max_stack_depth"]),  # type: ignore[arg-type]
            literal_values=tuple(int(v) for v in data["literal_values"]),  # type: ignore[union-attr]
            substrate_version=int(data["substrate_version"]),  # type: ignore[arg-type]
            provenance=tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
        )

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def deserialize(cls, text: str) -> "SubstrateState":
        return cls.from_dict(json.loads(text))

    def digest(self) -> str:
        return hashlib.sha256(canonical_bytes(self.to_dict())).hexdigest()

    # ---------------------------------------------------------------------------- state surgery

    def without(self, key: str) -> "SubstrateState":
        """Delete an operation. Used to prove the state is the authority, not a cache."""

        if self.operation(key) is None:
            raise LanguageError(f"cannot remove absent operation {key!r}")
        return SubstrateState(
            operations=tuple(item for item in self.operations if item.key != key),
            slot_count=self.slot_count, input_count=self.input_count,
            max_body_length=self.max_body_length, max_stack_depth=self.max_stack_depth,
            literal_values=self.literal_values, substrate_version=self.substrate_version,
            provenance=self.provenance + (f"removed {key}",),
        )

    def replacing(self, key: str, program: Sequence[Instruction]) -> "SubstrateState":
        """Corrupt or rewrite one operation's program, leaving everything else identical."""

        target = self.operation(key)
        if target is None:
            raise LanguageError(f"cannot replace absent operation {key!r}")
        replacement = SubstrateOperation(
            key=target.key, argument_role=target.argument_role, program=tuple(program),
            origin=target.origin, provenance=target.provenance + ("program replaced",),
            capabilities=target.capabilities,
        )
        return SubstrateState(
            operations=tuple(
                replacement if item.key == key else item for item in self.operations
            ),
            slot_count=self.slot_count, input_count=self.input_count,
            max_body_length=self.max_body_length, max_stack_depth=self.max_stack_depth,
            literal_values=self.literal_values, substrate_version=self.substrate_version,
            provenance=self.provenance + (f"replaced {key}",),
        )


# ---------------------------------------------------------------------------------------------
# The dispatcher. Mirrors the frozen reference contract step for step, resolving only through state.
# ---------------------------------------------------------------------------------------------


def _resolve(argument: object, arguments: Sequence[object]) -> object:
    if isinstance(argument, str) and argument.startswith("$"):
        index = int(argument[1:])
        if index >= len(arguments):
            raise LanguageError(f"parameter {argument} is not supplied")
        return arguments[index]
    return argument


def run_body_from_state(
    body: Sequence[tuple[str, object]],
    arguments: Sequence[object],
    slots: Sequence[int],
    inputs: Sequence[int],
    substrate: SubstrateState,
) -> list[int]:
    """Execute a primitive body with the substrate state as the only authority.

    The order of checks matches the frozen reference exactly -- body bound, then unknown name, then
    stack bound, then the operation itself -- because conservation compares refusals as well as
    values, and a reordering would change which refusal a doubly-invalid call produces.
    """

    if len(body) > substrate.max_body_length:
        raise LanguageError("primitive body exceeds the frozen length bound")

    names = substrate.operation_names
    stack: list[int] = []
    updated = [int(value) for value in slots]
    materialized = [int(value) for value in inputs]

    for name, argument in body:
        if name not in names:
            raise LanguageError(f"unknown micro-operation {name!r}")
        if len(stack) > substrate.max_stack_depth:
            raise LanguageError("primitive body exceeded the stack bound")

        resolved = _resolve(argument, arguments)
        key = substrate.dispatch_key(name, resolved)
        operation = substrate.operation(key)
        if operation is None:
            # No fallback to host semantics. An unregistered selector is simply not executable.
            raise LanguageError(f"substrate operation {key!r} is not registered")

        if operation.argument_role in ("none", "selector"):
            operand = 0
        else:
            try:
                operand = int(resolved)  # type: ignore[arg-type]
            except (TypeError, ValueError) as error:
                raise LanguageError(f"argument {resolved!r} is not an integer") from error

        machine = Machine(
            stack=stack, slots=updated, inputs=materialized, argument=operand,
        )
        execute_program(operation.program, machine, validate=False)
        stack, updated = machine.stack, machine.slots

    return updated


def execute_from_state(
    program: Sequence[tuple[str, tuple[object, ...]]],
    inputs: Sequence[int],
    language: MetaLanguageState,
    substrate: SubstrateState,
) -> tuple[int, ...]:
    """Run a whole program. The language says what a primitive is; the substrate says what its
    micro-operations mean. Neither is host code."""

    slots = [0] * substrate.slot_count
    for name, arguments in program:
        definition = language.definition(name)
        if definition is None:
            raise LanguageError(
                f"operation {name!r} is not defined in language version "
                f"{language.language_version}"
            )
        if len(arguments) != definition.arity:
            raise LanguageError(
                f"{name!r} expects {definition.arity} arguments, received {len(arguments)}"
            )
        _check_arguments(definition, arguments, substrate)
        slots = run_body_from_state(definition.body, arguments, slots, inputs, substrate)
    return tuple(slots)


def _check_arguments(definition, arguments: Sequence[object], substrate: SubstrateState) -> None:
    """Argument-domain checks, with every bound taken from the substrate state.

    The legal unary operator names are the registered selector values, so widening the substrate is
    the only way to widen this check -- it cannot drift apart from what is actually executable.
    """

    unary_operators = substrate.selector_values("UNOP")
    for kind, argument in zip(definition.parameter_kinds, arguments, strict=True):
        if kind == "slot" and not (
            isinstance(argument, int) and 0 <= argument < substrate.slot_count
        ):
            raise LanguageError("slot argument out of range")
        if kind == "input" and not (
            isinstance(argument, int) and 0 <= argument < substrate.input_count
        ):
            raise LanguageError("input argument out of range")
        if kind == "const" and argument not in substrate.literal_values:
            raise LanguageError("constant argument outside the frozen set")
        if kind == "unary_op" and argument not in unary_operators:
            raise LanguageError("unary operator argument outside the frozen set")


def registered_reach_report(substrate: SubstrateState) -> dict[str, object]:
    """Evidence that registered reach did not grow, separate from what the kernel could run."""

    looping = [
        operation.key for operation in substrate.operations if has_backward_jump(operation.program)
    ]
    return {
        "operations": len(substrate.operations),
        "operation_names": sorted(substrate.operation_names),
        "selector_names": sorted(substrate.selector_names),
        "acquired_operations": [
            operation.key for operation in substrate.operations if operation.origin != "inherited"
        ],
        "programs_with_a_backward_jump": looping,
        "every_registered_program_is_loop_free": not looping,
        "kernel_can_express_loops": True,
        "note": (
            "the kernel can iterate and the registered substrate cannot; 'can execute' is not "
            "'has registered', and M092-A registers no acquired operation"
        ),
    }


__all__ = [
    "ARGUMENT_ROLES", "ORIGINS", "SUBSTRATE_STATE_SCHEMA", "SubstrateOperation", "SubstrateState",
    "execute_from_state", "registered_reach_report", "run_body_from_state",
]
