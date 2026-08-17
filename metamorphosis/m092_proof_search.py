"""Deterministic candidate-side affine proof search for M092.

This module is intentionally independent from ``m092_certificate_verifier``. It does not
import the verifier, qualification data, target fixtures, or any result artifact. Its only
job is to search for exact bounded Farkas-style witnesses over the closed affine record
format used by M092 certificates.

A proof is a vector of integer multipliers plus a non-negative constant slack. Equality
premises may be multiplied by signed integers. Inequality premises may only receive
non-negative multipliers, and may not participate in equality goals. This is the same
mathematical proof language consumed by the independent verifier, but the implementation
below is candidate-side and mechanically target-neutral.

The search is sparse-support first, exactly as before, but it prunes a partial assignment
when the remaining bounded premises cannot possibly close one of the affine coordinates.
Slack is solved exactly at a leaf instead of being brute-forced. These are completeness-
preserving optimisations inside the declared multiplier/support bounds; they do not change
which witnesses are legal and they use no verifier feedback.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
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
    values = [0]
    for magnitude in range(1, bound + 1):
        values.extend((-magnitude, magnitude))
    return tuple(values)


def _support_order(count: int, support_bound: int) -> tuple[tuple[int, ...], ...]:
    maximum = min(count, support_bound)
    return tuple(
        support
        for size in range(maximum + 1)
        for support in combinations(range(count), size)
    )


def _coordinates(premises: Sequence[_Constraint], goal: _Constraint) -> tuple[str, ...]:
    names = {name for premise in premises for name, _ in premise.expression.terms}
    names.update(name for name, _ in goal.expression.terms)
    return tuple(sorted(names))


def _vector(expression: _Affine, coordinates: Sequence[str]) -> tuple[int, ...]:
    values = dict(expression.terms)
    return tuple(values.get(name, 0) for name in coordinates) + (expression.constant,)


def _add_scaled(vector: Sequence[int], other: Sequence[int], multiplier: int) -> tuple[int, ...]:
    return tuple(left + multiplier * right for left, right in zip(vector, other, strict=True))


def _within_remaining_reach(
    current: Sequence[int],
    target: Sequence[int],
    suffix_reach: Sequence[int],
    *,
    slack_bound: int,
) -> bool:
    # Every non-constant coordinate must be closable by the unassigned premises. For the constant
    # coordinate the verifier also permits a non-negative slack, so the conservative reachable
    # interval receives that additional positive allowance.
    last = len(current) - 1
    for index, (value, wanted, reach) in enumerate(zip(current, target, suffix_reach, strict=True)):
        residual = wanted - value
        if index == last:
            if residual < -reach or residual > reach + slack_bound:
                return False
        elif abs(residual) > reach:
            return False
    return True


def find_affine_proof(
    premises: Sequence[Mapping[str, object]],
    goal: Mapping[str, object],
    *,
    multiplier_bound: int = DEFAULT_MULTIPLIER_BOUND,
    support_bound: int = DEFAULT_SUPPORT_BOUND,
    attempt_cap: int = MAX_SEARCH_ATTEMPTS,
) -> dict[str, object] | None:
    """Return the first exact bounded witness, or ``None`` if this search space has none.

    Enumeration is deterministic and sparse-support first. A support is searched by depth-first
    multiplier order, with exact coordinate reachability pruning. The independent verifier remains
    the sole authority that decides whether a returned candidate proof is valid.
    """

    if not 0 <= multiplier_bound <= 256:
        raise ProofSearchError("multiplier_bound must be between zero and 256")
    if support_bound < 0:
        raise ProofSearchError("support_bound must be non-negative")
    if attempt_cap <= 0:
        raise ProofSearchError("attempt_cap must be positive")

    parsed_premises = tuple(
        _parse_constraint(item, f"premise[{index}]") for index, item in enumerate(premises)
    )
    parsed_goal = _parse_constraint(goal, "goal")
    coordinates = _coordinates(parsed_premises, parsed_goal)
    premise_vectors = tuple(_vector(item.expression, coordinates) for item in parsed_premises)
    target = _vector(parsed_goal.expression, coordinates)
    value_sets = tuple(
        _candidate_values(item.relation, parsed_goal.relation, multiplier_bound)
        for item in parsed_premises
    )
    slack_bound = 0 if parsed_goal.relation == "eq" else multiplier_bound
    zero = (0,) * len(target)
    attempts = 0

    for support in _support_order(len(parsed_premises), support_bound):
        active_values = tuple(value_sets[index][1:] for index in support)
        if any(not values for values in active_values):
            continue

        # suffix_reach[position][coordinate] is a conservative maximum absolute contribution from
        # every still-unassigned active premise. It makes pruning exact-safe without consulting the
        # verifier or any target observations.
        suffix_reach: list[tuple[int, ...]] = [zero for _ in range(len(support) + 1)]
        running = [0] * len(target)
        for position in range(len(support) - 1, -1, -1):
            premise_index = support[position]
            max_multiplier = max(abs(value) for value in active_values[position])
            vector = premise_vectors[premise_index]
            running = [
                reach + max_multiplier * abs(coefficient)
                for reach, coefficient in zip(running, vector, strict=True)
            ]
            suffix_reach[position] = tuple(running)

        chosen = [0] * len(parsed_premises)

        def search(position: int, current: tuple[int, ...]) -> dict[str, object] | None:
            nonlocal attempts
            if not _within_remaining_reach(
                current,
                target,
                suffix_reach[position],
                slack_bound=slack_bound,
            ):
                return None

            if position == len(support):
                attempts += 1
                if attempts > attempt_cap:
                    return None
                if current[:-1] != target[:-1]:
                    return None
                slack = target[-1] - current[-1]
                if not 0 <= slack <= slack_bound:
                    return None
                return {"multipliers": list(chosen), "slack": slack}

            premise_index = support[position]
            vector = premise_vectors[premise_index]
            for multiplier in active_values[position]:
                chosen[premise_index] = multiplier
                result = search(position + 1, _add_scaled(current, vector, multiplier))
                if result is not None:
                    return result
                if attempts > attempt_cap:
                    break
            chosen[premise_index] = 0
            return None

        result = search(0, zero)
        if result is not None:
            return result
        if attempts > attempt_cap:
            return None

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
