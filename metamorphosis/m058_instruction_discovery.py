"""M058: the lineage discovers which instructions exist, not only what they do.

M057 removed the authored compiler but kept an authored list. Six handles were exposed, and the
lineage discovered their semantics by probing. Its result named the remaining boundary:

    The set of available operations remains authored by a human. What the lineage discovers is
    what they do and how to build its tools from them.

M058 removes the list. The lineage is told only the *shape* it needs — a function taking two
`f64` values and returning one — and then asks the substrate, byte by byte, which candidates are
operations at all. What validates exists; what fails validation does not.

That question is answered by the substrate's own validator, not by a table. The lineage does not
know in advance how many operations it will find, nor which bytes they occupy.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import struct
from typing import Mapping, Sequence


class M058Error(ValueError):
    """Raised when an M058 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


F64 = 0x7C
_LOCAL_GET = 0x20
_F64_CONST = 0x44
_END = 0x0B

#: Every single-byte opcode is a candidate. The lineage scans the whole space; nothing narrows
#: it in advance, and nothing says how many will turn out to be operations.
OPCODE_SPACE = tuple(range(0x00, 0x100))


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


def candidate_module(opcode: int, export: str = "f") -> bytes:
    """A module whose single function applies one candidate opcode to two f64 parameters.

    Whether this module exists as a program is the substrate's decision, not ours.
    """
    signature = bytes([0x60]) + _vec([bytes([F64])] * 2) + _vec([bytes([F64])])
    inner = _vec([]) + bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, opcode]) + bytes([_END])
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)]))
        + _section(7, _vec([_name(export) + bytes([0x00]) + _uleb(0)]))
        + _section(10, _vec([_uleb(len(inner)) + inner]))
    )


def scan_requests(export: str = "f") -> dict[str, str]:
    """One candidate module per opcode byte, keyed by its hexadecimal name."""
    import base64

    return {
        f"{opcode:#04x}": base64.b64encode(candidate_module(opcode, export)).decode("ascii")
        for opcode in OPCODE_SPACE
    }


@dataclass(frozen=True)
class DiscoveredOperation:
    name: str
    opcode: int
    observations: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "opcode": self.opcode, "observations": list(self.observations)}


def discovered_from(response: Mapping[str, object]) -> tuple[DiscoveredOperation, ...]:
    """Turn a scan response into the operation set the lineage now has."""
    found = []
    for name, values in sorted(response.get("valid", {}).items()):
        if any(value is None for value in values):
            continue
        found.append(DiscoveredOperation(name, int(name, 16), tuple(float(v) for v in values)))
    if not found:
        raise M058Error("the scan discovered no operation at all")
    return tuple(found)


def expression_space_size(size: int, atom_count: int, operation_count: int) -> int:
    if size < 1 or size % 2 == 0:
        raise M058Error("an expression tree has an odd node count of at least one")
    counts = {1: atom_count}
    total = atom_count
    for current in range(3, size + 1, 2):
        value = 0
        for left in range(1, current - 1, 2):
            right = current - 1 - left
            value += operation_count * counts.get(left, 0) * counts.get(right, 0)
        counts[current] = value
        total += value
    return total


@dataclass(frozen=True)
class Expr:
    atom: str | None = None
    operation: str | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None

    def __post_init__(self) -> None:
        if self.atom is not None:
            if self.operation is not None or self.left is not None or self.right is not None:
                raise M058Error("an atom carries no operation or operands")
            return
        if not self.operation:
            raise M058Error("an application requires a discovered operation")
        if self.left is None or self.right is None:
            raise M058Error("an application requires two operands")

    @property
    def size(self) -> int:
        return 1 if self.atom is not None else 1 + self.left.size + self.right.size

    def canonical(self) -> str:
        if self.atom is not None:
            return self.atom
        return f"{self.operation}({self.left.canonical()},{self.right.canonical()})"

    def body(self) -> dict[str, object]:
        if self.atom is not None:
            return {"atom": self.atom}
        return {"operation": self.operation, "left": self.left.body(), "right": self.right.body()}


def load_expression(value: object) -> Expr:
    if not isinstance(value, Mapping):
        raise M058Error("malformed expression body")
    if "atom" in value:
        return Expr(atom=str(value["atom"]))
    return Expr(
        operation=str(value.get("operation")),
        left=load_expression(value.get("left")),
        right=load_expression(value.get("right")),
    )


def atoms_for(arity: int) -> tuple[str, ...]:
    return tuple(f"p{index}" for index in range(arity)) + ("k",)


def emit_tool(
    tool_name: str, expression: Expr, arity: int, operations: Mapping[str, int],
) -> tuple[bytes, dict[str, object]]:
    """Emit wasm for a synthesized tool, using opcodes the lineage discovered itself."""
    def instructions(node: Expr) -> bytes:
        if node.atom is not None:
            if node.atom == "k":
                return bytes([_F64_CONST]) + struct.pack("<d", float(arity))
            index = int(node.atom[1:])
            if not 0 <= index < arity:
                raise M058Error("expression reads a parameter the tool does not have")
            return bytes([_LOCAL_GET, index])
        opcode = operations.get(node.operation)
        if opcode is None:
            raise M058Error(f"expression uses an operation the scan never discovered: {node.operation}")
        return instructions(node.left) + instructions(node.right) + bytes([opcode])

    signature = bytes([0x60]) + _vec([bytes([F64])] * arity) + _vec([bytes([F64])])
    inner = _vec([]) + instructions(expression) + bytes([_END])
    module = (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)]))
        + _section(7, _vec([_name(tool_name) + bytes([0x00]) + _uleb(0)]))
        + _section(10, _vec([_uleb(len(inner)) + inner]))
    )
    return module, {"tool_name": tool_name, "arity": arity, "expression": expression.canonical()}


def operations_module(operations: Sequence[DiscoveredOperation]) -> bytes:
    """One module exposing every discovered operation, for synthesis to evaluate against."""
    signature = bytes([0x60]) + _vec([bytes([F64])] * 2) + _vec([bytes([F64])])
    bodies = []
    for operation in operations:
        inner = _vec([]) + bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, operation.opcode]) + bytes([_END])
        bodies.append(_uleb(len(inner)) + inner)
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)] * len(operations)))
        + _section(
            7,
            _vec([
                _name(operation.name) + bytes([0x00]) + _uleb(index)
                for index, operation in enumerate(operations)
            ]),
        )
        + _section(10, _vec(bodies))
    )


__all__ = [
    "OPCODE_SPACE", "DiscoveredOperation", "Expr", "M058Error", "atoms_for", "candidate_module",
    "discovered_from", "emit_tool", "expression_space_size", "load_expression",
    "operations_module", "scan_requests",
]
