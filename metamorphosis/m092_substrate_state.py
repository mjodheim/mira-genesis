"""The substrate as serialized state, and the generic dispatcher that resolves only through it.

Before M092-A the authority over micro-operation semantics was `m090_language.run_body`: it branched
on `MICRO_OPERATIONS` by name, and `_binary` and `_unary` were host functions with hard-coded arms.
Editing that Python changed what the lineage's substrate meant. After M092-A the authority is a
`SubstrateState`, and the host retains only the K1 kernel, which cannot tell one substrate operation
from another.

**Dispatch resolves exclusively through state, and so does validation.** The legal operation names,
which operations are selector-dispatched, each operation's argument role, the parameter-kind domains,
the capability vocabulary and the body and stack bounds are all *read from the state object*. This
module contains **no** micro-operation identifier and no operator name -- an AST-level test asserts
zero occurrences in executable code, with a positive control proving the scanner can fail.

The first version of this module still named one operation, because the language's `unary_op`
parameter kind had to be validated against *something*. That is now `ParameterDomain`: the state says
"the `unary_op` kind draws its legal values from the selector values of operation X", and X is data.

**There is no fallback.** An unknown operation raises. It does not reach `run_body`, which this
module does not import and cannot reach -- nothing here imports a historical module at all.

**Refusals are semantic.** Every refusal carries a `RefusalCode`, so conservation compares *why* two
implementations refused rather than merely observing that both did.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m092_kernel import (
    Instruction, Machine, Program, execute_program, has_backward_jump, program_from_list,
    program_to_list, validate_program,
)
from metamorphosis.m092_runtime import (
    RefusalCode, RuntimeLanguage, RuntimePrimitive, SubstrateError, digest_of,
)

SUBSTRATE_STATE_SCHEMA = "m092a-state-owned-substrate-v2"

# How an operation's single call-time operand is treated. Declared per operation, IN STATE, so the
# dispatcher never needs to know which operations take an index and which take an operator name.
ARGUMENT_ROLES = ("none", "index", "literal", "selector")

# How a language-level parameter kind is validated. Also declared in state.
DOMAIN_RULES = ("slot_index", "input_index", "literal_set", "selector_of")

ORIGINS = ("inherited", "acquired")


@dataclass(frozen=True)
class ParameterDomain:
    """Where a language parameter kind draws its legal values from. Data, not code.

    `selector_of` is the reason this type exists: the legal values of a parameter kind can be
    *the selector values registered for some operation*, which keeps the domain and what is actually
    executable from drifting apart -- and keeps the operation's name out of the dispatcher.
    """

    kind: str
    rule: str
    reference: str = ""

    def __post_init__(self) -> None:
        if self.rule not in DOMAIN_RULES:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, f"unknown domain rule {self.rule!r}")
        if (self.rule == "selector_of") != bool(self.reference):
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, "selector_of needs a reference and others must not",
            )

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "rule": self.rule, "reference": self.reference}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ParameterDomain":
        if set(data) != {"kind", "rule", "reference"}:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, "parameter domain schema mismatch")
        return cls(str(data["kind"]), str(data["rule"]), str(data["reference"]))


@dataclass(frozen=True)
class SubstrateOperation:
    """One micro-operation, semantics included, as a K1 program rather than as host code."""

    key: str
    argument_role: str
    program: Program
    origin: str
    provenance: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    # How deep the stack must already be for this operation to run. Declared per operation, IN
    # STATE, because the reference checks arity BEFORE it validates a selector -- so a call with
    # both too few operands and an unregistered selector must refuse for the arity, not the
    # selector. Without this the dispatcher resolved the selector first and refused with a
    # different semantic code; `refused == refused` could not see the difference.
    minimum_stack_depth: int = 0

    def __post_init__(self) -> None:
        if self.argument_role not in ARGUMENT_ROLES:
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, f"unknown argument role {self.argument_role!r}",
            )
        if self.origin not in ORIGINS:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, f"unknown origin {self.origin!r}")
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
            "minimum_stack_depth": self.minimum_stack_depth,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SubstrateOperation":
        expected = {
            "key", "argument_role", "program", "origin", "provenance", "capabilities",
            "minimum_stack_depth",
        }
        if set(data) != expected:
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, "operation fields differ from the closed schema",
            )
        return cls(
            key=str(data["key"]),
            argument_role=str(data["argument_role"]),
            program=program_from_list(data["program"]),  # type: ignore[arg-type]
            origin=str(data["origin"]),
            provenance=tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
            capabilities=tuple(str(item) for item in data["capabilities"]),  # type: ignore[union-attr]
            minimum_stack_depth=int(data["minimum_stack_depth"]),  # type: ignore[arg-type]
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
    parameter_domains: tuple[ParameterDomain, ...] = ()
    permitted_capabilities: tuple[str, ...] = ()
    forbidden_capabilities: tuple[str, ...] = ()
    substrate_version: int = 0
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        keys = [operation.key for operation in self.operations]
        if len(keys) != len(set(keys)):
            raise SubstrateError(RefusalCode.MALFORMED_STATE, "duplicate operation key")
        permitted, forbidden = set(self.permitted_capabilities), set(self.forbidden_capabilities)
        for operation in self.operations:
            held = set(operation.capabilities)
            if held & forbidden or not held <= permitted:
                raise SubstrateError(
                    RefusalCode.MALFORMED_STATE,
                    f"{operation.key} holds a capability outside the declared vocabulary",
                )
            for other in self.operations:
                # A name is either always selector-dispatched or never; a mixture would let one
                # spelling of a call reach two different programs.
                if operation.base_name == other.base_name and (
                    (operation.selector is None) != (other.selector is None)
                ):
                    raise SubstrateError(
                        RefusalCode.MALFORMED_STATE,
                        f"{operation.base_name!r} mixes selector and plain dispatch",
                    )
        for domain in self.parameter_domains:
            if domain.rule == "selector_of" and domain.reference not in self.selector_names:
                raise SubstrateError(
                    RefusalCode.MALFORMED_STATE,
                    f"domain {domain.kind!r} references unregistered {domain.reference!r}",
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

    def minimum_stack_depth(self, name: str) -> int:
        """How deep the stack must be before any entry under `name` may run.

        Every entry sharing a base name must agree, so an unregistered selector still has a
        well-defined arity -- which is exactly the case the reference checks before it looks at the
        operator at all.
        """

        declared = {
            operation.minimum_stack_depth
            for operation in self.operations
            if operation.base_name == name
        }
        if len(declared) > 1:
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, f"{name!r} declares inconsistent stack arity",
            )
        return next(iter(declared), 0)

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

    def domain(self, kind: str) -> ParameterDomain | None:
        return next((item for item in self.parameter_domains if item.kind == kind), None)

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
            "parameter_domains": [item.to_dict() for item in self.parameter_domains],
            "permitted_capabilities": list(self.permitted_capabilities),
            "forbidden_capabilities": list(self.forbidden_capabilities),
            "substrate_version": self.substrate_version,
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SubstrateState":
        if data.get("schema") != SUBSTRATE_STATE_SCHEMA:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, "substrate state schema mismatch")
        expected = {
            "schema", "operations", "slot_count", "input_count", "max_body_length",
            "max_stack_depth", "literal_values", "parameter_domains", "permitted_capabilities",
            "forbidden_capabilities", "substrate_version", "provenance",
        }
        if set(data) != expected:
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, "state fields differ from the closed schema",
            )
        return cls(
            operations=tuple(
                SubstrateOperation.from_dict(item) for item in data["operations"]  # type: ignore[union-attr]
            ),
            slot_count=int(data["slot_count"]),  # type: ignore[arg-type]
            input_count=int(data["input_count"]),  # type: ignore[arg-type]
            max_body_length=int(data["max_body_length"]),  # type: ignore[arg-type]
            max_stack_depth=int(data["max_stack_depth"]),  # type: ignore[arg-type]
            literal_values=tuple(int(v) for v in data["literal_values"]),  # type: ignore[union-attr]
            parameter_domains=tuple(
                ParameterDomain.from_dict(item) for item in data["parameter_domains"]  # type: ignore[union-attr]
            ),
            permitted_capabilities=tuple(
                str(c) for c in data["permitted_capabilities"]  # type: ignore[union-attr]
            ),
            forbidden_capabilities=tuple(
                str(c) for c in data["forbidden_capabilities"]  # type: ignore[union-attr]
            ),
            substrate_version=int(data["substrate_version"]),  # type: ignore[arg-type]
            provenance=tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
        )

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def deserialize(cls, text: str) -> "SubstrateState":
        return cls.from_dict(json.loads(text))

    def digest(self) -> str:
        return digest_of(self.to_dict())

    # ---------------------------------------------------------------------------- state surgery

    def _replaced(self, operations, note: str) -> "SubstrateState":
        return SubstrateState(
            operations=tuple(operations),
            slot_count=self.slot_count, input_count=self.input_count,
            max_body_length=self.max_body_length, max_stack_depth=self.max_stack_depth,
            literal_values=self.literal_values, parameter_domains=self.parameter_domains,
            permitted_capabilities=self.permitted_capabilities,
            forbidden_capabilities=self.forbidden_capabilities,
            substrate_version=self.substrate_version, provenance=self.provenance + (note,),
        )

    def without(self, key: str) -> "SubstrateState":
        """Delete an operation. Used to prove the state is the authority, not a cache."""

        if self.operation(key) is None:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, f"absent operation {key!r}")
        return self._replaced(
            (item for item in self.operations if item.key != key), f"removed {key}",
        )

    def replacing(self, key: str, program: Sequence[Instruction]) -> "SubstrateState":
        """Corrupt or rewrite one operation's program, leaving everything else identical."""

        target = self.operation(key)
        if target is None:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, f"absent operation {key!r}")
        replacement = SubstrateOperation(
            key=target.key, argument_role=target.argument_role, program=tuple(program),
            origin=target.origin, provenance=target.provenance + ("program replaced",),
            capabilities=target.capabilities,
            # Carried over deliberately: rewriting a program must change its semantics, not its
            # declared arity. Dropping this made sibling selectors disagree and the state
            # malformed, which is a corruption of the edit rather than of the operation.
            minimum_stack_depth=target.minimum_stack_depth,
        )
        return self._replaced(
            (replacement if item.key == key else item for item in self.operations),
            f"replaced {key}",
        )


