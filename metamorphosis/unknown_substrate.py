from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
import random
import time
from typing import Iterable, Mapping, Sequence

from .core import DFA, canonicalize, minimize_dfa
from .morphogenesis import Expr, GenericCubeSynthesizer, REGISTER_CATALOG, one_hot_constraints
from .opaque_machine_lab import OpcodeDescriptor, OpaqueBooleanMachine

TruthTable = tuple[int, ...]
Signature = tuple[int, ...]


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
        return json.dumps({
            "version": "m013-discovered-substrate/1",
            "probe_calls": self.probe_calls,
            "unstable_opcodes": list(self.unstable_opcodes),
            "opcodes": [{"opcode": o.opcode, "arity": o.arity, "cost": o.cost,
                         "table": list(o.table) if o.table is not None else None,
                         "stable": o.stable} for o in self.opcodes],
        }, sort_keys=True, separators=(",", ":"))


def discover_substrate(machine: OpaqueBooleanMachine, repetitions: int = 3,
                       probe_budget: int = 120) -> DiscoveredSubstrate:
    calls = 0
    found: list[DiscoveredOpcode] = []
    unstable: list[str] = []
    for descriptor in machine.describe():
        table: list[int] = []
        stable = True
        for inputs in product((0, 1), repeat=descriptor.arity):
            values = []
            for _ in range(repetitions):
                if calls >= probe_budget:
                    raise RuntimeError("substrate_probe_budget_exhausted")
                values.append(int(machine.probe(descriptor.opcode, inputs)))
                calls += 1
            stable &= len(set(values)) == 1
            table.append(values[0])
        if not stable:
            unstable.append(descriptor.opcode)
        found.append(DiscoveredOpcode(descriptor.opcode, descriptor.arity,
                                      descriptor.cost, tuple(table) if stable else None, stable))
    return DiscoveredSubstrate(tuple(found), calls, tuple(sorted(unstable)))


@dataclass(frozen=True)
class OpaqueExpr:
    kind: str
    args: tuple["OpaqueExpr", ...] = ()
    opcode: str | None = None
    index: int | None = None
    value: int | None = None

    @staticmethod
    def argument(index: int) -> "OpaqueExpr": return OpaqueExpr("arg", index=index)
    @staticmethod
    def input() -> "OpaqueExpr": return OpaqueExpr("input")
    @staticmethod
    def state(index: int) -> "OpaqueExpr": return OpaqueExpr("state", index=index)
    @staticmethod
    def const(value: int) -> "OpaqueExpr": return OpaqueExpr("const", value=int(bool(value)))
    @staticmethod
    def call(opcode: str, args: Sequence["OpaqueExpr"]) -> "OpaqueExpr":
        return OpaqueExpr("call", tuple(args), opcode=opcode)

    def evaluate(self, machine: OpaqueBooleanMachine, state: Sequence[int], symbol: int,
                 arguments: Sequence[int] = ()) -> int:
        if self.kind == "arg": return int(bool(arguments[self.index or 0]))
        if self.kind == "input": return int(bool(symbol))
        if self.kind == "state": return int(bool(state[self.index or 0]))
        if self.kind == "const": return int(bool(self.value))
        values = tuple(arg.evaluate(machine, state, symbol, arguments) for arg in self.args)
        return int(machine.execute(self.opcode or "", values))

    def instantiate(self, replacements: Sequence["OpaqueExpr"]) -> "OpaqueExpr":
        if self.kind == "arg": return replacements[self.index or 0]
        if not self.args: return self
        return OpaqueExpr(self.kind, tuple(a.instantiate(replacements) for a in self.args),
                          self.opcode, self.index, self.value)

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"kind": self.kind}
        if self.args: data["args"] = [a.to_dict() for a in self.args]
        if self.opcode is not None: data["opcode"] = self.opcode
        if self.index is not None: data["index"] = self.index
        if self.value is not None: data["value"] = self.value
        return data

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "OpaqueExpr":
        return OpaqueExpr(str(data["kind"]), tuple(OpaqueExpr.from_dict(x) for x in data.get("args", [])),
                          str(data["opcode"]) if "opcode" in data else None,
                          int(data["index"]) if "index" in data else None,
                          int(data["value"]) if "value" in data else None)

    def used_opcodes(self) -> set[str]:
        out = {self.opcode} if self.kind == "call" and self.opcode else set()
        for arg in self.args: out.update(arg.used_opcodes())
        return out


