"""Deterministic, resumable program-space enumeration for M092-B.

This module is deliberately pre-search infrastructure.  It does not know a target postcondition,
does not execute K1 programs, does not construct a proof certificate and does not read qualification
material.  Its only job is to turn the frozen M092-B program grammar into a deterministic stream of
structurally typed proposals while committing every emitted record to an append-only digest chain.

Programs are breadth-first by total instruction count.  M092-P already proves that a loop-free K1
program cannot satisfy the global requirement, so the first-pass grammar emits exactly one
structured loop rather than spending the frozen cap on already-refuted straight-line programs.
Within one length, the frozen seed orders the layouts and typed instructions through
domain-separated SHA-256 keys.  Register names are alpha normalised by first occurrence: the input
stack value is placed in ``r0`` and a prefix may introduce only the next unused register.  This
removes register-renaming duplicates without changing the represented behaviours.

The stack contract supplies a target-neutral canonical frame: ``SPOP r0`` is the prologue and
``SPUSH r; HALT`` is the epilogue.  Between them, a normal form contains constant initialisation, a
conditional exit, one or more affine update instructions, one fixed back edge and optional exit
updates.  Programs outside this canonical first-pass grammar are not proved impossible; as frozen
by the protocol, bounded search failure is never an impossibility result.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator, Mapping, Sequence

from metamorphosis.m092_kernel import (
    INSTRUCTION_SET,
    JUMP_OPCODES,
    REGISTER_COUNT,
    Instruction,
    Program,
    program_digest,
    program_to_list,
    validate_program,
)
from metamorphosis.m092_runtime import canonical_bytes


SEARCH_SEED = 9202
CANDIDATE_CAP = 2_000_000
MAX_CANDIDATE_PROGRAM_LENGTH = 14
MIN_ITERATIVE_PROGRAM_LENGTH = 6
CANDIDATE_LITERALS = (-1, 0, 1)
CANDIDATE_ALLOWED_OPCODES = (
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
CANDIDATE_FORBIDDEN_OPCODES = (
    "FAIL",
    "ARG",
    "SLEN",
    "SPEEK",
    "GETSLOT",
    "SETSLOT",
    "GETINPUT",
)

CURSOR_SCHEMA = "m092-program-enumeration-cursor-v1"
RECORD_SCHEMA = "m092-program-enumeration-record-v1"
AUDIT_SCHEMA = "m092-program-enumeration-audit-v1"

_DATA_OPCODES = ("LOADI", "MOV", "ADD", "SUB", "MUL")
_GUARD_OPCODES = ("JZ", "JNZ", "JLT")
_GENESIS_DIGEST = "0" * 64


class SearchEnumerationError(ValueError):
    """The enumeration configuration, cursor or provenance chain is invalid."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _cursor_payload(
    *,
    seed: int,
    program_length: int,
    decision_path: Sequence[int],
    generated_programs: int,
    emitted_in_length: int,
    layer_quota: int,
) -> dict[str, object]:
    return {
        "schema": CURSOR_SCHEMA,
        "seed": seed,
        "program_length": program_length,
        "decision_path": list(decision_path),
        "generated_programs": generated_programs,
        "emitted_in_length": emitted_in_length,
        "layer_quota": layer_quota,
    }


