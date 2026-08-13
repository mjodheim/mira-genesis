"""Materialize M088's qualifying programs in a SEPARATE process, after the constructor is adopted.

External review of PR #136 found that holding the pool as a module constant in `m088_worlds` put
every possible qualification program in the development process before `meta_search` ran, so the
recorded T8 to T9 ordering could not establish post-adoption materialization. That is the M086-A
defect — "the holdout existed as module constants before the meta-search" — recurring.

The pool therefore lives **here**, in a script the lineage never imports, and is drawn by a process
the lineage never runs. `run_m088_experiment.py` executes this as a subprocess after digesting the
adopted constructor, and reads only the artifact it writes. The development process has no access
to any qualifying program, in memory or on disk, before that point.

The artifact records the adopted constructor digest it was drawn against, so a qualification drawn
for a different constructor cannot be substituted afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

ARTIFACT_SCHEMA = "m088-qualification-v1"

# Every program uses THREE actions. The adopted constructor composes at most two, so no qualifying
# program lies inside its constructive image: the lineage cannot build one and therefore cannot run
# one. That structural guarantee is checked by `hidden_outside_constructive_image`.
QUALIFICATION_POOL: dict[str, tuple[tuple[str, ...], ...]] = {
    "stateful_protocol": (
        ("reset", "send_a", "send_b", "send_a", "observe"),
        ("reset", "send_b", "send_a", "send_b", "observe"),
        ("reset", "send_a", "send_a", "send_b", "observe"),
        ("reset", "send_b", "send_b", "send_a", "observe"),
    ),
    "path_graph": (
        ("reset", "follow_x", "follow_y", "follow_x", "observe"),
        ("reset", "follow_y", "follow_x", "follow_y", "observe"),
        ("reset", "follow_x", "follow_x", "follow_y", "observe"),
        ("reset", "follow_y", "follow_y", "follow_x", "observe"),
    ),
    "durable_service": (
        ("reset", "write", "flush", "crash", "observe"),
        ("reset", "write", "crash", "flush", "observe"),
        ("reset", "crash", "write", "flush", "observe"),
        ("reset", "flush", "write", "crash", "observe"),
    ),
}


def draw(world_id: str, salt: str, count: int = 2) -> list[list[str]]:
    pool = QUALIFICATION_POOL[world_id]
    order = sorted(
        range(len(pool)),
        key=lambda index: hashlib.sha256(
            f"m088-qualification-v1|{world_id}|{salt}|{index}".encode("utf-8")
        ).hexdigest(),
    )
    return [list(pool[index]) for index in sorted(order[:count])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salt", required=True)
    parser.add_argument(
        "--adopted-constructor-digest", required=True,
        help="binds this draw to the constructor that was adopted before it",
    )
    parser.add_argument("--worlds", required=True, help="comma-separated world identifiers")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()

    worlds = [item for item in arguments.worlds.split(",") if item]
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "salt_digest": hashlib.sha256(
            json.dumps(arguments.salt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "adopted_constructor_digest": arguments.adopted_constructor_digest,
        "materialized_by": "separate process",
        "programs": {world_id: draw(world_id, arguments.salt) for world_id in worlds},
    }
    artifact["artifact_digest"] = hashlib.sha256(
        json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    print(artifact["artifact_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
