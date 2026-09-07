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
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.evaluation_cost import (  # noqa: E402
    cost_record,
    measured,
    monetary_cost,
)
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


def deterministic_costs(campaign: Mapping[str, Any]) -> dict[str, int]:
    """Cost components a checker recomputes from the campaign rather than trusting."""
    horizons = campaign["horizons"].values()
    return {
        "model_calls": 0,
        "network_requests": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "episodes": sum(int(h["horizon"]) * len(ARMS) for h in horizons),
        "work_items": sum(arm["completed_work_items"] for h in horizons for arm in h["arms"].values()),
        "candidate_evaluations": sum(len(h["arms"]) for h in horizons),
        "budget_units_spent": sum(len(h["schedule"]["faults"]) for h in horizons),
    }


def _quality(campaign: Mapping[str, Any]) -> dict[str, Any]:
    horizons = campaign["horizons"]
    return {
        "full_operational_detections_before_harm": {
            key: value["arms"]["full"]["operational_detections_before_harm"]
            for key, value in sorted(horizons.items())
        },
        "full_quiescent_detections_before_harm": {
            key: value["arms"]["full"]["quiescent_detections_before_harm"]
            for key, value in sorted(horizons.items())
        },
        "full_silent_divergent_outputs": {
            key: value["arms"]["full"]["silent_divergent_outputs"]
            for key, value in sorted(horizons.items())
        },
    }


def _reliability(campaign: Mapping[str, Any]) -> dict[str, Any]:
    horizons = campaign["horizons"]
    return {
        "horizons_run": len(horizons),
        "arms_per_horizon": len(ARMS),
        "residual_corruption_in_full": {
            key: value["arms"]["full"]["residual_corruption"]
            for key, value in sorted(horizons.items())
        },
        "every_arm_shares_its_horizon_schedule": all(
            {arm["schedule_sha256"] for arm in value["arms"].values()}
            == {value["schedule"]["schedule_sha256"]}
            for value in horizons.values()
        ),
    }


def development_record() -> dict:
    """Build the DEVELOPMENT campaign record. Nothing here is a scientific observation."""
    with measured() as environment_costs:
        campaign = run_campaign(DEVELOPMENT_SALT, horizons=HORIZONS)
    deterministic = deterministic_costs(campaign)
    cost = cost_record(
        milestone="M121",
        deterministic=deterministic,
        environment_costs=environment_costs,
        quality=_quality(campaign),
        reliability=_reliability(campaign),
        monetary=monetary_cost(
            None,
            model="none",
            prompt_tokens=deterministic["prompt_tokens"],
            completion_tokens=deterministic["completion_tokens"],
        ),
    )
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
    # The reproducible digest covers reproducible things. Wall clock, CPU seconds and peak memory
    # differ on every host, so folding them into record_sha256 would make an honest rerun look like
    # tampering. The cost record is attached after the digest, and its deterministic half carries
    # its own digest that a checker does recompute.
    record["record_sha256"] = digest_of(record)
    record["cost"] = cost
    record["deterministic_cost_sha256"] = digest_of(cost["deterministic"])
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
