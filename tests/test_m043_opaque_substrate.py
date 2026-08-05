from __future__ import annotations

import inspect

import pytest

from metamorphosis.m043_opaque_substrate import (
    DiscoveredFieldSubstrate,
    OpcodeDescriptor,
    SubstrateError,
    discover_field_substrate,
    make_development_negative_machine,
    make_development_positive_machine,
)


def test_public_descriptors_do_not_expose_semantic_roles() -> None:
    descriptors = make_development_positive_machine(0).describe()
    assert descriptors
    assert all(isinstance(item, OpcodeDescriptor) for item in descriptors)
    assert all(not hasattr(item, "role") for item in descriptors)


@pytest.mark.parametrize("family", range(3))
def test_public_probes_recover_complete_field_basis(family: int) -> None:
    machine = make_development_positive_machine(family)
    discovery = discover_field_substrate(machine)
    assert isinstance(discovery, DiscoveredFieldSubstrate)
    assert set(dict(discovery.role_opcodes)) == {"add", "mul", "neg"}
    assert discovery.probe_calls <= discovery.probe_budget
    assert all(discovery.descriptor(opcode).stable for _, opcode in discovery.role_opcodes)


def test_opaque_opcode_assignments_differ_across_positive_families() -> None:
    assignments = {
        discover_field_substrate(make_development_positive_machine(index)).role_opcodes
        for index in range(3)
    }
    assert len(assignments) == 3


def test_discovery_is_deterministic_on_fresh_equal_machines() -> None:
    first = discover_field_substrate(make_development_positive_machine(1))
    second = discover_field_substrate(make_development_positive_machine(1))
    assert first == second
    assert first.digest() == second.digest()


def test_discovery_source_never_uses_evaluator_audit_methods() -> None:
    source = inspect.getsource(discover_field_substrate)
    assert "_audit_role" not in source
    assert "_audit_snapshot" not in source


@pytest.mark.parametrize("kind", range(3))
def test_incomplete_or_unstable_substrates_fail_closed(kind: int) -> None:
    with pytest.raises(SubstrateError):
        discover_field_substrate(make_development_negative_machine(kind))


def test_probe_budget_exhaustion_terminates_explicitly() -> None:
    with pytest.raises(SubstrateError, match="probe budget exhausted"):
        discover_field_substrate(
            make_development_positive_machine(0), probe_budget=8
        )


@pytest.mark.parametrize("repetitions", [0, 1, 2, True])
def test_discovery_rejects_insufficient_repetitions(repetitions: int) -> None:
    with pytest.raises(SubstrateError):
        discover_field_substrate(
            make_development_positive_machine(0), repetitions=repetitions
        )


@pytest.mark.parametrize("budget", [0, -1, True])
def test_discovery_rejects_invalid_probe_budgets(budget: int) -> None:
    with pytest.raises(SubstrateError):
        discover_field_substrate(
            make_development_positive_machine(0), probe_budget=budget
        )
