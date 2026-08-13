"""S — the bounded substrate from which a new L0 primitive can be *built*, not chosen.

The failure this module is shaped to avoid is picking `P*` out of a list of finished functions.
`S` therefore contains no operation that is itself the answer: it is a small typed stack machine
with eight micro-operations, and a primitive is a short program over them plus a parameter
signature. Most assemblies are ill-typed, do nothing useful, or are indistinguishable from an L0
composition; the lineage finds out by building them and having them validated elsewhere.

`S` is deliberately *lower level* than L0 rather than a superset of it. It cannot be used as a
working transformation language: it has no notion of a program over slots, no sequencing of
operations against an input record, and no way to be executed by the lineage except by being
registered as a primitive first. That is what the `extension_built_but_not_registered` control
exists to demonstrate.

The one property that matters for the science: `BINOP` pops **two** values, so a body containing it
can make one slot depend on two input positions. No L0 operation can, at any length. That is the
expressive gap, and it is a structural fact about the substrate rather than a name.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence

from metamorphosis.m089_meta_language import (
    INPUT_COUNT,
    SLOT_COUNT,
    MetaLanguageError,
    PrimitiveContract,
    UNARY_FUNCTIONS,
)


SUBSTRATE_SCHEMA = "m089-extension-substrate-v1"

# Eight micro-operations. `$n` denotes the primitive's n-th call-time parameter.
MICRO_OPERATIONS = (
    "PUSH_INPUT",   # push inputs[param]
    "PUSH_SLOT",    # push slots[param]
    "PUSH_CONST",   # push a literal
    "BINOP",        # pop two, push op(a, b)
    "UNOP",         # pop one, push u(a)
    "DUP",          # duplicate the top
    "SWAP",         # exchange the top two
    "STORE_SLOT",   # pop one, write to slots[param]
)

BINARY_OPERATORS = ("add", "sub", "mul", "max")

PARAMETER_KINDS = ("slot", "input")

# Capabilities a primitive may declare. Anything outside this set is an authority escalation and
# is refused: a new operation never acquires a power the language did not already have.
PERMITTED_CAPABILITIES = ("pure_slot_write",)

FORBIDDEN_CAPABILITIES = (
    "filesystem", "network", "credentials", "repository_write", "merge",
    "production", "evaluator", "science_gate",
)

MAX_BODY_LENGTH = 5
MAX_STACK_DEPTH = 8


class SubstrateError(MetaLanguageError):
    """Raised when a substrate body is ill-formed, unsafe or non-terminating."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _resolve(argument: object, arguments: Sequence[object]) -> int:
    """Resolve a body operand, which may be a literal or a `$n` call-time parameter."""

    if isinstance(argument, str) and argument.startswith("$"):
        index = int(argument[1:])
        if index >= len(arguments):
            raise SubstrateError(f"parameter {argument} is not supplied")
        return int(arguments[index])  # type: ignore[arg-type]
    return int(argument)  # type: ignore[arg-type]


def _binary(operator: str, left: int, right: int) -> int:
    if operator == "add":
        return left + right
    if operator == "sub":
        return left - right
    if operator == "mul":
        return left * right
    if operator == "max":
        return max(left, right)
    raise SubstrateError(f"unknown binary operator {operator!r}")


def _unary(name: str, value: int) -> int:
    if name == "inc":
        return value + 1
    if name == "dec":
        return value - 1
    if name == "neg":
        return -value
    if name == "double":
        return value * 2
    raise SubstrateError(f"unknown unary function {name!r}")