@dataclass(frozen=True)
class EnumerationCursor:
    """Authenticated location immediately after one emitted raw proposal."""

    seed: int
    program_length: int
    decision_path: tuple[int, ...]
    generated_programs: int
    emitted_in_length: int
    layer_quota: int
    cursor_digest: str

    @classmethod
    def make(
        cls,
        *,
        seed: int,
        program_length: int,
        decision_path: Sequence[int],
        generated_programs: int,
        emitted_in_length: int,
        layer_quota: int,
    ) -> "EnumerationCursor":
        payload = _cursor_payload(
            seed=seed,
            program_length=program_length,
            decision_path=decision_path,
            generated_programs=generated_programs,
            emitted_in_length=emitted_in_length,
            layer_quota=layer_quota,
        )
        return cls(
            seed=seed,
            program_length=program_length,
            decision_path=tuple(int(value) for value in decision_path),
            generated_programs=generated_programs,
            emitted_in_length=emitted_in_length,
            layer_quota=layer_quota,
            cursor_digest=_sha256(payload),
        )

    def to_dict(self) -> dict[str, object]:
        payload = _cursor_payload(
            seed=self.seed,
            program_length=self.program_length,
            decision_path=self.decision_path,
            generated_programs=self.generated_programs,
            emitted_in_length=self.emitted_in_length,
            layer_quota=self.layer_quota,
        )
        payload["cursor_digest"] = self.cursor_digest
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "EnumerationCursor":
        expected_fields = {
            "schema", "seed", "program_length", "decision_path",
            "generated_programs", "emitted_in_length", "layer_quota", "cursor_digest",
        }
        if set(value) != expected_fields or value.get("schema") != CURSOR_SCHEMA:
            raise SearchEnumerationError("cursor schema or fields differ")
        path_value = value.get("decision_path")
        if not isinstance(path_value, list) or any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0
            for item in path_value
        ):
            raise SearchEnumerationError("cursor decision path is malformed")
        integers = {
            name: value.get(name)
            for name in (
                "seed", "program_length", "generated_programs",
                "emitted_in_length", "layer_quota",
            )
        }
        if any(
            not isinstance(item, int) or isinstance(item, bool)
            for item in integers.values()
        ):
            raise SearchEnumerationError("cursor integer field is malformed")
        cursor = cls.make(
            seed=int(integers["seed"]),
            program_length=int(integers["program_length"]),
            decision_path=path_value,
            generated_programs=int(integers["generated_programs"]),
            emitted_in_length=int(integers["emitted_in_length"]),
            layer_quota=int(integers["layer_quota"]),
        )
        if value.get("cursor_digest") != cursor.cursor_digest:
            raise SearchEnumerationError("cursor digest differs")
        cursor._validate_bounds()
        return cursor

    def _validate_bounds(self) -> None:
        if self.seed != SEARCH_SEED:
            raise SearchEnumerationError("cursor seed differs from the frozen seed")
        if not MIN_ITERATIVE_PROGRAM_LENGTH <= self.program_length <= MAX_CANDIDATE_PROGRAM_LENGTH:
            raise SearchEnumerationError("cursor program length is outside the frozen bound")
        if len(self.decision_path) != self.program_length - 2:
            raise SearchEnumerationError("cursor decision path has the wrong length")
        if not 0 <= self.generated_programs <= CANDIDATE_CAP:
            raise SearchEnumerationError("cursor generated count is outside the frozen cap")
        if not 1 <= self.emitted_in_length <= self.layer_quota <= CANDIDATE_CAP:
            raise SearchEnumerationError("cursor layer counters are inconsistent")


@dataclass(frozen=True)
class EnumerationRecord:
    """One raw canonical proposal and its target-independent structural classification."""

    ordinal: int
    program: Program
    program_digest: str
    program_length: int
    loop_headers: tuple[int, ...]
    structurally_valid: bool
    structural_refusals: tuple[str, ...]
    cursor: EnumerationCursor

    def event(self) -> dict[str, object]:
        return {
            "schema": RECORD_SCHEMA,
            "ordinal": self.ordinal,
            "program": program_to_list(self.program),
            "program_digest": self.program_digest,
            "program_length": self.program_length,
            "loop_headers": list(self.loop_headers),
            "structurally_valid": self.structurally_valid,
            "structural_refusals": list(self.structural_refusals),
            "cursor_digest": self.cursor.cursor_digest,
        }


