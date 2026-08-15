from __future__ import annotations

import hashlib
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
    validate_reproduction_gate,
)
from metamorphosis.m092_runtime import RuntimeLanguage, canonical_bytes
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


def _rehash(value: dict[str, object]) -> dict[str, object]:
    payload = {key: item for key, item in value.items() if key != "result_digest"}
    result = dict(payload)
    result["result_digest"] = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    return result


def _canonical_result() -> dict[str, object]:
    return _rehash({
        "schema": "m092-canonical-criterion-search-result/2",
        "status": "first-canonical-criterion-search-result",
        "arming_head_sha": "a" * 40,
        "frozen_parent_sha": "b" * 40,
        "canonical_search_attempt": 1,
        "canonical_transport_mode": "immutable-artifact-segment-chain",
        "transport_segments": 1,
        "terminal_segment_index": 0,
        "terminal_segment_digest": "c" * 64,
        "terminal_segment": {},
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "qualification_forbidden": True,
        "independent_reproduction_required": True,
        "qualification_may_begin_before_reproduction": False,
        "target_search_executed": True,
        "qualification_loaded": False,
        "candidate_executed_for_selection": False,
        "program_limit_requested": 2_000_000,
        "terminal_search_status": "candidate_selected",
        "candidate_selected": True,
        "generated_programs": 17,
        "certificate_policy_attempts": 23,
        "certificates_constructed": 4,
        "surviving_candidates": 1,
        "marker_digest": "d" * 64,
        "marker": {},
        "search_state": {},
    })


def _reproduction_result(canonical: dict[str, object]) -> dict[str, object]:
    return _rehash({
        "schema": "m092-independent-reproduction-result/1",
        "status": "independent-reproduction-match",
        "arming_head_sha": "a" * 40,
        "arming_parent_sha": "b" * 40,
        "source_canonical_run_id": 11,
        "source_canonical_artifact_id": 12,
        "source_canonical_artifact_digest": "sha256:" + "e" * 64,
        "source_canonical_result_digest": canonical["result_digest"],
        "terminal_reproduction_segment_index": 0,
        "terminal_reproduction_segment_digest": "f" * 64,
        "canonical_result_content_loaded_only_after_reproduction_terminal": True,
        "reproduction_from_genesis": True,
        "reproduction_only": True,
        "target_search_rerolled": False,
        "qualification_loaded": False,
        "candidate_executed_for_selection": False,
        "canonical_terminal_status": "candidate_selected",
        "reproduced_terminal_status": "candidate_selected",
        "canonical_state_digest": "1" * 64,
        "reproduced_state_digest": "1" * 64,
        "state_byte_identical": True,
        "qualification_gate_open": True,
        "reproduced_search_state": {},
    })


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


def test_exact_independent_reproduction_opens_gate() -> None:
    canonical = _canonical_result()
    reproduction = _reproduction_result(canonical)
    gate = validate_reproduction_gate(canonical, reproduction)
    assert gate["qualification_gate_open"] is True
    assert gate["canonical_result_digest"] == canonical["result_digest"]
    assert gate["reproduction_result_digest"] == reproduction["result_digest"]


@pytest.mark.parametrize("field,value", [
    ("state_byte_identical", False),
    ("qualification_gate_open", False),
    ("status", "independent-reproduction-mismatch"),
])
def test_reproduction_mismatch_never_opens_gate(field: str, value: object) -> None:
    canonical = _canonical_result()
    reproduction = _reproduction_result(canonical)
    reproduction[field] = value
    reproduction = _rehash(reproduction)
    with pytest.raises(QualificationError):
        validate_reproduction_gate(canonical, reproduction)


def test_reproduction_bound_to_other_canonical_result_is_rejected() -> None:
    canonical = _canonical_result()
    reproduction = _reproduction_result(canonical)
    reproduction["source_canonical_result_digest"] = "9" * 64
    reproduction = _rehash(reproduction)
    with pytest.raises(QualificationError):
        validate_reproduction_gate(canonical, reproduction)


def test_no_candidate_cannot_enter_qualification_even_with_rehashed_results() -> None:
    canonical = _canonical_result()
    canonical["terminal_search_status"] = "program_budget_exhausted"
    canonical["candidate_selected"] = False
    canonical["surviving_candidates"] = 0
    canonical = _rehash(canonical)
    reproduction = _reproduction_result(canonical)
    reproduction["canonical_terminal_status"] = "program_budget_exhausted"
    reproduction["reproduced_terminal_status"] = "program_budget_exhausted"
    reproduction = _rehash(reproduction)
    with pytest.raises(QualificationError):
        validate_reproduction_gate(canonical, reproduction)
