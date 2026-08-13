"""Move M089's inherited operations into state without changing what they mean.

Three operations lived in `m089_meta_language`: `SET_CONST`, `COPY_INPUT` and `APPLY_UNARY`, each
implemented by a host function reached through a module constant. Here each becomes **one**
serialized definition over the interpreter substrate — one, not one per literal, which is why the
substrate carries `const` and `unary_op` parameter kinds. A registry that needed a separate entry
per constant would be smuggling semantics into its own shape.

The conservation proof runs both implementations over an exhaustive program space and requires
identical slots. M089's host interpreter is used **only here**, as the reference against which the
migration is checked, and it is unreachable from the qualifying execution path — a property the
anti-leak checker verifies from the import graph rather than by assertion.
"""
from __future__ import annotations

import itertools
from typing import Iterator, Sequence

from metamorphosis.m090_language import (
    CONST_VALUES,
    INPUT_COUNT,
    SLOT_COUNT,
    UNARY_OPERATORS,
    MetaLanguageState,
    PrimitiveDefinition,
    execute,
)


# The inherited operations, as data. Every one is a body over the substrate; none is a host
# function, and the interpreter has never heard of any of their names.
INHERITED_DEFINITIONS = (
    PrimitiveDefinition(
        primitive_id="SET_CONST",
        parameter_kinds=("slot", "const"),
        body=(("PUSH_CONST", "$1"), ("STORE_SLOT", "$0")),
        origin="inherited",
        provenance=("migrated from m089 host implementation",),
    ),
    PrimitiveDefinition(
        primitive_id="COPY_INPUT",
        parameter_kinds=("slot", "input"),
        body=(("PUSH_INPUT", "$1"), ("STORE_SLOT", "$0")),
        origin="inherited",
        provenance=("migrated from m089 host implementation",),
    ),
    PrimitiveDefinition(
        primitive_id="APPLY_UNARY",
        parameter_kinds=("slot", "unary_op"),
        body=(("PUSH_SLOT", "$0"), ("UNOP", "$1"), ("STORE_SLOT", "$0")),
        origin="inherited",
        provenance=("migrated from m089 host implementation",),
    ),
)

# The probe extension. Deliberately simple and authored: M090 is about where semantics LIVE, not
# about whether the lineage can invent one. Claiming otherwise would blur this into M089.
PROBE_EXTENSION = PrimitiveDefinition(
    primitive_id="COMBINE_INPUTS",
    parameter_kinds=("slot", "input", "input"),
    body=(
        ("PUSH_INPUT", "$1"), ("PUSH_INPUT", "$2"), ("BINOP", "add"), ("STORE_SLOT", "$0"),
    ),
    origin="acquired",
    provenance=("registered as an architectural probe, not as an endogenous invention",),
)


def migrated_l0() -> MetaLanguageState:
    """The inherited language, now entirely state-owned."""

    return MetaLanguageState(
        primitives=INHERITED_DEFINITIONS,
        language_version=0,
        provenance=("inherited operations migrated into lineage state",),
    )


def with_probe_extension(language: MetaLanguageState) -> MetaLanguageState:
    return language.register(
        PROBE_EXTENSION, "architectural probe extension registered through the one registry",
    )


# ---------------------------------------------------------------------------------------------
# conservation of the inherited semantics
# ---------------------------------------------------------------------------------------------


def legacy_alphabet() -> list[tuple[str, tuple[object, ...]]]:
    """Every call M089's inherited language admitted."""

    alphabet: list[tuple[str, tuple[object, ...]]] = []
    for slot in range(SLOT_COUNT):
        for constant in CONST_VALUES:
            alphabet.append(("SET_CONST", (slot, constant)))
        for index in range(INPUT_COUNT):
            alphabet.append(("COPY_INPUT", (slot, index)))
        for operator in UNARY_OPERATORS:
            # No exclusions. An operator excluded from the conservation space is an operator whose
            # conservation is not proved, which is exactly how the first draft hid a widened domain.
            alphabet.append(("APPLY_UNARY", (slot, operator)))
    return alphabet


def legacy_programs(max_length: int = 2) -> Iterator[tuple[tuple[str, tuple[object, ...]], ...]]:
    alphabet = legacy_alphabet()
    for length in range(1, max_length + 1):
        for program in itertools.product(alphabet, repeat=length):
            yield program


CONSERVATION_INPUTS = ((1, 2, 3), (0, 4, 1), (-2, 5, 7), (9, 0, 6))


def conservation_report(max_length: int = 2) -> dict[str, object]:
    """Run the historical host implementation and the state-owned one over the same space.

    The reference is imported inside this function so that it is reachable from the migration
    check and from nowhere in the qualifying path.
    """

    from metamorphosis.m089_meta_language import execute as legacy_execute
    from metamorphosis.m089_meta_language import l0_language as legacy_language

    reference = legacy_language()
    migrated = migrated_l0()
    checked = 0
    mismatches: list[dict[str, object]] = []
    for program in legacy_programs(max_length):
        for inputs in CONSERVATION_INPUTS:
            checked += 1
            expected = legacy_execute(program, inputs, reference)
            actual = execute(program, inputs, migrated)
            if expected != actual:
                mismatches.append({
                    "program": [[name, list(arguments)] for name, arguments in program],
                    "inputs": list(inputs),
                    "legacy": list(expected),
                    "migrated": list(actual),
                })
    return {
        "programs_checked": checked,
        "max_length": max_length,
        "mismatches": mismatches[:10],
        "mismatch_count": len(mismatches),
        "semantics_conserved": not mismatches,
    }


__all__ = [
    "CONSERVATION_INPUTS", "INHERITED_DEFINITIONS", "PROBE_EXTENSION", "conservation_report",
    "legacy_alphabet", "legacy_programs", "migrated_l0", "with_probe_extension",
]