@dataclass(frozen=True)
class EnumerationAudit:
    """Compact commitment to an ordered prefix of the raw proposal stream."""

    generated_programs: int = 0
    structurally_invalid_programs: int = 0
    last_program_digest: str | None = None
    last_cursor: EnumerationCursor | None = None
    event_chain_digest: str = _GENESIS_DIGEST

    def append(self, record: EnumerationRecord) -> "EnumerationAudit":
        if record.ordinal != self.generated_programs + 1:
            raise SearchEnumerationError("enumeration record is not the next ordinal")
        record.cursor._validate_bounds()
        EnumerationCursor.from_dict(record.cursor.to_dict())
        if record.cursor.generated_programs != record.ordinal:
            raise SearchEnumerationError("enumeration record and cursor ordinals differ")
        if record.program_length != len(record.program):
            raise SearchEnumerationError("enumeration record program length differs")
        if record.program_digest != program_digest(record.program):
            raise SearchEnumerationError("enumeration record program digest differs")
        headers, refusals = _classify(record.program)
        if (
            record.loop_headers != headers
            or record.structural_refusals != refusals
            or record.structurally_valid != (not refusals)
        ):
            raise SearchEnumerationError("enumeration record classification differs")
        if self.last_cursor is not None:
            if record.cursor.generated_programs != self.last_cursor.generated_programs + 1:
                raise SearchEnumerationError("enumeration cursor count is discontinuous")
        elif record.cursor.generated_programs != 1:
            raise SearchEnumerationError("first enumeration cursor must have count one")
        chain = _sha256({
            "previous_event_chain_digest": self.event_chain_digest,
            "event": record.event(),
        })
        return EnumerationAudit(
            generated_programs=record.ordinal,
            structurally_invalid_programs=(
                self.structurally_invalid_programs + (not record.structurally_valid)
            ),
            last_program_digest=record.program_digest,
            last_cursor=record.cursor,
            event_chain_digest=chain,
        )

    def to_dict(self) -> dict[str, object]:
        payload = {
            "schema": AUDIT_SCHEMA,
            "seed": SEARCH_SEED,
            "candidate_cap": CANDIDATE_CAP,
            "max_program_length": MAX_CANDIDATE_PROGRAM_LENGTH,
            "layer_plan": [layer.to_dict() for layer in search_layer_plan()],
            "generated_programs": self.generated_programs,
            "structurally_invalid_programs": self.structurally_invalid_programs,
            "last_program_digest": self.last_program_digest,
            "last_cursor": None if self.last_cursor is None else self.last_cursor.to_dict(),
            "event_chain_digest": self.event_chain_digest,
            "target_postcondition_loaded": False,
            "candidate_executed": False,
            "qualification_loaded": False,
        }
        payload["audit_digest"] = _sha256(payload)
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "EnumerationAudit":
        expected_fields = {
            "schema", "seed", "candidate_cap", "max_program_length",
            "layer_plan",
            "generated_programs", "structurally_invalid_programs",
            "last_program_digest", "last_cursor", "event_chain_digest",
            "target_postcondition_loaded", "candidate_executed", "qualification_loaded",
            "audit_digest",
        }
        if set(value) != expected_fields or value.get("schema") != AUDIT_SCHEMA:
            raise SearchEnumerationError("audit schema or fields differ")
        if value.get("seed") != SEARCH_SEED:
            raise SearchEnumerationError("audit seed differs from the frozen seed")
        if value.get("candidate_cap") != CANDIDATE_CAP:
            raise SearchEnumerationError("audit candidate cap differs")
        if value.get("max_program_length") != MAX_CANDIDATE_PROGRAM_LENGTH:
            raise SearchEnumerationError("audit program-length bound differs")
        if value.get("layer_plan") != [layer.to_dict() for layer in search_layer_plan()]:
            raise SearchEnumerationError("audit layer plan differs from the frozen plan")
        if any(value.get(name) is not False for name in (
            "target_postcondition_loaded", "candidate_executed", "qualification_loaded",
        )):
            raise SearchEnumerationError("pre-search audit declares a forbidden action")
        generated = value.get("generated_programs")
        invalid = value.get("structurally_invalid_programs")
        if any(
            not isinstance(item, int) or isinstance(item, bool)
            for item in (generated, invalid)
        ):
            raise SearchEnumerationError("audit counter is malformed")
        generated = int(generated)
        invalid = int(invalid)
        if not 0 <= invalid <= generated <= CANDIDATE_CAP:
            raise SearchEnumerationError("audit counters are inconsistent")
        last_digest = value.get("last_program_digest")
        cursor_value = value.get("last_cursor")
        if generated == 0:
            if last_digest is not None or cursor_value is not None:
                raise SearchEnumerationError("empty audit carries a last proposal")
            cursor = None
        else:
            if not _is_digest(last_digest):
                raise SearchEnumerationError("audit last program digest is malformed")
            if not isinstance(cursor_value, Mapping):
                raise SearchEnumerationError("non-empty audit lacks a cursor")
            cursor = EnumerationCursor.from_dict(cursor_value)
            if cursor.generated_programs != generated:
                raise SearchEnumerationError("audit and cursor counts differ")
        chain = value.get("event_chain_digest")
        if not _is_digest(chain):
            raise SearchEnumerationError("audit event-chain digest is malformed")
        if generated == 0 and chain != _GENESIS_DIGEST:
            raise SearchEnumerationError("empty audit has a non-genesis event chain")
        payload = dict(value)
        supplied_digest = payload.pop("audit_digest")
        if supplied_digest != _sha256(payload):
            raise SearchEnumerationError("audit digest differs")
        return cls(
            generated_programs=generated,
            structurally_invalid_programs=invalid,
            last_program_digest=last_digest,
            last_cursor=cursor,
            event_chain_digest=chain,
        )


