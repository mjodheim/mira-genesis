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
    initial_output: int = 0

    def step(self, state: Sequence[int], symbol: int) -> tuple[tuple[int, ...], int]:
        frozen = tuple(int(bool(x)) for x in state)
        next_state = tuple(expr.evaluate(frozen, symbol) for expr in self.next_state_exprs)
        output = self.output_expr.evaluate(frozen, symbol)
        return next_state, output

    def accepts(self, word: Iterable[int]) -> bool:
        state = self.initial_state
        output = int(bool(self.initial_output))
        for symbol in word:
            state, output = self.step(state, int(symbol))
        return bool(output)

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
                "initial_output": self.initial_output,
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
            initial_output=int(data.get("initial_output", 0)),
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
            offer(tuple(state[index] for state, _ in rows), self.catalog.costs["state"], Expr.state(index))

        changed = True
        while changed:
            changed = False
            snapshot = list(library.items())
            for signature, (cost, expr) in snapshot:
                for op in self.catalog.unary_ops:
                    changed |= offer(self._apply_unary(op, signature), cost + self.catalog.costs[op], Expr(op, (expr,)))
            snapshot = list(library.items())
            for (left_sig, (left_cost, left_expr)), (right_sig, (right_cost, right_expr)) in product(snapshot, repeat=2):
                for op in self.catalog.binary_ops:
                    changed |= offer(
                        self._apply_binary(op, left_sig, right_sig),
                        left_cost + right_cost + self.catalog.costs[op],
                        Expr(op, (left_expr, right_expr)),
                    )
        return library, considered

    def synthesize(self, constraints: Sequence[TransitionConstraint], state_width: int, initial_state: Sequence[int] | None = None) -> SynthesisResult:
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


# ---------------------------------------------------------------------------
# M012 increment 2: opaque-state discovery and generic partial-Boolean birth.
# ---------------------------------------------------------------------------

from dataclasses import field
import random
import time
from typing import Callable

from .core import DFA, LStarExtractor, MembershipOracle, canonicalize, minimize_dfa

Cube = tuple[int, ...]


@dataclass(frozen=True)
class CubeHeritage:
    """Inspectable construction motifs learned on development contracts."""

    templates: Mapping[int, tuple[Cube, ...]] = field(default_factory=dict)
    provenance: Mapping[str, object] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m012-cube-heritage/1",
                "templates": {str(k): [list(c) for c in v] for k, v in self.templates.items()},
                "provenance": dict(self.provenance),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "CubeHeritage":
        data = json.loads(raw)
        if data.get("version") != "m012-cube-heritage/1":
            raise ValueError("Unsupported heritage version")
        return CubeHeritage(
            templates={int(k): tuple(tuple(int(x) for x in c) for c in v) for k, v in data["templates"].items()},
            provenance=data.get("provenance", {}),
        )


@dataclass(frozen=True)
class BooleanSynthesisStats:
    candidate_evaluations: int
    cubes_selected: int
    expressions_built: int
    inherited_candidates_tested: int
    generic_candidates_tested: int


@dataclass(frozen=True)
class BirthCertificate:
    status: str
    reason: str
    body: NativeBody | None
    discovered_dfa: DFA | None
    behavioural_queries: int
    candidate_evaluations: int
    native_components: int
    serialized_bytes: int
    elapsed_seconds: float
    discovery_rounds: int
    counterexamples: int
    inheritance_used: bool
    trace: Mapping[str, object]


class InconsistentContractError(RuntimeError):
    pass


class OpaqueBehavioralContract:
    def __init__(self, fn: Callable[[tuple[int, ...]], bool], query_budget: int = 10_000) -> None:
        self._fn = fn
        self.query_budget = query_budget
        self.calls = 0
        self.observations: dict[tuple[int, ...], bool] = {}

    def query_uncached(self, word: tuple[int, ...]) -> bool:
        if self.calls >= self.query_budget:
            raise RuntimeError("behavioural_query_budget_exhausted")
        self.calls += 1
        return bool(self._fn(word))

    def query(self, word: tuple[int, ...]) -> bool:
        if word in self.observations:
            return self.observations[word]
        value = self.query_uncached(word)
        self.observations[word] = value
        return value

    def audit_consistency(self, probes: Sequence[tuple[int, ...]]) -> None:
        for word in probes:
            first = self.query_uncached(word)
            second = self.query_uncached(word)
            if first != second:
                raise InconsistentContractError(f"non_deterministic_contract_at:{word}")
            old = self.observations.get(word)
            if old is not None and old != first:
                raise InconsistentContractError(f"contract_changed_at:{word}")
            self.observations[word] = first