@dataclass(frozen=True)
class OpaqueNativeBody:
    state_width: int
    next_state_exprs: tuple[OpaqueExpr, ...]
    output_expr: OpaqueExpr
    initial_state: tuple[int, ...]
    initial_output: int

    def step(self, machine: OpaqueBooleanMachine, state: Sequence[int], symbol: int):
        frozen = tuple(int(bool(x)) for x in state)
        return (tuple(e.evaluate(machine, frozen, symbol) for e in self.next_state_exprs),
                self.output_expr.evaluate(machine, frozen, symbol))

    def accepts(self, machine: OpaqueBooleanMachine, word: Iterable[int]) -> bool:
        state, output = self.initial_state, self.initial_output
        for symbol in word: state, output = self.step(machine, state, int(symbol))
        return bool(output)

    def used_opcodes(self) -> set[str]:
        out: set[str] = set()
        for expr in (*self.next_state_exprs, self.output_expr): out.update(expr.used_opcodes())
        return out

    def to_json(self) -> str:
        return json.dumps({"version":"m013-opaque-body/1","state_width":self.state_width,
                           "initial_state":list(self.initial_state),"initial_output":self.initial_output,
                           "next_state":[e.to_dict() for e in self.next_state_exprs],
                           "output":self.output_expr.to_dict()}, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def from_json(raw: str) -> "OpaqueNativeBody":
        d = json.loads(raw)
        if d.get("version") != "m013-opaque-body/1": raise ValueError("unsupported body version")
        return OpaqueNativeBody(int(d["state_width"]), tuple(OpaqueExpr.from_dict(x) for x in d["next_state"]),
                                OpaqueExpr.from_dict(d["output"]), tuple(int(x) for x in d["initial_state"]),
                                int(d["initial_output"]))


@dataclass(frozen=True)
class LogicBasis:
    not_expr: OpaqueExpr
    and_expr: OpaqueExpr
    or_expr: OpaqueExpr
    candidate_evaluations: int


class OpaqueBasisSynthesizer:
    def __init__(self, substrate: DiscoveredSubstrate, candidate_budget: int, seed: int) -> None:
        self.substrate, self.candidate_budget = substrate, candidate_budget
        self.rng, self.evaluations = random.Random(seed), 0

    @staticmethod
    def _apply(table: TruthTable, inputs: Sequence[Signature]) -> Signature:
        if len(inputs) == 1: return tuple(table[x] for x in inputs[0])
        return tuple(table[a * 2 + b] for a, b in zip(inputs[0], inputs[1]))

    def _find(self, n_inputs: int, target: Signature) -> OpaqueExpr | None:
        rows = list(product((0, 1), repeat=n_inputs))
        library: dict[Signature, tuple[int, OpaqueExpr]] = {}
        def offer(sig: Signature, cost: int, expr: OpaqueExpr) -> bool:
            old = library.get(sig)
            if old is None or cost < old[0]: library[sig] = (cost, expr); return True
            return False
        offer(tuple(0 for _ in rows), 1, OpaqueExpr.const(0)); offer(tuple(1 for _ in rows), 1, OpaqueExpr.const(1))
        for i in range(n_inputs): offer(tuple(row[i] for row in rows), 1, OpaqueExpr.argument(i))
        operations = list(self.substrate.stable_opcodes); self.rng.shuffle(operations)
        changed = True
        while changed and self.evaluations < self.candidate_budget:
            changed = False; snapshot = sorted(library.items(), key=lambda x: (x[1][0], x[0]))
            for op in operations:
                assert op.table is not None
                if op.arity == 1:
                    candidates = [((sig,), cost, (expr,)) for sig, (cost, expr) in snapshot]
                else:
                    candidates = [((ls, rs), lc + rc, (le, re)) for ls,(lc,le) in snapshot for rs,(rc,re) in snapshot]
                    self.rng.shuffle(candidates)
                for signatures, cost, expressions in candidates:
                    self.evaluations += 1
                    if self.evaluations > self.candidate_budget: return None
                    changed |= offer(self._apply(op.table, signatures), cost + op.cost,
                                     OpaqueExpr.call(op.opcode, expressions))
                    if target in library: return library[target][1]
        return library.get(target, (0, None))[1]

    def synthesize(self) -> LogicBasis | None:
        n = self._find(1, (1,0)); a = self._find(2, (0,0,0,1)); o = self._find(2, (0,1,1,1))
        return LogicBasis(n,a,o,self.evaluations) if n and a and o else None


def translate(expr: Expr, basis: LogicBasis) -> OpaqueExpr:
    if expr.op == "input": return OpaqueExpr.input()
    if expr.op == "state": return OpaqueExpr.state(expr.index or 0)
    if expr.op == "const": return OpaqueExpr.const(int(bool(expr.value)))
    if expr.op == "not": return basis.not_expr.instantiate((translate(expr.args[0], basis),))
    if expr.op == "and": return basis.and_expr.instantiate(tuple(translate(x,basis) for x in expr.args))
    if expr.op == "or": return basis.or_expr.instantiate(tuple(translate(x,basis) for x in expr.args))
    raise ValueError(f"unsupported abstract operation: {expr.op}")


@dataclass(frozen=True)
class MigrationCertificate:
    status: str
    reason: str
    body: OpaqueNativeBody | None
    substrate: DiscoveredSubstrate
    probe_calls: int
    candidate_evaluations: int
    native_components: int
    serialized_bytes: int
    elapsed_seconds: float
    used_opcodes: tuple[str, ...]
    trace: Mapping[str, object]


class UnknownSubstrateMigrator:
    def __init__(self, candidate_budget: int = 75000, cpu_seconds: float = 120.0,
                 native_component_budget: int = 320, serialized_byte_budget: int = 16777216) -> None:
        self.candidate_budget, self.cpu_seconds = candidate_budget, cpu_seconds
        self.native_component_budget, self.serialized_byte_budget = native_component_budget, serialized_byte_budget

    def migrate(self, passport: DFA, machine: OpaqueBooleanMachine, search_seed: int,
                trace: Mapping[str, object] | None = None,
                supplied_substrate: DiscoveredSubstrate | None = None) -> MigrationCertificate:
        started = time.perf_counter()
        try: substrate = supplied_substrate or discover_substrate(machine)
        except RuntimeError as exc:
            empty = DiscoveredSubstrate((),120,())
            return MigrationCertificate("abstained",str(exc),None,empty,120,0,0,0,time.perf_counter()-started,(),dict(trace or {}))
        basis_search = OpaqueBasisSynthesizer(substrate,self.candidate_budget,search_seed); basis = basis_search.synthesize()
        if basis is None:
            return MigrationCertificate("abstained","insufficient_or_unstable_functional_basis",None,substrate,
                                        substrate.probe_calls,basis_search.evaluations,0,0,time.perf_counter()-started,(),dict(trace or {}))
        constraints, initial, initial_output = one_hot_constraints(canonicalize(minimize_dfa(passport)))
        abstract, stats, reason = GenericCubeSynthesizer(REGISTER_CATALOG, heritage=None,
            candidate_budget=max(1,self.candidate_budget-basis_search.evaluations), seed=search_seed).synthesize(constraints,initial,initial_output)
        total = basis_search.evaluations + stats.candidate_evaluations
        if abstract is None:
            return MigrationCertificate("abstained",reason,None,substrate,substrate.probe_calls,total,0,0,time.perf_counter()-started,(),dict(trace or {}))
        body = OpaqueNativeBody(abstract.state_width, tuple(translate(e,basis) for e in abstract.next_state_exprs),
                                translate(abstract.output_expr,basis), abstract.initial_state, abstract.initial_output)
        raw = body.to_json().encode(); components = len({json.dumps(e.to_dict(),sort_keys=True) for e in (*body.next_state_exprs,body.output_expr)}) + body.state_width
        elapsed = time.perf_counter()-started
        if total>self.candidate_budget or components>self.native_component_budget or len(raw)>self.serialized_byte_budget or elapsed>self.cpu_seconds:
            return MigrationCertificate("failed","resource_budget_exceeded",None,substrate,substrate.probe_calls,total,components,len(raw),elapsed,tuple(sorted(body.used_opcodes())),dict(trace or {}))
        return MigrationCertificate("success","native_body_constructed",body,substrate,substrate.probe_calls,total,components,len(raw),elapsed,tuple(sorted(body.used_opcodes())),dict(trace or {}))


def opaque_body_to_dfa(body: OpaqueNativeBody, machine: OpaqueBooleanMachine) -> DFA:
    n=body.state_width; initial=body.initial_state.index(1); accepting: list[bool|None]=[None]*n; accepting[initial]=bool(body.initial_output); transitions=[]
    for i in range(n):
        state=tuple(int(j==i) for j in range(n)); row=[]
        for symbol in (0,1):
            nxt,out=body.step(machine,state,symbol)
            if len(nxt)!=n or sum(nxt)!=1: raise ValueError("body left one-hot manifold")
            target=nxt.index(1); row.append(target)
            if accepting[target] is not None and accepting[target]!=bool(out): raise ValueError("inconsistent output")
            accepting[target]=bool(out)
        transitions.append(tuple(row))
    return canonicalize(DFA((0,1),tuple(transitions),tuple(bool(x) if x is not None else False for x in accepting),initial))


def fixed_role_baseline(descriptors: Sequence[OpcodeDescriptor]) -> DiscoveredSubstrate:
    unary=[(1,0),(0,1),(0,0),(1,1)]; binary=[(0,0,0,1),(0,1,1,1),(0,1,1,0),(1,1,1,0),(1,0,0,0),(0,0,1,1),(0,1,0,1)]
    ui=bi=0; ops=[]
    for d in sorted(descriptors,key=lambda x:x.opcode):
        if d.arity==1: table=unary[ui%len(unary)]; ui+=1
        else: table=binary[bi%len(binary)]; bi+=1
        ops.append(DiscoveredOpcode(d.opcode,d.arity,d.cost,table,True))
    return DiscoveredSubstrate(tuple(ops),0,())


def random_semantics_baseline(descriptors: Sequence[OpcodeDescriptor], seed: int) -> DiscoveredSubstrate:
    rng=random.Random(seed)
    return DiscoveredSubstrate(tuple(DiscoveredOpcode(d.opcode,d.arity,d.cost,tuple(rng.randrange(2) for _ in range(2**d.arity)),True)
        for d in sorted(descriptors,key=lambda x:x.opcode)),0,())
