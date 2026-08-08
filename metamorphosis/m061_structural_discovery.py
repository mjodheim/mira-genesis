"""M061: discovering the instructions that move data and control, not only those that compute.

M058 scanned the opcode space for arithmetic and found nine operations, three of which no
authored list contained. M060 then migrated the whole body — and had to author every structural
instruction it used: loads, stores, branches, loops, calls, the memory layout. Its result named
that as the next thing to remove, and named why it is harder:

    A branch has no observable value to compare against, only an effect on what runs next.

The answer is to place the candidate in a scaffold whose **return value depends on its effect**.
A load is discovered by planting a known byte and seeing it come back. A store is discovered by
writing through the candidate and reading the cell afterwards. A conditional branch is discovered
by a body that returns one number when the branch is taken and another when it is not.

The scaffold shape is authored, exactly as M058's two-operand shape was. What is discovered is
which byte fills the hole.

Two things this scan must survive that M058's did not.

**Malformed scaffolds are silent.** A first attempt emitted the memory section before the function
section, which the format forbids, and the substrate refused all 256 candidates. "Nothing exists"
and "the instrument is broken" produce identical output. Every scaffold therefore declares a
witness it must find, and a scan that misses its witness disqualifies itself rather than
reporting a negative.

**Some candidates do not terminate.** `0x12` is a tail call; a scaffold calling its own function
through it recurses without growing the stack, so it never traps and never returns. `0x10`, an
ordinary call, exhausts the stack and traps instead — the two differ only in whether the loop is
observable. Termination is therefore a third outcome, enforced by running one candidate per
process under a timeout, because deciding it in general is not possible.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping, Sequence


class M061Error(ValueError):
    """Raised when an M061 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


RESPONSE_SCHEMA = "m061-node-response-v1"
OPCODE_SPACE = tuple(range(0x00, 0x100))

I32 = 0x7F
F64 = 0x7C
_LOCAL_GET = 0x20
_I32_CONST = 0x41
_END = 0x0B

#: The floor. Every scaffold reads its parameters and frames a module, so `local.get`, `i32.const`,
#: the `end` that closes every body and the section layout are presupposed rather than discovered.
#: A scaffold that avoided them would have no way to present an operand or return a result, and the
#: experiment says so instead of pretending the floor is not there.
PRESUPPOSED = (
    "local.get", "i32.const", "end 0x0b", "module framing", "function signature shape",
)


def _uleb(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _vec(items: Sequence[bytes]) -> bytes:
    return _uleb(len(items)) + b"".join(items)


def _section(identifier: int, payload: bytes) -> bytes:
    return bytes([identifier]) + _uleb(len(payload)) + payload


def _name(text: str) -> bytes:
    encoded = text.encode("utf-8")
    return _uleb(len(encoded)) + encoded


def _module(params: Sequence[int], results: Sequence[int], body: bytes,
            locals_: Sequence[int] = ()) -> bytes:
    """Frame one function as a module exporting `f` and its memory.

    Section order is 1, 3, 5, 7, 10 and the format enforces it. Emitting memory before function
    made the substrate refuse all 256 candidates, which reads exactly like a negative result.
    """
    signature = bytes([0x60]) + _vec([bytes([t]) for t in params]) + _vec([bytes([t]) for t in results])
    runs = _vec([_uleb(1) + bytes([t]) for t in locals_])
    inner = runs + body + bytes([_END])
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)]))
        + _section(5, _vec([bytes([0x00]) + _uleb(1)]))
        + _section(7, _vec([
            _name("f") + bytes([0x00]) + _uleb(0),
            _name("memory") + bytes([0x02]) + _uleb(0),
        ]))
        + _section(10, _vec([_uleb(len(inner)) + inner]))
    )


@dataclass(frozen=True)
class Scaffold:
    """A shape with one hole, and a witness that proves the shape itself works."""

    name: str
    witness: str
    calls: tuple[Mapping[str, object], ...]
    #: What a match must observe, or None when the scaffold characterises instead: several
    #: instructions can inhabit one shape and be told apart only by what they leave behind.
    expected: tuple[object, ...] | None
    build: object  # Callable[[int], bytes]

    def module_for(self, opcode: int) -> bytes:
        return self.build(opcode)


def _load_scaffold(opcode: int) -> bytes:
    """(i32 address) -> i32, body `local.get 0; OP align offset`."""
    return _module([I32], [I32], bytes([_LOCAL_GET, 0, opcode, 0x00, 0x00]))


