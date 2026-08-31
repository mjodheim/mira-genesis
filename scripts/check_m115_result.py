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
from metamorphosis import m115_sealing as sealing  # noqa: E402
from scripts import check_m114_result as predecessor  # noqa: E402
from scripts.check_m113_result import EXPECTED_PREDICATES, canonical_json, digest  # noqa: E402


RESULT_PATH = ROOT / execution.RESULT_PATH
REPORT_PATH = ROOT / execution.CHECK_REPORT_PATH
INVALID = predecessor.INVALID
TERMINAL_SCHEMA = "m115-instrument-aborted-result-v1"
TERMINAL_REPORT_SCHEMA = "m115-instrument-aborted-check-report-v1"
TERMINAL_VERDICT_RULE = (
    "A completion that cannot be parsed as the frozen strict-JSON carrier payload terminates the "
    "single authorized reveal before qualification. It is not retried, is not reclassified as an "
    "insufficient valid bank, computes none of P1-P22, and leaves H60 untested."
)


class CheckError(RuntimeError):
    """The preserved M115 result or its independent terminal replay is inconsistent."""


def _require(holds: bool, message: str) -> None:
    if not holds:
        raise CheckError(message)


def _load_record(path: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CheckError("cannot read %s: %s" % (path.relative_to(ROOT), exc)) from exc
    if not isinstance(record, dict):
        raise CheckError("%s is not a JSON object" % path.relative_to(ROOT))
    return record


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


def check_terminal_abort(
    result: dict[str, Any],
    preserved_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a reveal that terminated before any carrier entered qualification."""
    _require(result.get("schema") == TERMINAL_SCHEMA, "terminal result schema drifted")
    _require(result.get("milestone") == bank.MILESTONE, "terminal result milestone drifted")
    _require(result.get("hypothesis") == bank.HYPOTHESIS, "terminal result hypothesis drifted")
    _require(result.get("terminal_failure") == "invalid_json", "terminal reason is not invalid_json")
    _require(
        result.get("observed_terminal_message")
        == "the materialized completion is not valid JSON",
        "terminal admission message drifted",
    )
    _require(result.get("verdict") == "instrument-aborted", "terminal verdict drifted")
    _require(result.get("hypothesis_status") == "untested", "H60 no longer remains untested")
    _require(
        result.get("verdict") not in {"positive", "negative"},
        "an aborted record masquerades as a scientific verdict",
    )
    _require(result.get("reveal_occurred") is True, "the legitimate reveal is not preserved")
    _require(result.get("reveal_legitimate") is True, "the reveal legitimacy flag drifted")
    _require(result.get("canonical_attempts") == 1, "the reveal attempt count is not exactly one")
    _require(result.get("scientific_retry_permitted") is False, "the terminal outcome permits retry")
    _require(result.get("qualification_started") is False, "qualification is falsely recorded")
    _require(result.get("carrier_payload_parsed") is False, "a carrier payload is falsely recorded")

    plan = _load_record(ROOT / bank.ANALYSIS_PLAN_PATH)
    bank.validate_analysis_plan(plan, root=ROOT)
    spec = _load_record(ROOT / bank.GENERATOR_SPEC_PATH)
    bank.validate_generator_spec(
        spec,
        root=ROOT,
        plan_commitment_sha256=plan.get("plan_commitment_sha256"),
    )
    ledger = _load_record(ROOT / bank.DELIVERY_LEDGER_PATH)
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=spec.get("spec_commitment_sha256"),
        request_body_sha256=spec.get("canonical_request_body_sha256"),
    )
    commitment = _load_record(ROOT / bank.BANK_COMMITMENT_PATH)
    sealing.validate_public_commitment(commitment, root=ROOT)
    protocol = _load_record(ROOT / execution.SYSTEM_PROTOCOL_PATH)
    authorization = _load_record(ROOT / execution.REVEAL_AUTHORIZATION_PATH)
    execution.validate_reveal_authorization(authorization, root=ROOT)
    execution.validate_system_protocol(
        protocol,
        root=ROOT,
        tested_system_commit=authorization.get("system_protocol_frozen_at_commit"),
    )

    attempts = ledger.get("attempts") or []
    materialized = [attempt for attempt in attempts if attempt.get("outcome") == "materialized"]
    _require(len(attempts) == 1, "the delivery ledger contains a second physical attempt")
    _require(len(materialized) == 1, "the delivery ledger does not contain one materialization")
    _require(ledger.get("bank_materialization_index") == 1, "materialization index drifted")
    _require(plan.get("max_bank_materializations") == 1, "materialization budget drifted")
    _require(plan.get("retries_permitted") is False, "the frozen plan now permits retry")
    _require(result.get("physical_delivery_attempts") == 1, "physical attempt count drifted")
    _require(result.get("bank_materializations") == 1, "materialization count drifted")

    attestation = materialized[0].get("identity_attestation") or {}
    router = attestation.get("router_attestation") or {}
    expected_identity = {
        "holds": attestation.get("holds") is True,
        "identity_semantics": attestation.get("identity_version"),
        "requested_model_alias": router.get("requested_model"),
        "canonical_checkpoint": router.get("canonical_checkpoint"),
        "provider": router.get("selected_provider"),
    }
    _require(attestation.get("holds") is True, "materialized runtime identity no longer holds")
    _require(result.get("runtime_identity") == expected_identity, "runtime identity binding drifted")

    expected_bindings = {
        "analysis_plan_commitment_sha256": plan.get("plan_commitment_sha256"),
        "system_protocol_commitment_sha256": protocol.get("protocol_commitment_sha256"),
        "system_protocol_frozen_at_commit": authorization.get("system_protocol_frozen_at_commit"),
        "authorization_commit": execution.commit_that_added(
            ROOT, execution.REVEAL_AUTHORIZATION_PATH
        ),
        "bank_commitment_sha256": commitment.get("commitment_sha256"),
        "ciphertext_sha256": commitment.get("ciphertext_sha256"),
        "generation_response_sha256": commitment.get("generation_response_sha256"),
    }
    for key, value in expected_bindings.items():
        _require(result.get(key) == value, "terminal provenance binding drifted: %s" % key)

    _require(result.get("total_carriers") == 0, "the aborted record contains carriers")
    _require(result.get("qualifying_carriers") == 0, "the aborted record contains qualifiers")
    _require(
        result.get("distinct_qualifying_structures") == 0,
        "the aborted record contains qualifying structures",
    )
    _require(result.get("minimum_bank_criteria_passed") is False, "minimum bank falsely passed")
    _require(
        result.get("minimum_qualifying_carriers") == plan.get("minimum_qualifying_carriers"),
        "minimum qualifying-carrier binding drifted",
    )
    _require(
        result.get("minimum_distinct_qualifying_structures")
        == plan.get("minimum_distinct_qualifying_structures"),
        "minimum distinct-structure binding drifted",
    )
    _require(
        result.get("insufficient_bank_verdict_not_applied_because_no_carrier_payload_existed")
        is True,
        "the admission abort was reclassified as insufficient bank",
    )
    _require("per_arm_totals" not in result, "qualification totals were fabricated for an abort")
    expected_predicates = {name: "not_computed" for name in EXPECTED_PREDICATES}
    _require(result.get("p1_p22") == expected_predicates, "P1-P22 are not exactly not_computed")

    expected_custody = {
        "carrier_content_printed": False,
        "plaintext_generation_response_present": False,
        "plaintext_generation_response_written_by_reveal": False,
    }
    _require(result.get("custody") == expected_custody, "terminal custody invariants drifted")
    _require(
        commitment.get("plaintext_response_present_in_repository") is False,
        "public commitment claims a plaintext response",
    )
    _require(
        not (ROOT / bank.EXPERIMENT_DIRECTORY / "GENERATION_RESPONSE.json").exists(),
        "plaintext generation response exists in the repository",
    )

    report = preserved_report or _load_record(REPORT_PATH)
    expected_replay = {
        "carrier_content_printed": False,
        "exit_status": 1,
        "matched_terminal_outcome": True,
        "mode": "scripts/run_m115_qualification.py --replay",
        "plaintext_generation_response_written": False,
        "terminal_failure": result["terminal_failure"],
    }
    _require(
        report.get("independent_replay") == expected_replay,
        "independent replay does not equal the terminal admission failure",
    )
    _require(report.get("result_digest") == result.get("result_digest"), "report/result binding drifted")
    _require(
        report.get("report_digest")
        == digest({key: value for key, value in report.items() if key != "report_digest"}),
        "terminal checker-report digest drifted",
    )

    expected_report: dict[str, Any] = {
        "schema": TERMINAL_REPORT_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "hypothesis_status": "untested",
        "physical_delivery_attempts": 1,
        "total_carriers": 0,
        "qualifying_carriers": 0,
        "distinct_qualifying_structures": 0,
        "minimum_bank_criteria_passed": False,
        "computed": 0,
        "passed": 0,
        "failing": [],
        "not_computed": list(EXPECTED_PREDICATES),
        "verdict": "instrument-aborted",
        "verdict_rule": TERMINAL_VERDICT_RULE,
        "independent_replay": expected_replay,
        "result_commit": execution.commit_that_added(ROOT, execution.RESULT_PATH),
        "result_digest": result["result_digest"],
        "report_digest": "",
    }
    expected_report["report_digest"] = digest(
        {key: value for key, value in expected_report.items() if key != "report_digest"}
    )
    _require(report == expected_report, "preserved terminal checker report differs from replay")
    return expected_report


def check(
    result: dict[str, Any],
    preserved_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if result.get("schema") == TERMINAL_SCHEMA:
        return check_terminal_abort(result, preserved_report)
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
    try:
        state = execution.readiness(ROOT)
        if state.get("phase") != "executed" or state.get("blockers"):
            raise CheckError("the reveal chain is not valid: %s" % "; ".join(state["blockers"]))
        result = _load_record(RESULT_PATH)
        measured_result_digest = digest(
            {key: value for key, value in result.items() if key != "result_digest"}
        )
        if result.get("result_digest") != measured_result_digest:
            raise CheckError("result digest drifted")
        preserved_report = (
            _load_record(REPORT_PATH) if result.get("schema") == TERMINAL_SCHEMA else None
        )
        report = check(result, preserved_report)
    except (
        CheckError,
        execution.ExecutionError,
        sealing.SealingError,
        bank.CarrierBankError,
        delivery.DeliveryError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print("REFUSED: %s" % exc)
        return 1
    report["result_digest"] = result["result_digest"]
    report["report_digest"] = digest({key: value for key, value in report.items() if key != "report_digest"})
    if arguments.write:
        REPORT_PATH.write_bytes((canonical_json(report) + "\n").encode("ascii"))
        print("wrote %s" % REPORT_PATH.relative_to(ROOT))
    conditions = report.get("conditions") or {}
    not_computed = set(report.get("not_computed") or [])
    for name in EXPECTED_PREDICATES:
        value = conditions.get(name)
        rendered = (
            "NOT_COMPUTED"
            if name in not_computed
            else "true" if value else "FALSE" if value is not None else "MISSING"
        )
        print("%-4s %s" % (name, rendered))
    print()
    print("verdict: %s (%d/%d)" % (report["verdict"], report["passed"], report["computed"]))
    if "outcome" in report:
        print("outcome: %s" % report["outcome"])
    else:
        print("hypothesis status: %s" % report["hypothesis_status"])
    if report["failing"]:
        print("failing: %s" % ", ".join(report["failing"]))
    if "runtime_identity" in report:
        print("runtime identity: %s" % ("true" if report["runtime_identity"]["holds"] else "FALSE"))
    if "independent_replay" in report:
        print(
            "independent replay: %s"
            % ("matched" if report["independent_replay"]["matched_terminal_outcome"] else "FALSE")
        )
    print("report digest: %s" % report["report_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
