"""The inert-transport refusals, each driven to its negative.

A separate process is only an isolation boundary if nothing executable crosses it. The transport
that replaced `multiprocessing` therefore refuses, in both directions, anything it cannot carry as
inert data — and the guard census found that eighteen of those refusals had no test at all. That is
the shape this project keeps finding: a boundary asserted in code nobody made fire.

Each test below removes the doubt for one of them. They are cheap on purpose: the refusals are the
boundary, so the cost of exercising them should never be a reason not to.
"""
from __future__ import annotations

import functools
import math
from pathlib import Path

import pytest

from genesis import development_bodies as bodies
from genesis import program as pg
from genesis import sandbox as sb


def _double_increment():
    return pg.program_artifact(
        pg.program(
            nodes=[
                {"op": "input", "field": "input"},
                {"op": "call", "operation": "double", "args": [0]},
                {"op": "call", "operation": "increment", "args": [1]},
            ],
            root=2,
            registry_reference=bodies.PROBE_REGISTRY,
        )
    )


# -- what may not cross on the way out ------------------------------------------------------------

def test_a_live_callable_object_is_refused_rather_than_pickled():
    """The defect the whole transport exists to close: executable state crossing the boundary."""

    class _Live:
        def __call__(self):  # pragma: no cover - never built
            return None

    with pytest.raises(sb.SandboxError, match="refuses to pickle executable state"):
        sb._wire_descriptor(_Live())


def test_a_lambda_has_no_reconstructible_identity_on_the_wire():
    with pytest.raises(sb.SandboxError, match="importable module-level symbol"):
        sb._wire_descriptor(lambda: None)


def test_a_closure_wearing_a_module_level_name_is_refused_on_the_wire():
    """The name check fires first for an ordinary nested function, so this reaches past it.

    `types.FunctionType` rebuilds a function with whatever name and closure the caller supplies —
    which is exactly what `genesis.capabilities` does to sever a capability from its module. Two
    such functions can share every field of a symbol descriptor and close over different values.
    """
    import types

    def make(bound):
        def closed():  # pragma: no cover - identity only
            return bound

        return closed

    original = make(1)
    disguised = types.FunctionType(
        original.__code__, {}, "looks_module_level", None, original.__closure__
    )
    disguised.__qualname__ = "looks_module_level"
    disguised.__module__ = "genesis.development_bodies"
    with pytest.raises(sb.SandboxError, match="closes over live values"):
        sb._wire_descriptor(disguised)


def test_a_non_finite_float_cannot_cross():
    """JSON has no NaN. Encoding one anyway would put a value on the wire that does not decode."""
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(sb.SandboxError, match="non-finite floats"):
            sb._wire_value(value)


def test_a_value_the_boundary_cannot_carry_is_named_rather_than_dropped():
    class _Opaque:
        pass

    with pytest.raises(sb.SandboxError, match="_Opaque, which cannot cross"):
        sb._wire_value(_Opaque())


@pytest.mark.parametrize(
    "value",
    [
        None, True, 3, "text", 1.5,
        b"bytes", Path("/tmp/x"),
        [1, "two"], (1, 2), {1, 2}, frozenset({3}),
        {"a": 1, "b": [2, 3]},
    ],
)
def test_what_the_boundary_does_carry_round_trips_unchanged(value):
    """The control. A boundary that refused everything would pass the tests above and be useless."""
    assert sb._decode_wire_value(sb._wire_value(value)) == value


def test_a_configured_body_and_a_program_both_survive_the_round_trip():
    """The two artifact kinds that actually run: one configured, one generated."""
    program = _double_increment()
    restored = sb._resolve_descriptor(sb._wire_descriptor(program))
    assert restored.value == program.value

    configured = bodies.migrated_improved_body
    back = sb._resolve_descriptor(sb._wire_descriptor(configured))
    assert back.dependencies == configured.dependencies
    assert dict(back.configuration) == dict(configured.configuration)

    partial = functools.partial(bodies.TableBody, {"t0"})
    assert sb._resolve_descriptor(sb._wire_descriptor(partial))().solves == {"t0"}


