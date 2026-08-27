"""Report M114's phase, and refuse a reveal that is not ready.

M086-A recorded a positive verdict against a threshold that could never fail, partly because a
scientific checker existed without being decisive in CI. This entry point is decisive: `--require-
ready` refuses unless every artifact exists, validates and agrees, and `--assert-not-revealed`
refuses the moment a result appears while the milestone is still supposed to be sealed.

M114's report also carries the delivery summary, because a bank that exists is not yet a bank
the frozen rule permitted: the phase machine refuses a ledger that violates the delivery
budget exactly as it refuses a missing spec.

Nothing here opens, decrypts or lists bank content, and no output names a carrier.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m114_carrier_bank as bank  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit non-zero unless the phase is reveal_authorized with no blockers",
    )
    parser.add_argument(
        "--assert-not-revealed",
        action="store_true",
        help="exit non-zero if a result exists; the CI guard while the bank is sealed",
    )
    arguments = parser.parse_args()

    report = bank.assess_carrier_bank_readiness(ROOT)
    if arguments.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print("milestone       %s" % report["milestone"])
        print("contract        %s" % report["contract_version"])
        print("carrier schema  %s" % report["carrier_schema_version"])
        print("phase           %s" % report["phase"])
        print("ready to reveal %s" % report["ready_for_reveal"])
        print("revealed        %s" % report["revealed"])
        summary = report.get("delivery_summary")
        if summary is not None:
            print("delivery        %d of %d attempts, %d materialization(s)" % (
                summary["delivery_attempts"],
                summary["delivery_budget"],
                summary["bank_materializations"],
            ))
        if report["blockers"]:
            print("blockers:")
            for item in report["blockers"]:
                print("  - %s" % item)

    if arguments.assert_not_revealed and report["revealed"]:
        print("REFUSED: a result exists while the bank is still supposed to be sealed")
        return 1
    if arguments.require_ready and not report["ready_for_reveal"]:
        print("REFUSED: the bank is not ready for reveal")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
