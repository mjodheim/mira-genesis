"""The language the lineage stores is the language the interpreter executes.

M089 ended on a defect rather than a capability. `m089_meta_language.execute` begins:

    if name in L0_OPERATIONS:
        slots = _execute_base(name, arguments, slots, inputs)
        continue
    primitive = language.primitive(name)

So base operations were dispatched from a **module constant** and a host function, and the registry
was only consulted for everything else. `language.base_operations` was carried in the serialized
state, digested and rolled back — and consulted by nothing. D059 recorded the consequence: with an
empty registry, no fault to the serialized state could change behaviour, because there was nothing
executable in it. Two authorities existed, and one of them lived outside the lineage.

This module removes that split. There is one registry, holding **every** primitive; `origin`
distinguishes inherited from acquired and is metadata only. The interpreter contains no branch on
any primitive name and no table of implementations: it looks a definition up in the state it was
handed, and runs its body on the substrate.

The boundary that remains, stated plainly rather than hidden:

* **Interpreter substrate I** — a fixed, authored stack machine of eight micro-operations. The host
  must execute *something*, and this is it. It is generic over primitives: it has never heard of
  `COPY_INPUT`.
* **Meta-language L** — the set of primitive definitions, entirely serialized lineage state.

M090 claims only that **L** is state-owned. **I** remains authored, and is the next ceiling.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Mapping, Sequence


LANGUAGE_SCHEMA = "m090-executable-meta-language-v1"
SUBSTRATE_SCHEMA = "m090-interpreter-substrate-v1"

SLOT_COUNT = 4
INPUT_COUNT = 3

# ---------------------------------------------------------------------------------------------
# Interpreter substrate I — fixed, authored, and generic over the language
# ---------------------------------------------------------------------------------------------

MICRO_OPERATIONS = (
    "PUSH_INPUT", "PUSH_SLOT", "PUSH_CONST", "BINOP", "UNOP", "DUP", "SWAP", "STORE_SLOT",
)

# Exactly M089's unary set. `identity` was present in a first draft and widened the accepted
# argument domain of the migrated APPLY_UNARY beyond what M089 accepted, which is a conservation
# violation however harmless the operator looks. External review of PR #138 caught it.
UNARY_OPERATORS = ("inc", "dec", "neg", "double")
BINARY_OPERATORS = ("add", "sub", "mul", "max")

# Parameter kinds a primitive may declare. `const` and `unary_op` exist so that an inherited
# operation like `SET_CONST(slot, c)` or `APPLY_UNARY(slot, fn)` is ONE definition rather than one
# per literal — the migration must not smuggle semantics into the shape of the registry.
PARAMETER_KINDS = ("slot", "input", "const", "unary_op")

CONST_VALUES = (0, 1)

MAX_BODY_LENGTH = 6
MAX_STACK_DEPTH = 8

# The only capability a primitive may hold. Making the language state-owned must not make it more
# powerful against the system: state ownership is not arbitrary code execution.
PERMITTED_CAPABILITIES = ("pure_slot_write",)
FORBIDDEN_CAPABILITIES = (
    "filesystem", "network", "subprocess", "credentials", "repository_write",
    "evaluator", "science_gate", "production",
)

ORIGINS = ("inherited", "acquired")


class LanguageError(RuntimeError):
    """Raised when a definition, program or state breaks the contract."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def digest_of(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _binary(operator: str, left: int, right: int) -> int:
    if operator == "add":
        return left + right
    if operator == "sub":
        return left - right
    if operator == "mul":
        return left * right
    if operator == "max":
        return max(left, right)
    raise LanguageError(f"unknown binary operator {operator!r}")


def _unary(name: str, value: int) -> int:
    if name == "inc":
        return value + 1
    if name == "dec":
        return value - 1
    if name == "neg":
        return -value
    if name == "double":
        return value * 2
    raise LanguageError(f"unknown unary operator {name!r}")


def _resolve(argument: object, arguments: Sequence[object]) -> object:
    if isinstance(argument, str) and argument.startswith("$"):
        index = int(argument[1:])
        if index >= len(arguments):
            raise LanguageError(f"parameter {argument} is not supplied")
        return arguments[index]
    return argument


