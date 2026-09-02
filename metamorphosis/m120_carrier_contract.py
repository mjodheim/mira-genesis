"""The M120 carrier contract: one representation, and a decoder that cannot produce a refused carrier.

M119 spent its qualifying generation and produced nothing to test. The bank arrived clean --
HTTP 200, one attempt, exact route, `finish_reason: stop`, valid JSON, conforming to the frozen
output schema -- and the frozen host then refused 34 of 37 machines. The model had followed the
schema exactly. The schema permitted values the host must reject, because two of the host's rules
are relations *between* fields and JSON Schema as M115 wrote it states them only in prose:

    arg_size must be 2..4 when arity is 1 and 0 when it is 0   -- flattened to minimum 0, maximum 4
    at least one entry of `visible` must be true               -- not expressed at all

25 machines died on the first, 8 on the second. This module exists so that class of failure cannot
happen again, and it closes it by construction rather than by asking more carefully.

## Two layers, and why there are two

**`CANDIDATE_SCHEMA`** is what the generator is handed. Every constraint in it is a bound on one
field against a constant -- `enum`, `minItems`, `maxItems`, `pattern`, `required`,
`additionalProperties: false`. It contains no relation between two fields, because a relation
between two fields is exactly what JSON Schema cannot enforce and what M119 died of. Where M115's
representation forced such a relation, the representation is changed here rather than described
more insistently:

    M115                                    M120
    ------------------------------------    ----------------------------------------------------
    `arity` 0..1 and `arg_size` 0..4        one field `arg_size` over {0, 2, 3, 4}; arity is
                                            derived, so the illegal combination cannot be written
    `initial`, a list as long as `cells`    `initial` lives inside its own cell, so the lengths
                                            cannot disagree
    `visible`, booleans, >= 1 true          `hidden`, at most one cell index, over >= 3 cells, so
                                            at least two cells are always observable
    `error`, a name that must appear in     `error_index`, an integer reduced against the declared
    `errors`                                error list
    `actions`, 2..6, guards optional        `conditional_actions` 2..3 with a guard each, plus
                                            `actions` 2..3 whose guard may be empty

It also uses **only the eleven schema feature classes M118's committed readiness gate observed this
route actually enforcing**. `oneOf`, `contains`, `minContains` and `uniqueItems` would each express
something here more directly, and not one of them has evidence on this route, so none is used.

**`decode_machine`** is the total function from a candidate to a carrier. It is not a repair and it
does not select: it is applied to every candidate identically, before anything is counted, and it
has no way to reject one. Every remaining host rule is a bound of one field against a *declared*
domain -- a cell index against the cell count, a guard value against that cell's size -- and the
decoder discharges each by modular reduction against the value the candidate itself declared. The
only conditional in it promotes an `arg_size` of 0 to 2 when the action's own effect asks for an
argument, which honours what the candidate wrote rather than discarding it.

The claim the two layers make together is mechanical and is checked, not asserted:

    for every value V satisfying CANDIDATE_SCHEMA, carrier_host.validate_carrier(decode_machine(V))
    returns, and never raises

`tests/test_m120_carrier_contract.py` establishes it by exhausting the constraint-relevant corners
of the candidate space and by fuzzing the rest, and `acceptance_census` enumerates every refusal
the host can raise so that a new one cannot appear without a fixture for it.

## What the decoder deliberately does not do

It cannot make a carrier *qualify*. Whether a carrier admits the experiment at all is decided by
`m113_evaluator.qualification_report` over reachability, observation depth and attribution, and
nothing here touches those. The decoder closes the gap between "the schema allowed it" and "the
host accepts it", which is a structural gap. It leaves the scientific gap where it belongs, in the
adequacy gate that runs before the seal.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from metamorphosis import carrier_host as host

CONTRACT_VERSION = "m120-carrier-contract-v1"
DECODER_VERSION = "m120-candidate-decoder-v1"

# ---------------------------------------------------------------------------------------------
# The family, fixed here before any H65 observation exists
# ---------------------------------------------------------------------------------------------
#
# M119's blind bank did not merely violate the host: it collapsed to the minimum of every range
# the schema offered. 22 of 37 machines had one cell, 35 of 37 had exactly two actions, and 28 of
# 37 had no reachable observation deeper than one step. Decoding that bank into host-valid form --
# measured, not guessed -- leaves exactly one machine of the 37 qualifying. A contract that permits
# the degenerate corner will be answered with the degenerate corner, so the corner is moved rather
# than the request repeated.
#
# These bounds are a narrowing of the carrier family, declared prospectively and disclosed as an
# instrument-design dependency on the closed M119 record. They are not a filter, a selection or a
# post-hoc adjustment: they are the contract the generator is given, before it generates.
MIN_CELLS = 3
MAX_CELLS = 4
MAX_HIDDEN_CELLS = 1          # >= 3 cells and <= 1 hidden means >= 2 are always observable
MIN_CONDITIONAL_ACTIONS = 2
MAX_CONDITIONAL_ACTIONS = 3
MIN_PLAIN_ACTIONS = 2
MAX_PLAIN_ACTIONS = 3
MIN_ERRORS = 1
MAX_ERRORS = 4

# Derived, and asserted against the host's own constants below.
MIN_ACTIONS = MIN_CONDITIONAL_ACTIONS + MIN_PLAIN_ACTIONS
MAX_ACTIONS = MAX_CONDITIONAL_ACTIONS + MAX_PLAIN_ACTIONS

CELL_SIZES = (2, 3, 4)
ARG_SIZES = (0, 2, 3, 4)      # 0 means nullary; every other value is a legal unary domain
CELL_INDICES = tuple(range(MAX_CELLS))
CELL_VALUES = tuple(range(max(CELL_SIZES)))
ERROR_INDICES = tuple(range(MAX_ERRORS))

IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]{1,11}$"
TOKEN_PATTERN = r"^[a-z][a-z0-9]{1,7}$"

_IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN)
_TOKEN_RE = re.compile(TOKEN_PATTERN)

# The eleven feature classes `experiments/M118/READINESS_RESULT.json` recorded this route enforcing,
# with none unenforced. The schema below is built from these and nothing else, so M118's readiness
# evidence still covers every keyword it uses. A successor that wants `oneOf` or `contains` must
# measure them on the route first.
PROVEN_FEATURE_CLASSES = (
    "additionalProperties_false",
    "array_of_object_levels",
    "enum",
    "items",
    "maxItems",
    "max_nesting_depth",
    "maximum",
    "minItems",
    "minimum",
    "pattern",
    "required",
)
READINESS_EVIDENCE_PATH = "experiments/M118/READINESS_RESULT.json"


class ContractError(RuntimeError):
    """The contract is not internally consistent. Every path fails closed."""


def _assert_within_the_host_meta_schema() -> None:
    """The family may narrow the host's meta-schema. It may never exceed it."""
    problems = []
    if not host.MIN_CELLS <= MIN_CELLS <= MAX_CELLS <= host.MAX_CELLS:
        problems.append("cell count")
    if not host.MIN_ACTIONS <= MIN_ACTIONS <= MAX_ACTIONS <= host.MAX_ACTIONS:
        problems.append("action count")
    if not host.MIN_ERRORS <= MIN_ERRORS <= MAX_ERRORS <= host.MAX_ERRORS:
        problems.append("error count")
    if set(CELL_SIZES) - set(range(host.MIN_CELL_DOMAIN, host.MAX_CELL_DOMAIN + 1)):
        problems.append("cell domain")
    if set(ARG_SIZES) - {0} - set(range(host.MIN_ARG_DOMAIN, host.MAX_ARG_DOMAIN + 1)):
        problems.append("argument domain")
    if MIN_CELLS - MAX_HIDDEN_CELLS < 1:
        problems.append("observability")
    if max(CELL_VALUES) + 1 < max(CELL_SIZES):
        problems.append("cell value range")
    if IDENTIFIER_PATTERN != host.IDENTIFIER_RE.pattern.replace("\\A", "^").replace("\\Z", "$"):
        problems.append("identifier pattern")
    if TOKEN_PATTERN != host.TOKEN_RE.pattern.replace("\\A", "^").replace("\\Z", "$"):
        problems.append("token pattern")
    if problems:
        raise ContractError(
            "the M120 carrier family is not inside the frozen host meta-schema: %s"
            % ", ".join(problems))


