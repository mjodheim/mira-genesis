"""M060: a general WebAssembly binary emitter, independent of any lineage.

M056 through M059 each emitted WebAssembly, but each emitter knew its own experiment: a fixed
`f64` shape, one signature per tool, no memory, no control flow. Those compilers cannot express
a loop, so nothing built on them can either — the substrate, not the lineage, was the ceiling.

This module removes that ceiling. It emits the whole binary format a self-contained module can
use — types, functions, linear memory, exports, code, data — with structured control flow and
both `i32` and `f64` operands, and it does so with the standard library alone.

Two conventions are worth stating because they are choices rather than format requirements:

- **Function indices are the order of `add_function` calls**, starting at 0. There are no
  imported functions, so nothing shifts the numbering. `Code.call` therefore accepts either an
  `int` the caller already knows or a `str` name resolved at `emit()` time, which is what makes
  mutual recursion and forward references expressible.
- **`add_function` appends the terminating `end`.** Block, loop and if bodies still close with
  an explicit `Code.end()`; only the outermost function body is closed for the caller, because
  forgetting that byte is otherwise a silent malformed-module error.

Local indices are parameters first (0..len(params)-1) then declared locals, as the format
requires.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Callable, Sequence

MAGIC = b"\x00asm"
VERSION = b"\x01\x00\x00\x00"

#: WebAssembly value types this emitter supports, keyed by the string the caller writes.
VALTYPES: dict[str, int] = {"i32": 0x7F, "f64": 0x7C}

_SECTION_TYPE = 1
_SECTION_FUNCTION = 3
_SECTION_MEMORY = 5
_SECTION_EXPORT = 7
_SECTION_CODE = 10
_SECTION_DATA = 11

_PAGE_SIZE = 65536
_FUNC_TYPE = 0x60
_EMPTY_BLOCKTYPE = 0x40
_END = 0x0B


class WasmEmitError(ValueError):
    """Raised when a module or instruction sequence cannot be encoded as valid WebAssembly."""


def uleb128(value: int) -> bytes:
    """Unsigned LEB128, used for every length, index and memarg field in the format."""
    if value < 0:
        raise WasmEmitError(f"uleb128 requires a non-negative value, got {value}")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def sleb128(value: int) -> bytes:
    """Signed LEB128, used for `i32.const` and for data-segment offset expressions."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        done = (value == 0 and not byte & 0x40) or (value == -1 and byte & 0x40)
        out.append(byte if done else byte | 0x80)
        if done:
            return bytes(out)


def _vec(items: Sequence[bytes]) -> bytes:
    return uleb128(len(items)) + b"".join(items)


def _section(identifier: int, payload: bytes) -> bytes:
    return bytes([identifier]) + uleb128(len(payload)) + payload


def _name(text: str) -> bytes:
    encoded = text.encode("utf-8")
    return uleb128(len(encoded)) + encoded


def _valtype(name: str) -> int:
    try:
        return VALTYPES[name]
    except KeyError:
        raise WasmEmitError(f"unknown value type {name!r}; expected one of {sorted(VALTYPES)}") from None


def _blocktype(result: str | None) -> int:
    return _EMPTY_BLOCKTYPE if result is None else _valtype(result)


@dataclass(frozen=True)
class _NamedCall:
    """A `call` whose target is known by name, resolved once every function index exists."""

    name: str