def _store_scaffold(opcode: int) -> bytes:
    """(i32 address, i32 value) -> i32, body `local.get 0; local.get 1; OP align offset; i32.const 0`.

    The return value is a constant: what the candidate did is read out of memory afterwards, not
    returned. A store leaves no value on the stack, so there is nothing else to observe.
    """
    return _module(
        [I32, I32], [I32],
        bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, opcode, 0x00, 0x00, _I32_CONST, 0x00]),
    )


def _branch_scaffold(opcode: int) -> bytes:
    """(i32 condition) -> i32, returning 7 when the candidate branches and 9 when it does not.

    `block (result i32) { i32.const 7; local.get 0; OP 0; drop; i32.const 9 } end`
    A conditional branch consumes the condition and leaves 7; anything else falls through to 9.
    """
    body = bytes([
        0x02, I32,              # block (result i32)
        _I32_CONST, 7,
        _LOCAL_GET, 0,
        opcode, 0x00,           # candidate, with a label immediate
        0x1A,                   # drop
        _I32_CONST, 9,
        _END,
    ])
    return _module([I32], [I32], body)


#: Constants in a scaffold are emitted as one SLEB128 byte, where bit 0x40 is the sign. Anything
#: from 64 upward flips negative: an earlier version wrote 99 and the module returned -29, the
#: witness vanished, and the scan disqualified itself exactly as it should have. Every scaffold
#: constant stays below 64.
_SCAFFOLD_CONSTANT = 33


def _local_set_scaffold(add: int):
    """Build a shape that separates storing a value from discarding it and from leaving.

    Three candidates inhabit `local.get 0; OP 1; ...` and two earlier versions could not tell them
    apart. Ending on the constant made `local.set` and `drop` identical, because nothing ever read
    the local back. Ending on `local.get 1` made `local.set` and `return` identical, because both
    surface x.

    Reading the local *and* adding the constant separates all three: `local.set` yields 33+x,
    `drop` leaves the local at its default and yields 33, and `return` leaves with x before either
    happens. `local.tee` writes the local but also leaves x on the stack, so the body ends with two
    values against one declared result and the substrate refuses it outright.

    The addition is the operation the integer scan already recovered, so a discovery is what makes
    the next discovery possible rather than an authored constant.
    """
    def build(opcode: int) -> bytes:
        body = bytes([
            _LOCAL_GET, 0,
            opcode, 0x01,       # candidate, with a local index immediate
            _I32_CONST, _SCAFFOLD_CONSTANT,
            _LOCAL_GET, 1,
            add,
        ])
        return _module([I32], [I32], body, locals_=[I32])
    return build


def _unconditional_branch_scaffold(add: int):
    """Build a shape that separates a branch out of a block from a return out of the function.

    Both leave with 7, so an earlier version matched `br` and `return` alike. Adding one to the
    block's result distinguishes them: a branch lands after `end` and is incremented, a return
    never comes back. The increment uses the operation the integer scan already recovered, so a
    discovery is what makes the next discovery possible rather than an authored constant.
    """
    def build(opcode: int) -> bytes:
        body = bytes([
            0x02, I32,          # block (result i32)
            _I32_CONST, 7,
            opcode, 0x00,       # candidate, with a label immediate
            0x1A,               # drop
            _I32_CONST, 9,
            _END,
            _I32_CONST, 1, add,
        ])
        return _module([I32], [I32], body)
    return build


def _i32_binary_scaffold(opcode: int) -> bytes:
    """(i32, i32) -> i32, body `local.get 0; local.get 1; OP`. M058's shape, over integers."""
    return _module([I32, I32], [I32], bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, opcode]))


