"""M057: an opaque target substrate, and synthesis of a migration path into it.

M056 handed the lineage a compiler: `_body_for(expression_id)` mapped each declared tool to a
WebAssembly instruction sequence, authored in advance. M057 removes it.

The target instruction set is exposed as opaque handles. The lineage may run a handle and observe
what it returns; nothing tells it which handle is addition and which is maximum. It must identify
what they do by probing, then compose them into a body for each of its accepted tools.

Synthesis is bottom-up by expression size, with candidates deduplicated by their behaviour on the
probe domain. That deduplication is M052's equivalence argument. D016 closed M052 as a
search-efficiency result rather than a capability gain, which it was; here it is the technique
that makes compositional synthesis reachable at all.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
import struct
from typing import Iterable, Mapping, Sequence


class M057Error(ValueError):
    """Raised when an M057 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


F64 = 0x7C
_LOCAL_GET = 0x20
_F64_CONST = 0x44
_END = 0x0B

#: The substrate's binary operations, exposed under opaque names. The opcode is the substrate's
#: own identity; the lineage never receives this mapping, only the handles.
_HANDLE_OPCODES: dict[str, int] = {
    "h1": 0xA0,  # f64.add
    "h2": 0xA1,  # f64.sub
    "h3": 0xA2,  # f64.mul
    "h4": 0xA3,  # f64.div
    "h5": 0xA4,  # f64.min
    "h6": 0xA5,  # f64.max
}
HANDLES: tuple[str, ...] = tuple(sorted(_HANDLE_OPCODES))
MAX_EXPRESSION_SIZE = 7
SYNTHESIS_BUDGET = 200_000


def handle_count() -> int:
    return len(HANDLES)


def expression_space_size(size: int, atom_count: int) -> int:
    """Number of expression trees of at most `size` nodes over the handles and atoms."""
    if size < 1 or size % 2 == 0:
        raise M057Error("an expression tree has an odd node count of at least one")
    counts = {1: atom_count}
    total = atom_count
    for current in range(3, size + 1, 2):
        value = 0
        for left in range(1, current - 1, 2):
            right = current - 1 - left
            value += len(HANDLES) * counts.get(left, 0) * counts.get(right, 0)
        counts[current] = value
        total += value
    return total


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


def probe_module() -> bytes:
    """A module exposing every handle as a two-argument function, under its opaque name."""
    signature = bytes([0x60]) + _vec([bytes([F64])] * 2) + _vec([bytes([F64])])
    bodies = []
    for handle in HANDLES:
        inner = _vec([]) + bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, _HANDLE_OPCODES[handle]]) + bytes([_END])
        bodies.append(_uleb(len(inner)) + inner)
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)] * len(HANDLES)))
        + _section(7, _vec([_name(handle) + bytes([0x00]) + _uleb(index) for index, handle in enumerate(HANDLES)]))
        + _section(10, _vec(bodies))
    )


@dataclass(frozen=True)
class Expr:
    """An expression over opaque handles. `atom` is a parameter index or the arity constant."""

    atom: str | None = None
    handle: str | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None

    def __post_init__(self) -> None:
        if self.atom is not None:
            if self.handle is not None or self.left is not None or self.right is not None:
                raise M057Error("an atom carries no handle or operands")
            return
        if self.handle not in _HANDLE_OPCODES:
            raise M057Error("unknown handle")
        if self.left is None or self.right is None:
            raise M057Error("a handle application requires two operands")

    @property
    def size(self) -> int:
        return 1 if self.atom is not None else 1 + self.left.size + self.right.size

    def canonical(self) -> str:
        if self.atom is not None:
            return self.atom
        return f"{self.handle}({self.left.canonical()},{self.right.canonical()})"

    def body(self) -> dict[str, object]:
        if self.atom is not None:
            return {"atom": self.atom}
        return {"handle": self.handle, "left": self.left.body(), "right": self.right.body()}


def _expr_from_body(value: object) -> Expr:
    if not isinstance(value, Mapping):
        raise M057Error("malformed expression body")
    if "atom" in value:
        return Expr(atom=str(value["atom"]))
    return Expr(
        handle=str(value.get("handle")),
        left=_expr_from_body(value.get("left")),
        right=_expr_from_body(value.get("right")),
    )


def emit_tool(tool_name: str, expression: Expr, arity: int) -> tuple[bytes, dict[str, object]]:
    """Emit wasm for one synthesized tool. Only the substrate resolves a handle to an opcode."""
    def instructions(node: Expr) -> bytes:
        if node.atom is not None:
            if node.atom == "k":
                return bytes([_F64_CONST]) + struct.pack("<d", float(arity))
            index = int(node.atom[1:])
            if not 0 <= index < arity:
                raise M057Error("expression reads a parameter the tool does not have")
            return bytes([_LOCAL_GET, index])
        return (
            instructions(node.left)
            + instructions(node.right)
            + bytes([_HANDLE_OPCODES[node.handle]])
        )

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


def atoms_for(arity: int) -> tuple[str, ...]:
    """Parameters the tool actually has, plus a constant derived from its own arity."""
    return tuple(f"p{index}" for index in range(arity)) + ("k",)


def load_expression(value: Mapping[str, object]) -> Expr:
    return _expr_from_body(value)


__all__ = [
    "HANDLES", "MAX_EXPRESSION_SIZE", "SYNTHESIS_BUDGET", "Expr", "M057Error", "atoms_for",
    "emit_tool", "expression_space_size", "handle_count", "load_expression", "probe_module",
]
