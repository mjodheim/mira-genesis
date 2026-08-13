"""L0 — the lineage's working transformation language, and the invariant that bounds it.

M088 left one ceiling: the lineage composed meta-operations we wrote and invented none. M089 asks
whether it can add a **new fundamental operation** to that language when the language cannot
express the modification it needs.

The whole milestone turns on not repeating M055. D019 closed that line because the acquired
expression was already reachable: *"737 candidates without the acquisition against 48 with it. The
acquisition made the search fifteen times cheaper and made nothing newly reachable."* A composition
of existing operations is not a new capability. So L0 is given a **structural invariant** that no
composition of its operations can break, and the qualifying transformation is one that requires
breaking it.

## L0

Programs rewrite a record of slots, given an input tuple. Three operations:

* `SET_CONST(slot, c)`      — write a literal
* `COPY_INPUT(slot, k)`     — copy one input position
* `APPLY_UNARY(slot, u)`    — apply a one-argument function to a slot, in place

## The invariant, and why it holds under composition

Define `sources(slot)` as the set of input indices the slot's value depends on. Then for every L0
program, **every slot satisfies `len(sources(slot)) <= 1`**, by induction on program length:

* `SET_CONST` sets `sources = {}`;
* `COPY_INPUT(slot, k)` sets `sources = {k}`;
* `APPLY_UNARY` is one-argument, so it maps a slot's value without consulting any other slot and
  leaves `sources` unchanged.

No operation reads two slots, and none reads a slot while writing another. So the single-source
property is closed under composition and under sequencing, at any length and any budget. This is
what makes the later inexpressibility claim a proof rather than a failed search: it is not that L0
did not find a two-source transformation, it is that no L0 program of any length has one.

Nothing in this module knows what primitive will be built, or what the qualifying task is.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


LANGUAGE_SCHEMA = "m089-meta-language-v1"

L0_OPERATIONS = ("SET_CONST", "COPY_INPUT", "APPLY_UNARY")

UNARY_FUNCTIONS: Mapping[str, str] = {
    "inc": "x + 1",
    "dec": "x - 1",
    "neg": "-x",
    "double": "x * 2",
}

SLOT_COUNT = 4
INPUT_COUNT = 3
CONSTANTS = (0, 1)


class MetaLanguageError(RuntimeError):
    """Raised when a program, primitive or language state breaks the contract."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def digest_of(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _apply_unary(name: str, value: int) -> int:
    if name == "inc":
        return value + 1
    if name == "dec":
        return value - 1
    if name == "neg":
        return -value
    if name == "double":
        return value * 2
    raise MetaLanguageError(f"unknown unary function {name!r}")


