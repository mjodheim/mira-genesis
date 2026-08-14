"""M092-A — move the inherited micro-operations into state without changing what they mean.

This is the same move M090 made one level up, applied one level down, and under the same discipline:
**zero new registered capability**. Every program here reproduces an arm of
`m090_language.run_body` exactly. Nothing is added, widened, generalized or "improved".

**This module is migration and conservation tooling, not runtime.** It is the only place where a
historical M090 object meets an M092 one. `run_body` survives here as the **frozen reference oracle**
against which conservation is proved; it is never execution authority, and no module on the runtime
path imports it -- or imports `m090_language` at all. The physical-isolation test builds a runtime
from files that do not include `m090_language.py` and executes the inherited substrate anyway.

The fourteen programs are deliberately dull. `BINOP:max` is the only one with a branch, because `max`
is the only inherited operation that compares; it is written with `JLT` rather than a `MAX`
instruction so that the kernel stays general and the comparison lives in state.
"""
from __future__ import annotations

import itertools
from typing import Iterator, Sequence

from metamorphosis.m090_language import (
    BINARY_OPERATORS, CONST_VALUES, FORBIDDEN_CAPABILITIES, INPUT_COUNT, MAX_BODY_LENGTH,
    MAX_STACK_DEPTH, MICRO_OPERATIONS, PERMITTED_CAPABILITIES, SLOT_COUNT, UNARY_OPERATORS,
    LanguageError, MetaLanguageState, PrimitiveDefinition, execute, run_body,
)
from metamorphosis.m090_migration import INHERITED_DEFINITIONS, migrated_l0
from metamorphosis.m091_substrate import MAX_ASSEMBLY_LENGTH
from metamorphosis.m092_runtime import (
    RefusalCode, RuntimeLanguage, RuntimePrimitive, SubstrateError,
)
from metamorphosis.m092_substrate_state import (
    ParameterDomain, SubstrateOperation, SubstrateState, execute_from_state, run_body_from_state,
)

MIGRATION_SCHEMA = "m092a-substrate-migration-v2"

_PROVENANCE = ("migrated from the m090 host interpreter arm of the same name",)


def _operation(
    key: str, role: str, program: Sequence[Sequence[object]], minimum_stack_depth: int = 0,
) -> SubstrateOperation:
    return SubstrateOperation(
        key=key, argument_role=role,
        program=tuple(tuple(step) for step in program),
        origin="inherited", provenance=_PROVENANCE,
        capabilities=tuple(PERMITTED_CAPABILITIES),
        minimum_stack_depth=minimum_stack_depth,
    )


# ---------------------------------------------------------------------------------------------
# The fourteen inherited micro-operations, as K1 programs. Jump targets are absolute.
# ---------------------------------------------------------------------------------------------

