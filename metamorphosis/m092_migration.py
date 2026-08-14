"""M092-A — move the inherited micro-operations into state without changing what they mean.

This is the same move M090 made one level up, applied one level down, and under the same discipline:
**zero new expressive capability**. Every program here reproduces an arm of `m090_language.run_body`
exactly. Nothing is added, widened, generalized or "improved".

`run_body` survives in the codebase as the **frozen reference oracle** for the conservation proof
below. It is never execution authority after migration, and `run_body_from_state` does not import it,
call it, or fall back to it. The fresh-process script proves that by replacing `run_body` with a
tripwire and executing anyway.

The twelve programs are deliberately dull. `BINOP:max` is the only one with a branch, because `max`
is the only inherited operation that compares; it is written with `JLT` rather than a `MAX`
instruction so that the kernel stays general and the comparison lives in state. Every program is
loop-free, which `registered_reach_report` checks -- a substrate that cannot iterate cannot have
escaped the eventual-polynomial invariant, whatever the kernel underneath it could run.
"""
from __future__ import annotations

import itertools
from typing import Iterator, Sequence

from metamorphosis.m090_language import (
    BINARY_OPERATORS, CONST_VALUES, INPUT_COUNT, MAX_BODY_LENGTH, MAX_STACK_DEPTH,
    MICRO_OPERATIONS, SLOT_COUNT, UNARY_OPERATORS, LanguageError, MetaLanguageState,
    PrimitiveDefinition, execute, run_body,
)
from metamorphosis.m090_migration import INHERITED_DEFINITIONS, migrated_l0
from metamorphosis.m092_substrate_state import (
    SubstrateOperation, SubstrateState, execute_from_state, run_body_from_state,
)

MIGRATION_SCHEMA = "m092a-substrate-migration-v1"

_PROVENANCE = ("migrated from the m090 host interpreter arm of the same name",)


def _operation(key: str, role: str, program: Sequence[Sequence[object]]) -> SubstrateOperation:
    return SubstrateOperation(
        key=key, argument_role=role,
        program=tuple(tuple(step) for step in program),
        origin="inherited", provenance=_PROVENANCE,
    )


# ---------------------------------------------------------------------------------------------
# The twelve inherited micro-operations, as K1 programs. Jump targets are absolute.
# ---------------------------------------------------------------------------------------------

