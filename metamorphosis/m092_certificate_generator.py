"""Generic candidate-side certificate construction for the frozen M092 search.

This module intentionally does not import the independent M092 certificate verifier. It rebuilds
only the small affine machinery needed by the lineage to *propose* certificates: syntactic CFG
construction, symbolic execution of the frozen candidate opcode surface, bounded invariant and
variant enumeration, and exact affine proof-witness search.

No qualification artifact, hidden value, finite target table, or result artifact is an input. The
required postcondition is a theorem statement. Every emitted certificate remains a candidate claim
until the independent verifier recomputes and accepts it.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterator, Mapping, Sequence

from metamorphosis.m092_kernel import (
    FUEL_BASE,
    FUEL_SLOPE,
    INSTRUCTION_SET,
    REGISTER_COUNT,
    Instruction,
    Program,
    program_digest,
    validate_program,
)
from metamorphosis.m092_proof_search import find_affine_proof
from metamorphosis.m092_runtime import canonical_bytes

CERTIFICATE_SCHEMA = "m092-global-k1-certificate-v1"
PRECONDITION_SCHEMA = "m092-nonnegative-stack-input-v1"
POSTCONDITION_SCHEMA = "m092-affine-postcondition-v1"
INDUCTION_SCHEMA = "m092-affine-induction-v1"
TERMINATION_SCHEMA = "m092-affine-termination-v1"
FRAME_SCHEMA = "m092-k1-frame-v1"
STEP_BOUND_SCHEMA = "m092-linear-step-bound-v1"

MAX_AFFINE_COEFFICIENT = 4
MAX_CONSTRAINTS_PER_LOOP = 8
MAX_GHOST_COUNTERS = 2
MAX_PATHS = 4096
MAX_EQUALITY_SUPPORT = 3
MAX_INITIAL_BOUND_CONSTANT = 8
PROOF_MULTIPLIER_BOUND = 8
PROOF_SUPPORT_BOUND = 6

FORBIDDEN_OPCODES = (
    "FAIL", "ARG", "SLEN", "SPEEK", "GETSLOT", "SETSLOT", "GETINPUT",
)


class CertificateGenerationError(ValueError):
    """The exact program has no certificate in this deterministic template family."""


@dataclass(frozen=True)
class Affine:
    terms: tuple[tuple[str, int], ...] = ()
    constant: int = 0

    @classmethod
    def make(cls, terms: Mapping[str, int] | None = None, constant: int = 0) -> "Affine":
        return cls(
            tuple(sorted((str(name), int(value)) for name, value in (terms or {}).items() if value)),
            int(constant),
        )

    @classmethod
    def variable(cls, name: str) -> "Affine":
        return cls(((name, 1),), 0)

    def coefficients(self) -> dict[str, int]:
        return dict(self.terms)

    def __add__(self, other: "Affine") -> "Affine":
        values = self.coefficients()
        for name, coefficient in other.terms:
            values[name] = values.get(name, 0) + coefficient
            if values[name] == 0:
                del values[name]
        return Affine.make(values, self.constant + other.constant)

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
            if name not in values:
                raise CertificateGenerationError(f"missing affine substitution for {name!r}")
            result = result + values[name].scale(coefficient)
        return result

    @property
    def is_constant(self) -> bool:
        return not self.terms

    def to_dict(self) -> dict[str, object]:
        return {"coefficients": dict(self.terms), "constant": self.constant}


@dataclass(frozen=True)
class Constraint:
    relation: str
    expression: Affine

    def to_dict(self) -> dict[str, object]:
        return {
            "relation": self.relation,
            "coefficients": dict(self.expression.terms),
            "constant": self.expression.constant,
        }


def _normalise(constraint: Constraint) -> Constraint:
    values = [abs(value) for _, value in constraint.expression.terms]
    values.append(abs(constraint.expression.constant))
    divisor = math.gcd(*values) if values else 1
    expression = constraint.expression
    if divisor > 1:
        expression = Affine.make(
            {name: coefficient // divisor for name, coefficient in expression.terms},
            expression.constant // divisor,
        )
    if constraint.relation == "eq":
        ordered = [coefficient for _, coefficient in expression.terms] + [expression.constant]
        first = next((coefficient for coefficient in ordered if coefficient), 0)
        if first < 0:
            expression = expression.scale(-1)
    return Constraint(constraint.relation, expression)


def _constraint(relation: str, expression: Affine) -> Constraint:
    if relation not in ("eq", "ge"):
        raise CertificateGenerationError("unsupported affine relation")
    return _normalise(Constraint(relation, expression))


def _false_constraint() -> Constraint:
    return Constraint("ge", Affine.make(constant=-1))


def control_flow_graph(program: Sequence[Instruction]) -> dict[str, object]:
    """Recompute the same closed syntactic CFG that a submitted certificate must carry."""

    validate_program(program)
    edges: list[dict[str, object]] = []
    for pc, step in enumerate(program):
        opcode = str(step[0])
        if opcode in ("HALT", "FAIL"):
            continue
        if opcode == "JMP":
            edges.append({"source": pc, "target": int(step[1]), "kind": "jump"})
            continue
        if opcode in ("JZ", "JNZ", "JLT"):
            edges.append({"source": pc, "target": int(step[-1]), "kind": "taken"})
            if pc + 1 >= len(program):
                raise CertificateGenerationError("conditional can fall off the program")
            edges.append({"source": pc, "target": pc + 1, "kind": "fallthrough"})
            continue
        if pc + 1 >= len(program):
            raise CertificateGenerationError("non-halting instruction can fall off the program")
        edges.append({"source": pc, "target": pc + 1, "kind": "next"})

    reachable = {0}
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge["source"] in reachable and edge["target"] not in reachable:
                reachable.add(int(edge["target"]))
                changed = True
    if reachable != set(range(len(program))):
        raise CertificateGenerationError("program contains unreachable instructions")

    back_edges = [edge for edge in edges if int(edge["target"]) <= int(edge["source"])]
    headers = sorted({int(edge["target"]) for edge in back_edges})
    if len(headers) != 1:
        raise CertificateGenerationError("certificate template requires exactly one loop header")

    forward = [edge for edge in edges if edge not in back_edges]
    adjacency: dict[int, list[int]] = {pc: [] for pc in range(len(program))}
    for edge in forward:
        adjacency[int(edge["source"])].append(int(edge["target"]))
    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(node: int) -> None:
        if node in visiting:
            raise CertificateGenerationError("cycle remains after removing the declared back edge")
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
        "loop_headers": headers,
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
    payload = {
        "source": source,
        "outcome": outcome,
        "target": target,
        "pcs": list(pcs),
        "decisions": [[pc, decision] for pc, decision in decisions],
    }
    return "path-" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


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
            raise CertificateGenerationError("symbolic path count exceeds the frozen bound")
        if pcs and pc in stop_headers:
            paths.append(SymbolicPath(
                _path_id(source, "header", pc, pcs, decisions), source, "header", pc,
                pcs, decisions, guards, state,
            ))
            return
        if pc in seen or not 0 <= pc < len(program):
            raise CertificateGenerationError("unexpected symbolic cycle or program falloff")

        step = program[pc]
        opcode = str(step[0])
        operands = [int(value) for value in step[1:]]
        next_pcs = pcs + (pc,)
        next_seen = seen | {pc}
        registers = state.registers

        if opcode == "HALT":
            paths.append(SymbolicPath(
                _path_id(source, "halt", pc, next_pcs, decisions), source, "halt", pc,
                next_pcs, decisions, guards, state,
            ))
            return
        if opcode == "FAIL":
            raise CertificateGenerationError("FAIL is outside the candidate surface")
        if opcode == "LOADI":
            updated = state.with_register(operands[0], Affine.make(constant=operands[1]))
            walk(pc + 1, updated, next_pcs, decisions, guards, next_seen)
            return
        if opcode == "MOV":
            walk(pc + 1, state.with_register(operands[0], registers[operands[1]]),
                 next_pcs, decisions, guards, next_seen)
            return
        if opcode in ("ADD", "SUB"):
            right = registers[operands[2]]
            value = registers[operands[1]] + right if opcode == "ADD" else registers[operands[1]] - right
            walk(pc + 1, state.with_register(operands[0], value), next_pcs, decisions, guards, next_seen)
            return
        if opcode == "MUL":
            left = registers[operands[1]]
            right = registers[operands[2]]
            if left.is_constant:
                value = right.scale(left.constant)
            elif right.is_constant:
                value = left.scale(right.constant)
            else:
                raise CertificateGenerationError("symbolic multiplication leaves affine logic")
            walk(pc + 1, state.with_register(operands[0], value), next_pcs, decisions, guards, next_seen)
            return
        if opcode == "SPOP":
            if not state.stack:
                raise CertificateGenerationError("candidate may pop an opaque frame entry")
            updated = state.with_register(operands[0], state.stack[-1]).with_stack(state.stack[:-1])
            walk(pc + 1, updated, next_pcs, decisions, guards, next_seen)
            return
        if opcode == "SPUSH":
            if state.stack:
                raise CertificateGenerationError("candidate can exceed the entry stack depth")
            walk(pc + 1, state.with_stack((registers[operands[0]],)),
                 next_pcs, decisions, guards, next_seen)
            return
        if opcode == "JMP":
            walk(operands[0], state, next_pcs, decisions, guards, next_seen)
            return
        if opcode in ("JZ", "JNZ"):
            expression = registers[operands[0]]
            zero = _constraint("eq", expression)
            negative = _constraint("ge", expression.scale(-1) + Affine.make(constant=-1))
            positive = _constraint("ge", expression + Affine.make(constant=-1))
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
            taken = _constraint("ge", right - left + Affine.make(constant=-1))
            fallthrough = _constraint("ge", left - right)
            walk(operands[2], state, next_pcs, decisions + ((pc, "taken"),),
                 guards + (taken,), next_seen)
            walk(pc + 1, state, next_pcs, decisions + ((pc, "fallthrough"),),
                 guards + (fallthrough,), next_seen)
            return
        raise CertificateGenerationError(f"opcode {opcode!r} is outside the candidate surface")

    walk(start, initial_state, (), (), (), frozenset())
    return sorted(paths, key=lambda item: item.path_id)


def _source_values(state: SymbolicState) -> dict[str, Affine]:
    values = {"x": Affine.variable("x")}
    values.update({f"r{index}": value for index, value in enumerate(state.registers)})
    values.update(state.ghost_map())
    return values


def _ghost_update(
    path: SymbolicPath,
    ghosts: Sequence[str],
    increments: tuple[int, ...],
) -> dict[str, Affine]:
    back_edge = path.outcome == "header" and path.source.startswith("header:")
    return {
        name: Affine.variable(name) + Affine.make(
            constant=increments[index] if back_edge else 0,
        )
        for index, name in enumerate(ghosts)
    }


def _apply_update(state: SymbolicState, update: Mapping[str, Affine]) -> SymbolicState:
    values = _source_values(state)
    return state.with_ghosts({
        name: expression.substitute(values) for name, expression in update.items()
    })


def _active_registers(program: Sequence[Instruction]) -> tuple[int, ...]:
    registers: set[int] = set()
    for step in program:
        roles = INSTRUCTION_SET[str(step[0])]
        for operand, role in zip(step[1:], roles, strict=True):
            if role == "r":
                registers.add(int(operand))
    return tuple(sorted(registers))


def _active_variables(program: Sequence[Instruction], ghosts: Sequence[str]) -> tuple[str, ...]:
    return (
        "x",
        *[f"r{index}" for index in _active_registers(program)],
        *ghosts,
    )


def _rank(rows: Sequence[Sequence[int]]) -> int:
    matrix = [[Fraction(value) for value in row] for row in rows]
    if not matrix:
        return 0
    pivot_row = 0
    for column in range(len(matrix[0])):
        pivot = next((row for row in range(pivot_row, len(matrix)) if matrix[row][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        divisor = matrix[pivot_row][column]
        matrix[pivot_row] = [value / divisor for value in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                left - factor * right
                for left, right in zip(matrix[row], matrix[pivot_row], strict=True)
            ]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row


def _entry_header_values(
    paths: Sequence[SymbolicPath],
    updates: Mapping[str, Mapping[str, Affine]],
) -> list[dict[str, Affine]]:
    return [
        _source_values(_apply_update(path.state, updates[path.path_id]))
        for path in paths
        if path.source == "entry" and path.outcome == "header"
    ]


def _derive_equalities(
    program: Sequence[Instruction],
    paths: Sequence[SymbolicPath],
    ghosts: Sequence[str],
    updates: Mapping[str, Mapping[str, Affine]],
) -> list[Constraint]:
    entries = _entry_header_values(paths, updates)
    if not entries:
        return []
    back_paths = [
        path for path in paths
        if path.source.startswith("header:") and path.outcome == "header"
    ]
    variables = _active_variables(program, ghosts)
    coefficient_values = (-1, 1, -2, 2, -3, 3, -4, 4)
    candidates: list[Constraint] = []

    for support_size in range(1, min(MAX_EQUALITY_SUPPORT, len(variables)) + 1):
        for support in itertools.combinations(variables, support_size):
            for coefficients in itertools.product(coefficient_values, repeat=support_size):
                expression = Affine.make(dict(zip(support, coefficients, strict=True)))
                entry_forms = [expression.substitute(values) for values in entries]
                if any(form.terms for form in entry_forms):
                    continue
                constants = {form.constant for form in entry_forms}
                if len(constants) != 1:
                    continue
                constant = -next(iter(constants))
                if abs(constant) > MAX_AFFINE_COEFFICIENT:
                    continue
                expression = expression + Affine.make(constant=constant)
                if any(
                    expression.substitute(
                        _source_values(_apply_update(path.state, updates[path.path_id]))
                    ) - expression != Affine.make()
                    for path in back_paths
                ):
                    continue
                candidate = _constraint("eq", expression)
                if candidate not in candidates:
                    candidates.append(candidate)

    basis: list[Constraint] = []
    rows: list[list[int]] = []
    for candidate in candidates:
        row = [candidate.expression.coefficients().get(name, 0) for name in variables]
        row.append(candidate.expression.constant)
        if _rank([*rows, row]) > _rank(rows):
            basis.append(candidate)
            rows.append(row)
        if len(basis) >= MAX_CONSTRAINTS_PER_LOOP - 1:
            break
    return basis


def _proof(premises: Sequence[Constraint], goal: Constraint) -> dict[str, object] | None:
    return find_affine_proof(
        [item.to_dict() for item in premises],
        goal.to_dict(),
        multiplier_bound=PROOF_MULTIPLIER_BOUND,
        support_bound=PROOF_SUPPORT_BOUND,
    )


def _path_premises(
    path: SymbolicPath,
    precondition: Sequence[Constraint],
    invariants: Sequence[Constraint],
) -> tuple[Constraint, ...]:
    source = tuple(precondition) if path.source == "entry" else tuple(invariants)
    return (*source, *path.guards)


def _is_infeasible(premises: Sequence[Constraint]) -> bool:
    return _proof(premises, _false_constraint()) is not None


def _derive_inequalities(
    program: Sequence[Instruction],
    paths: Sequence[SymbolicPath],
    equalities: Sequence[Constraint],
    precondition: Sequence[Constraint],
    updates: Mapping[str, Mapping[str, Affine]],
    ghosts: Sequence[str],
) -> list[Constraint]:
    active = _active_registers(program)
    names = (
        *(["r0"] if 0 in active else []),
        *ghosts,
        *[f"r{index}" for index in active if index != 0],
        "x",
    )
    accepted: list[Constraint] = []
    for name in names:
        for sign in (1, -1):
            candidate = _constraint("ge", Affine.make({name: sign}))
            if _proof([*equalities, *accepted], candidate) is not None:
                continue
            if len(equalities) + len(accepted) >= MAX_CONSTRAINTS_PER_LOOP:
                return accepted

            establishes = True
            for path in paths:
                if path.source != "entry" or path.outcome != "header":
                    continue
                premises = _path_premises(path, precondition, ())
                final = _apply_update(path.state, updates[path.path_id])
                goal = _constraint(
                    "ge", candidate.expression.substitute(_source_values(final)),
                )
                if _proof(premises, goal) is None:
                    establishes = False
                    break
            if not establishes:
                continue

            trial = [*equalities, *accepted, candidate]
            preserves = True
            for path in paths:
                if not path.source.startswith("header:") or path.outcome != "header":
                    continue
                premises = _path_premises(path, precondition, trial)
                if _is_infeasible(premises):
                    continue
                final = _apply_update(path.state, updates[path.path_id])
                goal = _constraint(
                    "ge", candidate.expression.substitute(_source_values(final)),
                )
                if _proof(premises, goal) is None:
                    preserves = False
                    break
            if preserves:
                accepted.append(candidate)
    return accepted


def _path_statuses(
    paths: Sequence[SymbolicPath],
    precondition: Sequence[Constraint],
    invariants: Sequence[Constraint],
) -> dict[str, str]:
    return {
        path.path_id: (
            "infeasible"
            if _is_infeasible(_path_premises(path, precondition, invariants))
            else "feasible"
        )
        for path in paths
    }


def _variant_candidates(program: Sequence[Instruction], ghosts: Sequence[str]) -> Iterator[Affine]:
    active = _active_registers(program)
    names = (
        *(["r0"] if 0 in active else []),
        *[f"r{index}" for index in active if index != 0],
        *ghosts,
    )
    for name in names:
        for coefficient in (1, -1, 2, -2, 3, -3, 4, -4):
            yield Affine.make({name: coefficient})


def _find_variant(
    program: Sequence[Instruction],
    paths: Sequence[SymbolicPath],
    statuses: Mapping[str, str],
    precondition: Sequence[Constraint],
    invariants: Sequence[Constraint],
    updates: Mapping[str, Mapping[str, Affine]],
    header: int,
    ghosts: Sequence[str],
) -> tuple[Affine, int, int, int] | None:
    for variant in _variant_candidates(program, ghosts):
        if _proof(invariants, _constraint("ge", variant)) is None:
            continue
        for decrease in range(1, MAX_AFFINE_COEFFICIENT + 1):
            if any(
                _proof(
                    _path_premises(path, precondition, invariants),
                    _constraint(
                        "ge",
                        variant
                        - variant.substitute(
                            _source_values(_apply_update(path.state, updates[path.path_id]))
                        )
                        + Affine.make(constant=-decrease),
                    ),
                ) is None
                for path in paths
                if statuses[path.path_id] == "feasible"
                and path.source == f"header:{header}"
                and path.outcome == "header"
            ):
                continue

            for coefficient in range(FUEL_SLOPE + 1):
                for constant in range(MAX_INITIAL_BOUND_CONSTANT + 1):
                    bounded = True
                    for path in paths:
                        if (
                            statuses[path.path_id] != "feasible"
                            or path.source != "entry"
                            or path.outcome != "header"
                        ):
                            continue
                        initial = variant.substitute(
                            _source_values(_apply_update(path.state, updates[path.path_id]))
                        )
                        upper = Affine.make(
                            {"x": coefficient} if coefficient else {}, constant,
                        )
                        goal = _constraint("ge", upper - initial)
                        if _proof(_path_premises(path, precondition, invariants), goal) is None:
                            bounded = False
                            break
                    if bounded:
                        return variant, decrease, constant, coefficient
    return None


def _obligation_record(
    kind: str,
    path: SymbolicPath,
    index: int,
    premises: Sequence[Constraint],
    goal: Constraint,
) -> dict[str, object] | None:
    goal = _constraint(goal.relation, goal.expression)
    proof = _proof(premises, goal)
    if proof is None:
        return None
    return {
        "id": f"{kind}:{path.path_id}:{index}",
        "path_id": path.path_id,
        "premises": [item.to_dict() for item in premises],
        "goal": goal.to_dict(),
        "proof": proof,
    }


def _frame(headers: Sequence[int]) -> dict[str, object]:
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


def _requirement(
    value: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[Constraint, ...]]:
    if set(value) != {"schema", "witnesses", "constraints"}:
        raise CertificateGenerationError("expected postcondition uses an open schema")
    if value.get("schema") != POSTCONDITION_SCHEMA:
        raise CertificateGenerationError("unexpected postcondition schema")
    witnesses_value = value.get("witnesses")
    constraints_value = value.get("constraints")
    if not isinstance(witnesses_value, Sequence) or isinstance(witnesses_value, (str, bytes)):
        raise CertificateGenerationError("expected witnesses are malformed")
    if not isinstance(constraints_value, Sequence) or isinstance(constraints_value, (str, bytes)):
        raise CertificateGenerationError("expected constraints are malformed")
    witnesses = tuple(str(item) for item in witnesses_value)
    if len(witnesses) != len(set(witnesses)):
        raise CertificateGenerationError("expected witness names are not unique")

    constraints: list[Constraint] = []
    for raw in constraints_value:
        if not isinstance(raw, Mapping) or set(raw) != {"relation", "coefficients", "constant"}:
            raise CertificateGenerationError("expected affine constraint is malformed")
        coefficients = raw["coefficients"]
        if not isinstance(coefficients, Mapping):
            raise CertificateGenerationError("expected affine coefficients are malformed")
        constraints.append(_constraint(
            str(raw["relation"]),
            Affine.make(
                {str(name): int(coefficient) for name, coefficient in coefficients.items()},
                int(raw["constant"]),
            ),
        ))
    if not constraints:
        raise CertificateGenerationError("expected theorem has no constraints")
    return witnesses, tuple(constraints)


def build_candidate_certificate(
    program: Program,
    expected_postcondition: Mapping[str, object],
    *,
    ghost_increments: tuple[int, ...],
) -> dict[str, object]:
    """Construct one complete generic certificate candidate for an exact K1 program."""

    cfg = control_flow_graph(program)
    header = int(cfg["loop_headers"][0])
    witnesses, postcondition = _requirement(expected_postcondition)
    ghost_count = len(ghost_increments)
    if not len(witnesses) <= ghost_count <= MAX_GHOST_COUNTERS:
        raise CertificateGenerationError("ghost policy cannot bind the required witnesses")
    if any(value not in (0, 1) for value in ghost_increments):
        raise CertificateGenerationError("ghost increments must be zero or one")
    ghosts = tuple(f"g{index}" for index in range(ghost_count))

    paths = _symbolic_paths(
        program,
        source="entry",
        start=0,
        stop_headers={header},
        initial_state=_initial_entry_state(ghosts),
    )
    paths.extend(_symbolic_paths(
        program,
        source=f"header:{header}",
        start=header,
        stop_headers={header},
        initial_state=_initial_header_state(ghosts),
    ))
    paths.sort(key=lambda item: item.path_id)

    updates = {
        path.path_id: _ghost_update(path, ghosts, ghost_increments) for path in paths
    }
    precondition = (_constraint("ge", Affine.variable("x")),)
    equalities = _derive_equalities(program, paths, ghosts, updates)
    inequalities = _derive_inequalities(
        program, paths, equalities, precondition, updates, ghosts,
    )
    invariants = tuple([*equalities, *inequalities][:MAX_CONSTRAINTS_PER_LOOP])
    if not invariants:
        raise CertificateGenerationError("no inductive invariant survived the bounded templates")

    statuses = _path_statuses(paths, precondition, invariants)
    if not any(
        statuses[path.path_id] == "feasible" and path.source == "entry"
        for path in paths
    ):
        raise CertificateGenerationError("certificate declares every entry path infeasible")
    if not any(
        statuses[path.path_id] == "feasible"
        and path.source.startswith("header:")
        and path.outcome == "halt"
        for path in paths
    ):
        raise CertificateGenerationError("certificate has no feasible loop exit")

    variant_data = _find_variant(
        program, paths, statuses, precondition, invariants, updates, header, ghosts,
    )
    if variant_data is None:
        raise CertificateGenerationError("no bounded affine variant survived")
    variant, decrease, initial_constant, initial_coefficient = variant_data

    witness_bindings = {name: ghosts[index] for index, name in enumerate(witnesses)}
    induction: list[dict[str, object]] = []
    for path in paths:
        premises = _path_premises(path, precondition, invariants)
        if statuses[path.path_id] == "infeasible":
            record = _obligation_record("infeasible", path, 0, premises, _false_constraint())
            if record is None:
                raise CertificateGenerationError("infeasible-path proof search failed")
            induction.append(record)
            continue

        final_state = _apply_update(path.state, updates[path.path_id])
        final_values = _source_values(final_state)
        if path.outcome == "header":
            if final_state.stack:
                raise CertificateGenerationError("loop path does not preserve the opaque frame")
            for index, invariant in enumerate(invariants):
                goal = _constraint(
                    invariant.relation, invariant.expression.substitute(final_values),
                )
                kind = "establish" if path.source == "entry" else "preserve"
                record = _obligation_record(kind, path, index, premises, goal)
                if record is None:
                    raise CertificateGenerationError("inductive proof search failed")
                induction.append(record)
        else:
            if len(final_state.stack) != 1:
                raise CertificateGenerationError("halt path does not leave exactly one output")
            post_values = {"x": Affine.variable("x"), "y": final_state.stack[0]}
            final_ghosts = final_state.ghost_map()
            post_values.update({
                name: final_ghosts[counter] for name, counter in witness_bindings.items()
            })
            for index, condition in enumerate(postcondition):
                goal = _constraint(
                    condition.relation, condition.expression.substitute(post_values),
                )
                record = _obligation_record("postcondition", path, index, premises, goal)
                if record is None:
                    raise CertificateGenerationError("postcondition proof search failed")
                induction.append(record)

    termination: list[dict[str, object]] = []
    synthetic = SymbolicPath(
        f"header-{header}", f"header:{header}", "header", header,
        (), (), (), _initial_header_state(ghosts),
    )
    record = _obligation_record(
        "variant_nonnegative", synthetic, 0, invariants, _constraint("ge", variant),
    )
    if record is None:
        raise CertificateGenerationError("variant non-negativity proof failed")
    termination.append(record)

    for path in paths:
        if (
            statuses[path.path_id] != "feasible"
            or path.source != f"header:{header}"
            or path.outcome != "header"
        ):
            continue
        final_state = _apply_update(path.state, updates[path.path_id])
        next_variant = variant.substitute(_source_values(final_state))
        goal = _constraint(
            "ge", variant - next_variant + Affine.make(constant=-decrease),
        )
        record = _obligation_record(
            "variant_decrease", path, 0,
            _path_premises(path, precondition, invariants), goal,
        )
        if record is None:
            raise CertificateGenerationError("variant decrease proof failed")
        termination.append(record)

    for path in paths:
        if (
            statuses[path.path_id] != "feasible"
            or path.source != "entry"
            or path.outcome != "header"
        ):
            continue
        final_state = _apply_update(path.state, updates[path.path_id])
        initial_variant = variant.substitute(_source_values(final_state))
        upper = Affine.make(
            {"x": initial_coefficient} if initial_coefficient else {}, initial_constant,
        )
        record = _obligation_record(
            "variant_initial_upper_bound", path, 0,
            _path_premises(path, precondition, invariants),
            _constraint("ge", upper - initial_variant),
        )
        if record is None:
            raise CertificateGenerationError("variant initial-bound proof failed")
        termination.append(record)

    feasible = [path for path in paths if statuses[path.path_id] == "feasible"]
    max_entry = max((
        len(path.pcs) for path in feasible
        if path.source == "entry" and path.outcome == "header"
    ), default=0)
    direct_bound = max((
        len(path.pcs) for path in feasible
        if path.source == "entry" and path.outcome == "halt"
    ), default=0)
    max_back = max((
        len(path.pcs) for path in feasible
        if path.source.startswith("header:") and path.outcome == "header"
    ), default=0)
    max_exit = max((
        len(path.pcs) for path in feasible
        if path.source.startswith("header:") and path.outcome == "halt"
    ), default=0)
    constant_bound = max(
        direct_bound,
        max_entry + max_back * initial_constant + max_exit,
    )
    coefficient_bound = max_back * initial_coefficient
    if constant_bound > FUEL_BASE or coefficient_bound > FUEL_SLOPE:
        raise CertificateGenerationError("proved step bound exceeds the frozen K1 fuel rule")

    return {
        "schema": CERTIFICATE_SCHEMA,
        "program_digest": program_digest(program),
        "precondition": {
            "schema": PRECONDITION_SCHEMA,
            "input_variable": "x",
            "constraints": [item.to_dict() for item in precondition],
            "register_initial_values": [0] * REGISTER_COUNT,
            "ghost_initial_values": {name: 0 for name in ghosts},
            "stack": "opaque_prefix_plus_x",
        },
        "control_flow_graph": cfg,
        "loop_invariants": [{
            "header": header,
            "constraints": [item.to_dict() for item in invariants],
        }],
        "well_founded_variants": [{
            "header": header,
            "expression": variant.to_dict(),
            "minimum_decrease": decrease,
        }],
        "inductive_steps": {
            "schema": INDUCTION_SCHEMA,
            "ghost_updates": [
                {
                    "path_id": path.path_id,
                    "assignments": {
                        name: expression.to_dict()
                        for name, expression in updates[path.path_id].items()
                    },
                }
                for path in paths
            ],
            "path_status": [
                {"path_id": path.path_id, "status": statuses[path.path_id]}
                for path in paths
            ],
            "obligations": induction,
        },
        "termination_argument": {
            "schema": TERMINATION_SCHEMA,
            "back_edges_break_all_cycles": True,
            "obligations": termination,
        },
        "linear_step_bound": {
            "schema": STEP_BOUND_SCHEMA,
            "constant": constant_bound,
            "x_coefficient": coefficient_bound,
            "variant_initial_bounds": [{
                "header": header,
                "constant": initial_constant,
                "x_coefficient": initial_coefficient,
            }],
            "max_entry_steps": max_entry,
            "max_back_edge_steps": max_back,
            "max_exit_steps": max_exit,
        },
        "postcondition": {
            "schema": POSTCONDITION_SCHEMA,
            "witness_bindings": witness_bindings,
            "constraints": copy.deepcopy(expected_postcondition["constraints"]),
        },
        "frame_condition": _frame((header,)),
    }


def generate_candidate_certificates(
    program: Program,
    expected_postcondition: Mapping[str, object],
    *,
    limit: int = 4096,
) -> Iterator[dict[str, object]]:
    """Yield complete certificate candidates in a fixed target-neutral ghost-policy order."""

    witnesses, _ = _requirement(expected_postcondition)
    if limit <= 0:
        return
    emitted = 0
    for ghost_count in range(len(witnesses), MAX_GHOST_COUNTERS + 1):
        for increments in itertools.product((0, 1), repeat=ghost_count):
            if witnesses and ghost_count and not any(increments):
                continue
            try:
                certificate = build_candidate_certificate(
                    program,
                    expected_postcondition,
                    ghost_increments=tuple(increments),
                )
            except CertificateGenerationError:
                continue
            yield certificate
            emitted += 1
            if emitted >= limit:
                return


__all__ = [
    "CertificateGenerationError",
    "build_candidate_certificate",
    "generate_candidate_certificates",
]
