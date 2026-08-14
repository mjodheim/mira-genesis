"""Deterministic candidate-side affine proof search for M092.

This module is intentionally independent from ``m092_certificate_verifier``.  It does not
import the verifier, qualification data, target fixtures, or any result artifact.  Its only
job is to search for exact bounded Farkas-style witnesses over the closed affine record
format used by M092 certificates.

A proof is a vector of integer multipliers plus a non-negative constant slack.  Equality
premises may be multiplied by signed integers.  Inequality premises may only receive
non-negative multipliers, and may not participate in equality goals.  This is the same
mathematical proof language consumed by the independent verifier, but the implementation
below is candidate-side and mechanically target-neutral.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from math import gcd
from typing import Mapping, Sequence

PROOF_SEARCH_SCHEMA = "m092-affine-proof-search-v1"
DEFAULT_MULTIPLIER_BOUND = 8
DEFAULT_SUPPORT_BOUND = 4
MAX_SEARCH_ATTEMPTS = 250_000


class ProofSearchError(ValueError):
    """A proof-search input is malformed or exceeds the candidate-side bounds."""


@dataclass(frozen=True)
class _Affine:
    terms: tuple[tuple[str, int], ...]
    constant: int

    @classmethod
    def make(cls, coefficients: Mapping[str, int], constant: int) -> "_Affine":
        return cls(
            tuple(sorted((str(name), int(value)) for name, value in coefficients.items() if value)),
            int(constant),
        )

    def add_scaled(self, other: "_Affine", multiplier: int) -> "_Affine":
        values = dict(self.terms)
        for name, coefficient in other.terms:
            values[name] = values.get(name, 0) + coefficient * multiplier
            if values[name] == 0:
                del values[name]
        return _Affine.make(values, self.constant + other.constant * multiplier)


@dataclass(frozen=True)
class _Constraint:
    relation: str
    expression: _Affine


def _integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProofSearchError(f"{label} must be an integer")
    return value


def _parse_constraint(value: Mapping[str, object], label: str) -> _Constraint:
    if set(value) != {"relation", "coefficients", "constant"}:
        raise ProofSearchError(f"{label} fields differ from the closed affine schema")
    relation = value["relation"]
    if relation not in ("eq", "ge"):
        raise ProofSearchError(f"{label}.relation is unsupported")
    coefficients = value["coefficients"]
    if not isinstance(coefficients, Mapping) or any(not isinstance(key, str) for key in coefficients):
        raise ProofSearchError(f"{label}.coefficients must be a string-keyed object")
    parsed: dict[str, int] = {}
    for name, raw in coefficients.items():
        coefficient = _integer(raw, f"{label}.coefficients.{name}")
        if coefficient == 0:
            raise ProofSearchError(f"{label} contains an explicit zero coefficient")
        parsed[name] = coefficient
    constant = _integer(value["constant"], f"{label}.constant")
    return _Constraint(str(relation), _Affine.make(parsed, constant))


def _candidate_values(relation: str, goal_relation: str, bound: int) -> tuple[int, ...]:
    if relation == "ge":
        if goal_relation == "eq":
            return (0,)
        return tuple(range(0, bound + 1))
    # Signed equality multipliers are enumerated by increasing absolute magnitude, with the
    # negative value first.  This is deterministic and independent of the target semantics.
    values = [0]
    for magnitude in range(1, bound + 1):
        values.extend((-magnitude, magnitude))
    return tuple(values)


def _slack_values(goal: _Constraint, bound: int) -> tuple[int, ...]:
    if goal.relation == "eq":
        return (0,)
    return tuple(range(0, bound + 1))


def _combine(
    premises: Sequence[_Constraint], multipliers: Sequence[int], slack: int,
) -> _Affine:
    result = _Affine.make({}, slack)
    for premise, multiplier in zip(premises, multipliers, strict=True):
        result = result.add_scaled(premise.expression, multiplier)
    return result


def _support_order(count: int, support_bound: int) -> tuple[tuple[int, ...], ...]:
    """Enumerate premise supports by size then lexicographically.

    Exact proofs in this closed fragment are normally sparse.  Searching sparse supports first is
    only a deterministic proof-search optimization: every returned witness is independently
    checkable and no verifier feedback changes this order.
    """

    maximum = min(count, support_bound)
    return tuple(
        support
        for size in range(maximum + 1)
        for support in combinations(range(count), size)
    )


def find_affine_proof(
    premises: Sequence[Mapping[str, object]],
    goal: Mapping[str, object],
    *,
    multiplier_bound: int = DEFAULT_MULTIPLIER_BOUND,
    support_bound: int = DEFAULT_SUPPORT_BOUND,
    attempt_cap: int = MAX_SEARCH_ATTEMPTS,
) -> dict[str, object] | None:
    """Return the first exact bounded witness, or ``None`` if this search space has none.

    The function never weakens a goal, changes a premise, or asks the verifier how a failed proof
    should be repaired.  Enumeration is fixed by premise order, support size, multiplier magnitude,
    and slack.  A returned witness therefore remains a candidate claim until the independent M092
    verifier accepts it.
    """

    if not 0 <= multiplier_bound <= 256:
        raise ProofSearchError("multiplier_bound must be between zero and 256")
    if not 0 <= support_bound <= len(premises):
        raise ProofSearchError("support_bound is outside the premise count")
    if attempt_cap <= 0:
        raise ProofSearchError("attempt_cap must be positive")

    parsed_premises = tuple(
        _parse_constraint(item, f"premise[{index}]") for index, item in enumerate(premises)
    )
    parsed_goal = _parse_constraint(goal, "goal")
    values = tuple(
        _candidate_values(item.relation, parsed_goal.relation, multiplier_bound)
        for item in parsed_premises
    )
    slacks = _slack_values(parsed_goal, multiplier_bound)

    attempts = 0
    seen: set[tuple[int, ...]] = set()
    for support in _support_order(len(parsed_premises), support_bound):
        support_set = set(support)
        active_ranges = [values[index][1:] for index in support]
        # Equality value order begins with zero and inequality order begins with zero.  A selected
        # support means every selected multiplier must be non-zero; zero-support is handled once.
        if any(not choices for choices in active_ranges):
            continue
        assignments = product(*active_ranges) if active_ranges else ((),)
        for active in assignments:
            multipliers = [0] * len(parsed_premises)
            for index, multiplier in zip(support, active, strict=True):
                multipliers[index] = multiplier
            key = tuple(multipliers)
            if key in seen:
                continue
            seen.add(key)
            for slack in slacks:
                attempts += 1
                if attempts > attempt_cap:
                    return None
                if _combine(parsed_premises, multipliers, slack) == parsed_goal.expression:
                    return {
                        "multipliers": multipliers,
                        "slack": slack,
                    }
    return None


def proof_search_receipt(
    premises: Sequence[Mapping[str, object]],
    goal: Mapping[str, object],
    **kwargs: int,
) -> dict[str, object]:
    """Produce a compact deterministic candidate-side receipt for audit tests."""

    proof = find_affine_proof(premises, goal, **kwargs)
    return {
        "schema": PROOF_SEARCH_SCHEMA,
        "premise_count": len(premises),
        "goal_relation": goal.get("relation"),
        "proof_found": proof is not None,
        "proof": proof,
    }