_assert_within_the_host_meta_schema()


# ---------------------------------------------------------------------------------------------
# The candidate schema. Constant bounds only; no relation between two fields.
# ---------------------------------------------------------------------------------------------

def _identifier() -> dict[str, Any]:
    return {"type": "string", "pattern": IDENTIFIER_PATTERN}


def _token() -> dict[str, Any]:
    return {"type": "string", "pattern": TOKEN_PATTERN}


def _guard_clause() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["cell", "relation", "value"],
        "properties": {
            "cell": {"type": "integer", "enum": list(CELL_INDICES)},
            "relation": {"type": "string", "enum": list(host.GUARD_RELATIONS)},
            "value": {"type": "integer", "enum": list(CELL_VALUES)},
        },
    }


def _effect_assignment() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["cell", "mode", "operand"],
        "properties": {
            "cell": {"type": "integer", "enum": list(CELL_INDICES)},
            "mode": {"type": "string", "enum": list(host.EFFECT_MODES)},
            "operand": {"type": "integer", "enum": list(CELL_VALUES)},
        },
    }


def _action(*, minimum_guard_clauses: int) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["name", "arg_size", "guard", "effect", "error_index"],
        "properties": {
            "name": _identifier(),
            # One field where M115 had two. `arity` is derived from it, so the combination the
            # host refuses -- a unary action with an argument domain of 0 or 1 -- cannot be
            # written down at all.
            "arg_size": {"type": "integer", "enum": list(ARG_SIZES)},
            "guard": {"type": "array", "minItems": minimum_guard_clauses,
                      "maxItems": host.MAX_GUARD_CLAUSES, "items": _guard_clause()},
            "effect": {"type": "array", "minItems": 1,
                       "maxItems": host.MAX_EFFECT_ASSIGNMENTS, "items": _effect_assignment()},
            # An index rather than a name, so an action cannot name an error the machine does not
            # declare. The decoder reduces it against the declared list.
            "error_index": {"type": "integer", "enum": list(ERROR_INDICES)},
        },
    }


