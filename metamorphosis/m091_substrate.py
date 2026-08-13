"""S — the bounded assembly substrate a new primitive is *built* from, one level below the language.

M090 froze an interpreter substrate: eight micro-operations, a stack, four slots, three inputs.
This module adds nothing to it. It is the **assembly** layer: which signatures a primitive may
declare, which micro-operations may appear in a body, in which order candidates are produced, and
what makes a body well formed. The micro-operations themselves are M090's, unchanged and imported
rather than restated, so that M091 cannot be accused of quietly widening the machine.

Three properties are deliberate.

* **Assembly, not selection.** There is no list of finished operations here. A candidate is a
  sequence of micro-operations plus a signature, and the overwhelming majority of sequences are
  ill-formed, do nothing, or compute something the inherited language already computes. Nothing in
  this module knows which one is wanted; `enumerate_candidate_bodies` is a product over an
  alphabet, in a fixed order, and it produces the useless with the useful.

* **Lower level than the language, and not a language.** A body cannot be run by the lineage. The
  lineage runs *programs*, and a program is a sequence of calls to primitives held in the language
  state. A body only becomes callable by being registered, which is what
  `extension_built_but_not_registered` exists to demonstrate: the same bytes, validated, and
  useless until the state owns them.

* **Bounded.** Four micro-operations at most, a stack depth M090 already fixed, one capability. A
  primitive assembled here can write slots and nothing else — no filesystem, no network, no
  subprocess, no evaluator. Extension adds expressive power to the language and no authority
  against the system.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from typing import Iterator, Sequence

from metamorphosis.m090_language import (
    BINARY_OPERATORS,
    FORBIDDEN_CAPABILITIES,
    MAX_BODY_LENGTH,
    MICRO_OPERATIONS,
    PERMITTED_CAPABILITIES,
    SLOT_COUNT,
    UNARY_OPERATORS,
    LanguageError,
    PrimitiveDefinition,
    run_body,
)
from metamorphosis.m091_expressivity import SOUNDNESS_INPUTS, parameter_bindings


SUBSTRATE_SCHEMA = "m091-assembly-substrate-v1"

# The signatures a candidate may declare, in the order they are searched. The third exists so that
# the search really can produce an M089-shaped primitive — one that routes two input positions into
# a slot — and be told by the validator that this is not the limitation that was diagnosed.
SIGNATURES: tuple[tuple[str, ...], ...] = (
    ("slot",),
    ("slot", "input"),
    ("slot", "input", "input"),
)

# Body literals available to the assembler. Kept to the two constants the language already admits.
BODY_CONSTANTS: tuple[int, ...] = (0, 1)

MAX_ASSEMBLY_LENGTH = 4

CAPABILITIES: tuple[str, ...] = ("pure_slot_write",)


class SubstrateError(LanguageError):
    """Raised when an assembly request is outside the frozen substrate."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def body_alphabet(signature: Sequence[str]) -> tuple[tuple[str, object], ...]:
    """Every micro-operation an assembler may place, for this signature, in a frozen order.

    `$n` refers to the primitive's n-th call-time parameter. A signature with no `input` parameter
    simply has no way to name an input, which is how the arity of a candidate bounds what it can
    reach without anything being special-cased.
    """

    if MAX_ASSEMBLY_LENGTH > MAX_BODY_LENGTH:
        raise SubstrateError("the assembly bound exceeds the interpreter's body bound")
    alphabet: list[tuple[str, object]] = [("PUSH_SLOT", "$0")]
    for index, kind in enumerate(signature):
        if kind == "input":
            alphabet.append(("PUSH_INPUT", f"${index}"))
        elif kind != "slot":
            raise SubstrateError(f"signature kind {kind!r} is outside the assembly substrate")
    for constant in BODY_CONSTANTS:
        alphabet.append(("PUSH_CONST", constant))
    for operator in BINARY_OPERATORS:
        alphabet.append(("BINOP", operator))
    for operator in UNARY_OPERATORS:
        alphabet.append(("UNOP", operator))
    alphabet.append(("DUP", None))
    alphabet.append(("SWAP", None))
    alphabet.append(("STORE_SLOT", "$0"))
    for name, _ in alphabet:
        if name not in MICRO_OPERATIONS:
            raise SubstrateError(f"{name!r} is not a micro-operation of the frozen substrate")
    return tuple(alphabet)


def enumerate_candidate_bodies(
    signature: Sequence[str], max_length: int = MAX_ASSEMBLY_LENGTH,
) -> Iterator[tuple[tuple[str, object], ...]]:
    """Assemble bodies shortest first, then in alphabet order. Deterministic and exhaustive."""

    alphabet = body_alphabet(signature)
    for length in range(1, max_length + 1):
        for body in itertools.product(alphabet, repeat=length):
            yield tuple(body)