SCAFFOLDS: tuple[Scaffold, ...] = (
    Scaffold(
        name="memory_load",
        witness="0x2d",  # i32.load8_u
        # A four-byte pattern separates the load widths the way an overflowing value separates
        # the stores: one byte returns 0x44, two return 0x3344, four return 0x11223344.
        #
        # Width alone is not enough. On that pattern every byte is positive, so the signed and
        # unsigned one-byte loads return the same number and the scan refused to name either —
        # correctly. The second call plants a byte with the high bit set, where the unsigned form
        # returns 255 and the signed form returns -1. The probe was widened rather than the
        # resolver loosened.
        calls=({"args": [0], "memory": [[0, 0x44], [1, 0x33], [2, 0x22], [3, 0x11]]},
               {"args": [16], "memory": [[16, 0xFF], [17, 0x00], [18, 0x00], [19, 0x00]]}),
        expected=None,
        build=_load_scaffold,
    ),
    Scaffold(
        name="memory_store",
        witness="0x3a",  # i32.store8
        # A one-byte value cannot separate the stores: writing 0x5E at an address and reading
        # that address back looks identical for widths one, two and four. The probe writes a
        # value that overflows a byte and reads the neighbouring cells, so each width leaves a
        # different footprint and the scan characterises rather than merely matches.
        calls=({"args": [8, 0x11223344], "memory": [[8, 0], [9, 0], [10, 0], [11, 0]],
                "read": [8, 9, 10, 11]},),
        expected=None,
        build=_store_scaffold,
    ),
    Scaffold(
        name="conditional_branch",
        witness="0x0d",  # br_if
        calls=({"args": [1], "memory": []}, {"args": [0], "memory": []}),
        expected=(7, 9),
        build=_branch_scaffold,
    ),
    Scaffold(
        name="i32_binary",
        witness="0x6a",  # i32.add
        # Characterised, not matched: this one shape holds every integer binary operation, and
        # the arithmetic the copy loop needs is picked out of it afterwards by behaviour.
        calls=({"args": [12, 5], "memory": []}, {"args": [7, 7], "memory": []},
               {"args": [-8, 3], "memory": []}),
        expected=None,
        build=_i32_binary_scaffold,
    ),
)

#: What the copy loop needs from the integer shape, keyed by what each operation does. Resolved
#: against observations rather than written as opcodes.
I32_BINARY_NEEDED = {
    "i32.add": lambda a, b: a + b,
    "i32.sub": lambda a, b: a - b,
    "i32.le_s": lambda a, b: 1 if a <= b else 0,
}


#: The second stage. Both of these shapes need an operation the first stage recovered, so neither
#: can be scanned until the integer shape has been. Discovery bootstrapping discovery is the point:
#: the alternative was an authored opcode inside the scaffold that discovers opcodes.
def staged_scaffolds(add_opcode: int) -> tuple[Scaffold, ...]:
    return (
        Scaffold(
            name="local_set",
            witness="0x21",  # local.set
            calls=({"args": [41], "memory": []}, {"args": [-9], "memory": []}),
            expected=(_SCAFFOLD_CONSTANT + 41, _SCAFFOLD_CONSTANT - 9),
            build=_local_set_scaffold(add_opcode),
        ),
        Scaffold(
            name="unconditional_branch",
            witness="0x0c",  # br
            calls=({"args": [1], "memory": []}, {"args": [0], "memory": []}),
            expected=(8, 8),
            build=_unconditional_branch_scaffold(add_opcode),
        ),
    )


def _scaffold(name: str) -> Scaffold:
    """Look a shape up by name, so reordering the tuple cannot silently repoint a resolver."""
    for scaffold in SCAFFOLDS:
        if scaffold.name == name:
            return scaffold
    raise M061Error(f"no scaffold named {name}")


def resolve_i32_binary(scan: Mapping[str, object]) -> dict[str, int]:
    """Name the integer operations the loop needs, refusing where the probes do not separate."""
    resolved: dict[str, int] = {}
    calls = [call["args"] for call in _scaffold("i32_binary").calls]
    for label, function in I32_BINARY_NEEDED.items():
        expected = [function(a, b) for a, b in calls]
        matches = sorted(
            name for name, observations in scan["observations"].items()
            if list(observations) == expected
        )
        if len(matches) != 1:
            raise M061Error(f"{label} is not uniquely determined by the probes: {matches}")
        resolved[label] = int(matches[0], 16)
    return resolved


def _probe_script() -> Path:
    return Path(__file__).resolve().with_name("m061_structural_probe.mjs")


def probe(module: bytes, calls: Sequence[Mapping[str, object]], timeout_seconds: float) -> Mapping[str, object]:
    """Run one candidate in its own process. A candidate that does not return is not waited for."""
    request = json.dumps(
        {"wasm": base64.b64encode(module).decode("ascii"), "calls": list(calls)},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_probe_script())],
            input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"outcome": "did_not_terminate"}
    except OSError as exc:
        raise M061Error(f"Node runtime unavailable: {type(exc).__name__}") from exc
    if not completed.stdout:
        return {"outcome": "no_output"}
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"outcome": "malformed_output"}
    if response.get("schema") != RESPONSE_SCHEMA:
        raise M061Error("probe response identity mismatch")
    return response


