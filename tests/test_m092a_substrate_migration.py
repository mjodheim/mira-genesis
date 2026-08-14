"""M092-A — the substrate is state, the state is the authority, and the legacy module is absent.

Conservation tests say the migration changed no meaning. Authority tests say it moved control. Both
are needed: a migration that copied semantics into state while still executing them from host code
would pass the first set and fail the second.

Several tests deliberately damage something and require the damage to show. A falsifier that cannot
fire is the M086-A shape, and it is what D061 forbids here.
"""
from __future__ import annotations

import ast
import inspect
import itertools
import json
import subprocess
import sys
from dataclasses import replace

import pytest

from metamorphosis.m090_language import (
    BINARY_OPERATORS, CONST_VALUES, INPUT_COUNT, MAX_BODY_LENGTH, MICRO_OPERATIONS, SLOT_COUNT,
    UNARY_OPERATORS, LanguageError, execute, run_body,
)
from metamorphosis import m092_kernel, m092_runtime, m092_substrate_state
from metamorphosis.m091_substrate import MAX_ASSEMBLY_LENGTH
from metamorphosis.m092_kernel import (
    INSTRUCTION_SET, MAX_PROGRAM_LENGTH, REGISTER_COUNT, KernelError, Machine, default_fuel,
    execute_program, fuel_policy_provenance, has_backward_jump, kernel_manifest, program_digest,
    program_from_list, program_to_list, validate_program,
)
from metamorphosis.m092_migration import (
    CONSERVATION_STATES, INHERITED_SUBSTRATE_OPERATIONS, capability_conservation, enumerate_bodies,
    exhaustive_legal_conservation, exhaustive_representation_conservation, inherited_l1,
    intractable_dimension, language_conservation, legal_alphabet, migrated_l0, migrated_substrate,
    observe_reference, observe_state, refusal_conservation, refusal_taxonomy_can_fail,
    serialization_conservation, signature_conservation, stack_depth_certificate,
    to_runtime_language,
)
from metamorphosis.m092_runtime import (
    RefusalCode, RuntimeLanguage, RuntimePrimitive, SubstrateError,
)
from metamorphosis.m092_substrate_state import (
    ParameterDomain, SubstrateOperation, SubstrateState, execute_from_state,
    registered_reach_report, run_body_from_state,
)

RUNTIME_MODULES = (m092_runtime, m092_kernel, m092_substrate_state)


@pytest.fixture(scope="module")
def substrate() -> SubstrateState:
    return migrated_substrate()


@pytest.fixture(scope="module")
def language() -> RuntimeLanguage:
    return to_runtime_language(inherited_l1())


# ------------------------------------------------------------------------ the AST-level scanner


def executable_source(module) -> str:
    """Module source with docstrings removed, so prose cannot fail a code check.

    A module is allowed to *discuss* a micro-operation in its documentation; what must not happen is
    executable code branching on one. Comments never reach the AST, so unparsing drops them too.
    """

    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_no_inherited_operation_name_in_any_runtime_module() -> None:
    """Zero inherited micro-operation names and zero operator names, in all three modules."""

    for module in RUNTIME_MODULES:
        source = executable_source(module)
        found = [name for name in MICRO_OPERATIONS if name in source]
        assert found == [], f"{module.__name__} branches on {found}"
        operators = [
            operator for operator in tuple(BINARY_OPERATORS) + tuple(UNARY_OPERATORS)
            if f"'{operator}'" in source or f'"{operator}"' in source
        ]
        assert operators == [], f"{module.__name__} names operators {operators}"


def test_the_scanner_detects_deliberately_planted_names() -> None:
    """Positive control. Without it, every scan above could pass by returning nothing."""

    # the migration module is exactly where these names SHOULD appear in executable code
    from metamorphosis import m092_migration

    source = executable_source(m092_migration)
    assert "PUSH_SLOT" in source and "BINOP:max" in source and "'max'" in source
    assert len(source) > 2000

    # and a synthetic module with a planted name is caught
    planted = ast.parse("def f():\n    return 'PUSH_SLOT'\n")
    assert "PUSH_SLOT" in ast.unparse(planted)


