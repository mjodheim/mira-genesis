"""Structural and anti-cheating validation for generated M092-B candidate artifacts.

This module does not search for a program and does not inspect qualification material.  It accepts
only the frozen K1 candidate surface, binds a certificate to the exact canonical program, and scans
candidate-supplied support artifacts for the table, mask, equality-chain and host-callback channels
precommitted in ``experiments/M092/PROTOCOL.json``.

Global mathematical correctness remains the responsibility of
``m092_certificate_verifier.py``.  Keeping the scanner separate makes both boundaries auditable:
this file imports only the frozen K1 kernel and neutral runtime vocabulary, and neither executes a
candidate nor tries to complete its certificate.
"""
from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence, Set
from typing import Any

from metamorphosis.m092_kernel import (
    INSTRUCTION_SET,
    JUMP_OPCODES,
    Instruction,
    KernelError,
    Program,
    program_digest,
    program_to_list,
    validate_program,
)
from metamorphosis.m092_runtime import canonical_bytes

SCANNER_SCHEMA = "m092-candidate-validation-v1"
SELFTEST_SCHEMA = "m092-anti-cheating-selftest-v1"

MAX_CANDIDATE_PROGRAM_LENGTH = 14
MAX_SUPPORT_ARTIFACT_BYTES = 1_000_000
MAX_SCAN_NODES = 100_000
MAX_SCAN_DEPTH = 32

ALLOWED_OPCODES = (
    "HALT",
    "LOADI",
    "MOV",
    "ADD",
    "SUB",
    "MUL",
    "JMP",
    "JZ",
    "JNZ",
    "JLT",
    "SPOP",
    "SPUSH",
)
FORBIDDEN_OPCODES = (
    "FAIL",
    "ARG",
    "SLEN",
    "SPEEK",
    "GETSLOT",
    "SETSLOT",
    "GETINPUT",
)
CANDIDATE_LITERAL_SET = (-1, 0, 1)

STRUCTURAL_CODES = (
    "program_is_well_formed",
    "program_length_within_frozen_bound",
    "opcodes_within_frozen_candidate_surface",
    "literals_within_frozen_set",
    "at_most_one_loop_header",
    "certificate_bound_to_exact_program",
)
ANTI_CHEATING_CODES = (
    "no_direct_output_table",
    "no_encoded_bit_mask",
    "no_equality_chain_lookup",
    "no_host_callback_or_import",
    "no_candidate_specific_fixture",
    "no_target_named_executable_artifact",
    "no_domain_sized_output_vector",
    "no_large_literal_output_set",
)

DIRECT_TABLE_KEYS = {
    "answers",
    "expected_outputs",
    "lookup",
    "lookup_table",
    "output_table",
    "outputs",
    "truth_table",
    "vectors",
}
MASK_KEYS = {"bit_mask", "bitmask", "bitset", "encoded_mask", "mask", "packed_outputs"}
CALLBACK_KEYS = {
    "callback",
    "callable",
    "host_callback",
    "host_function",
    "import",
    "imports",
    "module",
}
FIXTURE_KEYS = {
    "candidate_fixture",
    "expected_answer",
    "fixture",
    "fixtures",
    "gold_outputs",
}
TARGET_TOKENS = re.compile(
    r"(?:\bparity\b|\bmodulo\b|\bremainder\b|\bx\s*mod\s*2\b|\beven\b|\bodd\b)",
    re.IGNORECASE,
)
EQUALITY_TEST = re.compile(
    r"(?:\bx\b|\binput\b|\bvalue\b)\s*==\s*-?\d+", re.IGNORECASE,
)
PACKED_STRING = re.compile(
    r"(?:0x[0-9a-f]{8,}|0b[01]{16,}|[A-Za-z0-9+/]{24,}={0,2})", re.IGNORECASE,
)
IMPORT_OR_CALLBACK_TEXT = re.compile(
    r"(?:\bimport\s+[A-Za-z_]|\bfrom\s+[A-Za-z_].*\bimport\b|\blambda\b|\bcallback\b|\bhost[_ -]?function\b)",
    re.IGNORECASE,
)


