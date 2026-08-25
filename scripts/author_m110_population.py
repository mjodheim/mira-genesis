"""Author an M110 consumer population from a declared deterministic generator.

A world is admitted on **structure only**. The criterion never mentions an arm, a restored rule or a
row label, so the row -> component map the canonical run measures is not a property this script
selected for. The emitted file carries the worlds and nothing else: no census, no label, no canonical
target, no digest of the producer. Everything an arm needs is recomputed inside its capsule.

Development and canonical populations are drawn from disjoint declared seed ranges.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m110_runtime as runtime  # noqa: E402

POPULATION_SCHEMA = runtime.POPULATION_SCHEMA
SEED_RANGES = {"development": (0, 999), "canonical": (1000, 1999)}
DEFAULT_COUNT = 6

# The rows the criterion requires to be present with a determined label at the base state. Which
# component each of them resolves to is measured later and is not required here.
REQUIRED_ROWS = (3, 5, 7)


def generate_world(tag: str, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    documents = []
    side: dict[str, Any] = {}
    for index in range(runtime.DOCUMENT_COUNT):
        key = "k%d" % index
        document = {field: rng.choice(runtime.VALUES) for field in runtime.VISIBLE_FIELDS}
        document[runtime.REFERENCE_FIELD] = key
        documents.append(document)
        side[key] = {"zeta": rng.choice(runtime.VALUES), "note": "n%d" % index}
    return runtime.consumer_world("%s-%04d" % (tag, seed), documents, side)


def admit(world: dict[str, Any]) -> dict[str, Any]:
    """Structure only. No label, no arm, no restored rule is consulted."""
    census = runtime.attribution_census(world)
    reasons = []
    if not census["census_complete"]:
        reasons.append("census_incomplete")
    if census["ambiguous_rows"]:
        reasons.append("ambiguous_rows_present")
    missing = [row for row in REQUIRED_ROWS if str(row) not in census["canonical_targets"]]
    if missing:
        reasons.append("required_rows_absent_at_base_state")
    return {
        "world_id": world["world_id"],
        "admitted": not reasons,
        "reasons": reasons,
        "rows": census["rows"],
        "ambiguous_row_count": len(census["ambiguous_rows"]),
        "missing_required_rows": missing,
    }


def author(tag: str, count: int, limit: int) -> dict[str, Any]:
    if tag not in SEED_RANGES:
        raise SystemExit("M110 population tag is outside the declared ranges")
    low, high = SEED_RANGES[tag]
    worlds: list[dict[str, Any]] = []
    log: list[dict[str, Any]] = []
    for seed in range(low, min(low + limit, high + 1)):
        world = generate_world(tag, seed)
        decision = admit(world)
        log.append(decision)
        if decision["admitted"]:
            worlds.append(world)
        if len(worlds) == count:
            break
    if len(worlds) != count:
        raise SystemExit("M110 population could not be filled inside the declared seed budget")
    payload = {
        "schema": POPULATION_SCHEMA,
        "tag": tag,
        "seed_range": [low, high],
        "document_count": runtime.DOCUMENT_COUNT,
        "value_chain": list(runtime.VALUES),
        "visible_fields": list(runtime.VISIBLE_FIELDS),
        "required_rows": list(REQUIRED_ROWS),
        "worlds": worlds,
    }
    payload["population_digest"] = runtime.digest(payload)
    return {"population": payload, "admission_log": log}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, choices=sorted(SEED_RANGES))
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--out", required=True)
    parser.add_argument("--log")
    arguments = parser.parse_args()
    authored = author(arguments.tag, arguments.count, arguments.limit)
    destination = Path(arguments.out)
    raw = runtime.canonical_json(authored["population"]).encode("ascii")
    with destination.open("xb") as handle:
        handle.write(raw)
    if arguments.log:
        Path(arguments.log).write_bytes(
            runtime.canonical_json(
                {"schema": "m110-admission-log-v1", "tag": arguments.tag,
                 "entries": authored["admission_log"]}
            ).encode("ascii")
        )
    print(
        json.dumps(
            {
                "tag": arguments.tag,
                "path": str(destination),
                "world_count": len(authored["population"]["worlds"]),
                "seeds_examined": len(authored["admission_log"]),
                "population_digest": authored["population"]["population_digest"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
