from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Iterable

TruthTable = tuple[int, ...]


@dataclass(frozen=True)
class OpcodeDescriptor:
    opcode: str
    arity: int
    cost: int


@dataclass
class _HiddenOperation:
    arity: int
    table: TruthTable
    cost: int
    instability: str = "stable"
    calls: int = 0

    def apply(self, inputs: tuple[int, ...]) -> int:
        if len(inputs) != self.arity or any(bit not in (0, 1) for bit in inputs):
            raise ValueError("invalid opcode inputs")
        index = inputs[0] if self.arity == 1 else inputs[0] * 2 + inputs[1]
        value = self.table[index]
        self.calls += 1
        if self.instability == "alternate":
            return value if self.calls % 2 else 1 - value
        if self.instability == "periodic_three":
            return 1 - value if self.calls % 3 == 0 else value
        return value


class OpaqueBooleanMachine:
    """Lab-owned machine exposing structure and behavior, never semantics."""

    def __init__(self, machine_id: str, operations: dict[str, _HiddenOperation]) -> None:
        self.machine_id = machine_id
        self.__operations = operations

    def describe(self) -> tuple[OpcodeDescriptor, ...]:
        return tuple(
            OpcodeDescriptor(opcode, hidden.arity, hidden.cost)
            for opcode, hidden in sorted(self.__operations.items())
        )

    def probe(self, opcode: str, inputs: Iterable[int]) -> int:
        try:
            hidden = self.__operations[opcode]
        except KeyError as exc:
            raise ValueError("unknown opcode") from exc
        return hidden.apply(tuple(int(value) for value in inputs))

    def execute(self, opcode: str, inputs: Iterable[int]) -> int:
        return self.probe(opcode, inputs)

    # Evaluator-only methods. Public Genesis source is audited against these names.
    def _audit_truth_table(self, opcode: str) -> TruthTable:
        return self.__operations[opcode].table

    def _audit_stability(self, opcode: str) -> str:
        return self.__operations[opcode].instability

    def _audit_snapshot(self) -> dict[str, dict[str, object]]:
        return {
            opcode: {
                "arity": hidden.arity,
                "table": hidden.table,
                "cost": hidden.cost,
                "instability": hidden.instability,
            }
            for opcode, hidden in self.__operations.items()
        }


NOT = (1, 0)
IDENTITY = (0, 1)
CONST0_U = (0, 0)
CONST1_U = (1, 1)
AND = (0, 0, 0, 1)
OR = (0, 1, 1, 1)
XOR = (0, 1, 1, 0)
XNOR = (1, 0, 0, 1)
NAND = (1, 1, 1, 0)
NOR = (1, 0, 0, 0)
PROJ_A = (0, 0, 1, 1)
PROJ_B = (0, 1, 0, 1)
CONST0_B = (0, 0, 0, 0)
CONST1_B = (1, 1, 1, 1)
IMPLIES = (1, 1, 0, 1)
A_AND_NOT_B = (0, 0, 1, 0)

Spec = tuple[int, TruthTable, int, str]


def _opaque_ids(seed: int, count: int) -> list[str]:
    rng = random.Random(seed ^ 0x5A17_D013)
    identifiers: set[str] = set()
    while len(identifiers) < count:
        raw = f"{seed}:{rng.getrandbits(128)}".encode("utf-8")
        identifiers.add("op_" + hashlib.sha256(raw).hexdigest()[:12])
    return sorted(identifiers)


def _make_machine(seed: int, specs: list[Spec]) -> OpaqueBooleanMachine:
    identifiers = _opaque_ids(seed, len(specs))
    rng = random.Random(seed)
    rng.shuffle(identifiers)
    shuffled = list(specs)
    rng.shuffle(shuffled)
    operations = {
        opcode: _HiddenOperation(arity, table, cost, instability)
        for opcode, (arity, table, cost, instability) in zip(identifiers, shuffled)
    }
    machine_hash = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:12]
    return OpaqueBooleanMachine(f"opaque-{machine_hash}", operations)


def make_positive_machine(seed: int, family_index: int) -> OpaqueBooleanMachine:
    family = family_index % 3
    if family == 0:
        specs: list[Spec] = [
            (2, NAND, 1, "stable"),
            (2, XOR, 3, "stable"),
            (2, PROJ_A, 1, "stable"),
            (2, PROJ_B, 1, "stable"),
            (2, CONST0_B, 1, "stable"),
            (2, IMPLIES, 2, "stable"),
            (1, IDENTITY, 1, "stable"),
            (1, CONST1_U, 1, "stable"),
        ]
    elif family == 1:
        specs = [
            (2, NOR, 1, "stable"),
            (2, XNOR, 3, "stable"),
            (2, PROJ_A, 1, "stable"),
            (2, PROJ_B, 1, "stable"),
            (2, CONST1_B, 1, "stable"),
            (2, A_AND_NOT_B, 2, "stable"),
            (1, IDENTITY, 1, "stable"),
            (1, CONST0_U, 1, "stable"),
        ]
    else:
        specs = [
            (1, NOT, 1, "stable"),
            (1, IDENTITY, 1, "stable"),
            (2, AND, 1, "stable"),
            (2, OR, 1, "stable"),
            (2, XOR, 2, "stable"),
            (2, XNOR, 2, "stable"),
            (2, PROJ_A, 1, "stable"),
            (2, CONST0_B, 1, "stable"),
            (2, IMPLIES, 2, "stable"),
        ]
    return _make_machine(seed, specs)


def _negative_specs(kind: int) -> list[Spec]:
    category = kind % 3
    if category == 0:
        return [
            (1, IDENTITY, 1, "stable"),
            (1, CONST0_U, 1, "stable"),
            (1, CONST1_U, 1, "stable"),
            (2, AND, 1, "stable"),
            (2, OR, 1, "stable"),
            (2, PROJ_A, 1, "stable"),
            (2, PROJ_B, 1, "stable"),
            (2, CONST0_B, 1, "stable"),
        ]
    if category == 1:
        return [
            (2, NAND, 1, "alternate"),
            (1, IDENTITY, 1, "stable"),
            (1, CONST0_U, 1, "stable"),
            (2, PROJ_A, 1, "stable"),
            (2, PROJ_B, 1, "stable"),
            (2, CONST0_B, 1, "stable"),
        ]
    return [
        (2, NOR, 1, "periodic_three"),
        (1, NOT, 1, "periodic_three"),
        (1, IDENTITY, 1, "stable"),
        (2, PROJ_A, 1, "stable"),
        (2, PROJ_B, 1, "stable"),
        (2, CONST1_B, 1, "stable"),
    ]


def make_negative_machine(seed: int, kind: int) -> OpaqueBooleanMachine:
    return _make_machine(seed, _negative_specs(kind))


# Development-only factories use a disjoint fixed namespace.
def make_development_positive_machine(family_index: int) -> OpaqueBooleanMachine:
    return make_positive_machine(22_001 + family_index, family_index)


def make_development_negative_machine(kind: int) -> OpaqueBooleanMachine:
    return make_negative_machine(23_001 + kind, kind)
