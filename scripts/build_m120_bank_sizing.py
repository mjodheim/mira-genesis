#!/usr/bin/env python3
"""DEVELOPMENT bank sizing: how many carriers to ask for, derived rather than chosen.

A carrier count picked after seeing how many carriers qualified would be a forking path. This one
is computed before any H65 observation exists, from the M120 contract's own bounds, and written
down so the derivation can be recomputed rather than believed.

Three draws are measured and all three are recorded:

    corner    the smallest machine the contract admits -- three cells, two conditional actions,
              two plain actions, one error code
    uniform   uniform over the contract's bounds
    ceiling   the largest machine the contract admits

**The derivation uses the corner**, because that is the shape M119's blind generator actually
produced when M115's schema offered it a range: 22 of 37 machines had one cell and 35 of 37 had
exactly two actions. Sizing against the uniform draw would be sizing against a generator this
project has not observed.

The record also measures what the decoder does over every draw, so the acceptance claim -- every
schema-valid candidate decodes to a carrier the frozen host accepts -- is asserted over thousands
of machines here as well as over the boundary corners the tests exhaust.

This script sends no request, reads no completion and scores no hypothesis. Its output is
DEVELOPMENT evidence about an instrument.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_schema as schema_tools  # noqa: E402
from metamorphosis import m119_endpoint as endpoint  # noqa: E402
from metamorphosis import m120_bank as bank  # noqa: E402
from metamorphosis import m120_carrier_contract as contract  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis import m120_devkit as devkit  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

SIZING_SCHEMA = "m120-bank-sizing-development-v1"
OUT_PATH = ROOT / chronology.BANK_SIZING
SEED_PREFIX = "m120-sizing-"
SAMPLE = 400


class SizingError(RuntimeError):
    """The sizing cannot be derived honestly. Every path fails closed."""


def _schema_conformance(sample: int) -> dict[str, Any]:
    """Every drawn candidate must satisfy the candidate schema the generator will be handed.

    The emitter draws from the contract's constants. If a draw ever fell outside the schema built
    from those same constants, the two would have drifted apart and the measurement below would be
    measuring a family the generator is not being asked for.
    """
    schema = contract.candidate_schema()
    invalid = 0
    for mode in devkit.MODES:
        for candidate in devkit.development_candidates(SEED_PREFIX + mode + "-", sample,
                                                       mode=mode):
            ok, _, _ = schema_tools.instance_is_valid({"machines": [candidate]}, schema)
            invalid += 0 if ok else 1
    return {
        "candidates_checked": sample * len(devkit.MODES),
        "candidates_outside_the_candidate_schema": invalid,
        "every_drawn_candidate_satisfies_the_candidate_schema": invalid == 0,
    }


def _completion_size(sample: int) -> dict[str, Any]:
    """How large a completion of `REQUESTED_CARRIER_COUNT` machines would be, at each draw."""
    sizes = {}
    for mode in devkit.MODES:
        machines = list(devkit.development_candidates(
            SEED_PREFIX + "size-" + mode + "-", bank.REQUESTED_CARRIER_COUNT, mode=mode))
        sizes[mode] = len(json.dumps({"machines": machines}, separators=(",", ":")))
    return {
        "requested_carriers": bank.REQUESTED_CARRIER_COUNT,
        "completion_characters": sizes,
        "characters_per_token_assumed": 2.6,
        "estimated_completion_tokens": {k: int(v / 2.6) for k, v in sizes.items()},
        "readiness_proved_completion_tokens": 73731,
        "max_output_tokens": 131072,
        "ceiling_estimate_is_below_the_proved_envelope":
            int(sizes["ceiling"] / 2.6) < 73731,
    }


def derive(sample: int = SAMPLE) -> dict[str, Any]:
    rates = {mode: devkit.qualification_rate(SEED_PREFIX, sample, mode=mode)
             for mode in devkit.MODES}
    corner = rates[devkit.MODE_CORNER]
    if not all(rate["every_decoded_candidate_was_accepted"] for rate in rates.values()):
        raise SizingError(
            "the decoder did not carry every drawn candidate into a carrier the frozen host "
            "accepts; the contract is not what it claims and no sizing follows from it")

    # The planning rate is deliberately half the measured corner rate. The corner is the
    # pessimistic *shape*; halving it is the pessimistic *generator*, and M119 is the reason to
    # assume one.
    planning_rate = round(corner["qualification_rate"] / 2, 4)
    expected_qualifying = bank.REQUESTED_CARRIER_COUNT * planning_rate
    expected_paired = (expected_qualifying
                       * corner["mean_demand_pairs_per_qualifying_carrier"] * 2)
    needed = endpoint.required_paired_demands()

    record = {
        "schema": SIZING_SCHEMA,
        "milestone": "M120", "hypothesis": "H65",
        "development": True,
        "is_a_qualifying_call": False,
        "advances_a_generality_gate": False,
        "contract_version": contract.CONTRACT_VERSION,
        "decoder_version": contract.DECODER_VERSION,
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "seed_prefix": SEED_PREFIX,
        "sample_per_mode": sample,
        "schema_conformance": _schema_conformance(sample),
        "qualification_rates": rates,
        "derivation_mode": devkit.MODE_CORNER,
        "why_the_corner": "M119's blind generator answered every range in M115's schema with its "
                          "minimum, so the smallest shape the contract admits is the shape this "
                          "route has actually been observed to produce.",
        "planning_qualification_rate": planning_rate,
        "planning_rate_is_half_the_measured_corner_rate": True,
        "requested_carriers": bank.REQUESTED_CARRIER_COUNT,
        "expected_qualifying_carriers_at_the_planning_rate": expected_qualifying,
        "expected_paired_demands_at_the_planning_rate": expected_paired,
        "minimum_qualifying_carriers": bank.MINIMUM_QUALIFYING_CARRIERS,
        "minimum_distinct_qualifying_structures":
            bank.MINIMUM_DISTINCT_QUALIFYING_STRUCTURES,
        "discordant_pairs_needed_for_significance": needed,
        "expected_paired_demands_exceed_the_arithmetic_minimum": expected_paired >= needed,
        "expected_qualifying_exceeds_the_plan_minimum":
            expected_qualifying >= bank.MINIMUM_QUALIFYING_CARRIERS,
        "completion_size": _completion_size(sample),
        "this_is_a_sizing_estimate_not_a_prediction": True,
        "the_estimate_measures_a_development_emitter_not_the_blind_generator": True,
        "no_h65_carrier_existed_when_this_was_derived": True,
        "result_sha256": "",
    }
    record["result_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "result_sha256"}))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=SAMPLE)
    parser.add_argument("--write", action="store_true",
                        help="write the derivation to the committed sizing path")
    args = parser.parse_args()
    try:
        chronology.assert_no_scientific_observation_yet(ROOT)
        record = derive(args.sample)
    except (SizingError, chronology.ChronologyError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    if args.write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_bytes(canonical_bytes(record) + b"\n")
        print("wrote %s" % OUT_PATH.name)
    print(json.dumps({
        "requested_carriers": record["requested_carriers"],
        "qualification_rate_corner": record["qualification_rates"]["corner"][
            "qualification_rate"],
        "qualification_rate_uniform": record["qualification_rates"]["uniform"][
            "qualification_rate"],
        "planning_qualification_rate": record["planning_qualification_rate"],
        "expected_qualifying_carriers": record[
            "expected_qualifying_carriers_at_the_planning_rate"],
        "expected_paired_demands": record["expected_paired_demands_at_the_planning_rate"],
        "every_decoded_candidate_was_accepted": all(
            r["every_decoded_candidate_was_accepted"]
            for r in record["qualification_rates"].values()),
        "result_sha256": record["result_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
