"""Materialize and bind the frozen G2 episode suite as an immutable artifact.

The suite is derived only from the committed salt, family grammar and deterministic index. It is
written once and bound by digest before any arm result is recorded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m076_multimodal_grounding import (  # noqa: E402
    EPISODES_PER_FAMILY,
    FAMILIES,
    GENERATOR_VERSION,
    RASTER_BYTES,
    materialize_suite,
)

PROTOCOL_PATH = ROOT / "experiments/M076/PROTOCOL.json"
COMMITMENT_PATH = ROOT / "experiments/M076/EPISODE_COMMITMENT.json"


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    generation = protocol["episode_generation"]
    if generation["generator_version"] != GENERATOR_VERSION:
        raise SystemExit("generator version drifted from the frozen protocol")
    salt = bytes.fromhex(generation["salt_hex"])

    suite = materialize_suite(salt)
    if len(suite) != generation["episode_count"]:
        raise SystemExit("materialized episode count drifted from the frozen protocol")

    records = []
    for episode in suite:
        if len(episode.raster) != RASTER_BYTES:
            raise SystemExit(f"episode {episode.family}/{episode.index} raster length drifted")
        records.append({
            "family": episode.family,
            "index": episode.index,
            "selection_digest": episode.selection_digest,
            "commitment": episode.commitment(),
            "raster_sha256": hashlib.sha256(episode.raster).hexdigest(),
            "instruction_token_count": len(episode.instruction.split()),
            "structured_keys": list(episode.structured),
        })

    for family in FAMILIES:
        digests = [
            record["selection_digest"] for record in records if record["family"] == family
        ]
        if len(digests) != EPISODES_PER_FAMILY:
            raise SystemExit(f"family {family} episode count drifted")
        if digests != sorted(digests):
            raise SystemExit(f"family {family} is not in ascending selection-digest order")

    payload = {
        "schema": "m076-episode-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "episode_count": len(records),
        "episodes": records,
    }
    payload["suite_commitment"] = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()

    if COMMITMENT_PATH.exists():
        existing = json.loads(COMMITMENT_PATH.read_text(encoding="utf-8"))
        if existing.get("suite_commitment") != payload["suite_commitment"]:
            raise SystemExit(
                "refusing to overwrite a bound suite with a different commitment; "
                "the frozen protocol forbids replacing materialized episodes"
            )
        print("suite already bound and identical:", payload["suite_commitment"])
        return 0

    COMMITMENT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print("bound suite commitment:", payload["suite_commitment"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
