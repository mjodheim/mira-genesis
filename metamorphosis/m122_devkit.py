"""DEVELOPMENT-only candidate emitter for the M122 carrier contract.

Inherited from `m120_devkit` in shape and purpose, and narrowed to the flattened family: one
`actions` array rather than two, with guards optional.

It answers the same two questions before anything is spent: does the decoder carry every
schema-valid candidate into a carrier the frozen host accepts, and how many of those carriers clear
the frozen qualification clauses. **It is not the generator and its rate is not a prediction.**

`corner` draws the smallest machine the contract admits and is the mode the sizing derivation uses,
because that is the shape M119's blind generator actually produced when it was offered a range.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Iterator

from metamorphosis import carrier_host as host
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m122_carrier_contract as contract

DEVKIT_VERSION = "m122-development-candidate-emitter-v1"

MODE_UNIFORM = "uniform"
MODE_CORNER = "corner"
MODE_CEILING = "ceiling"
MODES = (MODE_UNIFORM, MODE_CORNER, MODE_CEILING)


def _seed(prefix: str, index: int) -> random.Random:
    material = "%s|%d" % (prefix, index)
    return random.Random(int(hashlib.sha256(material.encode("ascii")).hexdigest()[:16], 16))


def _identifier(rng: random.Random, prefix: str, index: int) -> str:
    return "%s%d%s" % (prefix, index, rng.choice(("", "x", "_v", "0")))[:12]


def _shape(rng: random.Random, mode: str) -> tuple[int, int, int]:
    """Cells, actions, errors."""
    if mode == MODE_CORNER:
        return contract.MIN_CELLS, contract.MIN_ACTIONS, contract.MIN_ERRORS
    if mode == MODE_CEILING:
        return contract.MAX_CELLS, contract.MAX_ACTIONS, contract.MAX_ERRORS
    return (rng.randint(contract.MIN_CELLS, contract.MAX_CELLS),
            rng.randint(contract.MIN_ACTIONS, contract.MAX_ACTIONS),
            rng.randint(contract.MIN_ERRORS, contract.MAX_ERRORS))


def _action(rng: random.Random, index: int) -> dict[str, Any]:
    return {
        "name": _identifier(rng, "op", index),
        "arg_size": rng.choice(contract.ARG_SIZES),
        "guard": [
            {"cell": rng.choice(contract.CELL_INDICES),
             "relation": rng.choice(host.GUARD_RELATIONS),
             "value": rng.choice(contract.CELL_VALUES)}
            for _ in range(rng.randint(contract.MIN_GUARD_CLAUSES, host.MAX_GUARD_CLAUSES))
        ],
        "effect": [
            {"cell": rng.choice(contract.CELL_INDICES),
             "mode": rng.choice(host.EFFECT_MODES),
             "operand": rng.choice(contract.CELL_VALUES)}
            for _ in range(rng.randint(1, host.MAX_EFFECT_ASSIGNMENTS))
        ],
        "error_index": rng.choice(contract.ERROR_INDICES),
    }


def development_candidate(seed_prefix: str, index: int, *,
                          mode: str = MODE_UNIFORM) -> dict[str, Any]:
    """One candidate, drawn from the contract's own bounds. Deterministic in its seed."""
    if mode not in MODES:
        raise ValueError("unknown development draw mode %r" % mode)
    rng = _seed(seed_prefix, index)
    n_cells, n_actions, n_errors = _shape(rng, mode)
    return {
        "surface": {
            "kind": rng.choice(host.SURFACE_KINDS),
            "ok_token": "ok%d" % rng.randrange(100),
            "error_token": "er%d" % rng.randrange(100),
            "field_separator": rng.choice(host.FIELD_SEPARATORS),
            "pair_separator": rng.choice(host.PAIR_SEPARATORS),
            "action_key": _identifier(rng, "ak", 0),
            "argument_key": _identifier(rng, "gk", 0),
            "status_key": _identifier(rng, "sk", 0),
        },
        "cells": [{"name": _identifier(rng, "cell", i),
                   "size": rng.choice(contract.CELL_SIZES),
                   "initial": rng.choice(contract.CELL_VALUES)}
                  for i in range(n_cells)],
        "hidden": ([rng.choice(contract.CELL_INDICES)] if rng.random() < 0.5 else []),
        "errors": [_identifier(rng, "err", i) for i in range(n_errors)],
        "actions": [_action(rng, i) for i in range(n_actions)],
    }


def development_candidates(seed_prefix: str, count: int, *,
                           mode: str = MODE_UNIFORM) -> Iterator[dict[str, Any]]:
    for index in range(count):
        yield development_candidate(seed_prefix, index, mode=mode)


def qualification_rate(seed_prefix: str, count: int, *,
                       mode: str = MODE_UNIFORM) -> dict[str, Any]:
    """Decode `count` candidates and report what the frozen host and evaluator make of them."""
    accepted = qualifying = demand_pairs = 0
    blocking: dict[str, int] = {}
    signatures: set[str] = set()
    refusals: dict[str, int] = {}
    for candidate in development_candidates(seed_prefix, count, mode=mode):
        try:
            carrier = host.validate_carrier(contract.decode_machine(candidate))
        except host.CarrierError as exc:
            refusals[str(exc)] = refusals.get(str(exc), 0) + 1
            continue
        accepted += 1
        report = evaluator.qualification_report(carrier)
        for clause in report["blocking_clauses"]:
            blocking[clause] = blocking.get(clause, 0) + 1
        if not report["qualifies"]:
            continue
        qualifying += 1
        signatures.add(host.structural_signature(carrier))
        demand_pairs += len(evaluator.derive_demand_pairs(carrier, "opaque-development", 4000))
    return {
        "schema": "m122-development-qualification-rate-v1",
        "devkit_version": DEVKIT_VERSION,
        "contract_version": contract.CONTRACT_VERSION,
        "decoder_version": contract.DECODER_VERSION,
        "mode": mode,
        "seed_prefix": seed_prefix,
        "sample": count,
        "host_accepted": accepted,
        "host_refusals": dict(sorted(refusals.items())),
        "every_decoded_candidate_was_accepted": accepted == count,
        "qualifying_carriers": qualifying,
        "qualification_rate": (qualifying / count) if count else 0.0,
        "distinct_qualifying_structures": len(signatures),
        "demand_pairs_over_qualifying_carriers": demand_pairs,
        "mean_demand_pairs_per_qualifying_carrier": (
            (demand_pairs / qualifying) if qualifying else 0.0),
        "blocking_clauses": dict(sorted(blocking.items())),
        "this_measures_a_development_emitter_not_the_blind_generator": True,
    }


__all__ = [
    "DEVKIT_VERSION",
    "MODES",
    "MODE_CEILING",
    "MODE_CORNER",
    "MODE_UNIFORM",
    "development_candidate",
    "development_candidates",
    "qualification_rate",
]
