"""What the inherited language can express, and the certificates that prove it cannot.

M089 attacked a **fan-in** gap: no L0 operation reads two values, so no slot can depend on two
input positions. That gap is spent, and M090's authored probe extension already occupies it.

M091 attacks a different and orthogonal axis. Every operation of the inherited language moves a
value with an *affine* map — `inc`, `dec`, `neg` and `double` are `x+1`, `x-1`, `-x` and `2x`, and
`SET_CONST` and `COPY_INPUT` install a constant or an input untouched. Affine maps compose to
affine maps, so:

    after any program over L0, every slot holds either a constant or `a*inputs[i] + b`.

The required transformation of M091 is **single-source** — it reads one input position and no more,
so M089's invariant is *not* violated and its primitive would not help — and it is **not affine**.
A clamp is the simplest example: `max(x, 0)` bends at zero, and no composition of `x+1`, `x-1`,
`-x` and `2x` bends anywhere.

Two things live here:

* the abstract domain `Shape`, which tracks *how many* input positions a value depends on and
  *whether* the dependence is affine, and the machine-checked lemma that every L0 primitive maps
  the domain into itself — which is what makes the insufficiency claim hold at any program length
  and therefore at any budget;
* the **refutation certificates**, which are finite, concrete and re-checkable: three points that
  no affine map passes through, and one pair of points per rival input position.

Nothing here knows what the answer is. It knows what the inherited language *is*.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from metamorphosis.m090_language import (
    CONST_VALUES,
    INPUT_COUNT,
    SLOT_COUNT,
    UNARY_OPERATORS,
    LanguageError,
    MetaLanguageState,
    PrimitiveDefinition,
    execute,
    run_body,
)


INVARIANT_NAME = "affine_single_source"
INVARIANT_STATEMENT = (
    "after any program over the inherited language, every slot holds either a constant or "
    "a*inputs[i] + b for a single input position i"
)


class ExpressivityError(RuntimeError):
    """Raised when an abstract evaluation cannot mirror the concrete one."""


# ---------------------------------------------------------------------------------------------
# the abstract domain
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Shape:
    """How a value depends on the inputs, abstracted to the two facts that matter.

    `sources` are the input positions the value may depend on. `affine` records whether that
    dependence is degree-at-most-one and unbent: a product of two varying values or a clamp
    against a varying value clears it. `constant` carries a statically known value so that
    constant folding does not lose precision — `max(0, 1)` is the constant `1`, not a bend.
    """

    sources: frozenset[int]
    affine: bool
    constant: int | None = None

    @property
    def affine_single_source(self) -> bool:
        return self.affine and len(self.sources) <= 1

    def describe(self) -> str:
        if self.constant is not None:
            return f"const({self.constant})"
        if not self.sources:
            return "const(?)"
        kind = "affine" if self.affine else "bent"
        return f"{kind}({','.join(str(item) for item in sorted(self.sources))})"


CONST_UNKNOWN = Shape(frozenset(), True, None)


def const_shape(value: int) -> Shape:
    return Shape(frozenset(), True, int(value))


def input_shape(index: int) -> Shape:
    return Shape(frozenset({int(index)}), True, None)


def _fold_unary(name: str, value: int) -> int:
    if name == "inc":
        return value + 1
    if name == "dec":
        return value - 1
    if name == "neg":
        return -value
    if name == "double":
        return value * 2
    raise ExpressivityError(f"unknown unary operator {name!r}")


def _fold_binary(operator: str, left: int, right: int) -> int:
    if operator == "add":
        return left + right
    if operator == "sub":
        return left - right
    if operator == "mul":
        return left * right
    if operator == "max":
        return max(left, right)
    raise ExpressivityError(f"unknown binary operator {operator!r}")


def unary_shape(name: str, value: Shape) -> Shape:
    """Every unary operator of the inherited language is affine, so none can bend a value."""

    if value.constant is not None:
        return const_shape(_fold_unary(name, value.constant))
    return Shape(value.sources, value.affine, None)


def binary_shape(operator: str, left: Shape, right: Shape) -> Shape:
    """Where bending can enter: a product of two varying values, or a clamp against one."""

    if left.constant is not None and right.constant is not None:
        return const_shape(_fold_binary(operator, left.constant, right.constant))
    sources = left.sources | right.sources
    if operator in {"add", "sub"}:
        # Sums of affine values are affine, however many sources they draw on.
        return Shape(sources, left.affine and right.affine, None)
    if operator == "mul":
        # Scaling by a known constant is affine; multiplying two varying values is not.
        if left.constant is not None:
            return Shape(right.sources, right.affine, None)
        if right.constant is not None:
            return Shape(left.sources, left.affine, None)
        return Shape(sources, False, None)
    if operator == "max":
        # A clamp bends wherever the branch changes, whether or not one side is constant.
        return Shape(sources, False, None)
    raise ExpressivityError(f"unknown binary operator {operator!r}")


def _resolve(argument: object, arguments: Sequence[object]) -> object:
    if isinstance(argument, str) and argument.startswith("$"):
        index = int(argument[1:])
        if index >= len(arguments):
            raise ExpressivityError(f"parameter {argument} is not supplied")
        return arguments[index]
    return argument


def abstract_run_body(
    body: Sequence[tuple[str, object]], arguments: Sequence[object], slots: Sequence[Shape],
) -> list[Shape]:
    """Abstract interpretation mirroring `m090_language.run_body` micro-operation for micro-operation.

    Any divergence between this and the concrete interpreter would make the insufficiency proof
    worthless, which is why `abstraction_soundness_report` re-checks the two against each other
    on concrete values rather than trusting the correspondence.
    """

    stack: list[Shape] = []
    updated = list(slots)
    for name, argument in body:
        if name == "PUSH_INPUT":
            updated_index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= updated_index < INPUT_COUNT:
                raise ExpressivityError("input index out of range")
            stack.append(input_shape(updated_index))
        elif name == "PUSH_SLOT":
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < SLOT_COUNT:
                raise ExpressivityError("slot index out of range")
            stack.append(updated[index])
        elif name == "PUSH_CONST":
            stack.append(const_shape(int(_resolve(argument, arguments))))  # type: ignore[arg-type]
        elif name == "BINOP":
            if len(stack) < 2:
                raise ExpressivityError("BINOP needs two operands")
            right, left = stack.pop(), stack.pop()
            stack.append(binary_shape(str(_resolve(argument, arguments)), left, right))
        elif name == "UNOP":
            if not stack:
                raise ExpressivityError("UNOP needs one operand")
            stack.append(unary_shape(str(_resolve(argument, arguments)), stack.pop()))
        elif name == "DUP":
            if not stack:
                raise ExpressivityError("DUP needs one operand")
            stack.append(stack[-1])
        elif name == "SWAP":
            if len(stack) < 2:
                raise ExpressivityError("SWAP needs two operands")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif name == "STORE_SLOT":
            if not stack:
                raise ExpressivityError("STORE_SLOT needs one operand")
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
            if not 0 <= index < SLOT_COUNT:
                raise ExpressivityError("slot index out of range")
            updated[index] = stack.pop()
        else:
            raise ExpressivityError(f"unknown micro-operation {name!r}")
    return updated


# ---------------------------------------------------------------------------------------------
# parameter bindings
# ---------------------------------------------------------------------------------------------


def parameter_bindings(kinds: Sequence[str]) -> tuple[tuple[object, ...], ...]:
    """Every legal call of a primitive with this signature, in a deterministic order."""

    options: list[list[object]] = []
    for kind in kinds:
        if kind == "slot":
            options.append(list(range(SLOT_COUNT)))
        elif kind == "input":
            options.append(list(range(INPUT_COUNT)))
        elif kind == "const":
            options.append(list(CONST_VALUES))
        elif kind == "unary_op":
            options.append(list(UNARY_OPERATORS))
        else:
            raise ExpressivityError(f"unknown parameter kind {kind!r}")
    bindings: list[tuple[object, ...]] = [()]
    for choices in options:
        bindings = [item + (choice,) for item in bindings for choice in choices]
    return tuple(bindings)


# ---------------------------------------------------------------------------------------------
# the closure lemma: every inherited primitive maps the domain into itself
# ---------------------------------------------------------------------------------------------

# The domain, as shape classes. A known constant and an unknown constant are kept apart so that
# constant folding is exercised, and every input position appears because an operator could in
# principle treat one differently from another.
DOMAIN_REPRESENTATIVES: tuple[Shape, ...] = (
    const_shape(0), CONST_UNKNOWN,
) + tuple(input_shape(index) for index in range(INPUT_COUNT))


def _domain_states() -> Iterable[tuple[Shape, ...]]:
    return itertools.product(DOMAIN_REPRESENTATIVES, repeat=SLOT_COUNT)


def closure_lemma(language: MetaLanguageState) -> dict[str, object]:
    """Check that every primitive of `language` maps affine-single-source states to such states.

    This is the whole insufficiency argument. It is a statement about **one step**, and induction
    carries it to programs of any length: the initial state is all zeros, which is in the domain,
    and no step can leave it. No budget defeats a closure property.
    """

    escapes: list[dict[str, object]] = []
    checked = 0
    for definition in sorted(language.primitives, key=lambda item: item.primitive_id):
        for arguments in parameter_bindings(definition.parameter_kinds):
            for state in _domain_states():
                checked += 1
                try:
                    after = abstract_run_body(definition.body, arguments, state)
                except ExpressivityError:
                    # A body that cannot run on a legal binding cannot leave the domain either.
                    continue
                for index, shape in enumerate(after):
                    if not shape.affine_single_source:
                        escapes.append({
                            "primitive_id": definition.primitive_id,
                            "arguments": [
                                item if isinstance(item, str) else int(item) for item in arguments
                            ],
                            "slot": index,
                            "shape": shape.describe(),
                        })
    return {
        "invariant": INVARIANT_NAME,
        "statement": INVARIANT_STATEMENT,
        "primitives": list(sorted(language.primitive_ids)),
        "abstract_states_checked": checked,
        "escapes": escapes[:10],
        "escape_count": len(escapes),
        "closed_under_every_primitive": not escapes,
    }


# ---------------------------------------------------------------------------------------------
# soundness: the abstraction must not be lying about the concrete interpreter
# ---------------------------------------------------------------------------------------------

# Points chosen so that a clamp against zero, a sign flip and a doubling are all distinguishable.
SOUNDNESS_INPUTS: tuple[tuple[int, ...], ...] = (
    (-4, 3, 7), (-1, 0, 2), (0, 5, -3), (2, -2, 1), (6, 1, 0), (9, -7, 4),
)

AFFINITY_PROBE_VALUES: tuple[int, ...] = (-5, -2, -1, 0, 1, 3, 8)


def _slot_function(
    program: Sequence[tuple[str, tuple[object, ...]]], language: MetaLanguageState, slot: int,
) -> Callable[[Sequence[int]], int | None]:
    def value(inputs: Sequence[int]) -> int | None:
        try:
            return execute(program, inputs, language)[slot]
        except LanguageError:
            return None

    return value


def behavioural_sources(
    target: Callable[[Sequence[int]], int | None], base_points: Sequence[Sequence[int]] = SOUNDNESS_INPUTS,
) -> list[int]:
    """Which input positions actually change this value. Measured, never read off a definition."""

    sources: set[int] = set()
    for base in base_points:
        reference = target(base)
        for index in range(INPUT_COUNT):
            for delta in (1, -1, 5):
                altered = list(base)
                altered[index] += delta
                if target(altered) != reference:
                    sources.add(index)
                    break
    return sorted(sources)


def _collinear(points: Sequence[tuple[int, int]]) -> bool:
    (x1, y1), (x2, y2), (x3, y3) = points
    return (y2 - y1) * (x3 - x1) == (y3 - y1) * (x2 - x1)


def affinity_witness(
    target: Callable[[Sequence[int]], int | None], source: int,
    base: Sequence[int] = SOUNDNESS_INPUTS[0],
) -> dict[str, object] | None:
    """Three points varying only `source` that no affine map passes through, if any exist.

    `a*x + b` sends collinear abscissae to collinear ordinates. Exhibiting three points off a line
    refutes **every** affine map at once — every integer `a`, every integer `b` — which is what
    makes the refutation independent of any budget or program length.
    """

    for triple in itertools.combinations(AFFINITY_PROBE_VALUES, 3):
        points: list[tuple[int, int]] = []
        for value in triple:
            inputs = list(base)
            inputs[source] = value
            observed = target(inputs)
            if observed is None:
                break
            points.append((value, observed))
        if len(points) != 3 or _collinear(points):
            continue
        return {
            "source": source,
            "held_fixed": [
                int(item) for index, item in enumerate(base) if index != source
            ],
            "points": [[int(x), int(y)] for x, y in points],
            "collinear": False,
        }
    return None


def abstraction_soundness_report(
    language: MetaLanguageState, programs: Sequence[Sequence[tuple[str, tuple[object, ...]]]],
) -> dict[str, object]:
    """Confirm concretely what the abstraction claims: these slots really are affine, really.

    The abstract lemma says every L0 program leaves every slot affine in one source. Here that
    prediction is tested against the concrete interpreter: a slot the abstraction calls affine
    must pass no non-collinear triple, and must vary with at most one input position.
    """

    violations: list[dict[str, object]] = []
    checked = 0
    for program in programs:
        for slot in range(SLOT_COUNT):
            target = _slot_function(program, language, slot)
            if target(SOUNDNESS_INPUTS[0]) is None:
                continue
            checked += 1
            sources = behavioural_sources(target)
            if len(sources) > 1:
                violations.append({
                    "program": [[name, list(args)] for name, args in program],
                    "slot": slot, "reason": "depends on more than one input", "sources": sources,
                })
                continue
            if sources and affinity_witness(target, sources[0]) is not None:
                violations.append({
                    "program": [[name, list(args)] for name, args in program],
                    "slot": slot, "reason": "not affine in its single source",
                })
    return {
        "slot_functions_checked": checked,
        "programs_checked": len(programs),
        "violations": violations[:10],
        "violation_count": len(violations),
        "abstraction_agrees_with_the_interpreter": not violations,
    }


# ---------------------------------------------------------------------------------------------
# refuting the whole affine single-source class for a required behaviour
# ---------------------------------------------------------------------------------------------


def refute_affine_single_source(
    required: Callable[[Sequence[int]], int], slot: int,
    base: Sequence[int] = SOUNDNESS_INPUTS[0],
) -> dict[str, object]:
    """A finite certificate that no affine single-source function computes `required`.

    Three parts, and all three are needed for the argument to be complete:

    * the requirement is not constant — two points with different values;
    * it is not affine in the position it does vary with — three non-collinear points;
    * it is not a function of any other position alone — for each rival `j`, two points that
      agree on `j` and disagree on the value.

    Together these eliminate every element of the class the inherited language is closed under,
    so no program over that language computes this, at any length.
    """

    def target(inputs: Sequence[int]) -> int | None:
        return required(inputs)

    sources = behavioural_sources(target)
    constant_refutation: dict[str, object] | None = None
    first = None
    for inputs in SOUNDNESS_INPUTS:
        value = required(inputs)
        if first is None:
            first = (list(inputs), value)
        elif value != first[1]:
            constant_refutation = {"points": [first, [list(inputs), value]]}
            break

    affine_refutation = (
        affinity_witness(target, sources[0], base) if len(sources) == 1 else None
    )

    rivals: dict[str, object] = {}
    for index in range(INPUT_COUNT):
        if len(sources) == 1 and index == sources[0]:
            continue
        witness = None
        for left, right in itertools.combinations(SOUNDNESS_INPUTS, 2):
            if left[index] != right[index]:
                continue
            if required(left) != required(right):
                witness = {
                    "agree_on_position": index,
                    "points": [[list(left), required(left)], [list(right), required(right)]],
                }
                break
        if witness is None:
            # Fall back to constructing the pair rather than searching for it.
            for probe in AFFINITY_PROBE_VALUES:
                left = list(base)
                right = list(base)
                other = next(item for item in range(INPUT_COUNT) if item != index)
                right[other] = right[other] + probe
                if required(left) != required(right):
                    witness = {
                        "agree_on_position": index,
                        "points": [[left, required(left)], [right, required(right)]],
                    }
                    break
        rivals[str(index)] = witness
    every_rival_refuted = all(value is not None for value in rivals.values())

    return {
        "slot": slot,
        "invariant": INVARIANT_NAME,
        "behavioural_sources": sources,
        "single_source": len(sources) == 1,
        "fan_in": len(sources),
        "not_constant": constant_refutation,
        "not_affine_in_its_source": affine_refutation,
        "not_a_function_of_any_rival_position": rivals,
        "every_rival_position_refuted": every_rival_refuted,
        "outside_affine_single_source": bool(
            constant_refutation is not None
            and affine_refutation is not None
            and every_rival_refuted
        ),
    }


def verify_refutation(
    certificate: Mapping[str, object], required: Callable[[Sequence[int]], int],
) -> list[str]:
    """Re-derive a refutation certificate from the requirement itself. Used by the checker."""

    problems: list[str] = []
    constant = certificate.get("not_constant")
    if not isinstance(constant, Mapping):
        problems.append("the certificate carries no refutation of the constant functions")
    else:
        points = list(constant["points"])  # type: ignore[index]
        values = [required(list(item[0])) for item in points]
        if values != [item[1] for item in points]:
            problems.append("the constant refutation does not reproduce from the requirement")
        if len(set(values)) < 2:
            problems.append("the constant refutation exhibits no differing values")

    affine = certificate.get("not_affine_in_its_source")
    if not isinstance(affine, Mapping):
        problems.append("the certificate carries no refutation of the affine functions")
    else:
        points = [(int(x), int(y)) for x, y in affine["points"]]  # type: ignore[index]
        source = int(affine["source"])  # type: ignore[index]
        base = list(SOUNDNESS_INPUTS[0])
        held = list(affine.get("held_fixed", []))  # type: ignore[union-attr]
        rebuilt = []
        for position in range(INPUT_COUNT):
            if position != source:
                rebuilt.append(base[position])
        if held and held != rebuilt:
            problems.append("the affine refutation does not hold the rival positions fixed")
        for x, y in points:
            inputs = list(base)
            inputs[source] = x
            if required(inputs) != y:
                problems.append("the affine refutation does not reproduce from the requirement")
                break
        if len(points) != 3 or _collinear(points):
            problems.append("the affine refutation points are collinear")

    rivals = certificate.get("not_a_function_of_any_rival_position")
    if not isinstance(rivals, Mapping):
        problems.append("the certificate carries no refutation of the rival positions")
    else:
        for key, witness in sorted(rivals.items()):
            if not isinstance(witness, Mapping):
                problems.append(f"input position {key} is not refuted")
                continue
            points = list(witness["points"])  # type: ignore[index]
            if len(points) != 2:
                problems.append(f"input position {key} has no two-point witness")
                continue
            left, right = points
            if left[0][int(key)] != right[0][int(key)]:
                problems.append(f"the witness for position {key} does not agree on that position")
            if required(list(left[0])) == required(list(right[0])):
                problems.append(f"the witness for position {key} does not disagree on the value")
    return problems


# ---------------------------------------------------------------------------------------------
# what a primitive does to the invariant
# ---------------------------------------------------------------------------------------------


def touched_slots(
    body: Sequence[tuple[str, object]], arguments: Sequence[object],
) -> tuple[int, ...]:
    """Slot positions a body reads or writes under this binding.

    Slots it never mentions keep whatever shape they arrived with, so enumerating them changes
    no answer and multiplies the work by five per slot. Restricting the product to the slots a
    body actually touches is exact rather than approximate.
    """

    touched: set[int] = set()
    for name, argument in body:
        if name not in {"PUSH_SLOT", "STORE_SLOT"}:
            continue
        try:
            index = int(_resolve(argument, arguments))  # type: ignore[arg-type]
        except (ExpressivityError, TypeError, ValueError):
            continue
        if 0 <= index < SLOT_COUNT:
            touched.add(index)
    return tuple(sorted(touched))


def _states_for(
    body: Sequence[tuple[str, object]], arguments: Sequence[object],
) -> Iterable[tuple[Shape, ...]]:
    positions = touched_slots(body, arguments)
    if not positions:
        return (tuple(const_shape(0) for _ in range(SLOT_COUNT)),)
    states: list[tuple[Shape, ...]] = []
    for combination in itertools.product(DOMAIN_REPRESENTATIVES, repeat=len(positions)):
        state = [const_shape(0)] * SLOT_COUNT
        for position, shape in zip(positions, combination, strict=True):
            state[position] = shape
        states.append(tuple(state))
    return states


def primitive_shape_report(definition: PrimitiveDefinition) -> dict[str, object]:
    """How this primitive treats the invariant: does it bend, and does it widen the source set?

    A primitive that bends **and** keeps every slot on one source is a targeted extension of the
    diagnosed limitation. One that widens the source set is doing something else as well, and the
    validator refuses it as overbroad — that is M089's primitive, and it is not this experiment's.
    """

    bends = False
    max_sources = 0
    bending_bindings: list[list[object]] = []
    for arguments in parameter_bindings(definition.parameter_kinds):
        for state in _states_for(definition.body, arguments):
            try:
                after = abstract_run_body(definition.body, arguments, state)
            except ExpressivityError:
                continue
            for shape in after:
                max_sources = max(max_sources, len(shape.sources))
                if not shape.affine:
                    if not bends:
                        bending_bindings.append([
                            item if isinstance(item, str) else int(item) for item in arguments
                        ])
                    bends = True
    return {
        "bends_the_affine_invariant": bends,
        "max_source_fan_in": max_sources,
        "preserves_single_source": max_sources <= 1,
        "example_bending_binding": bending_bindings[0] if bending_bindings else None,
        "targeted_extension": bool(bends and max_sources <= 1),
    }


def primitive_bend_witness(definition: PrimitiveDefinition) -> dict[str, object] | None:
    """A concrete triple showing the primitive's own transfer function is not affine.

    The abstract report may over-approximate — it calls every clamp bent even when the branch
    never changes. This does not: it runs the real interpreter and exhibits three points that no
    `a*x + b` passes through. A certificate nobody has to take on trust.
    """

    for arguments in parameter_bindings(definition.parameter_kinds):
        for slot in touched_slots(definition.body, arguments):
            for inputs in SOUNDNESS_INPUTS:
                def transfer(value: int) -> int | None:
                    slots = [0] * SLOT_COUNT
                    slots[slot] = value
                    try:
                        return run_body(definition.body, arguments, slots, inputs)[slot]
                    except LanguageError:
                        return None

                for triple in itertools.combinations(AFFINITY_PROBE_VALUES, 3):
                    points = []
                    for value in triple:
                        observed = transfer(value)
                        if observed is None:
                            break
                        points.append((value, observed))
                    if len(points) != 3 or _collinear(points):
                        continue
                    return {
                        "arguments": [
                            item if isinstance(item, str) else int(item) for item in arguments
                        ],
                        "slot": slot,
                        "inputs": list(inputs),
                        "points": [[int(x), int(y)] for x, y in points],
                        "collinear": False,
                    }
    return None


def verify_bend_witness(
    definition: PrimitiveDefinition, witness: Mapping[str, object],
) -> list[str]:
    """Re-run a bend witness against the primitive's body. Renaming the primitive changes nothing."""

    problems: list[str] = []
    arguments = tuple(witness["arguments"])  # type: ignore[index]
    slot = int(witness["slot"])  # type: ignore[arg-type]
    inputs = list(witness["inputs"])  # type: ignore[arg-type]
    points = [(int(x), int(y)) for x, y in witness["points"]]  # type: ignore[index]
    for value, expected in points:
        slots = [0] * SLOT_COUNT
        slots[slot] = value
        try:
            observed = run_body(definition.body, arguments, slots, inputs)[slot]
        except LanguageError:
            problems.append("the bend witness does not run against the primitive body")
            return problems
        if observed != expected:
            problems.append("the bend witness does not reproduce against the primitive body")
            return problems
    if _collinear(points):
        problems.append("the bend witness points are collinear and refute nothing")
    return problems


__all__ = [
    "AFFINITY_PROBE_VALUES", "CONST_UNKNOWN", "DOMAIN_REPRESENTATIVES", "ExpressivityError",
    "INVARIANT_NAME", "INVARIANT_STATEMENT", "SOUNDNESS_INPUTS", "Shape", "abstract_run_body",
    "abstraction_soundness_report", "affinity_witness", "behavioural_sources", "binary_shape",
    "closure_lemma", "const_shape", "input_shape", "parameter_bindings",
    "primitive_bend_witness", "primitive_shape_report", "refute_affine_single_source",
    "touched_slots", "unary_shape", "verify_bend_witness", "verify_refutation",
]
