"""A deterministic stand-in for the blind generator, able to emit development payloads only.

`blind_bank_devkit` exists so the M075-B chain could be driven end to end without a model and
without writing anything into the repository. This is the same idea for the carrier meta-schema, and
it has one job beyond exercising the pipeline: **measuring a base rate before the plan is frozen**.

M112's analysis plan could set a minimum stratum size that was both reachable and refusable because
the project had measured the relevant rates over 1 160 of its own worlds. Nothing comparable exists
for carriers, because carriers of this kind have never been generated before. So the devkit emits a
large sample under the same meta-schema, the frozen qualification rule is run over it, and the rate
that comes out is what the plan's minimum is judged against.

That rate is **not a prediction about the model**, and the plan must not be read as one. M112
measured a six per cent ambiguous rate over project-generated worlds and the blind bank returned
twenty-five per cent. A pseudo-random emitter's distribution is a different distribution again. What
the measurement buys is only this: a minimum that a plausible emitter can both meet and miss, fixed
before any real payload exists.

Every payload this module produces carries the development schema. `m113_carrier_bank` refuses a
development payload wherever a qualifying one is required, so a devkit sample can never be mistaken
for a materialization.
"""

from __future__ import annotations

import hashlib
from typing import Any

from metamorphosis import carrier_host as host

DEVELOPMENT_PAYLOAD_SCHEMA = "m113-blind-carrier-payload-development-v1"

_CELL_NAMES = (
    "gate", "level", "phase", "slot", "mark", "depth", "token", "index",
    "flag", "count", "mode", "step", "port", "lane", "cursor", "epoch",
)
_ACTION_NAMES = (
    "open", "close", "push", "pull", "step", "reset", "load", "store",
    "arm", "fire", "seek", "halt", "bump", "clear", "swap", "hold",
)
_ERROR_NAMES = (
    "denied", "closed", "range", "busy", "empty", "full", "stale", "bad",
)
_OK_TOKENS = ("ok", "ack", "done", "yes", "good", "pass", "hit", "up")
_ERROR_TOKENS = ("err", "nak", "fail", "no", "bad2", "miss", "down", "stop")
_KEYS = ("verb", "cmd", "call", "act", "arg", "param", "value", "operand", "st", "status", "res", "code2")


class _Stream:
    """A reproducible integer stream. Seeded by digest, so a sample is a function of its seed."""

    __slots__ = ("_buffer", "_position", "_seed", "_counter")

    def __init__(self, seed: str) -> None:
        self._seed = str(seed)
        self._counter = 0
        self._buffer = b""
        self._position = 0

    def _refill(self) -> None:
        self._buffer = hashlib.sha256(
            ("%s:%d" % (self._seed, self._counter)).encode("ascii")
        ).digest()
        self._counter += 1
        self._position = 0

    def byte(self) -> int:
        if self._position >= len(self._buffer):
            self._refill()
        value = self._buffer[self._position]
        self._position += 1
        return int(value)

    def below(self, ceiling: int) -> int:
        if ceiling <= 1:
            return 0
        return self.byte() % int(ceiling)

    def between(self, low: int, high: int) -> int:
        return low + self.below(high - low + 1)

    def choice(self, options):
        items = list(options)
        return items[self.below(len(items))]


def _distinct(stream: _Stream, pool, count: int) -> list[str]:
    items = list(pool)
    picked: list[str] = []
    for _ in range(count):
        picked.append(items.pop(stream.below(len(items))))
    return picked


def development_carrier(seed: str) -> dict[str, Any]:
    """One schema-valid carrier, chosen by the stream and by nothing that knows what it is for.

    Like the frozen prompt, this emitter is given no notion of a target, a feature, a component or
    a demand. It cannot aim, because nothing here names anything to aim at.
    """
    stream = _Stream(seed)
    cell_count = stream.between(host.MIN_CELLS, host.MAX_CELLS)
    cell_names = _distinct(stream, _CELL_NAMES, cell_count)
    cells = [
        {"name": name, "size": stream.between(host.MIN_CELL_DOMAIN, host.MAX_CELL_DOMAIN)}
        for name in cell_names
    ]
    initial = [stream.below(item["size"]) for item in cells]
    visible = [stream.below(4) != 0 for _ in cells]
    if not any(visible):
        visible[stream.below(cell_count)] = True

    error_count = stream.between(host.MIN_ERRORS, min(host.MAX_ERRORS, len(_ERROR_NAMES)))
    errors = _distinct(stream, _ERROR_NAMES, error_count)

    action_count = stream.between(host.MIN_ACTIONS, host.MAX_ACTIONS)
    action_names = _distinct(stream, _ACTION_NAMES, action_count)
    actions: list[dict[str, Any]] = []
    for name in action_names:
        arity = 1 if stream.below(2) else 0
        action: dict[str, Any] = {"name": name, "arity": arity, "error": stream.choice(errors)}
        if arity == 1:
            action["arg_size"] = stream.between(host.MIN_ARG_DOMAIN, host.MAX_ARG_DOMAIN)
        guard_count = stream.below(host.MAX_GUARD_CLAUSES + 1)
        guard = []
        for _ in range(guard_count):
            cell = stream.below(cell_count)
            guard.append(
                {
                    "cell": cell,
                    "relation": stream.choice(host.GUARD_RELATIONS),
                    "value": stream.below(cells[cell]["size"]),
                }
            )
        action["guard"] = guard
        effect = []
        for _ in range(stream.between(1, host.MAX_EFFECT_ASSIGNMENTS)):
            cell = stream.below(cell_count)
            modes = [mode for mode in host.EFFECT_MODES if mode != "arg" or arity == 1]
            mode = stream.choice(modes)
            if mode == "copy":
                operand = stream.below(cell_count)
            elif mode == "arg":
                operand = 0
            else:
                operand = stream.below(cells[cell]["size"])
            effect.append({"cell": cell, "mode": mode, "operand": operand})
        action["effect"] = effect
        actions.append(action)

    keys = _distinct(stream, _KEYS, 3)
    surface = {
        "kind": stream.choice(host.SURFACE_KINDS),
        "ok_token": stream.choice(_OK_TOKENS),
        "error_token": stream.choice(_ERROR_TOKENS),
        "field_separator": stream.choice(host.FIELD_SEPARATORS),
        "pair_separator": stream.choice(host.PAIR_SEPARATORS),
        "action_key": keys[0],
        "argument_key": keys[1],
        "status_key": keys[2],
    }
    while set(keys) & set(cell_names):
        keys = _distinct(_Stream(seed + ":rekey"), _KEYS, 3)
        surface["action_key"], surface["argument_key"], surface["status_key"] = keys

    return host.validate_carrier(
        {
            "surface": surface,
            "cells": cells,
            "initial": initial,
            "visible": visible,
            "errors": errors,
            "actions": actions,
        }
    )


def development_payload(seed: str, count: int) -> dict[str, Any]:
    """A development bank. Never a materialization, and the schema says so on every path."""
    carriers = []
    index = 0
    while len(carriers) < int(count):
        try:
            carriers.append(development_carrier("%s:%d" % (seed, index)))
        except host.CarrierError:
            pass
        index += 1
        if index > int(count) * 20:
            raise RuntimeError("the devkit could not fill a development bank from this seed")
    return {
        "schema": DEVELOPMENT_PAYLOAD_SCHEMA,
        "seed": str(seed),
        "carriers": carriers,
        "attempted": index,
    }
