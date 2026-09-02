"""DEVELOPMENT-only candidate emitter for the M120 carrier contract.

This is an instrument-calibration tool and nothing else. It draws candidates uniformly from
`m120_carrier_contract.CANDIDATE_SCHEMA` so that two questions can be answered *before* the
qualifying generation is spent:

1. does the decoder in fact carry every schema-valid candidate into a carrier the frozen host
   accepts, over a large sample rather than over a handful of examples;
2. how many of the resulting carriers clear the frozen qualification clauses, so that a requested
   bank size can be derived rather than guessed.

**It is not the generator and its rate is not a prediction.** M113 recorded six per cent
qualification over project-authored worlds against twenty-five per cent from M112's blind bank, so
a devkit rate establishes only that a minimum is both meetable and missable. What makes the
estimate here more useful than M119's is the third mode below: `corner` draws only the *smallest*
machine the contract admits, which is what M119's blind generator actually did when it was offered
a range. Sizing against that corner is the conservative reading.

Nothing here is on the scientific path. It emits no request, reads no completion, and is bound by
the tested-system freeze only so that a change to it cannot silently change a recorded derivation.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Iterator

from metamorphosis import carrier_host as host
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m120_carrier_contract as contract

DEVKIT_VERSION = "m120-development-candidate-emitter-v1"

# Three shapes of draw. `corner` is the pessimistic one and the one the sizing derivation uses.
MODE_UNIFORM = "uniform"
MODE_CORNER = "corner"
MODE_CEILING = "ceiling"
MODES = (MODE_UNIFORM, MODE_CORNER, MODE_CEILING)


def _seed(prefix: str, index: int) -> random.Random:
    material = "%s|%d" % (prefix, index)
    return random.Random(int(hashlib.sha256(material.encode("ascii")).hexdigest()[:16], 16))


def _identifier(rng: random.Random, prefix: str, index: int) -> str:
    return "%s%d%s" % (prefix, index, rng.choice(("", "x", "_v", "0")))[:12]


def _shape(rng: random.Random, mode: str) -> tuple[int, int, int, int]:
    """Cells, conditional actions, plain actions, errors."""
    if mode == MODE_CORNER:
        return (contract.MIN_CELLS, contract.MIN_CONDITIONAL_ACTIONS,
                contract.MIN_PLAIN_ACTIONS, contract.MIN_ERRORS)
    if mode == MODE_CEILING:
        return (contract.MAX_CELLS, contract.MAX_CONDITIONAL_ACTIONS,
                contract.MAX_PLAIN_ACTIONS, contract.MAX_ERRORS)
    return (rng.randint(contract.MIN_CELLS, contract.MAX_CELLS),
            rng.randint(contract.MIN_CONDITIONAL_ACTIONS, contract.MAX_CONDITIONAL_ACTIONS),
            rng.randint(contract.MIN_PLAIN_ACTIONS, contract.MAX_PLAIN_ACTIONS),
            rng.randint(contract.MIN_ERRORS, contract.MAX_ERRORS))


def _action(rng: random.Random, index: int, *, minimum_guard_clauses: int) -> dict[str, Any]:
    return {
        "name": _identifier(rng, "op", index),
        "arg_size": rng.choice(contract.ARG_SIZES),
        "guard": [
            {"cell": rng.choice(contract.CELL_INDICES),
             "relation": rng.choice(host.GUARD_RELATIONS),
             "value": rng.choice(contract.CELL_VALUES)}
            for _ in range(rng.randint(minimum_guard_clauses, host.MAX_GUARD_CLAUSES))
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
    n_cells, n_conditional, n_plain, n_errors = _shape(rng, mode)
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
        "hidden": ([rng.choice(contract.CELL_INDICES)]
                   if rng.random() < 0.5 else []),
        "errors": [_identifier(rng, "err", i) for i in range(n_errors)],
        "conditional_actions": [_action(rng, i, minimum_guard_clauses=1)
                                for i in range(n_conditional)],
        "actions": [_action(rng, n_conditional + i, minimum_guard_clauses=0)
                    for i in range(n_plain)],
    }


def development_candidates(seed_prefix: str, count: int, *,
                           mode: str = MODE_UNIFORM) -> Iterator[dict[str, Any]]:
    for index in range(count):
        yield development_candidate(seed_prefix, index, mode=mode)


def qualification_rate(seed_prefix: str, count: int, *,
                       mode: str = MODE_UNIFORM) -> dict[str, Any]:
    """Decode `count` candidates and report what the frozen host and evaluator make of them.

    Counts only. DEVELOPMENT evidence about the contract, never about a hypothesis.
    """
    accepted = qualifying = 0
    demand_pairs = 0
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
        "schema": "m120-development-qualification-rate-v1",
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