def _seeded_key(
    value: Instruction,
    *,
    seed: int,
    program_length: int,
    position: int,
    register_frontier: int,
) -> tuple[str, bytes]:
    payload = {
        "domain": "m092-typed-breadth-first-instruction-order-v1",
        "seed": seed,
        "program_length": program_length,
        "position": position,
        "register_frontier": register_frontier,
        "instruction": list(value),
    }
    encoded = canonical_bytes(payload)
    return hashlib.sha256(encoded).hexdigest(), encoded


def _layout_key(
    layout: tuple[int, int, int], *, seed: int, program_length: int,
) -> tuple[str, bytes]:
    payload = {
        "domain": "m092-typed-breadth-first-layout-order-v1",
        "seed": seed,
        "program_length": program_length,
        "prelude_instructions": layout[0],
        "loop_update_instructions": layout[1],
        "exit_instructions": layout[2],
    }
    encoded = canonical_bytes(payload)
    return hashlib.sha256(encoded).hexdigest(), encoded


def _register_tuples(role_count: int, frontier: int) -> Iterator[tuple[tuple[int, ...], int]]:
    """Yield restricted-growth register tuples and their resulting frontier."""

    def visit(prefix: tuple[int, ...], current: int) -> Iterator[tuple[tuple[int, ...], int]]:
        if len(prefix) == role_count:
            yield prefix, current
            return
        maximum = min(current + 1, REGISTER_COUNT - 1)
        for register in range(maximum + 1):
            yield from visit(prefix + (register,), max(current, register))

    yield from visit((), frontier)


