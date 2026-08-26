"""A universal host for carriers it knows nothing about.

M107 made the operators data and left the interpreter empty of their semantics. M110 carried that
interpreter into a different laboratory. M112 then let a blind generator choose the *values* inside
a carrier this project designed, and recorded the ceiling that remained in one word: **the carrier**.

This module lifts the same move one level. A carrier here is **data**: its state cells, its initial
configuration, which cells are observable, its action names, their arities, their preconditions,
their effects, its error codes and the wire grammar its requests and responses are written in. The
host holds none of that. It can execute any carrier under the meta-schema and has no way to
distinguish one from another beyond the bytes it was handed.

Everything here is total and deterministic. No carrier can raise, loop, allocate without bound,
touch the filesystem, open a socket, import a module or execute generated source: an action is a
finite list of arithmetic assignments modulo a declared domain, and a guard is a finite list of
comparisons. That is a deliberate restriction of what a blind generator may emit, not an accident of
implementation -- a bank of arbitrary programs would make the sandbox, rather than the science, the
load-bearing part of the result.

## What varies between carriers, and what does not

Varies, and is chosen entirely by the emitter:

- **representation** -- four wire surfaces (named JSON object, named text line, packed positional
  digits, positional JSON array), each with its own emitter-chosen tokens and separators;
- **state** -- one to four named cells, each over its own finite domain, some of them latent;
- **interaction** -- two to six actions, each nullary or unary over its own argument domain;
- **permitted operations** -- each action carries a precondition over the state, so a carrier can
  impose an order in which its actions may legally be used;
- **error structure** -- an emitter-chosen error vocabulary and an emitter-chosen mapping from
  refused action to code.

Does not vary, and is this project's reception contract:

- the meta-schema itself, and therefore the space carriers are drawn from;
- the four wire surfaces' shapes, though not their tokens;
- the meta-channel, which reports the wire grammar and the action names and arities and **nothing
  else** -- no cell, no precondition, no effect, no observability and no error mapping.

## The meta-channel is the honest part of the boundary

A learner that cannot form a syntactically valid request discovers nothing, so some framing has to
be legitimately observable. Real systems make exactly this much observable and no more: a CLI's
usage line, a service's schema endpoint, a protocol banner. What the meta-channel deliberately does
not carry is every fact the science is about -- what an action does, what it costs, when it is
refused, what the response means, and which states can be reached at all.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "mira-blind-carrier-v1"
META_CHANNEL_SCHEMA = "mira-blind-carrier-meta-channel-v1"

# The meta-schema's fixed dimensions. These bound the emitter's choices; they do not make them.
MIN_CELLS = 1
MAX_CELLS = 4
MIN_CELL_DOMAIN = 2
MAX_CELL_DOMAIN = 4
MIN_ACTIONS = 2
MAX_ACTIONS = 6
MIN_ARG_DOMAIN = 2
MAX_ARG_DOMAIN = 4
MAX_GUARD_CLAUSES = 3
MAX_EFFECT_ASSIGNMENTS = 3
MIN_ERRORS = 1
MAX_ERRORS = 4

SURFACE_KINDS = ("json_object", "text_line", "packed_digits", "json_array")
GUARD_RELATIONS = ("eq", "ne", "lt", "ge")
EFFECT_MODES = ("set", "add", "sub", "arg", "copy")

FIELD_SEPARATORS = (" ", ":", ",", ";", "|")
PAIR_SEPARATORS = ("=", "-", "/")

IDENTIFIER_RE = re.compile(r"\A[a-z][a-z0-9_]{1,11}\Z")
TOKEN_RE = re.compile(r"\A[a-z][a-z0-9]{1,7}\Z")


class CarrierError(ValueError):
    """Raised when a carrier payload is outside the meta-schema. Every path fails closed."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


