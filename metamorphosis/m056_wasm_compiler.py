"""M056: compile the accepted native tool modules into a WebAssembly module.

The compiler works from each module's declared metadata, never from its name. `tool_mean` was
learned before the first migration and `tool_max` after it, and both declare
`kind: synthesized_tool`, so both take the identical path. That is what makes the experiment's
falsifier honest: a compiler with a hand-written case for the post-migration tool would carry it
across while proving nothing.

Values are `f64` throughout. JavaScript numbers are IEEE-754 doubles, and `mean` divides, so
compiling to f64 makes the migration semantically exact rather than approximate.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import struct
from typing import Mapping, Sequence


class WasmCompileError(ValueError):
    """Raised when an accepted module cannot be compiled by the declared path."""


F64 = 0x7C
_LOCAL_GET = 0x20
_F64_CONST = 0x44
_F64_ADD = 0xA0
_F64_MUL = 0xA2
_F64_DIV = 0xA3
_F64_MIN = 0xA4
_F64_MAX = 0xA5
_END = 0x0B

#: Expression identifiers this compiler knows how to emit, and their arity. The map is keyed by
#: what a module declares, not by what it is called.
EXPRESSION_ARITY: dict[str, int] = {
    "add": 2,
    "mul": 2,
    "maximum": 2,
    "minimum": 2,
    "mean": 3,
}


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


def _f64_const(value: float) -> bytes:
    return bytes([_F64_CONST]) + struct.pack("<d", value)


def _body_for(expression_id: str) -> bytes:
    """Emit the instruction sequence for a declared expression identifier."""
    arity = EXPRESSION_ARITY.get(expression_id)
    if arity is None:
        raise WasmCompileError(f"no wasm emission rule for expression {expression_id!r}")
    if expression_id == "add":
        return bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, _F64_ADD])
    if expression_id == "mul":
        return bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, _F64_MUL])
    if expression_id == "maximum":
        return bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, _F64_MAX])
    if expression_id == "minimum":
        return bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, _F64_MIN])
    # mean: (a + b + c) / arity
    return (
        bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, _F64_ADD, _LOCAL_GET, 2, _F64_ADD])
        + _f64_const(float(arity))
        + bytes([_F64_DIV])
    )


@dataclass(frozen=True)
class CompiledTool:
    tool_name: str
    expression_id: str
    arity: int
    source_module: str
    origin: str


def declared_tools(body: Mapping[str, object]) -> tuple[CompiledTool, ...]:
    """Read what each accepted tool module declares. No module is recognised by its name."""
    found: list[CompiledTool] = []
    for module in body["modules"]:
        name = str(module["name"])
        if not (name == "tool_core" or name.startswith("tool_")):
            continue
        meta = module["meta"]
        kind = str(meta.get("kind"))
        if kind == "tool_module":
            for tool in meta.get("tools", ()):
                found.append(
                    CompiledTool(str(tool), str(tool), EXPRESSION_ARITY[str(tool)], name, "founder")
                )
        elif kind == "synthesized_tool":
            tool_name = str(meta["tool_name"])
            expression_id = str(meta["expression_id"])
            if expression_id not in EXPRESSION_ARITY:
                raise WasmCompileError(
                    f"module {name} declares expression {expression_id!r} with no emission rule"
                )
            found.append(
                CompiledTool(
                    tool_name, expression_id, EXPRESSION_ARITY[expression_id], name, "synthesized"
                )
            )
        else:
            raise WasmCompileError(f"module {name} declares unknown tool kind {kind!r}")
    if not found:
        raise WasmCompileError("the accepted body declares no tool module")
    return tuple(sorted(found, key=lambda tool: tool.tool_name))


def compile_tools_to_wasm(body: Mapping[str, object]) -> tuple[bytes, tuple[CompiledTool, ...]]:
    """Emit one WebAssembly module exporting every declared tool.

    The emitted module carries the arithmetic. Nothing calls back out for it: the module has no
    imports at all, which the caller can and does verify.
    """
    tools = declared_tools(body)
    signatures: list[bytes] = []
    signature_index: dict[int, int] = {}
    for tool in tools:
        if tool.arity not in signature_index:
            signature_index[tool.arity] = len(signatures)
            signatures.append(
                bytes([0x60]) + _vec([bytes([F64])] * tool.arity) + _vec([bytes([F64])])
            )
    type_section = _section(1, _vec(signatures))
    function_section = _section(3, _vec([_uleb(signature_index[tool.arity]) for tool in tools]))
    export_section = _section(
        7,
        _vec([_name(tool.tool_name) + bytes([0x00]) + _uleb(index) for index, tool in enumerate(tools)]),
    )
    bodies = []
    for tool in tools:
        inner = _vec([]) + _body_for(tool.expression_id) + bytes([_END])
        bodies.append(_uleb(len(inner)) + inner)
    code_section = _section(10, _vec(bodies))
    module = (
        b"\x00asm\x01\x00\x00\x00"
        + type_section
        + function_section
        + export_section
        + code_section
    )
    return module, tools


def module_digest(module: bytes) -> str:
    return hashlib.sha256(b"m056-wasm-module-v1\x00" + module).hexdigest()


def compilation_record(tools: Sequence[CompiledTool], module: bytes) -> dict[str, object]:
    return {
        "schema": "m056-wasm-compilation-v1",
        "target_runtime": "webassembly",
        "value_type": "f64",
        "module_bytes": len(module),
        "module_digest": module_digest(module),
        "imports": 0,
        "tools": [
            {
                "tool_name": tool.tool_name,
                "expression_id": tool.expression_id,
                "arity": tool.arity,
                "source_module": tool.source_module,
                "origin": tool.origin,
            }
            for tool in tools
        ],
    }


__all__ = [
    "EXPRESSION_ARITY", "CompiledTool", "WasmCompileError", "compilation_record",
    "compile_tools_to_wasm", "declared_tools", "module_digest",
]
