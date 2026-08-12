"""The M086-B holdout generator, in a module phase 1 does not import.

M086-A kept its holdout as module-level constants in the same module and process as the meta-search,
and defended the boundary by checking that one function did not name them. That is an argument about
source text where the protocol promised an ordering, and it is why the attempt was disqualified.

Here the holdout does not exist until this module is invoked, by a separate process, after the
adopted mechanism has been written and committed. It records the digest of that mechanism, so the
ordering is provable from artifacts rather than from the absence of a reference.

This module imports the bank grammar and nothing else from M086-B. It never imports the lineage.
"""
from __future__ import annotations

import hashlib
import json
from typing import Sequence

from metamorphosis.m047_software_body import SoftwareCase
from metamorphosis.m086b_bank import (
    BankShape,
    _canonical,
    _digest,
    _expected,
    body_from_shape,
    draw_shape,
    public_cases_from_shape,
)

HIDDEN_CASES_PER_HOLDOUT = 4


def holdout_shape(salt: bytes) -> BankShape:
    """Drawn from the same grammar under a different tag, so it is a sibling and not a copy."""

    return draw_shape(salt, "holdout")


def holdout_public(salt: bytes) -> tuple[SoftwareCase, ...]:
    return public_cases_from_shape(holdout_shape(salt), "holdout")


def holdout_hidden(salt: bytes) -> tuple[SoftwareCase, ...]:
    """Evaluator-owned. Same operations, different operands, never shown to the mechanism."""

    shape = holdout_shape(salt)
    cases: list[SoftwareCase] = []
    for index in range(HIDDEN_CASES_PER_HOLDOUT):
        seed = _digest(salt, "holdout:hidden", index)
        use_unknown = index % 2 == 0
        canonical = shape.unknown_canonical if use_unknown else shape.routeless_operation
        token = shape.unknown_token if use_unknown else shape.routeless_operation
        arity = 3 if canonical == "mean" else 2
        operands = tuple(1 + seed[position] % 9 for position in range(arity))
        request = " ".join([token] + [str(value) for value in operands])
        cases.append(SoftwareCase(
            f"hidden_{index}", request, _expected(canonical, operands), "holdout_hidden",
        ))
    return tuple(cases)


def holdout_record(salt: bytes, adopted_mechanism_digest: str) -> dict[str, object]:
    """The artifact phase 3 reads, binding this holdout to the mechanism that preceded it."""

    payload = {
        "schema": "m086b-holdout-v1",
        "generated_after_adopted_mechanism_digest": adopted_mechanism_digest,
        "shape": holdout_shape(salt).to_dict(),
        "starting_body": body_from_shape(holdout_shape(salt)).digest(),
        "public": [case.to_dict() for case in holdout_public(salt)],
        "hidden": [case.to_dict() for case in holdout_hidden(salt)],
    }
    payload["holdout_digest"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload


def cases_from_record(record: Sequence[dict]) -> tuple[SoftwareCase, ...]:
    return tuple(SoftwareCase.from_dict(item) for item in record)