class BudgetedMembershipOracle(MembershipOracle):
    def __init__(self, contract: OpaqueBehavioralContract) -> None:
        self.contract = contract
        super().__init__(contract.query)


def one_hot_constraints(dfa: DFA) -> tuple[list[TransitionConstraint], tuple[int, ...], int]:
    dfa = canonicalize(minimize_dfa(dfa))
    n = dfa.n_states
    constraints: list[TransitionConstraint] = []
    for state in range(n):
        encoded = tuple(int(i == state) for i in range(n))
        for symbol in dfa.alphabet:
            target = dfa.transitions[state][symbol]
            nxt = tuple(int(i == target) for i in range(n))
            constraints.append(TransitionConstraint(encoded, int(symbol), nxt, int(dfa.accepting[target])))
    initial = tuple(int(i == dfa.initial) for i in range(n))
    return constraints, initial, int(dfa.accepting[dfa.initial])


def _cube_matches(cube: Cube, row: tuple[int, ...]) -> bool:
    return all(c == -1 or c == value for c, value in zip(cube, row))


def _cube_literals(cube: Cube) -> int:
    return sum(c != -1 for c in cube)


def _literal_expr(index: int, value: int, state_width: int) -> Expr:
    base = Expr.input() if index == state_width else Expr.state(index)
    return base if value else Expr("not", (base,))


def _and_expr(parts: Sequence[Expr]) -> Expr:
    if not parts:
        return Expr.const(1)
    out = parts[0]
    for part in parts[1:]:
        out = Expr("and", (out, part))
    return out


def _or_expr(parts: Sequence[Expr]) -> Expr:
    if not parts:
        return Expr.const(0)
    out = parts[0]
    for part in parts[1:]:
        out = Expr("or", (out, part))
    return out


def cube_to_expr(cube: Cube, state_width: int) -> Expr:
    return _and_expr([_literal_expr(i, value, state_width) for i, value in enumerate(cube) if value != -1])


def unique_component_count(body: NativeBody) -> int:
    seen: set[str] = set()
    def visit(expr: Expr) -> None:
        key = json.dumps(expr.to_dict(), sort_keys=True, separators=(",", ":"))
        if key in seen:
            return
        seen.add(key)
        for child in expr.args:
            visit(child)
    for expr in (*body.next_state_exprs, body.output_expr):
        visit(expr)
    return len(seen) + body.state_width


