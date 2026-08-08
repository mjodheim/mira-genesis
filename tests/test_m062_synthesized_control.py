"""M062 falsifications for region discovery and bounded arrangement synthesis."""
from __future__ import annotations

from dataclasses import replace
import inspect

import pytest

from metamorphosis.m061_structural_discovery import M060_AUTHORED_STRUCTURAL, probe
from metamorphosis.m062_synthesized_control import (
    CONDITIONS,
    HIDDEN_CASES,
    M062Error,
    PRESUPPOSED,
    PUBLIC_CASES,
    Arrangement,
    _region_scaffold,
    candidate_space,
    emit_arrangement,
    evaluate_arrangements,
    run_m062_synthesized_control,
    scan_region_openers,
    synthesize_arrangement,
    validate_arrangement,
    validate_survivor_class,
)


REGIONS = {"block": 0x02, "loop": 0x03}
OPCODES = dict(M060_AUTHORED_STRUCTURAL)


@pytest.fixture(scope="module")
def synthesis():
    return synthesize_arrangement(OPCODES, REGIONS)


@pytest.fixture(scope="module")
def manifest():
    return run_m062_synthesized_control()


def test_the_grammar_constructs_480_distinct_arrangements():
    candidates = candidate_space()

    assert len(candidates) == 2 * 2 * 5 * 24 == 480
    assert len({candidate.digest() for candidate in candidates}) == len(candidates)
    assert {candidate.topology for candidate in candidates} == {
        "block_then_loop", "loop_then_block"
    }
    assert {candidate.condition for candidate in candidates} == set(CONDITIONS)


def test_a_branch_makes_block_and_loop_observably_different():
    block = probe(_region_scaffold(0x02, OPCODES["br"], OPCODES["i32.add"]),
                  ({"args": [], "memory": []},), 2.0)
    loop = probe(_region_scaffold(0x03, OPCODES["br"], OPCODES["i32.add"]),
                 ({"args": [], "memory": []},), 2.0)

    assert block["outcome"] == "observed"
    assert block["observations"] == [8]
    assert loop["outcome"] == "did_not_terminate"


def test_the_region_scan_uses_discovered_dependencies_and_recovers_both_openers():
    scan = scan_region_openers(OPCODES)

    assert scan["scanned"] == 256
    assert scan["block_matches"] == ["0x02", "0x06"]
    assert scan["loop_matches"] == ["0x03"]
    assert scan["resolved"] == REGIONS
    assert scan["effect_classes"] == {
        "exit_region": [0x02, 0x06], "repeat_region": [0x03]
    }
    assert scan["uniquely_determined"] == {
        "exit_region": False, "repeat_region": True
    }
    assert scan["witnesses_found"] == {"block": True, "loop": True}


def test_the_region_ambiguity_survives_whole_program_hidden_validation(synthesis):
    for exit_region in (0x02, 0x06):
        verdict = validate_arrangement(
            synthesis.selected, OPCODES, {"block": exit_region, "loop": 0x03}
        )
        assert verdict["accepted"] is True, hex(exit_region)


def test_public_search_selects_a_valid_arrangement_without_hidden_cases(synthesis):
    assert synthesis.candidate_count == 480
    assert synthesis.public_survivors
    assert synthesis.selected in synthesis.public_survivors
    assert "hidden_cases" not in inspect.signature(synthesize_arrangement).parameters

    selected_observations = synthesis.observations[synthesis.selected.digest()]["cases"]
    for case in PUBLIC_CASES:
        assert selected_observations[case.name]["destination_window"] == (
            case.expected_destination_window()
        )


def test_independent_hidden_validation_accepts_the_selected_arrangement(synthesis):
    verdict = validate_arrangement(synthesis.selected, OPCODES, REGIONS)

    assert verdict["accepted"] is True
    assert verdict["case_count"] == len(HIDDEN_CASES) == 3
    assert all(verdict["passed"].values())


def test_independent_hidden_validation_accepts_every_public_survivor(synthesis):
    verdict = validate_survivor_class(synthesis.public_survivors, OPCODES, REGIONS)

    assert verdict["candidate_count"] == len(synthesis.public_survivors) == 16
    assert verdict["accepted_count"] == 16
    assert verdict["all_accepted"] is True


