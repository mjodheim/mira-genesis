from __future__ import annotations

from dataclasses import replace
import json

import pytest

from metamorphosis.m043_mealy import MealyMachine, exact_mealy_equivalence
from metamorphosis.m043_native_program import (
    NativeMealyProgram,
    NativeNode,
    NativeProgramError,
    NativeSynthesisCertificate,
    audit_program_against_discovery,
    native_program_to_mealy,
    synthesize_native_mealy,
)
from metamorphosis.m043_opaque_substrate import (
    discover_field_substrate,
    make_development_positive_machine,
)
from metamorphosis.m043_rewrite import exact_body_bytes


@pytest.fixture(scope="module")
def source() -> MealyMachine:
    return MealyMachine(
        input_alphabet=(0, 1, 2),
        output_alphabet=(0, 1, 2),
        transitions=((1, 0, 2), (1, 2, 0), (2, 0, 1)),
        outputs=((0, 1, 2), (2, 0, 1), (1, 2, 0)),
        initial=0,
    )


@pytest.fixture(scope="module")
def native_case(source: MealyMachine):
    machine = make_development_positive_machine(0)
    discovery = discover_field_substrate(machine)
    program, certificate = synthesize_native_mealy(source, discovery, machine)
    return machine, discovery, program, certificate


def test_native_synthesis_is_pairwise_and_behaviourally_exact(
    source: MealyMachine, native_case
) -> None:
    machine, _, program, certificate = native_case
    reconstructed = native_program_to_mealy(program, machine)
    assert reconstructed == source
    assert exact_mealy_equivalence(source, reconstructed) == (True, None)
    assert certificate.exact
    assert certificate.exact_pair_count == 9


def test_native_program_is_a_table_free_scalar_dag(source: MealyMachine, native_case) -> None:
    _, _, program, certificate = native_case
    payload = program.to_dict()
    forbidden = {"transitions", "outputs", "transition_table", "output_table", "table"}
    assert forbidden.isdisjoint(payload)
    assert exact_body_bytes(source) not in program.to_bytes()
    assert certificate.forbidden_table_keys_absent
    assert not certificate.source_body_bytes_embedded
    assert certificate.maximum_call_arity <= 2
    assert program.reachable_node_indices() == frozenset(range(len(program.nodes)))


def test_native_program_round_trip_is_byte_identical(native_case) -> None:
    _, _, program, _ = native_case
    restored = NativeMealyProgram.from_bytes(program.to_bytes())
    assert restored == program
    assert restored.to_bytes() == program.to_bytes()
    assert restored.digest() == program.digest()


def test_synthesis_certificate_round_trip(native_case) -> None:
    _, _, _, certificate = native_case
    restored = NativeSynthesisCertificate.from_dict(certificate.to_dict())
    assert restored == certificate
    assert restored.digest() == certificate.digest()


def test_native_execution_matches_source_on_words(source: MealyMachine, native_case) -> None:
    machine, _, program, _ = native_case
    words = [(), (0,), (1, 2), (2, 1, 0), (0, 1, 2, 0, 2)]
    assert [program.transduce(machine, word) for word in words] == [
        source.transduce(word) for word in words
    ]


def test_three_opaque_substrates_produce_distinct_exact_programs(
    source: MealyMachine,
) -> None:
    digests = set()
    for family in range(3):
        machine = make_development_positive_machine(family)
        discovery = discover_field_substrate(machine)
        program, certificate = synthesize_native_mealy(source, discovery, machine)
        assert certificate.exact
        digests.add(program.digest())
    assert len(digests) == 3


def test_program_rejects_forward_references(native_case) -> None:
    _, _, program, _ = native_case
    nodes = list(program.nodes)
    call_index = next(index for index, node in enumerate(nodes) if node.kind == "call")
    nodes[call_index] = replace(nodes[call_index], args=(call_index,))
    with pytest.raises(NativeProgramError, match="forward reference"):
        replace(program, nodes=tuple(nodes))


def test_program_rejects_unreachable_payload_nodes(native_case) -> None:
    _, _, program, _ = native_case
    with pytest.raises(NativeProgramError, match="unreachable payload"):
        replace(program, nodes=program.nodes + (NativeNode("constant", value=4),))


def test_program_parser_rejects_direct_transition_table_smuggling(native_case) -> None:
    _, _, program, _ = native_case
    raw = program.to_dict()
    raw["transitions"] = [[0, 1, 2]]
    with pytest.raises(NativeProgramError, match="invalid native program fields"):
        NativeMealyProgram.from_bytes(json.dumps(raw))


def test_program_parser_rejects_missing_fields(native_case) -> None:
    _, _, program, _ = native_case
    raw = program.to_dict()
    del raw["output_root"]
    with pytest.raises(NativeProgramError):
        NativeMealyProgram.from_bytes(json.dumps(raw))


def test_program_rejects_constants_outside_field(native_case) -> None:
    _, _, program, _ = native_case
    nodes = list(program.nodes)
    constant_index = next(
        index for index, node in enumerate(nodes) if node.kind == "constant"
    )
    nodes[constant_index] = replace(nodes[constant_index], value=5)
    with pytest.raises(NativeProgramError, match="outside the field"):
        replace(program, nodes=tuple(nodes))


def test_discovery_binding_is_checked(native_case) -> None:
    _, discovery, program, _ = native_case
    with pytest.raises(NativeProgramError, match="another discovery"):
        audit_program_against_discovery(
            replace(program, discovery_digest="0" * 64), discovery
        )


def test_machine_binding_is_checked(native_case) -> None:
    machine, _, program, _ = native_case
    other = make_development_positive_machine(1)
    with pytest.raises(NativeProgramError, match="another substrate"):
        program.step(other, 0, 0)
    assert machine.machine_id == program.machine_id


def test_source_state_capacity_must_fit_the_field() -> None:
    source = MealyMachine(
        (0, 1, 2),
        (0, 1, 2),
        tuple((state, state, state) for state in range(6)),
        tuple((0, 1, 2) for _ in range(6)),
        0,
    )
    machine = make_development_positive_machine(0)
    discovery = discover_field_substrate(machine)
    with pytest.raises(NativeProgramError, match="state count exceeds"):
        synthesize_native_mealy(source, discovery, machine)
