"""Measure the M092 canonical-search execution envelope without loading the target theorem.

This is performance instrumentation only. It never imports or reads the M092 target-theorem file,
qualification data, result artifacts or candidate-selection state. The proposal benchmark consumes a
large deterministic prefix of the frozen target-independent enumerator. The certificate benchmark
uses the neutral countdown theorem already used by the pre-search readiness checks and deliberately
continues after any neutral verifier acceptance so it cannot become a surrogate candidate search.

The report contains measurements and linear projections, not a pass/fail scientific verdict. A
projection cannot prove the full canonical run will finish in time; it exists to avoid knowingly
arming a first run whose frozen computation obviously exceeds the available CI envelope.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import metamorphosis.m092_candidate_validation as scanner
import metamorphosis.m092_certificate_policy_search as policy_search
import metamorphosis.m092_certificate_verifier as verifier
import metamorphosis.m092_search_enumerator as enumerator
from metamorphosis.m092_runtime import canonical_bytes

REPORT_SCHEMA = "m092-neutral-runtime-envelope-v1"
DEFAULT_ENUMERATION_SAMPLE = 100_000
DEFAULT_POLICY_ATTEMPT_SAMPLE = 10_000
DEFAULT_POLICY_PROGRAM_CAP = 25_000
CANONICAL_PROGRAM_CAP = 2_000_000
CANONICAL_CERTIFICATE_CAP = 2_000_000
CANONICAL_JOB_SECONDS = 6 * 60 * 60

# This theorem is deliberately unrelated to parity/remainder. It is the same neutral countdown
# rehearsal used before M092 target search existed: output y=0 and explicit witness steps=x.
NEUTRAL_REQUIREMENT = {
    "schema": "m092-affine-postcondition-v1",
    "witnesses": ["steps"],
    "constraints": [
        {"relation": "eq", "coefficients": {"steps": -1, "x": 1}, "constant": 0},
        {"relation": "eq", "coefficients": {"y": 1}, "constant": 0},
        {"relation": "ge", "coefficients": {"steps": 1}, "constant": 0},
    ],
}


class RuntimeAuditError(ValueError):
    """Neutral runtime-audit invocation is malformed."""


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _measurement(seconds: float, units: int, canonical_units: int) -> dict[str, object]:
    rate = 0.0 if seconds <= 0 else units / seconds
    projected = None if rate <= 0 else canonical_units / rate
    return {
        "sample_units": units,
        "seconds": seconds,
        "units_per_second": rate,
        "canonical_units": canonical_units,
        "linear_projection_seconds": projected,
    }


def benchmark_enumerator(sample: int) -> dict[str, object]:
    if sample > enumerator.CANDIDATE_CAP:
        raise RuntimeAuditError("enumeration sample exceeds the frozen candidate cap")
    start = time.perf_counter()
    count = 0
    invalid = 0
    length_counts: Counter[int] = Counter()
    chain = "0" * 64
    last_cursor: dict[str, object] | None = None
    for record in enumerator.enumerate_programs(limit=sample):
        count += 1
        invalid += int(not record.structurally_valid)
        length_counts[record.program_length] += 1
        chain = _sha256({
            "previous": chain,
            "ordinal": record.ordinal,
            "program_digest": record.program_digest,
            "structurally_valid": record.structurally_valid,
        })
        last_cursor = record.cursor.to_dict()
    seconds = time.perf_counter() - start
    if count != sample:
        raise RuntimeAuditError(f"enumerator emitted {count} records for requested sample {sample}")
    result = _measurement(seconds, count, CANONICAL_PROGRAM_CAP)
    result.update({
        "structurally_invalid_programs": invalid,
        "program_lengths": {str(key): value for key, value in sorted(length_counts.items())},
        "prefix_digest": chain,
        "last_cursor_digest": None if last_cursor is None else last_cursor["cursor_digest"],
    })
    return result


def benchmark_neutral_certificate_pipeline(
    attempt_sample: int,
    program_cap: int,
) -> dict[str, object]:
    if attempt_sample > CANONICAL_CERTIFICATE_CAP:
        raise RuntimeAuditError("policy-attempt sample exceeds the frozen global certificate cap")
    if program_cap > enumerator.CANDIDATE_CAP:
        raise RuntimeAuditError("policy program cap exceeds the frozen candidate cap")

    start = time.perf_counter()
    attempts = 0
    programs_seen = 0
    structurally_valid = 0
    constructed = 0
    scanner_refused = 0
    verifier_accepted = 0
    verifier_refused = 0
    construction_refusals: Counter[str] = Counter()
    scanner_refusals: Counter[str] = Counter()
    verifier_refusals: Counter[str] = Counter()
    chain = "0" * 64

    for record in enumerator.enumerate_programs(limit=program_cap):
        programs_seen += 1
        if not record.structurally_valid:
            continue
        structurally_valid += 1
        remaining = attempt_sample - attempts
        if remaining <= 0:
            break
        local_limit = min(4096, remaining)
        for policy in policy_search.enumerate_certificate_policy_records(
            record.program,
            NEUTRAL_REQUIREMENT,
            limit=local_limit,
        ):
            attempts += 1
            outcome: dict[str, object] = {
                "program_ordinal": record.ordinal,
                "program_digest": record.program_digest,
                "policy_ordinal": policy.ordinal,
            }
            if policy.certificate is None:
                reason = policy.refusal or "unspecified"
                construction_refusals[reason] += 1
                outcome["outcome"] = "construction_refusal"
                outcome["reason"] = reason
            else:
                constructed += 1
                scan_report = scanner.validate_candidate_artifacts(record.program, policy.certificate)
                if scan_report.get("accepted") is not True:
                    scanner_refused += 1
                    codes: list[str] = []
                    for section_name in ("structural_findings", "anti_cheating_findings"):
                        section = scan_report.get(section_name, {})
                        if isinstance(section, dict):
                            for item in section.get("refusals", []):
                                if isinstance(item, dict) and isinstance(item.get("code"), str):
                                    codes.append(str(item["code"]))
                    if not codes:
                        codes.append("unspecified")
                    scanner_refusals.update(codes)
                    outcome["outcome"] = "scanner_refusal"
                    outcome["reason"] = sorted(codes)
                else:
                    try:
                        report = verifier.verify_global_certificate(
                            record.program,
                            policy.certificate,
                            expected_postcondition=NEUTRAL_REQUIREMENT,
                        )
                    except verifier.CertificateError as error:
                        verifier_refused += 1
                        reason = str(error)
                        verifier_refusals[reason] += 1
                        outcome["outcome"] = "verifier_refusal"
                        outcome["reason"] = reason
                    else:
                        verifier_accepted += 1
                        outcome["outcome"] = "verifier_acceptance"
                        outcome["verification_status"] = report.get("status")
                        # Deliberately continue. This audit is not a first-accepted-candidate search.
            chain = _sha256({"previous": chain, "event": outcome})
            if attempts >= attempt_sample:
                break
        if attempts >= attempt_sample:
            break

    seconds = time.perf_counter() - start
    result = _measurement(seconds, attempts, CANONICAL_CERTIFICATE_CAP)
    result.update({
        "program_cap": program_cap,
        "programs_seen": programs_seen,
        "structurally_valid_programs": structurally_valid,
        "requested_policy_attempts": attempt_sample,
        "sample_reached": attempts >= attempt_sample,
        "certificates_constructed": constructed,
        "scanner_refused": scanner_refused,
        "verifier_accepted": verifier_accepted,
        "verifier_refused": verifier_refused,
        "construction_refusals": dict(construction_refusals.most_common(20)),
        "scanner_refusals": dict(scanner_refusals.most_common(20)),
        "verifier_refusals": dict(verifier_refusals.most_common(20)),
        "event_digest": chain,
        "continues_after_neutral_acceptance": True,
    })
    return result


def build_report(
    *,
    enumeration_sample: int,
    policy_attempt_sample: int,
    policy_program_cap: int,
) -> dict[str, object]:
    enumeration = benchmark_enumerator(enumeration_sample)
    policy = benchmark_neutral_certificate_pipeline(policy_attempt_sample, policy_program_cap)
    enumeration_projection = enumeration["linear_projection_seconds"]
    policy_projection = policy["linear_projection_seconds"]
    combined_projection = None
    if isinstance(enumeration_projection, float) and isinstance(policy_projection, float):
        combined_projection = enumeration_projection + policy_projection

    report: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "neutral_only": True,
        "target_theorem_loaded": False,
        "qualification_loaded": False,
        "candidate_selection_executed": False,
        "scientific_verdict": None,
        "canonical_job_seconds": CANONICAL_JOB_SECONDS,
        "canonical_program_cap": CANONICAL_PROGRAM_CAP,
        "canonical_certificate_cap": CANONICAL_CERTIFICATE_CAP,
        "neutral_requirement_digest": _sha256(NEUTRAL_REQUIREMENT),
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "enumeration": enumeration,
        "neutral_certificate_pipeline": policy,
        "naive_additive_linear_projection_seconds": combined_projection,
        "projection_is_not_a_bound": True,
        "notes": [
            "The canonical search can stop before either frozen global cap.",
            "The certificate workload depends on program structure and theorem shape.",
            "This neutral sample therefore supports execution planning only; it is not a target rehearsal or runtime proof.",
        ],
    }
    report["report_digest"] = _sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enumeration-sample", type=_positive_integer, default=DEFAULT_ENUMERATION_SAMPLE)
    parser.add_argument("--policy-attempt-sample", type=_positive_integer, default=DEFAULT_POLICY_ATTEMPT_SAMPLE)
    parser.add_argument("--policy-program-cap", type=_positive_integer, default=DEFAULT_POLICY_PROGRAM_CAP)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = build_report(
            enumeration_sample=args.enumeration_sample,
            policy_attempt_sample=args.policy_attempt_sample,
            policy_program_cap=args.policy_program_cap,
        )
    except RuntimeAuditError as error:
        raise SystemExit(str(error)) from error
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
