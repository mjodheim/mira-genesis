"""M056 falsifications.

The experiment asks whether a capability learned *after* the first migration survives the
second one. The answer is only worth something if the compiler cannot have been written to
carry that particular capability, so the tests that pin the compiler's indifference to names
come first.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from metamorphosis.m056_second_migration import (
    M056Error, M056_PROTOCOL, adopt, corrupt_state, detect_fault, execute_on_wasm,
    execute_without_wasm, learning_cases, propose_post_migration_capability,
    reconstruct_m048_version_eight, restore, run_m056_second_migration, snapshot_state,
)
from metamorphosis.m056_wasm_compiler import (
    EXPRESSION_ARITY, WasmCompileError, compile_tools_to_wasm, declared_tools,
)


@pytest.fixture(scope="module")
def lineage():
    return reconstruct_m048_version_eight()


@pytest.fixture(scope="module")
def manifest():
    return run_m056_second_migration()


def _body_with(modules):
    return {"schema": "m048-js-body-v1", "modules": modules, "regression_cases": []}


def _tool_module(name, meta):
    return {"name": name, "source": "// stub\n", "meta": meta}


def test_the_compiler_reads_declarations_and_not_names():
    """The load-bearing anti-cheating property.

    A compiler with a case for `tool_max` would carry the post-migration capability across
    while proving nothing. These bodies name their modules deliberately badly.
    """
    disguised = _body_with([
        _tool_module("tool_zzz", {"kind": "synthesized_tool", "tool_name": "peak", "expression_id": "maximum"}),
    ])

    module, tools = compile_tools_to_wasm(disguised)

    assert [tool.tool_name for tool in tools] == ["peak"]
    assert tools[0].expression_id == "maximum"
    assert module.startswith(b"\x00asm")


def test_a_module_named_like_a_known_tool_but_declaring_nothing_known_is_refused():
    liar = _body_with([
        _tool_module("tool_max", {"kind": "synthesized_tool", "tool_name": "max", "expression_id": "sorcery"}),
    ])

    with pytest.raises(WasmCompileError, match="no emission rule"):
        compile_tools_to_wasm(liar)


def test_an_unknown_tool_kind_is_refused():
    with pytest.raises(WasmCompileError, match="unknown tool kind"):
        compile_tools_to_wasm(_body_with([_tool_module("tool_x", {"kind": "smuggled"})]))
    with pytest.raises(WasmCompileError, match="declares no tool module"):
        compile_tools_to_wasm(_body_with([]))


def test_the_two_synthesized_tools_take_the_same_path(lineage):
    """`tool_mean` was learned before the first migration and `tool_max` after it."""
    tools = {tool.tool_name: tool for tool in declared_tools(lineage.body())}

    assert tools["mean"].origin == "synthesized"
    assert tools["max"].origin == "synthesized"
    assert tools["add"].origin == "founder"
    assert set(tools) == {"add", "mul", "max", "mean"}


def test_the_emitted_module_declares_no_imports(manifest):
    value = manifest.to_dict()

    assert value["compilation"]["imports"] == 0
    assert value["migrated_wasm_import_count"] == 0
    assert value["semantic_delegation_to_javascript"] is False


def test_every_inherited_capability_survives_the_second_migration(manifest):
    value = manifest.to_dict()

    assert value["inherited_version"] == 8
    assert value["inherited_retained_case_count"] == 32
    assert value["pre_first_migration_case_count"] == 28
    assert value["migrated_all_retained_passed"] is True
    assert sorted(value["migrated_wasm_exported_tools"]) == ["add", "max", "mean", "mul"]


def test_the_capability_learned_after_the_first_migration_survives_the_second(manifest):
    """The question the experiment exists to answer."""
    value = manifest.to_dict()

    assert value["post_migration_case_count"] == 4
    assert value["post_migration_capability_survived_second_migration"] is True


def test_removing_the_module_breaks_every_capability(lineage):
    """The counter-check. If the shell still answers, the semantics never left JavaScript."""
    without = execute_without_wasm(lineage.body(), lineage.retained)

    assert without["any_passed"] is False
    assert without["passed_count"] == 0
    assert without["total"] == 32


def test_the_migrated_arithmetic_is_f64_and_not_integer(lineage):
    """`mean` divides, which makes the operand type observable end to end.

    The inherited `critique` module rounds a non-integer result to two decimals, so the
    pipeline reports `2.33` for `mean 1 2 4`. Under integer division the tool would have
    returned exactly `2`, `critique` would have left it alone, and the case would read `2`.
    The reported value therefore discriminates f64 from integer arithmetic rather than merely
    agreeing with it.
    """
    module, _tools = compile_tools_to_wasm(lineage.body())
    case = type(lineage.retained[0])
    cases = [
        case("m056_exact_1", "mean 1 2 4", 2.33, "m056_exact"),
        case("m056_exact_2", "mean 1 2 3", 2, "m056_exact"),
        case("m056_exact_3", "mean -4 7 0", 1, "m056_exact"),
    ]

    execution = execute_on_wasm(lineage.body(), module, cases)

    assert execution["all_passed"] is True, [
        (item["request"], item["expected"], item["result"].get("output"))
        for item in execution["case_results"] if not item["passed"]
    ]


def test_the_lineage_learns_again_in_the_migrated_substrate(manifest):
    value = manifest.to_dict()

    assert value["learned_token"] == "minimum"
    assert value["learned_tool"] == "min"
    assert value["learned_in_runtime"] == "webassembly"
    assert value["candidate_tool_count"] == 5
    assert value["learning_hidden_passed"] is True
    assert value["accepted_version"] == 9


def test_adoption_requires_validation_and_the_inherited_bank(lineage):
    with pytest.raises(M056Error, match="unvalidated"):
        adopt(lineage.state, lineage.body(), {"accepted": False, "inherited_regression_passed": True})
    with pytest.raises(M056Error, match="inherited regression"):
        adopt(lineage.state, lineage.body(), {"accepted": True, "inherited_regression_passed": False})


def test_the_inherited_bank_is_executed_after_learning_not_assumed(manifest):
    value = manifest.to_dict()

    assert value["learning_inherited_regression_total"] == 32
    assert value["learning_inherited_regression_passed"] is True


def test_an_intact_state_reports_no_fault(lineage):
    """A detector that cannot answer no proves nothing."""
    from metamorphosis.m056_second_migration import _state_digest

    assert detect_fault(lineage.state, _state_digest(lineage.state)) is False


def test_a_tampered_state_is_detected_and_restored_byte_for_byte(lineage):
    from metamorphosis.m056_second_migration import _state_digest

    digest = _state_digest(lineage.state)
    snapshot = snapshot_state(lineage.state)

    assert detect_fault(corrupt_state(lineage.state), digest) is True

    restored = restore(snapshot, digest)

    assert _state_digest(restored) == digest
    assert snapshot_state(restored) == snapshot
    with pytest.raises(M056Error, match="does not match its digest"):
        restore(snapshot_state(corrupt_state(lineage.state)), digest)


def test_the_learning_proposal_is_deterministic(lineage):
    first_body, first_module = propose_post_migration_capability(lineage.body())
    second_body, second_module = propose_post_migration_capability(lineage.body())

    assert first_body == second_body
    assert first_module == second_module
    assert "min" in [tool.tool_name for tool in declared_tools(first_body)]


def test_the_manifest_records_the_boundaries(manifest):
    value = manifest.to_dict()

    assert value["source_runtime"] == "node-esm"
    assert value["target_runtime"] == "webassembly"
    assert value["value_type"] == "f64"
    assert value["fault_detected"] is True
    assert value["rollback_exact"] is True
    assert value["replay_identical"] is True
    assert value["capabilities_answered_without_wasm"] == 0
    assert value["arbitrary_code_generation"] is False
    assert value["network_authority"] is False
    assert value["repository_authority"] is False
    assert value["credential_authority"] is False
    assert value["deployment_authority"] is False
    assert value["canonical"] is False


def test_the_manifest_is_reproducible_across_processes(manifest):
    """Publishable because of D018."""
    script = (
        "from metamorphosis.m056_second_migration import "
        "run_m056_second_migration as r; print(r().digest())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    assert manifest.digest() == completed.stdout.decode("utf-8").strip().splitlines()[-1]


def test_the_declared_emission_rules_are_pinned():
    assert EXPRESSION_ARITY == {"add": 2, "mul": 2, "maximum": 2, "minimum": 2, "mean": 3}
    assert M056_PROTOCOL.target_runtime == "webassembly"
    assert M056_PROTOCOL.value_type == "f64"