def scan_scaffold(scaffold: Scaffold, timeout_seconds: float = 2.0) -> dict[str, object]:
    """Try every opcode in one shape, and refuse to report a result the witness contradicts."""
    outcomes: dict[str, str] = {}
    matches: list[str] = []
    observed: dict[str, object] = {}
    for opcode in OPCODE_SPACE:
        name = f"{opcode:#04x}"
        response = probe(scaffold.module_for(opcode), scaffold.calls, timeout_seconds)
        outcome = str(response.get("outcome"))
        outcomes[name] = outcome
        if outcome != "observed":
            continue
        observations = response.get("observations")
        observed[name] = observations
        if scaffold.expected is None:
            matches.append(name)
            continue
        if tuple(tuple(x) if isinstance(x, list) else x for x in observations) == tuple(
            tuple(x) if isinstance(x, list) else x for x in scaffold.expected
        ):
            matches.append(name)
    counts: dict[str, int] = {}
    for outcome in outcomes.values():
        counts[outcome] = counts.get(outcome, 0) + 1
    return {
        "scaffold": scaffold.name,
        "scanned": len(OPCODE_SPACE),
        "outcome_counts": counts,
        "observed_count": len(observed),
        "matches": sorted(matches),
        "observations": {name: observed[name] for name in sorted(matches)},
        # Every candidate that ran and returned, matching or not. The resolvers read `observations`
        # and must not see the near misses; showing what the rejected candidates did is how an
        # ambiguity can be argued about rather than merely asserted.
        "all_observations": {name: observed[name] for name in sorted(observed)},
        "witness": scaffold.witness,
        "witness_found": scaffold.witness in matches,
    }


def store_widths(scan: Mapping[str, object]) -> dict[str, int]:
    """How many bytes each candidate store actually wrote, from the footprint it left.

    Writing `0x11223344` and reading four cells separates the widths: a one-byte store leaves
    `44 00 00 00`, two bytes leave `44 33 00 00`, four leave `44 33 22 11`. Nothing here is told
    which opcode is which; the count of non-zero cells is what distinguishes them.
    """
    widths: dict[str, int] = {}
    for name, observations in scan["observations"].items():
        cells = observations[0]
        written = 0
        for index, value in enumerate(cells):
            if value != 0:
                written = index + 1
        widths[name] = written
    return widths


#: What a load of each width returns from the planted pattern `44 33 22 11`. Unsigned and signed
#: forms coincide here because every byte plants a positive value, which is deliberate: the scan
#: reports the ambiguity rather than resolving it by preferring one.
_LOAD_FOOTPRINTS = {0x44: 1, 0x3344: 2, 0x11223344: 4}


def load_shapes(scan: Mapping[str, object]) -> dict[str, tuple[int, bool]]:
    """Each candidate load as (bytes read, reads unsigned).

    The second observation plants `0xFF`: a candidate returning 255 widened it without a sign,
    one returning -1 carried the sign through. Candidates that read more than one byte see a
    zero-padded value and are reported unsigned, which is true of the pattern rather than of the
    instruction — the manifest says which observation each conclusion rests on.
    """
    shapes: dict[str, tuple[int, bool]] = {}
    for name, observations in scan["observations"].items():
        width = _LOAD_FOOTPRINTS.get(observations[0], 0)
        shapes[name] = (width, observations[1] >= 0)
    return shapes


def resolve_load(shapes: Mapping[str, tuple[int, bool]], width: int, unsigned: bool, label: str) -> str:
    """Take the one candidate of a given width and signedness, or refuse rather than pick."""
    matches = sorted(name for name, shape in shapes.items() if shape == (width, unsigned))
    if len(matches) != 1:
        raise M061Error(f"{label} is not uniquely determined: {matches}")
    return matches[0]


def resolve_width(widths: Mapping[str, int], width: int, label: str) -> str:
    """Take the one candidate of a given width, or refuse rather than pick."""
    matches = sorted(name for name, value in widths.items() if value == width)
    if len(matches) != 1:
        raise M061Error(f"{label} of width {width} is not uniquely determined: {matches}")
    return matches[0]


def resolve_unique(scan: Mapping[str, object], label: str) -> str:
    """Take the one candidate a scaffold matched, or refuse rather than pick."""
    if not scan["witness_found"]:
        raise M061Error(f"the {label} scaffold did not find its own witness; the instrument is suspect")
    matches = list(scan["matches"])
    if len(matches) != 1:
        raise M061Error(f"{label} is not uniquely determined by the probes: {matches}")
    return matches[0]


