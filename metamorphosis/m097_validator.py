"""Independent candidate validator for M097's expression-operation definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m097_language import (
    ExpressionDefinition,
    evaluate_symbol,
    symbolic_expression,
)

VALIDATOR_SCHEMA = "m097-independent-validator-v1"


@dataclass(frozen=True)
class Validation:
    accepted: bool
    reason: str
    expression: tuple[object, ...] | None
    cases_passed: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": VALIDATOR_SCHEMA,
            "accepted": self.accepted,
            "reason": self.reason,
            "expression": list(self.expression) if self.expression else None,
            "cases_passed": self.cases_passed,
        }


def validate(
    definition: ExpressionDefinition,
    public_cases: Sequence[Mapping[str, int | float]],
) -> Validation:
    expression = symbolic_expression(definition.body)
    if expression is None:
        return Validation(False, "malformed_or_partial_stack_program", None, 0)
    rendered = repr(expression)
    if "('left',)" not in rendered or "('right',)" not in rendered:
        return Validation(False, "does_not_use_both_observed_roles", expression, 0)
    passed = 0
    for case in public_cases:
        try:
            actual = evaluate_symbol(expression, case["left"], case["right"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return Validation(False, "execution_failed", expression, passed)
        if actual != case["expected"]:
            return Validation(False, "public_behavior_disagreed", expression, passed)
        passed += 1
    if not public_cases:
        return Validation(False, "no_public_cases", expression, 0)
    return Validation(True, "accepted", expression, passed)


__all__ = ["VALIDATOR_SCHEMA", "Validation", "validate"]