def run_body(
    body: Sequence[tuple[str, object]], arguments: Sequence[object],
    slots: Sequence[int], inputs: Sequence[int],
) -> list[int]:
    """The whole interpreter substrate. It knows micro-operations and nothing else.

    There is no parameter here naming a primitive, and no branch on one. Whatever the language
    state says a primitive's body is, this runs it.
    """

    if len(body) > MAX_BODY_LENGTH:
        raise LanguageError("primitive body exceeds the frozen length bound")
    stack: list[int] = []
    updated = list(slots)
    for name, argument in body:
        if name not in MICRO_OPERATIONS:
            raise LanguageError(f"unknown micro-operation {name!r}")
        if len(stack) > MAX_STACK_DEPTH:
            raise LanguageError("primitive body exceeded the stack bound")
        if name == "PUSH_INPUT":
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < INPUT_COUNT:
                raise LanguageError("input index out of range")
            stack.append(int(inputs[index]))
        elif name == "PUSH_SLOT":
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < SLOT_COUNT:
                raise LanguageError("slot index out of range")
            stack.append(int(updated[index]))
        elif name == "PUSH_CONST":
            stack.append(int(_resolve(argument, arguments)))  # type: ignore[arg-type]
        elif name == "BINOP":
            if len(stack) < 2:
                raise LanguageError("BINOP needs two operands")
            right, left = stack.pop(), stack.pop()
            stack.append(_binary(str(_resolve(argument, arguments)), left, right))
        elif name == "UNOP":
            if not stack:
                raise LanguageError("UNOP needs one operand")
            stack.append(_unary(str(_resolve(argument, arguments)), stack.pop()))
        elif name == "DUP":
            if not stack:
                raise LanguageError("DUP needs one operand")
            stack.append(stack[-1])
        elif name == "SWAP":
            if len(stack) < 2:
                raise LanguageError("SWAP needs two operands")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif name == "STORE_SLOT":
            if not stack:
                raise LanguageError("STORE_SLOT needs one operand")
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < SLOT_COUNT:
                raise LanguageError("slot index out of range")
            updated[index] = stack.pop()
    return updated