# ------------------------------------------------------------------------------------- the kernel


def test_kernel_contains_no_prohibited_capability() -> None:
    manifest = kernel_manifest()
    for flag in (
        "contains_modulo_or_division", "contains_parity_operation", "contains_target_predicate",
        "contains_lookup_table", "contains_host_callback",
        "branches_on_micro_operation_identifiers",
    ):
        assert manifest[flag] is False
    assert manifest["is_the_next_ceiling"] is True
    assert "MOD" not in INSTRUCTION_SET and "DIV" not in INSTRUCTION_SET


def test_kernel_rejects_malformed_programs() -> None:
    for program in (
        (),
        (("NOPE",),),
        (("LOADI", 0),),
        (("LOADI", REGISTER_COUNT, 1), ("HALT",)),
        (("JMP", 99), ("HALT",)),
        tuple(("HALT",) for _ in range(MAX_PROGRAM_LENGTH + 1)),
    ):
        with pytest.raises(KernelError) as caught:
            validate_program(program)
        assert caught.value.code is RefusalCode.MALFORMED_PROGRAM


def test_kernel_refuses_on_resource_exhaustion() -> None:
    looping = (("LOADI", 0, 1), ("JNZ", 0, 0), ("HALT",))
    with pytest.raises(KernelError) as caught:
        execute_program(looping, Machine(), fuel=500)
    assert caught.value.code is RefusalCode.RESOURCE_EXHAUSTED


def test_kernel_can_iterate_but_nothing_registered_does(substrate: SubstrateState) -> None:
    """`can execute` is not `has registered`, and the two are separately reported."""

    # r0 = n; r2 = 0; while r0 != 0: r2 += r0; r0 -= 1     -- a neutral countdown accumulator
    countdown = (
        ("ARG", 0), ("LOADI", 1, 1), ("LOADI", 2, 0),
        ("JZ", 0, 7),
        ("ADD", 2, 2, 0), ("SUB", 0, 0, 1), ("JMP", 3),
        ("SPUSH", 2), ("HALT",),
    )
    assert has_backward_jump(countdown) is True
    assert execute_program(countdown, Machine(argument=6), fuel=500).stack == [21]

    report = registered_reach_report(substrate)
    assert report["every_registered_program_is_loop_free"] is True
    assert report["acquired_operations"] == []
    assert report["kernel_potential_expressivity_is_larger"] is True
    assert report["loop_freedom_is_corroboration_not_definition"] is True


def test_fuel_policy_provenance_is_recorded_and_target_free() -> None:
    provenance = fuel_policy_provenance()
    assert provenance["derived_from_a_target_value"] is False
    assert provenance["derived_from_a_qualifying_world"] is False
    assert provenance["fitted_to_any_candidate_implementation"] is False
    assert provenance["binding_for_m092a"] is False
    # the base must actually satisfy the requirement it claims to be derived from
    assert provenance["fuel_base"] >= provenance["fuel_base_requirement"]
    assert default_fuel([100], 0) > default_fuel([1], 0)


def test_fuel_tracks_values_received_through_stack_and_slots() -> None:
    """The future substrate operand is machine state, not necessarily a call argument or input."""

    baseline = default_fuel([0], 0, [1], [0])
    assert default_fuel([0], 0, [10_000], [0]) > baseline
    assert default_fuel([0], 0, [], [10_000]) > baseline

    # The executor must use the same complete entry-state rule, not the old inputs-only shortcut.
    countdown = (
        ("SPOP", 0), ("LOADI", 1, 1), ("JZ", 0, 5),
        ("SUB", 0, 0, 1), ("JMP", 2), ("SPUSH", 0), ("HALT",),
    )
    machine = execute_program(countdown, Machine(stack=[1_000], inputs=[0], slots=[0]))
    assert machine.stack == [0]


