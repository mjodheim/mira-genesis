"""M092-A — the substrate is state, and the state is the authority.

Conservation tests say the migration changed no meaning. Authority tests say it moved control. Both
are needed: a migration that copied semantics into state while still executing them from host code
would pass the first set and fail the second.

Several tests deliberately damage something and require the damage to show. A falsifier that cannot
fire is the M086-A shape, and it is what D061 forbids here.
"""
from __future__ import annotations

import itertools
import json

import pytest

from metamorphosis.m090_language import (
    BINARY_OPERATORS, CONST_VALUES, INPUT_COUNT, MAX_BODY_LENGTH, MICRO_OPERATIONS, SLOT_COUNT,
    UNARY_OPERATORS, LanguageError, execute, run_body,
)
from metamorphosis.m092_kernel import (
    INSTRUCTION_SET, MAX_PROGRAM_LENGTH, REGISTER_COUNT, KernelError, Machine, default_fuel,
    execute_program, has_backward_jump, kernel_manifest, program_digest, program_from_list,
    program_to_list, validate_program,
)
from metamorphosis.m092_migration import (
    CONSERVATION_STATES, INHERITED_SUBSTRATE_OPERATIONS, body_conservation,
    capability_conservation, enumerate_bodies, inherited_l1, language_conservation, migrated_l0,
    migrated_substrate, refusal_conservation, serialization_conservation, signature_conservation,
    stack_bound_is_unreachable,
)
from metamorphosis.m092_substrate_state import (
    SubstrateOperation, SubstrateState, execute_from_state, registered_reach_report,
    run_body_from_state,
)


@pytest.fixture(scope="module")
def substrate() -> SubstrateState:
    return migrated_substrate()


# ------------------------------------------------------------------------------------- the kernel


def executable_source(module) -> str:
    """Module source with docstrings and comments removed, so prose cannot fail a code check.

    M091 checked its anti-lookup scanner the same way. A module is allowed to *discuss* a
    micro-operation in its documentation; what must not happen is executable code branching on one.
    """

    import ast
    import inspect

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


def test_kernel_knows_no_micro_operation() -> None:
    """The kernel's executable code must not contain a single micro-operation identifier."""

    from metamorphosis import m092_kernel

    source = executable_source(m092_kernel)
    for name in MICRO_OPERATIONS:
        assert name not in source, f"the kernel branches on {name}"
    for operator in tuple(BINARY_OPERATORS) + tuple(UNARY_OPERATORS):
        assert f"'{operator}'" not in source and f'"{operator}"' not in source


def test_the_docstring_scanner_can_fail() -> None:
    """If `executable_source` silently returned nothing, every scan above would pass vacuously."""

    from metamorphosis import m092_migration

    source = executable_source(m092_migration)
    # the migration module is exactly where micro-operation names SHOULD appear in code
    assert "PUSH_SLOT" in source and "BINOP:max" in source
    assert len(source) > 2000


def test_kernel_contains_no_prohibited_capability() -> None:
    manifest = kernel_manifest()
    assert manifest["contains_modulo_or_division"] is False
    assert manifest["contains_parity_operation"] is False
    assert manifest["contains_target_predicate"] is False
    assert manifest["contains_lookup_table"] is False
    assert manifest["contains_host_callback"] is False
    assert manifest["branches_on_micro_operation_identifiers"] is False
    assert manifest["is_the_next_ceiling"] is True
    assert "MOD" not in INSTRUCTION_SET and "DIV" not in INSTRUCTION_SET


def test_kernel_rejects_malformed_programs() -> None:
    for program, reason in (
        ((), "empty"),
        ((("NOPE",),), "unknown opcode"),
        ((("LOADI", 0),), "operand count"),
        ((("LOADI", REGISTER_COUNT, 1), ("HALT",)), "register range"),
        ((("JMP", 99), ("HALT",)), "jump target"),
        (tuple(("HALT",) for _ in range(MAX_PROGRAM_LENGTH + 1)), "length"),
    ):
        with pytest.raises(KernelError):
            validate_program(program)


def test_kernel_refuses_on_resource_exhaustion_and_running_off_the_end() -> None:
    # a program that jumps backwards forever must be stopped by fuel, not hang
    looping = (("LOADI", 0, 1), ("JNZ", 0, 0), ("HALT",))
    with pytest.raises(KernelError):
        execute_program(looping, Machine(), fuel=500)
    with pytest.raises(KernelError):
        execute_program((("LOADI", 0, 1),), Machine(), fuel=10)  # no HALT