def run_body(
    body: Sequence[tuple[str, object]], arguments: Sequence[object],
    slots: Sequence[int], inputs: Sequence[int],
) -> list[int]:
    """Execute a primitive body on the stack machine. Bounded, total and side-effect free."""

    if len(body) > MAX_BODY_LENGTH:
        raise SubstrateError("primitive body exceeds the frozen length bound")
    stack: list[int] = []
    updated = list(slots)
    for name, argument in body:
        if name not in MICRO_OPERATIONS:
            raise SubstrateError(f"unknown micro-operation {name!r}")
        if len(stack) > MAX_STACK_DEPTH:
            raise SubstrateError("primitive body exceeded the stack bound")
        if name == "PUSH_INPUT":
            index = _resolve(argument, arguments)
            if not 0 <= index < INPUT_COUNT:
                raise SubstrateError("input index out of range")
            stack.append(int(inputs[index]))
        elif name == "PUSH_SLOT":
            index = _resolve(argument, arguments)
            if not 0 <= index < SLOT_COUNT:
                raise SubstrateError("slot index out of range")
            stack.append(int(updated[index]))
        elif name == "PUSH_CONST":
            stack.append(int(argument))  # type: ignore[arg-type]
        elif name == "BINOP":
            if len(stack) < 2:
                raise SubstrateError("BINOP needs two operands")
            right, left = stack.pop(), stack.pop()
            stack.append(_binary(str(argument), left, right))
        elif name == "UNOP":
            if not stack:
                raise SubstrateError("UNOP needs one operand")
            stack.append(_unary(str(argument), stack.pop()))
        elif name == "DUP":
            if not stack:
                raise SubstrateError("DUP needs one operand")
            stack.append(stack[-1])
        elif name == "SWAP":
            if len(stack) < 2:
                raise SubstrateError("SWAP needs two operands")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif name == "STORE_SLOT":
            if not stack:
                raise SubstrateError("STORE_SLOT needs one operand")
            index = _resolve(argument, arguments)
            if not 0 <= index < SLOT_COUNT:
                raise SubstrateError("slot index out of range")
            updated[index] = stack.pop()
    return updated


def body_source_effect(
    body: Sequence[tuple[str, object]], arguments: Sequence[object],
    sources: Sequence[frozenset[int]],
) -> list[frozenset[int]]:
    """Abstract interpretation of a body over dependency sets, mirroring `run_body` exactly."""

    stack: list[frozenset[int]] = []
    updated = list(sources)
    for name, argument in body:
        if name == "PUSH_INPUT":
            stack.append(frozenset({_resolve(argument, arguments)}))
        elif name == "PUSH_SLOT":
            stack.append(updated[_resolve(argument, arguments)])
        elif name == "PUSH_CONST":
            stack.append(frozenset())
        elif name == "BINOP":
            if len(stack) < 2:
                raise SubstrateError("BINOP needs two operands")
            right, left = stack.pop(), stack.pop()
            stack.append(left | right)  # the union is the whole expressive point
        elif name == "UNOP":
            if not stack:
                raise SubstrateError("UNOP needs one operand")
        elif name == "DUP":
            if not stack:
                raise SubstrateError("DUP needs one operand")
            stack.append(stack[-1])
        elif name == "SWAP":
            if len(stack) < 2:
                raise SubstrateError("SWAP needs two operands")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif name == "STORE_SLOT":
            if not stack:
                raise SubstrateError("STORE_SLOT needs one operand")
            updated[_resolve(argument, arguments)] = stack.pop()
        else:
            raise SubstrateError(f"unknown micro-operation {name!r}")
    return updated


def primitive_max_source_fanout(primitive: PrimitiveContract) -> int:
    """The largest number of distinct input positions this primitive can route into one slot.

    Computed over every legal parameter binding, so it is a property of the primitive rather than
    of one call. A value above one means the primitive breaks L0's single-source invariant, which
    is the certificate the expressive claim rests on.
    """

    best = 0
    for arguments in _parameter_bindings(primitive.parameter_kinds):
        try:
            effect = body_source_effect(
                primitive.body, arguments, [frozenset() for _ in range(SLOT_COUNT)],
            )
        except SubstrateError:
            continue
        best = max(best, max((len(item) for item in effect), default=0))
    return best


def _parameter_bindings(kinds: Sequence[str]) -> list[tuple[int, ...]]:
    options: list[list[int]] = []
    for kind in kinds:
        if kind == "slot":
            options.append(list(range(SLOT_COUNT)))
        elif kind == "input":
            options.append(list(range(INPUT_COUNT)))
        else:
            raise SubstrateError(f"unknown parameter kind {kind!r}")
    bindings: list[tuple[int, ...]] = [()]
    for choices in options:
        bindings = [item + (choice,) for item in bindings for choice in choices]
    return bindings


