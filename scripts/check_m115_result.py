"""Independent M115 checker: M114's P1-P22 unchanged, plus the M115 identity gate."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_carrier_bank as bank  # noqa: E402
from metamorphosis import m115_delivery as delivery  # noqa: E402
from metamorphosis import m115_execution as execution  # noqa: E402
from metamorphosis import m115_identity as identity  # noqa: E402
from scripts import check_m114_result as predecessor  # noqa: E402
from scripts.check_m113_result import EXPECTED_PREDICATES, canonical_json, digest  # noqa: E402


RESULT_PATH = ROOT / execution.RESULT_PATH
REPORT_PATH = ROOT / execution.CHECK_REPORT_PATH
INVALID = predecessor.INVALID


@contextmanager
def _m115_predecessor_context() -> Iterator[None]:
    """Run M114's checker code against M115 labels and M115's schema-delegating delivery module."""
    old_bank = predecessor.bank
    old_delivery = predecessor.delivery
    predecessor.bank = SimpleNamespace(
        MILESTONE=bank.MILESTONE,
        HYPOTHESIS=bank.HYPOTHESIS,
        FILIATION=bank.PLAN_FILIATION,
    )
    predecessor.delivery = delivery
    try:
        yield
    finally:
        predecessor.bank = old_bank
        predecessor.delivery = old_delivery


def identity_findings(result: dict[str, Any]) -> dict[str, Any]:
    ledger = result.get("delivery_ledger")
    attempts = ledger.get("attempts") if isinstance(ledger, dict) else None
    materialized = [
        attempt
        for attempt in attempts or []
        if isinstance(attempt, dict) and attempt.get("outcome") == "materialized"
    ]
    recorded = result.get("runtime_identity_attestation")
    ledger_attestation = materialized[0].get("identity_attestation") if len(materialized) == 1 else None
    router = recorded.get("router_attestation") if isinstance(recorded, dict) else None
    instrument = result.get("frozen_instrument") or {}
    clauses = {
        "exactly_one_materialized_identity_record": len(materialized) == 1,
        "result_and_ledger_attestations_match": recorded == ledger_attestation,
        "attestation_holds": isinstance(recorded, dict) and recorded.get("holds") is True,
        "identity_version_exact": isinstance(recorded, dict)
        and recorded.get("identity_version") == identity.IDENTITY_VERSION,
        "requested_alias_exact": isinstance(router, dict)
        and router.get("requested_model") == identity.REQUESTED_MODEL,
        "canonical_checkpoint_exact": isinstance(router, dict)
        and router.get("canonical_checkpoint") == identity.CANONICAL_CHECKPOINT,
        "provider_exact": isinstance(router, dict)
        and router.get("selected_provider") == identity.SELECTED_PROVIDER,
        "frozen_instrument_binds_checkpoint": instrument.get("canonical_checkpoint")
        == identity.CANONICAL_CHECKPOINT,
        "frozen_instrument_binds_identity_semantics": instrument.get("identity_semantics")
        == identity.IDENTITY_VERSION,
    }
    return {
        "schema": "m115-runtime-identity-findings-v1",
        "holds": all(clauses.values()),
        "clauses": clauses,
        "failed": sorted(key for key, value in clauses.items() if not value),
        "requested_model_alias": identity.REQUESTED_MODEL,
        "canonical_checkpoint": identity.CANONICAL_CHECKPOINT,
        "selected_provider": identity.SELECTED_PROVIDER,
        "identity_semantics": identity.IDENTITY_VERSION,
    }


def check(result: dict[str, Any]) -> dict[str, Any]:
    # All twenty-two computations, including M114's explicitly versioned P15, execute in the
    # predecessor module.  M115 patches only labels and the ledger-schema adapter while the call is
    # active; it does not restate or version a predicate.
    with _m115_predecessor_context():
        report = dict(predecessor.check(result))
    report["schema"] = "m115-check-report-v1"
    report["milestone"] = bank.MILESTONE
    report["hypothesis"] = bank.HYPOTHESIS
    report["filiation"] = dict(bank.PLAN_FILIATION)
    report["predicate_provenance"] = {
        "schema": "m115-predicate-provenance-v1",
        "retains_m114_computations": ["P%d" % index for index in range(1, 23)],
        "newly_versioned_for_m115": [],
        "p15_version": "m114-phase-boundary-v1",
        "identity_is_a_pre_materialization_instrument_gate_not_a_scientific_predicate": True,
    }
    report["claim_boundary"] = dict((result.get("filiation") and _load_plan_claim()) or {})

    findings = identity_findings(result)
    report["runtime_identity"] = findings
    if not findings["holds"]:
        report["verdict"] = INVALID

    conditions = report.get("conditions") or {}
    cardinality = result.get("cardinality") or {}
    if report["verdict"] == INVALID:
        outcome = "invalid"
    elif cardinality.get("minimum_met") is not True or cardinality.get("distinct_minimum_met") is not True:
        outcome = "insufficient-bank-negative"
    elif report["verdict"] == "positive":
        outcome = "positive"
    else:
        outcome = "negative"
    report["outcome"] = outcome
    report["predicates_missing"] = [name for name in EXPECTED_PREDICATES if name not in conditions]
    report["computed"] = len(conditions)
    report["passed"] = sum(1 for value in conditions.values() if value)
    report["failing"] = sorted(name for name, value in conditions.items() if not value)
    report["verdict_rule"] = (
        "P1-P22 retain M114's computations exactly, including m114-phase-boundary-v1 for P15. "
        "Positive iff every predicate is computed true. A bank below either frozen minimum is the "
        "pre-registered negative insufficient-bank outcome. The M115 canonical-checkpoint identity "
        "relation is an additional strictly subtractive instrument gate: failure makes the record "
        "invalid and can never improve P22 or any scientific verdict. No outcome is retried."
    )
    return report


def _load_plan_claim() -> dict[str, Any]:
    plan = json.loads((ROOT / bank.ANALYSIS_PLAN_PATH).read_text(encoding="utf-8"))
    return dict(plan["claim_boundary"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    if not RESULT_PATH.is_file():
        print("no evidence at %s" % RESULT_PATH.name)
        return 1
    state = execution.readiness(ROOT)
    if state.get("phase") != "executed" or state.get("blockers"):
        print("REFUSED: the reveal chain is not valid")
        return 1
    result = json.loads(RESULT_PATH.read_text(encoding="ascii"))
    measured_result_digest = digest({key: value for key, value in result.items() if key != "result_digest"})
    if result.get("result_digest") != measured_result_digest:
        print("REFUSED: result digest drifted")
        return 1
    report = check(result)
    report["result_digest"] = result["result_digest"]
    report["report_digest"] = digest({key: value for key, value in report.items() if key != "report_digest"})
    if arguments.write:
        REPORT_PATH.write_bytes((canonical_json(report) + "\n").encode("ascii"))
        print("wrote %s" % REPORT_PATH.relative_to(ROOT))
    for name in EXPECTED_PREDICATES:
        value = report["conditions"].get(name)
        print("%-4s %s" % (name, "true" if value else "FALSE" if value is not None else "MISSING"))
    print()
    print("verdict: %s (%d/%d)" % (report["verdict"], report["passed"], report["computed"]))
    print("outcome: %s" % report["outcome"])
    if report["failing"]:
        print("failing: %s" % ", ".join(report["failing"]))
    print("runtime identity: %s" % ("true" if report["runtime_identity"]["holds"] else "FALSE"))
    print("report digest: %s" % report["report_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