# --------------------------------------------------------------------------------------------
# primitives: the units of the working language
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveContract:
    """What a language primitive promises. Semantics are checked, names are not trusted."""

    primitive_id: str
    arity: int
    parameter_kinds: tuple[str, ...]
    body: tuple[tuple[str, object], ...]
    semantics_digest: str
    implementation_digest: str
    provenance: tuple[str, ...]
    validation_receipt: str
    capabilities: tuple[str, ...]
    introduced_in_version: int

    def to_dict(self) -> dict[str, object]:
        return {
            "primitive_id": self.primitive_id,
            "arity": self.arity,
            "parameter_kinds": list(self.parameter_kinds),
            "body": [[name, argument] for name, argument in self.body],
            "semantics_digest": self.semantics_digest,
            "implementation_digest": self.implementation_digest,
            "provenance": list(self.provenance),
            "validation_receipt": self.validation_receipt,
            "capabilities": list(self.capabilities),
            "introduced_in_version": self.introduced_in_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PrimitiveContract":
        expected = {
            "primitive_id", "arity", "parameter_kinds", "body", "semantics_digest",
            "implementation_digest", "provenance", "validation_receipt", "capabilities",
            "introduced_in_version",
        }
        if set(data) != expected:
            raise MetaLanguageError("primitive contract fields differ from the closed schema")
        return cls(
            str(data["primitive_id"]), int(data["arity"]),  # type: ignore[arg-type]
            tuple(str(item) for item in data["parameter_kinds"]),  # type: ignore[union-attr]
            tuple((str(item[0]), item[1]) for item in data["body"]),  # type: ignore[index,union-attr]
            str(data["semantics_digest"]), str(data["implementation_digest"]),
            tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
            str(data["validation_receipt"]),
            tuple(str(item) for item in data["capabilities"]),  # type: ignore[union-attr]
            int(data["introduced_in_version"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class MetaLanguageState:
    """The lineage's transformation language, as versioned serialized state."""

    version: int
    base_operations: tuple[str, ...]
    registry: tuple[PrimitiveContract, ...]
    provenance: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": LANGUAGE_SCHEMA,
            "version": self.version,
            "base_operations": list(self.base_operations),
            "registry": [item.to_dict() for item in self.registry],
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "MetaLanguageState":
        if set(data) != {
            "schema", "version", "base_operations", "registry", "provenance",
        } or data.get("schema") != LANGUAGE_SCHEMA:
            raise MetaLanguageError("serialized language fields differ from the closed schema")
        return cls(
            int(data["version"]),  # type: ignore[arg-type]
            tuple(str(item) for item in data["base_operations"]),  # type: ignore[union-attr]
            tuple(
                PrimitiveContract.from_dict(item)
                for item in data["registry"]  # type: ignore[union-attr]
            ),
            tuple(str(item) for item in data["provenance"]),  # type: ignore[union-attr]
        )

    def digest(self) -> str:
        return digest_of(self.to_dict())

    @property
    def operation_names(self) -> tuple[str, ...]:
        return self.base_operations + tuple(item.primitive_id for item in self.registry)

    def primitive(self, primitive_id: str) -> PrimitiveContract | None:
        return next(
            (item for item in self.registry if item.primitive_id == primitive_id), None
        )

    def register(self, primitive: PrimitiveContract, reason: str) -> "MetaLanguageState":
        if self.primitive(primitive.primitive_id) is not None:
            raise MetaLanguageError(f"{primitive.primitive_id!r} is already registered")
        return MetaLanguageState(
            version=self.version + 1,
            base_operations=self.base_operations,
            registry=self.registry + (primitive,),
            provenance=self.provenance + (reason,),
        )


def l0_language() -> MetaLanguageState:
    """The language the lineage starts with. Three operations, no registry."""

    return MetaLanguageState(version=0, base_operations=L0_OPERATIONS, registry=(), provenance=())


# --------------------------------------------------------------------------------------------
# executing a transformation program
# --------------------------------------------------------------------------------------------


def execute(
    program: Sequence[tuple[str, tuple[object, ...]]],
    inputs: Sequence[int],
    language: MetaLanguageState,
) -> tuple[int, ...]:
    """Run a transformation program under a language. Unknown operations are refused.

    The refusal is the point: a program using a primitive that is not registered does not run,
    which is what separates *having built an implementation* from *having extended the language*.
    """

    slots = [0] * SLOT_COUNT
    for name, arguments in program:
        if name in L0_OPERATIONS:
            slots = _execute_base(name, arguments, slots, inputs)
            continue
        primitive = language.primitive(name)
        if primitive is None:
            raise MetaLanguageError(
                f"operation {name!r} is not in language version {language.version}"
            )
        if len(arguments) != primitive.arity:
            raise MetaLanguageError(f"{name!r} expects {primitive.arity} arguments")
        slots = run_primitive_body(primitive.body, arguments, slots, inputs)
    return tuple(slots)


def _execute_base(
    name: str, arguments: Sequence[object], slots: Sequence[int], inputs: Sequence[int],
) -> list[int]:
    updated = list(slots)
    if name == "SET_CONST":
        slot, constant = int(arguments[0]), int(arguments[1])  # type: ignore[arg-type]
        updated[slot] = constant
    elif name == "COPY_INPUT":
        slot, index = int(arguments[0]), int(arguments[1])  # type: ignore[arg-type]
        updated[slot] = inputs[index]
    elif name == "APPLY_UNARY":
        slot, function = int(arguments[0]), str(arguments[1])
        updated[slot] = _apply_unary(function, updated[slot])
    else:
        raise MetaLanguageError(f"unknown base operation {name!r}")
    return updated


def run_primitive_body(
    body: Sequence[tuple[str, object]], arguments: Sequence[object],
    slots: Sequence[int], inputs: Sequence[int],
) -> list[int]:
    """Execute a primitive's stack body. Imported here so `execute` stays the single entry point."""

    from metamorphosis.m089_substrate import run_body

    return run_body(body, arguments, slots, inputs)


# --------------------------------------------------------------------------------------------
# the invariant, and the proof that L0 cannot break it
# --------------------------------------------------------------------------------------------


def source_signature(
    program: Sequence[tuple[str, tuple[object, ...]]], language: MetaLanguageState,
) -> tuple[frozenset[int], ...]:
    """Which input positions each slot depends on, computed by abstract interpretation.

    This is the invariant the whole milestone rests on, so it is computed structurally rather than
    sampled: `SET_CONST` clears a slot's sources, `COPY_INPUT` sets them to one index, and
    `APPLY_UNARY` cannot change them because it is a one-argument function of that slot alone.
    """

    sources: list[frozenset[int]] = [frozenset() for _ in range(SLOT_COUNT)]
    for name, arguments in program:
        if name == "SET_CONST":
            sources[int(arguments[0])] = frozenset()  # type: ignore[arg-type]
        elif name == "COPY_INPUT":
            sources[int(arguments[0])] = frozenset({int(arguments[1])})  # type: ignore[arg-type]
        elif name == "APPLY_UNARY":
            pass  # one argument, one slot: the dependency set is unchanged
        else:
            primitive = language.primitive(name)
            if primitive is None:
                raise MetaLanguageError(f"operation {name!r} is not in this language")
            from metamorphosis.m089_substrate import body_source_effect

            sources = body_source_effect(primitive.body, arguments, sources)
    return tuple(sources)


def max_sources(
    program: Sequence[tuple[str, tuple[object, ...]]], language: MetaLanguageState,
) -> int:
    return max((len(item) for item in source_signature(program, language)), default=0)


def l0_single_source_invariant_holds(language: MetaLanguageState) -> bool:
    """Whether every operation of this language preserves the single-source property.

    True for L0 by the induction in the module docstring. A registered primitive that can make a
    slot depend on two inputs makes it False — which is exactly the expressive gain being claimed,
    and is why the certificate records it rather than hiding it.
    """

    for primitive in language.registry:
        from metamorphosis.m089_substrate import primitive_max_source_fanout

        if primitive_max_source_fanout(primitive) > 1:
            return False
    return True


def enumerate_l0_reachable_signatures(max_length: int = 3) -> frozenset[tuple[frozenset[int], ...]]:
    """Exhaustively enumerate every source signature L0 can reach up to a length.

    Belt and braces. The induction already proves the single-source bound at *any* length; this
    enumerates a bounded prefix so the checker can confirm the claim by exhaustion as well as by
    argument, the way M088's constructive image was.
    """

    language = l0_language()
    frontier: set[tuple[tuple[str, tuple[object, ...]], ...]] = {()}
    signatures: set[tuple[frozenset[int], ...]] = {
        source_signature((), language),
    }
    operations: list[tuple[str, tuple[object, ...]]] = []
    for slot in range(SLOT_COUNT):
        for constant in CONSTANTS:
            operations.append(("SET_CONST", (slot, constant)))
        for index in range(INPUT_COUNT):
            operations.append(("COPY_INPUT", (slot, index)))
        for function in sorted(UNARY_FUNCTIONS):
            operations.append(("APPLY_UNARY", (slot, function)))
    for _ in range(max_length):
        nxt: set[tuple[tuple[str, tuple[object, ...]], ...]] = set()
        for program in frontier:
            for operation in operations:
                extended = program + (operation,)
                nxt.add(extended)
                signatures.add(source_signature(extended, language))
        frontier = nxt
    return frozenset(signatures)


__all__ = [
    "CONSTANTS", "INPUT_COUNT", "LANGUAGE_SCHEMA", "L0_OPERATIONS", "MetaLanguageError",
    "MetaLanguageState", "PrimitiveContract", "SLOT_COUNT", "UNARY_FUNCTIONS", "digest_of",
    "enumerate_l0_reachable_signatures", "execute", "l0_language",
    "l0_single_source_invariant_holds", "max_sources", "run_primitive_body",
    "source_signature",
]