def _machine() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["surface", "cells", "hidden", "errors", "conditional_actions", "actions"],
        "properties": {
            "surface": {
                "type": "object", "additionalProperties": False,
                "required": ["kind", "ok_token", "error_token", "field_separator",
                             "pair_separator", "action_key", "argument_key", "status_key"],
                "properties": {
                    "kind": {"type": "string", "enum": list(host.SURFACE_KINDS)},
                    "ok_token": _token(),
                    "error_token": _token(),
                    "field_separator": {"type": "string", "enum": list(host.FIELD_SEPARATORS)},
                    "pair_separator": {"type": "string", "enum": list(host.PAIR_SEPARATORS)},
                    "action_key": _identifier(),
                    "argument_key": _identifier(),
                    "status_key": _identifier(),
                },
            },
            # `initial` lives inside the cell it belongs to. In M115 it was a parallel array whose
            # length had to match `cells` and whose entries had to respect each cell's own size --
            # two relations between fields, neither expressible, both left to prose.
            "cells": {
                "type": "array", "minItems": MIN_CELLS, "maxItems": MAX_CELLS,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["name", "size", "initial"],
                    "properties": {
                        "name": _identifier(),
                        "size": {"type": "integer", "enum": list(CELL_SIZES)},
                        "initial": {"type": "integer", "enum": list(CELL_VALUES)},
                    },
                },
            },
            # Latency stated as the exception rather than the rule. At most one cell may be
            # hidden and there are at least three, so a machine that observes none of its own
            # state -- 8 of M119's 34 refusals -- is not a value this contract can express.
            "hidden": {"type": "array", "minItems": 0, "maxItems": MAX_HIDDEN_CELLS,
                       "items": {"type": "integer", "enum": list(CELL_INDICES)}},
            "errors": {"type": "array", "minItems": MIN_ERRORS, "maxItems": MAX_ERRORS,
                       "items": _identifier()},
            # Split so that "at least two actions carry a precondition" is a `minItems` on an
            # array rather than a `contains` this route has no evidence of enforcing.
            "conditional_actions": {
                "type": "array",
                "minItems": MIN_CONDITIONAL_ACTIONS, "maxItems": MAX_CONDITIONAL_ACTIONS,
                "items": _action(minimum_guard_clauses=1)},
            "actions": {
                "type": "array",
                "minItems": MIN_PLAIN_ACTIONS, "maxItems": MAX_PLAIN_ACTIONS,
                "items": _action(minimum_guard_clauses=0)},
        },
    }