def well_formed(body: Sequence[tuple[str, object]], signature: Sequence[str]) -> bool:
    """Whether a body writes a slot and runs to completion on every legal call."""

    if not body or len(body) > MAX_ASSEMBLY_LENGTH:
        return False
    if not any(name == "STORE_SLOT" for name, _ in body):
        return False
    bindings = parameter_bindings(signature)
    if not bindings:
        return False
    for arguments in bindings:
        for inputs in (SOUNDNESS_INPUTS[0], SOUNDNESS_INPUTS[3]):
            try:
                run_body(body, arguments, [0] * SLOT_COUNT, inputs)
            except LanguageError:
                return False
    return True


def implementation_digest(body: Sequence[tuple[str, object]]) -> str:
    return hashlib.sha256(
        _canonical([[name, argument] for name, argument in body])
    ).hexdigest()


# Probe states for the extensional fingerprint. Deliberately wider than the assembler's own
# constants so that two bodies agreeing on the easy cases are still told apart.
SEMANTIC_PROBES: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] = (
    ((1, 2, 3), (0, 0, 0, 0)),
    ((-4, 3, 7), (-2, 5, 0, 1)),
    ((0, 5, -3), (3, -1, 4, 0)),
    ((9, -7, 4), (0, 0, -6, 2)),
    ((-1, 0, 2), (7, 7, 7, 7)),
)


def argument_row(arguments: Sequence[object]) -> list[object]:
    """One binding, rendered so that a slot index and an operator name cannot be confused."""

    return [item if isinstance(item, str) else int(item) for item in arguments]


def fingerprint(observations: Sequence[object]) -> str:
    """Hash a table of observations. Shared so that a body and a composition are comparable."""

    return hashlib.sha256(_canonical(list(observations))).hexdigest()


def semantics_digest(body: Sequence[tuple[str, object]], signature: Sequence[str]) -> str:
    """An extensional fingerprint: what a body *does*, over every legal call.

    The identifier is not an input to this. Two bodies that behave identically share a digest
    whatever they are called, and a body given the right name and the wrong behaviour does not.
    A composition of inherited operations is fingerprinted by the same table over the same probes
    in the same order, so the two are directly comparable — which is what the macro test needs.
    """

    observations: list[object] = []
    for arguments in parameter_bindings(signature):
        for inputs, slots in SEMANTIC_PROBES:
            try:
                observations.append([
                    argument_row(arguments), list(run_body(body, arguments, list(slots), inputs)),
                ])
            except LanguageError:
                observations.append([argument_row(arguments), "refused"])
    return fingerprint(observations)


def build_definition(
    primitive_id: str, body: Sequence[tuple[str, object]], signature: Sequence[str],
    provenance: Sequence[str],
) -> PrimitiveDefinition:
    """Wrap an assembled body in the language's own definition type. This validates nothing."""

    for capability in CAPABILITIES:
        if capability in FORBIDDEN_CAPABILITIES or capability not in PERMITTED_CAPABILITIES:
            raise SubstrateError(f"capability {capability!r} is outside the permitted set")
    return PrimitiveDefinition(
        primitive_id=primitive_id,
        parameter_kinds=tuple(signature),
        body=tuple((str(name), argument) for name, argument in body),
        origin="acquired",
        provenance=tuple(provenance),
        capabilities=CAPABILITIES,
    )


def substrate_manifest() -> dict[str, object]:
    """What the assembler is allowed to build from, as an artifact the checker re-derives."""

    return {
        "schema": SUBSTRATE_SCHEMA,
        "interpreter_substrate": "m090-interpreter-substrate-v1",
        "micro_operations": list(MICRO_OPERATIONS),
        "binary_operators": list(BINARY_OPERATORS),
        "unary_operators": list(UNARY_OPERATORS),
        "body_constants": list(BODY_CONSTANTS),
        "signatures": [list(item) for item in SIGNATURES],
        "max_assembly_length": MAX_ASSEMBLY_LENGTH,
        "capabilities": list(CAPABILITIES),
        "forbidden_capabilities": list(FORBIDDEN_CAPABILITIES),
        "alphabet_sizes": {
            "|".join(signature): len(body_alphabet(signature)) for signature in SIGNATURES
        },
        "body_space_size": {
            "|".join(signature): sum(
                len(body_alphabet(signature)) ** length
                for length in range(1, MAX_ASSEMBLY_LENGTH + 1)
            )
            for signature in SIGNATURES
        },
        "a_body_is_not_executable_until_it_is_registered": True,
        "contains_no_finished_operation_to_select": True,
    }


__all__ = [
    "BODY_CONSTANTS", "CAPABILITIES", "MAX_ASSEMBLY_LENGTH", "SEMANTIC_PROBES", "SIGNATURES",
    "SUBSTRATE_SCHEMA", "SubstrateError", "argument_row", "body_alphabet", "build_definition",
    "enumerate_candidate_bodies", "fingerprint", "implementation_digest", "semantics_digest",
    "substrate_manifest", "well_formed",
]
