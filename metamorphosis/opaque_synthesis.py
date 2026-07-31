from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import random
from typing import Sequence

from .morphogenesis import Expr
from .opaque_runtime import DiscoveredSubstrate, OpaqueExpr, TruthTable

Signature = tuple[int, ...]


@dataclass(frozen=True)
class LogicBasis:
    not_expr: OpaqueExpr
    and_expr: OpaqueExpr
    or_expr: OpaqueExpr
    candidate_evaluations: int


class OpaqueBasisSynthesizer:
    """Find canonical Boolean roles using only inferred truth tables."""

    def __init__(self, substrate: DiscoveredSubstrate, candidate_budget: int, seed: int) -> None:
        self.substrate = substrate
        self.candidate_budget = candidate_budget
        self.rng = random.Random(seed)
        self.evaluations = 0

    @staticmethod
    def _apply(table: TruthTable, inputs: Sequence[Signature]) -> Signature:
        if len(inputs) == 1:
            return tuple(table[x] for x in inputs[0])
        return tuple(table[a * 2 + b] for a, b in zip(inputs[0], inputs[1]))

    def _find(self, n_inputs: int, target: Signature) -> OpaqueExpr | None:
        rows = list(product((0, 1), repeat=n_inputs))
        library: dict[Signature, tuple[int, OpaqueExpr]] = {}

        def offer(signature: Signature, cost: int, expr: OpaqueExpr) -> bool:
            old = library.get(signature)
            if old is None or cost < old[0]:
                library[signature] = (cost, expr)
                return True
            return False

        offer(tuple(0 for _ in rows), 1, OpaqueExpr.const(0))
        offer(tuple(1 for _ in rows), 1, OpaqueExpr.const(1))
        for index in range(n_inputs):
            offer(tuple(row[index] for row in rows), 1, OpaqueExpr.argument(index))
        if target in library:
            return library[target][1]

        operations = list(self.substrate.stable_opcodes)
        self.rng.shuffle(operations)
        changed = True
        while changed and self.evaluations < self.candidate_budget:
            changed = False
            snapshot = sorted(library.items(), key=lambda item: (item[1][0], item[0]))
            for operation in operations:
                assert operation.table is not None
                if operation.arity == 1:
                    for signature, (cost, expr) in snapshot:
                        self.evaluations += 1
                        if self.evaluations > self.candidate_budget:
                            return None
                        changed |= offer(
                            self._apply(operation.table, (signature,)),
                            cost + operation.cost,
                            OpaqueExpr.call(operation.opcode, (expr,)),
                        )
                        if target in library:
                            return library[target][1]
                else:
                    pairs = [(left, right) for left in snapshot for right in snapshot]
                    self.rng.shuffle(pairs)
                    for (left_sig, (left_cost, left_expr)), (right_sig, (right_cost, right_expr)) in pairs:
                        self.evaluations += 1
                        if self.evaluations > self.candidate_budget:
                            return None
                        changed |= offer(
                            self._apply(operation.table, (left_sig, right_sig)),
                            left_cost + right_cost + operation.cost,
                            OpaqueExpr.call(operation.opcode, (left_expr, right_expr)),
                        )
                        if target in library:
                            return library[target][1]
        return library.get(target, (0, None))[1]

    def synthesize(self) -> LogicBasis | None:
        not_expr = self._find(1, (1, 0))
        if not_expr is None:
            return None
        and_expr = self._find(2, (0, 0, 0, 1))
        if and_expr is None:
            return None
        or_expr = self._find(2, (0, 1, 1, 1))
        if or_expr is None:
            return None
        return LogicBasis(not_expr, and_expr, or_expr, self.evaluations)


def translate_abstract_expr(expr: Expr, basis: LogicBasis) -> OpaqueExpr:
    if expr.op == "input":
        return OpaqueExpr.input()
    if expr.op == "state":
        if expr.index is None:
            raise ValueError("missing state index")
        return OpaqueExpr.state(expr.index)
    if expr.op == "const":
        return OpaqueExpr.const(int(bool(expr.value)))
    if expr.op == "not":
        return basis.not_expr.instantiate((translate_abstract_expr(expr.args[0], basis),))
    if expr.op == "and":
        return basis.and_expr.instantiate(tuple(translate_abstract_expr(arg, basis) for arg in expr.args))
    if expr.op == "or":
        return basis.or_expr.instantiate(tuple(translate_abstract_expr(arg, basis) for arg in expr.args))
    raise ValueError(f"unsupported abstract operation for M013: {expr.op}")