class CandidateValidationError(ValueError):
    """The scanner itself received an unsupported or over-budget object."""


def _normal_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _looks_like_pair_table(value: object) -> bool:
    if not _is_sequence(value) or len(value) < 2:  # type: ignore[arg-type]
        return False
    rows = list(value)  # type: ignore[arg-type]
    return all(
        (_is_sequence(row) and len(row) == 2 and all(_is_scalar(item) for item in row))
        or (
            isinstance(row, Mapping)
            and any(_normal_key(key) in {"input", "x", "value"} for key in row)
            and any(_normal_key(key) in {"answer", "expected", "output", "y"} for key in row)
        )
        for row in rows
    )


def _looks_like_numeric_lookup(value: object) -> bool:
    if not isinstance(value, Mapping) or len(value) < 2:
        return False
    try:
        [int(str(key)) for key in value]
    except ValueError:
        return False
    return all(_is_scalar(item) for item in value.values())


def _json_safe(value: object, *, depth: int = 0, counter: list[int] | None = None) -> bool:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_SCAN_NODES or depth > MAX_SCAN_DEPTH:
        raise CandidateValidationError("support artifact exceeds the scanner resource bound")
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and _json_safe(item, depth=depth + 1, counter=counter)
            for key, item in value.items()
        )
    if _is_sequence(value):
        return all(_json_safe(item, depth=depth + 1, counter=counter) for item in value)  # type: ignore[arg-type]
    return False


def _finding(code: str, path: str, detail: str) -> dict[str, str]:
    return {"code": code, "path": path, "detail": detail}


def _scan_value(
    value: object,
    *,
    path: str,
    executable_support: bool,
    findings: list[dict[str, str]],
    depth: int = 0,
    counter: list[int] | None = None,
) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_SCAN_NODES or depth > MAX_SCAN_DEPTH:
        raise CandidateValidationError("support artifact exceeds the scanner resource bound")

    if callable(value):
        findings.append(_finding(
            "host_callback_or_import", path, "callable object is an executable host channel",
        ))
        return

    if isinstance(value, str):
        equality_matches = EQUALITY_TEST.findall(value)
        if len(equality_matches) >= 2:
            findings.append(_finding(
                "equality_chain_lookup", path, "multiple input equality tests encode a lookup chain",
            ))
        if PACKED_STRING.search(value):
            findings.append(_finding(
                "encoded_bit_mask", path, "packed hexadecimal, binary or base64-like payload",
            ))
        if IMPORT_OR_CALLBACK_TEXT.search(value):
            findings.append(_finding(
                "host_callback_or_import", path, "text contains an import, lambda or callback channel",
            ))
        if executable_support and TARGET_TOKENS.search(value):
            findings.append(_finding(
                "target_named_executable_artifact", path, "executable support names target semantics",
            ))
        return

    if isinstance(value, Mapping):
        if _looks_like_numeric_lookup(value):
            findings.append(_finding(
                "direct_output_table", path, "numeric-keyed scalar mapping is a lookup table",
            ))
        for key, item in value.items():
            normalized = _normal_key(key)
            item_path = f"{path}.{key}"
            if normalized in DIRECT_TABLE_KEYS and (
                _looks_like_pair_table(item) or _looks_like_numeric_lookup(item)
            ):
                findings.append(_finding(
                    "direct_output_table", item_path, "field contains input/output lookup rows",
                ))
            if normalized in MASK_KEYS and (
                isinstance(item, int) and not isinstance(item, bool) and abs(item) > 255
                or isinstance(item, str) and (PACKED_STRING.search(item) or len(item) >= 8)
            ):
                findings.append(_finding(
                    "encoded_bit_mask", item_path, "mask field carries packed output information",
                ))
            if normalized in CALLBACK_KEYS:
                findings.append(_finding(
                    "host_callback_or_import", item_path, "field declares a host callback or import",
                ))
            if normalized in FIXTURE_KEYS:
                findings.append(_finding(
                    "candidate_specific_fixture", item_path, "candidate artifact embeds a fixture or answer",
                ))
            if normalized in DIRECT_TABLE_KEYS and _is_sequence(item) and len(item) in (6, 3000, 7000):  # type: ignore[arg-type]
                findings.append(_finding(
                    "domain_sized_output_vector", item_path,
                    "ordered output field matches a frozen verification or qualification size",
                ))
            if normalized in {"answers", "expected_outputs", "literals", "outputs", "values"}:
                if isinstance(item, (Set, Sequence)) and not isinstance(item, (str, bytes, bytearray)):
                    numeric = [entry for entry in item if isinstance(entry, int) and not isinstance(entry, bool)]
                    if len(set(numeric)) >= 32:
                        findings.append(_finding(
                            "large_literal_output_set", item_path,
                            "large integer literal set can encode target outputs",
                        ))
            # A global certificate is required to carry this exact SHA-256 binding.  Hex-looking
            # data is suspicious in executable support, but the closed certificate field is the
            # control that prevents substitution and must not be mistaken for a packed table.
            if (
                not executable_support
                and normalized == "program_digest"
                and isinstance(item, str)
                and re.fullmatch(r"[0-9a-f]{64}", item)
            ):
                continue
            _scan_value(
                item, path=item_path, executable_support=executable_support,
                findings=findings, depth=depth + 1, counter=counter,
            )
        return

    if _is_sequence(value):
        if _looks_like_pair_table(value):
            findings.append(_finding(
                "direct_output_table", path, "unlabelled input/output row sequence",
            ))
        for index, item in enumerate(value):  # type: ignore[arg-type]
            _scan_value(
                item, path=f"{path}[{index}]", executable_support=executable_support,
                findings=findings, depth=depth + 1, counter=counter,
            )


