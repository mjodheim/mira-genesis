"""M059 falsifications.

The claim is that the lineage judged its situation rather than executed an instruction. Two
tests decide that: the judgement must reverse between task families, and it must be capable of
refusing to move. Both come first.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from metamorphosis.m059_substrate_judgement import (
    M059Error, M059_PROTOCOL, OPCODE_SPACE, SCAN_PAIRS, SHAPES, candidate_module, judge_family,
    operations_module, run_m059_substrate_judgement, scan_substrate, task_families,
)


@pytest.fixture(scope="module")
def manifest():
    return run_m059_substrate_judgement()


@pytest.fixture(scope="module")
def scans():
    return {shape: scan_substrate(shape) for shape in sorted(SHAPES)}


def test_the_judgement_reverses_between_task_families(manifest):
    """If one substrate always won, the result would be a fact about substrates, not a judgement."""
    value = manifest.to_dict()

    assert value["migrations"] == ["bitwise_difference", "fractional_mean"]
    assert value["distinct_migration_targets"] == ["f64", "i32"]
    assert value["journey"] == ["f64", "i32", "f64"]


def test_a_capability_the_current_substrate_expresses_produces_a_refusal(manifest):
    """A lineage that always migrates is executing, not judging."""
    value = manifest.to_dict()

    assert value["decisions"]["larger_of_two"] == "stay"
    assert value["refusals"] == ["larger_of_two"]
    assert value["current_substrate_outcome"]["larger_of_two"] == "synthesized"


def test_the_refusal_comes_from_the_same_mechanism_as_the_migrations():
    """`stay` is what happens when the current substrate answers first, not a separate branch."""
    from pathlib import Path

    source = Path(__file__).resolve().parents[1].joinpath(
        "metamorphosis", "m059_wasm_runtime.mjs"
    ).read_text(encoding="utf-8")
    judge = source.split("function judge(", 1)[1].split("\nfunction ", 1)[0]

    # One synthesis call decides `stay`; the second decides `migrate`. No third path.
    assert judge.count("synthesizeWith(") == 2
    assert judge.count("decision:") == 3


def test_no_ranking_between_substrates_is_supplied(manifest):
    value = manifest.to_dict()

    assert value["substrate_ranking_supplied"] is False
    assert sorted(value["shapes_declared"]) == ["f64", "i32"]


def test_both_instruction_sets_are_discovered_not_supplied(scans):
    for shape, scan in scans.items():
        assert scan["scanned"] == 256
        assert scan["rejected_count"] > 200
        assert scan["valid_count"] + scan["rejected_count"] == 256


def test_the_two_substrates_genuinely_differ(manifest, scans):
    value = manifest.to_dict()

    assert value["operations_discovered"] == {"f64": 9, "i32": 27}
    f64 = set(scans["f64"]["valid"])
    i32 = set(scans["i32"]["valid"])
    assert i32 - f64, "i32 must contain operations f64 lacks"
    assert f64 & i32, "the substrates share the projections"


def test_the_two_failures_have_different_causes(manifest):
    """Not found is not the same as budget exhausted, and the record says which."""
    value = manifest.to_dict()

    assert value["current_substrate_outcome"]["bitwise_difference"] == "insufficient_evidence"
    assert value["current_substrate_outcome"]["fractional_mean"] == "budget_exhausted"
    assert value["candidates_constructed_here"]["fractional_mean"] == M059_PROTOCOL.judgement_budget
    assert value["candidates_constructed_here"]["bitwise_difference"] < M059_PROTOCOL.judgement_budget


def test_not_found_is_never_promoted_into_impossibility(manifest):
    """The reasons quote the search outcome, not a claim about what a substrate can express."""
    reasons = manifest.to_dict()["reasons"]

    for name in ("bitwise_difference", "fractional_mean"):
        assert "insufficient_evidence" in reasons[name] or "budget_exhausted" in reasons[name]
        assert "impossible" not in reasons[name]
        assert "cannot" not in reasons[name]


def test_every_accepted_body_holds_on_a_domain_the_judgement_never_saw(manifest):
    value = manifest.to_dict()

    assert value["hidden_domain_verified"] == {
        "bitwise_difference": True, "fractional_mean": True, "larger_of_two": True,
    }
    families = task_families()
    for family in families.values():
        seen = {tuple(item["args"]) for item in family["observations"]}
        hidden = {tuple(item["args"]) for item in family["hidden"]}
        assert not seen & hidden


def test_integer_division_traps_and_the_search_survives_it(scans):
    """`i32.div_s` traps on a zero divisor where `f64` yields Infinity.

    An uncaught trap aborted the search during development. The substrates do not share this
    behaviour, and the difference had to be handled rather than assumed away.
    """
    assert "0x6d" in scans["i32"]["valid"]
    assert "0x6d" not in scans["f64"]["valid"]


def test_a_shape_that_was_not_declared_is_refused():
    with pytest.raises(M059Error, match="unknown signature shape"):
        scan_substrate("i64")


def test_the_declared_parameters_are_pinned():
    assert sorted(SHAPES) == ["f64", "i32"]
    assert SHAPES == {"f64": 0x7C, "i32": 0x7F}
    assert len(OPCODE_SPACE) == 256
    assert len(SCAN_PAIRS) == 3
    assert M059_PROTOCOL.max_expression_size == 7
    assert M059_PROTOCOL.judgement_budget == 200000
    assert M059_PROTOCOL.starting_substrate == "f64"


def test_candidate_and_operation_modules_are_well_formed():
    assert candidate_module(0xA0, SHAPES["f64"]).startswith(b"\x00asm\x01\x00\x00\x00")
    assert operations_module(["0xa0", "0xa5"], SHAPES["f64"]).startswith(b"\x00asm")


def test_the_manifest_records_the_boundaries(manifest):
    value = manifest.to_dict()

    assert value["starting_substrate"] == "f64"
    assert value["arbitrary_code_generation"] is False
    assert value["network_authority"] is False
    assert value["repository_authority"] is False
    assert value["credential_authority"] is False
    assert value["deployment_authority"] is False
    assert value["canonical"] is False


def test_the_manifest_is_reproducible_across_processes(manifest):
    script = (
        "from metamorphosis.m059_substrate_judgement import "
        "run_m059_substrate_judgement as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    assert manifest.digest() == completed.stdout.decode("utf-8").strip().splitlines()[-1]
