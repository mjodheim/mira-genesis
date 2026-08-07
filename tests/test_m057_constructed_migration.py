"""M057 falsifications.

The claim is that the lineage discovered the substrate rather than being told about it. The
tests that could catch a violation of that come first: no handle carries a name, synthesis
evaluates by calling the substrate, and both ablations fail as they must.
"""
from __future__ import annotations

import base64
import subprocess
import sys

import pytest

from metamorphosis.m057_constructed_migration import (
    HIDDEN_ARGUMENTS, M057_PROTOCOL, OBSERVATION_ARGUMENTS, PROBE_PAIRS, observe_own_tools,
    probe_handles, run_m057_constructed_migration, synthesize_body,
)
from metamorphosis.m057_opaque_substrate import (
    HANDLES, Expr, M057Error, atoms_for, emit_tool, expression_space_size, load_expression,
    probe_module,
)
from metamorphosis.m056_second_migration import reconstruct_m048_version_eight
from metamorphosis.m056_wasm_compiler import declared_tools


@pytest.fixture(scope="module")
def manifest():
    return run_m057_constructed_migration()


@pytest.fixture(scope="module")
def lineage():
    return reconstruct_m048_version_eight()


def test_no_handle_carries_a_semantic_name():
    """If a handle were called `add`, the lineage would be told what it is."""
    assert HANDLES == ("h1", "h2", "h3", "h4", "h5", "h6")
    for handle in HANDLES:
        assert handle[0] == "h" and handle[1:].isdigit()


def test_the_probe_module_is_the_only_way_to_learn_what_a_handle_does():
    probed = probe_handles()

    assert probed["import_count"] == 0
    assert sorted(probed["handles"]) == sorted(HANDLES)
    observations = probed["observations"]
    # Four probe pairs separate all six handles: no two behave alike.
    signatures = {handle: tuple(values) for handle, values in observations.items()}
    assert len(set(signatures.values())) == len(HANDLES)


def test_the_python_side_holds_no_table_of_handle_semantics():
    """The defect this test guards against was present in an early draft.

    Synthesis once evaluated candidates in Python against a table of the opcodes' meanings,
    which would have let the lineage use the knowledge it was supposed to discover.
    """
    import metamorphosis.m057_opaque_substrate as substrate

    assert not hasattr(substrate, "_APPLY")
    source = open(substrate.__file__, encoding="utf-8").read()
    assert "lambda a, b: a + b" not in source
    assert "def synthesize_tool_body" not in source


def test_synthesis_reaches_a_tool_no_single_handle_satisfies(manifest):
    """The falsifier of the experiment: discovery must not stop at labelling."""
    value = manifest.to_dict()

    assert value["tools_requiring_composition"] == ["mean"]
    assert value["expression_sizes"]["mean"] == 7
    assert value["expressions"]["mean"] == "h4(h1(p0,h1(p1,p2)),k)"


def test_the_directly_matched_tools_are_found_at_size_three(manifest):
    value = manifest.to_dict()

    for name in ("add", "max", "mul"):
        assert value["expression_sizes"][name] == 3
        assert value["candidates_constructed"][name] < 100


def test_every_synthesized_body_holds_on_a_domain_synthesis_never_saw(manifest):
    value = manifest.to_dict()

    assert value["hidden_domain_verified"] == {"add": True, "max": True, "mean": True, "mul": True}
    for arity, arguments in HIDDEN_ARGUMENTS.items():
        assert not set(arguments) & set(OBSERVATION_ARGUMENTS[arity])


def test_the_lineage_migrates_on_the_path_it_constructed(manifest):
    value = manifest.to_dict()

    assert value["inherited_version"] == 8
    assert value["inherited_retained_case_count"] == 32
    assert value["migrated_all_retained_passed"] is True
    assert value["migrated_import_count"] == 0


def test_taking_handles_in_declaration_order_fails(manifest):
    """Without probing, the result would be an artifact of the exposure order."""
    assert manifest.to_dict()["ablation_declaration_order_passed"] is False


def test_denying_composition_fails_exactly_on_the_composed_tool(manifest):
    value = manifest.to_dict()

    assert value["ablation_composition_denied"] == {"mean": "composition_denied"}


def test_the_search_does_not_enumerate_but_the_margin_is_recorded(manifest):
    """M057 does not claim M054's separation, and the numbers say why."""
    value = manifest.to_dict()

    admissible = value["admissible_space_by_arity"]["3"]
    constructed = value["candidates_constructed"]["mean"]

    assert admissible == expression_space_size(7, len(atoms_for(3))) == 281188
    assert constructed < admissible
    assert constructed < M057_PROTOCOL.synthesis_budget
    # Roughly a sixth of the space, not the five orders of magnitude M054 had.
    assert 0.1 < constructed / admissible < 0.25


def test_behavioural_deduplication_is_what_makes_it_reachable(manifest):
    value = manifest.to_dict()

    assert value["behaviour_classes"]["mean"] < value["candidates_constructed"]["mean"]


def test_an_expression_cannot_read_a_parameter_the_tool_lacks():
    expression = Expr(handle="h1", left=Expr(atom="p0"), right=Expr(atom="p2"))

    with pytest.raises(M057Error, match="parameter the tool does not have"):
        emit_tool("broken", expression, 2)


def test_malformed_expressions_are_refused():
    with pytest.raises(M057Error, match="unknown handle"):
        Expr(handle="h99", left=Expr(atom="p0"), right=Expr(atom="p1"))
    with pytest.raises(M057Error, match="two operands"):
        Expr(handle="h1", left=Expr(atom="p0"))
    with pytest.raises(M057Error, match="no handle or operands"):
        Expr(atom="p0", handle="h1")


def test_the_emitted_module_declares_no_imports():
    module, record = emit_tool("t", Expr(handle="h6", left=Expr(atom="p0"), right=Expr(atom="p1")), 2)

    assert module.startswith(b"\x00asm")
    assert record["expression"] == "h6(p0,p1)"


def test_the_declared_parameters_are_pinned():
    assert M057_PROTOCOL.max_expression_size == 7
    assert M057_PROTOCOL.synthesis_budget == 200000
    assert len(PROBE_PAIRS) == 4
    assert atoms_for(3) == ("p0", "p1", "p2", "k")


def test_the_manifest_records_the_boundaries(manifest):
    value = manifest.to_dict()

    assert value["handles_carry_semantic_names"] is False
    assert value["probe_import_count"] == 0
    assert value["arbitrary_code_generation"] is False
    assert value["network_authority"] is False
    assert value["repository_authority"] is False
    assert value["credential_authority"] is False
    assert value["deployment_authority"] is False
    assert value["canonical"] is False


def test_the_manifest_is_reproducible_across_processes(manifest):
    script = (
        "from metamorphosis.m057_constructed_migration import "
        "run_m057_constructed_migration as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    assert manifest.digest() == completed.stdout.decode("utf-8").strip().splitlines()[-1]
