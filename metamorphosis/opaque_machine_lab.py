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
    """Laboratory-owned machine exposing no semantic metadata."""

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
        return hidden.apply(tuple(int(x) for x in inputs))

    def execute(self, opcode: str, inputs: Iterable[int]) -> int:
        return self.probe(opcode, inputs)

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


def _opaque_ids(seed: int, count: int) -> list[str]:
    rng = random.Random(seed ^ 0xA5A5_13)
    ids: set[str] = set()
    while len(ids) < count:
        raw = f"{seed}:{rng.getrandbits(64)}".encode()
        ids.add("op_" + hashlib.sha256(raw).hexdigest()[:10])
    return list(ids)


def _make_machine(seed: int, specs: list[tuple[int, TruthTable, int, str]]) -> OpaqueBooleanMachine:
    ids = _opaque_ids(seed, len(specs))
    rng = random.Random(seed)
    rng.shuffle(ids)
    shuffled = list(specs)
    rng.shuffle(shuffled)
    operations = {
        opcode: _HiddenOperation(arity, table, cost, instability)
        for opcode, (arity, table, cost, instability) in zip(ids, shuffled)
    }
    return OpaqueBooleanMachine(f"opaque-{seed}", operations)


def make_positive_machine(seed: int) -> OpaqueBooleanMachine:
    families = {
        12911: "nand", 12923: "nor", 12937: "mixed",
        13011: "nand", 13023: "nor", 13037: "mixed",
        13411: "nand", 13423: "nor", 13437: "mixed",
        14411: "nand", 14423: "nor", 14437: "mixed",
    }
    family = families.get(seed)
    if family == "nand":
        specs = [
            (2, NAND, 1, "stable"), (2, XOR, 3, "stable"),
            (2, PROJ_A, 1, "stable"), (2, PROJ_B, 1, "stable"),
            (2, CONST0_B, 1, "stable"), (2, IMPLIES, 2, "stable"),
            (1, IDENTITY, 1, "stable"), (1, CONST1_U, 1, "stable"),
        ]
    elif family == "nor":
        specs = [
            (2, NOR, 1, "stable"), (2, XNOR, 3, "stable"),
            (2, PROJ_A, 1, "stable"), (2, PROJ_B, 1, "stable"),
            (2, CONST1_B, 1, "stable"), (2, A_AND_NOT_B, 2, "stable"),
            (1, IDENTITY, 1, "stable"), (1, CONST0_U, 1, "stable"),
        ]
    elif family == "mixed":
        specs = [
            (1, NOT, 1, "stable"), (1, IDENTITY, 1, "stable"),
            (2, AND, 1, "stable"), (2, OR, 1, "stable"),
            (2, XOR, 2, "stable"), (2, XNOR, 2, "stable"),
            (2, PROJ_A, 1, "stable"), (2, CONST0_B, 1, "stable"),
            (2, IMPLIES, 2, "stable"),
        ]
    else:
        raise ValueError("unknown positive machine seed")
    return _make_machine(seed, specs)


def _negative_specs(index: int) -> list[tuple[int, TruthTable, int, str]]:
    if not 0 <= index < 12:
        raise ValueError(index)
    if index < 4:
        return [
            (1, IDENTITY, 1, "stable"), (1, CONST0_U, 1, "stable"),
            (1, CONST1_U, 1, "stable"), (2, AND, 1, "stable"),
            (2, OR, 1, "stable"), (2, PROJ_A, 1, "stable"),
            (2, PROJ_B, 1, "stable"), (2, CONST0_B, 1, "stable"),
        ]
    if index < 8:
        return [
            (2, NAND, 1, "alternate"), (1, IDENTITY, 1, "stable"),
            (1, CONST0_U, 1, "stable"), (2, PROJ_A, 1, "stable"),
            (2, PROJ_B, 1, "stable"), (2, CONST0_B, 1, "stable"),
        ]
    return [
        (2, NOR, 1, "periodic_three"), (1, NOT, 1, "periodic_three"),
        (1, IDENTITY, 1, "stable"), (2, PROJ_A, 1, "stable"),
        (2, PROJ_B, 1, "stable"), (2, CONST1_B, 1, "stable"),
    ]


def make_development_negative_machine(index: int) -> OpaqueBooleanMachine:
    return _make_machine(12800 + index, _negative_specs(index))


def make_negative_machine(index: int) -> OpaqueBooleanMachine:
    return _make_machine(14500 + index, _negative_specs(index))
