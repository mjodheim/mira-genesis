"""M063 falsifiers for transfer of arrangement synthesis to a checksum body."""
from __future__ import annotations

from dataclasses import replace
import inspect
import itertools

import pytest

from metamorphosis.m061_structural_discovery import M060_AUTHORED_STRUCTURAL
from metamorphosis.m063_control_transfer import (
    CHECKSUM_REQUIRED,
    HIDDEN_CASES,
    M063Error,
    PRESUPPOSED,
    PUBLIC_CASES,
    STEP_NAMES,
    ChecksumArrangement,
    candidate_space,
    case_passes,
    emit_arrangement,
    evaluate_arrangements,
    evaluate_copy_negative_control,
    run_m063_control_transfer,
    synthesize_checksum_arrangement,
    validate_arrangement,
    validate_survivor_class,
)


REGIONS = {"block": 0x02, "loop": 0x03}
OPCODES = dict(M060_AUTHORED_STRUCTURAL)


@pytest.fixture(scope="module")
def synthesis():
    return synthesize_checksum_arrangement(OPCODES, REGIONS)


@pytest.fixture(scope="module")
def manifest():
    return run_m063_control_transfer()


def test_the_transferred_grammar_constructs_96_distinct_arrangements():
    candidates = candidate_space()

    assert len(candidates) == 2 * 2 * 4 * 6 == 96
    assert len({candidate.digest() for candidate in candidates}) == len(candidates)
    assert {candidate.step_order for candidate in candidates} == set(itertools.permutations(STEP_NAMES))


def test_public_synthesis_has_no_hidden_case_parameter(synthesis):
    assert synthesis.candidate_count == 96
    assert synthesis.public_survivors
    assert synthesis.selected in synthesis.public_survivors
    assert "hidden_cases" not in inspect.signature(synthesize_checksum_arrangement).parameters


def test_selected_checksum_returns_the_sum_without_writing_memory(synthesis):
    selected = synthesis.observations[synthesis.selected.digest()]
    observations = selected["cases"]

    assert selected["import_count"] == 0
    for case in PUBLIC_CASES:
        observation = observations[case.name]
        assert observation["return_value"] == case.expected()
        assert observation["memory_unchanged"] is True
        assert case_passes(observation, case)


def test_every_public_survivor_passes_independent_hidden_admission(synthesis):
    verdict = validate_survivor_class(synthesis.public_survivors, OPCODES, REGIONS)

    assert verdict["candidate_count"] == len(synthesis.public_survivors)
    assert verdict["accepted_count"] == len(synthesis.public_survivors)
    assert verdict["all_accepted"] is True


def test_selected_arrangement_passes_disjoint_hidden_cases(synthesis):
    verdict = validate_arrangement(synthesis.selected, OPCODES, REGIONS)

    assert verdict["accepted"] is True
    assert verdict["case_count"] == len(HIDDEN_CASES) == 3
    assert all(verdict["passed"].values())


def test_region_effect_ambiguity_is_readmitted_for_the_new_body(synthesis):
    for exit_region in (0x02, 0x06):
        verdict = validate_survivor_class(
            synthesis.public_survivors, OPCODES, {"block": exit_region, "loop": 0x03}
        )
        assert verdict["all_accepted"] is True, hex(exit_region)


def test_the_m062_copy_body_is_a_rejected_cross_body_control():
    control = evaluate_copy_negative_control(OPCODES, REGIONS)

    assert control["rejected"] is True
    assert control["passed"]["public_zero"] is True
    assert not all(control["passed"].values())


def test_a_wrong_predicate_fails_public_checksum_evidence(synthesis):
    wrong = replace(synthesis.selected, condition="zero_le_remaining")
    result = evaluate_arrangements((wrong,), OPCODES, REGIONS, PUBLIC_CASES)[wrong.digest()]["cases"]

    assert any(not case_passes(result[case.name], case) for case in PUBLIC_CASES)


