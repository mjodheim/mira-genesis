"""M061 falsifications.

Two properties decide whether the scan is an instrument or a formality: it must find its own
witness, and it must refuse where its probes do not separate. Both come first, because a
structural scan that is silently broken produces exactly the output of a true negative.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from metamorphosis.m061_discovered_structure import (
    COPY_PHRASE, M061_PROTOCOL, SCAFFOLD_NAMES, resolve_structure, run_all_scans, run_copy_loop,
    run_m061_discovered_structure, unresolved_shapes,
)
from metamorphosis.m061_structural_discovery import (
    LOOP_REQUIRED, M060_AUTHORED_STRUCTURAL, OPCODE_SPACE, PRESUPPOSED, SCAFFOLDS,
    UNDISCOVERED_IN_LOOP, M061Error, build_copy_loop, load_shapes, probe, resolve_i32_binary,
    resolve_load, resolve_unique, resolve_width, scan_scaffold, staged_scaffolds, store_widths,
)


@pytest.fixture(scope="module")
def manifest():
    return run_m061_discovered_structure()


@pytest.fixture(scope="module")
def scans():
    return run_all_scans(M061_PROTOCOL)


def test_every_scaffold_finds_its_own_witness(scans):
    """The instrument's self-check.

    A first attempt emitted the memory section before the function section, which the format
    forbids, and the substrate refused all 256 candidates. "Nothing exists" and "the scaffold is
    malformed" produce identical output, so each shape names an instruction it must recover.
    """
    for name, scan in scans.items():
        assert scan["witness_found"] is True, name
        assert scan["witness"] in scan["matches"], name


def test_a_broken_scaffold_is_caught_rather_than_reported_as_a_negative():
    """Emitting the sections out of order makes the substrate refuse everything."""
    from metamorphosis.m061_structural_discovery import _section, _vec, _uleb, _name, I32

    signature = bytes([0x60]) + _vec([bytes([I32])]) + _vec([bytes([I32])])
    inner = _vec([]) + bytes([0x20, 0, 0x2D, 0x00, 0x00]) + bytes([0x0B])
    malformed = (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(5, _vec([bytes([0x00]) + _uleb(1)]))   # memory before function: forbidden
        + _section(3, _vec([_uleb(0)]))
        + _section(7, _vec([_name("f") + bytes([0x00]) + _uleb(0),
                            _name("memory") + bytes([0x02]) + _uleb(0)]))
        + _section(10, _vec([_uleb(len(inner)) + inner]))
    )

    response = probe(malformed, [{"args": [0], "memory": [[0, 1]]}], 2.0)

    assert response["outcome"] == "refused"


def test_the_probes_refuse_what_they_cannot_separate(scans, manifest):
    """`0x2e` and `0x2f` read two bytes each and both planted patterns are positive."""
    unresolved = unresolved_shapes(scans)

    assert unresolved == {"load_width_2_unsigned_True": ["0x2e", "0x2f"]}
    assert manifest.to_dict()["shapes_the_probes_could_not_separate"] == unresolved


def test_widening_a_probe_is_what_resolved_the_one_byte_loads(scans):
    """Signed and unsigned byte loads agree on a positive pattern; the second call separates them."""
    shapes = load_shapes(scans["memory_load"])

    assert shapes["0x2d"] == (1, True)
    assert shapes["0x2c"] == (1, False)
    assert resolve_load(shapes, 1, True, "load8_u") == "0x2d"
    assert resolve_load(shapes, 1, False, "load8_s") == "0x2c"


def test_store_widths_come_from_the_footprint_not_from_a_name(scans):
    widths = store_widths(scans["memory_store"])

    assert widths["0x3a"] == 1
    assert widths["0x3b"] == 2
    assert widths["0x36"] == 4
    # The branches inhabit the shape and write nothing, which is how they are excluded.
    for branch in ("0x0c", "0x0d", "0x0e", "0x0f"):
        assert widths[branch] == 0


def test_a_conditional_branch_is_discovered_by_its_effect(scans):
    """It has no value to compare; the scaffold returns 7 when taken and 9 when not."""
    scan = scans["conditional_branch"]

    assert scan["matches"] == ["0x0d"]
    assert scan["observations"]["0x0d"] == [7, 9]


def test_some_candidates_never_terminate(manifest):
    """`0x12` is a tail call: it recurses without growing the stack, so it never traps.

    It only hangs where the shape lets it call the enclosing function with matching arity. The
    counts are per shape rather than a single number, because that difference is a property of the
    scaffolds and not noise.
    """
    counts = manifest.to_dict()["non_terminating_candidates"]

    assert counts == {
        "conditional_branch": 1, "i32_binary": 0, "local_set": 0,
        "memory_load": 1, "memory_store": 1, "unconditional_branch": 1,
    }
    assert sum(counts.values()) == 4


def test_the_timeout_is_what_makes_a_scan_possible():
    """Without a per-candidate deadline the scan stops at the first non-terminating byte."""
    from metamorphosis.m061_structural_discovery import _load_scaffold

    response = probe(_load_scaffold(0x12), [{"args": [0], "memory": []}], 2.0)

    assert response["outcome"] == "did_not_terminate"


def test_discovery_recovers_every_instruction_m060_authored(manifest):
    value = manifest.to_dict()

    assert value["discovery_recovered_every_authored_opcode"] is True
    assert value["resolved_structural_opcodes"] == {
        label: hex(code) for label, code in sorted(M060_AUTHORED_STRUCTURAL.items())
    }
    assert len(M060_AUTHORED_STRUCTURAL) == 10
    assert value["structural_operations_authored"] is False


def test_the_second_stage_is_scanned_with_what_the_first_stage_found(scans):
    """Two shapes cannot observe their candidate without an addition, and it is a discovered one.

    Writing `0x6a` into the scaffold that discovers opcodes would have been the same shortcut this
    experiment exists to remove, so the first stage's integer scan supplies it.
    """
    add = resolve_i32_binary(scans["i32_binary"])["i32.add"]
    staged = staged_scaffolds(add)

    assert [scaffold.name for scaffold in staged] == ["local_set", "unconditional_branch"]
    assert [scaffold.name for scaffold in SCAFFOLDS] == SCAFFOLD_NAMES[:4]
    # The stage-two shapes are built from `add`, so a wrong byte changes the module they scan.
    assert staged[0].build(0x21) != _local_set_module_with_a_wrong_addition()


def _local_set_module_with_a_wrong_addition() -> bytes:
    return staged_scaffolds(0x6B)[0].build(0x21)   # subtraction where the addition belongs


def test_storing_a_value_is_separated_from_discarding_it_and_from_leaving(scans):
    """Three candidates inhabit this shape and two earlier versions could not tell them apart.

    Ending on the constant made `local.set` and `drop` identical, because nothing read the local
    back. Ending on `local.get 1` made `local.set` and `return` identical, because both surface the
    parameter. Reading the local *and* adding the constant separates all three.
    """
    scan = scans["local_set"]
    seen = scan["all_observations"]

    assert scan["matches"] == ["0x21"]
    assert seen["0x21"] == [74, 24]      # local.set: 33 + 41 and 33 - 9
    assert seen["0x1a"] == [33, 33]      # drop: the local stays at its default, so 33 + 0
    assert seen["0x0f"] == [41, -9]      # return: leaves before the addition happens
    assert "0x22" not in seen            # local.tee leaves two values against one result
    assert resolve_unique(scan, "local.set") == "0x21"


def test_an_unconditional_branch_is_separated_from_a_return(scans):
    """Both leave the block with 7. Only the branch comes back to have one added to it."""
    scan = scans["unconditional_branch"]

    assert scan["matches"] == ["0x0c"]
    assert scan["all_observations"]["0x0c"] == [8, 8]
    assert scan["all_observations"]["0x0f"] == [7, 7]


def test_the_scan_disagreed_with_the_authored_loop_and_was_right():
    """`i32.le_s` is `0x4c`; the first copy loop hardcoded `0x4d`, the unsigned comparison.

    Nothing caught it, because the loop's counter never goes negative. The scan named the opcode
    from behaviour rather than from a table, and in doing so found a defect in the code it was
    meant to reproduce. M060's own emitter had it right.
    """
    from metamorphosis.m060_wasm_emit import Code

    assert M060_AUTHORED_STRUCTURAL["i32.le_s"] == 0x4C
    assert Code().i32_le_s().bytes()[-1:] == b"\x4c"


def test_the_recovered_instructions_actually_compute(manifest):
    """Naming a byte is not the same as being able to build with it."""
    value = manifest.to_dict()

    assert value["copy_phrase_recovered"] is True
    assert value["copy_loop_bytes"] == 97


def test_the_manifest_names_what_the_loop_still_writes_by_hand(manifest):
    """The claim this replaces was false, and the correction is a list rather than softer wording.

    An earlier manifest asserted the loop used discovered instructions alone while the builder
    hardcoded seven opcodes. Six are now discovered; `block` and `loop` are not instructions with an
    observable effect on a value, so they stay authored and are named here at the same level as
    what was found.
    """
    value = manifest.to_dict()

    assert value["copy_loop_uses_only_discovered_instructions"] is False
    assert value["copy_loop_discovered_instructions"] == sorted(LOOP_REQUIRED)
    assert value["copy_loop_authored_elements"] == list(UNDISCOVERED_IN_LOOP)
    assert value["block_structure_authored"] is True
    assert set(LOOP_REQUIRED) <= set(value["resolved_structural_opcodes"])


def test_the_loop_refuses_to_be_built_from_an_incomplete_discovery():
    """Every operation it needs must have been found; there is no fallback to an authored byte."""
    partial = {label: 0x6A for label in LOOP_REQUIRED if label != "local.set"}

    with pytest.raises(M061Error, match="local.set"):
        build_copy_loop(partial)


def test_the_copy_loop_fails_when_given_the_wrong_branch(scans):
    """The loop is a real check, not a formality: a wrong branch stops it copying anything."""
    resolved = dict(resolve_structure(scans))
    resolved["br_if"] = 0x0C  # the unconditional branch where the conditional one belongs

    result = run_copy_loop(build_copy_loop(resolved))

    assert result["correct"] is False


def test_a_wrong_store_width_is_not_caught_by_this_loop(scans):
    """Recorded because it bounds what the copy loop can falsify.

    Substituting the four-byte store for the one-byte store leaves the copied range correct:
    each iteration writes its byte plus three zeros, and the next iteration overwrites those
    zeros with the following byte. The width only shows past the end of the range, which this
    loop never reads. The control is real for the branch and blind to this substitution, and
    saying so is better than implying the loop falsifies everything.
    """
    resolved = dict(resolve_structure(scans))
    resolved["i32.store8"] = 0x36

    result = run_copy_loop(build_copy_loop(resolved))

    assert result["correct"] is True


def test_the_floor_is_named(manifest):
    """Every scaffold presents an operand and returns a result, so it cannot discover how."""
    assert manifest.to_dict()["presupposed"] == list(PRESUPPOSED)
    assert "local.get" in PRESUPPOSED
    assert "i32.const" in PRESUPPOSED
    assert "end 0x0b" in PRESUPPOSED


def test_the_whole_space_is_scanned_per_scaffold(manifest):
    value = manifest.to_dict()

    assert value["opcode_space_scanned"] == len(OPCODE_SPACE) == 256
    for counts in value["outcome_counts"].values():
        assert sum(counts.values()) == 256


def test_the_manifest_records_the_boundaries(manifest):
    value = manifest.to_dict()

    assert value["compiler_authored"] is True
    assert value["arbitrary_code_generation"] is False
    assert value["network_authority"] is False
    assert value["repository_authority"] is False
    assert value["credential_authority"] is False
    assert value["deployment_authority"] is False
    assert value["canonical"] is False
    assert value["replay_identical"] is True


def test_the_manifest_is_reproducible_across_processes(manifest):
    script = (
        "from metamorphosis.m061_discovered_structure import "
        "run_m061_discovered_structure as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    assert manifest.digest() == completed.stdout.decode("utf-8").strip().splitlines()[-1]
