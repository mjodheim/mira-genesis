from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .m012b_primitives import PrimitiveCatalog

@dataclass(frozen=True)
class Expr:
    kind: str
    args: tuple["Expr", ...] = ()
    primitive_id: str | None = None
    index: int | None = None
    value: int | None = None

    @staticmethod
    def argument(index: int) -> "Expr":
        return Expr("argument", index=index)

    @staticmethod
    def state(index: int) -> "Expr":
        return Expr("state", index=index)

    @staticmethod
    def symbol() -> "Expr":
        return Expr("symbol")

    @staticmethod
    def constant(value: int) -> "Expr":
        return Expr("constant", value=int(bool(value)))

    @staticmethod
    def call(primitive_id: str, args: Sequence["Expr"]) -> "Expr":
        return Expr("call", tuple(args), primitive_id=primitive_id)

    def instantiate(self, replacements: Sequence["Expr"]) -> "Expr":
        if self.kind == "argument":
            if self.index is None or self.index >= len(replacements):
                raise ValueError("invalid template argument")
            return replacements[self.index]
        if not self.args:
            return self
        return Expr(
            self.kind,
            tuple(argument.instantiate(replacements) for argument in self.args),
            self.primitive_id,
            self.index,
            self.value,
        )

    def evaluate(
        self,
        catalog: PrimitiveCatalog,
        state: Sequence[int],
        symbol: int,
        arguments: Sequence[int] = (),
    ) -> int:
        if self.kind == "argument":
            if self.index is None or self.index >= len(arguments):
                raise ValueError("invalid argument")
            return int(bool(arguments[self.index]))
        if self.kind == "state":
            if self.index is None or self.index >= len(state):
                raise ValueError("invalid state source")
            return int(bool(state[self.index]))
        if self.kind == "symbol":
            return int(bool(symbol))
        if self.kind == "constant":
            return int(bool(self.value))
        if self.kind == "call":
            if self.primitive_id is None:
                raise ValueError("missing primitive")
            primitive = catalog.primitive_map()[self.primitive_id]
            values = tuple(
                argument.evaluate(catalog, state, symbol, arguments) for argument in self.args
            )
            return primitive.apply(values)
        raise ValueError(f"unknown expression kind: {self.kind}")

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"kind": self.kind}
        if self.args:
            data["args"] = [argument.to_dict() for argument in self.args]
        if self.primitive_id is not None:
            data["primitive_id"] = self.primitive_id
        if self.index is not None:
            data["index"] = self.index
        if self.value is not None:
            data["value"] = self.value
        return data

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "Expr":
        return Expr(
            kind=str(data["kind"]),
            args=tuple(Expr.from_dict(item) for item in data.get("args", [])),
            primitive_id=str(data["primitive_id"]) if "primitive_id" in data else None,
            index=int(data["index"]) if "index" in data else None,
            value=int(data["value"]) if "value" in data else None,
        )
