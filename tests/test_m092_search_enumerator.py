"""The M092-B proposal stream is frozen, bounded and resumable before target search."""
from __future__ import annotations

import ast
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from metamorphosis.m092_kernel import INSTRUCTION_SET, JUMP_OPCODES
from metamorphosis.m092_search_enumerator import (
    CANDIDATE_ALLOWED_OPCODES,
    CANDIDATE_CAP,
    CANDIDATE_FORBIDDEN_OPCODES,
    CANDIDATE_LITERALS,
    MAX_CANDIDATE_PROGRAM_LENGTH,
    MIN_ITERATIVE_PROGRAM_LENGTH,
    SEARCH_SEED,
    EnumerationAudit,
    EnumerationCursor,
    SearchEnumerationError,
    audit_prefix,
    canonical_layer_cardinality,
    enumerate_programs,
    search_layer_plan,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "experiments" / "M092" / "PROTOCOL.json").read_text())
SOURCE = ROOT / "metamorphosis" / "m092_search_enumerator.py"


def test_frozen_search_surface_matches_the_protocol() -> None:
    search = PROTOCOL["search"]
    kernel = PROTOCOL["k1_frozen"]
    assert SEARCH_SEED == search["deterministic_seed"]
    assert CANDIDATE_CAP == search["candidate_cap"]
    assert MAX_CANDIDATE_PROGRAM_LENGTH == search["candidate_program_max_length"]
    assert list(CANDIDATE_LITERALS) == search["candidate_literal_set"]
    assert list(CANDIDATE_ALLOWED_OPCODES) == kernel["candidate_allowed_opcodes"]
    assert list(CANDIDATE_FORBIDDEN_OPCODES) == kernel["candidate_forbidden_opcodes"]
    assert set(CANDIDATE_ALLOWED_OPCODES) | set(CANDIDATE_FORBIDDEN_OPCODES) == set(
        INSTRUCTION_SET
    )
    assert set(CANDIDATE_ALLOWED_OPCODES).isdisjoint(CANDIDATE_FORBIDDEN_OPCODES)


def test_first_five_hundred_twelve_proposals_are_stable_and_breadth_first() -> None:
    records = list(enumerate_programs(limit=512))
    assert [record.ordinal for record in records] == list(range(1, 513))
    assert [record.program_length for record in records] == sorted(
        record.program_length for record in records
    )
    assert records[0].program == (
        ("SPOP", 0),
        ("JLT", 0, 1, 4),
        ("SUB", 2, 2, 2),
        ("JMP", 1),
        ("SPUSH", 1),
        ("HALT",),
    )
    assert records[0].program_length == MIN_ITERATIVE_PROGRAM_LENGTH
    assert all(len(record.program) <= MAX_CANDIDATE_PROGRAM_LENGTH for record in records)
    assert all(
        set(str(step[0]) for step in record.program) <= set(CANDIDATE_ALLOWED_OPCODES)
        for record in records
    )
    assert all(
        len(record.loop_headers) <= 1
        for record in records
        if record.structurally_valid
    )

    audit = audit_prefix(limit=512)
    assert audit.generated_programs == 512
    assert audit.structurally_invalid_programs == 0
    assert audit.last_program_digest == (
        "6e4a82aeb2c08e1a1633ea9e439de92eef30accf0d3b1cf256666831d4b9fa39"
    )
    assert audit.event_chain_digest == (
        "ec345bf19bda55d5328b96a4df021a99abaa9bf53ff8face63f5ab6803e3268a"
    )
    assert audit.last_cursor is not None
    assert audit.last_cursor.cursor_digest == (
        "370ea96fc80948f142142e15653c5daefb7c1054a675a4e0a8a049d7c766192e"
    )


def test_layer_plan_reaches_every_length_before_the_frozen_cap() -> None:
    plan = search_layer_plan()
    assert [layer.program_length for layer in plan] == list(
        range(MIN_ITERATIVE_PROGRAM_LENGTH, MAX_CANDIDATE_PROGRAM_LENGTH + 1)
    )
    assert canonical_layer_cardinality(6) == 3_324
    assert canonical_layer_cardinality(7) == 2_838_822
    assert plan[0].truncated is False
    assert all(layer.emitted_programs > 0 for layer in plan)
    assert all(layer.truncated for layer in plan[1:])
    assert sum(layer.emitted_programs for layer in plan) == CANDIDATE_CAP


def test_registers_are_alpha_normalised_by_first_occurrence() -> None:
    for record in enumerate_programs(limit=1_000):
        frontier = 0
        for step in record.program:
            roles = INSTRUCTION_SET[str(step[0])]
            for operand, role in zip(step[1:], roles, strict=True):
                if role != "r":
                    continue
                assert int(operand) <= frontier + 1
                frontier = max(frontier, int(operand))


