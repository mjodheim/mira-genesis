"""M058 falsifications.

The claim is that the lineage discovered which instructions exist. The tests that could catch a
violation come first: nothing supplies an opcode list, the scan really refuses most of the
space, and what it found is not what a human had written down.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from metamorphosis.m058_discovered_migration import (
    HIDDEN_ARGUMENTS, M057_AUTHORED_OPCODES, M058_PROTOCOL, OBSERVATION_ARGUMENTS, SCAN_PAIRS,
    run_m058_discovered_migration, scan_instruction_space,
)
from metamorphosis.m058_instruction_discovery import (
    OPCODE_SPACE, Expr, M058Error, atoms_for, candidate_module, discovered_from, emit_tool,
    expression_space_size, load_expression, scan_requests,
)


@pytest.fixture(scope="module")
def manifest():
    return run_m058_discovered_migration()


@pytest.fixture(scope="module")
def scan():
    return scan_instruction_space()


def test_the_whole_single_byte_space_is_a_candidate():
    """Nothing narrows the search in advance."""
    assert OPCODE_SPACE == tuple(range(0x00, 0x100))
    assert len(scan_requests()) == 256


def test_the_substrate_refuses_most_of_the_space(scan):
    """Validation is the answer. A byte that is not an operation refuses to compile."""
    assert scan["scanned"] == 256
    assert scan["rejected_count"] > 200
    assert scan["valid_count"] + scan["rejected_count"] == 256


def test_discovery_finds_operations_no_human_list_contained(manifest):
    """The point of the experiment.

    `0xa6` is `copysign`, a genuine arithmetic operation M057's authored list simply omitted.
    `0x0f` and `0x1a` behave as projections — return and drop — which no designer would have
    entered under "binary operations" at all.
    """
    value = manifest.to_dict()

    assert value["operations_discovered"] == 9
    assert value["operations_authored_by_m057"] == 6
    assert value["operations_discovery_added"] == ["0x0f", "0x1a", "0xa6"]
    assert value["instruction_set_authored_by_human"] is False


def test_the_projections_really_are_projections(scan):
    """`0x0f` returns its second argument and `0x1a` its first, on every scan pair."""
    observations = scan["valid"]
    first = [pair[0] for pair in SCAN_PAIRS]
    second = [pair[1] for pair in SCAN_PAIRS]

    assert observations["0x0f"] == second
    assert observations["0x1a"] == first


def test_no_opcode_list_is_supplied_anywhere():
    """A guard against reintroducing the thing M058 exists to remove."""
    import metamorphosis.m058_instruction_discovery as discovery

    source = open(discovery.__file__, encoding="utf-8").read()
    # The module may build candidates for every byte, but must not enumerate a chosen few.
    assert "0xA0" not in source and "0xa0" not in source
    assert "f64.add" not in source


def test_the_authored_list_is_kept_only_for_comparison():
    """`M057_AUTHORED_OPCODES` must not reach the scan or the synthesis."""
    import metamorphosis.m058_discovered_migration as migration

    source = open(migration.__file__, encoding="utf-8").read()
    uses = [line for line in source.splitlines() if "M057_AUTHORED_OPCODES" in line]

    assert any("beyond_m057" in line for line in uses)
    assert not any("scan" in line and "M057_AUTHORED_OPCODES" in line for line in uses)


def test_synthesis_reaches_a_tool_no_single_operation_satisfies(manifest):
    value = manifest.to_dict()

    assert value["tools_requiring_composition"] == ["mean"]
    assert value["expression_sizes"]["mean"] == 7
    assert value["expressions"]["mean"] == "0xa3(0xa0(p0,0xa0(p1,p2)),k)"


def test_denying_composition_fails_exactly_on_the_composed_tool(manifest):
    assert manifest.to_dict()["ablation_composition_denied"] == {"mean": "composition_denied"}


def test_every_synthesized_body_holds_on_a_domain_synthesis_never_saw(manifest):
    value = manifest.to_dict()

    assert value["hidden_domain_verified"] == {"add": True, "max": True, "mean": True, "mul": True}
    for arity, arguments in HIDDEN_ARGUMENTS.items():
        assert not set(arguments) & set(OBSERVATION_ARGUMENTS[arity])


def test_the_lineage_migrates_on_the_instruction_set_it_discovered(manifest):
    value = manifest.to_dict()

    assert value["inherited_version"] == 8
    assert value["inherited_retained_case_count"] == 32
    assert value["migrated_all_retained_passed"] is True
    assert value["migrated_import_count"] == 0


def test_the_margin_improved_because_discovery_widened_the_space(manifest):
    """Better than M057's sixth, and earned rather than declared."""
    value = manifest.to_dict()

    admissible = value["admissible_space_by_arity"]["3"]
    constructed = value["candidates_constructed"]["mean"]

    assert admissible == expression_space_size(7, len(atoms_for(3)), 9) == 943636
    assert admissible > expression_space_size(7, len(atoms_for(3)), 6)
    assert constructed / admissible < 0.10


def test_an_expression_using_an_undiscovered_operation_is_refused():
    expression = Expr(operation="0xff", left=Expr(atom="p0"), right=Expr(atom="p1"))

    with pytest.raises(M058Error, match="never discovered"):
        emit_tool("broken", expression, 2, {"0xa0": 0xA0})


def test_an_expression_cannot_read_a_parameter_the_tool_lacks():
    expression = Expr(operation="0xa0", left=Expr(atom="p0"), right=Expr(atom="p2"))

    with pytest.raises(M058Error, match="parameter the tool does not have"):
        emit_tool("broken", expression, 2, {"0xa0": 0xA0})


def test_malformed_expressions_are_refused():
    with pytest.raises(M058Error, match="discovered operation"):
        Expr(operation="", left=Expr(atom="p0"), right=Expr(atom="p1"))
    with pytest.raises(M058Error, match="two operands"):
        Expr(operation="0xa0", left=Expr(atom="p0"))
    with pytest.raises(M058Error, match="no operation or operands"):
        Expr(atom="p0", operation="0xa0")


def test_an_empty_scan_is_refused():
    with pytest.raises(M058Error, match="no operation at all"):
        discovered_from({"valid": {}})


def test_a_candidate_module_is_well_formed():
    assert candidate_module(0xA0).startswith(b"\x00asm\x01\x00\x00\x00")
    assert len(candidate_module(0xA0)) == len(candidate_module(0xFF))


def test_the_remaining_human_boundary_is_declared(manifest):
    """M058 removes the operation list and keeps the signature shape. It says so."""
    value = manifest.to_dict()

    assert value["instruction_set_authored_by_human"] is False
    assert value["signature_shape_authored_by_human"] is True


def test_the_manifest_records_the_boundaries(manifest):
    value = manifest.to_dict()

    assert value["arbitrary_code_generation"] is False
    assert value["network_authority"] is False
    assert value["repository_authority"] is False
    assert value["credential_authority"] is False
    assert value["deployment_authority"] is False
    assert value["canonical"] is False


def test_the_manifest_is_reproducible_across_processes(manifest):
    script = (
        "from metamorphosis.m058_discovered_migration import "
        "run_m058_discovered_migration as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    assert manifest.digest() == completed.stdout.decode("utf-8").strip().splitlines()[-1]