class Code:
    """Chainable builder for a raw instruction sequence.

    The builder does no type checking: it is a faithful encoder, and the WebAssembly runtime is
    the validator. That keeps it usable for deliberately odd sequences an experiment may want to
    emit, and keeps validation in one place rather than two.
    """

    def __init__(self) -> None:
        self._parts: list[bytes | _NamedCall] = []

    def _put(self, payload: bytes) -> "Code":
        self._parts.append(payload)
        return self

    def op(self, opcode: int) -> "Code":
        """Append a raw single-byte opcode, for anything without a named method."""
        if not 0 <= opcode <= 0xFF:
            raise WasmEmitError(f"opcode {opcode} is not a byte")
        return self._put(bytes([opcode]))

    def raw(self, payload: bytes) -> "Code":
        """Append pre-encoded bytes, for multi-byte opcodes or already-built fragments."""
        return self._put(bytes(payload))

    # -- locals ---------------------------------------------------------------------------
    def local_get(self, i: int) -> "Code":
        return self._put(b"\x20" + uleb128(i))

    def local_set(self, i: int) -> "Code":
        return self._put(b"\x21" + uleb128(i))

    def local_tee(self, i: int) -> "Code":
        return self._put(b"\x22" + uleb128(i))

    # -- constants ------------------------------------------------------------------------
    def i32_const(self, v: int) -> "Code":
        if not -(2**31) <= v < 2**32:
            raise WasmEmitError(f"i32 constant {v} is out of range")
        return self._put(b"\x41" + sleb128(v - 2**32 if v >= 2**31 else v))

    def f64_const(self, v: float) -> "Code":
        return self._put(b"\x44" + struct.pack("<d", float(v)))

    # -- memory ---------------------------------------------------------------------------
    def _memarg(self, opcode: int, align: int, offset: int) -> "Code":
        return self._put(bytes([opcode]) + uleb128(align) + uleb128(offset))

    def i32_load(self, offset: int = 0, align: int = 2) -> "Code":
        return self._memarg(0x28, align, offset)

    def i32_load8_u(self, offset: int = 0, align: int = 0) -> "Code":
        return self._memarg(0x2D, align, offset)

    def i32_store(self, offset: int = 0, align: int = 2) -> "Code":
        return self._memarg(0x36, align, offset)

    def i32_store8(self, offset: int = 0, align: int = 0) -> "Code":
        return self._memarg(0x3A, align, offset)

    def f64_load(self, offset: int = 0, align: int = 3) -> "Code":
        return self._memarg(0x2B, align, offset)

    def f64_store(self, offset: int = 0, align: int = 3) -> "Code":
        return self._memarg(0x39, align, offset)

    # -- control flow ---------------------------------------------------------------------
    def block(self, result: str | None = None) -> "Code":
        return self._put(bytes([0x02, _blocktype(result)]))

    def loop(self, result: str | None = None) -> "Code":
        return self._put(bytes([0x03, _blocktype(result)]))

    def if_(self, result: str | None = None) -> "Code":
        return self._put(bytes([0x04, _blocktype(result)]))

    def else_(self) -> "Code":
        return self.op(0x05)

    def end(self) -> "Code":
        return self.op(_END)

    def br(self, depth: int) -> "Code":
        return self._put(b"\x0c" + uleb128(depth))

    def br_if(self, depth: int) -> "Code":
        return self._put(b"\x0d" + uleb128(depth))

    def ret(self) -> "Code":
        return self.op(0x0F)

    def drop(self) -> "Code":
        return self.op(0x1A)

    def select(self) -> "Code":
        return self.op(0x1B)

    def nop(self) -> "Code":
        return self.op(0x01)

    def unreachable(self) -> "Code":
        return self.op(0x00)

    def call(self, index: int | str) -> "Code":
        """Call by index, or by exported-or-declared function name resolved at `emit()`."""
        if isinstance(index, str):
            self._parts.append(_NamedCall(index))
            return self
        return self._put(b"\x10" + uleb128(index))

    # -- i32 operators --------------------------------------------------------------------
    def i32_add(self) -> "Code":
        return self.op(0x6A)

    def i32_sub(self) -> "Code":
        return self.op(0x6B)

    def i32_mul(self) -> "Code":
        return self.op(0x6C)

    def i32_div_s(self) -> "Code":
        return self.op(0x6D)

    def i32_rem_s(self) -> "Code":
        return self.op(0x6F)

    def i32_and(self) -> "Code":
        return self.op(0x71)

    def i32_or(self) -> "Code":
        return self.op(0x72)

    def i32_xor(self) -> "Code":
        return self.op(0x73)

    def i32_shl(self) -> "Code":
        return self.op(0x74)

    def i32_shr_s(self) -> "Code":
        return self.op(0x75)

    def i32_eq(self) -> "Code":
        return self.op(0x46)

    def i32_ne(self) -> "Code":
        return self.op(0x47)

    def i32_lt_s(self) -> "Code":
        return self.op(0x48)

    def i32_gt_s(self) -> "Code":
        return self.op(0x4A)

    def i32_le_s(self) -> "Code":
        return self.op(0x4C)

    def i32_ge_s(self) -> "Code":
        return self.op(0x4E)

    def i32_eqz(self) -> "Code":
        return self.op(0x45)

    # -- f64 operators --------------------------------------------------------------------
    def f64_add(self) -> "Code":
        return self.op(0xA0)

    def f64_sub(self) -> "Code":
        return self.op(0xA1)

    def f64_mul(self) -> "Code":
        return self.op(0xA2)

    def f64_div(self) -> "Code":
        return self.op(0xA3)

    def f64_min(self) -> "Code":
        return self.op(0xA4)

    def f64_max(self) -> "Code":
        return self.op(0xA5)

    def f64_abs(self) -> "Code":
        return self.op(0x99)

    def f64_neg(self) -> "Code":
        return self.op(0x9A)

    def f64_ceil(self) -> "Code":
        return self.op(0x9B)

    def f64_floor(self) -> "Code":
        return self.op(0x9C)

    def f64_trunc(self) -> "Code":
        return self.op(0x9D)

    def f64_nearest(self) -> "Code":
        return self.op(0x9E)

    def f64_eq(self) -> "Code":
        return self.op(0x61)

    def f64_ne(self) -> "Code":
        return self.op(0x62)

    def f64_lt(self) -> "Code":
        return self.op(0x63)

    def f64_gt(self) -> "Code":
        return self.op(0x64)

    # -- conversions ----------------------------------------------------------------------
    def f64_convert_i32_s(self) -> "Code":
        return self.op(0xB7)

    def i32_trunc_f64_s(self) -> "Code":
        return self.op(0xAA)

    # -- rendering ------------------------------------------------------------------------
    def render(self, index_for: Callable[[str], int]) -> bytes:
        """Flatten to bytes, resolving named calls through `index_for`."""
        out = bytearray()
        for part in self._parts:
            if isinstance(part, _NamedCall):
                out += b"\x10" + uleb128(index_for(part.name))
            else:
                out += part
        return bytes(out)

    def bytes(self) -> bytes:
        """Flatten to bytes. Named calls cannot be resolved here, only by the owning module."""

        def unresolved(name: str) -> int:
            raise WasmEmitError(
                f"call to {name!r} needs module context; pass this Code to add_function instead"
            )

        return self.render(unresolved)

    def __len__(self) -> int:
        return len(self.bytes())


