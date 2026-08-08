"""M060 falsifications: every emitted module is executed by Node, and the numbers are checked.

A byte emitter that is only checked against its own expectations proves nothing — it will agree
with itself while producing a module no runtime accepts. So each test here instantiates the real
binary in `node` and asserts on values that came back out of WebAssembly, not out of Python.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import pytest

from metamorphosis.m060_wasm_emit import Code, WasmEmitError, WasmModule

NODE_TIMEOUT_SECONDS = 60.0

_HARNESS = """
const fs = require('fs');
const bytes = fs.readFileSync(process.argv[1]);
const instance = new WebAssembly.Instance(new WebAssembly.Module(bytes), {});
const exports = instance.exports;
const memory = new Uint8Array(exports.memory.buffer);
const value = (() => { __SCRIPT__ })();
process.stdout.write(JSON.stringify(value));
"""


def run_in_node(module: WasmModule | bytes, script: str) -> Any:
    """Instantiate the emitted module in Node and return whatever `script` returns, via JSON.

    `script` is a JavaScript function body with `instance`, `exports` and `memory` in scope.
    """
    binary = module if isinstance(module, bytes) else module.emit()
    handle, path = tempfile.mkstemp(suffix=".wasm")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(binary)
        completed = subprocess.run(
            ["node", "-e", _HARNESS.replace("__SCRIPT__", script), path],
            capture_output=True,
            text=True,
            timeout=NODE_TIMEOUT_SECONDS,
            check=False,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if completed.returncode != 0:
        raise AssertionError(f"node rejected the module: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def _sum_to_n() -> WasmModule:
    """sum_to_n(n) = 1 + 2 + ... + n, as a `loop` with a `br_if` exit and two locals."""
    module = WasmModule()
    body = (
        Code()
        .i32_const(0).local_set(1)
        .i32_const(1).local_set(2)
        .block()
        .loop()
        .local_get(2).local_get(0).i32_gt_s().br_if(1)
        .local_get(1).local_get(2).i32_add().local_set(1)
        .local_get(2).i32_const(1).i32_add().local_set(2)
        .br(0)
        .end()
        .end()
        .local_get(1)
    )
    module.add_function("sum_to_n", ["i32"], ["i32"], ["i32", "i32"], body)
    return module


def test_two_parameter_f64_add_returns_correct_sums():
    module = WasmModule()
    module.add_function("add", ["f64", "f64"], ["f64"], [], Code().local_get(0).local_get(1).f64_add())

    values = run_in_node(module, "return [exports.add(1.5, 2.25), exports.add(-3.5, 0.5), exports.add(0.1, 0.2)];")

    assert values[0] == 3.75
    assert values[1] == -3.0
    assert values[2] == pytest.approx(0.30000000000000004)


def test_a_loop_with_a_local_accumulator_sums_one_to_n():
    """Structured control flow is the capability every earlier emitter in this repo lacked."""
    values = run_in_node(_sum_to_n(), "return [0, 1, 5, 10, 100].map(n => exports.sum_to_n(n));")

    assert values == [0, 1, 15, 55, 5050]


def test_if_else_selects_between_two_values():
    module = WasmModule()
    body = Code().local_get(0).if_("i32").i32_const(111).else_().i32_const(222).end()
    module.add_function("pick", ["i32"], ["i32"], [], body)

    values = run_in_node(module, "return [exports.pick(1), exports.pick(0), exports.pick(-4)];")

    assert values == [111, 222, 111]


def test_a_branch_out_of_a_nested_block_skips_code():
    """The `br 1` must escape both blocks, leaving the trailing increment unexecuted."""
    module = WasmModule()
    body = (
        Code()
        .block()
        .block()
        .local_get(0).br_if(0)
        .i32_const(10).local_set(1)
        .br(1)
        .end()
        .local_get(1).i32_const(1).i32_add().local_set(1)
        .end()
        .local_get(1)
    )
    module.add_function("escape", ["i32"], ["i32"], ["i32"], body)

    values = run_in_node(module, "return [exports.escape(0), exports.escape(1)];")

    assert values == [10, 1]


def test_memory_stores_and_loads_round_trip_through_linear_memory():
    module = WasmModule(memory_pages=1)
    poke = Code()
    for address, byte in ((0, 10), (1, 20), (2, 30), (3, 40)):
        poke.i32_const(address).i32_const(byte).i32_store8()
    poke.i32_const(0).i32_load8_u()
    for address in (1, 2, 3):
        poke.i32_const(address).i32_load8_u().i32_add()
    module.add_function("poke_sum", [], ["i32"], [], poke)

    wide = Code().i32_const(64).local_get(0).i32_store().i32_const(64).i32_load()
    module.add_function("i32_round_trip", ["i32"], ["i32"], [], wide)

    doubles = Code().i32_const(128).local_get(0).f64_store().i32_const(128).f64_load().f64_const(2.0).f64_mul()
    module.add_function("f64_round_trip", ["f64"], ["f64"], [], doubles)

    values = run_in_node(
        module,
        "return [exports.poke_sum(), exports.i32_round_trip(-123456), exports.f64_round_trip(1.25)];",
    )

    assert values == [100, -123456, 2.5]


def test_a_data_section_is_present_in_memory_at_instantiation():
    module = WasmModule()
    module.add_data(0, b"Mira\x00\xff")
    module.add_data(16, bytes([7, 8, 9]))
    module.add_function("byte_at", ["i32"], ["i32"], [], Code().local_get(0).i32_load8_u())

    values = run_in_node(
        module,
        "return [0,1,2,3,4,5,6,16,17,18].map(i => exports.byte_at(i));",
    )

    assert values == [77, 105, 114, 97, 0, 255, 0, 7, 8, 9]


def test_one_function_calls_another_by_forward_reference_and_by_index():
    """`quad` is declared before its callee exists, so the name must resolve at emit() time."""
    module = WasmModule()
    quad = Code().local_get(0).call("double").call("double")
    module.add_function("quad", ["i32"], ["i32"], [], quad)
    double_index = module.add_function(
        "double", ["i32"], ["i32"], [], Code().local_get(0).i32_const(2).i32_mul()
    )
    octuple = Code().local_get(0).call(module.function_index("quad")).call(double_index)
    module.add_function("octuple", ["i32"], ["i32"], [], octuple)

    assert double_index == 1
    values = run_in_node(module, "return [exports.double(3), exports.quad(3), exports.octuple(3)];")

    assert values == [6, 12, 24]


def test_i32_and_f64_conversions_round_trip():
    module = WasmModule()
    module.add_function("to_f64", ["i32"], ["f64"], [], Code().local_get(0).f64_convert_i32_s())
    module.add_function("to_i32", ["f64"], ["i32"], [], Code().local_get(0).i32_trunc_f64_s())
    halve = Code().local_get(0).f64_convert_i32_s().f64_const(2.0).f64_div().i32_trunc_f64_s()
    module.add_function("halve", ["i32"], ["i32"], [], halve)

    values = run_in_node(
        module,
        "return [exports.to_f64(-5), exports.to_i32(7.9), exports.to_i32(-7.9),"
        " exports.to_i32(exports.to_f64(123456789)), exports.halve(9), exports.halve(-7)];",
    )

    assert values == [-5.0, 7, -7, 123456789, 4, -3]


def test_exported_memory_is_writable_from_javascript():
    """The memory export is what lets a host feed data in, so JS writes and wasm reads."""
    module = WasmModule()
    body = (
        Code()
        .i32_const(0).local_set(1)
        .i32_const(0).local_set(2)
        .block()
        .loop()
        .local_get(2).local_get(0).i32_ge_s().br_if(1)
        .local_get(1).local_get(2).i32_load8_u().i32_add().local_set(1)
        .local_get(2).i32_const(1).i32_add().local_set(2)
        .br(0)
        .end()
        .end()
        .local_get(1)
    )
    module.add_function("sum_range", ["i32"], ["i32"], ["i32", "i32"], body)

    values = run_in_node(
        module,
        "const view = new Uint8Array(instance.exports.memory.buffer);"
        " for (let i = 0; i < 8; i++) { view[i] = (i + 1) * 3; }"
        " return [exports.sum_range(8), exports.sum_range(3), memory.length];",
    )

    assert values[0] == 108
    assert values[1] == 18
    assert values[2] == 65536


def test_emission_is_deterministic_and_the_repeated_bytes_still_run():
    first = _sum_to_n()
    first.add_data(0, b"determinism")
    second = _sum_to_n()
    second.add_data(0, b"determinism")

    once, twice = first.emit(), first.emit()

    assert once == twice
    assert once == second.emit()
    assert run_in_node(twice, "return exports.sum_to_n(10);") == 55


def test_an_unresolvable_named_call_is_rejected_rather_than_mis_encoded():
    module = WasmModule()
    module.add_function("caller", [], ["i32"], [], Code().call("missing"))

    with pytest.raises(WasmEmitError, match="undefined function"):
        module.emit()