# ---------------------------------------------------------------------------------------------
# The dispatcher. Mirrors the frozen reference contract step for step, resolving only through state.
# ---------------------------------------------------------------------------------------------


def _resolve(argument: object, arguments: Sequence[object]) -> object:
    if isinstance(argument, str) and argument.startswith("$"):
        index = int(argument[1:])
        if index >= len(arguments):
            raise SubstrateError(RefusalCode.UNRESOLVED_PARAMETER, f"parameter {argument}")
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
    stack bound, then the operation itself -- because conservation compares refusal *codes* as well
    as values, and a reordering would change which refusal a doubly-invalid call produces.
    """

    if len(body) > substrate.max_body_length:
        raise SubstrateError(RefusalCode.BODY_LENGTH_EXCEEDED, "body exceeds the length bound")

    names = substrate.operation_names
    stack: list[int] = []
    updated = [int(value) for value in slots]
    materialized = [int(value) for value in inputs]

    for name, argument in body:
        if name not in names:
            raise SubstrateError(RefusalCode.UNKNOWN_OPERATION, f"{name!r}")
        if len(stack) > substrate.max_stack_depth:
            raise SubstrateError(RefusalCode.STACK_BOUND_EXCEEDED, "stack bound exceeded")

        if len(stack) < substrate.minimum_stack_depth(name):
            # Arity is checked before the selector is resolved, because that is the order the
            # frozen reference uses. Conservation compares refusal codes, so the order matters.
            raise SubstrateError(RefusalCode.STACK_UNDERFLOW, f"{name!r} needs more operands")

        resolved = _resolve(argument, arguments)
        key = substrate.dispatch_key(name, resolved)
        operation = substrate.operation(key)
        if operation is None:
            # No fallback to host semantics. An unregistered selector is simply not executable.
            raise SubstrateError(RefusalCode.INVALID_SELECTOR, f"{key!r} is not registered")

        if operation.argument_role in ("none", "selector"):
            operand = 0
        else:
            try:
                operand = int(resolved)  # type: ignore[arg-type]
            except (TypeError, ValueError) as error:
                raise SubstrateError(
                    RefusalCode.INVALID_ARGUMENT_ROLE, f"{resolved!r} is not an integer",
                ) from error

        machine = Machine(stack=stack, slots=updated, inputs=materialized, argument=operand)
        execute_program(operation.program, machine, validate=False)
        stack, updated = machine.stack, machine.slots

    return updated


def check_arguments(
    definition: RuntimePrimitive, arguments: Sequence[object], substrate: SubstrateState,
) -> None:
    """Argument-domain checks, with every rule and every bound taken from the substrate state.

    No parameter kind and no operation name appears here. The state says which rule a kind uses and,
    for `selector_of`, which operation's registered selectors are its legal values -- so the domain
    cannot drift apart from what is actually executable.
    """

    for kind, argument in zip(definition.parameter_kinds, arguments, strict=True):
        domain = substrate.domain(kind)
        if domain is None:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, f"no domain declared for {kind!r}")
        if domain.rule == "slot_index":
            legal = isinstance(argument, int) and 0 <= argument < substrate.slot_count
        elif domain.rule == "input_index":
            legal = isinstance(argument, int) and 0 <= argument < substrate.input_count
        elif domain.rule == "literal_set":
            legal = argument in substrate.literal_values
        else:
            legal = argument in substrate.selector_values(domain.reference)
        if not legal:
            raise SubstrateError(
                RefusalCode.PARAMETER_OUT_OF_DOMAIN, f"{kind} argument {argument!r}",
            )


def execute_from_state(
    program: Sequence[tuple[str, tuple[object, ...]]],
    inputs: Sequence[int],
    language: RuntimeLanguage,
    substrate: SubstrateState,
) -> tuple[int, ...]:
    """Run a whole program. The language says what a primitive is; the substrate says what its
    micro-operations mean. Neither is host code."""

    slots = [0] * substrate.slot_count
    for name, arguments in program:
        definition = language.definition(name)
        if definition is None:
            raise SubstrateError(RefusalCode.UNDEFINED_PRIMITIVE, f"{name!r}")
        if len(arguments) != definition.arity:
            raise SubstrateError(
                RefusalCode.SIGNATURE_MISMATCH,
                f"{name!r} expects {definition.arity}, received {len(arguments)}",
            )
        check_arguments(definition, arguments, substrate)
        slots = run_body_from_state(definition.body, arguments, slots, inputs, substrate)
    return tuple(slots)


def registered_reach_report(substrate: SubstrateState) -> dict[str, object]:
    """Evidence about what is REGISTERED, kept separate from what the kernel could run.

    Three expressivities must not be conflated, and this report names all three:

    * the authored K1 kernel's **potential** expressivity, which is deliberately larger;
    * `SUBSTRATE_A`'s **registered** expressivity, which is the subject of the conservation claim;
    * the **language-level** expressivity inherited from M091, which sits above both.

    Loop-freedom is corroborating evidence about the second, not the definition of it. The claim
    that registered semantics equal inherited semantics is established by conservation over the
    complete registered state, not by this report.
    """

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
        "kernel_potential_expressivity_is_larger": True,
        "registered_expressivity_claim": (
            "the effective semantics reachable through the registered state are exactly those "
            "reachable through the inherited M091 substrate; established by conservation over the "
            "complete registered state, not by loop-freedom"
        ),
        "loop_freedom_is_corroboration_not_definition": True,
    }


__all__ = [
    "ARGUMENT_ROLES", "DOMAIN_RULES", "ORIGINS", "SUBSTRATE_STATE_SCHEMA", "ParameterDomain",
    "SubstrateOperation", "SubstrateState", "check_arguments", "execute_from_state",
    "registered_reach_report", "run_body_from_state",
]