@dataclass(frozen=True)
class _Function:
    name: str
    params: tuple[str, ...]
    results: tuple[str, ...]
    locals: tuple[str, ...]
    body: bytes | Code
    export: bool


@dataclass(frozen=True)
class _DataSegment:
    offset: int
    payload: bytes


class WasmModule:
    """A self-contained WebAssembly module: no imports, one linear memory, exported by name."""

    def __init__(self, memory_pages: int = 1) -> None:
        if memory_pages < 0:
            raise WasmEmitError(f"memory_pages must be non-negative, got {memory_pages}")
        self.memory_pages = memory_pages
        self._functions: list[_Function] = []
        self._index_by_name: dict[str, int] = {}
        self._data: list[_DataSegment] = []

    def add_data(self, offset: int, payload: bytes) -> None:
        """Place `payload` in linear memory at `offset` when the module is instantiated."""
        if offset < 0:
            raise WasmEmitError(f"data offset must be non-negative, got {offset}")
        end = offset + len(payload)
        if end > self.memory_pages * _PAGE_SIZE:
            raise WasmEmitError(
                f"data segment ends at {end} but memory holds {self.memory_pages * _PAGE_SIZE} bytes"
            )
        self._data.append(_DataSegment(offset, bytes(payload)))

    def add_function(
        self,
        name: str,
        params: Sequence[str],
        results: Sequence[str],
        locals: Sequence[str],
        body: bytes | Code,
        export: bool = True,
    ) -> int:
        """Declare a function and return its index. Indices are assigned in call order from 0."""
        if name in self._index_by_name:
            raise WasmEmitError(f"function {name!r} is already defined")
        for valtype in (*params, *results, *locals):
            _valtype(valtype)
        if not isinstance(body, (bytes, bytearray, Code)):
            raise WasmEmitError("body must be bytes or a Code builder")
        index = len(self._functions)
        self._functions.append(
            _Function(
                name=name,
                params=tuple(params),
                results=tuple(results),
                locals=tuple(locals),
                body=body if isinstance(body, Code) else bytes(body),
                export=export,
            )
        )
        self._index_by_name[name] = index
        return index

    def function_index(self, name: str) -> int:
        """Index of an already-declared function, for callers that resolve references early."""
        try:
            return self._index_by_name[name]
        except KeyError:
            raise WasmEmitError(f"no function named {name!r}") from None

    def _resolve(self, name: str) -> int:
        try:
            return self._index_by_name[name]
        except KeyError:
            raise WasmEmitError(f"call to undefined function {name!r}") from None

    def _type_section(self) -> tuple[bytes, list[int]]:
        """Deduplicate signatures, preserving first-use order so emission stays deterministic."""
        seen: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}
        entries: list[bytes] = []
        assigned: list[int] = []
        for function in self._functions:
            signature = (function.params, function.results)
            if signature not in seen:
                seen[signature] = len(entries)
                entries.append(
                    bytes([_FUNC_TYPE])
                    + _vec([bytes([_valtype(t)]) for t in function.params])
                    + _vec([bytes([_valtype(t)]) for t in function.results])
                )
            assigned.append(seen[signature])
        return _section(_SECTION_TYPE, _vec(entries)), assigned

    def _code_entry(self, function: _Function) -> bytes:
        runs: list[list[object]] = []
        for valtype in function.locals:
            if runs and runs[-1][1] == valtype:
                runs[-1][0] = int(runs[-1][0]) + 1  # type: ignore[arg-type]
            else:
                runs.append([1, valtype])
        declarations = _vec([uleb128(int(count)) + bytes([_valtype(str(t))]) for count, t in runs])
        body = function.body.render(self._resolve) if isinstance(function.body, Code) else function.body
        payload = declarations + body + bytes([_END])
        return uleb128(len(payload)) + payload

    def emit(self) -> bytes:
        """Serialise the whole module. Pure: emitting twice yields byte-identical output."""
        if not self._functions and not self._data:
            raise WasmEmitError("module has no functions and no data")

        type_section, type_indices = self._type_section()
        out = bytearray(MAGIC + VERSION)
        out += type_section
        out += _section(_SECTION_FUNCTION, _vec([uleb128(i) for i in type_indices]))
        out += _section(_SECTION_MEMORY, _vec([b"\x00" + uleb128(self.memory_pages)]))

        exports = [
            _name(function.name) + b"\x00" + uleb128(index)
            for index, function in enumerate(self._functions)
            if function.export
        ]
        exports.append(_name("memory") + b"\x02" + uleb128(0))
        out += _section(_SECTION_EXPORT, _vec(exports))

        out += _section(_SECTION_CODE, _vec([self._code_entry(f) for f in self._functions]))

        if self._data:
            segments = [
                b"\x00"
                + b"\x41"
                + sleb128(segment.offset)
                + bytes([_END])
                + uleb128(len(segment.payload))
                + segment.payload
                for segment in self._data
            ]
            out += _section(_SECTION_DATA, _vec(segments))
        return bytes(out)
