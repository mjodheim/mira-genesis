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
readiness, and the delivery ledger.

**Two quantities, two fields, and never one field carrying both.** M113 defined `P15`'s generator
half as the number of *physical invocations*, on the stated ground that a series of physical
requests must not be presentable afterwards as one logical invocation. M114 separates delivery from
materialization, so the two are no longer the same number, and a field named for one of them cannot
be allowed to hold the other:

    physical_delivery_attempts   how many physical requests were sent, 429s included
    bank_materializations        how many of them carried a model completion

A 429 before generation is a **physical network request** even though it is not a model execution.
An earlier form of this file wrote `model_calls_in_bank_generation = bank_materializations`, which
would have reported a milestone that spent three attempts on a queue as one that made zero network
requests -- while the same milestone claimed `P15` was imported unchanged. That field is gone; both
quantities are now reported under their own names, and `P15` is M114's own versioned predicate
rather than M113's read against a different meaning.

The whole delivery ledger is preserved into the result, not only its summary, so the checker can
re-derive every delivery clause itself instead of agreeing with a boolean this runner wrote.
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


def delivery_ledger(root: Path | None = None) -> dict[str, Any] | None:
    """The whole delivery record, preserved into the result rather than summarised into it.

    The checker re-derives every delivery clause of `P15` from these attempts. Handing it only a
    summary would make it agree with arithmetic this runner performed, which is the M095 defect:
    a record field that asserts where it is supposed to measure.
    """
    path = (Path(root) / bank.DELIVERY_LEDGER_PATH) if root is not None else LEDGER_PATH
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def physical_delivery_attempts(root: Path | None = None) -> int | None:
    """How many physical requests were sent, capacity rejections included.

    This is the quantity M113 called "physical invocations", and it is reported under its own name.
    A 429 before generation is a physical network request even though no model executed; folding it
    into a model-call count, in either direction, is exactly the conflation M114 exists to undo.
    """
    ledger = delivery_ledger(root)
    if ledger is None:
        return None
    attempts = ledger.get("attempts")
    return len(attempts) if isinstance(attempts, list) else 0


def bank_materializations(root: Path | None = None) -> int | None:
    """How many delivery attempts carried a model completion. The frozen rule caps this at one."""
    summary = bank_delivery(root)
    if summary is None:
        return None
    return summary["bank_materializations"]


def model_execution_evidence(root: Path | None = None) -> list[dict[str, Any]] | None:
    """Per attempt, what the response said about whether the model ran and what it produced.

    Reported whether or not the verdict is positive, because this is the evidence the outcome
    classification was derived from and a reader must be able to re-derive it.
    """
    ledger = delivery_ledger(root)
    if ledger is None:
        return None
    attempts = ledger.get("attempts")
    if not isinstance(attempts, list):
        return []
    return [
        {
            "attempt_index": attempt.get("attempt_index"),
            "status": attempt.get("status"),
            "completion_present": attempt.get("completion_present"),
            "model_execution_cannot_be_excluded": attempt.get(
                "model_execution_cannot_be_excluded"
            ),
            "outcome": attempt.get("outcome"),
            "response_sha256": attempt.get("response_sha256"),
        }
        for attempt in attempts
        if isinstance(attempt, dict)
    ]


def frozen_instrument(root: Path | None = None) -> dict[str, Any] | None:
    """What the frozen spec pinned, preserved so the checker can test the record against it.

    `P15`'s delivery half asks whether every attempt sent the frozen body to the frozen identity
    with no fallback available. None of that is answerable from the ledger alone: the ledger says
    what was sent, and only the spec says what was supposed to be.
    """
    path = (Path(root) / bank.GENERATOR_SPEC_PATH) if root is not None else (
        ROOT / bank.GENERATOR_SPEC_PATH
    )
    if not path.is_file():
        return None
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {
        "spec_commitment_sha256": spec.get("spec_commitment_sha256"),
        "canonical_request_body_sha256": spec.get("canonical_request_body_sha256"),
        "model": (spec.get("generator_identity") or {}).get("model"),
        "provider": (spec.get("generator_identity") or {}).get("provider"),
        "routing": spec.get("routing"),
    }


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
    # The two quantities, under their own names. `model_calls_in_bank_generation` is deliberately
    # absent: under M114's separation there is no single number that field could honestly hold.
    result["physical_delivery_attempts"] = physical_delivery_attempts()
    result["bank_materializations"] = bank_materializations()
    result["model_execution_evidence"] = model_execution_evidence()
    result["delivery_ledger"] = delivery_ledger()
    result["frozen_instrument"] = frozen_instrument()
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
