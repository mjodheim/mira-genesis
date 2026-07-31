from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Iterable, Mapping, Sequence

Signature = tuple[int, ...]


@dataclass(frozen=True)
class PrimitiveCatalog:
    """Declarative primitive catalogue used by the generic synthesizer.

    The catalogue contains names and costs only. It does not contain a target
    transition system, a task identifier, or a substrate-specific compiler.
    """

    name: str
    unary_ops: tuple[str, ...]
    binary_ops: tuple[str, ...]
    costs: Mapping[str, int]
    max_expression_cost: int = 8

    def validate(self) -> None:
        supported_unary = {"not"}
        supported_binary = {"and", "or", "xor", "nand", "nor"}
        unknown = (set(self.unary_ops) - supported_unary) | (
            set(self.binary_ops) - supported_binary
        )
        if unknown:
            raise ValueError(f"Unsupported catalogue primitives: {sorted(unknown)}")
        for op in (*self.unary_ops, *self.binary_ops):
            if self.costs.get(op, 0) <= 0:
                raise ValueError(f"Missing positive cost for primitive {op!r}")
        if self.max_expression_cost < 1:
            raise ValueError("max_expression_cost must be positive")


REGISTER_CATALOG = PrimitiveCatalog(
    name="register_machine",
    unary_ops=("not",),
    binary_ops=("and", "or", "xor"),
    costs={"input": 1, "state": 1, "const": 1, "not": 1, "and": 2, "or": 2, "xor": 2},
    max_expression_cost=8,
)

GATE_GRAPH_CATALOG = PrimitiveCatalog(
    name="typed_gate_graph",
    unary_ops=("not",),
    binary_ops=("and", "or", "xor", "nand", "nor"),
    costs={
        "input": 1,
        "state": 1,
        "const": 1,
        "not": 1,
        "and": 1,
        "or": 1,
        "xor": 2,
        "nand": 1,
        "nor": 1,
    },
    max_expression_cost=8,
)

QUANTIZED_RECURRENT_CATALOG = PrimitiveCatalog(
    name="quantized_recurrent_network",
    unary_ops=("not",),
    binary_ops=("and", "or", "nand", "nor"),
    costs={"input": 1, "state": 1, "const": 1, "not": 1, "and": 1, "or": 1, "nand": 2, "nor": 2},
    max_expression_cost=8,
)


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple["Expr", ...] = ()
    index: int | None = None
    value: int | None = None

    @staticmethod
    def input() -> "Expr":
        return Expr("input")

    @staticmethod
    def state(index: int) -> "Expr":
        return Expr("state", index=index)

    @staticmethod
    def const(value: int) -> "Expr":
        if value not in (0, 1):
            raise ValueError("Boolean constant must be 0 or 1")
        return Expr("const", value=value)

    def evaluate(self, state: Sequence[int], symbol: int) -> int:
        if self.op == "input":
            return int(bool(symbol))
        if self.op == "state":
            if self.index is None or self.index >= len(state):
                raise ValueError("Invalid state variable")
            return int(bool(state[self.index]))
        if self.op == "const":
            return int(bool(self.value))
        if self.op == "not":
            return 1 - self.args[0].evaluate(state, symbol)
        left = self.args[0].evaluate(state, symbol)
        right = self.args[1].evaluate(state, symbol)
        if self.op == "and":
            return left & right
        if self.op == "or":
            return left | right
        if self.op == "xor":
            return left ^ right
        if self.op == "nand":
            return 1 - (left & right)
        if self.op == "nor":
            return 1 - (left | right)
        raise ValueError(f"Unknown expression op: {self.op}")

    def to_dict(self) -> dict:
        data: dict[str, object] = {"op": self.op}
        if self.args:
            data["args"] = [arg.to_dict() for arg in self.args]
        if self.index is not None:
            data["index"] = self.index
        if self.value is not None:
            data["value"] = self.value
        return data

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "Expr":
        return Expr(
            op=str(data["op"]),
            args=tuple(Expr.from_dict(arg) for arg in data.get("args", [])),
            index=int(data["index"]) if "index" in data else None,
            value=int(data["value"]) if "value" in data else None,
        )


@dataclass(frozen=True)
class TransitionConstraint:
    state: tuple[int, ...]
    symbol: int
    next_state: tuple[int, ...]
    output: int

    def validate(self, width: int) -> None:
        if len(self.state) != width or len(self.next_state) != width:
            raise ValueError("Constraint state width mismatch")
        if self.symbol not in (0, 1) or self.output not in (0, 1):
            raise ValueError("Constraints are binary")
        if any(bit not in (0, 1) for bit in (*self.state, *self.next_state)):
            raise ValueError("State vectors must be binary")


