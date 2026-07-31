from __future__ import annotations

import inspect

from metamorphosis.m012b_dfa import exact_equivalence, random_minimal_dfa
from metamorphosis.m013e_engine import UnknownSubstrateMigrator
from metamorphosis.m013e_lab import (
    make_development_negative_machine,
    make_development_positive_machine,
)
from metamorphosis.m013e_runtime import OpaqueNativeBody, discover_substrate, opaque_body_to_dfa


def test_discovers_stable_truth_tables_on_development_machine() -> None:
    machine = make_development_positive_machine(0)
    discovered = discover_substrate(machine)
    assert discovered.probe_calls <= 120
    assert not discovered.unstable_opcodes
    hidden = machine._audit_snapshot()
    for opcode in discovered.opcodes:
        assert opcode.stable
        assert opcode.table == tuple(hidden[opcode.opcode]["table"])


def test_migrates_inherited_passport_to_three_unknown_development_families() -> None:
    passport = random_minimal_dfa(21_001)
    migrator = UnknownSubstrateMigrator()
    for family in range(3):
        machine = make_development_positive_machine(family)
        certificate = migrator.migrate(passport, machine, 24_001 + family)
        assert certificate.status == "success", (family, certificate.reason)
        assert certificate.body is not None
        assert certificate.probe_calls <= 120
        candidate = opaque_body_to_dfa(certificate.body, machine)
        assert exact_equivalence(passport, candidate)[0]


def test_opaque_body_round_trip_contains_no_semantic_tables() -> None:
    passport = random_minimal_dfa(21_002)
    machine = make_development_positive_machine(1)
    certificate = UnknownSubstrateMigrator().migrate(passport, machine, 24_010)
    assert certificate.body is not None
    raw = certificate.body.to_json()
    restored = OpaqueNativeBody.from_json(raw)
    assert restored == certificate.body
    assert '"table"' not in raw
    for forbidden in ('"and"', '"or"', '"not"', '"nand"', '"nor"'):
        assert forbidden not in raw.lower()
    assert exact_equivalence(passport, opaque_body_to_dfa(restored, machine))[0]


def test_all_development_negative_families_abstain() -> None:
    passport = random_minimal_dfa(21_003)
    migrator = UnknownSubstrateMigrator()
    for kind in range(3):
        certificate = migrator.migrate(
            passport,
            make_development_negative_machine(kind),
            24_020 + kind,
        )
        assert certificate.status == "abstained", (kind, certificate.reason)
        assert certificate.body is None


def test_detects_unstable_development_operations() -> None:
    for kind in (1, 2):
        machine = make_development_negative_machine(kind)
        discovered = discover_substrate(machine)
        assert discovered.unstable_opcodes
        assert all(not opcode.stable for opcode in discovered.opcodes if opcode.opcode in discovered.unstable_opcodes)


def test_migration_interface_has_no_task_oracle_parameter() -> None:
    parameters = inspect.signature(UnknownSubstrateMigrator.migrate).parameters
    assert "oracle" not in parameters
    assert "task_oracle" not in parameters
    assert set(parameters) >= {"self", "passport", "machine", "search_seed"}
