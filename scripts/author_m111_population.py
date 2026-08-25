"""Author an M111 consumer population of **ambiguous** worlds.

M110 admitted worlds whose census carried no ambiguous feature row, because an ambiguous row makes an
attribution rule underivable. M111 studies exactly the worlds M110 excluded: the criterion here is the
complement of the criterion there, drawn from the same generator, over a disjoint seed range.

A world is admitted on structure only. The criterion says that one feature row resolves through more
than one component and that the other reachable rows do not. It never says **which** components, and
it never looks at an arm, a restored cascade or a policy. The emitted file carries worlds and nothing
else; everything an arm needs is recomputed inside its capsule.
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

from metamorphosis import m110_runtime as consumer  # noqa: E402
from metamorphosis import m111_runtime as runtime  # noqa: E402

POPULATION_SCHEMA = "m111-ambiguous-population-v1"
SEED_RANGES = {"development": (2000, 2999), "canonical": (3000, 3999)}
DEFAULT_COUNT = 5

# The row the criterion requires to be undetermined, and the rows it requires to be determined. Which
# components any of them resolve through is measured later and is never required here.
AMBIGUOUS_ROW = 3
DETERMINED_ROWS = (1, 7)


def generate_world(tag: str, seed: int) -> dict[str, Any]:
    """The same generator M110 used, over a disjoint seed range."""
    rng = random.Random(seed)
    documents = []
    side: dict[str, Any] = {}
    for index in range(consumer.DOCUMENT_COUNT):
        key = "k%d" % index
        document = {field: rng.choice(consumer.VALUES) for field in consumer.VISIBLE_FIELDS}
        document[consumer.REFERENCE_FIELD] = key
        documents.append(document)
        side[key] = {"zeta": rng.choice(consumer.VALUES), "note": "n%d" % index}
    return consumer.consumer_world("%s-%04d" % (tag, seed), documents, side)


def admit(world: dict[str, Any]) -> dict[str, Any]:
    """Structure only. Ambiguity is required; which components produce it is not.

    Row 7 is required because it is what the expressibility lemma needs: row 3 lies below row 7
    componentwise, so a record holding both is what forces a policy out of the monotone language. A
    record holding only rows 1 and 3 would be satisfiable monotonically and would test nothing.
    """
    survey = runtime.base_state_survey(world)
    reasons = []
    if survey["ambiguous_rows"] != [AMBIGUOUS_ROW]:
        reasons.append("the_ambiguous_row_is_not_the_declared_one")
    missing = [row for row in DETERMINED_ROWS if row not in survey["determined_rows"]]
    if missing:
        reasons.append("required_determined_rows_absent_at_base_state")
    pair = runtime.ambiguous_pair(world, AMBIGUOUS_ROW) if not reasons else None
    if not reasons and pair is None:
        reasons.append("no_two_targets_at_the_ambiguous_row_differ_in_component")
    return {
        "world_id": world["world_id"],
        "admitted": not reasons,
        "reasons": reasons,
        "rows": survey["rows"],
        "ambiguous_rows": survey["ambiguous_rows"],
        "missing_determined_rows": missing,
    }


def author(tag: str, count: int, limit: int) -> dict[str, Any]:
    if tag not in SEED_RANGES:
        raise SystemExit("M111 population tag is outside the declared ranges")
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
        raise SystemExit("M111 population could not be filled inside the declared seed budget")
    payload = {
        "schema": POPULATION_SCHEMA,
        "tag": tag,
        "seed_range": [low, high],
        "document_count": consumer.DOCUMENT_COUNT,
        "value_chain": list(consumer.VALUES),
        "ambiguous_row": AMBIGUOUS_ROW,
        "determined_rows": list(DETERMINED_ROWS),
        "worlds": worlds,
    }
    payload["population_digest"] = consumer.digest(payload)
    return {"population": payload, "admission_log": log}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, choices=sorted(SEED_RANGES))
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--out", required=True)
    parser.add_argument("--log")
    arguments = parser.parse_args()
    authored = author(arguments.tag, arguments.count, arguments.limit)
    destination = Path(arguments.out)
    with destination.open("xb") as handle:
        handle.write(consumer.canonical_json(authored["population"]).encode("ascii"))
    if arguments.log:
        Path(arguments.log).write_bytes(
            consumer.canonical_json(
                {"schema": "m111-admission-log-v1", "tag": arguments.tag,
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