# ----------------------------------------------------------------------------------------
# Validation. A carrier the host refuses is not a carrier, and no later stage sees it.
# ----------------------------------------------------------------------------------------


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise CarrierError("%s is not a carrier identifier" % label)
    return value


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not TOKEN_RE.match(value):
        raise CarrierError("%s is not a carrier surface token" % label)
    return value


def _bounded_int(value: Any, low: int, high: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise CarrierError("%s is outside %d..%d" % (label, low, high))
    return int(value)


def validate_surface(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CarrierError("carrier surface is not an object")
    kind = raw.get("kind")
    if kind not in SURFACE_KINDS:
        raise CarrierError("carrier surface kind is outside the meta-schema")
    ok_token = _token(raw.get("ok_token"), "surface ok_token")
    error_token = _token(raw.get("error_token"), "surface error_token")
    if ok_token == error_token:
        raise CarrierError("carrier surface cannot report success and failure with one token")
    field_separator = raw.get("field_separator")
    if field_separator not in FIELD_SEPARATORS:
        raise CarrierError("carrier surface field separator is outside the meta-schema")
    pair_separator = raw.get("pair_separator")
    if pair_separator not in PAIR_SEPARATORS:
        raise CarrierError("carrier surface pair separator is outside the meta-schema")
    action_key = _identifier(raw.get("action_key"), "surface action_key")
    argument_key = _identifier(raw.get("argument_key"), "surface argument_key")
    status_key = _identifier(raw.get("status_key"), "surface status_key")
    if len({action_key, argument_key, status_key}) != 3:
        raise CarrierError("carrier surface reuses one key for two roles")
    return {
        "kind": kind,
        "ok_token": ok_token,
        "error_token": error_token,
        "field_separator": field_separator,
        "pair_separator": pair_separator,
        "action_key": action_key,
        "argument_key": argument_key,
        "status_key": status_key,
    }


def _validate_guard(
    raw: Any, cell_count: int, cells: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise CarrierError("action guard is not a list")
    if len(raw) > MAX_GUARD_CLAUSES:
        raise CarrierError("action guard carries more clauses than the meta-schema permits")
    clauses: list[dict[str, Any]] = []
    for clause in raw:
        if not isinstance(clause, Mapping):
            raise CarrierError("action guard clause is not an object")
        cell = _bounded_int(clause.get("cell"), 0, cell_count - 1, "guard clause cell")
        relation = clause.get("relation")
        if relation not in GUARD_RELATIONS:
            raise CarrierError("guard relation is outside the meta-schema")
        value = _bounded_int(
            clause.get("value"), 0, int(cells[cell]["size"]) - 1, "guard clause value"
        )
        clauses.append({"cell": cell, "relation": relation, "value": value})
    return clauses


def _validate_effect(
    raw: Any, cell_count: int, cells: Sequence[Mapping[str, Any]], arity: int
) -> list[dict[str, Any]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise CarrierError("action effect is empty or is not a list")
    if len(raw) > MAX_EFFECT_ASSIGNMENTS:
        raise CarrierError("action effect carries more assignments than the meta-schema permits")
    assignments: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise CarrierError("action effect assignment is not an object")
        cell = _bounded_int(item.get("cell"), 0, cell_count - 1, "effect assignment cell")
        mode = item.get("mode")
        if mode not in EFFECT_MODES:
            raise CarrierError("effect mode is outside the meta-schema")
        if mode == "arg" and arity != 1:
            raise CarrierError("a nullary action cannot assign from an argument it does not take")
        if mode == "copy":
            operand = _bounded_int(item.get("operand"), 0, cell_count - 1, "copy source cell")
        elif mode == "arg":
            operand = 0
        else:
            operand = _bounded_int(
                item.get("operand"), 0, int(cells[cell]["size"]) - 1, "effect operand"
            )
        assignments.append({"cell": cell, "mode": mode, "operand": operand})
    return assignments


def validate_carrier(raw: Any) -> dict[str, Any]:
    """Structural conformity, and nothing about whether the carrier is any good.

    The rebuilt object is canonical: later stages compare digests over it rather than over whatever
    key order the emitter happened to produce.
    """
    if not isinstance(raw, Mapping):
        raise CarrierError("carrier is not an object")

    surface = validate_surface(raw.get("surface"))

    raw_cells = raw.get("cells")
    if not isinstance(raw_cells, Sequence) or isinstance(raw_cells, (str, bytes)):
        raise CarrierError("carrier cells is not a list")
    if not MIN_CELLS <= len(raw_cells) <= MAX_CELLS:
        raise CarrierError("carrier cell count is outside the meta-schema")
    cells: list[dict[str, Any]] = []
    for item in raw_cells:
        if not isinstance(item, Mapping):
            raise CarrierError("carrier cell is not an object")
        cells.append(
            {
                "name": _identifier(item.get("name"), "cell name"),
                "size": _bounded_int(
                    item.get("size"), MIN_CELL_DOMAIN, MAX_CELL_DOMAIN, "cell domain size"
                ),
            }
        )
    if len({item["name"] for item in cells}) != len(cells):
        raise CarrierError("carrier repeats a cell name")

    raw_initial = raw.get("initial")
    if not isinstance(raw_initial, Sequence) or isinstance(raw_initial, (str, bytes)):
        raise CarrierError("carrier initial state is not a list")
    if len(raw_initial) != len(cells):
        raise CarrierError("carrier initial state does not cover every cell")
    initial = [
        _bounded_int(value, 0, cells[index]["size"] - 1, "initial cell value")
        for index, value in enumerate(raw_initial)
    ]

    raw_visible = raw.get("visible")
    if not isinstance(raw_visible, Sequence) or isinstance(raw_visible, (str, bytes)):
        raise CarrierError("carrier visibility is not a list")
    if len(raw_visible) != len(cells):
        raise CarrierError("carrier visibility does not cover every cell")
    visible = []
    for value in raw_visible:
        if not isinstance(value, bool):
            raise CarrierError("carrier visibility entry is not a boolean")
        visible.append(bool(value))
    if not any(visible):
        raise CarrierError("carrier observes none of its own state")

    raw_errors = raw.get("errors")
    if not isinstance(raw_errors, Sequence) or isinstance(raw_errors, (str, bytes)):
        raise CarrierError("carrier errors is not a list")
    if not MIN_ERRORS <= len(raw_errors) <= MAX_ERRORS:
        raise CarrierError("carrier error count is outside the meta-schema")
    errors = [_identifier(value, "error code") for value in raw_errors]
    if len(set(errors)) != len(errors):
        raise CarrierError("carrier repeats an error code")

    raw_actions = raw.get("actions")
    if not isinstance(raw_actions, Sequence) or isinstance(raw_actions, (str, bytes)):
        raise CarrierError("carrier actions is not a list")
    if not MIN_ACTIONS <= len(raw_actions) <= MAX_ACTIONS:
        raise CarrierError("carrier action count is outside the meta-schema")
    actions: list[dict[str, Any]] = []
    for item in raw_actions:
        if not isinstance(item, Mapping):
            raise CarrierError("carrier action is not an object")
        arity = _bounded_int(item.get("arity"), 0, 1, "action arity")
        arg_size = (
            _bounded_int(
                item.get("arg_size"), MIN_ARG_DOMAIN, MAX_ARG_DOMAIN, "action argument domain"
            )
            if arity == 1
            else 0
        )
        error = item.get("error")
        if error not in errors:
            raise CarrierError("action names an error code the carrier does not declare")
        actions.append(
            {
                "name": _identifier(item.get("name"), "action name"),
                "arity": arity,
                "arg_size": arg_size,
                "guard": _validate_guard(item.get("guard"), len(cells), cells),
                "effect": _validate_effect(item.get("effect"), len(cells), cells, arity),
                "error": error,
            }
        )
    if len({item["name"] for item in actions}) != len(actions):
        raise CarrierError("carrier repeats an action name")

    # A name collision between the surface's own keys and a cell name would make a response
    # ambiguous to any reader, including the evaluator.
    reserved = {surface["action_key"], surface["argument_key"], surface["status_key"]}
    if reserved & {item["name"] for item in cells}:
        raise CarrierError("a cell name collides with a surface key")

    carrier = {
        "schema": SCHEMA,
        "surface": surface,
        "cells": cells,
        "initial": initial,
        "visible": visible,
        "errors": errors,
        "actions": actions,
    }
    carrier["carrier_digest"] = digest(carrier)
    return carrier


# ----------------------------------------------------------------------------------------
# Semantics. Total, deterministic, and unaware of which carrier it is running.
# ----------------------------------------------------------------------------------------


def observation(carrier: Mapping[str, Any], state: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(value) for value, shown in zip(state, carrier["visible"]) if shown)


def observed_cells(carrier: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(item["name"] for item, shown in zip(carrier["cells"], carrier["visible"]) if shown)


def guard_holds(
    carrier: Mapping[str, Any], state: Sequence[int], action: Mapping[str, Any]
) -> bool:
    for clause in action["guard"]:
        held = int(state[clause["cell"]])
        wanted = int(clause["value"])
        relation = clause["relation"]
        if relation == "eq" and held != wanted:
            return False
        if relation == "ne" and held == wanted:
            return False
        if relation == "lt" and not held < wanted:
            return False
        if relation == "ge" and not held >= wanted:
            return False
    return True


def apply_effect(
    carrier: Mapping[str, Any], state: Sequence[int], action: Mapping[str, Any], argument: int
) -> tuple[int, ...]:
    """Assignments read the state as it was before the action. Order cannot change the outcome."""
    before = [int(value) for value in state]
    after = list(before)
    for item in action["effect"]:
        cell = item["cell"]
        size = int(carrier["cells"][cell]["size"])
        mode = item["mode"]
        if mode == "set":
            value = item["operand"]
        elif mode == "add":
            value = before[cell] + item["operand"]
        elif mode == "sub":
            value = before[cell] - item["operand"]
        elif mode == "arg":
            value = int(argument)
        else:
            value = before[item["operand"]]
        after[cell] = value % size
    return tuple(after)


def find_action(carrier: Mapping[str, Any], name: str) -> dict[str, Any] | None:
    for item in carrier["actions"]:
        if item["name"] == name:
            return item
    return None


UNKNOWN_ACTION = "unknown_action"
MALFORMED_REQUEST = "malformed_request"


def step(
    carrier: Mapping[str, Any], state: Sequence[int], name: str, argument: int
) -> dict[str, Any]:
    """One transition. Never raises: a refused or unknown action is an outcome, not an exception."""
    action = find_action(carrier, name)
    if action is None:
        return {"accepted": False, "error": UNKNOWN_ACTION, "state": tuple(int(v) for v in state)}
    if action["arity"] == 1 and not 0 <= int(argument) < action["arg_size"]:
        return {"accepted": False, "error": action["error"], "state": tuple(int(v) for v in state)}
    if not guard_holds(carrier, state, action):
        return {"accepted": False, "error": action["error"], "state": tuple(int(v) for v in state)}
    return {
        "accepted": True,
        "error": None,
        "state": apply_effect(carrier, state, action, int(argument)),
    }


def initial_state(carrier: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(int(value) for value in carrier["initial"])


def action_alphabet(carrier: Mapping[str, Any]) -> list[tuple[str, int]]:
    """Every request the carrier's own declaration admits, in canonical order."""
    alphabet: list[tuple[str, int]] = []
    for item in carrier["actions"]:
        if item["arity"] == 0:
            alphabet.append((item["name"], 0))
        else:
            for value in range(item["arg_size"]):
                alphabet.append((item["name"], value))
    return alphabet


# ----------------------------------------------------------------------------------------
# The wire. Four surfaces, each with the emitter's own tokens; the host holds no preference.
# ----------------------------------------------------------------------------------------


def encode_request(carrier: Mapping[str, Any], name: str, argument: int) -> str:
    surface = carrier["surface"]
    kind = surface["kind"]
    if kind == "json_object":
        return canonical_json({surface["action_key"]: name, surface["argument_key"]: int(argument)})
    if kind == "json_array":
        return canonical_json([name, int(argument)])
    if kind == "text_line":
        return "%s%s%d" % (name, surface["field_separator"], int(argument))
    index = next(
        (position for position, item in enumerate(carrier["actions"]) if item["name"] == name),
        None,
    )
    if index is None:
        # An unknown action still has to be expressible on a positional wire, or the learner could
        # never make the mistake the carrier is entitled to refuse.
        index = len(carrier["actions"])
    return "%d%d" % (index % 10, int(argument) % 10)


def decode_request(carrier: Mapping[str, Any], request: str) -> tuple[str, int] | None:
    surface = carrier["surface"]
    kind = surface["kind"]
    if kind in ("json_object", "json_array"):
        try:
            parsed = json.loads(request)
        except (ValueError, TypeError):
            return None
        if kind == "json_object":
            if not isinstance(parsed, dict):
                return None
            name = parsed.get(surface["action_key"])
            argument = parsed.get(surface["argument_key"], 0)
        else:
            if not isinstance(parsed, list) or len(parsed) != 2:
                return None
            name, argument = parsed[0], parsed[1]
        if not isinstance(name, str) or isinstance(argument, bool) or not isinstance(argument, int):
            return None
        return name, int(argument)
    if kind == "text_line":
        parts = request.split(surface["field_separator"])
        if len(parts) != 2 or not parts[1].isdigit():
            return None
        return parts[0], int(parts[1])
    if len(request) != 2 or not request.isdigit():
        return None
    index = int(request[0])
    if index >= len(carrier["actions"]):
        return UNKNOWN_ACTION, int(request[1])
    return carrier["actions"][index]["name"], int(request[1])


def encode_response(carrier: Mapping[str, Any], outcome: Mapping[str, Any]) -> str:
    surface = carrier["surface"]
    kind = surface["kind"]
    names = observed_cells(carrier)
    values = observation(carrier, outcome["state"])
    if outcome["accepted"]:
        if kind == "json_object":
            payload = {surface["status_key"]: surface["ok_token"]}
            payload.update({name: int(value) for name, value in zip(names, values)})
            return canonical_json(payload)
        if kind == "json_array":
            return canonical_json([surface["ok_token"]] + [int(value) for value in values])
        if kind == "text_line":
            pairs = [
                "%s%s%d" % (name, surface["pair_separator"], int(value))
                for name, value in zip(names, values)
            ]
            return surface["field_separator"].join([surface["ok_token"]] + pairs)
        return surface["ok_token"] + "".join(str(int(value) % 10) for value in values)
    code = outcome["error"]
    if kind == "json_object":
        return canonical_json({surface["status_key"]: surface["error_token"], "code": code})
    if kind == "json_array":
        return canonical_json([surface["error_token"], code])
    if kind == "text_line":
        return "%s%s%s" % (surface["error_token"], surface["field_separator"], code)
    position = carrier["errors"].index(code) if code in carrier["errors"] else len(carrier["errors"])
    return surface["error_token"] + str(position % 10)


def meta_channel(carrier: Mapping[str, Any]) -> dict[str, Any]:
    """Everything the reception contract declares legitimately observable, and nothing else.

    Absent by design: the cells, their domains, the initial configuration, which cells are
    observable, every precondition, every effect, the error vocabulary and the mapping from a
    refused action to the code it returns. A learner handed this knows how to *speak*; it knows
    nothing about what any sentence *does*.
    """
    return {
        "schema": META_CHANNEL_SCHEMA,
        "surface": dict(carrier["surface"]),
        "actions": [
            {"name": item["name"], "arity": item["arity"], "arg_size": item["arg_size"]}
            for item in carrier["actions"]
        ],
    }


# ----------------------------------------------------------------------------------------
# The session: the only object a learner is ever handed.
# ----------------------------------------------------------------------------------------


class BudgetExhausted(RuntimeError):
    """Raised when a session is asked for one more invocation than its declared budget."""


class Session:
    """An opaque handle over a carrier the holder cannot read.

    The carrier is held in a closure rather than on the instance, so there is no attribute, no
    ``__dict__`` entry and no property through which a learner could recover a precondition, an
    effect or a latent cell. What a holder can do is exactly what the reception contract permits:
    read the meta-channel, send a request, and ask how much of its budget it has spent.

    This is a boundary, not a sandbox, and the difference is worth stating rather than glossing.
    Python closures are introspectable: ``session._send.__closure__`` does contain the carrier, and
    no arrangement of ``__slots__`` changes that. What makes the boundary real is that the learner's
    source is audited and refused if it names a carrier-internal key or calls a host function that
    reads carrier structure. A claim that the learner *cannot* reach the carrier would be false; the
    claim made here is that it does not, and that this is checked mechanically.
    """

    __slots__ = ("_send", "_describe", "_budget", "_used", "_transcript", "carrier_ref")

    def __init__(
        self,
        carrier_ref: str,
        send: Callable[[str], str],
        describe: Callable[[], dict[str, Any]],
        budget: int,
    ) -> None:
        self.carrier_ref = str(carrier_ref)
        self._send = send
        self._describe = describe
        self._budget = int(budget)
        self._used = 0
        self._transcript: list[tuple[str, str]] = []

    @property
    def budget(self) -> int:
        return self._budget

    @property
    def invocations_used(self) -> int:
        return self._used

    @property
    def invocations_left(self) -> int:
        return self._budget - self._used

    def describe(self) -> dict[str, Any]:
        """The meta-channel. Free: it is a declaration, not an observation of state."""
        return self._describe()

    def send(self, request: str) -> str:
        if self._used >= self._budget:
            raise BudgetExhausted("carrier session budget exhausted")
        self._used += 1
        response = self._send(str(request))
        self._transcript.append((str(request), response))
        return response

    def transcript(self) -> list[list[str]]:
        return [list(item) for item in self._transcript]

    def transcript_digest(self) -> str:
        return digest(self.transcript())


class Channel:
    """A carrier that can be restarted, under one budget shared across every restart.

    A learner cannot rewind a stateful service, so exploring one means driving it from its initial
    configuration again -- and a restart is an action in the world, not a free rewind. It costs one
    invocation from the same budget the requests come out of. Every arm is handed a channel built
    the same way with the same number, so an arm that explores wastefully pays for it in the only
    currency the experiment has.
    """

    __slots__ = ("_carrier", "carrier_ref", "_budget", "_used", "_restarts", "_open")

    def __init__(self, carrier: Mapping[str, Any], carrier_ref: str, budget: int) -> None:
        self._carrier = validate_carrier(carrier) if carrier.get("schema") != SCHEMA else carrier
        self.carrier_ref = str(carrier_ref)
        self._budget = int(budget)
        self._used = 0
        self._restarts = 0
        self._open: Session | None = None

    @property
    def budget(self) -> int:
        return self._budget

    @property
    def invocations_used(self) -> int:
        return self._used + (self._open.invocations_used if self._open is not None else 0)

    @property
    def invocations_left(self) -> int:
        return self._budget - self.invocations_used

    @property
    def restarts(self) -> int:
        return self._restarts

    def describe(self) -> dict[str, Any]:
        return json.loads(canonical_json(meta_channel(self._carrier)))

    def restart(self) -> Session:
        """Close the running session and start the carrier again. Costs one invocation."""
        if self._open is not None:
            self._used += self._open.invocations_used
            self._open = None
        if self.invocations_left < 1:
            raise BudgetExhausted("carrier channel budget exhausted before a restart")
        self._used += 1
        self._restarts += 1
        self._open = open_session(self._carrier, self.carrier_ref, self.invocations_left)
        return self._open


def open_session(carrier: Mapping[str, Any], carrier_ref: str, budget: int) -> Session:
    """Start a carrier at its initial state and hand back a handle that reveals nothing else."""
    validated = carrier if carrier.get("schema") == SCHEMA else validate_carrier(carrier)
    state = {"current": initial_state(validated)}
    frozen_meta = meta_channel(validated)

    def send(request: str) -> str:
        decoded = decode_request(validated, request)
        if decoded is None:
            return encode_response(
                validated,
                {"accepted": False, "error": MALFORMED_REQUEST, "state": state["current"]},
            )
        name, argument = decoded
        outcome = step(validated, state["current"], name, argument)
        if outcome["accepted"]:
            state["current"] = outcome["state"]
        return encode_response(validated, outcome)

    def describe() -> dict[str, Any]:
        return json.loads(canonical_json(frozen_meta))

    return Session(carrier_ref, send, describe, int(budget))


# ----------------------------------------------------------------------------------------
# The exact reachable set, by fixed point rather than by a bound somebody guessed.
# ----------------------------------------------------------------------------------------

EXPLORATION_CEILING = 4096


def reachable_states(
    carrier: Mapping[str, Any], ceiling: int = EXPLORATION_CEILING
) -> dict[str, Any]:
    """Breadth-first closure of the transition relation, run to a genuine fixed point.

    M112's `P5` recorded what happens when a bound is inherited from an empirical observation: seven
    expression nodes closed the image on 1 160 project-generated worlds and did not close it on the
    first blind one. So no bound is asserted here. The frontier is expanded until it is empty, and
    the certificate records the iteration at which growth stopped. ``ceiling`` is a termination
    guarantee against a hostile payload, not an operating parameter: a carrier that reaches it is
    **non-qualifying** under a rule frozen before any carrier existed, and is never re-run at a
    larger ceiling.

    The meta-schema makes saturation impossible in fact -- four cells of at most four values bound
    the whole state space at 256 -- which is the point. The ceiling exists so that the guarantee is
    structural rather than a property of the numbers that happened to be chosen.
    """
    start = initial_state(carrier)
    alphabet = action_alphabet(carrier)
    depth: dict[tuple[int, ...], int] = {start: 0}
    predecessor: dict[tuple[int, ...], tuple[str, int, tuple[int, ...]] | None] = {start: None}
    frontier = [start]
    iterations = 0
    saturated = False
    while frontier and not saturated:
        iterations += 1
        following: list[tuple[int, ...]] = []
        for current in frontier:
            for name, argument in alphabet:
                outcome = step(carrier, current, name, argument)
                if not outcome["accepted"]:
                    continue
                nxt = outcome["state"]
                if nxt in depth:
                    continue
                if len(depth) >= ceiling:
                    saturated = True
                    break
                depth[nxt] = iterations
                predecessor[nxt] = (name, argument, current)
                following.append(nxt)
            if saturated:
                break
        frontier = following
    return {
        "schema": "mira-blind-carrier-reachability-v1",
        "closed": not saturated,
        "saturated_at_ceiling": saturated,
        "ceiling": int(ceiling),
        "iterations": iterations,
        "state_count": len(depth),
        "max_depth": max(depth.values()) if depth else 0,
        "depth": depth,
        "predecessor": predecessor,
    }


def witness_sequence(
    reachability: Mapping[str, Any], state: tuple[int, ...]
) -> list[tuple[str, int]] | None:
    """The canonical shortest request sequence reaching a state, read off the BFS tree."""
    predecessor = reachability["predecessor"]
    if state not in predecessor:
        return None
    path: list[tuple[str, int]] = []
    current = state
    while predecessor[current] is not None:
        name, argument, previous = predecessor[current]
        path.append((name, argument))
        current = previous
    path.reverse()
    return path


def _unreachable_observations(
    sizes: Sequence[int], reachable: set[tuple[int, ...]]
) -> list[tuple[int, ...]]:
    found: list[tuple[int, ...]] = []
    stack: list[tuple[int, ...]] = [()]
    while stack:
        prefix = stack.pop()
        if len(prefix) == len(sizes):
            if prefix not in reachable:
                found.append(prefix)
            continue
        for value in reversed(range(sizes[len(prefix)])):
            stack.append(prefix + (value,))
    return sorted(found)


def observation_closure(
    carrier: Mapping[str, Any], ceiling: int = EXPLORATION_CEILING
) -> dict[str, Any]:
    """The reachable observations, and the observations the carrier structurally cannot show.

    The unreachable set is what makes an incompatible demand *structural*. It is not a task phrased
    so that a careful reader gives up: it is a value tuple over the carrier's own observable cells
    that no request sequence of any length can produce, established by exhausting the state space.
    """
    reachability = reachable_states(carrier, ceiling)
    reachable: dict[tuple[int, ...], tuple[int, ...]] = {}
    ordered = sorted(reachability["depth"].items(), key=lambda item: (item[1], item[0]))
    for state, _depth in ordered:
        reachable.setdefault(observation(carrier, state), state)
    depth_of_observation = {}
    for state, value in ordered:
        depth_of_observation.setdefault(observation(carrier, state), value)
    sizes = [int(item["size"]) for item, shown in zip(carrier["cells"], carrier["visible"]) if shown]
    total = 1
    for size in sizes:
        total *= size
    return {
        "schema": "mira-blind-carrier-observation-closure-v1",
        "closed": reachability["closed"],
        "iterations": reachability["iterations"],
        "state_count": reachability["state_count"],
        "max_depth": reachability["max_depth"],
        "observation_space_size": total,
        "reachable_observations": sorted(reachable),
        "unreachable_observations": _unreachable_observations(sizes, set(reachable)),
        "reachable_representatives": {key: reachable[key] for key in sorted(reachable)},
        "observation_depth": depth_of_observation,
        "reachability": reachability,
    }


def carrier_facts(carrier: Mapping[str, Any]) -> dict[str, Any]:
    """A structural summary. Used by validators and audits; never handed to a learner."""
    validated = carrier if carrier.get("schema") == SCHEMA else validate_carrier(carrier)
    return {
        "carrier_digest": validated["carrier_digest"],
        "surface_kind": validated["surface"]["kind"],
        "cell_count": len(validated["cells"]),
        "latent_cell_count": sum(1 for shown in validated["visible"] if not shown),
        "action_count": len(validated["actions"]),
        "guarded_action_count": sum(1 for item in validated["actions"] if item["guard"]),
        "unary_action_count": sum(1 for item in validated["actions"] if item["arity"] == 1),
        "error_count": len(validated["errors"]),
        "alphabet_size": len(action_alphabet(validated)),
    }


def structural_signature(carrier: Mapping[str, Any]) -> str:
    """Identity for de-duplication that ignores names and tokens.

    Two carriers that differ only by renaming are the same experiment twice. The prompt asks the
    emitter not to repeat itself; this is what measures whether it did.
    """
    validated = carrier if carrier.get("schema") == SCHEMA else validate_carrier(carrier)
    skeleton = {
        "surface_kind": validated["surface"]["kind"],
        "cells": [item["size"] for item in validated["cells"]],
        "initial": list(validated["initial"]),
        "visible": list(validated["visible"]),
        "error_count": len(validated["errors"]),
        "actions": [
            {
                "arity": item["arity"],
                "arg_size": item["arg_size"],
                "guard": item["guard"],
                "effect": item["effect"],
                "error_index": validated["errors"].index(item["error"]),
            }
            for item in validated["actions"]
        ],
    }
    return digest(skeleton)
