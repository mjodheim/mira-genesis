from __future__ import annotations

import random

from metamorphosis.core import exact_equivalence, random_minimal_dfa
from metamorphosis.opaque_machine_lab import make_negative_machine, make_positive_machine
from metamorphosis.unknown_substrate import (
    OpaqueNativeBody,
    UnknownSubstrateMigrator,
    discover_substrate,
    fixed_role_baseline,
    opaque_body_to_dfa,
)


def test_discovers_exact_stable_truth_tables_without_semantic_names():
    machine = make_positive_machine(13011)
    discovered = discover_substrate(machine)
    assert discovered.probe_calls <= 120
    assert not discovered.unstable_opcodes
    hidden = machine._audit_snapshot()
    for opcode in discovered.opcodes:
        assert opcode.stable
        assert opcode.table == tuple(hidden[opcode.opcode]["table"])


def test_detects_unstable_indispensable_operations():
    machine = make_negative_machine(4)
    discovered = discover_substrate(machine)
    assert discovered.unstable_opcodes


def test_migrates_passport_to_each_unknown_machine():
    passport = random_minimal_dfa(random.Random(12011), 3, 8)
    for seed in (13011, 13023, 13037):
        machine = make_positive_machine(seed)
        cert = UnknownSubstrateMigrator().migrate(passport, machine, 17)
        assert cert.status == "success", (seed, cert.reason)
        assert cert.body is not None
        assert cert.probe_calls <= 120
        assert exact_equivalence(passport, opaque_body_to_dfa(cert.body, machine))[0]


def test_body_serialization_contains_only_opaque_ids():
    passport = random_minimal_dfa(random.Random(12023), 3, 8)
    machine = make_positive_machine(13023)
    cert = UnknownSubstrateMigrator().migrate(passport, machine, 31)
    assert cert.body is not None
    raw = cert.body.to_json()
    restored = OpaqueNativeBody.from_json(raw)
    assert restored == cert.body
    lowered = raw.lower()
    for forbidden in ('"and"', '"or"', '"not"', '"nand"', '"nor"'):
        assert forbidden not in lowered
    assert exact_equivalence(passport, opaque_body_to_dfa(restored, machine))[0]


def test_negative_machines_cause_abstention():
    passport = random_minimal_dfa(random.Random(12011), 3, 8)
    for index in range(12):
        cert = UnknownSubstrateMigrator().migrate(passport, make_negative_machine(index), 17)
        assert cert.status == "abstained"
        assert cert.body is None


def test_fixed_role_baseline_uses_no_probes():
    machine = make_positive_machine(13037)
    supplied = fixed_role_baseline(machine.describe())
    passport = random_minimal_dfa(random.Random(12037), 3, 8)
    cert = UnknownSubstrateMigrator().migrate(passport, machine, 17, supplied_substrate=supplied)
    assert cert.probe_calls == 0
