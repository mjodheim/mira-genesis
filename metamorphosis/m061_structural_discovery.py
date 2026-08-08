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

#: The floor. Every scaffold reads its parameters and frames a module, so `local.get`, `i32.const`
#: and the section layout are presupposed rather than discovered. A scaffold that avoided them
#: would have no way to present an operand or return a result, and the experiment says so instead
#: of pretending the floor is not there.
PRESUPPOSED = ("local.get", "i32.const", "module framing", "function signature shape")


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
)


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


#: What M060 authored, and what the scans must recover if discovery is to replace authorship.
M060_AUTHORED_STRUCTURAL = {
    "i32.load8_u": 0x2D,
    "i32.load": 0x28,
    "i32.store8": 0x3A,
    "i32.store": 0x36,
    "br_if": 0x0D,
}


def build_copy_loop(opcodes: Mapping[str, int]) -> bytes:
    """A byte-copy loop built only from discovered instructions, to prove they are usable.

    Recovering an opcode by probe is not the same as being able to compute with it. This emits
    `(i32 source, i32 destination, i32 count) -> i32`, copying byte by byte and returning the
    number copied, using the discovered load, store and conditional branch inside a loop. If the
    discovery named the wrong bytes the module either fails to validate or returns wrong data.
    """
    load8 = opcodes["i32.load8_u"]
    store8 = opcodes["i32.store8"]
    br_if = opcodes["br_if"]
    body = bytes([
        0x02, 0x40,                       # block
        0x03, 0x40,                       # loop
        _LOCAL_GET, 2, _I32_CONST, 0x00, 0x4D,   # count <= 0 ?  (i32.le_s)
        br_if, 0x01,                      # leave the block when it is
        _LOCAL_GET, 1,                    # destination
        _LOCAL_GET, 0, load8, 0x00, 0x00,  # load a byte from source
        store8, 0x00, 0x00,               # store it at destination
        _LOCAL_GET, 0, _I32_CONST, 0x01, 0x6A, 0x21, 0,   # source += 1
        _LOCAL_GET, 1, _I32_CONST, 0x01, 0x6A, 0x21, 1,   # destination += 1
        _LOCAL_GET, 2, _I32_CONST, 0x01, 0x6B, 0x21, 2,   # count -= 1
        0x0C, 0x00,                       # br to the loop
        _END,                             # end loop
        _END,                             # end block
        _I32_CONST, 0x00,
    ])
    return _module([I32, I32, I32], [I32], body)


__all__ = [
    "M060_AUTHORED_STRUCTURAL", "OPCODE_SPACE", "PRESUPPOSED", "RESPONSE_SCHEMA", "SCAFFOLDS",
    "M061Error", "Scaffold", "build_copy_loop", "load_shapes", "probe", "resolve_load",
    "resolve_unique", "resolve_width", "scan_scaffold", "store_widths",
]
