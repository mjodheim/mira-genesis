"""The M086-C starting body and development limitation, generated from the frozen salt.

M086-B drew a limitation whose routeless operation was `add`, and every candidate repairing it was
refused by the sandbox as a duplicate tool registration. Probing M047's frozen templates shows why
the fix is not simply a shorter list:

    add   already registered by tool_core          -> duplicate registration
    mul   already registered, and no expression computes a product
    max   the synthesized tool shadows the builtin its own expression needs
    mean  repairable

**`mean` is the only missing-route operation M047's templates can repair.** That is a property of the
inherited machinery, not a choice, and it is worth stating plainly: the frozen mechanism's
constructive surface is narrower than its five-branch dispatch suggests.

So the routeless operation cannot vary here. What the salt still draws, and what the outcome still
depends on, is:

  * which canonical the unknown token means, among those that already have a route;
  * the token itself;
  * the operands of both public cases;
  * the operands of the hidden cases.

The last two carry the real risk. A `mean a b c` case is passed by the `mean` expression always, and
by `midpoint` whenever `(a + c) / 2 == (a + b + c) / 3`. When both pass the public case the cycle
takes the first in the frozen expression order, which is `midpoint`, and the hidden cases then decide
whether that generalizes. Nothing here arranges for it to.
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

# Forced, not chosen: see the module docstring. `add` and `mul` are already registered by
# tool_core so a synthesized module collides, `mul` has no product expression, and a tool named
# `max` shadows the builtin its expression needs.
ROUTELESS_CANDIDATES = ("mean",)

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