class GenericCubeSynthesizer:
    def __init__(self, catalog: PrimitiveCatalog, heritage: CubeHeritage | None = None, candidate_budget: int = 50_000, random_order: bool = False, seed: int = 0) -> None:
        catalog.validate()
        required = {"not", "and", "or"}
        if not required.issubset(set(catalog.unary_ops) | set(catalog.binary_ops)):
            raise ValueError("M012 cube synthesis requires generic NOT/AND/OR primitives")
        self.catalog = catalog
        self.heritage = heritage
        self.candidate_budget = candidate_budget
        self.random_order = random_order
        self.rng = random.Random(seed)
        self.evaluations = 0
        self.inherited_tested = 0
        self.generic_tested = 0

    def _all_cubes(self, n_vars: int) -> list[Cube]:
        cubes = [tuple(x) for x in product((-1, 0, 1), repeat=n_vars)]
        cubes.sort(key=lambda c: (_cube_literals(c), c))
        return cubes

    def _candidate_stream(self, n_vars: int) -> Iterable[tuple[Cube, bool]]:
        yielded: set[Cube] = set()
        if self.heritage is not None:
            for cube in self.heritage.templates.get(n_vars - 1, ()):
                if len(cube) == n_vars and cube not in yielded:
                    yielded.add(cube)
                    yield cube, True
        if self.random_order:
            while True:
                yield tuple(self.rng.choices((-1, 0, 1), weights=(1, 4, 4), k=1)[0] for _ in range(n_vars)), False
        else:
            for cube in self._all_cubes(n_vars):
                if cube not in yielded:
                    yield cube, False

    def _synthesize_bit(self, rows: Sequence[tuple[int, ...]], labels: Sequence[int], state_width: int) -> tuple[Expr, list[Cube]] | None:
        positives = {i for i, y in enumerate(labels) if y}
        if not positives:
            return Expr.const(0), []
        if len(positives) == len(rows):
            return Expr.const(1), [tuple(-1 for _ in rows[0])]
        negatives = set(range(len(rows))) - positives
        candidates: list[tuple[Cube, set[int]]] = []
        coverable: set[int] = set()
        for cube, inherited in self._candidate_stream(len(rows[0])):
            if self.evaluations >= self.candidate_budget:
                return None
            self.evaluations += 1
            if inherited:
                self.inherited_tested += 1
            else:
                self.generic_tested += 1
            covered = {i for i, row in enumerate(rows) if _cube_matches(cube, row)}
            if not covered or covered & negatives:
                continue
            positive_cover = covered & positives
            if not positive_cover:
                continue
            candidates.append((cube, positive_cover))
            coverable |= positive_cover
            if coverable == positives:
                break
        if coverable != positives:
            return None
        uncovered = set(positives)
        selected: list[Cube] = []
        while uncovered:
            cube, cover = max(candidates, key=lambda item: (len(item[1] & uncovered), -_cube_literals(item[0]), tuple(-x for x in item[0])))
            gained = cover & uncovered
            if not gained:
                return None
            selected.append(cube)
            uncovered -= gained
        return _or_expr([cube_to_expr(cube, state_width) for cube in selected]), selected

    def synthesize(self, constraints: Sequence[TransitionConstraint], initial_state: tuple[int, ...], initial_output: int) -> tuple[NativeBody | None, BooleanSynthesisStats, str]:
        if not constraints:
            raise ValueError("At least one constraint is required")
        state_width = len(initial_state)
        for c in constraints:
            c.validate(state_width)
        rows = [tuple((*c.state, c.symbol)) for c in constraints]
        targets = [tuple(c.next_state[i] for c in constraints) for i in range(state_width)]
        targets.append(tuple(c.output for c in constraints))
        expressions: list[Expr] = []
        selected_count = 0
        for labels in targets:
            result = self._synthesize_bit(rows, labels, state_width)
            if result is None:
                return None, BooleanSynthesisStats(self.evaluations, selected_count, len(expressions), self.inherited_tested, self.generic_tested), "candidate_budget_or_unexpressible"
            expr, cubes = result
            expressions.append(expr)
            selected_count += len(cubes)
        body = NativeBody(self.catalog.name, state_width, tuple(expressions[:-1]), expressions[-1], initial_state, initial_output)
        if not body.satisfies(constraints):
            return None, BooleanSynthesisStats(self.evaluations, selected_count, len(expressions), self.inherited_tested, self.generic_tested), "internal_validation_failed"
        return body, BooleanSynthesisStats(self.evaluations, selected_count, len(expressions), self.inherited_tested, self.generic_tested), "exact"


def learn_cube_heritage(development_dfas: Sequence[DFA], provenance: Mapping[str, object] | None = None) -> CubeHeritage:
    templates: dict[int, set[Cube]] = {}
    for dfa in development_dfas:
        constraints, initial, _ = one_hot_constraints(dfa)
        state_width = len(initial)
        rows = [tuple((*c.state, c.symbol)) for c in constraints]
        labels_list = [tuple(c.next_state[i] for c in constraints) for i in range(state_width)]
        labels_list.append(tuple(c.output for c in constraints))
        synth = GenericCubeSynthesizer(REGISTER_CATALOG, candidate_budget=50_000)
        for labels in labels_list:
            result = synth._synthesize_bit(rows, labels, state_width)
            if result is not None:
                _, cubes = result
                templates.setdefault(state_width, set()).update(cubes)
    return CubeHeritage({k: tuple(sorted(v, key=lambda c: (_cube_literals(c), c))) for k, v in templates.items()}, dict(provenance or {}))


