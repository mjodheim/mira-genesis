"""Author an M111 population in two strata, from the same generator M110 used.

M110 admitted worlds whose census carried no ambiguous feature row, because an ambiguous row makes an
attribution rule underivable. M111 needs both kinds and cannot get them from one world: a pre-freeze
survey of 160 worlds measured that row-3 ambiguity and row-7 reachability never co-occur here. So the
population is declared in two strata and the lineage's record is pooled across both.

- **ambiguous worlds** - the only ambiguous base-state row is row 3, and two targets there resolve
  through different components. This is where `A` and `B` live and where competence is measured.
- **witness worlds** - row 7 is present and determined at the base state. This is what makes the
  pooled requirement inexpressible in the monotone policy language.

Both criteria mention structure only. Neither says **which** components produce the ambiguity, and
neither looks at an arm, a restored cascade or a policy. The emitted file carries worlds and nothing
else.
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

POPULATION_SCHEMA = "m111-two-stratum-population-v1"
SEED_RANGES = {"development": (2000, 2999), "canonical": (3000, 3999)}
DEFAULT_AMBIGUOUS = 3
DEFAULT_WITNESS = 2

AMBIGUOUS_ROW = 3
WITNESS_ROW = 7
DETERMINED_CONTRAST_ROW = 1


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


def classify(world: dict[str, Any]) -> dict[str, Any]:
    """Which stratum, if any, this world belongs to. Structure only."""
    survey = runtime.base_state_survey(world)
    ambiguous_reasons = []
    if survey["ambiguous_rows"] != [AMBIGUOUS_ROW]:
        ambiguous_reasons.append("the_only_ambiguous_row_is_not_the_declared_one")
    if DETERMINED_CONTRAST_ROW not in survey["determined_rows"]:
        ambiguous_reasons.append("the_determined_contrast_row_is_absent")
    pair = runtime.ambiguous_pair(world, AMBIGUOUS_ROW) if not ambiguous_reasons else None
    if not ambiguous_reasons and pair is None:
        ambiguous_reasons.append("no_two_targets_at_the_ambiguous_row_differ_in_component")

    witness_reasons = []
    if WITNESS_ROW not in survey["determined_rows"]:
        witness_reasons.append("the_witness_row_is_not_present_and_determined")
    if survey["ambiguous_rows"]:
        witness_reasons.append("a_witness_world_must_carry_no_ambiguous_row")

    return {
        "world_id": world["world_id"],
        "rows": survey["rows"],
        "ambiguous_rows": survey["ambiguous_rows"],
        "determined_rows": survey["determined_rows"],
        "is_ambiguous_world": not ambiguous_reasons,
        "is_witness_world": not witness_reasons,
        "ambiguous_reasons": ambiguous_reasons,
        "witness_reasons": witness_reasons,
    }


def author(tag: str, ambiguous: int, witness: int, limit: int) -> dict[str, Any]:
    if tag not in SEED_RANGES:
        raise SystemExit("M111 population tag is outside the declared ranges")
    low, high = SEED_RANGES[tag]
    ambiguous_worlds: list[dict[str, Any]] = []
    witness_worlds: list[dict[str, Any]] = []
    log: list[dict[str, Any]] = []
    for seed in range(low, min(low + limit, high + 1)):
        world = generate_world(tag, seed)
        decision = classify(world)
        log.append(decision)
        if decision["is_ambiguous_world"] and len(ambiguous_worlds) < ambiguous:
            ambiguous_worlds.append(world)
        elif decision["is_witness_world"] and len(witness_worlds) < witness:
            witness_worlds.append(world)
        if len(ambiguous_worlds) == ambiguous and len(witness_worlds) == witness:
            break
    if len(ambiguous_worlds) != ambiguous or len(witness_worlds) != witness:
        raise SystemExit(
            "M111 population could not be filled inside the declared seed budget: %d/%d ambiguous, "
            "%d/%d witness" % (len(ambiguous_worlds), ambiguous, len(witness_worlds), witness)
        )
    payload = {
        "schema": POPULATION_SCHEMA,
        "tag": tag,
        "seed_range": [low, high],
        "document_count": consumer.DOCUMENT_COUNT,
        "value_chain": list(consumer.VALUES),
        "ambiguous_row": AMBIGUOUS_ROW,
        "witness_row": WITNESS_ROW,
        "ambiguous_worlds": ambiguous_worlds,
        "witness_worlds": witness_worlds,
    }
    payload["population_digest"] = consumer.digest(payload)
    return {"population": payload, "admission_log": log}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, choices=sorted(SEED_RANGES))
    parser.add_argument("--ambiguous", type=int, default=DEFAULT_AMBIGUOUS)
    parser.add_argument("--witness", type=int, default=DEFAULT_WITNESS)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--out", required=True)
    parser.add_argument("--log")
    arguments = parser.parse_args()
    authored = author(arguments.tag, arguments.ambiguous, arguments.witness, arguments.limit)
    destination = Path(arguments.out)
    with destination.open("xb") as handle:
        handle.write(consumer.canonical_json(authored["population"]).encode("ascii"))
    if arguments.log:
        Path(arguments.log).write_bytes(
            consumer.canonical_json(
                {
                    "schema": "m111-admission-log-v1",
                    "tag": arguments.tag,
                    "entries": authored["admission_log"],
                }
            ).encode("ascii")
        )
    print(
        json.dumps(
            {
                "tag": arguments.tag,
                "path": str(destination),
                "ambiguous_worlds": len(authored["population"]["ambiguous_worlds"]),
                "witness_worlds": len(authored["population"]["witness_worlds"]),
                "seeds_examined": len(authored["admission_log"]),
                "population_digest": authored["population"]["population_digest"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
