"""M060: the accepted body, compiled to WebAssembly by Python rather than by wat2wasm.

The pipeline already ran as hand-written WAT. That proved the *design* worked, but it left the
toolchain outside the organism: a text file plus an external assembler. This module removes that
dependency. Every function below is the same stage of the same pipeline, expressed as calls into
`m060_wasm_emit`, so the Python source *is* the compiler and the emitted bytes owe nothing to any
tool the repository does not contain.

Two deliberate departures from the WAT, both forced by the emitter's surface:

- **The WAT's `(global $X i32 (i32.const N))` become Python constants.** The emitter has no global
  section, and these globals were never mutated — they are the fixed memory map — so folding each
  `global.get` into its literal is behaviour-preserving.
- **`i32.gt_u` and friends are written as raw opcodes.** `Code` exposes the signed comparisons by
  name and the unsigned ones only through `op()`. The unsigned forms matter here: byte comparisons
  against 0x20 and the ASCII digit and upper-case ranges must not treat 0x80..0xff as negative.

Multi-value results (`parse` returns `(i32, i32)`, `descriptor` returns `(i32, f64)`) are declared
through `add_function(results=[...])` and consumed by popping in reverse, last result first.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from metamorphosis.m060_wasm_emit import Code, WasmEmitError, WasmModule

# -- memory map: the WAT globals, folded to literals (see module docstring) -------------------
REQUEST = 0  #: request bytes, written by the host
REQ_LEN = 256  #: i32 byte length of the request
TOKENS = 260  #: (offset, length) pairs, 8 bytes each
TOK_COUNT = 516  #: i32 token count
NODES = 520  #: AST nodes, 32 bytes each
NODE_COUNT = 2056  #: i32 node count
STEPS = 2064  #: plan steps, 48 bytes each
STEP_COUNT = 4368  #: i32 step count
RESULTS = 4376  #: f64 per step, indexed by step number
ALIASES = 5000  #: alias table, see ALIAS_TABLE

#: [len][canonical][bytes...] repeated, terminated by a zero length. Canonical operator codes are
#: add=0, maximum=1, mean=2, mul=3; `sum` and `average` are aliases onto add and mean.
ALIAS_TABLE = (
    b"\x03\x00add"
    b"\x07\x02average"
    b"\x07\x01maximum"
    b"\x04\x02mean"
    b"\x03\x03mul"
    b"\x03\x00sum"
    b"\x00"
)

# Unsigned comparisons, absent from Code's named methods.
_I32_LT_U = 0x49
_I32_GT_U = 0x4B
_I32_LE_U = 0x4D
_I32_GE_U = 0x4F

SEPARATOR = 32  #: bytes at or below this end a token
CANONICAL_MEAN = 2  #: the only ternary operator
ROUTE_COUNT = 4  #: routes 0..3 are the canonical operators; anything else is a refusal


def _tokenize() -> Code:
    """Split on bytes <= 0x20, recording (offset, length) pairs. Returns the token count."""
    # locals: len=0 i=1 start=2 count=3 entry=4
    return (
        Code()
        .i32_const(REQ_LEN).i32_load().local_set(0)
        .i32_const(0).local_set(1)
        .i32_const(0).local_set(3)
        .block()                                             # $done
        .loop()                                              # $scan
        .block()                                             # $skipped
        .loop()                                              # $skip
        .local_get(1).local_get(0).i32_ge_s().br_if(1)
        .i32_const(REQUEST).local_get(1).i32_add().i32_load8_u()
        .i32_const(SEPARATOR).op(_I32_GT_U).br_if(1)
        .local_get(1).i32_const(1).i32_add().local_set(1)
        .br(0)
        .end()
        .end()
        .local_get(1).local_get(0).i32_ge_s().br_if(1)
        .local_get(1).local_set(2)
        .block()                                             # $ended
        .loop()                                              # $take
        .local_get(1).local_get(0).i32_ge_s().br_if(1)
        .i32_const(REQUEST).local_get(1).i32_add().i32_load8_u()
        .i32_const(SEPARATOR).op(_I32_LE_U).br_if(1)
        .local_get(1).i32_const(1).i32_add().local_set(1)
        .br(0)
        .end()
        .end()
        .i32_const(TOKENS).local_get(3).i32_const(8).i32_mul().i32_add().local_set(4)
        .local_get(4).i32_const(REQUEST).local_get(2).i32_add().i32_store()
        .local_get(4).local_get(1).local_get(2).i32_sub().i32_store(offset=4)
        .local_get(3).i32_const(1).i32_add().local_set(3)
        .br(0)
        .end()
        .end()
        .i32_const(TOK_COUNT).local_get(3).i32_store()
        .local_get(3)
    )


def _token_is_number() -> Code:
    """An optional sign followed by at least one digit and nothing else."""
    # param idx=0; locals entry=1 off=2 len=3 p=4 b=5 digits=6
    return (
        Code()
        .i32_const(TOKENS).local_get(0).i32_const(8).i32_mul().i32_add().local_set(1)
        .local_get(1).i32_load().local_set(2)
        .local_get(1).i32_load(offset=4).local_set(3)
        .local_get(3).i32_eqz().if_().i32_const(0).ret().end()
        .i32_const(0).local_set(4)
        .local_get(2).i32_load8_u().local_set(5)
        .local_get(5).i32_const(45).i32_eq()
        .local_get(5).i32_const(43).i32_eq().i32_or()
        .if_()
        .local_get(3).i32_const(1).i32_eq().if_().i32_const(0).ret().end()
        .i32_const(1).local_set(4)
        .end()
        .i32_const(0).local_set(6)
        .block()
        .loop()
        .local_get(4).local_get(3).i32_ge_s().br_if(1)
        .local_get(2).local_get(4).i32_add().i32_load8_u().local_set(5)
        .local_get(5).i32_const(48).op(_I32_LT_U)
        .local_get(5).i32_const(57).op(_I32_GT_U).i32_or()
        .if_().i32_const(0).ret().end()
        .local_get(6).i32_const(1).i32_add().local_set(6)
        .local_get(4).i32_const(1).i32_add().local_set(4)
        .br(0)
        .end()
        .end()
        .local_get(6).i32_const(0).i32_gt_s()
    )


def _token_number() -> Code:
    """Decimal accumulation in i32, sign applied once at the end."""
    # param idx=0; locals entry=1 off=2 len=3 p=4 b=5 neg=6 value=7
    return (
        Code()
        .i32_const(TOKENS).local_get(0).i32_const(8).i32_mul().i32_add().local_set(1)
        .local_get(1).i32_load().local_set(2)
        .local_get(1).i32_load(offset=4).local_set(3)
        .i32_const(0).local_set(4)
        .i32_const(0).local_set(6)
        .local_get(2).i32_load8_u().local_set(5)
        .local_get(5).i32_const(45).i32_eq()
        .if_()
        .i32_const(1).local_set(6)
        .i32_const(1).local_set(4)
        .else_()
        .local_get(5).i32_const(43).i32_eq().if_().i32_const(1).local_set(4).end()
        .end()
        .i32_const(0).local_set(7)
        .block()
        .loop()
        .local_get(4).local_get(3).i32_ge_s().br_if(1)
        .local_get(7).i32_const(10).i32_mul()
        .local_get(2).local_get(4).i32_add().i32_load8_u().i32_const(48).i32_sub()
        .i32_add().local_set(7)
        .local_get(4).i32_const(1).i32_add().local_set(4)
        .br(0)
        .end()
        .end()
        .local_get(6).if_("f64")
        .i32_const(0).local_get(7).i32_sub().f64_convert_i32_s()
        .else_()
        .local_get(7).f64_convert_i32_s()
        .end()
    )


def _alias_index() -> Code:
    """Byte comparison against the alias table, lowering ASCII upper case. -1 when absent."""
    # param idx=0; locals entry=1 off=2 len=3 cur=4 slen=5 canon=6 p=7 left=8 right=9 ok=10
    return (
        Code()
        .i32_const(TOKENS).local_get(0).i32_const(8).i32_mul().i32_add().local_set(1)
        .local_get(1).i32_load().local_set(2)
        .local_get(1).i32_load(offset=4).local_set(3)
        .i32_const(ALIASES).local_set(4)
        .block()                                             # $missing
        .loop()                                              # $entries
        .local_get(4).i32_load8_u().local_set(5)
        .local_get(5).i32_eqz().br_if(1)
        .local_get(4).i32_load8_u(offset=1).local_set(6)
        .local_get(5).local_get(3).i32_eq().local_set(10)
        .local_get(10).if_()
        .i32_const(0).local_set(7)
        .block()                                             # $compared
        .loop()                                              # $chars
        .local_get(7).local_get(3).i32_ge_s().br_if(1)
        .local_get(4).i32_const(2).i32_add().local_get(7).i32_add().i32_load8_u().local_set(8)
        .local_get(2).local_get(7).i32_add().i32_load8_u().local_set(9)
        .local_get(9).i32_const(65).op(_I32_GE_U)
        .local_get(9).i32_const(90).op(_I32_LE_U).i32_and()
        .if_().local_get(9).i32_const(32).i32_add().local_set(9).end()
        .local_get(8).local_get(9).i32_ne()
        .if_().i32_const(0).local_set(10).br(2).end()        # br out of if, loop, to $compared
        .local_get(7).i32_const(1).i32_add().local_set(7)
        .br(0)
        .end()
        .end()
        .end()
        .local_get(10).if_().local_get(6).ret().end()
        .local_get(4).i32_const(2).i32_add().local_get(5).i32_add().local_set(4)
        .br(0)
        .end()
        .end()
        .i32_const(-1)
    )


def _arity() -> Code:
    """Arity per canonical operator: add 2, maximum 2, mean 3, mul 2."""
    return (
        Code()
        .local_get(0).i32_const(CANONICAL_MEAN).i32_eq()
        .if_("i32").i32_const(3).else_().i32_const(2).end()
    )


def _parse() -> Code:
    """Recursive prefix descent. Returns (node index, next cursor); traps on a malformed request."""
    # param cursor=0; locals node=1 base=2 op=3 n=4 slot=5 child=6 next=7
    return (
        Code()
        .local_get(0).i32_const(TOK_COUNT).i32_load().i32_ge_s().if_().unreachable().end()
        .i32_const(NODE_COUNT).i32_load().local_set(1)
        .i32_const(NODE_COUNT).local_get(1).i32_const(1).i32_add().i32_store()
        .i32_const(NODES).local_get(1).i32_const(32).i32_mul().i32_add().local_set(2)
        .local_get(0).call("token_is_number")
        .if_()
        .local_get(2).i32_const(0).i32_store()
        .local_get(2).local_get(0).call("token_number").f64_store(offset=24)
        .local_get(1).local_get(0).i32_const(1).i32_add().ret()
        .end()
        .local_get(0).call("alias_index").local_set(3)
        .local_get(3).i32_const(0).i32_lt_s().if_().unreachable().end()
        .local_get(2).i32_const(1).i32_store()
        .local_get(2).local_get(3).i32_store(offset=4)
        .local_get(3).call("arity").local_set(4)
        .local_get(0).i32_const(1).i32_add().local_set(7)
        .i32_const(0).local_set(5)
        .block()
        .loop()
        .local_get(5).local_get(4).i32_ge_s().br_if(1)
        .local_get(7).call("parse")
        .local_set(7)                                        # second result: the new cursor
        .local_set(6)                                        # first result: the child node
        .local_get(2).local_get(5).i32_const(4).i32_mul().i32_add()
        .local_get(6).i32_store(offset=8)
        .local_get(5).i32_const(1).i32_add().local_set(5)
        .br(0)
        .end()
        .end()
        .local_get(1).local_get(7)
    )


def _interpret() -> Code:
    """Tokens to an AST. Returns the root node, or -1 when tokens are left over."""
    # locals root=0 cursor=1
    return (
        Code()
        .i32_const(NODE_COUNT).i32_const(0).i32_store()
        .call("tokenize").drop()
        .i32_const(0).call("parse")
        .local_set(1)
        .local_set(0)
        .local_get(1).i32_const(TOK_COUNT).i32_load().i32_ne()
        .if_().i32_const(-1).ret().end()
        .local_get(0)
    )


def _emit_step() -> Code:
    """Postorder emit of one node into the step table. Returns its step index, -1 for a literal.

    Children are emitted first and held in locals, so a parent always takes a later step index
    than every child it references — preorder indices made nested requests read results that had
    not been written yet.
    """
    # param node=0; locals base=1 n=2 step=3 sbase=4 k0=5 k1=6 k2=7 v0=8 v1=9 v2=10
    return (
        Code()
        .i32_const(NODES).local_get(0).i32_const(32).i32_mul().i32_add().local_set(1)
        .local_get(1).i32_load().i32_eqz().if_().i32_const(-1).ret().end()
        .local_get(1).i32_load(offset=4).call("arity").local_set(2)
        .local_get(1).i32_load(offset=8).call("descriptor")
        .local_set(8).local_set(5)
        .local_get(1).i32_load(offset=12).call("descriptor")
        .local_set(9).local_set(6)
        .local_get(2).i32_const(3).i32_eq()
        .if_()
        .local_get(1).i32_load(offset=16).call("descriptor")
        .local_set(10).local_set(7)
        .else_()
        .i32_const(0).local_set(7)
        .f64_const(0.0).local_set(10)
        .end()
        .i32_const(STEP_COUNT).i32_load().local_set(3)
        .i32_const(STEP_COUNT).local_get(3).i32_const(1).i32_add().i32_store()
        .i32_const(STEPS).local_get(3).i32_const(48).i32_mul().i32_add().local_set(4)
        .local_get(4).local_get(1).i32_load(offset=4).i32_store()
        .local_get(4).local_get(5).i32_store(offset=4)
        .local_get(4).local_get(8).f64_store(offset=8)
        .local_get(4).local_get(6).i32_store(offset=20)
        .local_get(4).local_get(9).f64_store(offset=24)
        .local_get(4).local_get(7).i32_store(offset=36)
        .local_get(4).local_get(10).f64_store(offset=40)
        .local_get(3)
    )


def _descriptor() -> Code:
    """A child is either a literal (kind 0, its value) or a reference to the step computing it."""
    # param child=0; locals cbase=1
    return (
        Code()
        .i32_const(NODES).local_get(0).i32_const(32).i32_mul().i32_add().local_set(1)
        .local_get(1).i32_load().i32_eqz()
        .if_()
        .i32_const(0).local_get(1).f64_load(offset=24).ret()
        .end()
        .i32_const(1).local_get(0).call("emit").f64_convert_i32_s()
    )


def _plan() -> Code:
    """Reset the step table and emit the tree. Returns the root step index."""
    return (
        Code()
        .i32_const(STEP_COUNT).i32_const(0).i32_store()
        .local_get(0).call("emit")
    )


def _allocate() -> Code:
    """The accepted policy is double_plan_length, floored at one step of budget."""
    return (
        Code()
        .local_get(0).i32_const(2).i32_mul().i32_const(1).i32_gt_s()
        .if_("i32")
        .local_get(0).i32_const(2).i32_mul()
        .else_()
        .i32_const(1)
        .end()
    )


def _select() -> Code:
    """The route table is the identity over canonical operators; -1 refuses anything else."""
    return (
        Code()
        .local_get(0).i32_const(0).i32_ge_s()
        .local_get(0).i32_const(ROUTE_COUNT).i32_lt_s().i32_and()
        .if_("i32").local_get(0).else_().i32_const(-1).end()
    )


#: The arithmetic the body computes with, keyed by what each operation *does* rather than by an
#: opcode. `arithmetic_opcodes` resolves these against a substrate scan, so the four bytes are
#: discovered rather than written here. The structural instructions around them — loads, stores,
#: branches, calls — remain authored, and the protocol says so.
ARITHMETIC = {
    "add": lambda a, b: a + b,
    "max": lambda a, b: max(a, b),
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b if b else None,
}


def arithmetic_opcodes(observations: Mapping[str, Sequence[float]],
                       pairs: Sequence[tuple[float, float]]) -> dict[str, int]:
    """Identify the four operations the body needs, from probed behaviour alone.

    Each is required to be uniquely determined: if two candidate opcodes agree with an operation
    on every probe pair, the evidence does not name one and the caller is told so rather than
    handed an arbitrary choice.
    """
    resolved: dict[str, int] = {}
    for label, function in ARITHMETIC.items():
        expected = []
        usable = True
        for left, right in pairs:
            value = function(left, right)
            if value is None:
                usable = False
                break
            expected.append(value)
        if not usable:
            raise WasmEmitError(f"the probe pairs cannot characterise {label}")
        matches = [
            name for name, values in observations.items()
            if len(values) == len(expected)
            and all(abs(a - b) < 1e-12 for a, b in zip(values, expected))
        ]
        if len(matches) != 1:
            raise WasmEmitError(f"{label} is not uniquely determined by the probes: {matches}")
        resolved[label] = int(matches[0], 16)
    return resolved


#: What the compiler falls back to when no scan is supplied. These are the same four bytes a scan
#: resolves to; keeping them here lets the emitter be exercised without a substrate, and a test
#: asserts the two agree.
AUTHORED_ARITHMETIC = {"add": 0xA0, "max": 0xA5, "mul": 0xA2, "div": 0xA3}


def _tool(opcodes: Mapping[str, int]) -> Code:
    """Dispatch by route: 0 add, 1 maximum, 3 mul, and 2 (mean) as the fallthrough."""
    # params route=0 a=1 b=2 c=3
    return (
        Code()
        .local_get(0).i32_const(0).i32_eq()
        .if_().local_get(1).local_get(2).op(opcodes["add"]).ret().end()
        .local_get(0).i32_const(1).i32_eq()
        .if_().local_get(1).local_get(2).op(opcodes["max"]).ret().end()
        .local_get(0).i32_const(3).i32_eq()
        .if_().local_get(1).local_get(2).op(opcodes["mul"]).ret().end()
        .local_get(1).local_get(2).op(opcodes["add"]).local_get(3).op(opcodes["add"])
        .f64_const(3.0).op(opcodes["div"])
    )


def _execute() -> Code:
    """Walk the steps in order, resolving arguments and calling tools by route."""
    # params root=0 budget=1; locals count=2 i=3 sbase=4 route=5 a=6 b=7 c=8 abase=9
    return (
        Code()
        .i32_const(STEP_COUNT).i32_load().local_set(2)
        .local_get(2).local_get(1).i32_gt_s().if_().unreachable().end()
        .i32_const(0).local_set(3)
        .block()
        .loop()
        .local_get(3).local_get(2).i32_ge_s().br_if(1)
        .i32_const(STEPS).local_get(3).i32_const(48).i32_mul().i32_add().local_set(4)
        .local_get(4).i32_load().call("select").local_set(5)
        .local_get(5).i32_const(0).i32_lt_s().if_().unreachable().end()
        .local_get(4).local_set(9)
        .local_get(9).i32_const(0).call("argument").local_set(6)
        .local_get(9).i32_const(1).call("argument").local_set(7)
        .local_get(9).i32_const(2).call("argument").local_set(8)
        .i32_const(RESULTS).local_get(3).i32_const(8).i32_mul().i32_add()
        .local_get(5).local_get(6).local_get(7).local_get(8).call("tool")
        .f64_store()
        .local_get(3).i32_const(1).i32_add().local_set(3)
        .br(0)
        .end()
        .end()
        .i32_const(RESULTS).local_get(0).i32_const(8).i32_mul().i32_add().f64_load()
    )


def _argument() -> Code:
    """Read argument `slot` of a step: kind 0 is the literal, otherwise index into RESULTS."""
    # params sbase=0 slot=1; locals abase=2 kind=3 value=4
    return (
        Code()
        .local_get(0).local_get(1).i32_const(16).i32_mul().i32_add().local_set(2)
        .local_get(2).i32_load(offset=4).local_set(3)
        .local_get(2).f64_load(offset=8).local_set(4)
        .local_get(3).i32_eqz()
        .if_("f64")
        .local_get(4)
        .else_()
        .i32_const(RESULTS).local_get(4).i32_trunc_f64_s().i32_const(8).i32_mul().i32_add()
        .f64_load()
        .end()
    )


def _critique() -> Code:
    """The accepted policy is round_two, matching Math.round((v + EPSILON) * 100) / 100."""
    return (
        Code()
        .local_get(0).local_get(0).f64_trunc().f64_eq()
        .if_().local_get(0).ret().end()
        .local_get(0).f64_const(2.220446049250313e-16).f64_add()
        .f64_const(100.0).f64_mul()
        .f64_const(0.5).f64_add()
        .f64_floor()
        .f64_const(100.0).f64_div()
    )


def _run() -> Code:
    """The whole pipeline, returning NaN when a stage refuses rather than trapping."""
    # locals root=0 step=1 budget=2
    return (
        Code()
        .call("interpret").local_set(0)
        .local_get(0).i32_const(0).i32_lt_s()
        .if_().f64_const(float("nan")).ret().end()
        .local_get(0).call("plan").local_set(1)
        .local_get(1).i32_const(0).i32_lt_s()
        .if_().f64_const(float("nan")).ret().end()
        .i32_const(STEP_COUNT).i32_load().call("allocate").local_set(2)
        .local_get(1).local_get(2).call("execute").call("critique")
    )


def build_module(opcodes: Mapping[str, int] | None = None) -> WasmModule:
    """Assemble the module: one function per pipeline stage, plus the internal helpers.

    Exports mirror the WAT exactly — the eleven stages and `memory`. The helpers stay unexported
    but remain separate functions, because the call boundary between stages is the point.

    `opcodes` carries the arithmetic a substrate scan resolved. Everything else this function
    emits — loads, stores, branches, loops, calls, the memory layout — is authored, and that
    division is the honest boundary of the experiment.
    """
    resolved = dict(AUTHORED_ARITHMETIC if opcodes is None else opcodes)
    missing = [label for label in ARITHMETIC if label not in resolved]
    if missing:
        raise WasmEmitError(f"the arithmetic is not fully resolved: {missing}")
    module = WasmModule(memory_pages=1)
    module.add_data(ALIASES, ALIAS_TABLE)

    module.add_function("tokenize", [], ["i32"], ["i32"] * 5, _tokenize())
    module.add_function("token_is_number", ["i32"], ["i32"], ["i32"] * 6, _token_is_number())
    module.add_function("token_number", ["i32"], ["f64"], ["i32"] * 7, _token_number())
    module.add_function("alias_index", ["i32"], ["i32"], ["i32"] * 10, _alias_index())
    module.add_function("arity", ["i32"], ["i32"], [], _arity(), export=False)
    module.add_function("parse", ["i32"], ["i32", "i32"], ["i32"] * 7, _parse(), export=False)
    module.add_function("interpret", [], ["i32"], ["i32"] * 2, _interpret())
    module.add_function(
        "emit", ["i32"], ["i32"], ["i32"] * 7 + ["f64"] * 3, _emit_step(), export=False
    )
    module.add_function("descriptor", ["i32"], ["i32", "f64"], ["i32"], _descriptor(), export=False)
    module.add_function("plan", ["i32"], ["i32"], [], _plan())
    module.add_function("allocate", ["i32"], ["i32"], [], _allocate())
    module.add_function("select", ["i32"], ["i32"], [], _select())
    module.add_function("tool", ["i32", "f64", "f64", "f64"], ["f64"], [], _tool(resolved), export=False)
    module.add_function(
        "execute",
        ["i32", "i32"],
        ["f64"],
        ["i32", "i32", "i32", "i32", "f64", "f64", "f64", "i32"],
        _execute(),
    )
    module.add_function(
        "argument", ["i32", "i32"], ["f64"], ["i32", "i32", "f64"], _argument(), export=False
    )
    module.add_function("critique", ["f64"], ["f64"], [], _critique())
    module.add_function("run", [], ["f64"], ["i32"] * 3, _run())
    return module


def compile_body(opcodes: Mapping[str, int] | None = None) -> bytes:
    """Emit the whole accepted body as one WebAssembly module.

    `opcodes` carries what a substrate scan resolved. Omitting it falls back to the authored
    bytes, and a test asserts a scan produces exactly those, so the fallback cannot drift away
    from what discovery would have found.
    """
    return build_module(opcodes).emit()