@dataclass(frozen=True)
class NativeBody:
    catalog_name: str
    state_width: int
    next_state_exprs: tuple[Expr, ...]
    output_expr: Expr
    initial_state: tuple[int, ...]

    def step(self, state: Sequence[int], symbol: int) -> tuple[tuple[int, ...], int]:
        frozen = tuple(int(bool(x)) for x in state)
        next_state = tuple(expr.evaluate(frozen, symbol) for expr in self.next_state_exprs)
        output = self.output_expr.evaluate(frozen, symbol)
        return next_state, output

    def run(self, word: Iterable[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
        state = self.initial_state
        outputs: list[int] = []
        for symbol in word:
            state, output = self.step(state, int(symbol))
            outputs.append(output)
        return state, tuple(outputs)

    def satisfies(self, constraints: Iterable[TransitionConstraint]) -> bool:
        return all(self.step(c.state, c.symbol) == (c.next_state, c.output) for c in constraints)

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m012-native-body/1",
                "catalog": self.catalog_name,
                "state_width": self.state_width,
                "initial_state": list(self.initial_state),
                "next_state": [expr.to_dict() for expr in self.next_state_exprs],
                "output": self.output_expr.to_dict(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "NativeBody":
        data = json.loads(raw)
        if data.get("version") != "m012-native-body/1":
            raise ValueError("Unsupported body version")
        return NativeBody(
            catalog_name=str(data["catalog"]),
            state_width=int(data["state_width"]),
            initial_state=tuple(int(x) for x in data["initial_state"]),
            next_state_exprs=tuple(Expr.from_dict(x) for x in data["next_state"]),
            output_expr=Expr.from_dict(data["output"]),
        )


@dataclass(frozen=True)
class SynthesisResult:
    body: NativeBody | None
    expressions_considered: int
    signatures_discovered: int
    reason: str


class GenericMorphogenesisEngine:
    """One catalogue-driven synthesizer for every declared substrate.

    This first implementation solves finite transition constraints. Active
    behavioural-state discovery is deliberately left for the next increment.
    """

    def __init__(self, catalog: PrimitiveCatalog) -> None:
        catalog.validate()
        self.catalog = catalog

    @staticmethod
    def _apply_unary(op: str, values: Signature) -> Signature:
        if op == "not":
            return tuple(1 - x for x in values)
        raise ValueError(op)

    @staticmethod
    def _apply_binary(op: str, left: Signature, right: Signature) -> Signature:
        if op == "and":
            return tuple(a & b for a, b in zip(left, right))
        if op == "or":
            return tuple(a | b for a, b in zip(left, right))
        if op == "xor":
            return tuple(a ^ b for a, b in zip(left, right))
        if op == "nand":
            return tuple(1 - (a & b) for a, b in zip(left, right))
        if op == "nor":
            return tuple(1 - (a | b) for a, b in zip(left, right))
        raise ValueError(op)

    def _expression_library(
        self, constraints: Sequence[TransitionConstraint], state_width: int
    ) -> tuple[dict[Signature, tuple[int, Expr]], int]:
        library: dict[Signature, tuple[int, Expr]] = {}
        considered = 0

        def offer(signature: Signature, cost: int, expr: Expr) -> bool:
            nonlocal considered
            considered += 1
            old = library.get(signature)
            if cost > self.catalog.max_expression_cost:
                return False
            if old is None or cost < old[0]:
                library[signature] = (cost, expr)
                return True
            return False

        rows = [(c.state, c.symbol) for c in constraints]
        offer(tuple(0 for _ in rows), self.catalog.costs["const"], Expr.const(0))
        offer(tuple(1 for _ in rows), self.catalog.costs["const"], Expr.const(1))
        offer(tuple(symbol for _, symbol in rows), self.catalog.costs["input"], Expr.input())
        for index in range(state_width):
            offer(
                tuple(state[index] for state, _ in rows),
                self.catalog.costs["state"],
                Expr.state(index),
            )

        changed = True
        while changed:
            changed = False
            snapshot = list(library.items())
            for signature, (cost, expr) in snapshot:
                for op in self.catalog.unary_ops:
                    changed |= offer(
                        self._apply_unary(op, signature),
                        cost + self.catalog.costs[op],
                        Expr(op, (expr,)),
                    )
            snapshot = list(library.items())
            for (left_sig, (left_cost, left_expr)), (right_sig, (right_cost, right_expr)) in product(snapshot, repeat=2):
                for op in self.catalog.binary_ops:
                    changed |= offer(
                        self._apply_binary(op, left_sig, right_sig),
                        left_cost + right_cost + self.catalog.costs[op],
                        Expr(op, (left_expr, right_expr)),
                    )
        return library, considered

    def synthesize(
        self,
        constraints: Sequence[TransitionConstraint],
        state_width: int,
        initial_state: Sequence[int] | None = None,
    ) -> SynthesisResult:
        if not constraints:
            return SynthesisResult(None, 0, 0, "no_constraints")
        if state_width < 1:
            raise ValueError("state_width must be positive")
        for constraint in constraints:
            constraint.validate(state_width)

        initial = tuple(initial_state or (0,) * state_width)
        if len(initial) != state_width or any(bit not in (0, 1) for bit in initial):
            raise ValueError("Invalid initial state")

        library, considered = self._expression_library(constraints, state_width)
        targets = [tuple(c.next_state[bit] for c in constraints) for bit in range(state_width)]
        output_target = tuple(c.output for c in constraints)

        if any(target not in library for target in (*targets, output_target)):
            return SynthesisResult(None, considered, len(library), "unexpressible_under_catalog")

        body = NativeBody(
            catalog_name=self.catalog.name,
            state_width=state_width,
            next_state_exprs=tuple(library[target][1] for target in targets),
            output_expr=library[output_target][1],
            initial_state=initial,
        )
        if not body.satisfies(constraints):
            raise AssertionError("Synthesized body failed its own constraints")
        return SynthesisResult(body, considered, len(library), "exact")