def test_advancing_before_loading_is_falsified_by_distinct_bytes():
    wrong = ChecksumArrangement(
        "block_then_loop",
        "remaining_le_zero",
        0,
        ("advance_source", "accumulate_byte", "decrement_remaining"),
    )
    result = evaluate_arrangements((wrong,), OPCODES, REGIONS, PUBLIC_CASES)[wrong.digest()]["cases"]

    assert not case_passes(result["public_five"], PUBLIC_CASES[2])


def test_an_exit_check_after_accumulation_is_caught_by_zero_length_case():
    wrong = ChecksumArrangement(
        "block_then_loop",
        "remaining_le_zero",
        1,
        ("accumulate_byte", "advance_source", "decrement_remaining"),
    )
    result = evaluate_arrangements((wrong,), OPCODES, REGIONS, PUBLIC_CASES)[wrong.digest()]["cases"]

    assert not case_passes(result["public_zero"], PUBLIC_CASES[0])


def test_emission_refuses_missing_discovered_effects(synthesis):
    partial = dict(OPCODES)
    partial.pop("i32.load8_u")

    with pytest.raises(M063Error, match="i32.load8_u"):
        emit_arrangement(synthesis.selected, partial, REGIONS)
    with pytest.raises(M063Error, match="loop"):
        emit_arrangement(synthesis.selected, OPCODES, {"block": 0x02})


def test_invalid_checksum_arrangements_fail_before_emission():
    with pytest.raises(M063Error, match="exactly once"):
        ChecksumArrangement(
            "block_then_loop",
            "remaining_le_zero",
            0,
            ("accumulate_byte", "accumulate_byte", "decrement_remaining"),
        )


def test_selected_module_replays_byte_identically(synthesis):
    first = emit_arrangement(synthesis.selected, OPCODES, REGIONS)
    second = emit_arrangement(replace(synthesis.selected), dict(OPCODES), dict(REGIONS))

    assert first == second
    assert first.startswith(b"\x00asm\x01\x00\x00\x00")


def test_floor_and_remaining_authorship_are_explicit():
    assert "local declaration encoding" in PRESUPPOSED
    assert "label-depth encoding" in PRESUPPOSED
    assert set(CHECKSUM_REQUIRED) <= set(OPCODES)


def test_complete_manifest_derives_the_transfer_verdict(manifest):
    value = manifest.to_dict()

    assert manifest.digest() == "c2f0cdb05bef741b003740c2148fe3ad5d8bf78b802085c8234fa77fe0779107"
    assert value["m061_scaffolds_replayed"] == 6
    assert value["region_opcode_space_scanned"] == 256
    assert value["synthesis"]["candidate_count"] == 96
    assert value["synthesis"]["public_survivor_count"] > 0
    assert value["independent_validation"]["accepted"] is True
    assert value["copy_body_negative_control"]["rejected"] is True
    assert value["selected_module_imports"] == 0
    for verdict in value["region_effect_class_hidden_validation"].values():
        assert verdict["candidate_count"] == verdict["accepted_count"]
        assert verdict["all_accepted"] is True


def test_complete_manifest_preserves_claim_and_authority_boundaries(manifest):
    value = manifest.to_dict()

    assert value["emitter_inputs_from_discovery"]["operation_labels"] == sorted(CHECKSUM_REQUIRED)
    assert value["authored_elements"] == [
        "checksum-task decomposition",
        "three checksum atomic steps",
        "finite transferred Cartesian grammar",
        "checksum WebAssembly emitter",
        "local, blocktype and label-depth encoding",
        "public and hidden cases",
    ]
    assert "arbitrary compiler synthesis" in value["claim_exclusions"]
    assert value["external_authority_not_granted"] == [
        "network", "repository", "credentials", "deployment", "production systems"
    ]
    assert value["canonical"] is False
    assert value["replay_identical"] is True
