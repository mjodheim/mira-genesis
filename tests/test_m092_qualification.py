from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m092_adoption import (
    build_extended_bundle,
    downstream_primitive_id,
    sha256_bytes,
    validate_candidate_for_adoption,
)
from metamorphosis.m092_certificate_generator import generate_candidate_certificates
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_qualification import (
    CONTROL_BUDGET_MULTIPLIER,
    QualificationError,
    QualificationTask,
    run_qualification_ledger,
)
from metamorphosis.m092_runtime import RuntimeLanguage
from metamorphosis.m092_substrate_state import SubstrateState

BASE = Path("experiments/M092/SUBSTRATE_A.json")
NEUTRAL_PROGRAM = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _states() -> tuple[RuntimeLanguage, SubstrateState, RuntimeLanguage, SubstrateState, str]:
    raw = BASE.read_bytes()
    base = json.loads(raw)
    language = RuntimeLanguage.from_dict(base["language"])
    substrate = SubstrateState.from_dict(base["substrate"])
    certificate = next(
        generate_candidate_certificates(NEUTRAL_PROGRAM, COUNTDOWN_POSTCONDITION, limit=64)
    )
    receipt = validate_candidate_for_adoption(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )
    bundle = build_extended_bundle(
        language,
        substrate,
        NEUTRAL_PROGRAM,
        receipt=receipt,
        source_bundle_sha256=sha256_bytes(raw),
    )
    return (
        language,
        substrate,
        RuntimeLanguage.from_dict(bundle["language"]),
        SubstrateState.from_dict(bundle["substrate"]),
        downstream_primitive_id(NEUTRAL_PROGRAM),
    )


def _tasks() -> list[QualificationTask]:
    return [
        QualificationTask("small", f"small-{value}", value, 0) for value in range(10)
    ] + [
        QualificationTask("larger", f"larger-{value}", value, 0) for value in range(10, 20)
    ]


def test_qualification_refuses_before_adoption_or_fresh_reload() -> None:
    base_language, base_substrate, language, substrate, primitive_id = _states()
    with pytest.raises(QualificationError):
        run_qualification_ledger(
            _tasks(),
            primitive_id=primitive_id,
            extended_language=language,
            extended_substrate=substrate,
            control_language=base_language,
            control_substrate=base_substrate,
            fresh_process_loaded=False,
            adoption_committed=True,
        )
    with pytest.raises(QualificationError):
        run_qualification_ledger(
            _tasks(),
            primitive_id=primitive_id,
            extended_language=language,
            extended_substrate=substrate,
            control_language=base_language,
            control_substrate=base_substrate,
            fresh_process_loaded=True,
            adoption_committed=False,
        )


def test_two_families_and_ten_tasks_each_are_required() -> None:
    base_language, base_substrate, language, substrate, primitive_id = _states()
    with pytest.raises(QualificationError):
        run_qualification_ledger(
            [QualificationTask("one", f"t-{value}", value, 0) for value in range(10)],
            primitive_id=primitive_id,
            extended_language=language,
            extended_substrate=substrate,
            control_language=base_language,
            control_substrate=base_substrate,
            fresh_process_loaded=True,
            adoption_committed=True,
        )


def test_control_multiplier_is_real_execution_count_not_reported_arithmetic() -> None:
    base_language, base_substrate, language, substrate, primitive_id = _states()
    tasks = _tasks()
    ledger = run_qualification_ledger(
        tasks,
        primitive_id=primitive_id,
        extended_language=language,
        extended_substrate=substrate,
        control_language=base_language,
        control_substrate=base_substrate,
        fresh_process_loaded=True,
        adoption_committed=True,
    )
    assert ledger["extended_attempts_executed"] == len(tasks)
    assert ledger["control_attempts_executed"] == len(tasks) * CONTROL_BUDGET_MULTIPLIER
    assert len(ledger["extended_records"]) == len(tasks)
    assert len(ledger["control_records"]) == len(tasks) * CONTROL_BUDGET_MULTIPLIER
    assert all(record["success"] is True for record in ledger["extended_records"])
    assert all(record["success"] is False for record in ledger["control_records"])
    assert {record["refusal_code"] for record in ledger["control_records"]} == {
        "undefined_primitive"
    }


def test_multiplier_cannot_be_reported_without_execution() -> None:
    base_language, base_substrate, language, substrate, primitive_id = _states()
    with pytest.raises(QualificationError):
        run_qualification_ledger(
            _tasks(),
            primitive_id=primitive_id,
            extended_language=language,
            extended_substrate=substrate,
            control_language=base_language,
            control_substrate=base_substrate,
            fresh_process_loaded=True,
            adoption_committed=True,
            control_multiplier=9,
        )