def test_a_wrong_predicate_is_rejected_by_the_public_falsifier(synthesis):
    wrong = replace(synthesis.selected, condition="zero_le_remaining")
    result = evaluate_arrangements((wrong,), OPCODES, REGIONS, PUBLIC_CASES)[wrong.digest()]

    assert any(
        result["cases"][case.name]["destination_window"] != case.expected_destination_window()
        for case in PUBLIC_CASES
    )


def test_an_exit_check_after_copy_is_caught_by_the_zero_length_case(synthesis):
    order = ("copy_byte", "advance_source", "advance_destination", "decrement_remaining")
    wrong = Arrangement("block_then_loop", "remaining_le_zero", 1, order)
    result = evaluate_arrangements((wrong,), OPCODES, REGIONS, PUBLIC_CASES)[wrong.digest()]

    zero = PUBLIC_CASES[0]
    assert result["cases"][zero.name]["destination_window"] != zero.expected_destination_window()


def test_the_emitter_has_no_authored_fallback_for_a_missing_discovery(synthesis):
    partial = dict(OPCODES)
    partial.pop("br_if")

    with pytest.raises(M062Error, match="br_if"):
        emit_arrangement(synthesis.selected, partial, REGIONS)
    with pytest.raises(M062Error, match="loop"):
        emit_arrangement(synthesis.selected, OPCODES, {"block": 0x02})


def test_the_selected_module_is_deterministic(synthesis):
    first = emit_arrangement(synthesis.selected, OPCODES, REGIONS)
    second = emit_arrangement(replace(synthesis.selected), dict(OPCODES), dict(REGIONS))

    assert first == second
    assert first.startswith(b"\x00asm\x01\x00\x00\x00")


def test_the_floor_and_boundaries_are_explicit():
    assert "empty blocktype 0x40" in PRESUPPOSED
    assert "i32 result blocktype 0x7f in the region probe" in PRESUPPOSED
    assert "label-depth encoding" in PRESUPPOSED
    assert "module framing" in PRESUPPOSED


def test_an_invalid_arrangement_is_refused_before_emission():
    with pytest.raises(M062Error, match="exactly once"):
        Arrangement(
            "block_then_loop", "remaining_le_zero", 0,
            ("copy_byte", "copy_byte", "advance_source", "decrement_remaining"),
        )


def test_the_complete_manifest_is_derived_from_discovery_and_validation(manifest):
    value = manifest.to_dict()

    assert value["m061_scaffolds_replayed"] == 6
    assert value["region_opcode_space_scanned"] == 256
    assert value["region_effect_classes"] == {
        "exit_region": ["0x2", "0x6"], "repeat_region": ["0x3"]
    }
    assert value["synthesis"]["candidate_count"] == 480
    assert value["synthesis"]["public_survivor_count"] == 16
    assert value["independent_validation"]["accepted"] is True
    for verdict in value["region_effect_class_hidden_validation"].values():
        assert verdict["candidate_count"] == verdict["accepted_count"] == 16
        assert verdict["all_accepted"] is True


def test_the_complete_manifest_records_the_remaining_authorship(manifest):
    value = manifest.to_dict()

    discovered = value["emitter_inputs_from_discovery"]
    assert discovered["operation_labels"] == sorted(OPCODES)
    assert discovered["region_effect_classes"] == {
        "exit_region": ["0x2", "0x6"], "repeat_region": ["0x3"]
    }
    assert discovered["selected_arrangement_digest"] == value["synthesis"]["selected_digest"]
    assert discovered["selection_evidence_digest"] == value["synthesis"]["public_evidence_digest"]
    assert value["authored_elements"] == [
        "copy-task decomposition",
        "four atomic steps",
        "finite Cartesian search grammar",
        "generic WebAssembly emitter",
        "blocktype and label-depth encoding",
        "scaffold shapes",
        "public and hidden cases",
    ]
    assert "arbitrary compiler synthesis" in value["claim_exclusions"]
    assert value["external_authority_not_granted"] == [
        "network", "repository", "credentials", "deployment", "production systems"
    ]
    assert value["canonical"] is False
    assert value["replay_identical"] is True