def test_kernel_can_iterate_but_nothing_registered_does(substrate: SubstrateState) -> None:
    """`can execute` is not `has registered`. This is M092-A's central architectural claim.

    The loop below is a neutral countdown accumulator, chosen deliberately so that no target-shaped
    program appears anywhere in this repository during M092-A.
    """

    # r0 = n; r2 = 0; while r0 != 0: r2 += r0; r0 -= 1     -- sums 1..n
    countdown = (
        ("ARG", 0), ("LOADI", 1, 1), ("LOADI", 2, 0),
        ("JZ", 0, 7),
        ("ADD", 2, 2, 0), ("SUB", 0, 0, 1), ("JMP", 3),
        ("SPUSH", 2), ("HALT",),
    )
    assert has_backward_jump(countdown) is True
    machine = execute_program(countdown, Machine(argument=6), fuel=500)
    assert machine.stack == [21]

    # ...and yet no registered substrate operation can loop at all
    report = registered_reach_report(substrate)
    assert report["every_registered_program_is_loop_free"] is True
    assert report["programs_with_a_backward_jump"] == []
    assert report["acquired_operations"] == []
    assert report["kernel_can_express_loops"] is True


def test_program_serialization_round_trips() -> None:
    for operation in INHERITED_SUBSTRATE_OPERATIONS:
        restored = program_from_list(program_to_list(operation.program))
        assert restored == operation.program
        assert program_digest(restored) == program_digest(operation.program)


def test_fuel_depends_only_on_operand_magnitude() -> None:
    assert default_fuel([0, 0, 0], 0) == default_fuel([0], 0)
    assert default_fuel([100], 0) > default_fuel([1], 0)
    assert default_fuel([1], 100) > default_fuel([1], 0)


# -------------------------------------------------------------------------------- the state itself


def test_dispatch_rules_come_from_state_not_from_source(substrate: SubstrateState) -> None:
    from metamorphosis import m092_substrate_state

    source = executable_source(m092_substrate_state)
    mentioned = [name for name in MICRO_OPERATIONS if name in source]
    # Exactly one micro-operation name survives in executable code: the language's argument-domain
    # check has to name the operation whose registered selector values are the legal unary
    # operators. It resolves them through `selector_values`, so the domain still comes from state.
    assert mentioned == ["UNOP"], f"the dispatcher branches on {mentioned}"
    assert "selector_values('UNOP')" in source
    for operator in tuple(BINARY_OPERATORS) + tuple(UNARY_OPERATORS):
        assert f"'{operator}'" not in source

    assert substrate.dispatch_key("BINOP", "max") == "BINOP:max"
    assert substrate.dispatch_key("PUSH_SLOT", 2) == "PUSH_SLOT"
    assert substrate.selector_names == frozenset({"BINOP", "UNOP"})
    assert substrate.operation_names == frozenset(MICRO_OPERATIONS)



def test_state_round_trips_and_digests_stably(substrate: SubstrateState) -> None:
    text = substrate.serialize()
    restored = SubstrateState.deserialize(text)
    assert restored.serialize() == text
    assert restored.digest() == substrate.digest()
    assert SubstrateState.from_dict(json.loads(text)).digest() == substrate.digest()


def test_state_rejects_schema_drift(substrate: SubstrateState) -> None:
    payload = substrate.to_dict()
    payload["schema"] = "something-else"
    with pytest.raises(LanguageError):
        SubstrateState.from_dict(payload)
    payload = substrate.to_dict()
    payload["unexpected"] = True
    with pytest.raises(LanguageError):
        SubstrateState.from_dict(payload)


def test_state_rejects_forbidden_capability() -> None:
    with pytest.raises(LanguageError):
        SubstrateOperation(
            key="X", argument_role="none", program=(("HALT",),), origin="inherited",
            capabilities=("network",),
        )


def test_state_rejects_mixed_selector_dispatch() -> None:
    with pytest.raises(LanguageError):
        SubstrateState(
            operations=(
                SubstrateOperation("Z", "none", (("HALT",),), "inherited"),
                SubstrateOperation("Z:a", "selector", (("HALT",),), "inherited"),
            ),
            slot_count=4, input_count=3, max_body_length=6, max_stack_depth=8,
            literal_values=(0, 1),
        )


# ------------------------------------------------------------------------------------ conservation


def test_signatures_and_domains_are_exactly_m091s(substrate: SubstrateState) -> None:
    report = signature_conservation(substrate)
    assert report["names_identical"] is True
    assert report["binary_identical"] is True
    assert report["unary_identical"] is True
    assert report["literals_identical"] is True
    assert report["nothing_acquired"] is True
    assert report["acquired_operations"] == []


def test_capability_set_is_unchanged(substrate: SubstrateState) -> None:
    report = capability_conservation(substrate)
    assert report["holds_only_permitted"] is True
    assert report["holds_nothing_forbidden"] is True
    assert report["capability_set_unchanged"] is True


def test_body_conservation_is_exhaustive_and_exact(substrate: SubstrateState) -> None:
    report = body_conservation(substrate, 2)
    assert report["mismatches"] == 0
    assert report["first_mismatch"] is None
    assert report["agreeing_values"] > 1000
    assert report["agreeing_refusals"] > 1000
    assert report["comparisons"] == report["agreeing_values"] + report["agreeing_refusals"]


def test_language_conservation_covers_every_declared_binding(substrate: SubstrateState) -> None:
    for language in (migrated_l0(), inherited_l1()):
        report = language_conservation(substrate, language, 1)
        assert report["mismatches"] == 0
        assert report["coverage_is_complete"] is True
        assert report["declared_bindings"] == report["covered_bindings"]


