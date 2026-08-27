"""M114's checker: M113's scientific computations, plus the one predicate M114 had to version.

**What is imported unchanged, and what is not.** `P1`-`P14` and `P16`-`P22` retain M113's scientific
computations exactly -- they are imported from `check_m113_result`, not restated, so a corrective
replication cannot quietly soften one. `P15` is the explicitly versioned corrective boundary
predicate required by M114's preregistered separation of delivery attempts from bank materialization.

That exception is not a convenience, and hiding it would have been a defect of the same kind this
milestone exists to correct. M113 defines `P15`'s generator half as the number of **physical
invocations**, on the stated ground that a series of physical requests must never be presentable
afterwards as one logical invocation. M114 separates delivery from materialization, so "physical
invocations" and "model calls" are no longer the same number -- and an earlier form of this
milestone set `model_calls_in_bank_generation = bank_materializations` while claiming `P15` was
imported unchanged. It was not. A milestone whose whole subject is a conflated counter could not
ship a conflated counter of its own and describe it as an import.

So `P15` is versioned here as `m114-phase-boundary-v1`, recomputed independently from the preserved
record rather than read from any field the runner wrote about itself, and it is the conjunction of
three halves:

**Qualification.** Zero model calls, zero network calls, zero remote-execution calls, and a network
guard whose self-test actually fired -- because an absent guard and a silent run otherwise record
the same zero.

**Generator.** Exactly one bank materialization. A canonical run cannot exist on fewer, and the
frozen rule permits no more.

**Delivery.** The physical requests, counted separately from the model calls, within the frozen
budget of three; every attempt sending byte-identical request bytes to the same model and the same
provider with no fallback available; only explicit 429s carrying no completion and no evidence of
model execution preceding a further attempt; the frozen 60-second wait honoured; at most one
materializing response; nothing attempted after materialization; every ambiguity terminal; and the
ledger valid in full under the frozen rule.

**None of this can help `H59`.** The delivery checker is a gate and only a gate. A violation makes
the run `invalid`, zero materializations make it `instrument-aborted`, and no clause anywhere in it
can turn `P22` false into `P22` true. A milestone permitted three delivery attempts has exactly one
way to cheat -- drawing until something passes -- and a boundary predicate that could ever improve a
verdict would be the instrument of it.
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

PHASE_BOUNDARY_SCHEMA = "m114-phase-boundary-v1"

# The verdicts M114 can reach that M113 could not name.
INSTRUMENT_ABORTED = "instrument-aborted"
INVALID = "invalid"

# Stated once, carried in every report, so no reader has to take "unchanged" on trust.
PREDICATE_PROVENANCE = {
    "schema": "m114-predicate-provenance-v1",
    "retain_m113_scientific_computations": (
        ["P%d" % index for index in range(1, 15)]
        + ["P%d" % index for index in range(16, 23)]
    ),
    "versioned_for_this_milestone": ["P15"],
    "p15_version": PHASE_BOUNDARY_SCHEMA,
    "p15_reason": (
        "M113 defines P15's generator half as the number of physical invocations. M114's "
        "preregistered separation of delivery attempts from bank materialization makes that no "
        "longer a single number, so P15 is recomputed here rather than imported against a changed "
        "meaning."
    ),
    "p22_scientific_computation_is_unchanged_and_applied_to": bank.HYPOTHESIS,
    "the_versioned_predicate_can_only_subtract_from_a_verdict": True,
}


# ----------------------------------------------------------------------------------------
# P15, recomputed
# ----------------------------------------------------------------------------------------


def _qualification_half(result: dict[str, Any]) -> dict[str, Any]:
    """Silence, and a guard that proved it was live while keeping it."""
    counts = {
        key: result.get(key)
        for key in (
            "model_calls_in_qualification",
            "network_calls_in_qualification",
            "remote_execution_calls_in_qualification",
        )
    }
    silent = all(value == 0 for value in counts.values())
    # An absent guard and a silent run record the same zero. Only the self-test tells them apart.
    guard_live = result.get("network_guard_selftest_intercepted") is True
    return {
        "holds": bool(silent and guard_live),
        "model_calls_in_qualification": counts["model_calls_in_qualification"],
        "network_calls_in_qualification": counts["network_calls_in_qualification"],
        "remote_execution_calls_in_qualification": counts[
            "remote_execution_calls_in_qualification"
        ],
        "qualification_phase_is_silent": silent,
        "qualification_guard_was_live": guard_live,
        "outbound_addresses_attempted": result.get("outbound_addresses_attempted"),
        "model_client_modules_imported": result.get("model_client_modules_imported"),
    }


def _delivery_half(result: dict[str, Any]) -> dict[str, Any]:
    """Every delivery clause, re-derived from the preserved ledger.

    Nothing here reads `bank_delivery`, which is the runner's own summary. The ledger is
    re-validated from scratch and each clause is recomputed from the attempts, so a runner that
    summarised its way to a pass would still fail here.
    """
    ledger = result.get("delivery_ledger")
    instrument = result.get("frozen_instrument") or {}
    findings: dict[str, Any] = {
        "delivery_record_present": ledger is not None,
        "physical_delivery_attempts": result.get("physical_delivery_attempts"),
        "bank_materializations": result.get("bank_materializations"),
        "model_execution_evidence": result.get("model_execution_evidence"),
        "delivery_budget": delivery.MAX_DELIVERY_ATTEMPTS,
        "retry_wait_seconds": delivery.RETRY_WAIT_SECONDS,
    }
    if not isinstance(ledger, dict):
        findings["holds"] = False
        findings["violation"] = "no delivery ledger is preserved in the result"
        return findings

    # The frozen rule, in full, before any clause below is looked at individually. A ledger that
    # fails here fails P15 whatever the individual clauses happen to say.
    try:
        delivery.validate_delivery_ledger(
            ledger,
            spec_commitment_sha256=instrument.get("spec_commitment_sha256"),
            request_body_sha256=instrument.get("canonical_request_body_sha256"),
        )
    except delivery.DeliveryError as exc:
        findings["ledger_is_valid_under_the_frozen_rule"] = False
        findings["violation"] = str(exc)
        findings["holds"] = False
        return findings
    findings["ledger_is_valid_under_the_frozen_rule"] = True

    attempts = [a for a in (ledger.get("attempts") or []) if isinstance(a, dict)]
    outcomes = [a.get("outcome") for a in attempts]
    digests = {a.get("request_body_sha256") for a in attempts}
    models = {a.get("served_model") for a in attempts if a.get("served_model") is not None}
    providers = {a.get("served_provider") for a in attempts if a.get("served_provider") is not None}
    routing = instrument.get("routing") or {}
    materializing = [i for i, outcome in enumerate(outcomes, start=1) if outcome == "materialized"]

    clauses = {
        "physical_attempts_are_recorded_separately": (
            findings["physical_delivery_attempts"] == len(attempts)
        ),
        "within_the_frozen_delivery_budget": len(attempts) <= delivery.MAX_DELIVERY_ATTEMPTS,
        "every_attempt_sent_identical_request_bytes": len(digests) == 1,
        "the_request_bytes_are_the_frozen_ones": (
            instrument.get("canonical_request_body_sha256") in digests
        ),
        "every_attempt_was_served_by_the_same_model": len(models) <= 1,
        "the_served_model_is_the_frozen_one": models <= {instrument.get("model")},
        "every_attempt_was_served_by_the_same_provider": len(providers) <= 1,
        "the_served_provider_is_the_frozen_one": providers <= {instrument.get("provider")},
        "no_fallback_was_available": (
            routing.get("allow_fallbacks") is False
            and routing.get("automatic_routing") is False
            and not routing.get("model_fallbacks")
            and not routing.get("provider_fallbacks")
        ),
        # Only a clean 429 may precede another attempt. Recomputed from each attempt's own
        # evidence rather than from the outcome word it carries.
        "only_clean_capacity_rejections_preceded_a_retry": all(
            attempt.get("status") == delivery.RETRYABLE_STATUS
            and attempt.get("completion_present") is not True
            and attempt.get("model_execution_cannot_be_excluded") is not True
            for attempt in attempts[:-1]
        ),
        "the_frozen_wait_was_honoured": all(
            (attempt.get("waited_seconds_before_this_attempt") in (0, 0.0))
            if position == 1
            else (
                isinstance(attempt.get("waited_seconds_before_this_attempt"), (int, float))
                and attempt["waited_seconds_before_this_attempt"] >= delivery.RETRY_WAIT_SECONDS
            )
            for position, attempt in enumerate(attempts, start=1)
        ),
        "at_most_one_materializing_response": len(materializing) <= (
            delivery.MAX_BANK_MATERIALIZATIONS
        ),
        "nothing_was_attempted_after_a_materialization": (
            not materializing or materializing[-1] == len(attempts)
        ),
        # Every ambiguity is terminal. An ambiguous attempt that was followed by another is the one
        # failure mode no downstream check could ever recover from.
        "every_ambiguity_is_terminal": all(
            outcome != "failed_ambiguous" for outcome in outcomes[:-1]
        ),
    }
    findings["clauses"] = clauses
    findings["holds"] = all(clauses.values())
    findings["violation"] = None if findings["holds"] else ", ".join(
        sorted(name for name, ok in clauses.items() if not ok)
    )
    return findings


def phase_boundary(result: dict[str, Any]) -> dict[str, Any]:
    """`P15` for M114: qualification silence, one materialization, and a lawful delivery record."""
    canonical = bool(result.get("is_a_canonical_attempt"))
    qualification = _qualification_half(result)
    delivery_findings = _delivery_half(result)

    materializations = result.get("bank_materializations")
    if not canonical:
        # A development run has no generator phase and no delivery phase at all. Reporting them as
        # satisfied would be the M112 defect; reporting them as not applicable is the truth.
        generation_holds = True
        generation_state = "not_applicable_on_a_development_run"
        delivery_holds = True
        delivery_state = "not_applicable_on_a_development_run"
    else:
        generation_holds = materializations == delivery.MAX_BANK_MATERIALIZATIONS
        generation_state = (
            "exactly_one_bank_materialization" if generation_holds
            else "the_canonical_bank_does_not_record_exactly_one_materialization"
        )
        delivery_holds = bool(delivery_findings["holds"])
        delivery_state = "the_frozen_delivery_rule_holds" if delivery_holds else (
            "the_delivery_record_violates_the_frozen_rule"
        )

    return {
        "schema": PHASE_BOUNDARY_SCHEMA,
        "holds": bool(qualification["holds"] and generation_holds and delivery_holds),
        "qualification_phase": qualification,
        "generation_phase": {
            "holds": generation_holds,
            "state": generation_state,
            "bank_materializations": materializations,
            "required": delivery.MAX_BANK_MATERIALIZATIONS,
        },
        "delivery_phase": dict(delivery_findings, state=delivery_state, holds=delivery_holds),
        # Named here so no reader has to reconstruct which quantity is which. A 429 before
        # generation is a physical network request and is not a model execution.
        "physical_delivery_attempts": result.get("physical_delivery_attempts"),
        "bank_materializations": materializations,
        "model_execution_evidence": result.get("model_execution_evidence"),
        "model_calls_in_qualification": qualification["model_calls_in_qualification"],
        "network_calls_in_qualification": qualification["network_calls_in_qualification"],
        "remote_execution_calls_in_qualification": qualification[
            "remote_execution_calls_in_qualification"
        ],
    }


# ----------------------------------------------------------------------------------------
# The report
# ----------------------------------------------------------------------------------------


def delivery_findings(result: dict[str, Any]) -> dict[str, Any]:
    """What the verdict's delivery gate saw, reported whether or not the verdict is positive."""
    boundary = phase_boundary(result)
    canonical = bool(result.get("is_a_canonical_attempt"))
    findings = dict(boundary["delivery_phase"])
    findings["schema"] = "m114-delivery-findings-v1"
    if not canonical:
        findings["state"] = "not_applicable_on_a_development_run"
    return findings