def test_resume_cursor_reproduces_the_uninterrupted_stream_and_audit() -> None:
    uninterrupted_records = list(enumerate_programs(limit=400))
    first_records = list(enumerate_programs(limit=137))
    cursor = EnumerationCursor.from_dict(first_records[-1].cursor.to_dict())
    resumed_records = list(enumerate_programs(limit=263, cursor=cursor))
    assert [record.program_digest for record in first_records + resumed_records] == [
        record.program_digest for record in uninterrupted_records
    ]
    assert resumed_records[0].ordinal == 138

    uninterrupted_audit = audit_prefix(limit=400)
    first_audit = audit_prefix(limit=137)
    restored_audit = EnumerationAudit.from_dict(first_audit.to_dict())
    resumed_audit = audit_prefix(
        limit=263,
        cursor=restored_audit.last_cursor,
        audit=restored_audit,
    )
    assert resumed_audit.to_dict() == uninterrupted_audit.to_dict()


def test_resume_crosses_an_exhausted_breadth_layer_exactly_once() -> None:
    length_six_count = search_layer_plan()[0].emitted_programs
    first = list(enumerate_programs(limit=length_six_count))
    assert len(first) == 3_324
    assert all(record.program_length == 6 for record in first)
    resumed = list(enumerate_programs(limit=3, cursor=first[-1].cursor))
    assert [record.ordinal for record in resumed] == [3_325, 3_326, 3_327]
    assert all(record.program_length == 7 for record in resumed)
    assert resumed[0].cursor.emitted_in_length == 1


def test_cursor_and_audit_tampering_fail_closed() -> None:
    audit = audit_prefix(limit=20)
    assert audit.last_cursor is not None

    cursor_payload = audit.last_cursor.to_dict()
    cursor_payload["generated_programs"] = 19
    with pytest.raises(SearchEnumerationError, match="cursor digest differs"):
        EnumerationCursor.from_dict(cursor_payload)

    audit_payload = copy.deepcopy(audit.to_dict())
    audit_payload["candidate_executed"] = True
    with pytest.raises(SearchEnumerationError, match="forbidden action"):
        EnumerationAudit.from_dict(audit_payload)

    audit_payload = copy.deepcopy(audit.to_dict())
    audit_payload["generated_programs"] = 19
    with pytest.raises(SearchEnumerationError, match="audit and cursor counts differ"):
        EnumerationAudit.from_dict(audit_payload)

    record = next(enumerate_programs(limit=1))
    forged = replace(record, program_digest="0" * 64)
    with pytest.raises(SearchEnumerationError, match="program digest differs"):
        EnumerationAudit().append(forged)


def test_candidate_cap_is_enforced_before_enumeration() -> None:
    with pytest.raises(SearchEnumerationError, match="candidate cap"):
        list(enumerate_programs(limit=CANDIDATE_CAP + 1))
    with pytest.raises(SearchEnumerationError, match="non-negative integer"):
        list(enumerate_programs(limit=-1))


def test_structural_classification_is_recomputed_without_execution() -> None:
    records = list(enumerate_programs(limit=30))
    assert all(record.structurally_valid for record in records)
    assert all(not record.structural_refusals for record in records)
    forged = replace(
        records[0],
        structurally_valid=False,
        structural_refusals=("unreachable_instruction",),
    )
    with pytest.raises(SearchEnumerationError, match="classification differs"):
        EnumerationAudit().append(forged)


def test_enumerator_import_boundary_has_no_verifier_builder_or_qualification_path() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    project_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(
                alias.name for alias in node.names if alias.name.startswith("metamorphosis")
            )
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("metamorphosis"):
            project_imports.add(node.module or "")
    assert project_imports == {
        "metamorphosis.m092_kernel",
        "metamorphosis.m092_runtime",
    }
    assert "execute_program" not in {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "m092_certificate_verifier" not in source
    assert "m092_candidate_validation" not in source
    assert "QUALIFICATION.json" not in source
    assert "parity" not in source.lower()


def test_jump_targets_are_in_program_and_literals_are_frozen() -> None:
    for record in enumerate_programs(limit=1_000):
        for index, step in enumerate(record.program):
            opcode = str(step[0])
            roles = INSTRUCTION_SET[opcode]
            for operand, role in zip(step[1:], roles, strict=True):
                if role == "i":
                    assert int(operand) in CANDIDATE_LITERALS
                elif role == "t":
                    assert 0 <= int(operand) < len(record.program)
            if opcode in JUMP_OPCODES and int(step[-1]) <= index:
                assert int(step[-1]) in record.loop_headers