def test_program_serialization_round_trips() -> None:
    for operation in INHERITED_SUBSTRATE_OPERATIONS:
        restored = program_from_list(program_to_list(operation.program))
        assert restored == operation.program
        assert program_digest(restored) == program_digest(operation.program)


# -------------------------------------------------------------------------------- the state itself


def test_dispatch_and_validation_rules_come_from_state(substrate: SubstrateState) -> None:
    assert substrate.dispatch_key("BINOP", "max") == "BINOP:max"
    assert substrate.dispatch_key("PUSH_SLOT", 2) == "PUSH_SLOT"
    assert substrate.selector_names == frozenset({"BINOP", "UNOP"})
    assert substrate.operation_names == frozenset(MICRO_OPERATIONS)
    # the unary-operator domain is data referencing an operation, not a name in code
    domain = substrate.domain("unary_op")
    assert domain is not None and domain.rule == "selector_of" and domain.reference == "UNOP"
    assert substrate.selector_values(domain.reference) == tuple(sorted(UNARY_OPERATORS))


def test_arity_is_declared_in_state_and_checked_before_the_selector(
    substrate: SubstrateState,
) -> None:
    """The defect the semantic taxonomy caught: arity must beat selector validity."""

    assert substrate.minimum_stack_depth("BINOP") == 2
    assert substrate.minimum_stack_depth("UNOP") == 1
    assert substrate.minimum_stack_depth("PUSH_SLOT") == 0
    # both invalid at once: too few operands AND an unregistered selector
    body = (("BINOP", "nonesuch"),)
    assert observe_reference(body, (), (0,) * 4, (0,) * 3) == (
        "refused", RefusalCode.STACK_UNDERFLOW.value,
    )
    assert observe_state(body, (), (0,) * 4, (0,) * 3, substrate) == (
        "refused", RefusalCode.STACK_UNDERFLOW.value,
    )


def test_state_round_trips_and_digests_stably(substrate: SubstrateState) -> None:
    text = substrate.serialize()
    restored = SubstrateState.deserialize(text)
    assert restored.serialize() == text
    assert restored.digest() == substrate.digest()
    assert SubstrateState.from_dict(json.loads(text)).digest() == substrate.digest()


def test_state_rejects_schema_drift(substrate: SubstrateState) -> None:
    for mutate in (
        lambda d: d.update(schema="something-else"),
        lambda d: d.update(unexpected=True),
        lambda d: d.pop("parameter_domains"),
    ):
        payload = substrate.to_dict()
        mutate(payload)
        with pytest.raises(SubstrateError) as caught:
            SubstrateState.from_dict(payload)
        assert caught.value.code is RefusalCode.MALFORMED_STATE


def test_state_rejects_forbidden_capability_and_mixed_dispatch() -> None:
    with pytest.raises(SubstrateError):
        SubstrateState(
            operations=(
                SubstrateOperation("X", "none", (("HALT",),), "inherited",
                                   capabilities=("network",)),
            ),
            slot_count=4, input_count=3, max_body_length=6, max_stack_depth=8,
            literal_values=(0, 1), permitted_capabilities=("pure_slot_write",),
            forbidden_capabilities=("network",),
        )
    with pytest.raises(SubstrateError):
        SubstrateState(
            operations=(
                SubstrateOperation("Z", "none", (("HALT",),), "inherited"),
                SubstrateOperation("Z:a", "selector", (("HALT",),), "inherited"),
            ),
            slot_count=4, input_count=3, max_body_length=6, max_stack_depth=8,
            literal_values=(0, 1),
        )