@lru_cache(maxsize=None)
def _typed_instruction_options(
    *,
    opcodes: tuple[str, ...],
    program_length: int,
    position: int,
    register_frontier: int,
    seed: int,
    jump_targets: tuple[int, ...] = (),
) -> tuple[tuple[Instruction, int], ...]:
    options: list[tuple[Instruction, int]] = []
    for opcode in opcodes:
        roles = INSTRUCTION_SET[opcode]
        register_count = roles.count("r")
        for registers, next_frontier in _register_tuples(register_count, register_frontier):
            register_index = 0
            partial: list[tuple[tuple[object, ...], int]] = [((opcode,), next_frontier)]
            for role in roles:
                expanded: list[tuple[tuple[object, ...], int]] = []
                if role == "r":
                    operand_values = (registers[register_index],)
                    register_index += 1
                elif role == "i":
                    operand_values = CANDIDATE_LITERALS
                elif role == "t":
                    operand_values = tuple(jump_targets)
                    if not operand_values:
                        raise SearchEnumerationError("jump instruction lacks a typed target")
                else:  # pragma: no cover - the frozen K1 manifest is checked by tests.
                    raise SearchEnumerationError(f"unknown operand role {role!r}")
                for instruction, frontier_value in partial:
                    for operand in operand_values:
                        expanded.append((instruction + (operand,), frontier_value))
                partial = expanded
            options.extend(partial)
    options.sort(key=lambda item: _seeded_key(
        item[0],
        seed=seed,
        program_length=program_length,
        position=position,
        register_frontier=register_frontier,
    ))
    return tuple(options)


@lru_cache(maxsize=None)
def _frontier_transitions(
    opcodes: tuple[str, ...], register_frontier: int, jump_target_count: int,
) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for opcode in opcodes:
        roles = INSTRUCTION_SET[opcode]
        multiplier = 1
        for role in roles:
            if role == "i":
                multiplier *= len(CANDIDATE_LITERALS)
            elif role == "t":
                multiplier *= jump_target_count
        for _, next_frontier in _register_tuples(roles.count("r"), register_frontier):
            counts[next_frontier] = counts.get(next_frontier, 0) + multiplier
    return tuple(sorted(counts.items()))


@lru_cache(maxsize=None)
def canonical_layer_cardinality(program_length: int) -> int:
    """Count the structured alpha-normalised programs at one length without enumerating them."""

    if not MIN_ITERATIVE_PROGRAM_LENGTH <= program_length <= MAX_CANDIDATE_PROGRAM_LENGTH:
        raise SearchEnumerationError("program length is outside the iterative grammar")
    flexible_instructions = program_length - 5
    total = 0
    for prelude in range(flexible_instructions):
        for updates in range(1, flexible_instructions - prelude + 1):
            exits = flexible_instructions - prelude - updates
            stage_kinds = [(("LOADI",), 0)] * prelude
            stage_kinds.append((_GUARD_OPCODES, 1))
            stage_kinds.extend([(_DATA_OPCODES, 0)] * updates)
            stage_kinds.extend([(_DATA_OPCODES, 0)] * exits)
            states: dict[int, int] = {0: 1}
            for opcodes, target_count in stage_kinds:
                next_states: dict[int, int] = {}
                for frontier, count in states.items():
                    for next_frontier, multiplicity in _frontier_transitions(
                        opcodes, frontier, target_count,
                    ):
                        next_states[next_frontier] = (
                            next_states.get(next_frontier, 0) + count * multiplicity
                        )
                states = next_states
            total += sum(count * (frontier + 1) for frontier, count in states.items())
    return total


@dataclass(frozen=True)
class LayerBudget:
    """Target-neutral allocation of the frozen cap across remaining breadth layers."""

    program_length: int
    canonical_programs: int
    quota: int
    emitted_programs: int
    truncated: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "program_length": self.program_length,
            "canonical_programs": self.canonical_programs,
            "quota": self.quota,
            "emitted_programs": self.emitted_programs,
            "truncated": self.truncated,
        }