# ---------------------------------------------------------------------------------------------
# Meta-language L — entirely serialized state
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveDefinition:
    """One operation of the language, semantics included, as data."""

    primitive_id: str
    parameter_kinds: tuple[str, ...]
    body: tuple[tuple[str, object], ...]
    origin: str
    provenance: tuple[str, ...]
    capabilities: tuple[str, ...] = ("pure_slot_write",)

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise LanguageError(f"unknown origin {self.origin!r}")
        for kind in self.parameter_kinds:
            if kind not in PARAMETER_KINDS:
                raise LanguageError(f"unknown parameter kind {kind!r}")
        for capability in self.capabilities:
            if capability in FORBIDDEN_CAPABILITIES or capability not in PERMITTED_CAPABILITIES:
                raise LanguageError(f"forbidden capability {capability!r}")
        if not self.body:
            raise LanguageError("a primitive definition needs a body")

    @property
    def arity(self) -> int:
        return len(self.parameter_kinds)

    def to_dict(self) -> dict[str, object]:
        return {
            "primitive_id": self.primitive_id,
            "parameter_kinds": list(self.parameter_kinds),
            "body": [[name, argument] for name, argument in self.body],
            "origin": self.origin,
            "provenance": list(self.provenance),
            "capabilities": list(self.capabilities),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PrimitiveDefinition":
        expected = {
            "primitive_id", "parameter_kinds", "body", "origin", "provenance", "capabilities",
        }
        if set(data) != expected:
            raise LanguageError("primitive definition fields differ from the closed schema")
        return cls(
            str(data["primitive_id"]),
            tuple(str(item) for item in data["parameter_kinds"]),  # type: ignore[union-attr]
            tuple((str(item[0]), item[1]) for item in data["body"]),  # type: ignore[index,union-attr]
            str(data["origin"]),
            tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
            tuple(str(item) for item in data["capabilities"]),  # type: ignore[union-attr]
        )

    def semantics_digest(self) -> str:
        """Covers the body and the signature. The identifier is deliberately excluded.

        Renaming a primitive must not change what it means, and changing its body must change this
        even when the name is untouched.
        """

        return digest_of({
            "parameter_kinds": list(self.parameter_kinds),
            "body": [[name, argument] for name, argument in self.body],
        })

    def digest(self) -> str:
        return digest_of(self.to_dict())


@dataclass(frozen=True)
class MetaLanguageState:
    """The complete executable language, as lineage state. One registry, no second authority."""

    primitives: tuple[PrimitiveDefinition, ...]
    language_version: int = 0
    provenance: tuple[str, ...] = ()
    schema: str = LANGUAGE_SCHEMA

    def __post_init__(self) -> None:
        identifiers = [item.primitive_id for item in self.primitives]
        if len(set(identifiers)) != len(identifiers):
            raise LanguageError("primitive identifiers must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "language_version": self.language_version,
            "primitives": [item.to_dict() for item in self.primitives],
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "MetaLanguageState":
        if set(data) != {
            "schema", "language_version", "primitives", "provenance",
        } or data.get("schema") != LANGUAGE_SCHEMA:
            raise LanguageError("serialized language fields differ from the closed schema")
        return cls(
            tuple(
                PrimitiveDefinition.from_dict(item)
                for item in data["primitives"]  # type: ignore[union-attr]
            ),
            int(data["language_version"]),  # type: ignore[arg-type]
            tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
        )

    def digest(self) -> str:
        return digest_of(self.to_dict())

    def semantics_digest(self) -> str:
        """A digest over what the language MEANS, not over how its entries are labelled."""

        return digest_of(sorted(item.semantics_digest() for item in self.primitives))

    def definition(self, primitive_id: str) -> PrimitiveDefinition | None:
        return next(
            (item for item in self.primitives if item.primitive_id == primitive_id), None
        )

    @property
    def primitive_ids(self) -> tuple[str, ...]:
        return tuple(item.primitive_id for item in self.primitives)

    def register(self, definition: PrimitiveDefinition, reason: str) -> "MetaLanguageState":
        if self.definition(definition.primitive_id) is not None:
            raise LanguageError(f"{definition.primitive_id!r} is already defined")
        return MetaLanguageState(
            self.primitives + (definition,), self.language_version + 1,
            self.provenance + (reason,),
        )

    def without(self, primitive_id: str, reason: str) -> "MetaLanguageState":
        """Remove a primitive. Inherited and acquired are removed the same way."""

        if self.definition(primitive_id) is None:
            raise LanguageError(f"{primitive_id!r} is not defined")
        return MetaLanguageState(
            tuple(item for item in self.primitives if item.primitive_id != primitive_id),
            self.language_version + 1, self.provenance + (reason,),
        )

    def with_mutated(
        self, primitive_id: str, body: Sequence[tuple[str, object]], reason: str,
    ) -> "MetaLanguageState":
        """Change a primitive's semantics while keeping its identifier."""

        definition = self.definition(primitive_id)
        if definition is None:
            raise LanguageError(f"{primitive_id!r} is not defined")
        mutated = replace(definition, body=tuple((str(n), a) for n, a in body))
        return MetaLanguageState(
            tuple(mutated if item.primitive_id == primitive_id else item
                  for item in self.primitives),
            self.language_version + 1, self.provenance + (reason,),
        )


# ---------------------------------------------------------------------------------------------
# the interpreter: state is the only authority
# ---------------------------------------------------------------------------------------------


def execute(
    program: Sequence[tuple[str, tuple[object, ...]]],
    inputs: Sequence[int],
    language: MetaLanguageState,
) -> tuple[int, ...]:
    """Run a program. Every operation is looked up in `language` and nowhere else.

    There is no `if name in SOMETHING` here, no table of implementations, and no fallback. If the
    state does not define an operation, the program does not run — which is the property M089
    lacked and D059 named.
    """

    slots = [0] * SLOT_COUNT
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
        _check_arguments(definition, arguments)
        slots = run_body(definition.body, arguments, slots, inputs)
    return tuple(slots)


def _check_arguments(
    definition: PrimitiveDefinition, arguments: Sequence[object],
) -> None:
    for kind, argument in zip(definition.parameter_kinds, arguments, strict=True):
        if kind == "slot" and not (
            isinstance(argument, int) and 0 <= argument < SLOT_COUNT
        ):
            raise LanguageError("slot argument out of range")
        if kind == "input" and not (
            isinstance(argument, int) and 0 <= argument < INPUT_COUNT
        ):
            raise LanguageError("input argument out of range")
        if kind == "const" and argument not in CONST_VALUES:
            raise LanguageError("constant argument outside the frozen set")
        if kind == "unary_op" and argument not in UNARY_OPERATORS:
            raise LanguageError("unary operator argument outside the frozen set")


def available_operations(language: MetaLanguageState) -> tuple[str, ...]:
    """What the lineage can currently do, read from state alone."""

    return tuple(sorted(language.primitive_ids))


__all__ = [
    "BINARY_OPERATORS", "CONST_VALUES", "FORBIDDEN_CAPABILITIES", "INPUT_COUNT",
    "LANGUAGE_SCHEMA", "LanguageError", "MAX_BODY_LENGTH", "MAX_STACK_DEPTH",
    "MICRO_OPERATIONS", "MetaLanguageState", "ORIGINS", "PARAMETER_KINDS",
    "PERMITTED_CAPABILITIES", "PrimitiveDefinition", "SLOT_COUNT", "SUBSTRATE_SCHEMA",
    "UNARY_OPERATORS", "available_operations", "digest_of", "execute", "run_body",
]
