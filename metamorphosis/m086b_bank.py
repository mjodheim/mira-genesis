"""The M086-B starting body and development limitation, generated from the frozen salt.

M086-A's bank was written by hand, which made it easy to shape and hard to defend. Here a declared
grammar draws the alias table, the route table, the tokens and the operands from the salt.

What the grammar guarantees is the **premise**: a limitation whose public evidence names two stages at
once, which M047's mechanism cannot express. That is not a thumb on the scale — it is the documented
behaviour of the mechanism under test, and without it there is nothing to study.

What the grammar guarantees about the **outcome** is nothing. It does not decide which meta-primitive
helps, whether any does, or whether the lineage repairs anything at all.

This module knows nothing about the holdout. The holdout generator lives in `m086b_holdout`, which
phase 1 does not import.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m047_software_body import (
    SoftwareBody,
    SoftwareCase,
    SourceModule,
    render_allocation,
    render_critique,
    render_execution,
    render_interpretation,
    render_orchestration,
    render_planning,
    render_selection,
    render_tool_core,
)

GENERATOR_VERSION = 1

# M047's interpretation renderer fixes these arities, so an alias may only point here.
CANONICALS = ("add", "max", "mean", "mul")

# The operation left without a route must be repairable by some expression M047's tool renderer can
# emit. `mul` has no product expression, and a tool named `max` shadows the builtin its own
# expression needs — the latent M047 defect recorded in FAILURE_LOG. Two candidates remain, and the
# salt chooses between them.
ROUTELESS_CANDIDATES = ("mean", "add")

# Tokens that are not canonical operation names, so they cannot already be in the alias table.
TOKEN_VOCABULARY = (
    "plus", "times", "avg", "tot", "sum2", "combine", "merge", "fold",
    "gather", "join", "pair", "blend",
)


class BankError(RuntimeError):
    """Raised when the grammar cannot produce a well-formed limitation."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _digest(salt: bytes, tag: str, index: int = 0) -> bytes:
    return hashlib.sha256(
        salt + b"m086b\0" + tag.encode("utf-8") + b"\0" + index.to_bytes(4, "big"),
    ).digest()


@dataclass(frozen=True)
class BankShape:
    """Everything the grammar drew, recorded so the bank can be replayed and audited."""

    routeless_operation: str
    routes: Mapping[str, str]
    aliases: Mapping[str, str]
    unknown_token: str
    unknown_canonical: str
    routeless_operands: tuple[int, ...]
    unknown_operands: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "routeless_operation": self.routeless_operation,
            "routes": dict(self.routes),
            "aliases": dict(self.aliases),
            "unknown_token": self.unknown_token,
            "unknown_canonical": self.unknown_canonical,
            "routeless_operands": list(self.routeless_operands),
            "unknown_operands": list(self.unknown_operands),
        }


def _arity(canonical: str) -> int:
    return 3 if canonical == "mean" else 2


def _expected(canonical: str, operands: Sequence[int]) -> int | float:
    if canonical == "add":
        return operands[0] + operands[1]
    if canonical == "mul":
        return operands[0] * operands[1]
    if canonical == "max":
        return max(operands)
    return sum(operands) / len(operands)


def draw_shape(salt: bytes, tag: str = "development") -> BankShape:
    """Draw one limitation from the salt. Deterministic, and the same grammar serves the holdout."""

    routeless = ROUTELESS_CANDIDATES[_digest(salt, tag + ":routeless")[0] % len(ROUTELESS_CANDIDATES)]

    # tool_core supplies add and mul, so only those may carry a route before any repair.
    routable = tuple(name for name in ("add", "mul") if name != routeless)
    if not routable:
        raise BankError("the grammar left no routable canonical operation")
    routes = {name: name for name in routable}

    # The unknown token's canonical must already have a route, so repairing the alias cannot reveal a
    # new fault. That cascade is what made M086-A's first hand-written bank meaningless.
    unknown_canonical = routable[_digest(salt, tag + ":canonical")[0] % len(routable)]
    token = TOKEN_VOCABULARY[_digest(salt, tag + ":token")[0] % len(TOKEN_VOCABULARY)]
    if token in CANONICALS:
        raise BankError("the drawn token collides with a canonical operation")

    def operands(kind: str, canonical: str) -> tuple[int, ...]:
        seed = _digest(salt, f"{tag}:{kind}")
        return tuple(1 + seed[index] % 9 for index in range(_arity(canonical)))

    return BankShape(
        routeless_operation=routeless,
        routes=routes,
        aliases={name: name for name in CANONICALS},
        unknown_token=token,
        unknown_canonical=unknown_canonical,
        routeless_operands=operands("routeless", routeless),
        unknown_operands=operands("unknown", unknown_canonical),
    )


def body_from_shape(shape: BankShape) -> SoftwareBody:
    modules = (
        SourceModule("allocation", render_allocation("fixed_four")),
        SourceModule("critique", render_critique("identity")),
        SourceModule("execution", render_execution()),
        SourceModule("interpretation", render_interpretation(dict(shape.aliases))),
        SourceModule("orchestration", render_orchestration()),
        SourceModule("planning", render_planning("root_only")),
        SourceModule("selection", render_selection(dict(shape.routes))),
        SourceModule("tool_core", render_tool_core()),
    )
    return SoftwareBody(tuple(sorted(modules, key=lambda item: item.name)))


def public_cases_from_shape(shape: BankShape, prefix: str) -> tuple[SoftwareCase, ...]:
    """Two cases: one that cannot be parsed, one that parses and cannot be routed."""

    unknown_request = " ".join(
        [shape.unknown_token] + [str(value) for value in shape.unknown_operands],
    )
    routeless_request = " ".join(
        [shape.routeless_operation] + [str(value) for value in shape.routeless_operands],
    )
    return (
        SoftwareCase(
            f"{prefix}_unknown_token", unknown_request,
            _expected(shape.unknown_canonical, shape.unknown_operands), prefix,
        ),
        SoftwareCase(
            f"{prefix}_missing_route", routeless_request,
            _expected(shape.routeless_operation, shape.routeless_operands), prefix,
        ),
    )


def starting_body(salt: bytes) -> SoftwareBody:
    return body_from_shape(draw_shape(salt, "development"))


def development_public(salt: bytes) -> tuple[SoftwareCase, ...]:
    return public_cases_from_shape(draw_shape(salt, "development"), "development")


def bank_digest(salt: bytes) -> str:
    shape = draw_shape(salt, "development")
    return hashlib.sha256(_canonical({
        "generator_version": GENERATOR_VERSION,
        "shape": shape.to_dict(),
        "starting_body": body_from_shape(shape).digest(),
        "development_public": [case.to_dict() for case in development_public(salt)],
    })).hexdigest()
