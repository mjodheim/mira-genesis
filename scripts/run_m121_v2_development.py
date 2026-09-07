#!/usr/bin/env python3
"""Run the M121/H66 v2 apparatus on the public DEVELOPMENT fixture salt.

This runner cannot produce a scientific observation. It refuses every canonical input by
construction: it accepts no salt argument, draws no entropy, and writes a record that declares
itself non-canonical. The canonical chronology in the v2 design candidate places the canonical salt
draw *after* the apparatus is frozen, and that draw remains an owner-only action.

Its purpose is the third step of that chronology: demonstrate on neutral fixtures that the arms
dissociate as designed, so a later frozen apparatus is not being calibrated against its own
canonical result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.m121_long_horizon_v2 import (  # noqa: E402
    APPARATUS_VERSION,
    ARMS,
    DEVELOPMENT_SALT,
    GENERATOR_VERSION,
    HORIZONS,
    canonical_json,
    digest_of,
    run_campaign,
)

RESULT_PATH = ROOT / "experiments/M121/V2_DEVELOPMENT_RESULT.json"


def development_record() -> dict:
    """Build the DEVELOPMENT campaign record. Nothing here is a scientific observation."""
    campaign = run_campaign(DEVELOPMENT_SALT, horizons=HORIZONS)
    record = {
        "schema": "m121-v2-development-result-v1",
        "milestone": "M121",
        "hypothesis": "H66",
        "development": True,
        "canonical": False,
        "is_a_scientific_observation": False,
        "advances_a_generality_gate": False,
        "salt_is_the_public_development_fixture": True,
        "canonical_salt_drawn": False,
        "apparatus_version": APPARATUS_VERSION,
        "generator_version": GENERATOR_VERSION,
        "arms": list(ARMS),
        "horizons": list(HORIZONS),
        "campaign": campaign,
        "model_calls": 0,
        "network_calls": 0,
        "remote_executions": 0,
    }
    record["record_sha256"] = digest_of(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="persist the DEVELOPMENT record; without it the run only prints its digests",
    )
    arguments = parser.parse_args()
    record = development_record()
    if arguments.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_bytes(canonical_json(record) + b"\n")
        print("wrote %s" % RESULT_PATH.relative_to(ROOT))
    print(
        json.dumps(
            {
                "record_sha256": record["record_sha256"],
                "campaign_sha256": record["campaign"]["campaign_sha256"],
                "canonical": False,
                "is_a_scientific_observation": False,
                "schedules": {
                    horizon: record["campaign"]["horizons"][horizon]["schedule"]["schedule_sha256"]
                    for horizon in record["campaign"]["horizons"]
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