@lru_cache(maxsize=1)
def search_layer_plan() -> tuple[LayerBudget, ...]:
    """Distribute the cap without letting a short combinatorial layer consume every proposal."""

    remaining_budget = CANDIDATE_CAP
    plan: list[LayerBudget] = []
    for program_length in range(
        MIN_ITERATIVE_PROGRAM_LENGTH, MAX_CANDIDATE_PROGRAM_LENGTH + 1,
    ):
        remaining_layers = MAX_CANDIDATE_PROGRAM_LENGTH - program_length + 1
        quota = (remaining_budget + remaining_layers - 1) // remaining_layers
        cardinality = canonical_layer_cardinality(program_length)
        emitted = min(cardinality, quota)
        plan.append(LayerBudget(
            program_length=program_length,
            canonical_programs=cardinality,
            quota=quota,
            emitted_programs=emitted,
            truncated=emitted < cardinality,
        ))
        remaining_budget -= emitted
    if remaining_budget != 0:
        raise SearchEnumerationError("layer plan does not consume the frozen candidate cap")
    return tuple(plan)


def _loop_headers(program: Sequence[Instruction]) -> tuple[int, ...]:
    return tuple(sorted({
        int(step[-1])
        for index, step in enumerate(program)
        if str(step[0]) in JUMP_OPCODES and int(step[-1]) <= index
    }))


def _reachable_indices(program: Sequence[Instruction]) -> set[int]:
    pending = [0]
    reached: set[int] = set()
    while pending:
        index = pending.pop()
        if index in reached or not 0 <= index < len(program):
            continue
        reached.add(index)
        opcode = str(program[index][0])
        if opcode == "HALT":
            continue
        if opcode == "JMP":
            pending.append(int(program[index][-1]))
            continue
        if opcode in {"JZ", "JNZ", "JLT"}:
            pending.append(int(program[index][-1]))
        pending.append(index + 1)
    return reached


def _frame_refusals(program: Sequence[Instruction]) -> set[str]:
    """Explore the finite (pc, relative-depth) frame abstraction without executing K1."""

    pending = [(0, 1)]
    reached: set[tuple[int, int]] = set()
    refusals: set[str] = set()
    while pending:
        index, depth = pending.pop()
        state = (index, depth)
        if state in reached:
            continue
        reached.add(state)
        if not 0 <= index < len(program):
            refusals.add("control_flow_runs_off_program")
            continue
        step = program[index]
        opcode = str(step[0])
        next_depth = depth
        if opcode == "SPOP":
            next_depth -= 1
        elif opcode == "SPUSH":
            next_depth += 1
        if next_depth < 0:
            refusals.add("stack_prefix_may_be_popped")
            continue
        if next_depth > 1:
            refusals.add("stack_may_grow_above_entry_depth")
            continue
        if opcode == "HALT":
            if next_depth != 1:
                refusals.add("halt_stack_effect_differs")
            continue
        successors = []
        if opcode == "JMP":
            successors.append(int(step[-1]))
        else:
            successors.append(index + 1)
            if opcode in {"JZ", "JNZ", "JLT"}:
                successors.append(int(step[-1]))
        pending.extend((successor, next_depth) for successor in successors)
    return refusals


def _classify(program: Program) -> tuple[tuple[int, ...], tuple[str, ...]]:
    validate_program(program)
    refusals = _frame_refusals(program)
    reached = _reachable_indices(program)
    if reached != set(range(len(program))):
        refusals.add("unreachable_instruction")
    headers = _loop_headers(program)
    if len(headers) > 1:
        refusals.add("multiple_loop_headers")
    return headers, tuple(sorted(refusals))