def test_state_rejects_ambiguous_or_impossible_serialized_contracts(
    substrate: SubstrateState,
) -> None:
    mutations = [
        lambda: replace(substrate, slot_count=-1),
        lambda: replace(substrate, max_body_length=-1),
        lambda: replace(
            substrate,
            operations=(
                replace(substrate.operations[0], minimum_stack_depth=-1),
                *substrate.operations[1:],
            ),
        ),
        lambda: replace(
            substrate,
            parameter_domains=substrate.parameter_domains
            + (ParameterDomain("slot", "slot_index"),),
        ),
    ]
    for mutate in mutations:
        with pytest.raises(SubstrateError) as caught:
            mutate()
        assert caught.value.code is RefusalCode.MALFORMED_STATE


def test_runtime_language_rejects_duplicate_ids_and_unavailable_capabilities(
    substrate: SubstrateState, language: RuntimeLanguage,
) -> None:
    with pytest.raises(SubstrateError) as duplicate:
        RuntimeLanguage(primitives=(language.primitives[0], language.primitives[0]))
    assert duplicate.value.code is RefusalCode.MALFORMED_STATE

    base = language.primitives[0]
    forbidden = RuntimePrimitive(
        primitive_id=base.primitive_id,
        parameter_kinds=base.parameter_kinds,
        body=base.body,
        origin=base.origin,
        provenance=base.provenance,
        capabilities=("network",),
    )
    bad_language = RuntimeLanguage(
        primitives=(forbidden, *language.primitives[1:]),
        language_version=language.language_version,
        provenance=language.provenance,
    )
    with pytest.raises(SubstrateError) as unavailable:
        execute_from_state(
            [(forbidden.primitive_id, (0, 0))], (1, 2, 3), bad_language, substrate,
        )
    assert unavailable.value.code is RefusalCode.MALFORMED_STATE


def test_editing_a_program_preserves_declared_arity(substrate: SubstrateState) -> None:
    """Rewriting semantics must not silently rewrite arity, or sibling selectors disagree."""

    mutated = substrate.replacing("UNOP:inc", [("SPOP", 0), ("SPUSH", 0), ("HALT",)])
    assert mutated.minimum_stack_depth("UNOP") == 1
    assert mutated.operation("UNOP:inc").minimum_stack_depth == 1


# ------------------------------------------------------------------------------------ conservation


def test_signatures_domains_and_capabilities_are_exactly_m091s(substrate: SubstrateState) -> None:
    signatures = signature_conservation(substrate)
    for flag in ("names_identical", "binary_identical", "unary_identical", "literals_identical"):
        assert signatures[flag] is True
    assert signatures["nothing_acquired"] is True
    assert signatures["acquired_operations"] == []

    capabilities = capability_conservation(substrate)
    assert capabilities["vocabulary_matches_reference"] is True
    assert capabilities["holds_only_permitted"] is True
    assert capabilities["holds_nothing_forbidden"] is True
    assert capabilities["capability_set_unchanged"] is True


def test_exhaustive_conservation_over_the_complete_legal_space(substrate: SubstrateState) -> None:
    """Exhaustive to the assembly bound -- every body the inherited system could construct."""

    report = exhaustive_legal_conservation(substrate, 2)
    assert report["exhaustive"] is True
    assert report["mismatches"] == 0
    assert report["first_mismatch"] is None
    assert report["legal_bodies_enumerated"] == sum(
        len(legal_alphabet()) ** length for length in (1, 2)
    )


def test_exhaustive_conservation_including_out_of_representation(
    substrate: SubstrateState,
) -> None:
    report = exhaustive_representation_conservation(substrate, 2)
    assert report["mismatches"] == 0
    assert report["comparisons"] == report["agreeing_values"] + report["agreeing_refusals"]
    # refusals are recorded by semantic code, not merely counted
    assert len(report["refusals_by_code"]) >= 3


def test_the_intractable_dimension_is_named() -> None:
    report = intractable_dimension()
    assert report["explosion_dimension"] == "alphabet_size ** body_length"
    assert report["exhausted_to"] == MAX_ASSEMBLY_LENGTH
    assert report["legal_space_by_length"][str(MAX_BODY_LENGTH)] > 10_000_000


