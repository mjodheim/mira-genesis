"""Resumable first-accepted-candidate criterion search for M092.

This is the selection instrument, not the candidate builder and not the qualification evaluator.
It consumes the already-frozen deterministic M092-B program stream, asks the candidate-side policy
layer for complete certificates, applies structural/anti-cheating validation, then asks the
independent global verifier to judge each exact program/certificate pair.  The first accepted pair
in this fully ordered search is selected.

Selection never executes a candidate on target examples and never imports qualification material.
Verifier refusals are recorded as terminal facts about that certificate; they are not fed back to
repair or complete it.  Search state binds the theorem, implementation files, enumerator cursor,
ordered proposal audit, real certificate-policy attempts and an additional criterion-event digest
chain, so resuming in another process cannot silently change the search trajectory.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping

import metamorphosis.m092_candidate_validation as scanner
import metamorphosis.m092_certificate_generator as generator
import metamorphosis.m092_certificate_policy_search as policy_search
import metamorphosis.m092_certificate_verifier as verifier
import metamorphosis.m092_kernel as kernel
import metamorphosis.m092_proof_search as proof_search
import metamorphosis.m092_runtime as runtime
import metamorphosis.m092_search_enumerator as enumerator

SEARCH_STATE_SCHEMA = "m092-criterion-search-state-v1"
SELECTED_SCHEMA = "m092-criterion-selected-candidate-v1"
GENESIS_DIGEST = "0" * 64
PROGRAM_CAP = enumerator.CANDIDATE_CAP
CERTIFICATE_CAP = 2_000_000
CERTIFICATES_PER_PROGRAM = 4096


class CriterionSearchError(ValueError):
    """Search state or invocation violates the frozen criterion-run boundary."""


def _sha256(value: object) -> str:
    return hashlib.sha256(runtime.canonical_bytes(value)).hexdigest()


def _file_digest(module: object) -> str:
    path_value = getattr(module, "__file__", None)
    if not isinstance(path_value, str):
        raise CriterionSearchError("bound M092 module has no source file")
    return hashlib.sha256(Path(path_value).read_bytes()).hexdigest()


def implementation_digests() -> dict[str, str]:
    """Bind every implementation that can affect canonical candidate selection."""

    modules = {
        "criterion_search": __import__(__name__, fromlist=["*"]),
        "search_enumerator": enumerator,
        "certificate_policy_search": policy_search,
        "certificate_generator": generator,
        "proof_search": proof_search,
        "candidate_validation": scanner,
        "certificate_verifier": verifier,
        "kernel": kernel,
        "runtime": runtime,
    }
    return {name: _file_digest(module) for name, module in sorted(modules.items())}


def _counter(value: Mapping[str, object] | None = None) -> Counter[str]:
    result: Counter[str] = Counter()
    if value is None:
        return result
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
            raise CriterionSearchError("search refusal counter is malformed")
        result[key] = raw
    return result


def _scanner_refusal_codes(report: Mapping[str, object]) -> tuple[str, ...]:
    found: list[str] = []
    for section_name in ("structural_findings", "anti_cheating_findings"):
        section = report.get(section_name)
        if not isinstance(section, Mapping):
            raise CriterionSearchError("candidate scanner returned a malformed section")
        refusals = section.get("refusals")
        if not isinstance(refusals, list):
            raise CriterionSearchError("candidate scanner returned malformed refusals")
        for item in refusals:
            if not isinstance(item, Mapping) or not isinstance(item.get("code"), str):
                raise CriterionSearchError("candidate scanner refusal lacks a semantic code")
            found.append(str(item["code"]))
    return tuple(sorted(found))


def _selected_payload(
    record: enumerator.EnumerationRecord,
    policy: policy_search.CertificatePolicyRecord,
    scan_report: Mapping[str, object],
    verification_report: Mapping[str, object],
) -> dict[str, object]:
    if policy.certificate is None:
        raise CriterionSearchError("cannot select a policy without a complete certificate")
    certificate = dict(policy.certificate)
    return {
        "schema": SELECTED_SCHEMA,
        "program_ordinal": record.ordinal,
        "program": kernel.program_to_list(record.program),
        "program_digest": record.program_digest,
        "program_length": record.program_length,
        "program_cursor": record.cursor.to_dict(),
        "certificate_policy": policy.to_dict(include_certificate=False),
        "certificate": certificate,
        "certificate_digest": _sha256(certificate),
        "scanner_report": dict(scan_report),
        "verification_report": dict(verification_report),
    }


@dataclass(frozen=True)
class CriterionSearchState:
    theorem_digest: str
    implementation_bindings: Mapping[str, str]
    enumeration_audit: Mapping[str, object]
    generated_programs: int
    structurally_invalid_programs: int
    certificate_policy_attempts: int
    certificates_constructed: int
    scanner_refusals: Mapping[str, int]
    verifier_refusals: Mapping[str, int]
    surviving_candidates: int
    criterion_event_chain_digest: str
    status: str
    selected: Mapping[str, object] | None

    @classmethod
    def fresh(cls, expected_postcondition: Mapping[str, object]) -> "CriterionSearchState":
        # Candidate-side requirement parsing is intentionally reused only as a closed-schema check;
        # it does not import or execute qualification material.
        generator._requirement(expected_postcondition)
        audit = enumerator.EnumerationAudit()
        return cls(
            theorem_digest=_sha256(expected_postcondition),
            implementation_bindings=implementation_digests(),
            enumeration_audit=audit.to_dict(),
            generated_programs=0,
            structurally_invalid_programs=0,
            certificate_policy_attempts=0,
            certificates_constructed=0,
            scanner_refusals={},
            verifier_refusals={},
            surviving_candidates=0,
            criterion_event_chain_digest=GENESIS_DIGEST,
            status="searching",
            selected=None,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SEARCH_STATE_SCHEMA,
            "theorem_digest": self.theorem_digest,
            "implementation_bindings": dict(sorted(self.implementation_bindings.items())),
            "budgets": {
                "program_cap": PROGRAM_CAP,
                "certificate_cap": CERTIFICATE_CAP,
                "certificates_per_program": CERTIFICATES_PER_PROGRAM,
                "behaviour_deduplication_enabled": False,
            },
            "enumeration_audit": dict(self.enumeration_audit),
            "generated_programs": self.generated_programs,
            "structurally_invalid_programs": self.structurally_invalid_programs,
            "deduplicated_programs": 0,
            "certificate_policy_attempts": self.certificate_policy_attempts,
            "certificates_constructed": self.certificates_constructed,
            "scanner_refusals": dict(sorted(self.scanner_refusals.items())),
            "verifier_refusals": dict(sorted(self.verifier_refusals.items())),
            "surviving_candidates": self.surviving_candidates,
            "criterion_event_chain_digest": self.criterion_event_chain_digest,
            "status": self.status,
            "selected": self.selected,
            "candidate_executed_for_selection": False,
            "qualification_loaded": False,
            "verifier_feedback_used_for_repair": False,
        }
        payload["state_digest"] = _sha256(payload)
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CriterionSearchState":
        expected = {
            "schema", "theorem_digest", "implementation_bindings", "budgets",
            "enumeration_audit", "generated_programs", "structurally_invalid_programs",
            "deduplicated_programs", "certificate_policy_attempts", "certificates_constructed",
            "scanner_refusals", "verifier_refusals", "surviving_candidates",
            "criterion_event_chain_digest", "status", "selected",
            "candidate_executed_for_selection", "qualification_loaded",
            "verifier_feedback_used_for_repair", "state_digest",
        }
        if set(value) != expected or value.get("schema") != SEARCH_STATE_SCHEMA:
            raise CriterionSearchError("criterion search state schema or fields differ")
        payload = dict(value)
        supplied_digest = payload.pop("state_digest")
        if supplied_digest != _sha256(payload):
            raise CriterionSearchError("criterion search state digest differs")
        if value.get("budgets") != {
            "program_cap": PROGRAM_CAP,
            "certificate_cap": CERTIFICATE_CAP,
            "certificates_per_program": CERTIFICATES_PER_PROGRAM,
            "behaviour_deduplication_enabled": False,
        }:
            raise CriterionSearchError("criterion search budgets differ")
        if any(value.get(field) is not False for field in (
            "candidate_executed_for_selection", "qualification_loaded",
            "verifier_feedback_used_for_repair",
        )):
            raise CriterionSearchError("criterion state declares a forbidden selection action")
        if value.get("deduplicated_programs") != 0:
            raise CriterionSearchError("criterion state claims unimplemented behaviour deduplication")

        bindings = value.get("implementation_bindings")
        audit_value = value.get("enumeration_audit")
        scanner_counts = value.get("scanner_refusals")
        verifier_counts = value.get("verifier_refusals")
        if not all(isinstance(item, Mapping) for item in (
            bindings, audit_value, scanner_counts, verifier_counts,
        )):
            raise CriterionSearchError("criterion search mapping field is malformed")
        audit = enumerator.EnumerationAudit.from_dict(audit_value)  # type: ignore[arg-type]
        integer_fields = (
            "generated_programs", "structurally_invalid_programs", "certificate_policy_attempts",
            "certificates_constructed", "surviving_candidates",
        )
        integers: dict[str, int] = {}
        for field in integer_fields:
            raw = value.get(field)
            if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
                raise CriterionSearchError(f"criterion search {field} is malformed")
            integers[field] = raw
        if integers["generated_programs"] != audit.generated_programs:
            raise CriterionSearchError("criterion and enumeration generated-program counts differ")
        if integers["structurally_invalid_programs"] != audit.structurally_invalid_programs:
            raise CriterionSearchError("criterion and enumeration structural counts differ")
        if not (
            integers["surviving_candidates"] in (0, 1)
            and integers["certificates_constructed"] <= integers["certificate_policy_attempts"] <= CERTIFICATE_CAP
            and integers["generated_programs"] <= PROGRAM_CAP
        ):
            raise CriterionSearchError("criterion search counters are inconsistent")
        status = value.get("status")
        if status not in (
            "searching", "candidate_selected", "program_budget_exhausted",
            "certificate_budget_exhausted",
        ):
            raise CriterionSearchError("criterion search status is invalid")
        selected = value.get("selected")
        if (status == "candidate_selected") != isinstance(selected, Mapping):
            raise CriterionSearchError("criterion selected-candidate state is inconsistent")
        if (status == "candidate_selected") != (integers["surviving_candidates"] == 1):
            raise CriterionSearchError("criterion survivor count differs from selection status")
        theorem_digest = value.get("theorem_digest")
        chain = value.get("criterion_event_chain_digest")
        if not isinstance(theorem_digest, str) or len(theorem_digest) != 64:
            raise CriterionSearchError("criterion theorem digest is malformed")
        if not isinstance(chain, str) or len(chain) != 64:
            raise CriterionSearchError("criterion event chain is malformed")
        return cls(
            theorem_digest=theorem_digest,
            implementation_bindings={str(k): str(v) for k, v in bindings.items()},  # type: ignore[union-attr]
            enumeration_audit=dict(audit_value),  # type: ignore[arg-type]
            generated_programs=integers["generated_programs"],
            structurally_invalid_programs=integers["structurally_invalid_programs"],
            certificate_policy_attempts=integers["certificate_policy_attempts"],
            certificates_constructed=integers["certificates_constructed"],
            scanner_refusals=dict(_counter(scanner_counts)),  # type: ignore[arg-type]
            verifier_refusals=dict(_counter(verifier_counts)),  # type: ignore[arg-type]
            surviving_candidates=integers["surviving_candidates"],
            criterion_event_chain_digest=chain,
            status=str(status),
            selected=None if selected is None else dict(selected),  # type: ignore[arg-type]
        )


def _assert_resume_binding(
    state: CriterionSearchState,
    expected_postcondition: Mapping[str, object],
) -> None:
    generator._requirement(expected_postcondition)
    if state.theorem_digest != _sha256(expected_postcondition):
        raise CriterionSearchError("resume theorem differs from the frozen search state")
    current = implementation_digests()
    if dict(state.implementation_bindings) != current:
        raise CriterionSearchError("M092 search implementation changed across resume")


def _append_event(chain: str, event: Mapping[str, object]) -> str:
    return _sha256({"previous_criterion_event_chain_digest": chain, "event": dict(event)})


def _process_record(
    state: CriterionSearchState,
    audit: enumerator.EnumerationAudit,
    record: enumerator.EnumerationRecord,
    expected_postcondition: Mapping[str, object],
) -> tuple[CriterionSearchState, enumerator.EnumerationAudit]:
    """Consume exactly one enumerator record and return its immutable next state."""

    if state.status != "searching":
        raise CriterionSearchError("cannot consume a program after criterion search is terminal")
    next_audit = audit.append(record)
    scanner_counts = _counter(state.scanner_refusals)
    verifier_counts = _counter(state.verifier_refusals)
    attempts = state.certificate_policy_attempts
    constructed = state.certificates_constructed
    surviving = state.surviving_candidates
    selected: Mapping[str, object] | None = None
    program_scanner: Counter[str] = Counter()
    program_verifier: Counter[str] = Counter()
    program_attempts = 0
    program_constructed = 0
    accepted_digest: str | None = None

    if record.structurally_valid:
        remaining_global = CERTIFICATE_CAP - attempts
        local_limit = min(CERTIFICATES_PER_PROGRAM, remaining_global)
        for policy in policy_search.enumerate_certificate_policy_records(
            record.program,
            expected_postcondition,
            limit=local_limit,
        ):
            attempts += 1
            program_attempts += 1
            if policy.certificate is None:
                program_verifier[f"candidate_construction:{policy.refusal}"] += 1
                verifier_counts[f"candidate_construction:{policy.refusal}"] += 1
                continue
            constructed += 1
            program_constructed += 1
            scan_report = scanner.validate_candidate_artifacts(record.program, policy.certificate)
            if scan_report.get("accepted") is not True:
                codes = _scanner_refusal_codes(scan_report)
                if not codes:
                    raise CriterionSearchError("scanner refused candidate without a semantic reason")
                scanner_counts.update(codes)
                program_scanner.update(codes)
                continue
            try:
                verification_report = verifier.verify_global_certificate(
                    record.program,
                    policy.certificate,
                    expected_postcondition=expected_postcondition,
                )
            except verifier.CertificateError as error:
                reason = str(error)
                verifier_counts[reason] += 1
                program_verifier[reason] += 1
                continue
            surviving += 1
            selected = _selected_payload(record, policy, scan_report, verification_report)
            accepted_digest = str(selected["certificate_digest"])
            break

    event = {
        "program_ordinal": record.ordinal,
        "program_digest": record.program_digest,
        "program_length": record.program_length,
        "structurally_valid": record.structurally_valid,
        "structural_refusals": list(record.structural_refusals),
        "certificate_policy_attempts": program_attempts,
        "certificates_constructed": program_constructed,
        "scanner_refusals": dict(sorted(program_scanner.items())),
        "verifier_or_construction_refusals": dict(sorted(program_verifier.items())),
        "accepted_certificate_digest": accepted_digest,
    }
    chain = _append_event(state.criterion_event_chain_digest, event)

    status = "candidate_selected" if selected is not None else "searching"
    if status == "searching" and attempts >= CERTIFICATE_CAP:
        status = "certificate_budget_exhausted"
    if status == "searching" and record.ordinal >= PROGRAM_CAP:
        status = "program_budget_exhausted"

    next_state = CriterionSearchState(
        theorem_digest=state.theorem_digest,
        implementation_bindings=dict(state.implementation_bindings),
        enumeration_audit=next_audit.to_dict(),
        generated_programs=next_audit.generated_programs,
        structurally_invalid_programs=next_audit.structurally_invalid_programs,
        certificate_policy_attempts=attempts,
        certificates_constructed=constructed,
        scanner_refusals=dict(scanner_counts),
        verifier_refusals=dict(verifier_counts),
        surviving_candidates=surviving,
        criterion_event_chain_digest=chain,
        status=status,
        selected=selected,
    )
    # Round-trip the state at every program boundary.  This makes an invalid state fail at the point
    # it is created rather than much later during a resume or result checker.
    CriterionSearchState.from_dict(next_state.to_dict())
    return next_state, next_audit


def advance_search(
    state: CriterionSearchState,
    expected_postcondition: Mapping[str, object],
    *,
    program_limit: int,
) -> CriterionSearchState:
    """Advance one deterministic chunk without changing the canonical trajectory."""

    if not isinstance(program_limit, int) or isinstance(program_limit, bool) or program_limit < 0:
        raise CriterionSearchError("program_limit must be a non-negative integer")
    _assert_resume_binding(state, expected_postcondition)
    if state.status != "searching" or program_limit == 0:
        return state
    audit = enumerator.EnumerationAudit.from_dict(state.enumeration_audit)
    remaining_programs = PROGRAM_CAP - state.generated_programs
    request = min(program_limit, remaining_programs)
    current = state
    for record in enumerator.enumerate_programs(limit=request, cursor=audit.last_cursor):
        current, audit = _process_record(
            current, audit, record, expected_postcondition,
        )
        if current.status != "searching":
            break
    return current


__all__ = [
    "CERTIFICATE_CAP",
    "CERTIFICATES_PER_PROGRAM",
    "CriterionSearchError",
    "CriterionSearchState",
    "PROGRAM_CAP",
    "SEARCH_STATE_SCHEMA",
    "SELECTED_SCHEMA",
    "advance_search",
    "implementation_digests",
]
