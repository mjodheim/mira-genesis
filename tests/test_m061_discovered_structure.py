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
    COPY_PHRASE, M061_PROTOCOL, resolve_structure, run_copy_loop, run_m061_discovered_structure,
    unresolved_shapes,
)
from metamorphosis.m061_structural_discovery import (
    M060_AUTHORED_STRUCTURAL, OPCODE_SPACE, PRESUPPOSED, SCAFFOLDS, M061Error, build_copy_loop,
    load_shapes, probe, resolve_load, resolve_width, scan_scaffold, store_widths,
)


@pytest.fixture(scope="module")
def manifest():
    return run_m061_discovered_structure()


@pytest.fixture(scope="module")
def scans():
    return {s.name: scan_scaffold(s, M061_PROTOCOL.probe_timeout_seconds) for s in SCAFFOLDS}


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
    """`0x12` is a tail call: it recurses without growing the stack, so it never traps."""
    counts = manifest.to_dict()["non_terminating_candidates"]

    assert counts == {"conditional_branch": 1, "memory_load": 1, "memory_store": 1}
    for scan in manifest.to_dict()["outcome_counts"].values():
        assert scan["did_not_terminate"] == 1


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
    assert value["structural_instructions_authored"] is False


def test_the_recovered_instructions_actually_compute(manifest):
    """Naming a byte is not the same as being able to build with it."""
    value = manifest.to_dict()

    assert value["copy_phrase_recovered"] is True
    assert value["copy_loop_uses_only_discovered_instructions"] is True
    assert value["copy_loop_bytes"] == 97


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
