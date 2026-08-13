"""Worlds: what a transformation must achieve, stated as a requirement rather than a program.

A world is a small structured situation with its own vocabulary and its own notion of being right.
It is serialized as **data** in a closed schema, and the machinery that interprets that schema is
generic — it knows about requirements and invariants, not about signals, plans or links.

That genericity is the point. Only the **development** world lives in this module, because the
lineage has to encounter its limitation somewhere. Every qualifying world is drawn by a separate
process after the language is frozen, arrives as data in this same schema, and is interpreted by
this same code. Nothing under `metamorphosis/` contains a qualifying case, which is the defect
PR #136 found in M088's first draft and the one D053 recorded against M086-A.

A requirement is an expression over the inputs. The expression language is the **oracle's**, not
the lineage's: it can say `max` because it is stating what must be true, and the lineage cannot
call it, execute it, or read it as a program. The lineage sees required values on public instances
and must build something out of its own language that produces them.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from metamorphosis.m090_language import INPUT_COUNT, SLOT_COUNT


WORLD_SCHEMA = "m091-world-v1"

RULE_OPERATORS = (
    "input", "const", "neg", "inc", "dec", "double", "add", "sub", "mul", "max", "min",
)

INVARIANT_KINDS = (
    "never_below", "never_above", "matches_requirement", "tracks_input_when", "pinned_when",
)


class WorldError(RuntimeError):
    """Raised when a world specification is outside the closed schema."""


# ---------------------------------------------------------------------------------------------
# the requirement expression language
# ---------------------------------------------------------------------------------------------


def evaluate_rule(expression: Sequence[object], inputs: Sequence[int]) -> int:
    """Evaluate a requirement expression. Total, integer-valued and side-effect free."""

    if not isinstance(expression, (list, tuple)) or not expression:
        raise WorldError(f"malformed requirement expression {expression!r}")
    operator = str(expression[0])
    if operator not in RULE_OPERATORS:
        raise WorldError(f"unknown requirement operator {operator!r}")
    if operator == "input":
        index = int(expression[1])  # type: ignore[arg-type]
        if not 0 <= index < INPUT_COUNT:
            raise WorldError("requirement reads an input position that does not exist")
        return int(inputs[index])
    if operator == "const":
        return int(expression[1])  # type: ignore[arg-type]
    if operator in {"neg", "inc", "dec", "double"}:
        value = evaluate_rule(expression[1], inputs)  # type: ignore[arg-type]
        if operator == "neg":
            return -value
        if operator == "inc":
            return value + 1
        if operator == "dec":
            return value - 1
        return value * 2
    left = evaluate_rule(expression[1], inputs)  # type: ignore[arg-type]
    right = evaluate_rule(expression[2], inputs)  # type: ignore[arg-type]
    if operator == "add":
        return left + right
    if operator == "sub":
        return left - right
    if operator == "mul":
        return left * right
    if operator == "max":
        return max(left, right)
    return min(left, right)


def required_slots(world: Mapping[str, object], inputs: Sequence[int]) -> tuple[int, ...]:
    """The full slot vector a correct transformation must leave behind.

    Slots no requirement mentions must be untouched. A transformation that gets the answer right
    and scribbles on a slot it was not asked about is not correct here, which keeps the search
    from being rewarded for side effects.
    """

    slots = [0] * SLOT_COUNT
    for requirement in world["requirements"]:  # type: ignore[index]
        index = int(requirement["slot"])  # type: ignore[index]
        if not 0 <= index < SLOT_COUNT:
            raise WorldError("requirement writes a slot that does not exist")
        slots[index] = evaluate_rule(requirement["expression"], inputs)  # type: ignore[index]
    return tuple(slots)


# ---------------------------------------------------------------------------------------------
# world-level correctness
# ---------------------------------------------------------------------------------------------


def invariant_violations(
    world: Mapping[str, object], inputs: Sequence[int], slots: Sequence[int] | None,
) -> list[str]:
    """Check the world's own statement of being right, in the world's own terms.

    This is not `slots == required`. It is what the situation demands — a level that never goes
    negative, a region where the plan must track its input exactly, a region where it must be
    pinned. `matches_requirement` is available and is used, but it is one invariant among several
    rather than the whole notion of correctness.
    """

    if slots is None:
        return ["the transformation did not run"]
    violations: list[str] = []
    expected = required_slots(world, inputs)
    for invariant in world["invariants"]:  # type: ignore[index]
        kind = str(invariant["kind"])  # type: ignore[index]
        if kind not in INVARIANT_KINDS:
            raise WorldError(f"unknown world invariant {kind!r}")
        slot = int(invariant["slot"])  # type: ignore[index]
        observed = int(slots[slot])
        if kind == "never_below" and observed < int(invariant["bound"]):  # type: ignore[index]
            violations.append(f"slot {slot} fell below {invariant['bound']}")
        elif kind == "never_above" and observed > int(invariant["bound"]):  # type: ignore[index]
            violations.append(f"slot {slot} rose above {invariant['bound']}")
        elif kind == "matches_requirement" and observed != expected[slot]:
            violations.append(f"slot {slot} does not meet the requirement")
        elif kind == "tracks_input_when":
            source = int(invariant["input"])  # type: ignore[index]
            threshold = int(invariant["threshold"])  # type: ignore[index]
            scale = int(invariant["scale"])  # type: ignore[index]
            active = (
                inputs[source] >= threshold if str(invariant["when"]) == "at_or_above"  # type: ignore[index]
                else inputs[source] < threshold
            )
            if active and observed != scale * int(inputs[source]):
                violations.append(f"slot {slot} does not track input {source} where it must")
        elif kind == "pinned_when":
            source = int(invariant["input"])  # type: ignore[index]
            threshold = int(invariant["threshold"])  # type: ignore[index]
            value = int(invariant["value"])  # type: ignore[index]
            active = (
                inputs[source] < threshold if str(invariant["when"]) == "below"  # type: ignore[index]
                else inputs[source] >= threshold
            )
            if active and observed != value:
                violations.append(f"slot {slot} is not pinned to {value} where it must be")
    for index in range(SLOT_COUNT):
        if index not in {int(item["slot"]) for item in world["requirements"]}:  # type: ignore[index]
            if int(slots[index]) != 0:
                violations.append(f"slot {index} was written although nothing asked for it")
    return violations


def validate_world(world: Mapping[str, object]) -> None:
    """Refuse a world specification that is outside the closed schema."""

    expected = {
        "world_id", "family", "narrative", "input_names", "requirements", "invariants",
        "public_instances",
    }
    missing = expected - set(world)
    if missing:
        raise WorldError(f"world specification is missing {sorted(missing)}")
    if len(world["input_names"]) != INPUT_COUNT:  # type: ignore[arg-type]
        raise WorldError("a world must name every input position")
    if not world["requirements"]:  # type: ignore[index]
        raise WorldError("a world with no requirement asks for nothing")
    for instance in world["public_instances"]:  # type: ignore[index]
        if len(instance["inputs"]) != INPUT_COUNT:  # type: ignore[index]
            raise WorldError("an instance does not supply every input position")
    for invariant in world["invariants"]:  # type: ignore[index]
        if str(invariant["kind"]) not in INVARIANT_KINDS:  # type: ignore[index]
            raise WorldError(f"unknown world invariant {invariant['kind']!r}")


# ---------------------------------------------------------------------------------------------
# the development world, and only the development world
# ---------------------------------------------------------------------------------------------

DEVELOPMENT_WORLD: dict[str, object] = {
    "world_id": "dev_signal_conditioning",
    "family": "signal_conditioning",
    "narrative": (
        "A sensor channel reports a signed deviation from its calibrated baseline. The integrator "
        "downstream accumulates excursions above the baseline only: a reading below the baseline "
        "is an absence of excursion, not a negative one, and passing it through unconditioned "
        "makes the accumulated total smaller than the excursions that actually occurred. The "
        "conditioned channel must therefore reproduce the deviation wherever it is at or above "
        "the baseline and read as no excursion wherever it is below."
    ),
    "input_names": ["deviation", "gain", "tolerance"],
    "requirements": [
        {"slot": 0, "expression": ["max", ["input", 0], ["const", 0]]},
    ],
    "invariants": [
        {"kind": "never_below", "slot": 0, "bound": 0},
        {"kind": "matches_requirement", "slot": 0},
        {
            "kind": "tracks_input_when", "slot": 0, "input": 0,
            "when": "at_or_above", "threshold": 0, "scale": 1,
        },
        {"kind": "pinned_when", "slot": 0, "input": 0, "when": "below", "threshold": 0, "value": 0},
    ],
    # Five public instances: two below the baseline, the baseline itself, two above. Both sides of
    # the bend are pinned, so a transformation cannot pass by being constant or by being linear.
    # The two unused readings vary independently, so one that quietly consults them is caught.
    "public_instances": [
        {"payload": {"deviation": -4, "gain": 3, "tolerance": 7}, "inputs": [-4, 3, 7]},
        {"payload": {"deviation": -1, "gain": 0, "tolerance": 2}, "inputs": [-1, 0, 2]},
        {"payload": {"deviation": 0, "gain": 5, "tolerance": -3}, "inputs": [0, 5, -3]},
        {"payload": {"deviation": 3, "gain": -2, "tolerance": 4}, "inputs": [3, -2, 4]},
        {"payload": {"deviation": 6, "gain": 1, "tolerance": 0}, "inputs": [6, 1, 0]},
    ],
}


def development_world() -> dict[str, object]:
    validate_world(DEVELOPMENT_WORLD)
    return DEVELOPMENT_WORLD


__all__ = [
    "DEVELOPMENT_WORLD", "INVARIANT_KINDS", "RULE_OPERATORS", "WORLD_SCHEMA", "WorldError",
    "development_world", "evaluate_rule", "invariant_violations", "required_slots",
    "validate_world",
]
