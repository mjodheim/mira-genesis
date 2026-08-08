"""M060 falsifications at the experiment level.

`test_m060_body_compiler.py` checks that the emitted module is correct. These tests check the
claim built on it: that the **whole** accepted body crossed, that nothing was left behind, and
that no capability can reach back into JavaScript.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from metamorphosis.m060_whole_body_migration import (
    M060Error, M060_PROTOCOL, SHELL_MODULES, TOOL_MODULES, execute_in_wasm, inspect_module,
    reconstruct_m048_version_eight, run_m060_whole_body_migration,
)


@pytest.fixture(scope="module")
def manifest():
    return run_m060_whole_body_migration()


@pytest.fixture(scope="module")
def lineage():
    return reconstruct_m048_version_eight()


@pytest.fixture(scope="module")
def module():
    from metamorphosis.m060_body_compiler import compile_body

    return compile_body()


def test_nothing_is_left_in_javascript(manifest):
    """The claim M056 through M059 could not make."""
    value = manifest.to_dict()

    assert value["modules_left_in_javascript"] == 0
    assert sorted(value["shell_modules_migrated"]) == sorted(SHELL_MODULES)
    assert sorted(value["tool_modules_migrated"]) == sorted(TOOL_MODULES)
    assert value["inherited_module_count"] == len(SHELL_MODULES) + len(TOOL_MODULES) == 10


def test_the_seven_shell_modules_are_the_ones_earlier_experiments_left_behind(lineage):
    """Named explicitly, because this is what makes M060 different from M056–M059."""
    names = lineage.module_names()

    for name in ("interpretation", "planning", "selection", "execution", "critique",
                 "allocation", "orchestration"):
        assert name in names, name
    assert set(SHELL_MODULES) | set(TOOL_MODULES) == set(names)


def test_the_module_cannot_call_outward(module, manifest):
    """Structural, not a promise: a module with imports is refused before it runs."""
    inspected = inspect_module(module)

    assert inspected["import_count"] == 0
    assert manifest.to_dict()["declared_imports"] == 0
    assert manifest.to_dict()["semantic_delegation_to_javascript"] is False


def test_every_inherited_capability_executes_in_the_new_substrate(manifest):
    value = manifest.to_dict()

    assert value["inherited_version"] == 8
    assert value["retained_total"] == 32
    assert value["retained_passed"] == 32
    assert value["all_retained_passed"] is True
    assert value["pre_first_migration_case_count"] == 28


def test_the_pipeline_stages_survive_as_separate_functions(manifest):
    """Fusing the body into one function would preserve behaviour and destroy its structure."""
    exported = manifest.to_dict()["exported_functions"]

    for stage in ("interpret", "plan", "allocate", "select", "execute", "critique", "run"):
        assert stage in exported, stage
    assert "memory" in exported


def test_nested_requests_work(module, lineage):
    """The defect that took the first implementation from 32 to 23.

    A planner that allocates a parent's step before recursing produces preorder indices, and a
    parent then reads a result its children have not written. Flat requests never show it.
    """
    nested = [case for case in lineage.retained if len(case.request.split()) > 3]
    assert len(nested) >= 8

    execution = execute_in_wasm(module, nested)

    assert execution["all_passed"] is True


def test_refusals_are_reproduced(module, lineage):
    """Two shapes of refusal, and they are not the same shape.

    An unknown operator and an incomplete arity trap. Leftover tokens do not: `interpret`
    returns -1 and the pipeline yields NaN, exactly as the accepted body returns a failure
    record rather than throwing. Both are refusals; only one is a trap.
    """
    case = type(lineage.retained[0])
    trapping = [
        case("m060_unknown", "median 1 2", 0.0, "m060_refusal"),
        case("m060_short", "add 2", 0.0, "m060_refusal"),
    ]
    trailing = [case("m060_trailing", "add 2 3 4", 0.0, "m060_refusal")]

    trapped = execute_in_wasm(module, trapping)
    left_over = execute_in_wasm(module, trailing)

    assert all(item["refused"] for item in trapped["case_results"])
    assert trapped["all_passed"] is False
    result = left_over["case_results"][0]
    assert result["refused"] is False
    assert result["output"] != result["expected"]


def test_the_lineage_refuses_an_empty_request_before_the_substrate_sees_it(lineage):
    """The body's own case type rejects it, so the substrate is never asked."""
    case = type(lineage.retained[0])

    with pytest.raises(Exception, match="non-empty"):
        case("m060_empty", "", 0.0, "m060_refusal")