def semantics_digest(
    body: Sequence[tuple[str, object]], kinds: Sequence[str],
) -> str:
    """An extensional fingerprint: what the primitive DOES, independent of how it is named.

    Two implementations that behave identically on every probe over every legal binding get the
    same digest; a primitive with the right name and the wrong behaviour gets a different one.
    """

    probes = [
        ((1, 2, 3), (0, 0, 0, 0)),
        ((0, 5, 7), (1, 1, 1, 1)),
        ((-2, 4, 6), (2, 0, 3, 1)),
        ((9, 9, 1), (0, 4, 0, 2)),
    ]
    observations: list[object] = []
    for arguments in _parameter_bindings(kinds):
        for inputs, slots in probes:
            try:
                observations.append([list(arguments), list(run_body(body, arguments, slots, inputs))])
            except SubstrateError:
                observations.append([list(arguments), "refused"])
    return hashlib.sha256(_canonical(observations)).hexdigest()


def implementation_digest(body: Sequence[tuple[str, object]]) -> str:
    return hashlib.sha256(_canonical([[name, argument] for name, argument in body])).hexdigest()


# --------------------------------------------------------------------------------------------
# constructing candidate primitives
# --------------------------------------------------------------------------------------------


def enumerate_candidate_bodies(max_length: int = 4) -> tuple[tuple[tuple[str, object], ...], ...]:
    """Assemble candidate primitive bodies from the substrate, shortest first.

    This is construction, not selection from finished functions: the pieces are eight micro-ops
    and the assembler knows nothing about what any of them are for. Most results are ill-typed,
    do nothing, or are equivalent to an L0 composition.
    """

    alphabet: list[tuple[str, object]] = []
    for parameter in ("$1", "$2"):
        alphabet.append(("PUSH_INPUT", parameter))
    alphabet.append(("PUSH_SLOT", "$0"))
    alphabet.append(("PUSH_CONST", 1))
    for operator in BINARY_OPERATORS:
        alphabet.append(("BINOP", operator))
    for function in sorted(UNARY_FUNCTIONS):
        alphabet.append(("UNOP", function))
    alphabet.append(("DUP", None))
    alphabet.append(("SWAP", None))
    alphabet.append(("STORE_SLOT", "$0"))

    produced: list[tuple[tuple[str, object], ...]] = []
    frontier: list[tuple[tuple[str, object], ...]] = [()]
    for _ in range(max_length):
        nxt: list[tuple[tuple[str, object], ...]] = []
        for body in frontier:
            for operation in alphabet:
                extended = body + (operation,)
                nxt.append(extended)
                produced.append(extended)
        frontier = nxt
    return tuple(produced)


def well_formed(body: Sequence[tuple[str, object]], kinds: Sequence[str]) -> bool:
    """Whether a body runs to completion on every legal binding and writes at least one slot."""

    if not body or not any(name == "STORE_SLOT" for name, _ in body):
        return False
    bindings = _parameter_bindings(kinds)
    if not bindings:
        return False
    for arguments in bindings:
        try:
            run_body(body, arguments, (0, 0, 0, 0), (1, 2, 3))
        except SubstrateError:
            return False
    return True


def build_primitive(
    primitive_id: str, body: Sequence[tuple[str, object]], kinds: Sequence[str],
    provenance: Sequence[str], version: int,
) -> PrimitiveContract:
    """Assemble a contract around a constructed body. This does not validate it."""

    if any(item not in PARAMETER_KINDS for item in kinds):
        raise SubstrateError("unknown parameter kind")
    return PrimitiveContract(
        primitive_id=primitive_id,
        arity=len(kinds),
        parameter_kinds=tuple(kinds),
        body=tuple((str(name), argument) for name, argument in body),
        semantics_digest=semantics_digest(body, kinds),
        implementation_digest=implementation_digest(body),
        provenance=tuple(provenance),
        validation_receipt="",
        capabilities=("pure_slot_write",),
        introduced_in_version=version,
    )


__all__ = [
    "BINARY_OPERATORS", "FORBIDDEN_CAPABILITIES", "MAX_BODY_LENGTH", "MAX_STACK_DEPTH",
    "MICRO_OPERATIONS", "PARAMETER_KINDS", "PERMITTED_CAPABILITIES", "SUBSTRATE_SCHEMA",
    "SubstrateError", "body_source_effect", "build_primitive", "enumerate_candidate_bodies",
    "implementation_digest", "primitive_max_source_fanout", "run_body", "semantics_digest",
    "well_formed",
]