class AutonomousMorphogenesisEngine:
    def __init__(self, catalog: PrimitiveCatalog, heritage: CubeHeritage | None, search_seed: int, max_states: int = 8, behavioural_query_budget: int = 10_000, candidate_budget: int = 50_000, cpu_seconds: float = 120.0, native_component_budget: int = 256, serialized_byte_budget: int = 16_777_216, random_search: bool = False) -> None:
        self.catalog = catalog
        self.heritage = heritage
        self.search_seed = search_seed
        self.max_states = max_states
        self.behavioural_query_budget = behavioural_query_budget
        self.candidate_budget = candidate_budget
        self.cpu_seconds = cpu_seconds
        self.native_component_budget = native_component_budget
        self.serialized_byte_budget = serialized_byte_budget
        self.random_search = random_search

    def birth(self, fn: Callable[[tuple[int, ...]], bool], trace: Mapping[str, object] | None = None) -> BirthCertificate:
        started = time.perf_counter()
        contract = OpaqueBehavioralContract(fn, self.behavioural_query_budget)
        base_trace = dict(trace or {})
        try:
            probes = [(), (0,), (1,), (0, 1), (1, 0), (1, 1, 0)]
            contract.audit_consistency(probes)
            oracle = BudgetedMembershipOracle(contract)
            extractor = LStarExtractor((0, 1), oracle, exhaustive_depth=11, random_probes=3500, random_max_len=64, seed=self.search_seed)
            dfa, stats = extractor.extract(max_rounds=80)
            if dfa.n_states > self.max_states:
                return BirthCertificate("abstained", "discovered_state_limit_exceeded", None, dfa, contract.calls, 0, 0, 0, time.perf_counter() - started, stats.rounds, stats.counterexamples, self.heritage is not None, base_trace)
            constraints, initial, initial_output = one_hot_constraints(dfa)
            synthesizer = GenericCubeSynthesizer(self.catalog, self.heritage, self.candidate_budget, self.random_search, self.search_seed)
            body, syn_stats, reason = synthesizer.synthesize(constraints, initial, initial_output)
            if body is None:
                return BirthCertificate("abstained", reason, None, dfa, contract.calls, syn_stats.candidate_evaluations, 0, 0, time.perf_counter() - started, stats.rounds, stats.counterexamples, self.heritage is not None, base_trace)
            components = unique_component_count(body)
            raw = body.to_json().encode("utf-8")
            if components > self.native_component_budget:
                return BirthCertificate("failed", "native_component_budget_exceeded", None, dfa, contract.calls, syn_stats.candidate_evaluations, components, len(raw), time.perf_counter() - started, stats.rounds, stats.counterexamples, self.heritage is not None, base_trace)
            if len(raw) > self.serialized_byte_budget:
                return BirthCertificate("failed", "serialized_byte_budget_exceeded", None, dfa, contract.calls, syn_stats.candidate_evaluations, components, len(raw), time.perf_counter() - started, stats.rounds, stats.counterexamples, self.heritage is not None, base_trace)
            if time.perf_counter() - started > self.cpu_seconds:
                return BirthCertificate("failed", "cpu_budget_exceeded", None, dfa, contract.calls, syn_stats.candidate_evaluations, components, len(raw), time.perf_counter() - started, stats.rounds, stats.counterexamples, self.heritage is not None, base_trace)
            return BirthCertificate("success", "exact_candidate", body, dfa, contract.calls, syn_stats.candidate_evaluations, components, len(raw), time.perf_counter() - started, stats.rounds, stats.counterexamples, self.heritage is not None, base_trace)
        except InconsistentContractError as exc:
            return BirthCertificate("abstained", str(exc), None, None, contract.calls, 0, 0, 0, time.perf_counter() - started, 0, 0, self.heritage is not None, base_trace)
        except RuntimeError as exc:
            return BirthCertificate("abstained", str(exc), None, None, contract.calls, 0, 0, 0, time.perf_counter() - started, 0, 0, self.heritage is not None, base_trace)


def native_body_to_dfa(body: NativeBody) -> DFA:
    n = body.state_width
    transitions: list[tuple[int, int]] = []
    accepting: list[bool | None] = [None] * n
    if sum(body.initial_state) != 1:
        raise ValueError("Native body initial state is not one-hot")
    initial = body.initial_state.index(1)
    accepting[initial] = bool(body.initial_output)
    for state_index in range(n):
        state = tuple(int(i == state_index) for i in range(n))
        row: list[int] = []
        for symbol in (0, 1):
            nxt, output = body.step(state, symbol)
            if len(nxt) != n or sum(nxt) != 1 or any(bit not in (0, 1) for bit in nxt):
                raise ValueError("Native body left the one-hot state manifold")
            target = nxt.index(1)
            row.append(target)
            old = accepting[target]
            if old is not None and old != bool(output):
                raise ValueError("Inconsistent acceptance output for native state")
            accepting[target] = bool(output)
        transitions.append(tuple(row))
    return canonicalize(DFA((0, 1), tuple(transitions), tuple(bool(x) if x is not None else False for x in accepting), initial))