def _deduplicate(findings: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    unique = {
        (str(item["code"]), str(item["path"]), str(item["detail"]))
        for item in findings
    }
    return [
        {"code": code, "path": path, "detail": detail}
        for code, path, detail in sorted(unique)
    ]


def _loop_headers(program: Sequence[Instruction]) -> set[int]:
    return {
        int(step[-1])
        for index, step in enumerate(program)
        if str(step[0]) in JUMP_OPCODES and int(step[-1]) <= index
    }


def _candidate_program_digest(program: Sequence[Instruction]) -> str:
    """Bind malformed candidates deterministically too, so refusal reporting never executes them."""

    try:
        return program_digest(program)
    except (IndexError, TypeError, ValueError):
        raw = [list(step) if _is_sequence(step) else [repr(step)] for step in program]
        return hashlib.sha256(canonical_bytes(raw)).hexdigest()


def validate_candidate_artifacts(
    program: Program,
    certificate: Mapping[str, object],
    *,
    support_artifacts: Sequence[object] = (),
) -> dict[str, object]:
    """Return a deterministic refusal/acceptance report without executing the candidate."""

    structural_failures: list[dict[str, str]] = []
    passed_structural: list[str] = []
    well_formed = True
    try:
        validate_program(program)
    except KernelError as error:
        well_formed = False
        structural_failures.append(_finding(
            "malformed_program", "program", f"K1 structural refusal: {error.code.value}",
        ))
    else:
        passed_structural.append("program_is_well_formed")

    if len(program) <= MAX_CANDIDATE_PROGRAM_LENGTH:
        passed_structural.append("program_length_within_frozen_bound")
    else:
        structural_failures.append(_finding(
            "program_length_exceeded", "program", "candidate exceeds fourteen instructions",
        ))

    bad_opcodes = sorted({
        "<empty>" if not step else str(step[0])
        for step in program
        if not step or str(step[0]) not in ALLOWED_OPCODES
    })
    if not bad_opcodes:
        passed_structural.append("opcodes_within_frozen_candidate_surface")
    else:
        structural_failures.append(_finding(
            "forbidden_opcode", "program", ",".join(bad_opcodes),
        ))

    bad_literals = sorted({
        int(step[2]) for step in program
        if len(step) == 3 and str(step[0]) == "LOADI"
        and isinstance(step[2], int) and not isinstance(step[2], bool)
        and int(step[2]) not in CANDIDATE_LITERAL_SET
    })
    if not bad_literals:
        passed_structural.append("literals_within_frozen_set")
    else:
        structural_failures.append(_finding(
            "forbidden_literal", "program", ",".join(str(item) for item in bad_literals),
        ))

    headers = _loop_headers(program) if well_formed else set()
    if len(headers) <= 1:
        passed_structural.append("at_most_one_loop_header")
    else:
        structural_failures.append(_finding(
            "multiple_loop_headers", "program", ",".join(str(item) for item in sorted(headers)),
        ))

    exact_digest = _candidate_program_digest(program)
    if certificate.get("program_digest") == exact_digest:
        passed_structural.append("certificate_bound_to_exact_program")
    else:
        structural_failures.append(_finding(
            "wrong_program_digest", "certificate.program_digest",
            "certificate digest differs from the exact canonical K1 program",
        ))

    scan_findings: list[dict[str, str]] = []
    _scan_value(
        certificate, path="certificate", executable_support=False, findings=scan_findings,
    )
    for index, artifact in enumerate(support_artifacts):
        if _json_safe(artifact):
            size = len(canonical_bytes(artifact))
            if size > MAX_SUPPORT_ARTIFACT_BYTES:
                raise CandidateValidationError("support artifact exceeds the byte bound")
        _scan_value(
            artifact, path=f"support[{index}]", executable_support=True,
            findings=scan_findings,
        )
    scan_findings = _deduplicate(scan_findings)
    observed_codes = {item["code"] for item in scan_findings}
    code_to_pass = {
        "direct_output_table": "no_direct_output_table",
        "encoded_bit_mask": "no_encoded_bit_mask",
        "equality_chain_lookup": "no_equality_chain_lookup",
        "host_callback_or_import": "no_host_callback_or_import",
        "candidate_specific_fixture": "no_candidate_specific_fixture",
        "target_named_executable_artifact": "no_target_named_executable_artifact",
        "domain_sized_output_vector": "no_domain_sized_output_vector",
        "large_literal_output_set": "no_large_literal_output_set",
    }
    passed_anti_cheating = [
        pass_code for finding_code, pass_code in code_to_pass.items()
        if finding_code not in observed_codes
    ]

    report: dict[str, object] = {
        "schema": SCANNER_SCHEMA,
        "program_digest": exact_digest,
        "program_length": len(program),
        "loop_headers": sorted(headers),
        "support_artifacts_scanned": len(support_artifacts),
        "candidate_executed": False,
        "qualification_read": False,
        "structural_findings": {
            "passed": passed_structural,
            "refusals": _deduplicate(structural_failures),
        },
        "anti_cheating_findings": {
            "passed": passed_anti_cheating,
            "refusals": scan_findings,
        },
        "accepted": not structural_failures and not scan_findings,
    }
    report["report_digest"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    return report


def _neutral_program() -> Program:
    return (
        ("SPOP", 0),
        ("LOADI", 1, 1),
        ("JZ", 0, 5),
        ("SUB", 0, 0, 1),
        ("JMP", 2),
        ("SPUSH", 0),
        ("HALT",),
    )


def run_anti_cheating_selftest() -> dict[str, object]:
    """Exercise the five frozen rejection fixtures and prove clean-state restoration."""

    program = _neutral_program()
    clean_bundle: dict[str, object] = {
        "program": program_to_list(program),
        "certificate": {"program_digest": program_digest(program)},
        "support_artifacts": [],
    }
    clean_digest_before = hashlib.sha256(canonical_bytes(clean_bundle)).hexdigest()

    def explosive_callback(_: int) -> int:
        raise AssertionError("the scanner must never execute a host callback")

    fixtures: list[tuple[str, str, dict[str, object]]] = []
    direct = copy.deepcopy(clean_bundle)
    direct["support_artifacts"] = [{
        "output_table": [[0, 0], [1, 1], [2, 0], [3, 1]],
    }]
    fixtures.append(("direct output table", "direct_output_table", direct))

    mask = copy.deepcopy(clean_bundle)
    mask["support_artifacts"] = [{"encoded_mask": "0b1010101010101010"}]
    fixtures.append(("encoded bit mask", "encoded_bit_mask", mask))

    equality = copy.deepcopy(clean_bundle)
    equality["support_artifacts"] = [{
        "expression": "0 if x == 0 else 1 if x == 1 else 0 if x == 2 else 1",
    }]
    fixtures.append(("equality-chain lookup", "equality_chain_lookup", equality))

    callback = copy.deepcopy(clean_bundle)
    callback["support_artifacts"] = [{"callback": explosive_callback}]
    fixtures.append(("host callback", "host_callback_or_import", callback))

    wrong_digest = copy.deepcopy(clean_bundle)
    wrong_digest["certificate"] = {"program_digest": "0" * 64}
    fixtures.append(("wrong-program-digest certificate", "wrong_program_digest", wrong_digest))

    results: list[dict[str, object]] = []
    for name, expected_code, fixture in fixtures:
        report = validate_candidate_artifacts(
            program,
            fixture["certificate"],  # type: ignore[arg-type]
            support_artifacts=fixture["support_artifacts"],  # type: ignore[arg-type]
        )
        refusal_codes = {
            item["code"]
            for section in ("structural_findings", "anti_cheating_findings")
            for item in report[section]["refusals"]  # type: ignore[index]
        }
        results.append({
            "fixture": name,
            "expected_code": expected_code,
            "observed_codes": sorted(refusal_codes),
            "rejected": report["accepted"] is False and expected_code in refusal_codes,
        })
        if hashlib.sha256(canonical_bytes(clean_bundle)).hexdigest() != clean_digest_before:
            raise CandidateValidationError("anti-cheating fixture mutated the clean baseline")

    clean_report = validate_candidate_artifacts(
        program,
        clean_bundle["certificate"],  # type: ignore[arg-type]
        support_artifacts=clean_bundle["support_artifacts"],  # type: ignore[arg-type]
    )
    clean_digest_after = hashlib.sha256(canonical_bytes(clean_bundle)).hexdigest()
    result: dict[str, object] = {
        "schema": SELFTEST_SCHEMA,
        "fixtures": results,
        "all_five_rejected": len(results) == 5 and all(item["rejected"] for item in results),
        "clean_state_digest_before": clean_digest_before,
        "clean_state_digest_after": clean_digest_after,
        "clean_state_restored": clean_digest_before == clean_digest_after,
        "clean_candidate_accepted_after_fixtures": clean_report["accepted"],
        "candidate_executed": False,
        "qualification_read": False,
    }
    result["selftest_digest"] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


__all__ = [
    "ALLOWED_OPCODES",
    "ANTI_CHEATING_CODES",
    "CANDIDATE_LITERAL_SET",
    "CandidateValidationError",
    "FORBIDDEN_OPCODES",
    "MAX_CANDIDATE_PROGRAM_LENGTH",
    "SCANNER_SCHEMA",
    "SELFTEST_SCHEMA",
    "STRUCTURAL_CODES",
    "run_anti_cheating_selftest",
    "validate_candidate_artifacts",
]