#: What M060 authored in its emitter, and what the scans must recover if discovery is to replace
#: authorship. Every entry is the byte `m060_wasm_emit` writes for that operation.
#:
#: `i32.le_s` is the one that repaid the exercise. M060 wrote `0x4c` and was right; the first M061
#: copy loop hardcoded `0x4d`, which is the *unsigned* comparison, and nothing caught it because
#: the loop's counter never goes negative. The scan named `0x4c` from behaviour and disagreed with
#: the authored code — the discovery found a defect in what it was meant to reproduce.
M060_AUTHORED_STRUCTURAL = {
    "i32.load8_u": 0x2D,
    "i32.load": 0x28,
    "i32.store8": 0x3A,
    "i32.store": 0x36,
    "br_if": 0x0D,
    "br": 0x0C,
    "local.set": 0x21,
    "i32.add": 0x6A,
    "i32.sub": 0x6B,
    "i32.le_s": 0x4C,
}

#: The shapes that cannot be scanned until the first stage has run, named without running it.
STAGED_SCAFFOLD_NAMES = ("local_set", "unconditional_branch")

#: The instructions the copy loop takes from discovery. Every one must be in the resolved mapping
#: before the loop is built, and the manifest reports this list against what remains authored.
LOOP_REQUIRED = (
    "i32.load8_u", "i32.store8", "br_if", "br", "local.set", "i32.add", "i32.sub", "i32.le_s",
)


#: Emitted by the loop and not recovered by any scaffold. `block` and `loop` are not instructions
#: with an observable effect on a value: they open a region and decide where a branch lands, and a
#: scaffold that used one to expose the other would be assuming what it set out to find. The
#: blocktype byte and the label immediates are part of the encoding rather than opcodes at all.
UNDISCOVERED_IN_LOOP = ("block 0x02", "loop 0x03", "blocktype byte", "label immediates")


def build_copy_loop(opcodes: Mapping[str, int]) -> bytes:
    """A byte-copy loop, to prove the recovered instructions are usable rather than merely named.

    Every opcode with an observable effect comes from `opcodes`: the load, the store, both
    branches, `local.set`, and the integer add, subtract and comparison. What remains written here
    is listed in `UNDISCOVERED_IN_LOOP` and in the manifest.

    An earlier version took only three opcodes from discovery and hardcoded seven more while the
    manifest claimed the loop used discovered instructions alone. That claim was false, and the
    fix was to discover the seven rather than to soften the wording.
    """
    missing = [label for label in LOOP_REQUIRED if label not in opcodes]
    if missing:
        raise M061Error(f"the loop cannot be built from discovery alone: {missing}")
    load8 = opcodes["i32.load8_u"]
    store8 = opcodes["i32.store8"]
    br_if = opcodes["br_if"]
    br = opcodes["br"]
    local_set = opcodes["local.set"]
    add = opcodes["i32.add"]
    sub = opcodes["i32.sub"]
    le_s = opcodes["i32.le_s"]
    body = bytes([
        0x02, 0x40,                                       # block   (not discovered)
        0x03, 0x40,                                       # loop    (not discovered)
        _LOCAL_GET, 2, _I32_CONST, 0x00, le_s,
        br_if, 0x01,
        _LOCAL_GET, 1,
        _LOCAL_GET, 0, load8, 0x00, 0x00,
        store8, 0x00, 0x00,
        _LOCAL_GET, 0, _I32_CONST, 0x01, add, local_set, 0,
        _LOCAL_GET, 1, _I32_CONST, 0x01, add, local_set, 1,
        _LOCAL_GET, 2, _I32_CONST, 0x01, sub, local_set, 2,
        br, 0x00,
        _END,
        _END,
        _I32_CONST, 0x00,
    ])
    return _module([I32, I32, I32], [I32], body)


__all__ = [
    "I32_BINARY_NEEDED", "LOOP_REQUIRED", "M060_AUTHORED_STRUCTURAL", "OPCODE_SPACE", "PRESUPPOSED",
    "RESPONSE_SCHEMA", "SCAFFOLDS", "STAGED_SCAFFOLD_NAMES", "UNDISCOVERED_IN_LOOP", "M061Error",
    "Scaffold", "build_copy_loop", "load_shapes", "probe", "resolve_i32_binary", "resolve_load",
    "resolve_unique", "resolve_width", "scan_scaffold", "staged_scaffolds", "store_widths",
]
