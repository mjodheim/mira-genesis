#!/usr/bin/env python3
"""H65 qualification: run the four arms over the revealed bank and record per-demand evidence.

This runner **records and decides nothing**, and it is deliberately thin. Every input that could
change a verdict is resolved from the chronology's own constants rather than named on the command
line: the carrier bank, the bank nonce, the analysis plan and the observation budget. M118's runner
took `--session-budget` from argv, and M119's still took `--carriers`, `--nonce` and `--plan`. A
path a caller may name is a path a caller may swap, and the file that is authenticated has to be
the file that is used.

The measurement itself lives in `metamorphosis/m120_measurement.py`, because
`scripts/check_m120_result.py` reproduces it rather than reading it. Two implementations of the
same function are two things that can disagree; there is one here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m113_evaluator as evaluator  # noqa: E402
from metamorphosis import m119_endpoint as endpoint  # noqa: E402
from metamorphosis import m120_adequacy as adequacy  # noqa: E402
from metamorphosis import m120_bank as bank  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis import m120_measurement as measurement  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        help="where to write the measurements; defaults to the committed path. "
                             "No evidence path is taken from argv.")
    args = parser.parse_args()

    try:
        # The pre-generation freeze is necessary and not sufficient. Once a completion exists,
        # nothing in that earlier check stops an edit to the evaluator, the demand derivation or
        # the scoring before the result is computed, so the freeze is re-proved here.
        permission = chronology.assert_frozen_system_unchanged(ROOT, phase="scoring")
        reveal = json.loads((ROOT / chronology.REVEAL_RECORD).read_text(encoding="utf-8"))
        carrier_path = ROOT / chronology.CARRIER_BANK
        carrier_digest = sha256_hex(canonical_bytes(
            json.loads(carrier_path.read_text(encoding="utf-8"))))
        if carrier_digest != reveal["carrier_bank_sha256"]:
            raise measurement.MeasurementError(
                "the committed carriers are not the ones the committed reveal record names")
        plan = json.loads((ROOT / chronology.ANALYSIS_PLAN).read_text(encoding="utf-8"))
        bank.validate_analysis_plan(plan, ROOT)
        nonce = measurement.committed_nonce(ROOT, chronology.BANK_NONCE_COMMITMENT)
        carriers = measurement.load_carriers(carrier_path, nonce)
        record = measurement.measure(carriers, nonce, plan, provenance={
            "freeze_commitment_sha256": permission["freeze_commitment_sha256"],
            "reveal_record_sha256": reveal["reveal_record_sha256"],
            "carrier_bank_sha256": carrier_digest,
        })
    except (measurement.MeasurementError, adequacy.AdequacyError, bank.BankError,
            chronology.ChronologyError, endpoint.EndpointError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    out = args.out or (ROOT / chronology.MEASUREMENTS)
    out.write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({"qualifying_carriers": record["qualifying_carriers"],
                      "distinct_qualifying_structures": record["distinct_qualifying_structures"],
                      "paired_demands": len(record["entries"]) * len(evaluator.DEMAND_CLASSES),
                      "measurements_sha256": record["measurements_sha256"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
