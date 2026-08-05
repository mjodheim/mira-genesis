from __future__ import annotations

from dataclasses import replace
import json

import pytest

from metamorphosis.m043_adoption import initial_lineage
from metamorphosis.m043_mealy import MealyMachine
from metamorphosis.m043_migration import (
    MigrationError,
    NativeMigrationBundle,
    audit_native_migration_bundle,
    build_native_migration_bundle,
    run_q5_development_qualification,
)
from metamorphosis.m043_native_program import NativeProgramError
from metamorphosis.m043_opaque_substrate import (
    discover_field_substrate,
    make_development_positive_machine,
)


@pytest.fixture(scope="module")
def source_machine() -> MealyMachine:
    return MealyMachine(
        input_alphabet=(0, 1, 2),
        output_alphabet=(0, 1, 2),
        transitions=((1, 0, 2), (1, 2, 0), (2, 0, 1)),
        outputs=((0, 1, 2), (2, 0, 1), (1, 2, 0)),
        initial=0,
    )


@pytest.fixture(scope="module")
def migration_case(source_machine: MealyMachine):
    source = initial_lineage(source_machine)
    machine = make_development_positive_machine(0)
    discovery = discover_field_substrate(machine)
    bundle = build_native_migration_bundle(source, machine, discovery)
    return source, machine, discovery, bundle


def test_bundle_binds_all_source_lineage_components(migration_case) -> None:
    source, _, _, bundle = migration_case
    assert bundle.source_snapshot_digest == source.digest()
    assert bundle.source_version == source.version
    assert bundle.source_body_digest == bundle.synthesis_certificate.source_body_digest
    assert bundle.source_tool_registry_digest
    assert bundle.source_learning_state_digest
    assert bundle.source_journal_digest


def test_bundle_round_trip_and_audit(migration_case) -> None:
    source, machine, discovery, bundle = migration_case
    restored = NativeMigrationBundle.from_bytes(bundle.to_bytes())
    assert restored == bundle
    assert restored.digest() == bundle.digest()
    audit_native_migration_bundle(restored, source, machine, discovery)


def test_bundle_parser_rejects_extra_fields(migration_case) -> None:
    _, _, _, bundle = migration_case
    raw = bundle.to_dict()
    raw["source_transition_table"] = [[0]]
    with pytest.raises(MigrationError):
        NativeMigrationBundle.from_bytes(json.dumps(raw))


def test_bundle_rejects_wrong_source_lineage(migration_case, source_machine) -> None:
    _, machine, discovery, bundle = migration_case
    other_body = replace(source_machine, initial=1)
    other = initial_lineage(other_body)
    with pytest.raises(MigrationError, match="snapshot_digest mismatch"):
        audit_native_migration_bundle(bundle, other, machine, discovery)


def test_bundle_rejects_tampered_program_binding(migration_case) -> None:
    _, _, _, bundle = migration_case
    program = replace(bundle.native_program, discovery_digest="0" * 64)
    with pytest.raises((MigrationError, NativeProgramError)):
        replace(bundle, native_program=program)


def test_bundle_rejects_tampered_certificate(migration_case) -> None:
    _, _, _, bundle = migration_case
    certificate = replace(
        bundle.synthesis_certificate,
        native_program_digest="0" * 64,
    )
    with pytest.raises(MigrationError, match="another native program"):
        replace(bundle, synthesis_certificate=certificate)


def test_audit_recomputes_certificate_metadata(migration_case) -> None:
    source, machine, discovery, bundle = migration_case
    certificate = replace(
        bundle.synthesis_certificate,
        source_behaviour_digest="0" * 64,
    )
    tampered = replace(bundle, synthesis_certificate=certificate)
    with pytest.raises(MigrationError, match="failed recomputation"):
        audit_native_migration_bundle(tampered, source, machine, discovery)


def test_q5_development_qualification_is_complete() -> None:
    result = run_q5_development_qualification()
    assert result["status"] == "qualified"
    assert result["source_version"] == 1
    assert result["source_tool_registry_entries"] == 1
    assert result["source_journal_entries"] == 1
    assert result["source_learning_state_preserved"]
    assert len(result["positive_substrates"]) == 3
    assert all(item["exact"] for item in result["positive_substrates"])
    assert all(item["table_free"] for item in result["positive_substrates"])
    assert result["distinct_machine_identities"]
    assert result["distinct_opaque_role_assignments"]
    assert result["public_probe_discovery_only"]
    assert all(result["negative_substrates_rejected"].values())
    assert result["probe_budget_exhaustion_rejected"]
    assert result["wrong_source_lineage_rejected"]
    assert result["tampered_program_binding_rejected"]
    assert result["direct_transition_table_smuggling_rejected"]
    assert not result["source_transition_output_tables_in_native_program"]
    assert result["selected_seed"] is None
    assert not result["hidden_task_bank_authorised"]
    assert not result["canonical_workflow_authorised"]
