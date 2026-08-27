"""M114 orchestration -- M113's qualification, unchanged, over a bank M114 delivered.

Nothing about qualification differs between the two milestones, so nothing about it is restated
here. The arms, the restoration from the frozen M109 and M111 result bytes, the per-carrier closure,
the demand derivation, the scoring and the sealed scope that measures its own silence are all
imported from `run_m113_qualification` and driven against M114's plan and M114's bank.

That import is the claim "the mechanism is unchanged" made checkable. A copy of eight hundred lines
would drift, and the drift would be invisible in exactly the place where the two milestones must be
comparable: M114 exists to answer M113's question with a working instrument, and a qualification
that had quietly moved would answer a different question.

What M114 supplies instead of M113 is the record around the bank -- its own frozen plan, its own
readiness, and the delivery ledger. `P15`'s generator half reads that ledger: the number M113 read
was "physical invocations", and M114's separation of delivery from materialization means the number
that matters here is how many attempts *materialized a bank*, which the frozen rule caps at one.
The attempts that did not materialize anything are reported beside it rather than folded into it,
because a capacity rejection is a fact about a queue and never a model call.
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

from metamorphosis import m113_carrier_devkit as devkit  # noqa: E402
from metamorphosis import m114_carrier_bank as bank  # noqa: E402
from metamorphosis import m114_delivery as delivery  # noqa: E402
from metamorphosis.blind_bank_protocol import opaque_domain_id  # noqa: E402
from scripts.run_m113_qualification import (  # noqa: E402
    ARM_NAMES,
    DEVELOPMENT_NONCE,
    canonical_json,
    digest,
    run_bank,
)

EXPERIMENT = ROOT / bank.EXPERIMENT_DIRECTORY
RESULT_PATH = ROOT / bank.RESULT_PATH
DEVELOPMENT_PATH = EXPERIMENT / "DEVELOPMENT_RUN.json"
PLAN_PATH = ROOT / bank.ANALYSIS_PLAN_PATH
CANDIDATE_PLAN_PATH = ROOT / bank.ANALYSIS_PLAN_CANDIDATE_PATH
LEDGER_PATH = ROOT / bank.DELIVERY_LEDGER_PATH


def bank_delivery(root: Path | None = None) -> dict[str, Any] | None:
    """What the delivery ledger records, recomputed rather than read from its own summary.

    Returns `None` when no ledger exists at all -- a development run has no generator phase, and an
    absent generator is reported as not applicable rather than as a satisfied one. That distinction
    is the M112 lesson restated at the only place M114 could repeat it.
    """
    path = (Path(root) / bank.DELIVERY_LEDGER_PATH) if root is not None else LEDGER_PATH
    if not path.is_file():
        return None
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    summary = delivery.delivery_summary(ledger)
    summary["ledger_sha256"] = delivery.ledger_digest(ledger)
    try:
        delivery.validate_delivery_ledger(ledger)
    except delivery.DeliveryError as exc:
        summary["ledger_violates_the_frozen_rule"] = str(exc)
    else:
        summary["ledger_violates_the_frozen_rule"] = None
    return summary


def bank_generation_invocations(root: Path | None = None) -> int | None:
    """`P15`'s generator half: how many delivery attempts materialized a bank.

    Not how many requests were sent. A capacity rejection never reached the model, so counting it
    as a model call would report a generator phase that did not happen -- and, worse, would make a
    milestone that spent three attempts on a queue look like one that drew three times.
    """
    summary = bank_delivery(root)
    if summary is None:
        return None
    return summary["bank_materializations"]


def load_plan() -> dict[str, Any] | None:
    for path in (PLAN_PATH, CANDIDATE_PLAN_PATH):
        if path.is_file():
            return json.loads(path.read_bytes().decode("ascii"))
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--development",
        action="store_true",
        help="run against a devkit bank; the canonical path needs a revealed bank",
    )
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--seed", default="m114-development-run")
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    plan = load_plan()
    if plan is None:
        print("REFUSED: no analysis plan, frozen or candidate, exists")
        return 1

    if not arguments.development:
        readiness = bank.assess_carrier_bank_readiness(ROOT)
        print("REFUSED: the canonical path requires a revealed bank, which does not exist")
        for item in readiness["blockers"]:
            print("  - %s" % item)
        return 1

    sample = arguments.sample or int(plan["requested_carrier_count"])
    payload = devkit.development_payload(arguments.seed, sample)
    carriers = []
    for index, carrier in enumerate(payload["carriers"]):
        carrier = dict(carrier)
        carrier["carrier_ref"] = opaque_domain_id(DEVELOPMENT_NONCE, index)
        carriers.append(carrier)

    result = run_bank(
        carriers,
        DEVELOPMENT_NONCE,
        requested_carrier_count=sample,
        minimum_qualifying=int(plan["minimum_qualifying_carriers"]),
        minimum_distinct_structures=int(plan["minimum_distinct_qualifying_structures"]),
        session_budget=int(plan["session_budget"]),
    )
    result["milestone"] = bank.MILESTONE
    result["hypothesis"] = bank.HYPOTHESIS
    result["filiation"] = dict(bank.FILIATION)
    result["development"] = True
    result["is_a_canonical_attempt"] = False
    result["plan_commitment_sha256"] = plan.get("plan_commitment_sha256")
    result["model_calls_in_bank_generation"] = bank_generation_invocations()
    result["bank_delivery"] = bank_delivery()
    result["result_digest"] = digest({k: v for k, v in result.items() if k != "result_digest"})

    if arguments.write:
        DEVELOPMENT_PATH.write_bytes((canonical_json(result) + "\n").encode("ascii"))
        print("wrote %s" % DEVELOPMENT_PATH.relative_to(ROOT))

    print(
        "carriers %d  qualifying %d  demand pairs %d"
        % (len(carriers), result["qualifying_carriers"], result["demand_pairs_posed"])
    )
    print("rows where the cascades disagree: %s" % result["rows_where_the_cascades_disagree"])
    print("learner rows reached: %s" % canonical_json(result["learner_rows_reached"]))
    print("ambiguous feature rows: %s" % result["ambiguous_feature_rows"])
    print(
        "peak invocations at the base budget: %d of %d"
        % (result["peak_invocations_at_the_base_budget"], result["session_budget"])
    )
    print()
    print(
        "%-13s %8s %6s %10s %8s %9s %6s %14s"
        % ("arm", "correct", "unmet", "false-ref", "calib", "invented", "undet", "attribution")
    )
    for name in ARM_NAMES:
        totals = result["per_arm_totals"][name]
        agreement = result["attribution_agreement"][name]
        seen = agreement["correct"] + agreement["incorrect"]
        print(
            "%-13s %8d %6d %10d %8d %9d %6d %14s"
            % (
                name,
                totals.get("correct_construction", 0),
                totals.get("unmet_construction", 0),
                totals.get("false_refusal", 0),
                totals.get("calibrated_refusal", 0),
                totals.get("invented_adapter", 0),
                totals.get("undetermined", 0),
                "%d/%d" % (agreement["correct"], seen),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
