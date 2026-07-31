from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import random
from typing import Sequence

from .m012b_dfa import Signature
from .m012b_expr import Expr
from .m012b_primitives import PrimitiveCatalog

@dataclass(frozen=True)
class LogicBasis:
    negate: Expr
    conjunction: Expr
    disjunction: Expr
    candidate_evaluations: int


class GenericBasisSynthesizer:
    """Identical search procedure for every declarative catalogue."""

    def __init__(self, catalog: PrimitiveCatalog, candidate_budget: int, seed: int) -> None:
        self.catalog = catalog
        self.candidate_budget = candidate_budget
        self.rng = random.Random(seed)
        self.evaluations = 0

    @staticmethod
    def _apply(table: TruthTable, inputs: Sequence[Signature]) -> Signature:
        if len(inputs) == 1:
            return tuple(table[value] for value in inputs[0])
        return tuple(table[left * 2 + right] for left, right in zip(inputs[0], inputs[1]))

    def _find(self, n_inputs: int, target: Signature) -> Expr | None:
        rows = list(product((0, 1), repeat=n_inputs))
        library: dict[Signature, tuple[int, Expr]] = {}

        def offer(signature: Signature, cost: int, expr: Expr) -> bool:
            current = library.get(signature)
            if current is None or cost < current[0]:
                library[signature] = (cost, expr)
                return True
            return False

        offer(tuple(0 for _ in rows), 1, Expr.constant(0))
        offer(tuple(1 for _ in rows), 1, Expr.constant(1))
        for index in range(n_inputs):
            offer(tuple(row[index] for row in rows), 1, Expr.argument(index))
        if target in library:
            return library[target][1]

        primitives = list(self.catalog.primitives)
        self.rng.shuffle(primitives)
        changed = True
        while changed and self.evaluations < self.candidate_budget:
            changed = False
            snapshot = sorted(library.items(), key=lambda item: (item[1][0], item[0]))
            for primitive in primitives:
                if primitive.arity == 1:
                    combinations = [((signature, cost, expr),) for signature, (cost, expr) in snapshot]
                else:
                    combinations = [
                        ((left_signature, left_cost, left_expr), (right_signature, right_cost, right_expr))
                        for left_signature, (left_cost, left_expr) in snapshot
                        for right_signature, (right_cost, right_expr) in snapshot
                    ]
                    self.rng.shuffle(combinations)
                for combination in combinations:
                    self.evaluations += 1
                    if self.evaluations > self.candidate_budget:
                        return None
                    signatures = tuple(item[0] for item in combination)
                    cost = sum(item[1] for item in combination) + primitive.cost
                    expr = Expr.call(primitive.primitive_id, tuple(item[2] for item in combination))
                    changed |= offer(self._apply(primitive.table, signatures), cost, expr)
                    if target in library:
                        return library[target][1]
        return library.get(target, (0, None))[1]

    def synthesize(self) -> LogicBasis | None:
        negate = self._find(1, (1, 0))
        if negate is None:
            return None
        conjunction = self._find(2, (0, 0, 0, 1))
        if conjunction is None:
            return None
        disjunction = self._find(2, (0, 1, 1, 1))
        if disjunction is None:
            return None
        return LogicBasis(negate, conjunction, disjunction, self.evaluations)