# -- what may not cross on the way back in ---------------------------------------------------------

def test_a_wire_value_that_is_not_inert_data_is_refused():
    with pytest.raises(ValueError, match="not inert data"):
        sb._decode_wire_value(object())


def test_an_unrecognised_wire_value_is_refused_rather_than_guessed():
    with pytest.raises(ValueError, match="unrecognised inert wire value"):
        sb._decode_wire_value({"__something_new__": 1})


def test_a_descriptor_with_no_schema_is_refused():
    with pytest.raises(ValueError, match="unrecognised wire artifact schema"):
        sb._resolve_descriptor({"kind": "symbol", "module": "genesis", "qualname": "x"})


def test_a_descriptor_of_an_unsupported_kind_is_refused():
    with pytest.raises(ValueError, match="unsupported wire artifact kind"):
        sb._resolve_descriptor({"schema": sb.WIRE_ARTIFACT_SCHEMA, "kind": "something_else"})


@pytest.mark.parametrize(
    "descriptor, match",
    [
        ({"module": "", "qualname": "x"}, "names no module"),
        ({"module": "genesis.development_bodies", "qualname": ""}, "names no importable symbol"),
        (
            {"module": "genesis.development_bodies", "qualname": "f.<locals>.g"},
            "names no importable symbol",
        ),
    ],
)
def test_a_symbol_descriptor_that_names_nothing_importable_is_refused(descriptor, match):
    with pytest.raises(ValueError, match=match):
        sb._resolve_descriptor({"schema": sb.WIRE_ARTIFACT_SCHEMA, "kind": "symbol", **descriptor})


def test_a_symbol_whose_module_changed_after_admission_is_refused():
    """The digest is what makes the symbol an identity rather than a name to look up later."""
    descriptor = sb._wire_descriptor(bodies.parent_body)
    tampered = {**descriptor, "module_source_sha256": "0" * 64}
    with pytest.raises(ValueError, match="module source changed after admission"):
        sb._resolve_descriptor(tampered)


def test_a_program_descriptor_carrying_no_program_is_refused():
    with pytest.raises(ValueError, match="carries no program"):
        sb._resolve_descriptor({"schema": sb.WIRE_ARTIFACT_SCHEMA, "kind": "program"})


def test_a_program_whose_bytes_changed_in_transit_is_refused():
    """One changed operation is a different program, and the wire says so rather than running it."""
    descriptor = sb._wire_descriptor(_double_increment())
    tampered = dict(descriptor)
    tampered["program"] = dict(descriptor["program"])
    tampered["program"]["nodes"] = [
        {"op": "input", "field": "input"},
        {"op": "call", "operation": "triple", "args": [0]},
        {"op": "call", "operation": "increment", "args": [1]},
    ]
    with pytest.raises(ValueError, match="program bytes changed in transit"):
        sb._resolve_descriptor(tampered)


@pytest.mark.parametrize(
    "field, match",
    [
        ("target_artifact_digest", "target changed after admission"),
        ("target_module_source_sha256", "target module source changed after admission"),
    ],
)
def test_a_configured_body_whose_target_changed_after_admission_is_refused(field, match):
    descriptor = sb._wire_descriptor(bodies.migrated_improved_body)
    with pytest.raises(ValueError, match=match):
        sb._resolve_descriptor({**descriptor, field: "0" * 64})


# -- the worker's own request ----------------------------------------------------------------------

def test_the_worker_refuses_a_request_it_does_not_recognise(tmp_path):
    """The child is a fixed entry point; what it will act on is not open to negotiation."""
    import json
    import subprocess
    import sys

    for request in ({"schema": "something-else"}, {"schema": sb.WORKER_REQUEST_SCHEMA}):
        finished = subprocess.run(
            [sys.executable, "-m", "genesis.sandbox", "--worker"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        reply = json.loads(finished.stdout.strip().splitlines()[-1])
        assert reply["kind"] == "bootstrap_failure"
        assert (
            "unrecognised worker request" in reply["traceback"]
            or "nonce" in reply["traceback"]
        )