def test_two_decimal_rounding_is_reproduced_exactly(module, lineage):
    case = type(lineage.retained[0])
    rounding = [
        case("m060_round_1", "mean 1 2 2", 1.67, "m060_round"),
        case("m060_round_2", "mean 0 1 1", 0.67, "m060_round"),
        case("m060_round_3", "mean 2 2 3", 2.33, "m060_round"),
    ]

    execution = execute_in_wasm(module, rounding)

    assert execution["all_passed"] is True


def test_the_arithmetic_is_resolved_by_a_substrate_scan(manifest):
    """The discovery must be in the artifact, not only in a claim about it.

    An earlier revision verified this in an ad hoc command and shipped a compiler that used its
    authored fallback, so the manifest asserted nothing about discovery at all.
    """
    value = manifest.to_dict()

    assert value["opcode_space_scanned"] == 256
    assert value["operations_discovered"] == 9
    assert value["arithmetic_opcodes_discovered"] == {
        "add": "0xa0", "div": "0xa3", "max": "0xa5", "mul": "0xa2",
    }
    assert value["arithmetic_opcodes_authored"] is False
    assert value["arithmetic_matches_authored_fallback"] is True
    assert value["structural_instructions_authored"] is True


def test_an_ambiguous_or_absent_operation_is_refused_rather_than_guessed():
    from metamorphosis.m060_body_compiler import arithmetic_opcodes
    from metamorphosis.m060_wasm_emit import WasmEmitError

    pairs = [(6.0, 3.0), (2.0, 5.0)]
    twins = {"0x01": [9.0, 7.0], "0x02": [9.0, 7.0], "0x03": [18.0, 10.0], "0x04": [2.0, 0.4]}

    with pytest.raises(WasmEmitError, match="not uniquely determined"):
        arithmetic_opcodes(twins, pairs)
    with pytest.raises(WasmEmitError, match="not uniquely determined"):
        arithmetic_opcodes({"0x01": [9.0, 7.0]}, pairs)


def test_the_compiler_is_repository_code_not_a_blob(manifest):
    value = manifest.to_dict()

    assert value["compiler_is_repository_code"] is True
    assert value["precompiled_bytes_embedded"] is False


def test_the_compiler_does_not_shell_out_or_read_a_wat_file():
    """The module must be the compiler, not a wrapper around an external toolchain.

    Checked on executable code rather than on the text: the docstrings legitimately discuss
    the toolchain the module exists to avoid, and grepping the raw source flagged its own
    explanation of why it does not use one.
    """
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[1].joinpath("metamorphosis", "m060_body_compiler.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        for alias in (node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else [])
    }
    assert "subprocess" not in imported
    assert "os" not in imported

    called = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Name):
            called.add(target.id)
        elif isinstance(target, ast.Attribute):
            called.add(target.attr)

    for forbidden in ("open", "read_text", "read_bytes", "run", "Popen", "system", "check_output"):
        assert forbidden not in called, forbidden


def test_emission_is_deterministic(manifest, module):
    from metamorphosis.m060_body_compiler import compile_body

    assert manifest.to_dict()["replay_identical"] is True
    assert compile_body() == module


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
        "from metamorphosis.m060_whole_body_migration import "
        "run_m060_whole_body_migration as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    assert manifest.digest() == completed.stdout.decode("utf-8").strip().splitlines()[-1]