def _iter_length(
    program_length: int,
    *,
    seed: int,
    resume_path: tuple[int, ...] | None,
) -> Iterator[tuple[Program, tuple[int, ...]]]:
    flexible_instructions = program_length - 5
    layouts = [
        (prelude, updates, flexible_instructions - prelude - updates)
        for prelude in range(flexible_instructions)
        for updates in range(1, flexible_instructions - prelude + 1)
    ]
    layouts.sort(key=lambda layout: _layout_key(
        layout, seed=seed, program_length=program_length,
    ))
    if resume_path is not None and len(resume_path) != program_length - 2:
        raise SearchEnumerationError("cursor path length differs during resume")
    layout_start = 0 if resume_path is None else resume_path[0]
    if layout_start >= len(layouts):
        raise SearchEnumerationError("cursor layout is outside the typed option set")

    for layout_index in range(layout_start, len(layouts)):
        prelude_count, update_count, exit_count = layouts[layout_index]
        header = 1 + prelude_count
        back_jump_index = header + 1 + update_count
        exit_start = back_jump_index + 1
        stage_specs: list[tuple[int, tuple[str, ...], tuple[int, ...]]] = []
        stage_specs.extend(
            (position, ("LOADI",), ())
            for position in range(1, header)
        )
        stage_specs.append((header, _GUARD_OPCODES, (exit_start,)))
        stage_specs.extend(
            (position, _DATA_OPCODES, ())
            for position in range(header + 1, back_jump_index)
        )
        stage_specs.extend(
            (position, _DATA_OPCODES, ())
            for position in range(exit_start, exit_start + exit_count)
        )
        follows_layout_cursor = resume_path is not None and layout_index == layout_start

        def visit(
            stages: tuple[Instruction, ...],
            frontier: int,
            decisions: tuple[int, ...],
            still_resuming: bool,
        ) -> Iterator[tuple[Program, tuple[int, ...]]]:
            stage_index = len(stages)
            if stage_index == len(stage_specs):
                outputs = list(range(frontier + 1))
                outputs.sort(key=lambda register: _seeded_key(
                    ("SPUSH", register),
                    seed=seed,
                    program_length=program_length,
                    position=program_length - 2,
                    register_frontier=frontier,
                ))
                output_start = 0
                if still_resuming and resume_path is not None:
                    output_start = resume_path[-1] + 1
                for output_index in range(output_start, len(outputs)):
                    prelude = stages[:prelude_count]
                    guard = stages[prelude_count]
                    update_end = prelude_count + 1 + update_count
                    updates = stages[prelude_count + 1:update_end]
                    exits = stages[update_end:]
                    program: Program = (
                        ("SPOP", 0),
                        *prelude,
                        guard,
                        *updates,
                        ("JMP", header),
                        *exits,
                        ("SPUSH", outputs[output_index]),
                        ("HALT",),
                    )
                    if len(program) != program_length:
                        raise SearchEnumerationError("typed layout produced the wrong length")
                    yield program, decisions + (output_index,)
                return

            position, opcodes, targets = stage_specs[stage_index]
            options = _typed_instruction_options(
                opcodes=opcodes,
                program_length=program_length,
                position=position,
                register_frontier=frontier,
                seed=seed,
                jump_targets=targets,
            )
            option_start = 0
            if still_resuming and resume_path is not None:
                option_start = resume_path[stage_index + 1]
                if option_start >= len(options):
                    raise SearchEnumerationError(
                        "cursor decision is outside the typed option set"
                    )
            for option_index in range(option_start, len(options)):
                instruction, next_frontier = options[option_index]
                follows_option_cursor = still_resuming and option_index == option_start
                yield from visit(
                    stages + (instruction,),
                    next_frontier,
                    decisions + (option_index,),
                    follows_option_cursor,
                )

        yield from visit(
            (), 0, (layout_index,), follows_layout_cursor,
        )