def check(result: dict[str, Any]) -> dict[str, Any]:
    report = dict(m113_check(result))
    report["schema"] = "m114-check-report-v1"
    report["milestone"] = bank.MILESTONE
    report["hypothesis"] = bank.HYPOTHESIS
    report["filiation"] = dict(bank.FILIATION)
    report["predicate_provenance"] = dict(PREDICATE_PROVENANCE)

    # P15 is recomputed here. M113's own boundary predicate reads a field M114 does not write,
    # precisely because that field would have to hold two quantities at once, so the replacement is
    # explicit rather than an override that happens to agree.
    boundary = phase_boundary(result)
    conditions = dict(report["conditions"])
    conditions["P15"] = boundary["holds"]
    report["conditions"] = conditions

    measurements = dict(report["measurements"])
    measurements["phase_boundary"] = boundary
    report["measurements"] = measurements

    # Re-derived from the corrected conditions rather than carried over from M113's tally.
    missing = [name for name in EXPECTED_PREDICATES if name not in conditions]
    failing = sorted(name for name, ok in conditions.items() if not ok)
    report["predicates_missing"] = missing
    report["computed"] = len(conditions)
    report["passed"] = sum(1 for value in conditions.values() if value)
    report["failing"] = failing
    report["verdict"] = "positive" if not missing and not failing else "negative"

    findings = delivery_findings(result)
    report["delivery"] = findings

    # Strictly subtractive, and only on a canonical attempt.
    canonical = bool(result.get("is_a_canonical_attempt"))
    if canonical:
        if not findings.get("delivery_record_present"):
            report["verdict"] = INVALID
            report["delivery"]["violation"] = (
                "a canonical attempt carries no delivery record, so the bank cannot be tied to a "
                "delivery the frozen rule permitted"
            )
        elif findings.get("violation"):
            report["verdict"] = INVALID
        elif findings.get("bank_materializations") != delivery.MAX_BANK_MATERIALIZATIONS:
            report["verdict"] = INSTRUMENT_ABORTED

    report["verdict_rule"] = (
        "P1-P14 and P16-P22 retain M113's scientific computations; P15 is the explicitly versioned "
        "corrective boundary predicate (%s) required by M114's preregistered separation of "
        "delivery attempts from bank materialization, and is the conjunction of a silent "
        "qualification phase under a live guard, exactly one bank materialization, and a delivery "
        "record valid in full under the frozen rule. Positive iff every predicate is computed "
        "true. M114 then subtracts, never adds: a canonical attempt whose delivery record violates "
        "the frozen rule is %r, and one that materialized no bank is %r, which is a fact about "
        "transport capacity and not a result about %s."
        % (PHASE_BOUNDARY_SCHEMA, INVALID, INSTRUMENT_ABORTED, bank.HYPOTHESIS)
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
        print("no evidence at %s" % path.name)
        return 1
    result = json.loads(path.read_bytes().decode("ascii"))
    report = check(result)
    report["result_digest"] = result.get("result_digest")
    report["report_digest"] = digest({k: v for k, v in report.items() if k != "report_digest"})

    if arguments.write and not arguments.development:
        REPORT_PATH.write_bytes((canonical_json(report) + "\n").encode("ascii"))
        print("wrote %s" % REPORT_PATH.name)

    for name in EXPECTED_PREDICATES:
        value = report["conditions"].get(name)
        print("%-4s %s" % (name, "true" if value else "FALSE" if value is not None else "MISSING"))
    print()
    print("verdict: %s (%d/%d)" % (report["verdict"], report["passed"], report["computed"]))
    if report["failing"]:
        print("failing: %s" % ", ".join(report["failing"]))
    print()
    print("P15 (%s): %s" % (PHASE_BOUNDARY_SCHEMA, canonical_json(
        report["measurements"]["phase_boundary"]
    )))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
