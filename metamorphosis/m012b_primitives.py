from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .m012b_dfa import TruthTable

@dataclass(frozen=True)
class Primitive:
    primitive_id: str
    arity: int
    table: TruthTable
    cost: int = 1

    def __post_init__(self) -> None:
        if self.arity not in (1, 2):
            raise ValueError("only unary and binary primitives are supported")
        if len(self.table) != 2**self.arity or any(value not in (0, 1) for value in self.table):
            raise ValueError("invalid truth table")
        if self.cost <= 0:
            raise ValueError("primitive cost must be positive")

    def apply(self, inputs: Sequence[int]) -> int:
        if len(inputs) != self.arity or any(value not in (0, 1) for value in inputs):
            raise ValueError("invalid primitive inputs")
        index = inputs[0] if self.arity == 1 else inputs[0] * 2 + inputs[1]
        return self.table[index]


@dataclass(frozen=True)
class PrimitiveCatalog:
    catalog_id: str
    primitives: tuple[Primitive, ...]

    def __post_init__(self) -> None:
        ids = [primitive.primitive_id for primitive in self.primitives]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("catalogue must contain unique primitives")

    def primitive_map(self) -> dict[str, Primitive]:
        return {primitive.primitive_id: primitive for primitive in self.primitives}

    def to_dict(self) -> dict[str, object]:
        return {
            "catalog_id": self.catalog_id,
            "primitives": [
                {
                    "primitive_id": primitive.primitive_id,
                    "arity": primitive.arity,
                    "table": list(primitive.table),
                    "cost": primitive.cost,
                }
                for primitive in self.primitives
            ],
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "PrimitiveCatalog":
        return PrimitiveCatalog(
            catalog_id=str(data["catalog_id"]),
            primitives=tuple(
                Primitive(
                    primitive_id=str(item["primitive_id"]),
                    arity=int(item["arity"]),
                    table=tuple(int(value) for value in item["table"]),
                    cost=int(item["cost"]),
                )
                for item in data["primitives"]  # type: ignore[index]
            ),
        )


def evaluation_catalogs() -> tuple[PrimitiveCatalog, ...]:
    return (
        PrimitiveCatalog(
            "register_logic",
            (
                Primitive("u_inv", 1, (1, 0), 1),
                Primitive("b_conj", 2, (0, 0, 0, 1), 1),
                Primitive("b_disj", 2, (0, 1, 1, 1), 1),
                Primitive("b_parity", 2, (0, 1, 1, 0), 2),
            ),
        ),
        PrimitiveCatalog(
            "nand_fabric",
            (
                Primitive("cell_n", 2, (1, 1, 1, 0), 1),
                Primitive("wire_a", 2, (0, 0, 1, 1), 1),
            ),
        ),
        PrimitiveCatalog(
            "nor_fabric",
            (
                Primitive("cell_r", 2, (1, 0, 0, 0), 1),
                Primitive("wire_b", 2, (0, 1, 0, 1), 1),
            ),
        ),
    )


def insufficient_catalog() -> PrimitiveCatalog:
    return PrimitiveCatalog(
        "monotone_incomplete",
        (
            Primitive("meet", 2, (0, 0, 0, 1), 1),
            Primitive("join", 2, (0, 1, 1, 1), 1),
        ),
    )