def enumerate_programs(
    *,
    limit: int,
    cursor: EnumerationCursor | Mapping[str, object] | None = None,
) -> Iterator[EnumerationRecord]:
    """Yield at most ``limit`` new raw proposals after an authenticated cursor.

    The global frozen cap counts raw emitted programs, including target-independent structural
    refusals.  No candidate is executed and no semantic success criterion is accepted here.
    """

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise SearchEnumerationError("enumeration limit must be a non-negative integer")
    if isinstance(cursor, Mapping):
        cursor = EnumerationCursor.from_dict(cursor)
    if cursor is not None:
        cursor._validate_bounds()
    generated = 0 if cursor is None else cursor.generated_programs
    if generated + limit > CANDIDATE_CAP:
        raise SearchEnumerationError("enumeration request exceeds the frozen candidate cap")
    remaining = limit
    start_length = MIN_ITERATIVE_PROGRAM_LENGTH if cursor is None else cursor.program_length
    plan = search_layer_plan()
    plan_by_length = {layer.program_length: layer for layer in plan}
    if cursor is not None:
        layer = plan_by_length[cursor.program_length]
        generated_before_layer = sum(
            item.emitted_programs
            for item in plan
            if item.program_length < cursor.program_length
        )
        if cursor.layer_quota != layer.quota:
            raise SearchEnumerationError("cursor layer quota differs from the frozen plan")
        if cursor.emitted_in_length > layer.emitted_programs:
            raise SearchEnumerationError("cursor exceeds the frozen layer allocation")
        if cursor.generated_programs != generated_before_layer + cursor.emitted_in_length:
            raise SearchEnumerationError("cursor global and layer counts differ")
    for program_length in range(start_length, MAX_CANDIDATE_PROGRAM_LENGTH + 1):
        layer = plan_by_length[program_length]
        emitted_in_length = (
            cursor.emitted_in_length
            if cursor is not None and program_length == cursor.program_length
            else 0
        )
        if emitted_in_length == layer.emitted_programs:
            cursor = None
            continue
        resume_path = (
            cursor.decision_path
            if cursor is not None and program_length == cursor.program_length
            else None
        )
        for program, decision_path in _iter_length(
            program_length, seed=SEARCH_SEED, resume_path=resume_path,
        ):
            if remaining == 0:
                return
            if emitted_in_length == layer.emitted_programs:
                break
            generated += 1
            emitted_in_length += 1
            remaining -= 1
            headers, refusals = _classify(program)
            next_cursor = EnumerationCursor.make(
                seed=SEARCH_SEED,
                program_length=program_length,
                decision_path=decision_path,
                generated_programs=generated,
                emitted_in_length=emitted_in_length,
                layer_quota=layer.quota,
            )
            yield EnumerationRecord(
                ordinal=generated,
                program=program,
                program_digest=program_digest(program),
                program_length=program_length,
                loop_headers=headers,
                structurally_valid=not refusals,
                structural_refusals=refusals,
                cursor=next_cursor,
            )
        cursor = None


def audit_prefix(
    *,
    limit: int,
    cursor: EnumerationCursor | Mapping[str, object] | None = None,
    audit: EnumerationAudit | None = None,
) -> EnumerationAudit:
    """Commit an enumerated prefix to an order-sensitive digest chain."""

    if audit is None:
        if cursor is not None:
            raise SearchEnumerationError("resumed enumeration requires the prior audit")
        audit = EnumerationAudit()
    elif cursor is None or audit.last_cursor != (
        EnumerationCursor.from_dict(cursor) if isinstance(cursor, Mapping) else cursor
    ):
        raise SearchEnumerationError("audit and resume cursor differ")
    for record in enumerate_programs(limit=limit, cursor=cursor):
        audit = audit.append(record)
    return audit


__all__ = [
    "AUDIT_SCHEMA",
    "CANDIDATE_ALLOWED_OPCODES",
    "CANDIDATE_CAP",
    "CANDIDATE_FORBIDDEN_OPCODES",
    "CANDIDATE_LITERALS",
    "CURSOR_SCHEMA",
    "EnumerationAudit",
    "EnumerationCursor",
    "EnumerationRecord",
    "LayerBudget",
    "MAX_CANDIDATE_PROGRAM_LENGTH",
    "MIN_ITERATIVE_PROGRAM_LENGTH",
    "RECORD_SCHEMA",
    "SEARCH_SEED",
    "SearchEnumerationError",
    "audit_prefix",
    "canonical_layer_cardinality",
    "enumerate_programs",
    "search_layer_plan",
]
