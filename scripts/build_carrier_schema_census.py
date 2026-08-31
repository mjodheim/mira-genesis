#!/usr/bin/env python3
"""Derive the M116 schema-complexity census from the frozen M115 carrier output schema.

The census exists so that nobody chooses the DEVELOPMENT stress gate's structural thresholds. They
are recomputed here from the frozen carrier schema itself, committed, and then re-derived on every
audit run and compared. A census that drifts from the schema it claims to describe fails the gate.

This script reads the frozen M115 output schema and writes nothing into M115. It makes no network
call, sends no qualifying input and touches no bank.

    python scripts/build_carrier_schema_census.py --write
    python scripts/build_carrier_schema_census.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_schema as schema_tools  # noqa: E402
from metamorphosis import m116_stress_schema as stress  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

CENSUS_RECORD_SCHEMA = "m116-carrier-schema-census-v1"
FROZEN_CARRIER_SCHEMA_PATH = ROOT / "experiments" / "M115" / "OUTPUT_SCHEMA.json"
CENSUS_PATH = ROOT / "experiments" / "M116" / "CARRIER_SCHEMA_CENSUS.json"


def build() -> dict[str, object]:
    schema = json.loads(FROZEN_CARRIER_SCHEMA_PATH.read_text(encoding="utf-8"))
    frozen = schema_tools.census(schema)
    candidate_schema = stress.build_stress_schema()
    candidate = schema_tools.census(candidate_schema)
    holds, failures = schema_tools.census_dominates(candidate, frozen)
    record = {
        "schema": CENSUS_RECORD_SCHEMA,
        "milestone": "M116",
        "hypothesis": "H61",
        "development_only": True,
        "derived_from": "experiments/M115/OUTPUT_SCHEMA.json",
        "frozen_carrier_schema_sha256": sha256_hex(canonical_bytes(schema)),
        "frozen_carrier_census": frozen,
        "stress_schema_sha256": sha256_hex(canonical_bytes(candidate_schema)),
        "stress_schema_census": candidate,
        "dominance_fields": list(schema_tools.DOMINANCE_FIELDS),
        "stress_schema_dominates_frozen_carrier_schema": holds,
        "dominance_failures": failures,
        "thresholds_are_derived_not_chosen": True,
        "no_qualifying_input_is_referenced": True,
        "census_sha256": "",
    }
    record["census_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "census_sha256"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the census artifact")
    parser.add_argument("--check", action="store_true", help="verify the committed census")
    arguments = parser.parse_args()

    record = build()
    if not record["stress_schema_dominates_frozen_carrier_schema"]:
        print("stress schema is structurally weaker than the frozen carrier schema:")
        for failure in record["dominance_failures"]:
            print("  - %s" % failure)
        return 1

    if arguments.write:
        CENSUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CENSUS_PATH.write_bytes(canonical_bytes(record) + b"\n")
        print("wrote %s" % CENSUS_PATH.relative_to(ROOT))
        return 0

    if arguments.check:
        if not CENSUS_PATH.is_file():
            print("no committed census at %s" % CENSUS_PATH.relative_to(ROOT))
            return 1
        committed = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
        if committed != record:
            print("the committed census does not match the derivation")
            return 1
        print("census matches the frozen carrier schema and the stress schema")
        return 0

    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
