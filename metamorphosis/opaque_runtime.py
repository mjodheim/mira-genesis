from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from typing import Iterable, Mapping, Sequence

from .core import DFA, canonicalize
from .opaque_machine_lab import OpaqueBooleanMachine

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
        return tuple(op for op in self.opcodes if op.stable and op.table is not None)

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m013-discovered-substrate/1",
                "probe_calls": self.probe_calls,
                "unstable_opcodes": list(self.unstable_opcodes),
                "opcodes": [
                    {
                        "opcode": op.opcode,
                        "arity": op.arity,
                        "cost": op.cost,
                        "table": list(op.table) if op.table is not None else None,
                        "stable": op.stable,
                    }
                    for op in self.opcodes
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "DiscoveredSubstrate":
        data = json.loads(raw)
        if data.get("version") != "m013-discovered-substrate/1":
            raise ValueError("unsupported discovered substrate version")
        return DiscoveredSubstrate(
            opcodes=tuple(
                DiscoveredOpcode(
                    opcode=str(item["opcode"]),
                    arity=int(item["arity"]),
                    cost=int(item["cost"]),
                    table=tuple(int(x) for x in item["table"]) if item["table"] is not None else None,
                    stable=bool(item["stable"]),
                )
                for item in data["opcodes"]
            ),
            probe_calls=int(data["probe_calls"]),
            unstable_opcodes=tuple(str(x) for x in data["unstable_opcodes"]),
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
            if len(set(values)) != 1:
                stable = False
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


@dataclass(frozen=True)
class OpaqueExpr:
    kind: str
    args: tuple["OpaqueExpr", ...] = ()
    opcode: str | None = None
    index: int | None = None
    value: int | None = None

    @staticmethod
    def argument(index: int) -> "OpaqueExpr":
        return OpaqueExpr("arg", index=index)

    @staticmethod
    def input() -> "OpaqueExpr":
        return OpaqueExpr("input")

    @staticmethod
    def state(index: int) -> "OpaqueExpr":
        return OpaqueExpr("state", index=index)

    @staticmethod
    def const(value: int) -> "OpaqueExpr":
        return OpaqueExpr("const", value=int(bool(value)))

    @staticmethod
    def call(opcode: str, args: Sequence["OpaqueExpr"]) -> "OpaqueExpr":
        return OpaqueExpr("call", tuple(args), opcode=opcode)

    def evaluate(
        self,
        machine: OpaqueBooleanMachine,
        state: Sequence[int],
        symbol: int,
        arguments: Sequence[int] = (),
    ) -> int:
        if self.kind == "arg":
            if self.index is None or self.index >= len(arguments):
                raise ValueError("invalid template argument")
            return int(bool(arguments[self.index]))
        if self.kind == "input":
            return int(bool(symbol))
        if self.kind == "state":
            if self.index is None or self.index >= len(state):
                raise ValueError("invalid state source")
            return int(bool(state[self.index]))
        if self.kind == "const":
            return int(bool(self.value))
        if self.kind == "call":
            if self.opcode is None:
                raise ValueError("missing opcode")
            values = tuple(arg.evaluate(machine, state, symbol, arguments) for arg in self.args)
            return int(machine.execute(self.opcode, values))
        raise ValueError(f"unknown expression kind: {self.kind}")

    def instantiate(self, replacements: Sequence["OpaqueExpr"]) -> "OpaqueExpr":
        if self.kind == "arg":
            if self.index is None or self.index >= len(replacements):
                raise ValueError("invalid replacement index")
            return replacements[self.index]
        if not self.args:
            return self
        return OpaqueExpr(
            self.kind,
            tuple(arg.instantiate(replacements) for arg in self.args),
            self.opcode,
            self.index,
            self.value,
        )

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"kind": self.kind}
        if self.args:
            data["args"] = [arg.to_dict() for arg in self.args]
        if self.opcode is not None:
            data["opcode"] = self.opcode
        if self.index is not None:
            data["index"] = self.index
        if self.value is not None:
            data["value"] = self.value
        return data

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "OpaqueExpr":
        return OpaqueExpr(
            kind=str(data["kind"]),
            args=tuple(OpaqueExpr.from_dict(x) for x in data.get("args", [])),
            opcode=str(data["opcode"]) if "opcode" in data else None,
            index=int(data["index"]) if "index" in data else None,
            value=int(data["value"]) if "value" in data else None,
        )

    def used_opcodes(self) -> set[str]:
        found = {self.opcode} if self.kind == "call" and self.opcode is not None else set()
        for arg in self.args:
            found.update(arg.used_opcodes())
        return found


@dataclass(frozen=True)
class OpaqueNativeBody:
    state_width: int
    next_state_exprs: tuple[OpaqueExpr, ...]
    output_expr: OpaqueExpr
    initial_state: tuple[int, ...]
    initial_output: int

    def step(
        self,
        machine: OpaqueBooleanMachine,
        state: Sequence[int],
        symbol: int,
    ) -> tuple[tuple[int, ...], int]:
        frozen = tuple(int(bool(x)) for x in state)
        next_state = tuple(expr.evaluate(machine, frozen, symbol) for expr in self.next_state_exprs)
        output = self.output_expr.evaluate(machine, frozen, symbol)
        return next_state, output

    def accepts(self, machine: OpaqueBooleanMachine, word: Iterable[int]) -> bool:
        state = self.initial_state
        output = int(bool(self.initial_output))
        for symbol in word:
            state, output = self.step(machine, state, int(symbol))
        return bool(output)

    def used_opcodes(self) -> set[str]:
        found: set[str] = set()
        for expr in (*self.next_state_exprs, self.output_expr):
            found.update(expr.used_opcodes())
        return found

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m013-opaque-body/1",
                "state_width": self.state_width,
                "initial_state": list(self.initial_state),
                "initial_output": self.initial_output,
                "next_state": [expr.to_dict() for expr in self.next_state_exprs],
                "output": self.output_expr.to_dict(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "OpaqueNativeBody":
        data = json.loads(raw)
        if data.get("version") != "m013-opaque-body/1":
            raise ValueError("unsupported opaque body version")
        return OpaqueNativeBody(
            state_width=int(data["state_width"]),
            next_state_exprs=tuple(OpaqueExpr.from_dict(x) for x in data["next_state"]),
            output_expr=OpaqueExpr.from_dict(data["output"]),
            initial_state=tuple(int(x) for x in data["initial_state"]),
            initial_output=int(data["initial_output"]),
        )


def unique_component_count(body: OpaqueNativeBody) -> int:
    seen: set[str] = set()

    def visit(expr: OpaqueExpr) -> None:
        key = json.dumps(expr.to_dict(), sort_keys=True, separators=(",", ":"))
        if key in seen:
            return
        seen.add(key)
        for child in expr.args:
            visit(child)

    for expr in (*body.next_state_exprs, body.output_expr):
        visit(expr)
    return len(seen) + body.state_width


def opaque_body_to_dfa(body: OpaqueNativeBody, machine: OpaqueBooleanMachine) -> DFA:
    n = body.state_width
    if len(body.initial_state) != n or sum(body.initial_state) != 1:
        raise ValueError("opaque body initial state is not one-hot")
    initial = body.initial_state.index(1)
    accepting: list[bool | None] = [None] * n
    accepting[initial] = bool(body.initial_output)
    transitions: list[tuple[int, int]] = []
    for state_index in range(n):
        state = tuple(int(i == state_index) for i in range(n))
        row: list[int] = []
        for symbol in (0, 1):
            nxt, output = body.step(machine, state, symbol)
            if len(nxt) != n or any(bit not in (0, 1) for bit in nxt) or sum(nxt) != 1:
                raise ValueError("opaque body left one-hot state manifold")
            target = nxt.index(1)
            row.append(target)
            old = accepting[target]
            if old is not None and old != bool(output):
                raise ValueError("inconsistent output assigned to opaque state")
            accepting[target] = bool(output)
        transitions.append(tuple(row))
    return canonicalize(
        DFA(
            (0, 1),
            tuple(transitions),
            tuple(bool(value) if value is not None else False for value in accepting),
            initial,
        )
    )