def test_language_conservation_covers_every_declared_binding(substrate: SubstrateState) -> None:
    for state in (migrated_l0(), inherited_l1()):
        report = language_conservation(substrate, state, 1)
        assert report["mismatches"] == 0
        assert report["coverage_is_complete"] is True
        assert report["declared_bindings"] == report["covered_bindings"]


def test_acquired_m091_primitive_is_conserved(
    substrate: SubstrateState, language: RuntimeLanguage,
) -> None:
    reference_language = inherited_l1()
    program = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg")), ("CLAMP_FLOOR", (0,))]
    for inputs, _ in CONSERVATION_STATES:
        assert execute(program, inputs, reference_language) == execute_from_state(
            program, inputs, language, substrate,
        )


def test_serialization_is_behaviourally_conserved(substrate: SubstrateState) -> None:
    report = serialization_conservation(substrate)
    assert report["byte_identical"] is True
    assert report["digest_identical"] is True
    assert report["behavioural_mismatches"] == 0


# -------------------------------------------------------------------- the semantic refusal taxonomy


def test_every_declared_refusal_produces_the_same_semantic_code(substrate: SubstrateState) -> None:
    report = refusal_conservation(substrate)
    assert report["disagreements"] == 0
    for row in report["cases"]:
        assert row["agree"] is True, row
        assert row["matches_declared_code"] is True, row
    assert len(report["codes_observed"]) >= 6


def test_the_taxonomy_detects_refusals_for_different_reasons(substrate: SubstrateState) -> None:
    """Without this, `refused == refused` would still be the effective comparison."""

    report = refusal_taxonomy_can_fail(substrate)
    assert report["all_detected"] is True
    assert report["cases_where_both_refused_differently"] >= 2
    for row in report["cases"]:
        assert row["mismatch_detected"] is True, row


def test_refusal_codes_are_implementation_independent() -> None:
    """The state path raises typed codes; the reference is normalized into the same vocabulary."""

    assert {code.value for code in RefusalCode} >= {
        "unknown_operation", "invalid_selector", "stack_underflow", "invalid_slot_index",
        "invalid_input_index", "body_length_exceeded", "resource_exhausted", "malformed_program",
        "malformed_state", "signature_mismatch",
    }


# -------------------------------------------------------------------- the stack-bound certificate


def test_stack_overflow_is_unreachable_by_construction() -> None:
    """Not "we did not see it" -- a static bound, verified against the reference."""

    certificate = stack_depth_certificate()
    assert certificate["every_operation_increases_depth_by_at_most"] == 1
    assert certificate["max_reachable_stack_depth"] == MAX_BODY_LENGTH
    assert certificate["max_reachable_stack_depth"] < certificate["declared_stack_bound"]
    assert certificate["bound_is_reachable"] is False
    assert certificate["effect_disagreements"] == []
    assert certificate["declared_effects_verified_against_the_reference"] > 30


# ---------------------------------------------------------------------------------------- authority


def test_removing_an_operation_removes_the_capability(
    substrate: SubstrateState, language: RuntimeLanguage,
) -> None:
    program = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg")), ("CLAMP_FLOOR", (0,))]
    assert execute_from_state(program, (3, 1, -2), language, substrate)
    without = substrate.without("BINOP:max")
    with pytest.raises(SubstrateError):
        execute_from_state(program, (3, 1, -2), language, without)
    assert execute_from_state(
        [("COPY_INPUT", (0, 0))], (3, 1, -2), language, without,
    ) == execute_from_state([("COPY_INPUT", (0, 0))], (3, 1, -2), language, substrate)


def test_corrupting_a_program_changes_semantics(
    substrate: SubstrateState, language: RuntimeLanguage,
) -> None:
    program = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg"))]
    before = execute_from_state(program, (3, 1, -2), language, substrate)
    corrupted = substrate.replacing("UNOP:neg", [
        ("SPOP", 0), ("LOADI", 1, 7), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ])
    assert execute_from_state(program, (3, 1, -2), language, corrupted) != before


