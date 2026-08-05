"""Opaque finite-field substrate discovery for M043 qualification gate Q5.

Public callers can enumerate opcode descriptors and probe behaviour. Semantic roles remain
lab-owned until they are reconstructed from bounded repeated observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import hashlib
import json
import random
from typing import Iterable, Mapping


class SubstrateError(ValueError):
    """Raised when an opaque substrate or discovery record is invalid."""


@dataclass(frozen=True)
class OpcodeDescriptor:
    opcode: str
    arity: int
    cost: int


@dataclass
class _HiddenOperation:
    role: str
    arity: int
    cost: int
    instability: str = "stable"
    calls: int = 0

    def apply(self, modulus: int, inputs: tuple[int, ...]) -> int:
        if len(inputs) != self.arity or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value < modulus
            for value in inputs
        ):
            raise SubstrateError("invalid opaque opcode inputs")
        value = _role_value(self.role, modulus, inputs)
        self.calls += 1
        if self.instability == "alternate":
            return value if self.calls % 2 else (value + 1) % modulus
        if self.instability == "periodic_three":
            return (value + 1) % modulus if self.calls % 3 == 0 else value
        if self.instability != "stable":
            raise SubstrateError("unknown hidden instability mode")
        return value


def _role_value(role: str, modulus: int, inputs: tuple[int, ...]) -> int:
    if role == "add":
        return (inputs[0] + inputs[1]) % modulus
    if role == "mul":
        return (inputs[0] * inputs[1]) % modulus
    if role == "neg":
        return (-inputs[0]) % modulus
    if role == "sub":
        return (inputs[0] - inputs[1]) % modulus
    if role == "identity":
        return inputs[0]
    if role == "square":
        return (inputs[0] * inputs[0]) % modulus
    if role == "project_left":
        return inputs[0]
    if role == "project_right":
        return inputs[1]
    if role == "successor":
        return (inputs[0] + 1) % modulus
    if role == "constant_zero":
        return 0
    raise SubstrateError(f"unknown hidden opcode role: {role}")


class OpaqueFieldMachine:
    """Lab-owned field machine exposing only descriptors and observable behaviour."""

    __slots__ = ("machine_id", "modulus", "__operations")

    def __init__(
        self,
        machine_id: str,
        modulus: int,
        operations: Mapping[str, _HiddenOperation],
    ) -> None:
        if modulus != 5:
            raise SubstrateError("Q5 development substrate fixes the prime field of order 5")
        if not machine_id or not operations:
            raise SubstrateError("opaque machine requires an identity and operations")
        self.machine_id = machine_id
        self.modulus = modulus
        self.__operations = dict(operations)

    def describe(self) -> tuple[OpcodeDescriptor, ...]:
        return tuple(
            OpcodeDescriptor(opcode, hidden.arity, hidden.cost)
            for opcode, hidden in sorted(self.__operations.items())
        )

    def probe(self, opcode: str, inputs: Iterable[int]) -> int:
        try:
            hidden = self.__operations[opcode]
        except KeyError as exc:
            raise SubstrateError("unknown opaque opcode") from exc
        return hidden.apply(self.modulus, tuple(inputs))

    def execute(self, opcode: str, inputs: Iterable[int]) -> int:
        return self.probe(opcode, inputs)

    # Evaluator-only surfaces. Discovery code is permanently audited against these names.
    def _audit_role(self, opcode: str) -> str:
        return self.__operations[opcode].role

    def _audit_snapshot(self) -> dict[str, dict[str, object]]:
        return {
            opcode: {
                "role": hidden.role,
                "arity": hidden.arity,
                "cost": hidden.cost,
                "instability": hidden.instability,
            }
            for opcode, hidden in self.__operations.items()
        }


def _opaque_ids(seed: int, count: int) -> list[str]:
    rng = random.Random(seed ^ 0x43_05_A11C)
    identifiers: set[str] = set()
    while len(identifiers) < count:
        raw = f"{seed}:{rng.getrandbits(128)}".encode("ascii")
        identifiers.add("op_" + hashlib.sha256(raw).hexdigest()[:14])
    return sorted(identifiers)


def _make_machine(
    seed: int,
    specifications: list[tuple[str, int, int, str]],
) -> OpaqueFieldMachine:
    identifiers = _opaque_ids(seed, len(specifications))
    rng = random.Random(seed)
    rng.shuffle(identifiers)
    shuffled = list(specifications)
    rng.shuffle(shuffled)
    operations = {
        opcode: _HiddenOperation(role, arity, cost, instability)
        for opcode, (role, arity, cost, instability) in zip(identifiers, shuffled)
    }
    machine_hash = hashlib.sha256(f"m043-q5:{seed}".encode("ascii")).hexdigest()[:16]
    return OpaqueFieldMachine(f"opaque-field-{machine_hash}", 5, operations)


def make_development_positive_machine(family_index: int) -> OpaqueFieldMachine:
    family = family_index % 3
    common = [
        ("add", 2, 1, "stable"),
        ("mul", 2, 1, "stable"),
        ("neg", 1, 1, "stable"),
    ]
    if family == 0:
        extras = [
            ("sub", 2, 2, "stable"),
            ("identity", 1, 1, "stable"),
            ("project_left", 2, 1, "stable"),
            ("successor", 1, 2, "stable"),
        ]
    elif family == 1:
        extras = [
            ("square", 1, 2, "stable"),
            ("project_right", 2, 1, "stable"),
            ("constant_zero", 1, 1, "stable"),
            ("sub", 2, 3, "stable"),
        ]
    else:
        extras = [
            ("identity", 1, 2, "stable"),
            ("square", 1, 1, "stable"),
            ("project_left", 2, 2, "stable"),
            ("project_right", 2, 2, "stable"),
            ("successor", 1, 1, "stable"),
        ]
    return _make_machine(43_500 + family, common + extras)


def make_development_negative_machine(kind: int) -> OpaqueFieldMachine:
    category = kind % 3
    if category == 0:
        specs = [
            ("add", 2, 1, "stable"),
            ("neg", 1, 1, "stable"),
            ("sub", 2, 2, "stable"),
            ("identity", 1, 1, "stable"),
        ]
    elif category == 1:
        specs = [
            ("add", 2, 1, "alternate"),
            ("mul", 2, 1, "stable"),
            ("neg", 1, 1, "stable"),
            ("project_left", 2, 1, "stable"),
        ]
    else:
        specs = [
            ("add", 2, 1, "stable"),
            ("mul", 2, 1, "periodic_three"),
            ("neg", 1, 1, "stable"),
            ("project_right", 2, 1, "stable"),
        ]
    return _make_machine(43_600 + category, specs)


@dataclass(frozen=True)
class DiscoveredOpcode:
    opcode: str
    arity: int
    cost: int
    table: tuple[int, ...] | None
    stable: bool
    role: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "opcode": self.opcode,
            "arity": self.arity,
            "cost": self.cost,
            "table": None if self.table is None else list(self.table),
            "stable": self.stable,
            "role": self.role,
        }


@dataclass(frozen=True)
class DiscoveredFieldSubstrate:
    machine_id: str
    modulus: int
    opcodes: tuple[DiscoveredOpcode, ...]
    role_opcodes: tuple[tuple[str, str], ...]
    probe_calls: int
    probe_budget: int
    repetitions: int

    def __post_init__(self) -> None:
        if self.modulus != 5:
            raise SubstrateError("unsupported discovered field modulus")
        roles = dict(self.role_opcodes)
        if set(roles) != {"add", "mul", "neg"}:
            raise SubstrateError("discovery lacks the complete field basis")
        if len(set(roles.values())) != 3:
            raise SubstrateError("one opcode cannot fill multiple core field roles")
        if self.probe_calls > self.probe_budget:
            raise SubstrateError("discovery exceeded its probe budget")

    def opcode_for(self, role: str) -> str:
        try:
            return dict(self.role_opcodes)[role]
        except KeyError as exc:
            raise SubstrateError(f"undiscovered field role: {role}") from exc

    def descriptor(self, opcode: str) -> DiscoveredOpcode:
        for item in self.opcodes:
            if item.opcode == opcode:
                return item
        raise SubstrateError("unknown discovered opcode")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m043-q5-discovered-field-v1",
            "machine_id": self.machine_id,
            "modulus": self.modulus,
            "opcodes": [opcode.to_dict() for opcode in self.opcodes],
            "role_opcodes": [list(item) for item in self.role_opcodes],
            "probe_calls": self.probe_calls,
            "probe_budget": self.probe_budget,
            "repetitions": self.repetitions,
        }

    def digest(self) -> str:
        body = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        return hashlib.sha256(b"m043-q5-field-discovery-v1\x00" + body).hexdigest()


def _canonical_table(role: str, modulus: int, arity: int) -> tuple[int, ...]:
    return tuple(
        _role_value(role, modulus, inputs)
        for inputs in product(range(modulus), repeat=arity)
    )


def _classify_role(table: tuple[int, ...], modulus: int, arity: int) -> str | None:
    matches = [
        role
        for role, expected_arity in (("add", 2), ("mul", 2), ("neg", 1))
        if expected_arity == arity and table == _canonical_table(role, modulus, arity)
    ]
    if len(matches) > 1:
        raise SubstrateError("ambiguous core opcode semantics")
    return matches[0] if matches else None


def discover_field_substrate(
    machine: OpaqueFieldMachine,
    *,
    repetitions: int = 3,
    probe_budget: int = 512,
) -> DiscoveredFieldSubstrate:
    """Recover a stable field basis using public descriptors and repeated probes only."""

    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 3:
        raise SubstrateError("at least three repetitions are required")
    if isinstance(probe_budget, bool) or not isinstance(probe_budget, int) or probe_budget <= 0:
        raise SubstrateError("probe budget must be a positive integer")

    calls = 0
    discovered: list[DiscoveredOpcode] = []
    candidates: dict[str, list[DiscoveredOpcode]] = {"add": [], "mul": [], "neg": []}
    for descriptor in machine.describe():
        if descriptor.arity not in (1, 2) or descriptor.cost <= 0:
            raise SubstrateError("invalid public opcode descriptor")
        table: list[int] = []
        stable = True
        for inputs in product(range(machine.modulus), repeat=descriptor.arity):
            observed: list[int] = []
            for _ in range(repetitions):
                if calls >= probe_budget:
                    raise SubstrateError("substrate probe budget exhausted")
                observed.append(machine.probe(descriptor.opcode, inputs))
                calls += 1
            stable &= len(set(observed)) == 1
            table.append(observed[0])
        frozen = tuple(table) if stable else None
        role = None if frozen is None else _classify_role(
            frozen, machine.modulus, descriptor.arity
        )
        item = DiscoveredOpcode(
            descriptor.opcode,
            descriptor.arity,
            descriptor.cost,
            frozen,
            stable,
            role,
        )
        discovered.append(item)
        if role is not None:
            candidates[role].append(item)

    selected: list[tuple[str, str]] = []
    for role in ("add", "mul", "neg"):
        options = sorted(candidates[role], key=lambda item: (item.cost, item.opcode))
        if not options:
            raise SubstrateError(f"stable {role} opcode was not discovered")
        selected.append((role, options[0].opcode))

    return DiscoveredFieldSubstrate(
        machine_id=machine.machine_id,
        modulus=machine.modulus,
        opcodes=tuple(discovered),
        role_opcodes=tuple(selected),
        probe_calls=calls,
        probe_budget=probe_budget,
        repetitions=repetitions,
    )
