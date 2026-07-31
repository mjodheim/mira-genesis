from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Iterable, Mapping, Sequence

from .m012b_dfa import DFA, canonicalize
from .m012b_expr import Expr
from .m012b_primitives import Primitive, PrimitiveCatalog
from .m013e_lab import OpaqueBooleanMachine

TruthTable = tuple[int, ...]


@dataclass(frozen=True)
class DiscoveredOpcode:
    opcode: str
    arity: int
    cost: int
    table: TruthTable | None
    stable: bool


@dataclass(frozen=True)
class DiscoveredSubstrate:
    opcodes: tuple[DiscoveredOpcode, ...]
    probe_calls: int
    unstable_opcodes: tuple[str, ...]

    @property
    def stable_opcodes(self) -> tuple[DiscoveredOpcode, ...]:
        return tuple(opcode for opcode in self.opcodes if opcode.stable and opcode.table is not None)

    def catalog(self) -> PrimitiveCatalog:
        return PrimitiveCatalog(
            "opaque_discovered",
            tuple(
                Primitive(opcode.opcode, opcode.arity, opcode.table, opcode.cost)
                for opcode in self.stable_opcodes
                if opcode.table is not None
            ),
        )


def discover_substrate(
    machine: OpaqueBooleanMachine,
    repetitions: int = 3,
    probe_budget: int = 120,
) -> DiscoveredSubstrate:
    if repetitions < 2:
        raise ValueError("at least two repetitions are required")
    calls = 0
    discovered: list[DiscoveredOpcode] = []
    unstable: list[str] = []
    for descriptor in machine.describe():
        table: list[int] = []
        stable = True
        for inputs in product((0, 1), repeat=descriptor.arity):
            values: list[int] = []
            for _ in range(repetitions):
                if calls >= probe_budget:
                    raise RuntimeError("substrate_probe_budget_exhausted")
                values.append(int(machine.probe(descriptor.opcode, inputs)))
                calls += 1
            stable &= len(set(values)) == 1
            table.append(values[0])
        if not stable:
            unstable.append(descriptor.opcode)
        discovered.append(
            DiscoveredOpcode(
                descriptor.opcode,
                descriptor.arity,
                descriptor.cost,
                tuple(table) if stable else None,
                stable,
            )
        )
    return DiscoveredSubstrate(tuple(discovered), calls, tuple(sorted(unstable)))


def _evaluate_expr(
    expression: Expr,
    machine: OpaqueBooleanMachine,
    state: Sequence[int],
    symbol: int,
    arguments: Sequence[int] = (),
) -> int:
    if expression.kind == "argument":
        if expression.index is None or expression.index >= len(arguments):
            raise ValueError("invalid argument")
        return int(bool(arguments[expression.index]))
    if expression.kind == "state":
        if expression.index is None or expression.index >= len(state):
            raise ValueError("invalid state source")
        return int(bool(state[expression.index]))
    if expression.kind == "symbol":
        return int(bool(symbol))
    if expression.kind == "constant":
        return int(bool(expression.value))
    if expression.kind == "call":
        if expression.primitive_id is None:
            raise ValueError("missing opcode")
        values = tuple(
            _evaluate_expr(argument, machine, state, symbol, arguments)
            for argument in expression.args
        )
        return int(machine.execute(expression.primitive_id, values))
    raise ValueError(f"unknown expression kind: {expression.kind}")


@dataclass(frozen=True)
class OpaqueNativeBody:
    state_width: int
    next_state: tuple[Expr, ...]
    output: Expr
    initial_state: tuple[int, ...]
    initial_output: int

    def step(
        self,
        machine: OpaqueBooleanMachine,
        state: Sequence[int],
        symbol: int,
    ) -> tuple[tuple[int, ...], int]:
        frozen = tuple(int(bool(value)) for value in state)
        nxt = tuple(_evaluate_expr(expr, machine, frozen, symbol) for expr in self.next_state)
        output = _evaluate_expr(self.output, machine, frozen, symbol)
        return nxt, output

    def accepts(self, machine: OpaqueBooleanMachine, word: Iterable[int]) -> bool:
        state = self.initial_state
        output = self.initial_output
        for symbol in word:
            state, output = self.step(machine, state, int(symbol))
        return bool(output)

    def used_opcodes(self) -> set[str]:
        found: set[str] = set()

        def visit(expression: Expr) -> None:
            if expression.kind == "call" and expression.primitive_id is not None:
                found.add(expression.primitive_id)
            for argument in expression.args:
                visit(argument)

        for expression in (*self.next_state, self.output):
            visit(expression)
        return found

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m013e-opaque-body/1",
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
    def from_json(raw: str) -> "OpaqueNativeBody":
        data = json.loads(raw)
        if data.get("version") != "m013e-opaque-body/1":
            raise ValueError("unsupported opaque body version")
        return OpaqueNativeBody(
            state_width=int(data["state_width"]),
            next_state=tuple(Expr.from_dict(item) for item in data["next_state"]),
            output=Expr.from_dict(data["output"]),
            initial_state=tuple(int(value) for value in data["initial_state"]),
            initial_output=int(data["initial_output"]),
        )


def opaque_body_to_dfa(body: OpaqueNativeBody, machine: OpaqueBooleanMachine) -> DFA:
    width = body.state_width
    if len(body.initial_state) != width or sum(body.initial_state) != 1:
        raise ValueError("opaque body initial state is not one-hot")
    initial = body.initial_state.index(1)
    accepting: list[bool | None] = [None] * width
    accepting[initial] = bool(body.initial_output)
    transitions: list[tuple[int, int]] = []
    for state_index in range(width):
        state = tuple(int(index == state_index) for index in range(width))
        row: list[int] = []
        for symbol in (0, 1):
            nxt, output = body.step(machine, state, symbol)
            if len(nxt) != width or any(bit not in (0, 1) for bit in nxt) or sum(nxt) != 1:
                raise ValueError("opaque body left one-hot state manifold")
            target = nxt.index(1)
            row.append(target)
            if accepting[target] is not None and accepting[target] != bool(output):
                raise ValueError("inconsistent output for opaque state")
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


def unique_component_count(body: OpaqueNativeBody) -> int:
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
