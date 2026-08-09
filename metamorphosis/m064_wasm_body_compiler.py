"""Dynamic whole-body WebAssembly compiler for the M064 completion lineage.

The fixed M060 shell already owns parsing, planning, allocation, execution and
critique in one import-free module.  M064 parameterises the four pieces that a
native rewrite must extend: aliases, arities, route admission and tool dispatch.
Constructed tools call earlier routes through the WebAssembly ``tool`` function;
their reuse is therefore executable rather than a metadata-only assertion.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import metamorphosis.m060_body_compiler as m060
from metamorphosis.m060_wasm_emit import Code, WasmEmitError, WasmModule


class M064WasmCompileError(ValueError):
    """Raised when a dynamic native body cannot be emitted safely."""


def _extend(target: Code, fragment: Code) -> Code:
    # Code deliberately exposes no public concatenation method.  Both classes
    # are repository-owned emitters and named-call placeholders must remain
    # unresolved until WasmModule.emit(), so copying the parts is the exact
    # composition operation required here.
    target._parts.extend(fragment._parts)
    return target


def route_codes(tool_specs: Mapping[str, Mapping[str, object]]) -> dict[str, int]:
    preferred = ("add", "max", "mean", "mul")
    ordered = [name for name in preferred if name in tool_specs]
    ordered.extend(sorted(name for name in tool_specs if name not in ordered))
    if len(ordered) > 255:
        raise M064WasmCompileError("the one-byte route space is exhausted")
    return {name: index for index, name in enumerate(ordered)}


def alias_table(
    aliases: Mapping[str, str],
    codes: Mapping[str, int],
) -> bytes:
    payload = bytearray()
    for token, tool in sorted((str(key), str(value)) for key, value in aliases.items()):
        encoded = token.encode("ascii")
        if not encoded or len(encoded) > 255 or any(byte > 0x7F for byte in encoded):
            raise M064WasmCompileError("aliases must be non-empty bounded ASCII")
        if tool not in codes:
            raise M064WasmCompileError(f"alias {token!r} points to an unavailable tool")
        payload.extend((len(encoded), codes[tool]))
        payload.extend(encoded)
    payload.append(0)
    return bytes(payload)


def _arity(tool_specs: Mapping[str, Mapping[str, object]], codes: Mapping[str, int]) -> Code:
    code = Code()
    for name, route in sorted(codes.items(), key=lambda item: item[1]):
        arity = int(tool_specs[name]["arity"])
        if arity not in {2, 3}:
            raise M064WasmCompileError("M064 admits binary and ternary tools only")
        code.local_get(0).i32_const(route).i32_eq().if_()
        code.i32_const(arity).ret().end()
    return code.unreachable()


def _select(route_count: int) -> Code:
    if route_count <= 0:
        raise M064WasmCompileError("a native body must expose at least one route")
    return (
        Code()
        .local_get(0).i32_const(0).i32_ge_s()
        .local_get(0).i32_const(route_count).i32_lt_s().i32_and()
        .if_("i32").local_get(0).else_().i32_const(-1).end()
    )


def _primitive_body(name: str, opcodes: Mapping[str, int]) -> Code:
    if name == "add":
        return Code().local_get(1).local_get(2).op(int(opcodes["add"]))
    if name == "mul":
        return Code().local_get(1).local_get(2).op(int(opcodes["mul"]))
    if name == "max":
        return Code().local_get(1).local_get(2).op(int(opcodes["max"]))
    if name == "mean":
        return (
            Code()
            .local_get(1).local_get(2).op(int(opcodes["add"]))
            .local_get(3).op(int(opcodes["add"]))
            .f64_const(3.0).op(int(opcodes["div"]))
        )
    raise M064WasmCompileError(f"unsupported discovered primitive: {name}")


def _expression(
    value: Mapping[str, object],
    tool_specs: Mapping[str, Mapping[str, object]],
    codes: Mapping[str, int],
) -> Code:
    if value.get("kind") == "arg":
        index = int(value["index"])
        if index not in {0, 1, 2}:
            raise M064WasmCompileError("expression argument is outside the tool frame")
        return Code().local_get(index + 1)
    if value.get("kind") != "call":
        raise M064WasmCompileError("unknown expression node")
    tool = str(value.get("tool"))
    if tool not in tool_specs or tool not in codes:
        raise M064WasmCompileError(f"expression calls an unavailable route: {tool}")
    arguments = value.get("args")
    arity = int(tool_specs[tool]["arity"])
    if not isinstance(arguments, list) or len(arguments) != arity:
        raise M064WasmCompileError("expression call arity mismatch")
    code = Code().i32_const(codes[tool])
    for argument in arguments:
        if not isinstance(argument, Mapping):
            raise M064WasmCompileError("expression child is malformed")
        _extend(code, _expression(argument, tool_specs, codes))
    for _ in range(3 - arity):
        code.f64_const(0.0)
    return code.call("tool")


def _tool(
    tool_specs: Mapping[str, Mapping[str, object]],
    codes: Mapping[str, int],
    opcodes: Mapping[str, int],
) -> Code:
    code = Code()
    for name, route in sorted(codes.items(), key=lambda item: item[1]):
        spec = tool_specs[name]
        code.local_get(0).i32_const(route).i32_eq().if_()
        if spec.get("kind") == "primitive":
            primitive = str(spec.get("primitive"))
            _extend(code, _primitive_body(primitive, opcodes))
        elif spec.get("kind") == "constructed":
            expression = spec.get("expression")
            if not isinstance(expression, Mapping):
                raise M064WasmCompileError("constructed route lacks its expression")
            _extend(code, _expression(expression, tool_specs, codes))
        else:
            raise M064WasmCompileError(f"malformed tool specification for {name}")
        code.ret().end()
    return code.unreachable()


def build_dynamic_module(
    aliases: Mapping[str, str],
    tool_specs: Mapping[str, Mapping[str, object]],
    opcodes: Mapping[str, int],
) -> WasmModule:
    required_opcodes = {"add", "max", "mul", "div"}
    if set(opcodes) != required_opcodes:
        raise M064WasmCompileError(
            f"discovered arithmetic must be exactly {sorted(required_opcodes)}"
        )
    codes = route_codes(tool_specs)
    module = WasmModule(memory_pages=1)
    module.add_data(m060.ALIASES, alias_table(aliases, codes))

    module.add_function("tokenize", [], ["i32"], ["i32"] * 5, m060._tokenize())
    module.add_function("token_is_number", ["i32"], ["i32"], ["i32"] * 6, m060._token_is_number())
    module.add_function("token_number", ["i32"], ["f64"], ["i32"] * 7, m060._token_number())
    module.add_function("alias_index", ["i32"], ["i32"], ["i32"] * 10, m060._alias_index())
    module.add_function("arity", ["i32"], ["i32"], [], _arity(tool_specs, codes), export=False)
    module.add_function("parse", ["i32"], ["i32", "i32"], ["i32"] * 7, m060._parse(), export=False)
    module.add_function("interpret", [], ["i32"], ["i32"] * 2, m060._interpret())
    module.add_function(
        "emit", ["i32"], ["i32"], ["i32"] * 7 + ["f64"] * 3, m060._emit_step(), export=False
    )
    module.add_function("descriptor", ["i32"], ["i32", "f64"], ["i32"], m060._descriptor(), export=False)
    module.add_function("plan", ["i32"], ["i32"], [], m060._plan())
    module.add_function("allocate", ["i32"], ["i32"], [], m060._allocate())
    module.add_function("select", ["i32"], ["i32"], [], _select(len(codes)))
    module.add_function(
        "tool",
        ["i32", "f64", "f64", "f64"],
        ["f64"],
        [],
        _tool(tool_specs, codes, opcodes),
        export=False,
    )
    module.add_function(
        "execute",
        ["i32", "i32"],
        ["f64"],
        ["i32", "i32", "i32", "i32", "f64", "f64", "f64", "i32"],
        m060._execute(),
    )
    module.add_function(
        "argument", ["i32", "i32"], ["f64"], ["i32", "i32", "f64"], m060._argument(), export=False
    )
    module.add_function("critique", ["f64"], ["f64"], [], m060._critique())
    module.add_function("run", [], ["f64"], ["i32"] * 3, m060._run())
    return module


def compile_dynamic_body(
    aliases: Mapping[str, str],
    tool_specs: Mapping[str, Mapping[str, object]],
    opcodes: Mapping[str, int],
) -> bytes:
    return build_dynamic_module(aliases, tool_specs, opcodes).emit()


__all__ = [
    "M064WasmCompileError",
    "alias_table",
    "build_dynamic_module",
    "compile_dynamic_body",
    "route_codes",
]