def candidate_schema() -> dict[str, Any]:
    """The structured-output contract handed to the generator. Built, so it cannot drift."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "additionalProperties": False,
        "required": ["machines"],
        "properties": {"machines": {"type": "array", "minItems": 1, "items": _machine()}},
    }


CANDIDATE_SCHEMA = candidate_schema()


# ---------------------------------------------------------------------------------------------
# The decoder. Total, deterministic, content-independent, and unable to select.
# ---------------------------------------------------------------------------------------------

def _as_int(value: Any, default: int = 0) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else default


def _as_identifier(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and _IDENTIFIER_RE.match(value) else fallback


def _as_token(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and _TOKEN_RE.match(value) else fallback


def _as_choice(value: Any, allowed: Sequence[Any]) -> Any:
    return value if value in allowed else allowed[0]


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _distinct(names: Sequence[str], *, reserved: Sequence[str] = (),
              prefix: str = "n") -> list[str]:
    """Make identifiers distinct from each other and from `reserved`, deterministically.

    A collision is resolved by position, so the result depends on the candidate and on nothing
    else. It cannot consult a later field, a random source or how any other machine came out.
    """
    taken = set(reserved)
    out: list[str] = []
    for index, name in enumerate(names):
        chosen = name
        if chosen in taken or not _IDENTIFIER_RE.match(chosen):
            chosen = ""
            for suffix in range(1, 1000):
                trimmed = name[: max(1, 11 - len(str(suffix)))]
                proposal = "%s%d" % (trimmed, suffix)
                if _IDENTIFIER_RE.match(proposal) and proposal not in taken:
                    chosen = proposal
                    break
        if not chosen or not _IDENTIFIER_RE.match(chosen) or chosen in taken:
            chosen = "%s%d" % (prefix, index)
        taken.add(chosen)
        out.append(chosen)
    return out


def _decode_action(raw: Any, index: int, *, cells: Sequence[Mapping[str, Any]],
                   errors: Sequence[str], default_guard: Sequence[Any]) -> dict[str, Any]:
    raw = raw if isinstance(raw, Mapping) else {}
    n_cells = len(cells)

    effect_raw = _as_list(raw.get("effect"))[: host.MAX_EFFECT_ASSIGNMENTS]
    if not effect_raw:
        effect_raw = [{"cell": 0, "mode": "add", "operand": 1}]

    # Arity is derived from the one field that carries it. The single conditional in this decoder
    # is here: an action whose own effect asks for an argument is given the smallest legal
    # argument domain rather than having that effect silently rewritten. It honours what the
    # candidate wrote; it does not choose between candidates.
    arg_size = _as_choice(_as_int(raw.get("arg_size")), ARG_SIZES)
    wants_argument = any(isinstance(item, Mapping) and item.get("mode") == "arg"
                         for item in effect_raw)
    if wants_argument and arg_size == 0:
        arg_size = host.MIN_ARG_DOMAIN
    arity = 1 if arg_size else 0

    guard_raw = _as_list(raw.get("guard"))[: host.MAX_GUARD_CLAUSES] or list(default_guard)
    guard = []
    for clause in guard_raw:
        clause = clause if isinstance(clause, Mapping) else {}
        cell = _as_int(clause.get("cell")) % n_cells
        guard.append({
            "cell": cell,
            "relation": _as_choice(clause.get("relation"), host.GUARD_RELATIONS),
            "value": _as_int(clause.get("value")) % int(cells[cell]["size"]),
        })

    effect = []
    for item in effect_raw:
        item = item if isinstance(item, Mapping) else {}
        cell = _as_int(item.get("cell")) % n_cells
        mode = _as_choice(item.get("mode"), host.EFFECT_MODES)
        if mode == "copy":
            operand = _as_int(item.get("operand")) % n_cells
        elif mode == "arg":
            operand = 0
        else:
            operand = _as_int(item.get("operand")) % int(cells[cell]["size"])
        effect.append({"cell": cell, "mode": mode, "operand": operand})

    return {
        "name": _as_identifier(raw.get("name"), "a%d" % index),
        "arity": arity,
        "arg_size": arg_size,
        "guard": guard,
        "effect": effect,
        "error": errors[_as_int(raw.get("error_index")) % len(errors)],
    }


def decode_machine(candidate: Any) -> dict[str, Any]:
    """One candidate to one carrier the frozen host accepts. Total on every input.

    Applied identically to every machine in the completion, before anything is counted. It cannot
    refuse, cannot reorder, cannot drop and cannot consult another machine.
    """
    raw = candidate if isinstance(candidate, Mapping) else {}

    surface_raw = raw.get("surface") if isinstance(raw.get("surface"), Mapping) else {}
    ok_token = _as_token(surface_raw.get("ok_token"), "ok")
    error_token = _as_token(surface_raw.get("error_token"), "err")
    if error_token == ok_token:
        error_token = "err" if ok_token != "err" else "erred"
    keys = _distinct([_as_identifier(surface_raw.get("action_key"), "act"),
                      _as_identifier(surface_raw.get("argument_key"), "arg"),
                      _as_identifier(surface_raw.get("status_key"), "status")], prefix="k")
    surface = {
        "kind": _as_choice(surface_raw.get("kind"), host.SURFACE_KINDS),
        "ok_token": ok_token,
        "error_token": error_token,
        "field_separator": _as_choice(surface_raw.get("field_separator"), host.FIELD_SEPARATORS),
        "pair_separator": _as_choice(surface_raw.get("pair_separator"), host.PAIR_SEPARATORS),
        "action_key": keys[0], "argument_key": keys[1], "status_key": keys[2],
    }

    cells_raw = _as_list(raw.get("cells"))[:MAX_CELLS]
    while len(cells_raw) < MIN_CELLS:
        cells_raw.append({"name": "c%d" % len(cells_raw), "size": CELL_SIZES[0], "initial": 0})
    sizes = [_as_choice(_as_int((c or {}).get("size") if isinstance(c, Mapping) else None),
                        CELL_SIZES) for c in cells_raw]
    names = _distinct(
        [_as_identifier((c or {}).get("name") if isinstance(c, Mapping) else None, "c%d" % i)
         for i, c in enumerate(cells_raw)], reserved=keys, prefix="c")
    cells = [{"name": name, "size": size} for name, size in zip(names, sizes)]
    initial = [_as_int((c or {}).get("initial") if isinstance(c, Mapping) else None) % size
               for c, size in zip(cells_raw, sizes)]

    # `hidden` names the exception. Everything not named is observed, and the contract's floor of
    # three cells against a ceiling of one hidden cell means at least two always are.
    hidden = {_as_int(index) % len(cells)
              for index in _as_list(raw.get("hidden"))[:MAX_HIDDEN_CELLS]
              if isinstance(index, int) and not isinstance(index, bool)}
    visible = [position not in hidden for position in range(len(cells))]
    if not any(visible):  # pragma: no cover -- unreachable while MIN_CELLS > MAX_HIDDEN_CELLS
        visible[0] = True

    errors_raw = [_as_identifier(value, "e%d" % index)
                  for index, value in enumerate(_as_list(raw.get("errors"))[:MAX_ERRORS])]
    errors = _distinct(errors_raw or ["e0"], prefix="e")

    conditional = _as_list(raw.get("conditional_actions"))[:MAX_CONDITIONAL_ACTIONS]
    plain = _as_list(raw.get("actions"))[:MAX_PLAIN_ACTIONS]
    ordered = list(conditional) + list(plain)
    while len(ordered) < host.MIN_ACTIONS:
        ordered.append({})
    ordered = ordered[: host.MAX_ACTIONS]
    default_guard = ({"cell": 0, "relation": "ge", "value": 0},)
    actions = [
        # Only the conditional slots carry a guaranteed guard, and only when the candidate left
        # the list empty -- which the schema forbids for those slots and which therefore cannot
        # arise from a schema-valid completion.
        _decode_action(item, index, cells=cells, errors=errors,
                       default_guard=default_guard if index < len(conditional) else ())
        for index, item in enumerate(ordered)
    ]
    action_names = _distinct([action["name"] for action in actions], prefix="a")
    for action, name in zip(actions, action_names):
        action["name"] = name

    return {"surface": surface, "cells": cells, "initial": initial, "visible": visible,
            "errors": errors, "actions": actions}


def decode_completion(machines: Sequence[Any]) -> list[dict[str, Any]]:
    """Positional and total: machine *i* becomes carrier *i*, and none is dropped or reordered."""
    return [decode_machine(machine) for machine in machines]


# ---------------------------------------------------------------------------------------------
# The acceptance claim, stated so it can be checked rather than believed
# ---------------------------------------------------------------------------------------------

# Every distinct message `carrier_host.validate_carrier` can raise. The contract test asserts that
# this list is still exactly what the host's source contains, so a refusal added later cannot
# quietly become a class the decoder has never been shown to close.
HOST_REFUSALS = (
    "a cell name collides with a surface key",
    "a nullary action cannot assign from an argument it does not take",
    "action effect assignment is not an object",
    "action effect carries more assignments than the meta-schema permits",
    "action effect is empty or is not a list",
    "action guard carries more clauses than the meta-schema permits",
    "action guard clause is not an object",
    "action guard is not a list",
    "action names an error code the carrier does not declare",
    "carrier action count is outside the meta-schema",
    "carrier action is not an object",
    "carrier actions is not a list",
    "carrier cell count is outside the meta-schema",
    "carrier cell is not an object",
    "carrier cells is not a list",
    "carrier error count is outside the meta-schema",
    "carrier errors is not a list",
    "carrier initial state does not cover every cell",
    "carrier initial state is not a list",
    "carrier is not an object",
    "carrier observes none of its own state",
    "carrier repeats a cell name",
    "carrier repeats an action name",
    "carrier repeats an error code",
    "carrier surface cannot report success and failure with one token",
    "carrier surface field separator is outside the meta-schema",
    "carrier surface is not an object",
    "carrier surface kind is outside the meta-schema",
    "carrier surface pair separator is outside the meta-schema",
    "carrier surface reuses one key for two roles",
    "guard relation is outside the meta-schema",
    "carrier visibility does not cover every cell",
    "carrier visibility entry is not a boolean",
    "carrier visibility is not a list",
    "effect mode is outside the meta-schema",
)


def acceptance_census(candidates: Sequence[Any]) -> dict[str, Any]:
    """Decode each candidate and report whether the frozen host accepted every one.

    Counts and messages only. No carrier value ever appears in the result, so this is safe to
    record beside a sealed bank.
    """
    refusals: dict[str, int] = {}
    accepted = 0
    for candidate in candidates:
        try:
            host.validate_carrier(decode_machine(candidate))
        except host.CarrierError as exc:
            refusals[str(exc)] = refusals.get(str(exc), 0) + 1
        else:
            accepted += 1
    return {
        "schema": "m120-acceptance-census-v1",
        "contract_version": CONTRACT_VERSION,
        "decoder_version": DECODER_VERSION,
        "candidates": len(candidates),
        "accepted_by_the_frozen_host": accepted,
        "refused_by_the_frozen_host": len(candidates) - accepted,
        "refusals": dict(sorted(refusals.items())),
        "every_decoded_candidate_was_accepted": accepted == len(candidates),
    }


def contract_report() -> dict[str, Any]:
    """What the contract binds, for the plan and the freeze to carry."""
    return {
        "schema": "m120-carrier-contract-report-v1",
        "contract_version": CONTRACT_VERSION,
        "decoder_version": DECODER_VERSION,
        "family": {
            "cells": [MIN_CELLS, MAX_CELLS],
            "cell_sizes": list(CELL_SIZES),
            "hidden_cells_at_most": MAX_HIDDEN_CELLS,
            "observable_cells_at_least": MIN_CELLS - MAX_HIDDEN_CELLS,
            "conditional_actions": [MIN_CONDITIONAL_ACTIONS, MAX_CONDITIONAL_ACTIONS],
            "plain_actions": [MIN_PLAIN_ACTIONS, MAX_PLAIN_ACTIONS],
            "actions": [MIN_ACTIONS, MAX_ACTIONS],
            "errors": [MIN_ERRORS, MAX_ERRORS],
            "argument_domains": list(ARG_SIZES),
        },
        "schema_uses_only_feature_classes_proven_enforced_on_the_route": True,
        "proven_feature_classes": list(PROVEN_FEATURE_CLASSES),
        "readiness_evidence": READINESS_EVIDENCE_PATH,
        "schema_states_no_relation_between_two_fields": True,
        "decoder_is_total_deterministic_and_content_independent": True,
        "decoder_cannot_refuse_reorder_drop_or_select": True,
        "decoder_cannot_make_a_carrier_qualify": True,
        "host_refusal_classes_enumerated": len(HOST_REFUSALS),
        "family_is_narrower_than_m115_and_that_is_disclosed": True,
    }


__all__ = [
    "CANDIDATE_SCHEMA",
    "CONTRACT_VERSION",
    "DECODER_VERSION",
    "HOST_REFUSALS",
    "ContractError",
    "acceptance_census",
    "candidate_schema",
    "contract_report",
    "decode_completion",
    "decode_machine",
]