def test_no_fallback_to_legacy_host_semantics(substrate: SubstrateState) -> None:
    with pytest.raises(SubstrateError) as caught:
        run_body_from_state((("NO_SUCH_OP", 0),), (), [0] * 4, [0] * 3, substrate)
    assert caught.value.code is RefusalCode.UNKNOWN_OPERATION

    without = substrate.without("PUSH_SLOT")
    with pytest.raises(SubstrateError):
        run_body_from_state((("PUSH_SLOT", 0),), (), [0] * 4, [0] * 3, without)
    # ...while the reference oracle still runs it, proving the two paths are separate
    assert run_body((("PUSH_SLOT", 0),), (), [5, 0, 0, 0], [0, 0, 0]) == [5, 0, 0, 0]


def test_editing_state_diverges_from_the_reference_oracle(substrate: SubstrateState) -> None:
    body = (("PUSH_SLOT", 0), ("UNOP", "double"), ("STORE_SLOT", 0))
    mutated = substrate.replacing("UNOP:double", [
        ("SPOP", 0), ("LOADI", 1, 3), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ])
    assert run_body(body, (), [5, 0, 0, 0], [0, 0, 0]) == [10, 0, 0, 0]
    assert run_body_from_state(body, (), [5, 0, 0, 0], [0, 0, 0], mutated) == [15, 0, 0, 0]


def test_no_runtime_module_imports_a_historical_module() -> None:
    """The strong form of the authority claim, checked statically over the import graph."""

    for module in RUNTIME_MODULES:
        tree = ast.parse(inspect.getsource(module))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        offending = [
            name for name in imported
            if any(token in name for token in ("m089", "m090", "m091"))
        ]
        assert offending == [], f"{module.__name__} imports {offending}"


def test_physical_isolation_without_the_legacy_module(tmp_path) -> None:
    """Build a runtime whose directory does not contain `m090_language.py`, and execute anyway.

    Stronger than an import census or a tripwire: the legacy authority is not present, not
    shadowable, and not reachable through an injected meta-path finder.
    """

    from scripts.run_m092a_migration import build_probes, expected_outcomes, write_state

    substrate_state = migrated_substrate()
    reference_language = inherited_l1()
    runtime = to_runtime_language(reference_language)
    probes = build_probes(reference_language)
    state_path = tmp_path / "state.json"
    write_state(str(state_path), reference_language, substrate_state, probes)
    expected = expected_outcomes(probes, runtime, substrate_state)

    completed = subprocess.run(
        [sys.executable, "-m", "scripts.run_m092a_isolation", "--state", str(state_path)],
        capture_output=True, text=True,
    )
    report = json.loads(completed.stdout)
    assert completed.returncode == 0, completed.stderr[-2000:]
    assert report["findings"] == []
    assert report["m090_language_present_in_root"] is False
    assert report["modules_outside_the_isolated_root_or_stdlib"] == []
    assert sorted(report["loaded_project_modules"]) == [
        "__main__", "m092_kernel", "m092_runtime", "m092_substrate_state",
    ]
    assert report["outcomes"]
    for row in report["outcomes"]:
        assert (row["slots"] if row["status"] == "value" else None) == expected[row["id"]]


def test_rollback_is_exact_after_damage(substrate: SubstrateState) -> None:
    text = substrate.serialize()
    damaged = substrate.without("BINOP:max")
    assert damaged.digest() != substrate.digest()
    restored = SubstrateState.deserialize(text)
    assert restored.serialize() == text
    assert restored.digest() == substrate.digest()
    for body in itertools.islice(enumerate_bodies(2), 400):
        for inputs, slots in CONSERVATION_STATES[:2]:
            assert observe_state(body, (), slots, inputs, restored) == observe_state(
                body, (), slots, inputs, substrate,
            )
