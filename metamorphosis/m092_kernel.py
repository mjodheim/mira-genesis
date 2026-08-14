"""K1 — the fixed lower execution kernel. It knows no micro-operation and no primitive.

M090 moved the *language* into state and left a generic interpreter beneath it. M091 showed that
language could grow, and moved the ceiling to the assembly substrate — the micro-operations
themselves, which were still host Python: `run_body` branched on their names and `_binary` and
`_unary` were host functions with hard-coded arms.

This module is the machinery that replaces that authority. It is a register machine with a stack, a
slot array and an input array, and it branches on **nothing** that names a micro-operation. Whatever
program the serialized substrate state supplies for a dispatch key, this runs.

Three properties are deliberate, and the design audit fixed all three before this file existed.

* **Target-neutral.** The instruction set is arithmetic, data movement and conditional jumps. There
  is no modulo, no division, no parity, no comparison against a qualifying constant, no table and no
  host callback. K1 was selected in the audit as the smallest *audited* escape from the
  eventual-polynomial closure — see `experiments/M092/DESIGN_AUDIT.md`, gate 3. It was not designed
  around any target, and it is not claimed that iteration is universally forced.

* **Resource-bounded, by a rule fixed before any qualification exists.** Fuel is
  `FUEL_BASE + FUEL_SLOPE * magnitude`, a declared function of operand magnitude only. It is never
  derived from a target value or a qualifying world. For M092-A it is never binding, because every
  migrated program is loop-free — which `has_backward_jump` checks rather than assumes.

* **Authored, and therefore the next ceiling.** This instruction set, register model, numeric
  semantics, fuel rule, serialization and execution rules are ours. Moving micro-operation semantics
  into state does not make the machine underneath endogenous, and nothing in M092 may call this
  self-hosting or substrate independence.

K1 can physically execute richer programs than the inherited substrate needs. That is a property of
the *machine*, not of the registered substrate, and M092-A exists precisely to show the two do not
get confused: `can execute` is not `has registered`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m090_language import LanguageError

KERNEL_SCHEMA = "m092-k1-lower-kernel-v1"

REGISTER_COUNT = 8

# Resource guards. These are the kernel's own, distinct from any bound the language declares, and
# generous enough that no migrated program can reach them.
MAX_KERNEL_STACK = 64
MAX_PROGRAM_LENGTH = 64
FUEL_BASE = 256
FUEL_SLOPE = 4


class KernelError(LanguageError):
    """Raised when a K1 program refuses, faults or exhausts its resources.

    It subclasses `LanguageError` so that a refusal from state-owned execution is the same kind of
    event as a refusal from the frozen reference interpreter. Conservation compares refusals, and
    two different exception hierarchies would have made that comparison meaningless.
    """


# ---------------------------------------------------------------------------------------------
# The instruction set, frozen. Operand shapes are declared as data so a checker re-derives them.
# ---------------------------------------------------------------------------------------------

# opcode -> (operand roles). "r" = register index, "i" = immediate integer, "t" = jump target.
INSTRUCTION_SET: Mapping[str, tuple[str, ...]] = {
    "HALT": (),
    "FAIL": (),
    "LOADI": ("r", "i"),
    "MOV": ("r", "r"),
    "ADD": ("r", "r", "r"),
    "SUB": ("r", "r", "r"),
    "MUL": ("r", "r", "r"),
    "JMP": ("t",),
    "JZ": ("r", "t"),
    "JNZ": ("r", "t"),
    "JLT": ("r", "r", "t"),
    "ARG": ("r",),
    "SLEN": ("r",),
    "SPUSH": ("r",),
    "SPOP": ("r",),
    "SPEEK": ("r", "r"),
    "GETSLOT": ("r", "r"),
    "SETSLOT": ("r", "r"),
    "GETINPUT": ("r", "r"),
}

JUMP_OPCODES = ("JMP", "JZ", "JNZ", "JLT")

Instruction = tuple[object, ...]
Program = tuple[Instruction, ...]


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def program_to_list(program: Sequence[Instruction]) -> list[list[object]]:
    return [[str(step[0]), *[int(operand) for operand in step[1:]]] for step in program]


def program_from_list(data: Sequence[Sequence[object]]) -> Program:
    return tuple(
        (str(step[0]), *[int(operand) for operand in step[1:]]) for step in data
    )


def program_digest(program: Sequence[Instruction]) -> str:
    return hashlib.sha256(canonical_bytes(program_to_list(program))).hexdigest()


def validate_program(program: Sequence[Instruction]) -> None:
    """Structural validity, checked before execution and again by the checker.

    A malformed program must be refused rather than silently misinterpreted, because a substrate
    entry that decays into a no-op would look exactly like a successful migration of an operation
    that does nothing.
    """

    if not program:
        raise KernelError("a K1 program may not be empty")
    if len(program) > MAX_PROGRAM_LENGTH:
        raise KernelError("K1 program exceeds the frozen length bound")
    for index, step in enumerate(program):
        if not step:
            raise KernelError(f"instruction {index} is empty")
        opcode = step[0]
        roles = INSTRUCTION_SET.get(str(opcode))
        if roles is None:
            raise KernelError(f"unknown K1 opcode {opcode!r}")
        operands = step[1:]
        if len(operands) != len(roles):
            raise KernelError(f"{opcode} expects {len(roles)} operands, received {len(operands)}")
        for operand, role in zip(operands, roles, strict=True):
            if not isinstance(operand, int) or isinstance(operand, bool):
                raise KernelError(f"{opcode} operand {operand!r} is not an integer")
            if role == "r" and not 0 <= operand < REGISTER_COUNT:
                raise KernelError(f"{opcode} register operand {operand} is out of range")
            if role == "t" and not 0 <= operand < len(program):
                raise KernelError(f"{opcode} jump target {operand} is outside the program")


def has_backward_jump(program: Sequence[Instruction]) -> bool:
    """Whether the program can loop. Every M092-A program must be loop-free, and this proves it.

    A loop-free K1 program is straight-line code with forward branches. The design audit's K4 and
    K5 rows recorded that comparison, selection and straight-line arithmetic all stay inside the
    eventual-polynomial invariant, so a substrate whose every program is loop-free cannot have
    escaped it. That is the mechanical form of "M092-A adds no expressive reach".
    """

    for index, step in enumerate(program):
        if str(step[0]) in JUMP_OPCODES and int(step[-1]) <= index:
            return True
    return False


def default_fuel(inputs: Sequence[int], argument: int) -> int:
    """Fuel from operand magnitude alone. Never from a target value or a qualifying world."""

    magnitude = max((abs(int(value)) for value in inputs), default=0)
    return FUEL_BASE + FUEL_SLOPE * max(magnitude, abs(int(argument)))


# ---------------------------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------------------------


@dataclass
class Machine:
    """Everything a K1 program may read or write. There is no other channel.

    `stack`, `slots` and `inputs` are the substrate's working state; `argument` is the single
    resolved call-time operand. No filesystem, no network, no host callback, no import.
    """

    stack: list[int] = field(default_factory=list)
    slots: list[int] = field(default_factory=list)
    inputs: list[int] = field(default_factory=list)
    argument: int = 0
    registers: list[int] = field(default_factory=lambda: [0] * REGISTER_COUNT)
    steps: int = 0


def execute_program(
    program: Sequence[Instruction],
    machine: Machine,
    fuel: int | None = None,
    validate: bool = True,
) -> Machine:
    """Run one K1 program to `HALT`. Mutates and returns `machine`.

    The dispatch below is over K1 opcodes, which are the kernel's own vocabulary. It is **not** a
    dispatch over micro-operation identifiers: `PUSH_SLOT`, `BINOP` and `max` do not appear in this
    module, and the kernel cannot tell which substrate operation it is running.
    """

    if validate:
        validate_program(program)
    if fuel is None:
        fuel = default_fuel(machine.inputs, machine.argument)

    counter = 0
    while True:
        if machine.steps >= fuel:
            raise KernelError("K1 program exhausted its fuel")
        if not 0 <= counter < len(program):
            raise KernelError("K1 program ran off the end without halting")
        machine.steps += 1
        step = program[counter]
        opcode = str(step[0])
        operands = [int(operand) for operand in step[1:]]
        registers = machine.registers

        if opcode == "HALT":
            return machine
        if opcode == "FAIL":
            raise KernelError("K1 program executed FAIL")
        if opcode == "LOADI":
            registers[operands[0]] = operands[1]
        elif opcode == "MOV":
            registers[operands[0]] = registers[operands[1]]
        elif opcode == "ADD":
            registers[operands[0]] = registers[operands[1]] + registers[operands[2]]
        elif opcode == "SUB":
            registers[operands[0]] = registers[operands[1]] - registers[operands[2]]
        elif opcode == "MUL":
            registers[operands[0]] = registers[operands[1]] * registers[operands[2]]
        elif opcode == "JMP":
            counter = operands[0]
            continue
        elif opcode == "JZ":
            if registers[operands[0]] == 0:
                counter = operands[1]
                continue
        elif opcode == "JNZ":
            if registers[operands[0]] != 0:
                counter = operands[1]
                continue
        elif opcode == "JLT":
            if registers[operands[0]] < registers[operands[1]]:
                counter = operands[2]
                continue
        elif opcode == "ARG":
            registers[operands[0]] = machine.argument
        elif opcode == "SLEN":
            registers[operands[0]] = len(machine.stack)
        elif opcode == "SPUSH":
            if len(machine.stack) >= MAX_KERNEL_STACK:
                raise KernelError("K1 stack guard exceeded")
            machine.stack.append(registers[operands[0]])
        elif opcode == "SPOP":
            if not machine.stack:
                raise KernelError("SPOP on an empty stack")
            registers[operands[0]] = machine.stack.pop()
        elif opcode == "SPEEK":
            offset = registers[operands[1]]
            if not 0 <= offset < len(machine.stack):
                raise KernelError("SPEEK offset outside the stack")
            registers[operands[0]] = machine.stack[-1 - offset]
        elif opcode == "GETSLOT":
            index = registers[operands[1]]
            if not 0 <= index < len(machine.slots):
                raise KernelError("slot index out of range")
            registers[operands[0]] = machine.slots[index]
        elif opcode == "SETSLOT":
            index = registers[operands[0]]
            if not 0 <= index < len(machine.slots):
                raise KernelError("slot index out of range")
            machine.slots[index] = registers[operands[1]]
        elif opcode == "GETINPUT":
            index = registers[operands[1]]
            if not 0 <= index < len(machine.inputs):
                raise KernelError("input index out of range")
            registers[operands[0]] = machine.inputs[index]
        else:  # pragma: no cover - validate_program has already rejected this
            raise KernelError(f"unknown K1 opcode {opcode!r}")
        counter += 1


def kernel_manifest() -> dict[str, object]:
    """The kernel as an artifact a checker re-derives instead of trusting."""

    manifest: dict[str, object] = {
        "schema": KERNEL_SCHEMA,
        "register_count": REGISTER_COUNT,
        "max_kernel_stack": MAX_KERNEL_STACK,
        "max_program_length": MAX_PROGRAM_LENGTH,
        "fuel_rule": "FUEL_BASE + FUEL_SLOPE * max(|inputs|, |argument|)",
        "fuel_base": FUEL_BASE,
        "fuel_slope": FUEL_SLOPE,
        "instruction_set": {name: list(roles) for name, roles in INSTRUCTION_SET.items()},
        "jump_opcodes": list(JUMP_OPCODES),
        "numeric_semantics": "arbitrary-precision integers, no wraparound, no overflow",
        "contains_modulo_or_division": False,
        "contains_parity_operation": False,
        "contains_target_predicate": False,
        "contains_lookup_table": False,
        "contains_host_callback": False,
        "is_authored": True,
        "is_the_next_ceiling": True,
        "branches_on_micro_operation_identifiers": False,
    }
    manifest["digest"] = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    return manifest


__all__ = [
    "FUEL_BASE", "FUEL_SLOPE", "INSTRUCTION_SET", "JUMP_OPCODES", "KERNEL_SCHEMA",
    "MAX_KERNEL_STACK", "MAX_PROGRAM_LENGTH", "REGISTER_COUNT", "Instruction", "KernelError",
    "Machine", "Program", "canonical_bytes", "default_fuel", "execute_program", "has_backward_jump",
    "kernel_manifest", "program_digest", "program_from_list", "program_to_list", "validate_program",
]
