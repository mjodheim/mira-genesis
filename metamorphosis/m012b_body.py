from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable, Sequence

from .m012b_dfa import DFA, canonicalize, minimize_dfa
from .m012b_basis import GenericBasisSynthesizer, LogicBasis
from .m012b_expr import Expr
from .m012b_primitives import PrimitiveCatalog

@dataclass(frozen=True)
class NativeBody:
    catalog: PrimitiveCatalog
    state_width: int
    next_state: tuple[Expr, ...]
    output: Expr
    initial_state: tuple[int, ...]
    initial_output: int

    def step(self, state: Sequence[int], symbol: int) -> tuple[tuple[int, ...], int]:
        frozen = tuple(int(bool(value)) for value in state)
        next_state = tuple(
            expression.evaluate(self.catalog, frozen, symbol) for expression in self.next_state
        )
        output = self.output.evaluate(self.catalog, frozen, symbol)
        return next_state, output

    def accepts(self, word: Iterable[int]) -> bool:
        state = self.initial_state
        output = self.initial_output
        for symbol in word:
            state, output = self.step(state, int(symbol))
        return bool(output)

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m012b-native-body/1",
                "catalog": self.catalog.to_dict(),
                "state_width": self.state_width,
                "next_state": [expression.to_dict() for expression in self.next_state],
                "output": self.output.to_dict(),
                "initial_state": list(self.initial_state),
                "initial_output": self.initial_output,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "NativeBody":
        data = json.loads(raw)
        if data.get("version") != "m012b-native-body/1":
            raise ValueError("unsupported body version")
        return NativeBody(
            catalog=PrimitiveCatalog.from_dict(data["catalog"]),
            state_width=int(data["state_width"]),
            next_state=tuple(Expr.from_dict(item) for item in data["next_state"]),
            output=Expr.from_dict(data["output"]),
            initial_state=tuple(int(value) for value in data["initial_state"]),
            initial_output=int(data["initial_output"]),
        )


def _and(parts: Sequence[Expr], basis: LogicBasis) -> Expr:
    if not parts:
        return Expr.constant(1)
    expression = parts[0]
    for part in parts[1:]:
        expression = basis.conjunction.instantiate((expression, part))
    return expression


def _or(parts: Sequence[Expr], basis: LogicBasis) -> Expr:
    if not parts:
        return Expr.constant(0)
    expression = parts[0]
    for part in parts[1:]:
        expression = basis.disjunction.instantiate((expression, part))
    return expression


def _transition_term(state: int, symbol: int, basis: LogicBasis) -> Expr:
    state_source = Expr.state(state)
    symbol_source = Expr.symbol() if symbol else basis.negate.instantiate((Expr.symbol(),))
    return basis.conjunction.instantiate((state_source, symbol_source))


def synthesize_native_body(dfa: DFA, catalog: PrimitiveCatalog, seed: int, candidate_budget: int) -> tuple[NativeBody | None, int, str]:
    basis_search = GenericBasisSynthesizer(catalog, candidate_budget, seed)
    basis = basis_search.synthesize()
    if basis is None:
        return None, basis_search.evaluations, "insufficient_functional_basis"

    dfa = canonicalize(minimize_dfa(dfa))
    transition_terms: dict[tuple[int, int], Expr] = {
        (state, symbol): _transition_term(state, symbol, basis)
        for state in range(dfa.n_states)
        for symbol in (0, 1)
    }
    next_expressions: list[Expr] = []
    for target in range(dfa.n_states):
        terms = [
            transition_terms[(state, symbol)]
            for state in range(dfa.n_states)
            for symbol in (0, 1)
            if dfa.transitions[state][symbol] == target
        ]
        next_expressions.append(_or(terms, basis))

    output_terms = [
        transition_terms[(state, symbol)]
        for state in range(dfa.n_states)
        for symbol in (0, 1)
        if dfa.accepting[dfa.transitions[state][symbol]]
    ]
    initial_state = tuple(int(index == dfa.initial) for index in range(dfa.n_states))
    body = NativeBody(
        catalog=catalog,
        state_width=dfa.n_states,
        next_state=tuple(next_expressions),
        output=_or(output_terms, basis),
        initial_state=initial_state,
        initial_output=int(dfa.accepting[dfa.initial]),
    )
    construction_cost = basis.candidate_evaluations + len(transition_terms) + len(output_terms)
    return body, construction_cost, "native_body_constructed"


def native_body_to_dfa(body: NativeBody) -> DFA:
    width = body.state_width
    if len(body.initial_state) != width or sum(body.initial_state) != 1:
        raise ValueError("body initial state is not one-hot")
    initial = body.initial_state.index(1)
    accepting: list[bool | None] = [None] * width
    accepting[initial] = bool(body.initial_output)
    transitions: list[tuple[int, int]] = []
    for state_index in range(width):
        state = tuple(int(index == state_index) for index in range(width))
        row: list[int] = []
        for symbol in (0, 1):
            nxt, output = body.step(state, symbol)
            if len(nxt) != width or any(bit not in (0, 1) for bit in nxt) or sum(nxt) != 1:
                raise ValueError("body left one-hot state manifold")
            target = nxt.index(1)
            row.append(target)
            if accepting[target] is not None and accepting[target] != bool(output):
                raise ValueError("inconsistent body output")
            accepting[target] = bool(output)
        transitions.append((row[0], row[1]))
    return canonicalize(
        DFA(
            (0, 1),
            tuple(transitions),
            tuple(bool(value) if value is not None else False for value in accepting),
            initial,
        )
    )


def unique_component_count(body: NativeBody) -> int:
    seen: set[str] = set()

    def visit(expression: Expr) -> None:
        key = json.dumps(expression.to_dict(), sort_keys=True, separators=(",", ":"))
        if key in seen:
            return
        seen.add(key)
        for argument in expression.args:
            visit(argument)

    for expression in (*body.next_state, body.output):
        visit(expression)
    return len(seen) + body.state_width