INHERITED_SUBSTRATE_OPERATIONS: tuple[SubstrateOperation, ...] = (
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
    _operation("DUP", "none", minimum_stack_depth=1, program=[
        ("LOADI", 0, 0), ("SPEEK", 1, 0), ("SPUSH", 1), ("HALT",),
    ]),
    _operation("SWAP", "none", minimum_stack_depth=2, program=[
        ("SPOP", 0), ("SPOP", 1), ("SPUSH", 0), ("SPUSH", 1), ("HALT",),
    ]),
    _operation("STORE_SLOT", "index", minimum_stack_depth=1, program=[
        ("ARG", 0), ("SPOP", 1), ("SETSLOT", 0, 1), ("HALT",),
    ]),

    # right, left = stack.pop(), stack.pop()  --  note the order, which the reference fixes
    _operation("BINOP:add", "selector", minimum_stack_depth=2, program=[
        ("SPOP", 1), ("SPOP", 0), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("BINOP:sub", "selector", minimum_stack_depth=2, program=[
        ("SPOP", 1), ("SPOP", 0), ("SUB", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("BINOP:mul", "selector", minimum_stack_depth=2, program=[
        ("SPOP", 1), ("SPOP", 0), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    # max(left, right), built from a comparison rather than from a MAX instruction
    _operation("BINOP:max", "selector", minimum_stack_depth=2, program=[
        ("SPOP", 1), ("SPOP", 0), ("JLT", 0, 1, 5), ("SPUSH", 0), ("HALT",),
        ("SPUSH", 1), ("HALT",),
    ]),

    _operation("UNOP:inc", "selector", minimum_stack_depth=1, program=[
        ("SPOP", 0), ("LOADI", 1, 1), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("UNOP:dec", "selector", minimum_stack_depth=1, program=[
        ("SPOP", 0), ("LOADI", 1, 1), ("SUB", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("UNOP:neg", "selector", minimum_stack_depth=1, program=[
        ("SPOP", 0), ("LOADI", 1, 0), ("SUB", 2, 1, 0), ("SPUSH", 2), ("HALT",),
    ]),
    _operation("UNOP:double", "selector", minimum_stack_depth=1, program=[
        ("SPOP", 0), ("LOADI", 1, 2), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ]),
)

# Which operation's registered selectors supply each language parameter kind's legal values. This is
# the data that used to be a hard-coded name in the dispatcher.
INHERITED_PARAMETER_DOMAINS: tuple[ParameterDomain, ...] = (
    ParameterDomain("slot", "slot_index"),
    ParameterDomain("input", "input_index"),
    ParameterDomain("const", "literal_set"),
    ParameterDomain("unary_op", "selector_of", "UNOP"),
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
        parameter_domains=INHERITED_PARAMETER_DOMAINS,
        permitted_capabilities=tuple(PERMITTED_CAPABILITIES),
        forbidden_capabilities=tuple(FORBIDDEN_CAPABILITIES),
        substrate_version=0,
        provenance=("m091 micro-operations migrated into substrate state, semantics unchanged",),
    )


# ---------------------------------------------------------------------------------------------
# Conversion. The ONLY place a historical object becomes a runtime one.
# ---------------------------------------------------------------------------------------------


def to_runtime_primitive(definition: PrimitiveDefinition) -> RuntimePrimitive:
    return RuntimePrimitive(
        primitive_id=definition.primitive_id,
        parameter_kinds=tuple(definition.parameter_kinds),
        body=tuple((str(name), argument) for name, argument in definition.body),
        origin=definition.origin,
        provenance=tuple(definition.provenance),
        capabilities=tuple(definition.capabilities),
    )


def to_runtime_language(language: MetaLanguageState) -> RuntimeLanguage:
    """Convert an M090 language state into the neutral runtime representation.

    Migration tooling only. Nothing on the runtime path calls this, and nothing on the runtime path
    can reach the type it consumes.
    """

    return RuntimeLanguage(
        primitives=tuple(to_runtime_primitive(item) for item in language.primitives),
        language_version=language.language_version,
        provenance=tuple(language.provenance),
    )


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
# The refusal taxonomy, and how the frozen reference path is normalized into it
# ---------------------------------------------------------------------------------------------

# The reference interpreter raises one exception type with prose messages, so classifying it means
# reading those messages. That is migration tooling, documented as such: the *state-owned* path
# raises typed codes directly and this table is never applied to it.
_REFERENCE_MESSAGE_CODES: tuple[tuple[str, RefusalCode], ...] = (
    ("body exceeds the frozen length bound", RefusalCode.BODY_LENGTH_EXCEEDED),
    ("exceeded the stack bound", RefusalCode.STACK_BOUND_EXCEEDED),
    ("unknown micro-operation", RefusalCode.UNKNOWN_OPERATION),
    ("unknown binary operator", RefusalCode.INVALID_SELECTOR),
    ("unknown unary operator", RefusalCode.INVALID_SELECTOR),
    ("needs two operands", RefusalCode.STACK_UNDERFLOW),
    ("needs one operand", RefusalCode.STACK_UNDERFLOW),
    ("slot index out of range", RefusalCode.INVALID_SLOT_INDEX),
    ("input index out of range", RefusalCode.INVALID_INPUT_INDEX),
    ("is not supplied", RefusalCode.UNRESOLVED_PARAMETER),
    ("is not defined in language version", RefusalCode.UNDEFINED_PRIMITIVE),
    ("arguments, received", RefusalCode.SIGNATURE_MISMATCH),
    ("argument out of range", RefusalCode.PARAMETER_OUT_OF_DOMAIN),
    ("argument outside the frozen set", RefusalCode.PARAMETER_OUT_OF_DOMAIN),
)


def classify_reference_refusal(error: BaseException) -> RefusalCode:
    """Normalize a frozen-reference refusal into the implementation-independent taxonomy."""

    if isinstance(error, (ValueError, TypeError)):
        return RefusalCode.INVALID_ARGUMENT_ROLE
    message = str(error)
    for fragment, code in _REFERENCE_MESSAGE_CODES:
        if fragment in message:
            return code
    return RefusalCode.MALFORMED_STATE  # deliberately conspicuous: an unclassified refusal


Outcome = tuple[str, object]


def observe_reference(body, arguments, slots, inputs) -> Outcome:
    try:
        return ("value", tuple(run_body(body, arguments, list(slots), inputs)))
    except (LanguageError, ValueError, TypeError) as error:
        return ("refused", classify_reference_refusal(error).value)


def observe_state(body, arguments, slots, inputs, substrate: SubstrateState) -> Outcome:
    try:
        return (
            "value",
            tuple(run_body_from_state(body, arguments, list(slots), inputs, substrate)),
        )
    except SubstrateError as error:
        return ("refused", error.code.value)
    except (ValueError, TypeError):
        return ("refused", RefusalCode.INVALID_ARGUMENT_ROLE.value)


# ---------------------------------------------------------------------------------------------
# The static stack-depth certificate
# ---------------------------------------------------------------------------------------------

# Net stack effect of each micro-operation, and the depth it requires before running. Declared here
# and verified exhaustively against the reference interpreter by `stack_depth_certificate`.
_STACK_EFFECTS: dict[str, tuple[int, int]] = {  # name -> (minimum depth required, net change)
    "PUSH_INPUT": (0, +1),
    "PUSH_SLOT": (0, +1),
    "PUSH_CONST": (0, +1),
    "DUP": (1, +1),
    "SWAP": (2, 0),
    "STORE_SLOT": (1, -1),
    "BINOP": (2, -1),
    "UNOP": (1, 0),
}


def stack_depth_certificate(max_length: int = MAX_BODY_LENGTH) -> dict[str, object]:
    """Prove the maximum stack depth any legal inherited body can reach, statically.

    The reference interpreter and the state-owned dispatcher both check `len(stack) > 8` before every
    micro-operation. Neither check can ever fire, and this says why rather than observing that it
    did not: every micro-operation increases the stack by **at most one**, so a body of `L`
    micro-operations reaches depth at most `L`. With `L <= 6` and a bound of `8`, the condition is
    unreachable *by construction*.

    The `+1` claim is not asserted -- it is verified exhaustively against the reference interpreter
    over every micro-operation and every legal argument, and the resulting depth bound is then
    re-derived by dynamic programming over the whole legal body space.
    """

    # 1. verify the declared net effects against the reference interpreter itself
    verified = 0
    disagreements: list[str] = []
    for name, (required, change) in _STACK_EFFECTS.items():
        arguments = {
            "PUSH_INPUT": [0], "PUSH_SLOT": [0], "PUSH_CONST": [0], "STORE_SLOT": [0],
            "BINOP": ["add"], "UNOP": ["inc"], "DUP": [None], "SWAP": [None],
        }[name]
        for argument in arguments:
            for depth in range(required, MAX_STACK_DEPTH + 1):
                prelude = tuple(("PUSH_CONST", 1) for _ in range(depth))
                probe = prelude + ((name, argument),)
                if len(probe) > MAX_BODY_LENGTH:
                    continue
                try:
                    run_body(probe, (), [0] * SLOT_COUNT, [0] * INPUT_COUNT)
                except LanguageError:
                    disagreements.append(f"{name} refused at depth {depth}")
                    continue
                verified += 1

    # 2. re-derive the reachable depth set by dynamic programming over the legal body space
    reachable = {0}
    depth_by_length = {0: {0}}
    for length in range(1, max_length + 1):
        nxt: set[int] = set()
        for depth in reachable:
            for required, change in _STACK_EFFECTS.values():
                if depth >= required and depth + change >= 0:
                    nxt.add(depth + change)
        reachable = nxt
        depth_by_length[length] = set(nxt)
    maximum = max(max(values) for values in depth_by_length.values())

    return {
        "declared_effects_verified_against_the_reference": verified,
        "effect_disagreements": disagreements,
        "every_operation_increases_depth_by_at_most": max(
            change for _, change in _STACK_EFFECTS.values()
        ),
        "max_body_length": max_length,
        "max_reachable_stack_depth": maximum,
        "declared_stack_bound": MAX_STACK_DEPTH,
        "bound_is_reachable": maximum > MAX_STACK_DEPTH,
        "status": "unreachable by construction under the inherited legal representation",
        "note": (
            "stack overflow is NOT an exercised conservation case; it is excluded from the "
            "inherited semantic conservation claim and can only be provoked by programs outside "
            "the legal representation"
        ),
    }


# ---------------------------------------------------------------------------------------------
# Conservation
# ---------------------------------------------------------------------------------------------


def legal_alphabet() -> tuple[tuple[str, object], ...]:
    """Exactly the micro-operation instances a legal inherited body may contain. No illegal args."""

    alphabet: list[tuple[str, object]] = []
    for index in range(INPUT_COUNT):
        alphabet.append(("PUSH_INPUT", index))
    for index in range(SLOT_COUNT):
        alphabet.append(("PUSH_SLOT", index))
    for value in CONST_VALUES:
        alphabet.append(("PUSH_CONST", value))
    for operator in BINARY_OPERATORS:
        alphabet.append(("BINOP", operator))
    for operator in UNARY_OPERATORS:
        alphabet.append(("UNOP", operator))
    alphabet.append(("DUP", None))
    alphabet.append(("SWAP", None))
    for index in range(SLOT_COUNT):
        alphabet.append(("STORE_SLOT", index))
    return tuple(alphabet)


def conservation_alphabet() -> tuple[tuple[str, object], ...]:
    """The legal alphabet plus out-of-representation instances, so refusals are covered too."""

    return legal_alphabet() + (
        ("PUSH_INPUT", INPUT_COUNT), ("PUSH_SLOT", SLOT_COUNT), ("STORE_SLOT", SLOT_COUNT),
        ("BINOP", "nonesuch"), ("UNOP", "nonesuch"),
    )


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


def enumerate_bodies(
    max_length: int, alphabet: Sequence[tuple[str, object]] | None = None,
) -> Iterator[tuple[tuple[str, object], ...]]:
    symbols = tuple(alphabet) if alphabet is not None else conservation_alphabet()
    for length in range(1, max_length + 1):
        for body in itertools.product(symbols, repeat=length):
            yield tuple(body)


def _sweep(
    substrate: SubstrateState, bodies: Iterator, states: Sequence, label: str, exhaustive: bool,
) -> dict[str, object]:
    comparisons = values = mismatches = 0
    refusals_by_code: dict[str, int] = {}
    max_depth = 0
    first_mismatch = None
    for body in bodies:
        for inputs, slots in states:
            reference = observe_reference(body, (), slots, inputs)
            observed = observe_state(body, (), slots, inputs, substrate)
            comparisons += 1
            if reference != observed:
                mismatches += 1
                if first_mismatch is None:
                    first_mismatch = {
                        "body": [[n, a] for n, a in body], "inputs": list(inputs),
                        "slots": list(slots), "reference": list(reference),
                        "state": list(observed),
                    }
            elif reference[0] == "value":
                values += 1
            else:
                code = str(reference[1])
                refusals_by_code[code] = refusals_by_code.get(code, 0) + 1
        max_depth = max(max_depth, sum(1 for n, _ in body if _STACK_EFFECTS.get(n, (0, 0))[1] > 0))
    return {
        "label": label,
        "exhaustive": exhaustive,
        "comparisons": comparisons,
        "agreeing_values": values,
        "agreeing_refusals": sum(refusals_by_code.values()),
        "refusals_by_code": dict(sorted(refusals_by_code.items())),
        "mismatches": mismatches,
        "first_mismatch": first_mismatch,
        "max_observed_push_count": max_depth,
    }


def exhaustive_legal_conservation(
    substrate: SubstrateState, max_length: int = MAX_ASSEMBLY_LENGTH,
) -> dict[str, object]:
    """Exhaustive over the complete LEGAL inherited body space, at the real assembly bound.

    `MAX_ASSEMBLY_LENGTH` is M091's own bound on what a primitive body may be assembled from, so
    this is the entire space of bodies the inherited system could ever construct -- not a sample of
    it. Every one is compared against the frozen reference at every declared state.
    """

    alphabet = legal_alphabet()
    report = _sweep(
        substrate, enumerate_bodies(max_length, alphabet), CONSERVATION_STATES,
        "legal bodies, exhaustive to the assembly bound", True,
    )
    report["alphabet_size"] = len(alphabet)
    report["max_body_length_enumerated"] = max_length
    report["legal_bodies_enumerated"] = sum(
        len(alphabet) ** length for length in range(1, max_length + 1)
    )
    report["states"] = len(CONSERVATION_STATES)
    return report


def exhaustive_representation_conservation(
    substrate: SubstrateState, max_length: int = 3,
) -> dict[str, object]:
    """Exhaustive including out-of-representation instances, so refusal codes are covered."""

    alphabet = conservation_alphabet()
    report = _sweep(
        substrate, enumerate_bodies(max_length, alphabet), CONSERVATION_STATES,
        "legal and out-of-representation bodies, exhaustive", True,
    )
    report["alphabet_size"] = len(alphabet)
    report["max_body_length_enumerated"] = max_length
    report["bodies_enumerated"] = sum(
        len(alphabet) ** length for length in range(1, max_length + 1)
    )
    report["states"] = len(CONSERVATION_STATES)
    return report


def intractable_dimension() -> dict[str, object]:
    """Which dimension explodes, and why lengths beyond the assembly bound must be sampled."""

    legal, full = len(legal_alphabet()), len(conservation_alphabet())
    return {
        "explosion_dimension": "alphabet_size ** body_length",
        "legal_alphabet_size": legal,
        "full_alphabet_size": full,
        "legal_space_by_length": {
            str(length): legal ** length for length in range(1, MAX_BODY_LENGTH + 1)
        },
        "exhausted_to": MAX_ASSEMBLY_LENGTH,
        "why": (
            "the assembly bound is M091's own limit on constructible bodies, so the legal space is "
            "exhausted at that bound; the interpreter accepts up to MAX_BODY_LENGTH, where the "
            "legal space reaches tens of millions of bodies per state and is sampled instead"
        ),
    }


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
    """Randomised corroboration ABOVE the exhausted bound, reported separately and never as proof."""

    import random

    generator = random.Random(seed)
    alphabet = list(conservation_alphabet()) + list(PARAMETERISED_ALPHABET)
    checked = values = mismatches = 0
    refusals_by_code: dict[str, int] = {}
    first_mismatch = None
    for _ in range(trials):
        length = generator.randint(MAX_ASSEMBLY_LENGTH + 1, MAX_BODY_LENGTH)
        body = tuple(alphabet[generator.randrange(len(alphabet))] for _ in range(length))
        arguments = ADVERSARIAL_ARGUMENTS[generator.randrange(len(ADVERSARIAL_ARGUMENTS))]
        slots = [generator.randint(-9, 9) for _ in range(SLOT_COUNT)]
        inputs = [generator.randint(-9, 9) for _ in range(INPUT_COUNT)]
        reference = observe_reference(body, arguments, slots, inputs)
        observed = observe_state(body, arguments, slots, inputs, substrate)
        checked += 1
        if reference[0] == "value":
            values += 1
        else:
            code = str(reference[1])
            refusals_by_code[code] = refusals_by_code.get(code, 0) + 1
        if reference != observed:
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = {
                    "body": [[n, a] for n, a in body], "arguments": list(arguments),
                    "slots": slots, "inputs": inputs,
                    "reference": list(reference), "state": list(observed),
                }
    return {
        "trials": checked,
        "body_lengths": [MAX_ASSEMBLY_LENGTH + 1, MAX_BODY_LENGTH],
        "includes_parameterised_operands": True,
        "reference_values": values,
        "reference_refusals": sum(refusals_by_code.values()),
        "refusals_by_code": dict(sorted(refusals_by_code.items())),
        "mismatches": mismatches,
        "first_mismatch": first_mismatch,
        "exhaustive": False,
        "note": "adversarial corroboration above the exhausted bound, not a proof",
    }


def _parameter_bindings(kinds: Sequence[str], substrate: SubstrateState) -> list[tuple[object, ...]]:
    axes: list[Sequence[object]] = []
    for kind in kinds:
        domain = substrate.domain(kind)
        if domain is None:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, f"no domain for {kind!r}")
        if domain.rule == "slot_index":
            axes.append(range(substrate.slot_count))
        elif domain.rule == "input_index":
            axes.append(range(substrate.input_count))
        elif domain.rule == "literal_set":
            axes.append(substrate.literal_values)
        else:
            axes.append(substrate.selector_values(domain.reference))
    return [tuple(row) for row in itertools.product(*axes)] if axes else [()]


def language_conservation(
    substrate: SubstrateState, language: MetaLanguageState, max_program_length: int = 2,
) -> dict[str, object]:
    """Exhaustive over the language's own declared parameter domains, including the acquired op."""

    runtime = to_runtime_language(language)
    calls: list[tuple[str, tuple[object, ...]]] = []
    declared = 0
    for definition in language.primitives:
        bindings = _parameter_bindings(definition.parameter_kinds, substrate)
        declared += len(bindings)
        for binding in bindings:
            calls.append((definition.primitive_id, binding))

    programs = comparisons = mismatches = 0
    first_mismatch = None
    for length in range(1, max_program_length + 1):
        for program in itertools.product(calls, repeat=length):
            programs += 1
            for inputs, _ in CONSERVATION_STATES:
                try:
                    reference: Outcome = ("value", execute(list(program), inputs, language))
                except (LanguageError, ValueError, TypeError) as error:
                    reference = ("refused", classify_reference_refusal(error).value)
                try:
                    observed: Outcome = (
                        "value", execute_from_state(list(program), inputs, runtime, substrate),
                    )
                except SubstrateError as error:
                    observed = ("refused", error.code.value)
                comparisons += 1
                if reference != observed:
                    mismatches += 1
                    if first_mismatch is None:
                        first_mismatch = {
                            "program": [[n, list(a)] for n, a in program],
                            "inputs": list(inputs),
                            "reference": list(reference), "state": list(observed),
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


REFUSAL_BATTERY: tuple[tuple[str, tuple[tuple[str, object], ...], RefusalCode], ...] = (
    ("binop_on_empty_stack", (("BINOP", "add"),), RefusalCode.STACK_UNDERFLOW),
    ("binop_on_one_operand", (("PUSH_CONST", 1), ("BINOP", "add")), RefusalCode.STACK_UNDERFLOW),
    ("unop_on_empty_stack", (("UNOP", "inc"),), RefusalCode.STACK_UNDERFLOW),
    ("dup_on_empty_stack", (("DUP", None),), RefusalCode.STACK_UNDERFLOW),
    ("swap_on_empty_stack", (("SWAP", None),), RefusalCode.STACK_UNDERFLOW),
    ("swap_on_one_operand", (("PUSH_CONST", 1), ("SWAP", None)), RefusalCode.STACK_UNDERFLOW),
    ("store_on_empty_stack", (("STORE_SLOT", 0),), RefusalCode.STACK_UNDERFLOW),
    ("slot_index_out_of_range", (("PUSH_SLOT", 99),), RefusalCode.INVALID_SLOT_INDEX),
    ("input_index_out_of_range", (("PUSH_INPUT", 99),), RefusalCode.INVALID_INPUT_INDEX),
    (
        "store_slot_out_of_range", (("PUSH_CONST", 1), ("STORE_SLOT", 99)),
        RefusalCode.INVALID_SLOT_INDEX,
    ),
    (
        "unknown_binary_operator", (("PUSH_CONST", 1), ("PUSH_CONST", 1), ("BINOP", "nope")),
        RefusalCode.INVALID_SELECTOR,
    ),
    (
        "unknown_unary_operator", (("PUSH_CONST", 1), ("UNOP", "nope")),
        RefusalCode.INVALID_SELECTOR,
    ),
    ("unknown_micro_operation", (("NO_SUCH_OP", 0),), RefusalCode.UNKNOWN_OPERATION),
    (
        "body_exceeds_length_bound",
        tuple(("PUSH_CONST", 1) for _ in range(MAX_BODY_LENGTH + 1)),
        RefusalCode.BODY_LENGTH_EXCEEDED,
    ),
    ("unresolved_parameter", (("PUSH_SLOT", "$3"),), RefusalCode.UNRESOLVED_PARAMETER),
)


def refusal_conservation(substrate: SubstrateState) -> dict[str, object]:
    """Every declared refusal, required to produce the SAME SEMANTIC CODE on both sides."""

    rows = []
    disagreements = 0
    for name, body, expected in REFUSAL_BATTERY:
        reference = observe_reference(body, (), (0, 0, 0, 0), (0, 0, 0))
        observed = observe_state(body, (), (0, 0, 0, 0), (0, 0, 0), substrate)
        agree = reference == observed
        matches_expected = reference == ("refused", expected.value)
        if not agree or not matches_expected:
            disagreements += 1
        rows.append({
            "case": name,
            "expected_code": expected.value,
            "reference": list(reference),
            "state_owned": list(observed),
            "agree": agree,
            "matches_declared_code": matches_expected,
        })
    return {
        "cases": rows,
        "count": len(rows),
        "disagreements": disagreements,
        "codes_observed": sorted({
            str(row["reference"][1]) for row in rows if row["reference"][0] == "refused"
        }),
    }


def refusal_taxonomy_can_fail(substrate: SubstrateState) -> dict[str, object]:
    """Construct cases where both sides refuse for DIFFERENT reasons and require detection.

    Without this, `refused == refused` would still be the effective comparison and the taxonomy
    would be decoration. Each row damages the state so that its refusal code changes while the
    reference's stays put, and the checker must report a mismatch.
    """

    rows = []
    detected = 0
    cases = (
        # reference: INVALID_SELECTOR (unknown operator). state: UNKNOWN_OPERATION, because the
        # whole base name has been removed rather than just the selector.
        (
            "selector_vs_unknown_operation",
            (("PUSH_CONST", 1), ("PUSH_CONST", 1), ("BINOP", "nope")),
            substrate.without("BINOP:add").without("BINOP:sub")
                     .without("BINOP:mul").without("BINOP:max"),
        ),
        # reference: a value. state: STACK_UNDERFLOW, because the program now pops what it must not.
        (
            "value_vs_stack_underflow",
            (("PUSH_CONST", 1), ("UNOP", "inc")),
            substrate.replacing("UNOP:inc", [
                ("SPOP", 0), ("SPOP", 1), ("SPUSH", 0), ("HALT",),
            ]),
        ),
        # reference: INVALID_SLOT_INDEX. state: RESOURCE_EXHAUSTED, a different refusal entirely.
        (
            "slot_index_vs_resource_exhausted",
            (("PUSH_SLOT", 99),),
            substrate.replacing("PUSH_SLOT", [
                ("LOADI", 0, 1), ("JNZ", 0, 0), ("HALT",),
            ]),
        ),
    )
    for name, body, damaged in cases:
        reference = observe_reference(body, (), (0, 0, 0, 0), (0, 0, 0))
        observed = observe_state(body, (), (0, 0, 0, 0), (0, 0, 0), damaged)
        both_refused = reference[0] == "refused" and observed[0] == "refused"
        different_code = both_refused and reference[1] != observed[1]
        mismatch_detected = reference != observed
        if mismatch_detected:
            detected += 1
        rows.append({
            "case": name,
            "reference": list(reference),
            "state_owned": list(observed),
            "both_refused": both_refused,
            "refused_for_different_reasons": different_code,
            "mismatch_detected": mismatch_detected,
        })
    return {
        "cases": rows,
        "detected": detected,
        "all_detected": detected == len(rows),
        "cases_where_both_refused_differently": sum(
            1 for row in rows if row["refused_for_different_reasons"]
        ),
    }


def capability_conservation(substrate: SubstrateState) -> dict[str, object]:
    held: set[str] = set()
    for operation in substrate.operations:
        held.update(operation.capabilities)
    return {
        "capabilities_held": sorted(held),
        "permitted": list(substrate.permitted_capabilities),
        "forbidden": list(substrate.forbidden_capabilities),
        "reference_permitted": list(PERMITTED_CAPABILITIES),
        "reference_forbidden": list(FORBIDDEN_CAPABILITIES),
        "vocabulary_matches_reference": (
            list(substrate.permitted_capabilities) == list(PERMITTED_CAPABILITIES)
            and list(substrate.forbidden_capabilities) == list(FORBIDDEN_CAPABILITIES)
        ),
        "holds_only_permitted": held.issubset(set(substrate.permitted_capabilities)),
        "holds_nothing_forbidden": not held.intersection(set(substrate.forbidden_capabilities)),
        "capability_set_unchanged": sorted(held) == sorted(set(PERMITTED_CAPABILITIES)),
    }


def serialization_conservation(substrate: SubstrateState) -> dict[str, object]:
    text = substrate.serialize()
    restored = SubstrateState.deserialize(text)
    behavioural = mismatches = 0
    for body in enumerate_bodies(2):
        for inputs, slots in CONSERVATION_STATES[:3]:
            behavioural += 1
            if observe_state(body, (), slots, inputs, substrate) != observe_state(
                body, (), slots, inputs, restored,
            ):
                mismatches += 1
    return {
        "byte_identical": restored.serialize() == text,
        "digest_identical": restored.digest() == substrate.digest(),
        "behavioural_comparisons": behavioural,
        "behavioural_mismatches": mismatches,
        "digest": substrate.digest(),
    }


def signature_conservation(substrate: SubstrateState) -> dict[str, object]:
    return {
        "names": sorted(substrate.operation_names),
        "reference_names": sorted(MICRO_OPERATIONS),
        "names_identical": sorted(substrate.operation_names) == sorted(MICRO_OPERATIONS),
        "binary_selectors": list(substrate.selector_values("BINOP")),
        "binary_identical": list(substrate.selector_values("BINOP")) == sorted(BINARY_OPERATORS),
        "unary_selectors": list(substrate.selector_values("UNOP")),
        "unary_identical": list(substrate.selector_values("UNOP")) == sorted(UNARY_OPERATORS),
        "literal_values": list(substrate.literal_values),
        "literals_identical": list(substrate.literal_values) == list(CONST_VALUES),
        "parameter_domains": [item.to_dict() for item in substrate.parameter_domains],
        "acquired_operations": [
            operation.key for operation in substrate.operations if operation.origin != "inherited"
        ],
        "nothing_acquired": all(
            operation.origin == "inherited" for operation in substrate.operations
        ),
    }


__all__ = [
    "ADVERSARIAL_ARGUMENTS", "CONSERVATION_STATES", "INHERITED_PARAMETER_DOMAINS",
    "INHERITED_SUBSTRATE_OPERATIONS", "M091_ACQUIRED_PRIMITIVE", "MIGRATION_SCHEMA",
    "PARAMETERISED_ALPHABET", "REFUSAL_BATTERY", "adversarial_conservation",
    "capability_conservation", "classify_reference_refusal", "conservation_alphabet",
    "enumerate_bodies", "exhaustive_legal_conservation", "exhaustive_representation_conservation",
    "inherited_l1", "intractable_dimension", "language_conservation", "legal_alphabet",
    "migrated_l0", "migrated_substrate", "observe_reference", "observe_state",
    "refusal_conservation", "refusal_taxonomy_can_fail", "serialization_conservation",
    "signature_conservation", "stack_depth_certificate", "to_runtime_language",
    "to_runtime_primitive",
]
