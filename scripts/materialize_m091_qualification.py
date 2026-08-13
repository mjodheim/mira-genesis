"""Materialize M091's qualifying worlds in a SEPARATE process, after the language is frozen.

Nothing under `metamorphosis/` imports this file, and the anti-leak scan checks that from the
import graph rather than by assertion. That boundary is not decoration: D053 disqualified M086-A
partly because its holdout existed as module constants before the meta-search ran, and PR #136
found the same shape in M088's first draft.

A world is data in the schema `metamorphosis.m091_worlds` interprets. No world names an operation,
a primitive, a body or a program. Each states a situation, what the finished transformation must
achieve, and what being right means in that situation's own terms — a level that may not go
negative, a region where the plan must track its input, a region where it must be pinned.

The two families are materially different from each other and from development. Development
rectifies a data-flow channel. `capacity_planning` is a dispatch plan over shifts with a floor at
no allocation and a per-shift multiplier. `protocol_window` is deficit accounting on a link, whose
requirement is the **dual** clamp: a ceiling rather than a floor, which the lineage can only reach
by conjugating its new operation with the inherited sign flip. Same primitive, same semantics
digest, a construction it has never built.

Which variant of each family is drawn, and which held-out instances come with it, is decided by a
salt the caller derives from the extended language's own digest — a value that does not exist
until the primitive has been adopted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ARTIFACT_SCHEMA = "m091-qualification-v1"

HIDDEN_DRAW = 5

CAPACITY_PLANNING: tuple[dict[str, object], ...] = (
    {
        "world_id": "q_capacity_shift_plan",
        "family": "capacity_planning",
        "narrative": (
            "A depot plans dispatch for the coming shifts. The projected surplus is what remains "
            "after committed orders are met, and it may be negative when the depot is already "
            "over-committed. A negative surplus is not a negative dispatch: it releases nothing. "
            "Each unit of genuine surplus is dispatched once per shift, and the plan runs two "
            "shifts, so the released quantity is twice the surplus that actually exists."
        ),
        "input_names": ["reserve", "surplus", "shifts"],
        "requirements": [
            {"slot": 2, "expression": ["double", ["max", ["input", 1], ["const", 0]]]},
        ],
        "invariants": [
            {"kind": "never_below", "slot": 2, "bound": 0},
            {"kind": "matches_requirement", "slot": 2},
            {"kind": "tracks_input_when", "slot": 2, "input": 1,
             "when": "at_or_above", "threshold": 0, "scale": 2},
            {"kind": "pinned_when", "slot": 2, "input": 1,
             "when": "below", "threshold": 0, "value": 0},
        ],
        "public_instances": [
            {"payload": {"reserve": 3, "surplus": -5, "shifts": 2}, "inputs": [3, -5, 2]},
            {"payload": {"reserve": -2, "surplus": -1, "shifts": 4}, "inputs": [-2, -1, 4]},
            {"payload": {"reserve": 0, "surplus": 0, "shifts": 1}, "inputs": [0, 0, 1]},
            {"payload": {"reserve": 7, "surplus": 2, "shifts": -3}, "inputs": [7, 2, -3]},
            {"payload": {"reserve": -6, "surplus": 7, "shifts": 5}, "inputs": [-6, 7, 5]},
        ],
        "hidden_pool": [
            {"instance_id": "h1", "inputs": [1, -9, 0]},
            {"instance_id": "h2", "inputs": [-4, -2, 6]},
            {"instance_id": "h3", "inputs": [8, -1, -1]},
            {"instance_id": "h4", "inputs": [0, 1, 3]},
            {"instance_id": "h5", "inputs": [5, 4, -2]},
            {"instance_id": "h6", "inputs": [-7, 11, 2]},
            {"instance_id": "h7", "inputs": [2, 0, 9]},
            {"instance_id": "h8", "inputs": [-3, 6, -5]},
        ],
    },
    {
        "world_id": "q_capacity_relief_plan",
        "family": "capacity_planning",
        "narrative": (
            "A relief depot plans releases against a headroom figure that is negative whenever the "
            "depot is already drawing on its reserve. Drawing on the reserve releases nothing, and "
            "genuine headroom is released twice over the planning window."
        ),
        "input_names": ["headroom", "committed", "window"],
        "requirements": [
            {"slot": 1, "expression": ["double", ["max", ["input", 0], ["const", 0]]]},
        ],
        "invariants": [
            {"kind": "never_below", "slot": 1, "bound": 0},
            {"kind": "matches_requirement", "slot": 1},
            {"kind": "tracks_input_when", "slot": 1, "input": 0,
             "when": "at_or_above", "threshold": 0, "scale": 2},
            {"kind": "pinned_when", "slot": 1, "input": 0,
             "when": "below", "threshold": 0, "value": 0},
        ],
        "public_instances": [
            {"payload": {"headroom": -5, "committed": 3, "window": 2}, "inputs": [-5, 3, 2]},
            {"payload": {"headroom": -1, "committed": -2, "window": 4}, "inputs": [-1, -2, 4]},
            {"payload": {"headroom": 0, "committed": 0, "window": 1}, "inputs": [0, 0, 1]},
            {"payload": {"headroom": 2, "committed": 7, "window": -3}, "inputs": [2, 7, -3]},
            {"payload": {"headroom": 7, "committed": -6, "window": 5}, "inputs": [7, -6, 5]},
        ],
        "hidden_pool": [
            {"instance_id": "h1", "inputs": [-9, 1, 0]},
            {"instance_id": "h2", "inputs": [-2, -4, 6]},
            {"instance_id": "h3", "inputs": [-1, 8, -1]},
            {"instance_id": "h4", "inputs": [1, 0, 3]},
            {"instance_id": "h5", "inputs": [4, 5, -2]},
            {"instance_id": "h6", "inputs": [11, -7, 2]},
            {"instance_id": "h7", "inputs": [0, 2, 9]},
            {"instance_id": "h8", "inputs": [6, -3, -5]},
        ],
    },
    {
        "world_id": "q_capacity_yard_plan",
        "family": "capacity_planning",
        "narrative": (
            "A yard plans movements against a spare-capacity figure. Spare capacity below zero "
            "means the yard is oversubscribed and no movement may be planned; spare capacity is "
            "otherwise worked twice, once inbound and once outbound."
        ),
        "input_names": ["spare", "inbound", "outbound"],
        "requirements": [
            {"slot": 3, "expression": ["double", ["max", ["input", 2], ["const", 0]]]},
        ],
        "invariants": [
            {"kind": "never_below", "slot": 3, "bound": 0},
            {"kind": "matches_requirement", "slot": 3},
            {"kind": "tracks_input_when", "slot": 3, "input": 2,
             "when": "at_or_above", "threshold": 0, "scale": 2},
            {"kind": "pinned_when", "slot": 3, "input": 2,
             "when": "below", "threshold": 0, "value": 0},
        ],
        "public_instances": [
            {"payload": {"spare": 3, "inbound": 2, "outbound": -5}, "inputs": [3, 2, -5]},
            {"payload": {"spare": -2, "inbound": 4, "outbound": -1}, "inputs": [-2, 4, -1]},
            {"payload": {"spare": 0, "inbound": 1, "outbound": 0}, "inputs": [0, 1, 0]},
            {"payload": {"spare": 7, "inbound": -3, "outbound": 2}, "inputs": [7, -3, 2]},
            {"payload": {"spare": -6, "inbound": 5, "outbound": 7}, "inputs": [-6, 5, 7]},
        ],
        "hidden_pool": [
            {"instance_id": "h1", "inputs": [1, 0, -9]},
            {"instance_id": "h2", "inputs": [-4, 6, -2]},
            {"instance_id": "h3", "inputs": [8, -1, -1]},
            {"instance_id": "h4", "inputs": [0, 3, 1]},
            {"instance_id": "h5", "inputs": [5, -2, 4]},
            {"instance_id": "h6", "inputs": [-7, 2, 11]},
            {"instance_id": "h7", "inputs": [2, 9, 0]},
            {"instance_id": "h8", "inputs": [-3, -5, 6]},
        ],
    },
)

PROTOCOL_WINDOW: tuple[dict[str, object], ...] = (
    {
        "world_id": "q_protocol_link_deficit",
        "family": "protocol_window",
        "narrative": (
            "A receiver advertises a credit window to its sender. The credit figure goes negative "
            "when the sender has already been allowed more than the receiver can now absorb. The "
            "link's ledger records the **deficit** — the part of the credit that is missing — as a "
            "non-positive entry, so that a chain of links can be totalled by adding entries. Where "
            "credit is available the ledger entry is nothing at all; where it is not, the entry is "
            "the shortfall itself. The ledger may never record a positive figure: a surplus of "
            "credit is not a debt owed to the link."
        ),
        "input_names": ["hops", "ceiling", "credit"],
        "requirements": [
            {"slot": 3, "expression": ["min", ["input", 2], ["const", 0]]},
        ],
        "invariants": [
            {"kind": "never_above", "slot": 3, "bound": 0},
            {"kind": "matches_requirement", "slot": 3},
            {"kind": "tracks_input_when", "slot": 3, "input": 2,
             "when": "below", "threshold": 0, "scale": 1},
            {"kind": "pinned_when", "slot": 3, "input": 2,
             "when": "at_or_above", "threshold": 0, "value": 0},
        ],
        "public_instances": [
            {"payload": {"hops": 2, "ceiling": 5, "credit": -7}, "inputs": [2, 5, -7]},
            {"payload": {"hops": 4, "ceiling": 0, "credit": -2}, "inputs": [4, 0, -2]},
            {"payload": {"hops": 1, "ceiling": 3, "credit": 0}, "inputs": [1, 3, 0]},
            {"payload": {"hops": 3, "ceiling": -1, "credit": 4}, "inputs": [3, -1, 4]},
            {"payload": {"hops": 5, "ceiling": 2, "credit": 9}, "inputs": [5, 2, 9]},
        ],
        "hidden_pool": [
            {"instance_id": "h1", "inputs": [0, 1, -11]},
            {"instance_id": "h2", "inputs": [6, -4, -3]},
            {"instance_id": "h3", "inputs": [-1, 8, -1]},
            {"instance_id": "h4", "inputs": [3, 0, 1]},
            {"instance_id": "h5", "inputs": [-2, 5, 6]},
            {"instance_id": "h6", "inputs": [2, -7, 12]},
            {"instance_id": "h7", "inputs": [9, 2, 0]},
            {"instance_id": "h8", "inputs": [-5, -3, -8]},
        ],
    },
    {
        "world_id": "q_protocol_hop_deficit",
        "family": "protocol_window",
        "narrative": (
            "An intermediate hop keeps the same ledger against its own residual allowance. Where "
            "allowance remains the hop owes nothing; where it has been overrun the ledger carries "
            "the overrun as a non-positive entry, and may never carry a positive one."
        ),
        "input_names": ["allowance", "queued", "priority"],
        "requirements": [
            {"slot": 0, "expression": ["min", ["input", 0], ["const", 0]]},
        ],
        "invariants": [
            {"kind": "never_above", "slot": 0, "bound": 0},
            {"kind": "matches_requirement", "slot": 0},
            {"kind": "tracks_input_when", "slot": 0, "input": 0,
             "when": "below", "threshold": 0, "scale": 1},
            {"kind": "pinned_when", "slot": 0, "input": 0,
             "when": "at_or_above", "threshold": 0, "value": 0},
        ],
        "public_instances": [
            {"payload": {"allowance": -7, "queued": 2, "priority": 5}, "inputs": [-7, 2, 5]},
            {"payload": {"allowance": -2, "queued": 4, "priority": 0}, "inputs": [-2, 4, 0]},
            {"payload": {"allowance": 0, "queued": 1, "priority": 3}, "inputs": [0, 1, 3]},
            {"payload": {"allowance": 4, "queued": 3, "priority": -1}, "inputs": [4, 3, -1]},
            {"payload": {"allowance": 9, "queued": 5, "priority": 2}, "inputs": [9, 5, 2]},
        ],
        "hidden_pool": [
            {"instance_id": "h1", "inputs": [-11, 0, 1]},
            {"instance_id": "h2", "inputs": [-3, 6, -4]},
            {"instance_id": "h3", "inputs": [-1, -1, 8]},
            {"instance_id": "h4", "inputs": [1, 3, 0]},
            {"instance_id": "h5", "inputs": [6, -2, 5]},
            {"instance_id": "h6", "inputs": [12, 2, -7]},
            {"instance_id": "h7", "inputs": [0, 9, 2]},
            {"instance_id": "h8", "inputs": [-8, -5, -3]},
        ],
    },
    {
        "world_id": "q_protocol_edge_deficit",
        "family": "protocol_window",
        "narrative": (
            "An edge router keeps the ledger against its advertised headroom, which goes negative "
            "under burst. The recorded entry is the shortfall where there is one and nothing "
            "otherwise, and is never positive."
        ),
        "input_names": ["burst", "headroom", "route"],
        "requirements": [
            {"slot": 2, "expression": ["min", ["input", 1], ["const", 0]]},
        ],
        "invariants": [
            {"kind": "never_above", "slot": 2, "bound": 0},
            {"kind": "matches_requirement", "slot": 2},
            {"kind": "tracks_input_when", "slot": 2, "input": 1,
             "when": "below", "threshold": 0, "scale": 1},
            {"kind": "pinned_when", "slot": 2, "input": 1,
             "when": "at_or_above", "threshold": 0, "value": 0},
        ],
        "public_instances": [
            {"payload": {"burst": 2, "headroom": -7, "route": 5}, "inputs": [2, -7, 5]},
            {"payload": {"burst": 4, "headroom": -2, "route": 0}, "inputs": [4, -2, 0]},
            {"payload": {"burst": 1, "headroom": 0, "route": 3}, "inputs": [1, 0, 3]},
            {"payload": {"burst": 3, "headroom": 4, "route": -1}, "inputs": [3, 4, -1]},
            {"payload": {"burst": 5, "headroom": 9, "route": 2}, "inputs": [5, 9, 2]},
        ],
        "hidden_pool": [
            {"instance_id": "h1", "inputs": [0, -11, 1]},
            {"instance_id": "h2", "inputs": [6, -3, -4]},
            {"instance_id": "h3", "inputs": [-1, -1, 8]},
            {"instance_id": "h4", "inputs": [3, 1, 0]},
            {"instance_id": "h5", "inputs": [-2, 6, 5]},
            {"instance_id": "h6", "inputs": [2, 12, -7]},
            {"instance_id": "h7", "inputs": [9, 0, 2]},
            {"instance_id": "h8", "inputs": [-5, -8, -3]},
        ],
    },
)

POOL: dict[str, tuple[dict[str, object], ...]] = {
    "capacity_planning": CAPACITY_PLANNING,
    "protocol_window": PROTOCOL_WINDOW,
}


def _order(items: int, salt: str, tag: str) -> list[int]:
    return sorted(
        range(items),
        key=lambda index: hashlib.sha256(
            f"{ARTIFACT_SCHEMA}|{tag}|{salt}|{index}".encode("utf-8")
        ).hexdigest(),
    )


def materialize(salt: str, language_digest: str) -> dict[str, object]:
    worlds: list[dict[str, object]] = []
    for family, pool in sorted(POOL.items()):
        chosen = dict(pool[_order(len(pool), salt, family)[0]])
        hidden_pool = list(chosen.pop("hidden_pool"))  # type: ignore[arg-type]
        drawn = sorted(_order(len(hidden_pool), salt, f"{family}|hidden")[:HIDDEN_DRAW])
        chosen["hidden_instances"] = [hidden_pool[index] for index in drawn]
        worlds.append(chosen)
    artifact: dict[str, object] = {
        "schema": ARTIFACT_SCHEMA,
        "salt_digest": hashlib.sha256(salt.encode("utf-8")).hexdigest(),
        "extended_language_digest": language_digest,
        "materialized_by": "a separate process, after the extended language was frozen",
        "families": sorted(POOL),
        "pool_sizes": {family: len(pool) for family, pool in sorted(POOL.items())},
        "hidden_drawn_per_world": HIDDEN_DRAW,
        "worlds": worlds,
    }
    artifact["artifact_digest"] = hashlib.sha256(
        json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--language-digest", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()

    artifact = materialize(arguments.salt, arguments.language_digest)
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    print(artifact["artifact_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
