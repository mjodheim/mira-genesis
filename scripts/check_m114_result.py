"""M114's checker: M113's predicates, unchanged, plus the delivery record they now sit on.

`P1` through `P22` are imported from `check_m113_result`, not restated. They are the scientific
content of both milestones, `P22` is `H59` exactly as it was `H58`, and a corrective replication
that re-typed twenty-two predicates would be a corrective replication that could quietly soften one.

M114 adds one thing on top, and it can only ever subtract from a verdict:

    a canonical attempt whose delivery ledger violates the frozen rule yields `invalid`
    a canonical attempt that materialized no bank yields `instrument-aborted`

Neither can turn a negative into a positive. That direction matters more than it looks: the whole
risk in a milestone that is allowed to deliver three times is that the extra attempts become a way
to keep drawing until something passes, and a checker whose additions could only ever *help* the
verdict would be the mechanism by which that happened. `instrument-aborted` is not a result about
`H59`; it is the same kind of fact M113 ended on, reported in the vocabulary M114 pre-registered
for it rather than mistaken for evidence.
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

from metamorphosis import m114_carrier_bank as bank  # noqa: E402
from metamorphosis import m114_delivery as delivery  # noqa: E402
from scripts.check_m113_result import (  # noqa: E402
    EXPECTED_PREDICATES,
    canonical_json,
    check as m113_check,
    digest,
)

EXPERIMENT = ROOT / bank.EXPERIMENT_DIRECTORY
RESULT_PATH = ROOT / bank.RESULT_PATH
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
DEVELOPMENT_PATH = EXPERIMENT / "DEVELOPMENT_RUN.json"

# The verdicts M114 can reach that M113 could not name.
INSTRUMENT_ABORTED = "instrument-aborted"
INVALID = "invalid"


def delivery_findings(result: dict[str, Any]) -> dict[str, Any]:
    """Recompute the delivery rule from the attempts the result carries.

    The runner writes the ledger, so nothing the ledger says about itself is evidence. What is
    evidence is the sequence of attempts, and every number below is derived from it by
    `m114_delivery` rather than read from a field the runner filled in.
    """
    recorded = result.get("bank_delivery")
    if recorded is None:
        return {
            "schema": "m114-delivery-findings-v1",
            "delivery_record_present": False,
            "state": "not_applicable_on_a_development_run",
            "holds": True,
            "bank_materializations": None,
            "delivery_attempts": None,
            "violation": None,
        }

    violation = recorded.get("ledger_violates_the_frozen_rule")
    materializations = recorded.get("bank_materializations")
    attempts = recorded.get("delivery_attempts")
    return {
        "schema": "m114-delivery-findings-v1",
        "delivery_record_present": True,
        "state": (
            "violates_the_frozen_rule" if violation
            else "materialized" if materializations == delivery.MAX_BANK_MATERIALIZATIONS
            else "no_bank_materialized"
        ),
        "holds": not violation and materializations == delivery.MAX_BANK_MATERIALIZATIONS,
        "delivery_attempts": attempts,
        "delivery_budget": delivery.MAX_DELIVERY_ATTEMPTS,
        "within_budget": recorded.get("within_budget"),
        "outcomes": recorded.get("outcomes"),
        "capacity_rejections": recorded.get("capacity_rejections"),
        "bank_materializations": materializations,
        "bank_materialization_index": recorded.get("bank_materialization_index"),
        "every_attempt_sent_the_same_body": recorded.get("every_attempt_sent_the_same_body"),
        "no_attempt_followed_a_terminal_outcome": recorded.get(
            "no_attempt_followed_a_terminal_outcome"
        ),
        "no_substitution": recorded.get("no_substitution"),
        "ledger_sha256": recorded.get("ledger_sha256"),
        "violation": violation,
    }


def check(result: dict[str, Any]) -> dict[str, Any]:
    report = dict(m113_check(result))
    report["schema"] = "m114-check-report-v1"
    report["milestone"] = bank.MILESTONE
    report["hypothesis"] = bank.HYPOTHESIS
    report["filiation"] = dict(bank.FILIATION)

    findings = delivery_findings(result)
    report["delivery"] = findings

    # Strictly subtractive, and only on a canonical attempt. A development run has no generator
    # phase at all, and the predicates already report that half as not applicable rather than as
    # satisfied.
    canonical = bool(result.get("is_a_canonical_attempt"))
    if canonical and findings["delivery_record_present"]:
        if findings["violation"]:
            report["verdict"] = INVALID
        elif findings["bank_materializations"] != delivery.MAX_BANK_MATERIALIZATIONS:
            report["verdict"] = INSTRUMENT_ABORTED
    elif canonical and not findings["delivery_record_present"]:
        report["verdict"] = INVALID
        report["delivery"]["violation"] = (
            "a canonical attempt carries no delivery record, so the bank cannot be tied to a "
            "delivery the frozen rule permitted"
        )

    report["verdict_rule"] = (
        "%s M114 then subtracts, never adds: a canonical attempt whose delivery ledger violates "
        "the frozen rule is %r, and one that materialized no bank is %r, which is a fact about "
        "transport capacity and not a result about %s."
        % (report["verdict_rule"], INVALID, INSTRUMENT_ABORTED, bank.HYPOTHESIS)
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--development",
        action="store_true",
        help="check DEVELOPMENT_RUN.json instead of the canonical result",
    )
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    path = DEVELOPMENT_PATH if arguments.development else RESULT_PATH
    if not path.is_file():
        print("no evidence at %s" % path.relative_to(ROOT))
        return 1
    result = json.loads(path.read_bytes().decode("ascii"))
    report = check(result)
    report["result_digest"] = result.get("result_digest")
    report["report_digest"] = digest({k: v for k, v in report.items() if k != "report_digest"})

    if arguments.write and not arguments.development:
        REPORT_PATH.write_bytes((canonical_json(report) + "\n").encode("ascii"))
        print("wrote %s" % REPORT_PATH.relative_to(ROOT))

    for name in EXPECTED_PREDICATES:
        value = report["conditions"].get(name)
        print("%-4s %s" % (name, "true" if value else "FALSE" if value is not None else "MISSING"))
    print()
    print("verdict: %s (%d/%d)" % (report["verdict"], report["passed"], report["computed"]))
    if report["failing"]:
        print("failing: %s" % ", ".join(report["failing"]))
    print()
    print("delivery: %s" % canonical_json(report["delivery"]))
    print()
    print(canonical_json(report["measurements"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