INHERITED_SUBSTRATE_OPERATIONS: tuple[SubstrateOperation, ...] = (
    # stack.append(int(inputs[index])), with the range check the reference performs first
    _operation("PUSH_INPUT", "index", [
        ("ARG", 0), ("GETINPUT", 1, 0), ("SPUSH", 1), ("HALT",),
    ]),
    _operation("PUSH_SLOT", "index", [
        ("ARG", 0), ("GETSLOT", 1, 0), ("SPUSH", 1), ("HALT",),
    ]),
    _operation("PUSH_CONST", "literal", [
        ("ARG", 0), ("SPUSH", 0), ("HALT",),
    ]),
    # stack.append(stack[-1]); SPEEK refuses on an empty stack exactly as the reference does
    _operation("DUP", "none", [
        ("LOADI", 0, 0), ("SPEEK", 1, 0), ("SPUSH", 1), ("HALT",),
    ]),
    # stack[-1], stack[-2] = stack[-2], stack[-1]
    _operation("SWAP", "none", [
        ("SPOP", 0), ("SPOP", 1), ("SPUSH", 0), ("SPUSH", 1), ("HALT",),
    ]),
    _operation("STORE_SLOT", "index", [
        ("ARG", 0), ("SPOP", 1), ("SETSLOT", 0, 1), ("HALT",),
    ]),

    # right, left = stack.pop(), stack.pop()  --  note the order, which the reference fixes
    _operation("BINOP:add", "selector", [
        ("SPOP", 1), ("SPOP", 0), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("BINOP:sub", "selector", [
        ("SPOP", 1), ("SPOP", 0), ("SUB", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("BINOP:mul", "selector", [
        ("SPOP", 1), ("SPOP", 0), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    # max(left, right), built from a comparison rather than from a MAX instruction
    _operation("BINOP:max", "selector", [
        ("SPOP", 1), ("SPOP", 0), ("JLT", 0, 1, 5), ("SPUSH", 0), ("HALT",),
        ("SPUSH", 1), ("HALT",),
    ]),

    _operation("UNOP:inc", "selector", [
        ("SPOP", 0), ("LOADI", 1, 1), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("UNOP:dec", "selector", [
        ("SPOP", 0), ("LOADI", 1, 1), ("SUB", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("UNOP:neg", "selector", [
        ("SPOP", 0), ("LOADI", 1, 0), ("SUB", 2, 1, 0), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("UNOP:double", "selector", [
        ("SPOP", 0), ("LOADI", 1, 2), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
)


def migrated_substrate() -> SubstrateState:
    """The inherited substrate, now entirely state-owned. Version 0: nothing has been acquired."""

    return SubstrateState(
        operations=INHERITED_SUBSTRATE_OPERATIONS,
        slot_count=SLOT_COUNT,
        input_count=INPUT_COUNT,
        max_body_length=MAX_BODY_LENGTH,
        max_stack_depth=MAX_STACK_DEPTH,
        literal_values=CONST_VALUES,
        substrate_version=0,
        provenance=("m091 micro-operations migrated into substrate state, semantics unchanged",),
    )


# M091's adopted primitive, restated as data so conservation covers acquired-language behaviour.
# M091's own modules are imported and read; none is edited.
M091_ACQUIRED_PRIMITIVE = PrimitiveDefinition(
    primitive_id="CLAMP_FLOOR",
    parameter_kinds=("slot",),
    body=(("PUSH_SLOT", "$0"), ("PUSH_CONST", 0), ("BINOP", "max"), ("STORE_SLOT", "$0")),
    origin="acquired",
    provenance=("m091 adopted primitive",),
)


def inherited_l1() -> MetaLanguageState:
    return MetaLanguageState(
        primitives=INHERITED_DEFINITIONS + (M091_ACQUIRED_PRIMITIVE,),
        language_version=1,
        provenance=("m091 extended language",),
    )


# ---------------------------------------------------------------------------------------------
# Conservation against the frozen reference oracle
# ---------------------------------------------------------------------------------------------

# The declared conservation alphabet. It includes deliberately illegal arguments -- an out-of-range
# index, an unregistered operator -- because conservation must cover refusals, not just successes.
def conservation_alphabet() -> tuple[tuple[str, object], ...]:
    alphabet: list[tuple[str, object]] = []
    for index in range(INPUT_COUNT):
        alphabet.append(("PUSH_INPUT", index))
    alphabet.append(("PUSH_INPUT", INPUT_COUNT))          # out of range
    for index in range(SLOT_COUNT):
        alphabet.append(("PUSH_SLOT", index))
    alphabet.append(("PUSH_SLOT", SLOT_COUNT))            # out of range
    for value in CONST_VALUES:
        alphabet.append(("PUSH_CONST", value))
    for operator in BINARY_OPERATORS:
        alphabet.append(("BINOP", operator))
    alphabet.append(("BINOP", "nonesuch"))                # unregistered selector
    for operator in UNARY_OPERATORS:
        alphabet.append(("UNOP", operator))
    alphabet.append(("UNOP", "nonesuch"))                 # unregistered selector
    alphabet.append(("DUP", None))
    alphabet.append(("SWAP", None))
    for index in range(SLOT_COUNT):
        alphabet.append(("STORE_SLOT", index))
    alphabet.append(("STORE_SLOT", SLOT_COUNT))           # out of range
    return tuple(alphabet)


CONSERVATION_STATES: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] = (
    ((0, 0, 0), (0, 0, 0, 0)),
    ((1, 2, 3), (0, 0, 0, 0)),
    ((-4, 3, 7), (-2, 5, 0, 1)),
    ((0, 5, -3), (3, -1, 4, 0)),
    ((9, -7, 4), (0, 0, -6, 2)),
    ((-1, 0, 2), (7, 7, 7, 7)),
    ((6, -6, 0), (-5, 5, -5, 5)),
    ((2, 2, 2), (1, 1, 1, 1)),
)


def _observe_reference(
    body, arguments, slots, inputs,
) -> tuple[str, object]:
    try:
        return ("value", tuple(run_body(body, arguments, list(slots), inputs)))
    except (LanguageError, ValueError, TypeError):
        return ("refused", None)


def _observe_state(
    body, arguments, slots, inputs, substrate: SubstrateState,
) -> tuple[str, object]:
    try:
        return (
            "value",
            tuple(run_body_from_state(body, arguments, list(slots), inputs, substrate)),
        )
    except (LanguageError, ValueError, TypeError):
        return ("refused", None)


def enumerate_bodies(max_length: int) -> Iterator[tuple[tuple[str, object], ...]]:
    alphabet = conservation_alphabet()
    for length in range(1, max_length + 1):
        for body in itertools.product(alphabet, repeat=length):
            yield tuple(body)


def body_conservation(
    substrate: SubstrateState, max_length: int = 3,
) -> dict[str, object]:
    """Exhaustive over the micro-operation body space, at every declared state."""

    comparisons = values = refusals = mismatches = 0
    first_mismatch = None
    for body in enumerate_bodies(max_length):
        for inputs, slots in CONSERVATION_STATES:
            reference = _observe_reference(body, (), slots, inputs)
            observed = _observe_state(body, (), slots, inputs, substrate)
            comparisons += 1
            if reference != observed:
                mismatches += 1
                if first_mismatch is None:
                    first_mismatch = {
                        "body": [[n, a] for n, a in body], "inputs": list(inputs),
                        "slots": list(slots), "reference": str(reference), "state": str(observed),
                    }
            elif reference[0] == "value":
                values += 1
            else:
                refusals += 1
    return {
        "max_body_length_enumerated": max_length,
        "alphabet_size": len(conservation_alphabet()),
        "states": len(CONSERVATION_STATES),
        "comparisons": comparisons,
        "agreeing_values": values,
        "agreeing_refusals": refusals,
        "mismatches": mismatches,
        "first_mismatch": first_mismatch,
        "exhaustive": True,
    }


def _parameter_bindings(kinds: Sequence[str], substrate: SubstrateState) -> list[tuple[object, ...]]:
    axes: list[Sequence[object]] = []
    for kind in kinds:
        if kind == "slot":
            axes.append(range(substrate.slot_count))
        elif kind == "input":
            axes.append(range(substrate.input_count))
        elif kind == "const":
            axes.append(substrate.literal_values)
        elif kind == "unary_op":
            axes.append(substrate.selector_values("UNOP"))
        else:
            raise LanguageError(f"unknown parameter kind {kind!r}")
    return [tuple(row) for row in itertools.product(*axes)] if axes else [()]


def language_conservation(
    substrate: SubstrateState, language: MetaLanguageState, max_program_length: int = 2,
) -> dict[str, object]:
    """Exhaustive over the language's own declared parameter domains, including the acquired op.

    The declared and covered binding counts are reported side by side and the caller fails if they
    differ. That is M090's amendment A2, which M091 enforced rather than remembered.
    """

    calls: list[tuple[str, tuple[object, ...]]] = []
    declared = 0
    for definition in language.primitives:
        bindings = _parameter_bindings(definition.parameter_kinds, substrate)
        declared += len(bindings)
        for binding in bindings:
            calls.append((definition.primitive_id, binding))

    programs = 0
    comparisons = mismatches = 0
    first_mismatch = None
    for length in range(1, max_program_length + 1):
        for program in itertools.product(calls, repeat=length):
            programs += 1
            for inputs, _ in CONSERVATION_STATES:
                try:
                    reference: tuple[str, object] = (
                        "value", execute(list(program), inputs, language),
                    )
                except (LanguageError, ValueError, TypeError):
                    reference = ("refused", None)
                try:
                    observed: tuple[str, object] = (
                        "value", execute_from_state(list(program), inputs, language, substrate),
                    )
                except (LanguageError, ValueError, TypeError):
                    observed = ("refused", None)
                comparisons += 1
                if reference != observed:
                    mismatches += 1
                    if first_mismatch is None:
                        first_mismatch = {
                            "program": [[n, list(a)] for n, a in program],
                            "inputs": list(inputs),
                            "reference": str(reference), "state": str(observed),
                        }
    return {
        "language_version": language.language_version,
        "primitives": len(language.primitives),
        "declared_bindings": declared,
        "covered_bindings": len(calls),
        "coverage_is_complete": declared == len(calls),
        "programs": programs,
        "comparisons": comparisons,
        "mismatches": mismatches,
        "first_mismatch": first_mismatch,
    }


REFUSAL_BATTERY: tuple[tuple[str, tuple[tuple[str, object], ...]], ...] = (
    ("binop_on_empty_stack", (("BINOP", "add"),)),
    ("binop_on_one_operand", (("PUSH_CONST", 1), ("BINOP", "add"))),
    ("unop_on_empty_stack", (("UNOP", "inc"),)),
    ("dup_on_empty_stack", (("DUP", None),)),
    ("swap_on_empty_stack", (("SWAP", None),)),
    ("swap_on_one_operand", (("PUSH_CONST", 1), ("SWAP", None))),
    ("store_on_empty_stack", (("STORE_SLOT", 0),)),
    ("slot_index_out_of_range", (("PUSH_SLOT", 99),)),
    ("input_index_out_of_range", (("PUSH_INPUT", 99),)),
    ("store_slot_out_of_range", (("PUSH_CONST", 1), ("STORE_SLOT", 99))),
    ("unknown_binary_operator", (("PUSH_CONST", 1), ("PUSH_CONST", 1), ("BINOP", "nope"))),
    ("unknown_unary_operator", (("PUSH_CONST", 1), ("UNOP", "nope"))),
    ("unknown_micro_operation", (("NO_SUCH_OP", 0),)),
    ("body_exceeds_length_bound", tuple(("PUSH_CONST", 1) for _ in range(MAX_BODY_LENGTH + 1))),
    # NOT a refusal, and deliberately kept: see `stack_bound_is_unreachable` below. A maximal legal
    # body pushes six values against a bound of eight, so this case succeeds on both sides and is
    # here to record that the bound is never reached rather than to claim it is enforced.
    ("maximal_legal_push_body", tuple(("PUSH_CONST", 1) for _ in range(MAX_BODY_LENGTH))),
)


def stack_bound_is_unreachable() -> dict[str, object]:
    """An honest negative finding about the frozen representation, recorded rather than hidden.

    Both the reference interpreter and the state-owned dispatcher check `len(stack) > 8` before
    every micro-operation, and neither check can ever fire: a body is at most six micro-operations
    long, so it can push at most six values. The branch is dead code on both sides. It is conserved
    exactly -- vacuously -- and no conservation claim here should be read as evidence that the stack
    bound was exercised.
    """

    return {
        "max_body_length": MAX_BODY_LENGTH,
        "max_stack_depth": MAX_STACK_DEPTH,
        "maximum_reachable_stack_depth": MAX_BODY_LENGTH,
        "bound_is_reachable": MAX_BODY_LENGTH > MAX_STACK_DEPTH,
        "conserved_vacuously_on_both_sides": True,
    }


def refusal_conservation(substrate: SubstrateState) -> dict[str, object]:
    """Every declared refusal, named, and required to refuse identically on both sides."""

    rows = []
    disagreements = 0
    for name, body in REFUSAL_BATTERY:
        reference = _observe_reference(body, (), (0, 0, 0, 0), (0, 0, 0))
        observed = _observe_state(body, (), (0, 0, 0, 0), (0, 0, 0), substrate)
        agree = reference == observed
        if not agree:
            disagreements += 1
        rows.append({
            "case": name,
            "reference": reference[0],
            "state_owned": observed[0],
            "agree": agree,
        })
    return {
        "cases": rows,
        "count": len(rows),
        "disagreements": disagreements,
        "refusals_on_both_sides": sum(
            1 for row in rows if row["reference"] == "refused" and row["state_owned"] == "refused"
        ),
    }


# Parameterised arguments. The exhaustive sweep uses literal operands only, so `$n` resolution --
# which is how every real primitive body actually addresses its operands -- would go untested
# without these.
PARAMETERISED_ALPHABET: tuple[tuple[str, object], ...] = (
    ("PUSH_SLOT", "$0"), ("STORE_SLOT", "$0"), ("PUSH_INPUT", "$1"),
    ("PUSH_CONST", "$1"), ("BINOP", "$1"), ("UNOP", "$1"),
)

ADVERSARIAL_ARGUMENTS: tuple[tuple[object, ...], ...] = (
    (0, "max"), (1, "neg"), (3, 0), (2, "double"), (0, 1), (1, "nonesuch"), (9, "add"),
)


def adversarial_conservation(
    substrate: SubstrateState, trials: int = 200_000, seed: int = 7,
) -> dict[str, object]:
    """Attack conservation where enumeration is *not* exhaustive: lengths 4-6, and `$n` operands.

    Reported separately from `body_conservation` and never described as exhaustive. The value and
    refusal counts are both reported, because a sweep that refused almost everything would look
    reassuring while testing almost nothing.
    """

    import random

    generator = random.Random(seed)
    alphabet = list(conservation_alphabet()) + list(PARAMETERISED_ALPHABET)
    checked = values = refusals = mismatches = 0
    first_mismatch = None
    for _ in range(trials):
        length = generator.randint(4, MAX_BODY_LENGTH)
        body = tuple(alphabet[generator.randrange(len(alphabet))] for _ in range(length))
        arguments = ADVERSARIAL_ARGUMENTS[generator.randrange(len(ADVERSARIAL_ARGUMENTS))]
        slots = [generator.randint(-9, 9) for _ in range(SLOT_COUNT)]
        inputs = [generator.randint(-9, 9) for _ in range(INPUT_COUNT)]
        reference = _observe_reference(body, arguments, slots, inputs)
        observed = _observe_state(body, arguments, slots, inputs, substrate)
        checked += 1
        if reference[0] == "refused":
            refusals += 1
        else:
            values += 1
        if reference != observed:
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = {
                    "body": [[n, a] for n, a in body], "arguments": list(arguments),
                    "slots": slots, "inputs": inputs,
                    "reference": str(reference), "state": str(observed),
                }
    return {
        "trials": checked,
        "body_lengths": [4, MAX_BODY_LENGTH],
        "includes_parameterised_operands": True,
        "reference_values": values,
        "reference_refusals": refusals,
        "mismatches": mismatches,
        "first_mismatch": first_mismatch,
        "exhaustive": False,
        "note": "randomised corroboration beyond the exhaustive space, not a proof",
    }


def capability_conservation(substrate: SubstrateState) -> dict[str, object]:
    """No migrated operation may hold a capability the language did not already permit."""

    from metamorphosis.m090_language import FORBIDDEN_CAPABILITIES, PERMITTED_CAPABILITIES

    held: set[str] = set()
    for operation in substrate.operations:
        held.update(operation.capabilities)
    return {
        "capabilities_held": sorted(held),
        "permitted": list(PERMITTED_CAPABILITIES),
        "forbidden": list(FORBIDDEN_CAPABILITIES),
        "holds_only_permitted": held.issubset(set(PERMITTED_CAPABILITIES)),
        "holds_nothing_forbidden": not held.intersection(set(FORBIDDEN_CAPABILITIES)),
        "capability_set_unchanged": sorted(held) == sorted(set(PERMITTED_CAPABILITIES)),
    }


def serialization_conservation(substrate: SubstrateState) -> dict[str, object]:
    """A round trip must be byte-identical and behaviourally identical."""

    text = substrate.serialize()
    restored = SubstrateState.deserialize(text)
    same_bytes = restored.serialize() == text
    same_digest = restored.digest() == substrate.digest()
    behavioural = 0
    mismatches = 0
    for body in enumerate_bodies(2):
        for inputs, slots in CONSERVATION_STATES[:3]:
            left = _observe_state(body, (), slots, inputs, substrate)
            right = _observe_state(body, (), slots, inputs, restored)
            behavioural += 1
            if left != right:
                mismatches += 1
    return {
        "byte_identical": same_bytes,
        "digest_identical": same_digest,
        "behavioural_comparisons": behavioural,
        "behavioural_mismatches": mismatches,
        "digest": substrate.digest(),
    }


def signature_conservation(substrate: SubstrateState) -> dict[str, object]:
    """The micro-operation names and selector values must be exactly M091's, with none added."""

    return {
        "names": sorted(substrate.operation_names),
        "reference_names": sorted(MICRO_OPERATIONS),
        "names_identical": sorted(substrate.operation_names) == sorted(MICRO_OPERATIONS),
        "binary_selectors": list(substrate.selector_values("BINOP")),
        "reference_binary": sorted(BINARY_OPERATORS),
        "binary_identical": (
            list(substrate.selector_values("BINOP")) == sorted(BINARY_OPERATORS)
        ),
        "unary_selectors": list(substrate.selector_values("UNOP")),
        "reference_unary": sorted(UNARY_OPERATORS),
        "unary_identical": list(substrate.selector_values("UNOP")) == sorted(UNARY_OPERATORS),
        "literal_values": list(substrate.literal_values),
        "reference_literals": list(CONST_VALUES),
        "literals_identical": list(substrate.literal_values) == list(CONST_VALUES),
        "acquired_operations": [
            operation.key for operation in substrate.operations if operation.origin != "inherited"
        ],
        "nothing_acquired": all(
            operation.origin == "inherited" for operation in substrate.operations
        ),
    }


__all__ = [
    "ADVERSARIAL_ARGUMENTS", "CONSERVATION_STATES", "INHERITED_SUBSTRATE_OPERATIONS",
    "M091_ACQUIRED_PRIMITIVE", "PARAMETERISED_ALPHABET", "adversarial_conservation",
    "MIGRATION_SCHEMA", "REFUSAL_BATTERY", "body_conservation", "capability_conservation",
    "conservation_alphabet", "enumerate_bodies", "inherited_l1", "language_conservation",
    "migrated_l0", "migrated_substrate", "refusal_conservation", "serialization_conservation",
    "signature_conservation", "stack_bound_is_unreachable",
]
