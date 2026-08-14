"""Independent exact verifier for M092-B candidate-supplied K1 certificates.

The verifier is intentionally smaller than a general theorem prover.  It accepts a closed fragment:
normalized affine equalities and inequalities over arbitrary-precision integers, one natural loop,
at most two explicit ghost counters, and candidate-supplied integer Farkas witnesses.  It never
searches for, repairs, or completes a witness.

Finite execution is not used here.  A successful report is an algebraic proof over every original
top-of-stack value ``x >= 0`` together with a structural stack-frame proof.  Qualification and its
artifacts are outside this module's import and data boundary.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m092_kernel import (
    FUEL_BASE,
    FUEL_SLOPE,
    INSTRUCTION_SET,
    JUMP_OPCODES,
    REGISTER_COUNT,
    Instruction,
    Program,
    program_digest,
    validate_program,
)
from metamorphosis.m092_runtime import canonical_bytes

CERTIFICATE_SCHEMA = "m092-global-k1-certificate-v1"
PRECONDITION_SCHEMA = "m092-nonnegative-stack-input-v1"
POSTCONDITION_SCHEMA = "m092-affine-postcondition-v1"
INDUCTION_SCHEMA = "m092-affine-induction-v1"
TERMINATION_SCHEMA = "m092-affine-termination-v1"
FRAME_SCHEMA = "m092-k1-frame-v1"
STEP_BOUND_SCHEMA = "m092-linear-step-bound-v1"

MAX_CANDIDATE_PROGRAM_LENGTH = 14
MAX_CONSTRAINTS_PER_LOOP = 8
MAX_GHOST_COUNTERS = 2
MAX_PATHS = 4096
MAX_AFFINE_COEFFICIENT = 4
MAX_PROOF_MULTIPLIER = 256

ALLOWED_OPCODES = (
    "HALT",
    "LOADI",
    "MOV",
    "ADD",
    "SUB",
    "MUL",
    "JMP",
    "JZ",
    "JNZ",
    "JLT",
    "SPOP",
    "SPUSH",
)
FORBIDDEN_OPCODES = (
    "FAIL",
    "ARG",
    "SLEN",
    "SPEEK",
    "GETSLOT",
    "SETSLOT",
    "GETINPUT",
)
LITERAL_SET = (-1, 0, 1)

CERTIFICATE_FIELDS = {
    "schema",
    "program_digest",
    "precondition",
    "control_flow_graph",
    "loop_invariants",
    "well_founded_variants",
    "inductive_steps",
    "termination_argument",
    "linear_step_bound",
    "postcondition",
    "frame_condition",
}


class CertificateError(ValueError):
    """A candidate certificate is malformed, incomplete, or does not prove its claim."""


def _integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CertificateError(f"{label} must be an integer")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CertificateError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise CertificateError(f"{label} keys must be strings")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(f"{label} must be an array")
    return value


def _closed(value: object, fields: set[str], label: str) -> Mapping[str, object]:
    result = _mapping(value, label)
    if set(result) != fields:
        raise CertificateError(f"{label} fields differ from the closed schema")
    return result


@dataclass(frozen=True)
class Affine:
    """An exact integer affine expression."""

    terms: tuple[tuple[str, int], ...] = ()
    constant: int = 0

    @classmethod
    def make(cls, terms: Mapping[str, int] | None = None, constant: int = 0) -> "Affine":
        cleaned = tuple(sorted((name, coefficient) for name, coefficient in (terms or {}).items()
                               if coefficient))
        return cls(cleaned, constant)

    @classmethod
    def variable(cls, name: str) -> "Affine":
        return cls(((name, 1),), 0)

    def coefficients(self) -> dict[str, int]:
        return dict(self.terms)

    def __add__(self, other: "Affine") -> "Affine":
        terms = self.coefficients()
        for name, coefficient in other.terms:
            terms[name] = terms.get(name, 0) + coefficient
        return Affine.make(terms, self.constant + other.constant)

    def __sub__(self, other: "Affine") -> "Affine":
        return self + other.scale(-1)

    def scale(self, multiplier: int) -> "Affine":
        return Affine.make(
            {name: coefficient * multiplier for name, coefficient in self.terms},
            self.constant * multiplier,
        )

    def substitute(self, values: Mapping[str, "Affine"]) -> "Affine":
        result = Affine.make(constant=self.constant)
        for name, coefficient in self.terms:
            try:
                replacement = values[name]
            except KeyError as error:
                raise CertificateError(f"no substitution for affine variable {name!r}") from error
            result = result + replacement.scale(coefficient)
        return result

    @property
    def is_constant(self) -> bool:
        return not self.terms

    def to_dict(self) -> dict[str, object]:
        return {"coefficients": dict(self.terms), "constant": self.constant}


@dataclass(frozen=True)
class Constraint:
    """``expression == 0`` or ``expression >= 0``."""

    relation: str
    expression: Affine

    def to_dict(self) -> dict[str, object]:
        return {
            "relation": self.relation,
            "coefficients": dict(self.expression.terms),
            "constant": self.expression.constant,
        }


def _gcd_expression(expression: Affine) -> int:
    values = [abs(coefficient) for _, coefficient in expression.terms]
    values.append(abs(expression.constant))
    return math.gcd(*values) if values else 1


def _normalize_constraint(constraint: Constraint) -> Constraint:
    expression = constraint.expression
    divisor = _gcd_expression(expression)
    if divisor > 1:
        expression = Affine.make(
            {name: coefficient // divisor for name, coefficient in expression.terms},
            expression.constant // divisor,
        )
    if constraint.relation == "eq":
        ordered = [coefficient for _, coefficient in expression.terms]
        ordered.append(expression.constant)
        first = next((coefficient for coefficient in ordered if coefficient), 0)
        if first < 0:
            expression = expression.scale(-1)
    return Constraint(constraint.relation, expression)


def _parse_affine(
    value: object,
    *,
    allowed_variables: set[str],
    label: str,
    coefficient_bound: int | None = MAX_AFFINE_COEFFICIENT,
) -> Affine:
    data = _closed(value, {"coefficients", "constant"}, label)
    coefficients = _mapping(data["coefficients"], f"{label}.coefficients")
    terms: dict[str, int] = {}
    for name, raw_coefficient in coefficients.items():
        if name not in allowed_variables:
            raise CertificateError(f"{label} uses unknown variable {name!r}")
        coefficient = _integer(raw_coefficient, f"{label}.{name}")
        if coefficient == 0:
            raise CertificateError(f"{label} contains an explicit zero coefficient")
        if coefficient_bound is not None and abs(coefficient) > coefficient_bound:
            raise CertificateError(f"{label} coefficient exceeds the frozen bound")
        terms[name] = coefficient
    constant = _integer(data["constant"], f"{label}.constant")
    if coefficient_bound is not None and abs(constant) > coefficient_bound:
        raise CertificateError(f"{label} constant exceeds the frozen bound")
    return Affine.make(terms, constant)


def _parse_constraint(
    value: object,
    *,
    allowed_variables: set[str],
    label: str,
    coefficient_bound: int | None = MAX_AFFINE_COEFFICIENT,
) -> Constraint:
    data = _closed(value, {"relation", "coefficients", "constant"}, label)
    relation = data["relation"]
    if relation not in ("eq", "ge"):
        raise CertificateError(f"{label} has an unsupported relation")
    expression = _parse_affine(
        {"coefficients": data["coefficients"], "constant": data["constant"]},
        allowed_variables=allowed_variables,
        label=label,
        coefficient_bound=coefficient_bound,
    )
    constraint = Constraint(str(relation), expression)
    if _normalize_constraint(constraint) != constraint:
        raise CertificateError(f"{label} is not normalized")
    return constraint


def affine_constraint(
    relation: str,
    coefficients: Mapping[str, int],
    constant: int = 0,
) -> dict[str, object]:
    """Return the canonical public representation used by requirements and fixtures."""

    return _normalize_constraint(
        Constraint(relation, Affine.make(coefficients, constant))
    ).to_dict()


COUNTDOWN_POSTCONDITION: Mapping[str, object] = {
    "schema": POSTCONDITION_SCHEMA,
    "witnesses": [],
    "constraints": [affine_constraint("eq", {"y": 1})],
}

M092_TARGET_POSTCONDITION: Mapping[str, object] = {
    "schema": POSTCONDITION_SCHEMA,
    "witnesses": ["q"],
    "constraints": [
        affine_constraint("eq", {"x": 1, "q": -2, "y": -1}),
        affine_constraint("ge", {"y": 1}),
        affine_constraint("ge", {"y": -1}, 1),
        affine_constraint("ge", {"q": 1}),
    ],
}


def _edge(source: int, target: int, kind: str) -> dict[str, object]:
    return {"source": source, "target": target, "kind": kind}


def control_flow_graph(program: Sequence[Instruction]) -> dict[str, object]:
    """Recompute the exact syntactic CFG a certificate must carry."""

    validate_program(program)
    edges: list[dict[str, object]] = []
    for pc, step in enumerate(program):
        opcode = str(step[0])
        if opcode in ("HALT", "FAIL"):
            continue
        if opcode == "JMP":
            edges.append(_edge(pc, int(step[1]), "jump"))
            continue
        if opcode in ("JZ", "JNZ", "JLT"):
            edges.append(_edge(pc, int(step[-1]), "taken"))
            if pc + 1 >= len(program):
                raise CertificateError("conditional instruction can fall off the program")
            edges.append(_edge(pc, pc + 1, "fallthrough"))
            continue
        if pc + 1 >= len(program):
            raise CertificateError("non-halting instruction can fall off the program")
        edges.append(_edge(pc, pc + 1, "next"))

    reachable = {0}
    changed = True
    while changed:
        changed = False
        for item in edges:
            if item["source"] in reachable and item["target"] not in reachable:
                reachable.add(int(item["target"]))
                changed = True
    if reachable != set(range(len(program))):
        raise CertificateError("candidate contains unreachable instructions")

    back_edges = [item for item in edges if int(item["target"]) <= int(item["source"])]
    loop_headers = sorted({int(item["target"]) for item in back_edges})
    if len(loop_headers) > 1:
        raise CertificateError("candidate exceeds the one-loop-header certificate bound")

    forward_edges = [item for item in edges if item not in back_edges]
    adjacency: dict[int, list[int]] = {pc: [] for pc in range(len(program))}
    for item in forward_edges:
        adjacency[int(item["source"])].append(int(item["target"]))

    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(node: int) -> None:
        if node in visiting:
            raise CertificateError("a cycle remains after removing declared back edges")
        if node in visited:
            return
        visiting.add(node)
        for target in adjacency[node]:
            visit(target)
        visiting.remove(node)
        visited.add(node)

    visit(0)
    return {
        "entry": 0,
        "nodes": list(range(len(program))),
        "edges": edges,
        "loop_headers": loop_headers,
        "back_edges": back_edges,
    }


@dataclass(frozen=True)
class SymbolicState:
    registers: tuple[Affine, ...]
    stack: tuple[Affine, ...]
    ghosts: tuple[tuple[str, Affine], ...]

    def ghost_map(self) -> dict[str, Affine]:
        return dict(self.ghosts)

    def with_register(self, index: int, value: Affine) -> "SymbolicState":
        registers = list(self.registers)
        registers[index] = value
        return SymbolicState(tuple(registers), self.stack, self.ghosts)

    def with_stack(self, stack: Sequence[Affine]) -> "SymbolicState":
        return SymbolicState(self.registers, tuple(stack), self.ghosts)

    def with_ghosts(self, ghosts: Mapping[str, Affine]) -> "SymbolicState":
        return SymbolicState(self.registers, self.stack, tuple(sorted(ghosts.items())))


@dataclass(frozen=True)
class SymbolicPath:
    path_id: str
    source: str
    outcome: str
    target: int
    pcs: tuple[int, ...]
    decisions: tuple[tuple[int, str], ...]
    guards: tuple[Constraint, ...]
    state: SymbolicState


def _path_id(
    source: str,
    outcome: str,
    target: int,
    pcs: Sequence[int],
    decisions: Sequence[tuple[int, str]],
) -> str:
    value = {
        "source": source,
        "outcome": outcome,
        "target": target,
        "pcs": list(pcs),
        "decisions": [[pc, decision] for pc, decision in decisions],
    }
    return "path-" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _condition(expression: Affine, relation: str = "ge") -> Constraint:
    return _normalize_constraint(Constraint(relation, expression))


def _symbolic_paths(
    program: Sequence[Instruction],
    *,
    source: str,
    start: int,
    stop_headers: set[int],
    initial_state: SymbolicState,
) -> list[SymbolicPath]:
    paths: list[SymbolicPath] = []

    def walk(
        pc: int,
        state: SymbolicState,
        pcs: tuple[int, ...],
        decisions: tuple[tuple[int, str], ...],
        guards: tuple[Constraint, ...],
        seen: frozenset[int],
    ) -> None:
        if len(paths) >= MAX_PATHS:
            raise CertificateError("symbolic path count exceeds the frozen bound")
        if pcs and pc in stop_headers:
            paths.append(SymbolicPath(
                _path_id(source, "header", pc, pcs, decisions), source, "header", pc,
                pcs, decisions, guards, state,
            ))
            return
        if pc in seen:
            raise CertificateError("symbolic execution found a cycle outside the loop header")
        if not 0 <= pc < len(program):
            raise CertificateError("a candidate path runs off the program")

        next_seen = seen | {pc}
        step = program[pc]
        opcode = str(step[0])
        operands = [int(operand) for operand in step[1:]]
        next_pcs = pcs + (pc,)
        registers = state.registers

        if opcode == "HALT":
            paths.append(SymbolicPath(
                _path_id(source, "halt", pc, next_pcs, decisions), source, "halt", pc,
                next_pcs, decisions, guards, state,
            ))
            return
        if opcode == "FAIL":
            raise CertificateError("FAIL is outside the candidate opcode surface")
        if opcode == "LOADI":
            updated = state.with_register(operands[0], Affine.make(constant=operands[1]))
            walk(pc + 1, updated, next_pcs, decisions, guards, next_seen)
            return
        if opcode == "MOV":
            updated = state.with_register(operands[0], registers[operands[1]])
            walk(pc + 1, updated, next_pcs, decisions, guards, next_seen)
            return
        if opcode in ("ADD", "SUB"):
            right = registers[operands[2]]
            value = registers[operands[1]] + right if opcode == "ADD" else registers[operands[1]] - right
            walk(pc + 1, state.with_register(operands[0], value), next_pcs,
                 decisions, guards, next_seen)
            return
        if opcode == "MUL":
            left = registers[operands[1]]
            right = registers[operands[2]]
            if left.is_constant:
                value = right.scale(left.constant)
            elif right.is_constant:
                value = left.scale(right.constant)
            else:
                raise CertificateError("symbolic multiplication leaves the accepted affine logic")
            walk(pc + 1, state.with_register(operands[0], value), next_pcs,
                 decisions, guards, next_seen)
            return
        if opcode == "SPOP":
            if not state.stack:
                raise CertificateError("candidate may pop an opaque frame entry")
            updated = state.with_register(operands[0], state.stack[-1]).with_stack(state.stack[:-1])
            walk(pc + 1, updated, next_pcs, decisions, guards, next_seen)
            return
        if opcode == "SPUSH":
            if len(state.stack) >= 1:
                raise CertificateError(
                    "candidate can exceed the entry stack depth before restoring its frame"
                )
            updated = state.with_stack((*state.stack, registers[operands[0]]))
            walk(pc + 1, updated, next_pcs, decisions, guards, next_seen)
            return
        if opcode == "JMP":
            walk(operands[0], state, next_pcs, decisions, guards, next_seen)
            return
        if opcode in ("JZ", "JNZ"):
            expression = registers[operands[0]]
            zero = _condition(expression, "eq")
            negative = _condition(expression.scale(-1) + Affine.make(constant=-1))
            positive = _condition(expression + Affine.make(constant=-1))
            if opcode == "JZ":
                cases = ((operands[1], "zero", zero), (pc + 1, "negative", negative),
                         (pc + 1, "positive", positive))
            else:
                cases = ((operands[1], "negative", negative), (operands[1], "positive", positive),
                         (pc + 1, "zero", zero))
            for target, decision, guard in cases:
                walk(target, state, next_pcs, decisions + ((pc, decision),),
                     guards + (guard,), next_seen)
            return
        if opcode == "JLT":
            left = registers[operands[0]]
            right = registers[operands[1]]
            taken = _condition(right - left + Affine.make(constant=-1))
            fallthrough = _condition(left - right)
            walk(operands[2], state, next_pcs, decisions + ((pc, "taken"),),
                 guards + (taken,), next_seen)
            walk(pc + 1, state, next_pcs, decisions + ((pc, "fallthrough"),),
                 guards + (fallthrough,), next_seen)
            return
        raise CertificateError(f"opcode {opcode!r} is outside the candidate verifier")

    walk(start, initial_state, (), (), (), frozenset())
    return sorted(paths, key=lambda item: item.path_id)


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    path_id: str
    premises: tuple[Constraint, ...]
    goal: Constraint

    def to_candidate_dict(self, proof: Mapping[str, object]) -> dict[str, object]:
        return {
            "id": self.obligation_id,
            "path_id": self.path_id,
            "premises": [item.to_dict() for item in self.premises],
            "goal": self.goal.to_dict(),
            "proof": dict(proof),
        }


@dataclass
class Analysis:
    paths: tuple[SymbolicPath, ...]
    path_status: dict[str, str]
    inductive_obligations: tuple[Obligation, ...]
    termination_obligations: tuple[Obligation, ...]
    step_bound: dict[str, object]
    loop_headers: tuple[int, ...]
    invariant_constraints: int
    ghosts: tuple[str, ...]


def _state_variables(ghosts: Sequence[str]) -> set[str]:
    return {"x", *[f"r{index}" for index in range(REGISTER_COUNT)], *ghosts}


def _source_values(state: SymbolicState) -> dict[str, Affine]:
    values = {"x": Affine.variable("x")}
    values.update({f"r{index}": value for index, value in enumerate(state.registers)})
    values.update(state.ghost_map())
    return values


def _substitute_constraint(constraint: Constraint, values: Mapping[str, Affine]) -> Constraint:
    return _normalize_constraint(Constraint(
        constraint.relation, constraint.expression.substitute(values),
    ))


def _obligation(
    kind: str,
    path: SymbolicPath,
    index: int,
    premises: Sequence[Constraint],
    goal: Constraint,
) -> Obligation:
    obligation_id = f"{kind}:{path.path_id}:{index}"
    return Obligation(obligation_id, path.path_id, tuple(premises), _normalize_constraint(goal))


def _parse_requirement(value: Mapping[str, object]) -> tuple[tuple[str, ...], tuple[Constraint, ...]]:
    data = _closed(value, {"schema", "witnesses", "constraints"}, "expected postcondition")
    if data["schema"] != POSTCONDITION_SCHEMA:
        raise CertificateError("unexpected postcondition requirement schema")
    witnesses = tuple(str(item) for item in _sequence(data["witnesses"], "expected witnesses"))
    if len(witnesses) != len(set(witnesses)) or any(not name for name in witnesses):
        raise CertificateError("expected witness names must be unique and non-empty")
    variables = {"x", "y", *witnesses}
    constraints = tuple(
        _parse_constraint(item, allowed_variables=variables, label=f"expected constraint {index}")
        for index, item in enumerate(_sequence(data["constraints"], "expected constraints"))
    )
    if not constraints:
        raise CertificateError("expected postcondition has no constraints")
    return witnesses, constraints


def _parse_precondition(value: object) -> tuple[tuple[str, ...], tuple[Constraint, ...]]:
    data = _closed(value, {
        "schema", "input_variable", "constraints", "register_initial_values",
        "ghost_initial_values", "stack",
    }, "precondition")
    if data["schema"] != PRECONDITION_SCHEMA or data["input_variable"] != "x":
        raise CertificateError("precondition schema or input variable differs")
    if data["stack"] != "opaque_prefix_plus_x":
        raise CertificateError("precondition does not bind the original top stack value")
    registers = tuple(
        _integer(item, "register initial value")
        for item in _sequence(data["register_initial_values"], "register initial values")
    )
    if registers != (0,) * REGISTER_COUNT:
        raise CertificateError("K1 registers must be initially zero")
    ghost_values = _mapping(data["ghost_initial_values"], "ghost initial values")
    ghosts = tuple(sorted(ghost_values))
    if len(ghosts) > MAX_GHOST_COUNTERS or any(name not in ("g0", "g1") for name in ghosts):
        raise CertificateError("ghost counters exceed the frozen g0/g1 surface")
    if any(_integer(ghost_values[name], f"initial {name}") != 0 for name in ghosts):
        raise CertificateError("ghost counters must start at zero")
    constraints = tuple(
        _parse_constraint(item, allowed_variables={"x"}, label=f"precondition constraint {index}")
        for index, item in enumerate(_sequence(data["constraints"], "precondition constraints"))
    )
    expected = (_normalize_constraint(Constraint("ge", Affine.variable("x"))),)
    if constraints != expected:
        raise CertificateError("precondition must be exactly x >= 0")
    return ghosts, constraints


def _parse_postcondition(
    value: object,
    *,
    expected: Mapping[str, object],
    ghosts: Sequence[str],
) -> tuple[dict[str, str], tuple[Constraint, ...]]:
    data = _closed(value, {"schema", "witness_bindings", "constraints"}, "postcondition")
    if data["schema"] != POSTCONDITION_SCHEMA:
        raise CertificateError("postcondition schema differs")
    expected_witnesses, expected_constraints = _parse_requirement(expected)
    bindings_value = _mapping(data["witness_bindings"], "postcondition witness bindings")
    bindings = {name: str(counter) for name, counter in bindings_value.items()}
    if tuple(sorted(bindings)) != tuple(sorted(expected_witnesses)):
        raise CertificateError("postcondition witnesses differ from the required theorem")
    if len(set(bindings.values())) != len(bindings) or any(counter not in ghosts for counter in bindings.values()):
        raise CertificateError("postcondition witness binding is not an explicit ghost counter")
    variables = {"x", "y", *expected_witnesses}
    constraints = tuple(
        _parse_constraint(item, allowed_variables=variables, label=f"postcondition constraint {index}")
        for index, item in enumerate(_sequence(data["constraints"], "postcondition constraints"))
    )
    if constraints != expected_constraints:
        raise CertificateError("postcondition differs from the required theorem")
    return bindings, constraints


def _parse_invariants(
    value: object,
    *,
    headers: Sequence[int],
    ghosts: Sequence[str],
) -> dict[int, tuple[Constraint, ...]]:
    result: dict[int, tuple[Constraint, ...]] = {}
    variables = _state_variables(ghosts)
    for index, raw_item in enumerate(_sequence(value, "loop invariants")):
        item = _closed(raw_item, {"header", "constraints"}, f"loop invariant {index}")
        header = _integer(item["header"], f"loop invariant {index} header")
        if header in result:
            raise CertificateError("duplicate loop invariant header")
        constraints = tuple(
            _parse_constraint(
                raw_constraint,
                allowed_variables=variables,
                label=f"loop invariant {index} constraint {constraint_index}",
            )
            for constraint_index, raw_constraint in enumerate(
                _sequence(item["constraints"], f"loop invariant {index} constraints")
            )
        )
        if not 1 <= len(constraints) <= MAX_CONSTRAINTS_PER_LOOP:
            raise CertificateError("loop invariant constraint count exceeds the frozen bound")
        result[header] = constraints
    if tuple(sorted(result)) != tuple(headers):
        raise CertificateError("loop invariants do not cover exactly the recomputed headers")
    return result


def _parse_variants(
    value: object,
    *,
    headers: Sequence[int],
    ghosts: Sequence[str],
) -> dict[int, tuple[Affine, int]]:
    result: dict[int, tuple[Affine, int]] = {}
    variables = _state_variables(ghosts)
    for index, raw_item in enumerate(_sequence(value, "well-founded variants")):
        item = _closed(raw_item, {"header", "expression", "minimum_decrease"},
                       f"variant {index}")
        header = _integer(item["header"], f"variant {index} header")
        if header in result:
            raise CertificateError("duplicate variant header")
        expression = _parse_affine(
            item["expression"], allowed_variables=variables, label=f"variant {index}",
        )
        decrease = _integer(item["minimum_decrease"], f"variant {index} decrease")
        if not 1 <= decrease <= MAX_AFFINE_COEFFICIENT:
            raise CertificateError("variant decrease is outside the frozen bound")
        result[header] = (expression, decrease)
    if tuple(sorted(result)) != tuple(headers):
        raise CertificateError("variants do not cover exactly the recomputed headers")
    return result


def _parse_path_status(value: object, paths: Sequence[SymbolicPath]) -> dict[str, str]:
    data = _closed(value, {"schema", "ghost_updates", "path_status", "obligations"},
                   "inductive steps")
    if data["schema"] != INDUCTION_SCHEMA:
        raise CertificateError("inductive-step schema differs")
    statuses: dict[str, str] = {}
    for index, raw_item in enumerate(_sequence(data["path_status"], "path status")):
        item = _closed(raw_item, {"path_id", "status"}, f"path status {index}")
        path_id = str(item["path_id"])
        status = str(item["status"])
        if status not in ("feasible", "infeasible") or path_id in statuses:
            raise CertificateError("path status is invalid or duplicated")
        statuses[path_id] = status
    expected_ids = {path.path_id for path in paths}
    if set(statuses) != expected_ids:
        raise CertificateError("path status does not cover every recomputed path exactly once")
    return statuses


def _parse_ghost_updates(
    induction: Mapping[str, object],
    *,
    paths: Sequence[SymbolicPath],
    ghosts: Sequence[str],
) -> dict[str, dict[str, Affine]]:
    variables = _state_variables(ghosts)
    updates: dict[str, dict[str, Affine]] = {}
    paths_by_id = {path.path_id: path for path in paths}
    for index, raw_item in enumerate(_sequence(induction["ghost_updates"], "ghost updates")):
        item = _closed(raw_item, {"path_id", "assignments"}, f"ghost update {index}")
        path_id = str(item["path_id"])
        if path_id in updates or path_id not in paths_by_id:
            raise CertificateError("ghost update path is invalid or duplicated")
        assignments_value = _mapping(item["assignments"], f"ghost update {index} assignments")
        if set(assignments_value) != set(ghosts):
            raise CertificateError("ghost update must assign every ghost exactly once")
        assignments = {
            name: _parse_affine(
                assignments_value[name], allowed_variables=variables,
                label=f"ghost update {index} {name}",
            )
            for name in ghosts
        }
        path = paths_by_id[path_id]
        for name, expression in assignments.items():
            identity = Affine.variable(name)
            if path.outcome == "header" and path.source.startswith("header:"):
                difference = expression - identity
                if difference.terms or difference.constant not in (0, 1):
                    raise CertificateError("back-edge ghost counters may only stay or increment by one")
            elif expression != identity:
                raise CertificateError("ghost counters may change only on a back edge")
        updates[path_id] = assignments
    if set(updates) != set(paths_by_id):
        raise CertificateError("ghost updates do not cover every recomputed path exactly once")
    return updates


def _apply_ghost_update(state: SymbolicState, update: Mapping[str, Affine]) -> SymbolicState:
    values = _source_values(state)
    return state.with_ghosts({name: expression.substitute(values) for name, expression in update.items()})


def _frame_contract(headers: Sequence[int]) -> dict[str, object]:
    return {
        "schema": FRAME_SCHEMA,
        "entry_stack": "opaque_prefix_plus_x",
        "loop_header_relative_depths": [
            {"header": header, "relative_depth": -1} for header in headers
        ],
        "halt_stack": "opaque_prefix_plus_y",
        "slots": "unchanged",
        "inputs": "unchanged",
        "argument": "unread",
        "forbidden_opcodes": list(FORBIDDEN_OPCODES),
    }


def _initial_entry_state(ghosts: Sequence[str]) -> SymbolicState:
    return SymbolicState(
        tuple(Affine.make() for _ in range(REGISTER_COUNT)),
        (Affine.variable("x"),),
        tuple((name, Affine.make()) for name in ghosts),
    )


def _initial_header_state(ghosts: Sequence[str]) -> SymbolicState:
    return SymbolicState(
        tuple(Affine.variable(f"r{index}") for index in range(REGISTER_COUNT)),
        (),
        tuple((name, Affine.variable(name)) for name in ghosts),
    )


def _premises_for_path(
    path: SymbolicPath,
    *,
    precondition: Sequence[Constraint],
    invariants: Mapping[int, Sequence[Constraint]],
) -> tuple[Constraint, ...]:
    if path.source == "entry":
        source_constraints = tuple(precondition)
    else:
        source_constraints = tuple(invariants[int(path.source.split(":", 1)[1])])
    return (*source_constraints, *path.guards)


def _parse_step_bound(
    value: object,
    *,
    headers: Sequence[int],
) -> tuple[Mapping[str, object], dict[int, tuple[int, int]]]:
    data = _closed(value, {
        "schema", "constant", "x_coefficient", "variant_initial_bounds",
        "max_entry_steps", "max_back_edge_steps", "max_exit_steps",
    }, "linear step bound")
    if data["schema"] != STEP_BOUND_SCHEMA:
        raise CertificateError("linear step-bound schema differs")
    bounds: dict[int, tuple[int, int]] = {}
    for index, raw_item in enumerate(_sequence(data["variant_initial_bounds"],
                                               "variant initial bounds")):
        item = _closed(raw_item, {"header", "constant", "x_coefficient"},
                       f"variant initial bound {index}")
        header = _integer(item["header"], f"variant initial bound {index} header")
        constant = _integer(item["constant"], f"variant initial bound {index} constant")
        coefficient = _integer(item["x_coefficient"],
                               f"variant initial bound {index} coefficient")
        if header in bounds or constant < 0 or coefficient < 0:
            raise CertificateError("variant initial bound is duplicated or negative")
        bounds[header] = (constant, coefficient)
    if tuple(sorted(bounds)) != tuple(headers):
        raise CertificateError("variant initial bounds do not cover the loop headers")
    for field in ("constant", "x_coefficient", "max_entry_steps", "max_back_edge_steps",
                  "max_exit_steps"):
        if _integer(data[field], f"linear step bound {field}") < 0:
            raise CertificateError("linear step-bound values must be non-negative")
    return data, bounds


def _derive_analysis(
    program: Sequence[Instruction],
    certificate: Mapping[str, object],
    expected_postcondition: Mapping[str, object],
) -> Analysis:
    cfg = control_flow_graph(program)
    if certificate["control_flow_graph"] != cfg:
        raise CertificateError("certificate CFG differs from the recomputed program CFG")
    headers = tuple(int(item) for item in cfg["loop_headers"])
    ghosts, precondition = _parse_precondition(certificate["precondition"])
    bindings, postcondition = _parse_postcondition(
        certificate["postcondition"], expected=expected_postcondition, ghosts=ghosts,
    )
    invariants = _parse_invariants(
        certificate["loop_invariants"], headers=headers, ghosts=ghosts,
    )
    variants = _parse_variants(
        certificate["well_founded_variants"], headers=headers, ghosts=ghosts,
    )

    paths = _symbolic_paths(
        program, source="entry", start=0, stop_headers=set(headers),
        initial_state=_initial_entry_state(ghosts),
    )
    for header in headers:
        paths.extend(_symbolic_paths(
            program, source=f"header:{header}", start=header, stop_headers=set(headers),
            initial_state=_initial_header_state(ghosts),
        ))
    paths = sorted(paths, key=lambda item: item.path_id)

    induction = _closed(certificate["inductive_steps"],
                        {"schema", "ghost_updates", "path_status", "obligations"},
                        "inductive steps")
    statuses = _parse_path_status(induction, paths)
    updates = _parse_ghost_updates(induction, paths=paths, ghosts=ghosts)
    step_bound_data, initial_bounds = _parse_step_bound(
        certificate["linear_step_bound"], headers=headers,
    )

    feasible_paths = [path for path in paths if statuses[path.path_id] == "feasible"]
    if not any(path.source == "entry" for path in feasible_paths):
        raise CertificateError("certificate declares every entry path infeasible")
    if headers and not any(path.source.startswith("header:") and path.outcome == "halt"
                           for path in feasible_paths):
        raise CertificateError("certificate has no feasible loop exit")

    inductive: list[Obligation] = []
    termination: list[Obligation] = []
    for path in paths:
        premises = _premises_for_path(path, precondition=precondition, invariants=invariants)
        if statuses[path.path_id] == "infeasible":
            false_goal = Constraint("ge", Affine.make(constant=-1))
            inductive.append(_obligation("infeasible", path, 0, premises, false_goal))
            continue

        final_state = _apply_ghost_update(path.state, updates[path.path_id])
        final_values = _source_values(final_state)
        if path.outcome == "header":
            if final_state.stack:
                raise CertificateError("a feasible loop path does not preserve the opaque stack frame")
            for index, constraint in enumerate(invariants[path.target]):
                goal = _substitute_constraint(constraint, final_values)
                kind = "establish" if path.source == "entry" else "preserve"
                inductive.append(_obligation(kind, path, index, premises, goal))
        else:
            if len(final_state.stack) != 1:
                raise CertificateError("a feasible halt path does not leave exactly one output")
            post_values = {"x": Affine.variable("x"), "y": final_state.stack[0]}
            final_ghosts = final_state.ghost_map()
            post_values.update({name: final_ghosts[counter] for name, counter in bindings.items()})
            for index, constraint in enumerate(postcondition):
                goal = _substitute_constraint(constraint, post_values)
                inductive.append(_obligation("postcondition", path, index, premises, goal))

    for header in headers:
        variant, decrease = variants[header]
        header_path = SymbolicPath(
            f"header-{header}", f"header:{header}", "header", header, (), (), (),
            _initial_header_state(ghosts),
        )
        premises = tuple(invariants[header])
        termination.append(_obligation(
            "variant_nonnegative", header_path, 0, premises, Constraint("ge", variant),
        ))

        for path in feasible_paths:
            if path.source != f"header:{header}" or path.outcome != "header":
                continue
            final_state = _apply_ghost_update(path.state, updates[path.path_id])
            next_variant = variant.substitute(_source_values(final_state))
            goal = Constraint("ge", variant - next_variant + Affine.make(constant=-decrease))
            termination.append(_obligation(
                "variant_decrease", path, 0,
                _premises_for_path(path, precondition=precondition, invariants=invariants), goal,
            ))

        initial_constant, initial_coefficient = initial_bounds[header]
        for path in feasible_paths:
            if path.source != "entry" or path.outcome != "header" or path.target != header:
                continue
            final_state = _apply_ghost_update(path.state, updates[path.path_id])
            initial_variant = variant.substitute(_source_values(final_state))
            upper = Affine.make({"x": initial_coefficient}, initial_constant)
            termination.append(_obligation(
                "variant_initial_upper_bound", path, 0,
                _premises_for_path(path, precondition=precondition, invariants=invariants),
                Constraint("ge", upper - initial_variant),
            ))

    feasible_entry_to_header = [
        len(path.pcs) for path in feasible_paths
        if path.source == "entry" and path.outcome == "header"
    ]
    feasible_direct_halts = [
        len(path.pcs) for path in feasible_paths
        if path.source == "entry" and path.outcome == "halt"
    ]
    feasible_back = [
        len(path.pcs) for path in feasible_paths
        if path.source.startswith("header:") and path.outcome == "header"
    ]
    feasible_exits = [
        len(path.pcs) for path in feasible_paths
        if path.source.startswith("header:") and path.outcome == "halt"
    ]
    max_entry = max(feasible_entry_to_header, default=0)
    max_back = max(feasible_back, default=0)
    max_exit = max(feasible_exits, default=0)
    direct_bound = max(feasible_direct_halts, default=0)
    if headers:
        initial_constant, initial_coefficient = initial_bounds[headers[0]]
        expected_constant = max(direct_bound, max_entry + max_back * initial_constant + max_exit)
        expected_coefficient = max_back * initial_coefficient
    else:
        expected_constant = direct_bound
        expected_coefficient = 0
    expected_step_bound = {
        "schema": STEP_BOUND_SCHEMA,
        "constant": expected_constant,
        "x_coefficient": expected_coefficient,
        "variant_initial_bounds": [
            {"header": header, "constant": initial_bounds[header][0],
             "x_coefficient": initial_bounds[header][1]}
            for header in headers
        ],
        "max_entry_steps": max_entry,
        "max_back_edge_steps": max_back,
        "max_exit_steps": max_exit,
    }
    if dict(step_bound_data) != expected_step_bound:
        raise CertificateError("declared linear step bound is not the recomputed structural bound")
    if expected_constant > FUEL_BASE or expected_coefficient > FUEL_SLOPE:
        raise CertificateError("proved linear step bound exceeds the frozen K1 fuel rule")

    return Analysis(
        tuple(paths), statuses, tuple(inductive), tuple(termination), expected_step_bound,
        headers, sum(len(items) for items in invariants.values()), ghosts,
    )


def _verify_proof(obligation: Obligation, value: object) -> None:
    data = _closed(value, {"multipliers", "slack"}, f"proof {obligation.obligation_id}")
    multipliers = tuple(
        _integer(item, f"proof {obligation.obligation_id} multiplier")
        for item in _sequence(data["multipliers"], "proof multipliers")
    )
    if len(multipliers) != len(obligation.premises):
        raise CertificateError(f"proof {obligation.obligation_id} multiplier count differs")
    if any(abs(multiplier) > MAX_PROOF_MULTIPLIER for multiplier in multipliers):
        raise CertificateError(f"proof {obligation.obligation_id} multiplier exceeds the bound")
    slack = _integer(data["slack"], f"proof {obligation.obligation_id} slack")
    if not 0 <= slack <= MAX_PROOF_MULTIPLIER:
        raise CertificateError(f"proof {obligation.obligation_id} slack is outside the bound")

    combination = Affine.make(constant=slack)
    for premise, multiplier in zip(obligation.premises, multipliers, strict=True):
        if premise.relation == "ge" and multiplier < 0:
            raise CertificateError(
                f"proof {obligation.obligation_id} negates an inequality premise"
            )
        if obligation.goal.relation == "eq" and premise.relation == "ge" and multiplier:
            raise CertificateError(
                f"proof {obligation.obligation_id} uses an inequality to assert equality"
            )
        combination = combination + premise.expression.scale(multiplier)
    if obligation.goal.relation == "eq" and slack:
        raise CertificateError(f"proof {obligation.obligation_id} adds slack to equality")
    if combination != obligation.goal.expression:
        raise CertificateError(f"proof {obligation.obligation_id} does not derive its exact goal")


def _verify_obligation_records(
    expected: Sequence[Obligation],
    value: object,
    *,
    label: str,
) -> None:
    records = _sequence(value, label)
    if len(records) != len(expected):
        raise CertificateError(f"{label} count differs from the recomputed obligations")
    for index, (obligation, raw_record) in enumerate(zip(expected, records, strict=True)):
        record = _closed(
            raw_record, {"id", "path_id", "premises", "goal", "proof"}, f"{label} {index}",
        )
        exact = {
            "id": obligation.obligation_id,
            "path_id": obligation.path_id,
            "premises": [item.to_dict() for item in obligation.premises],
            "goal": obligation.goal.to_dict(),
        }
        if {key: record[key] for key in exact} != exact:
            raise CertificateError(f"{label} {index} differs from the recomputed obligation")
        _verify_proof(obligation, record["proof"])


def certificate_digest(certificate: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(certificate)).hexdigest()


def verify_global_certificate(
    program: Program,
    certificate: Mapping[str, object],
    *,
    expected_postcondition: Mapping[str, object],
) -> dict[str, object]:
    """Verify a complete candidate-supplied certificate without executing the program."""

    validate_program(program)
    if len(program) > MAX_CANDIDATE_PROGRAM_LENGTH:
        raise CertificateError("candidate program exceeds the frozen length bound")
    for step in program:
        opcode = str(step[0])
        if opcode not in ALLOWED_OPCODES:
            raise CertificateError(f"candidate opcode {opcode!r} is forbidden")
        if opcode == "LOADI" and int(step[2]) not in LITERAL_SET:
            raise CertificateError("candidate literal is outside the frozen set")
    if not any(str(step[0]) == "HALT" for step in program):
        raise CertificateError("candidate has no HALT instruction")
    if set(ALLOWED_OPCODES) | set(FORBIDDEN_OPCODES) != set(INSTRUCTION_SET):
        raise CertificateError("verifier opcode partition has drifted from K1")

    value = _closed(certificate, CERTIFICATE_FIELDS, "certificate")
    if value["schema"] != CERTIFICATE_SCHEMA:
        raise CertificateError("certificate schema differs")
    exact_program_digest = program_digest(program)
    if value["program_digest"] != exact_program_digest:
        raise CertificateError("certificate is not bound to the exact candidate program")

    analysis = _derive_analysis(program, value, expected_postcondition)
    if value["frame_condition"] != _frame_contract(analysis.loop_headers):
        raise CertificateError("frame condition differs from the recomputed closed contract")

    induction = _mapping(value["inductive_steps"], "inductive steps")
    _verify_obligation_records(
        analysis.inductive_obligations, induction["obligations"], label="inductive obligations",
    )
    termination = _closed(
        value["termination_argument"],
        {"schema", "back_edges_break_all_cycles", "obligations"},
        "termination argument",
    )
    if termination["schema"] != TERMINATION_SCHEMA:
        raise CertificateError("termination schema differs")
    if termination["back_edges_break_all_cycles"] is not True:
        raise CertificateError("termination argument does not cover every cycle")
    _verify_obligation_records(
        analysis.termination_obligations, termination["obligations"],
        label="termination obligations",
    )

    return {
        "status": "accepted",
        "program_digest": exact_program_digest,
        "certificate_digest": certificate_digest(certificate),
        "control_flow_nodes": len(program),
        "symbolic_paths": len(analysis.paths),
        "loop_headers": len(analysis.loop_headers),
        "invariant_constraints": analysis.invariant_constraints,
        "ghost_counters": len(analysis.ghosts),
        "inductive_obligations": len(analysis.inductive_obligations),
        "termination_obligations": len(analysis.termination_obligations),
        "linear_step_bound": analysis.step_bound,
        "global_domain": "every integer x >= 0",
        "finite_execution_used": False,
        "frame": {
            "remaining_stack": "unchanged",
            "slots": "unchanged",
            "inputs": "unchanged",
        },
    }


__all__ = [
    "ALLOWED_OPCODES",
    "CERTIFICATE_SCHEMA",
    "COUNTDOWN_POSTCONDITION",
    "CertificateError",
    "FORBIDDEN_OPCODES",
    "FRAME_SCHEMA",
    "INDUCTION_SCHEMA",
    "M092_TARGET_POSTCONDITION",
    "POSTCONDITION_SCHEMA",
    "PRECONDITION_SCHEMA",
    "STEP_BOUND_SCHEMA",
    "TERMINATION_SCHEMA",
    "affine_constraint",
    "certificate_digest",
    "control_flow_graph",
    "verify_global_certificate",
]
