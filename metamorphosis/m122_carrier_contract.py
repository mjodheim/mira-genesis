"""The M122 carrier contract: M120's, flattened to a depth this route has been observed to enforce.

M120 closed at its readiness gate. The contract was mechanically host-safe -- every schema-valid
candidate decoded into a carrier the frozen host accepts, established over 240 exhaustive corners,
1,200 fuzzed draws and M119's own committed bank -- and the route refused to enforce it. Seven of
the nine required feature classes held. `array_of_object_levels` did not: the probe free-ran to
101,379 completion tokens and truncated, where enforcement would have produced about fifty.

The cause was structural and is worth naming precisely, because it was not a mistake in the schema
so much as a mistake in what the schema was asked to guarantee.

## Why M120 was eight levels deep

The frozen host requires that at least one action carry a precondition, or the carrier fails the
`the_carrier_imposes_a_protocol` qualification clause. JSON Schema can say "at least one element of
this array satisfies X" with `contains` and `minContains`, and **this route has no evidence of
enforcing either**, so M120 could not use them. Its workaround was to split one `actions` array in
two -- `conditional_actions`, whose items require a non-empty `guard`, and `actions`, whose items do
not -- turning a `contains` into a `minItems`.

That works, and it duplicates the entire action subtree: action, guard, effect. Five
array-of-object levels became eight, and eight is past what the route holds.

## What the measurement then showed

The guarantee was not worth its price, and this is the part that matters more than the flattening.

Measured over the same family, carriers in which **no** action carries a guard occur at **0.75%**
at the smallest shape the contract admits, and at **0.00%** across the family as a whole. Requiring
every action to be guarded instead -- the other way to keep one array -- *costs* qualification
rather than buying it: 36.5% against 52.2% uniform, because gating every action makes states
unreachable and the reachability clauses fail.

So M120 spent three nesting levels, and about sixteen points of qualification rate, insuring
against a 0.75% risk that the pre-seal adequacy gate would have caught anyway. M122 drops the
guarantee, keeps one `actions` array with `guard` at `minItems: 0`, and lets the qualification
clause do what it is for.

## What is unchanged from M120

Everything that worked, and it worked well:

- the schema states **no relation between two fields**, which is what M119 died of;
- `arg_size` over `{0, 2, 3, 4}` with arity derived, so the combination the host refuses cannot be
  written down;
- `initial` inside its own cell, so two lengths cannot disagree;
- `hidden` rather than `visible`, at most one index over at least three cells, so a machine that
  observes none of its own state is not expressible;
- `error_index` rather than a name, reduced against the declared list;
- a total, deterministic, content-independent decoder that cannot refuse, reorder, drop or select,
  and cannot make a carrier qualify.

## The guard M120 did not have

`_assert_within_the_certified_census` fails at import if this schema's `array_of_object_levels`
exceeds the depth the route has been observed to enforce. M120's contract had no such check: its
census drifted from five to eight as the representation changed, and nothing said so until a
readiness gate spent sixteen requests discovering it. A contract that cannot state its own
serviceability is a contract that will be found unserviceable later and more expensively.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from metamorphosis import carrier_host as host

CONTRACT_VERSION = "m122-carrier-contract-v1"
DECODER_VERSION = "m122-candidate-decoder-v1"

# ---------------------------------------------------------------------------------------------
# The family
# ---------------------------------------------------------------------------------------------
#
# Inherited from M120 unchanged except for the action arrays, which merge back into one. The
# narrowing that M120 established -- at least three cells, at most one latent, four to six actions
# -- is kept: it was never the thing the route refused, and M119's degenerate bank is the reason
# for it.
MIN_CELLS = 3
MAX_CELLS = 4
MAX_HIDDEN_CELLS = 1          # >= 3 cells and <= 1 hidden means >= 2 are always observable
MIN_ACTIONS = 4
MAX_ACTIONS = 6
MIN_GUARD_CLAUSES = 0         # M120 required 1 on half the actions; measured cost, no benefit
MIN_ERRORS = 1
MAX_ERRORS = 4

CELL_SIZES = (2, 3, 4)
ARG_SIZES = (0, 2, 3, 4)      # 0 means nullary; every other value is a legal unary domain
CELL_INDICES = tuple(range(MAX_CELLS))
CELL_VALUES = tuple(range(max(CELL_SIZES)))
ERROR_INDICES = tuple(range(MAX_ERRORS))

IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]{1,11}$"
TOKEN_PATTERN = r"^[a-z][a-z0-9]{1,7}$"

_IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN)
_TOKEN_RE = re.compile(TOKEN_PATTERN)

# The depth this route has been observed to enforce. M115's schema sat at five array-of-object
# levels; M118's readiness gate certified that census and M116 and M119 both ran under it. M120
# raised it to eight and the route did not hold the shape. Five is therefore evidence, not
# preference, and the assertion below makes it binding on this schema rather than on a comment.
CERTIFIED_ARRAY_OF_OBJECT_LEVELS = 5
CERTIFIED_BY = ("experiments/M118/READINESS_RESULT.json",
                "experiments/M120/READINESS_RESULT.json")

# The classes M120's own readiness run observed this route enforcing. `array_of_object_levels` is
# on the list because the run establishes it at five even though it refused eight: the seven that
# passed did so inside a schema carrying five-level structures throughout.
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
    if MIN_CELLS - MAX_HIDDEN_CELLS < 2:
        problems.append("observability")
    if max(CELL_VALUES) + 1 < max(CELL_SIZES):
        problems.append("cell value range")
    if IDENTIFIER_PATTERN != host.IDENTIFIER_RE.pattern.replace("\\A", "^").replace("\\Z", "$"):
        problems.append("identifier pattern")
    if TOKEN_PATTERN != host.TOKEN_RE.pattern.replace("\\A", "^").replace("\\Z", "$"):
        problems.append("token pattern")
    if problems:
        raise ContractError(
            "the M122 carrier family is not inside the frozen host meta-schema: %s"
            % ", ".join(problems))


def _assert_within_the_certified_census() -> None:
    """The schema may not ask the route for more nesting than the route has been shown to hold.

    This is the check M120 did not have. Its census drifted from five array-of-object levels to
    eight as the representation changed, nothing in the apparatus said so, and the discrepancy
    surfaced only when a single-use readiness gate spent sixteen requests finding it. A contract
    that cannot state its own serviceability will be found unserviceable later and at a worse
    price.
    """
    from metamorphosis import m116_schema as schema_tools  # noqa: PLC0415

    census = schema_tools.census(candidate_schema())
    levels = int(census["array_of_object_levels"])
    if levels > CERTIFIED_ARRAY_OF_OBJECT_LEVELS:
        raise ContractError(
            "the candidate schema needs %d array-of-object levels and this route has been "
            "observed to enforce %d; see %s. M120 closed on exactly this."
            % (levels, CERTIFIED_ARRAY_OF_OBJECT_LEVELS, ", ".join(CERTIFIED_BY)))
    used = {name for name, count in census["keyword_counts"].items() if count}
    unproven = used - set(PROVEN_FEATURE_CLASSES) - {"properties"}
    if unproven:
        raise ContractError(
            "the candidate schema uses keywords this route has not been observed to enforce: %s"
            % ", ".join(sorted(unproven)))
    if census["composition_constructs"]:
        raise ContractError(
            "the candidate schema uses a composition construct; `oneOf` and `contains` would each "
            "say something here more directly and neither has evidence on this route")


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


def _action() -> dict[str, Any]:
    """One action shape, and only one.

    M120 needed two -- one requiring a guard, one not -- to express "at least one action carries a
    precondition" without `contains`. That guarantee cost three array-of-object levels and bought
    protection against a case measured at 0.75%. It is gone, and the qualification clause that
    cares is left to fail honestly on the rare carrier that earns it.
    """
    return {
        "type": "object", "additionalProperties": False,
        "required": ["name", "arg_size", "guard", "effect", "error_index"],
        "properties": {
            "name": _identifier(),
            # One field where M115 had two. `arity` is derived from it, so the combination the
            # host refuses -- a unary action with an argument domain of 0 or 1 -- cannot be
            # written down at all.
            "arg_size": {"type": "integer", "enum": list(ARG_SIZES)},
            "guard": {"type": "array", "minItems": MIN_GUARD_CLAUSES,
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
        "required": ["surface", "cells", "hidden", "errors", "actions"],
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
            "hidden": {"type": "array", "minItems": 0, "maxItems": MAX_HIDDEN_CELLS,
                       "items": {"type": "integer", "enum": list(CELL_INDICES)}},
            "errors": {"type": "array", "minItems": MIN_ERRORS, "maxItems": MAX_ERRORS,
                       "items": _identifier()},
            "actions": {"type": "array", "minItems": MIN_ACTIONS, "maxItems": MAX_ACTIONS,
                        "items": _action()},
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


_assert_within_the_certified_census()

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
    """Make identifiers distinct from each other and from `reserved`, deterministically."""
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
                   errors: Sequence[str]) -> dict[str, Any]:
    raw = raw if isinstance(raw, Mapping) else {}
    n_cells = len(cells)

    effect_raw = _as_list(raw.get("effect"))[: host.MAX_EFFECT_ASSIGNMENTS]
    if not effect_raw:
        effect_raw = [{"cell": 0, "mode": "add", "operand": 1}]

    # Arity is derived from the one field that carries it. The single conditional in this decoder
    # is here: an action whose own effect asks for an argument is given the smallest legal
    # argument domain rather than having that effect silently rewritten.
    arg_size = _as_choice(_as_int(raw.get("arg_size")), ARG_SIZES)
    wants_argument = any(isinstance(item, Mapping) and item.get("mode") == "arg"
                         for item in effect_raw)
    if wants_argument and arg_size == 0:
        arg_size = host.MIN_ARG_DOMAIN
    arity = 1 if arg_size else 0

    guard = []
    for clause in _as_list(raw.get("guard"))[: host.MAX_GUARD_CLAUSES]:
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
    """One candidate to one carrier the frozen host accepts. Total on every input."""
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

    hidden = {_as_int(index) % len(cells)
              for index in _as_list(raw.get("hidden"))[:MAX_HIDDEN_CELLS]
              if isinstance(index, int) and not isinstance(index, bool)}
    visible = [position not in hidden for position in range(len(cells))]
    if not any(visible):  # pragma: no cover -- unreachable while MIN_CELLS > MAX_HIDDEN_CELLS
        visible[0] = True

    errors_raw = [_as_identifier(value, "e%d" % index)
                  for index, value in enumerate(_as_list(raw.get("errors"))[:MAX_ERRORS])]
    errors = _distinct(errors_raw or ["e0"], prefix="e")

    ordered = _as_list(raw.get("actions"))[:MAX_ACTIONS]
    while len(ordered) < host.MIN_ACTIONS:
        ordered.append({})
    actions = [_decode_action(item, index, cells=cells, errors=errors)
               for index, item in enumerate(ordered)]
    action_names = _distinct([action["name"] for action in actions], prefix="a")
    for action, name in zip(actions, action_names):
        action["name"] = name

    return {"surface": surface, "cells": cells, "initial": initial, "visible": visible,
            "errors": errors, "actions": actions}


def decode_completion(machines: Sequence[Any]) -> list[dict[str, Any]]:
    """Positional and total: machine *i* becomes carrier *i*, and none is dropped or reordered."""
    return [decode_machine(machine) for machine in machines]


# ---------------------------------------------------------------------------------------------
# The acceptance claim
# ---------------------------------------------------------------------------------------------

# Inherited from M120 unchanged: every distinct message `carrier_host.validate_carrier` can raise.
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
    "carrier visibility does not cover every cell",
    "carrier visibility entry is not a boolean",
    "carrier visibility is not a list",
    "effect mode is outside the meta-schema",
    "guard relation is outside the meta-schema",
)


def acceptance_census(candidates: Sequence[Any]) -> dict[str, Any]:
    """Decode each candidate and report whether the frozen host accepted every one."""
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
        "schema": "m122-acceptance-census-v1",
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
    from metamorphosis import m116_schema as schema_tools  # noqa: PLC0415

    census = schema_tools.census(candidate_schema())
    return {
        "schema": "m122-carrier-contract-report-v1",
        "contract_version": CONTRACT_VERSION,
        "decoder_version": DECODER_VERSION,
        "family": {
            "cells": [MIN_CELLS, MAX_CELLS],
            "cell_sizes": list(CELL_SIZES),
            "hidden_cells_at_most": MAX_HIDDEN_CELLS,
            "observable_cells_at_least": MIN_CELLS - MAX_HIDDEN_CELLS,
            "actions": [MIN_ACTIONS, MAX_ACTIONS],
            "guard_clauses_per_action": [MIN_GUARD_CLAUSES, host.MAX_GUARD_CLAUSES],
            "errors": [MIN_ERRORS, MAX_ERRORS],
            "argument_domains": list(ARG_SIZES),
        },
        "array_of_object_levels": int(census["array_of_object_levels"]),
        "certified_array_of_object_levels": CERTIFIED_ARRAY_OF_OBJECT_LEVELS,
        "census_is_within_what_the_route_enforces": True,
        "certified_by": list(CERTIFIED_BY),
        "schema_uses_only_feature_classes_proven_enforced_on_the_route": True,
        "schema_states_no_relation_between_two_fields": True,
        "decoder_is_total_deterministic_and_content_independent": True,
        "decoder_cannot_refuse_reorder_drop_or_select": True,
        "decoder_cannot_make_a_carrier_qualify": True,
        "host_refusal_classes_enumerated": len(HOST_REFUSALS),
        "differs_from_m120_by": (
            "one actions array instead of two, with guard minItems 0. M120 split the array to "
            "express 'at least one action carries a precondition' without `contains`, which this "
            "route does not enforce; the split duplicated the action subtree and took the census "
            "from five array-of-object levels to eight, which this route also does not enforce."),
        "the_dropped_guarantee_was_measured_at_0_75_percent": True,
    }


__all__ = [
    "CANDIDATE_SCHEMA",
    "CERTIFIED_ARRAY_OF_OBJECT_LEVELS",
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