def test_acquired_m091_primitive_is_conserved(substrate: SubstrateState) -> None:
    """The clamp M091 invented must mean exactly what it meant, through the new authority."""

    language = inherited_l1()
    program = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg")), ("CLAMP_FLOOR", (0,))]
    for inputs, _ in CONSERVATION_STATES:
        assert execute(program, inputs, language) == execute_from_state(
            program, inputs, language, substrate,
        )


def test_every_declared_refusal_is_conserved(substrate: SubstrateState) -> None:
    report = refusal_conservation(substrate)
    assert report["disagreements"] == 0
    assert report["refusals_on_both_sides"] >= 14


def test_serialization_is_behaviourally_conserved(substrate: SubstrateState) -> None:
    report = serialization_conservation(substrate)
    assert report["byte_identical"] is True
    assert report["digest_identical"] is True
    assert report["behavioural_mismatches"] == 0


def test_the_stack_bound_is_recorded_as_unreachable() -> None:
    """An honest negative finding, asserted so it cannot be quietly forgotten."""

    report = stack_bound_is_unreachable()
    assert report["bound_is_reachable"] is False
    assert report["maximum_reachable_stack_depth"] == MAX_BODY_LENGTH


# -------------------------------------------------------------------------------------- authority


def test_removing_an_operation_removes_the_capability(substrate: SubstrateState) -> None:
    language = inherited_l1()
    program = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg")), ("CLAMP_FLOOR", (0,))]
    assert execute_from_state(program, (3, 1, -2), language, substrate)
    without = substrate.without("BINOP:max")
    with pytest.raises(LanguageError):
        execute_from_state(program, (3, 1, -2), language, without)
    # an unrelated operation is untouched
    assert execute_from_state(
        [("COPY_INPUT", (0, 0))], (3, 1, -2), language, without,
    ) == execute_from_state([("COPY_INPUT", (0, 0))], (3, 1, -2), language, substrate)


def test_corrupting_a_program_changes_semantics(substrate: SubstrateState) -> None:
    language = inherited_l1()
    program = [("COPY_INPUT", (0, 0)), ("APPLY_UNARY", (0, "neg"))]
    before = execute_from_state(program, (3, 1, -2), language, substrate)
    corrupted = substrate.replacing("UNOP:neg", [
        ("SPOP", 0), ("LOADI", 1, 7), ("ADD", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ])
    assert execute_from_state(program, (3, 1, -2), language, corrupted) != before


def test_an_unknown_operation_does_not_fall_through_to_host_semantics(
    substrate: SubstrateState,
) -> None:
    with pytest.raises(LanguageError):
        run_body_from_state((("NO_SUCH_OP", 0),), (), [0] * 4, [0] * 3, substrate)
    # and a legal name whose entry has been deleted must not be recovered from run_body
    without = substrate.without("PUSH_SLOT")
    with pytest.raises(LanguageError):
        run_body_from_state((("PUSH_SLOT", 0),), (), [0] * 4, [0] * 3, without)
    # ...while the reference oracle still happily runs it, proving the two paths are separate
    assert run_body((("PUSH_SLOT", 0),), (), [5, 0, 0, 0], [0, 0, 0]) == [5, 0, 0, 0]


def test_editing_state_diverges_from_the_reference_oracle(substrate: SubstrateState) -> None:
    """If editing state could not change behaviour, state would not be the authority."""

    body = (("PUSH_SLOT", 0), ("UNOP", "double"), ("STORE_SLOT", 0))
    mutated = substrate.replacing("UNOP:double", [
        ("SPOP", 0), ("LOADI", 1, 3), ("MUL", 2, 0, 1), ("SPUSH", 2), ("HALT",),
    ])
    assert run_body(body, (), [5, 0, 0, 0], [0, 0, 0]) == [10, 0, 0, 0]
    assert run_body_from_state(body, (), [5, 0, 0, 0], [0, 0, 0], mutated) == [15, 0, 0, 0]


def test_dispatcher_never_imports_or_calls_run_body() -> None:
    import inspect

    from metamorphosis import m092_substrate_state

    source = inspect.getsource(m092_substrate_state)
    assert "run_body(" not in source.replace("run_body_from_state(", "")
    assert "from metamorphosis.m090_language import" in source
    assert "run_body" not in source.split("__all__")[0].split("import (")[1].split(")")[0]


def test_rollback_is_exact_after_damage(substrate: SubstrateState) -> None:
    text = substrate.serialize()
    damaged = substrate.without("BINOP:max")
    assert damaged.digest() != substrate.digest()
    restored = SubstrateState.deserialize(text)
    assert restored.serialize() == text
    assert restored.digest() == substrate.digest()
    for body in itertools.islice(enumerate_bodies(2), 400):
        for inputs, slots in CONSERVATION_STATES[:2]:
            def observe(state):
                try:
                    return tuple(run_body_from_state(body, (), list(slots), inputs, state))
                except LanguageError:
                    return "refused"
            assert observe(restored) == observe(substrate)
