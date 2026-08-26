"""The host must execute any carrier under the meta-schema and prefer none of them."""

from __future__ import annotations

import pytest

from metamorphosis import carrier_host as host
from metamorphosis import m113_carrier_devkit as devkit


def a_carrier() -> dict:
    return host.validate_carrier(
        {
            "surface": {
                "kind": "text_line",
                "ok_token": "ack",
                "error_token": "nak",
                "field_separator": ":",
                "pair_separator": "=",
                "action_key": "verb",
                "argument_key": "operand",
                "status_key": "st",
            },
            "cells": [
                {"name": "gate", "size": 2},
                {"name": "level", "size": 4},
                {"name": "hidden", "size": 3},
            ],
            "initial": [0, 0, 0],
            "visible": [True, True, False],
            "errors": ["locked", "range"],
            "actions": [
                {
                    "name": "unlock",
                    "arity": 0,
                    "guard": [],
                    "effect": [{"cell": 0, "mode": "set", "operand": 1}],
                    "error": "locked",
                },
                {
                    "name": "raise_it",
                    "arity": 1,
                    "arg_size": 4,
                    "guard": [{"cell": 0, "relation": "eq", "value": 1}],
                    "effect": [
                        {"cell": 1, "mode": "arg", "operand": 0},
                        {"cell": 2, "mode": "add", "operand": 1},
                    ],
                    "error": "locked",
                },
                {
                    "name": "reset",
                    "arity": 0,
                    "guard": [{"cell": 1, "relation": "ge", "value": 2}],
                    "effect": [
                        {"cell": 0, "mode": "set", "operand": 0},
                        {"cell": 1, "mode": "set", "operand": 0},
                    ],
                    "error": "range",
                },
            ],
        }
    )


# ---------------------------------------------------------------- validation fails closed


@pytest.mark.parametrize(
    "mutation",
    [
        {"cells": []},
        {"cells": [{"name": "a", "size": 9}]},
        {"visible": [False, False, False]},
        {"initial": [0, 0]},
        {"errors": []},
        {"actions": []},
    ],
)
def test_a_payload_outside_the_meta_schema_is_not_a_carrier(mutation):
    raw = {key: value for key, value in a_carrier().items() if key not in ("schema", "carrier_digest")}
    raw.update(mutation)
    with pytest.raises(host.CarrierError):
        host.validate_carrier(raw)


def test_an_action_may_not_name_an_undeclared_error():
    raw = {key: value for key, value in a_carrier().items() if key not in ("schema", "carrier_digest")}
    raw["actions"][0]["error"] = "invented"
    with pytest.raises(host.CarrierError):
        host.validate_carrier(raw)


def test_a_nullary_action_may_not_assign_from_an_argument_it_does_not_take():
    raw = {key: value for key, value in a_carrier().items() if key not in ("schema", "carrier_digest")}
    raw["actions"][0]["effect"] = [{"cell": 1, "mode": "arg", "operand": 0}]
    with pytest.raises(host.CarrierError):
        host.validate_carrier(raw)


def test_a_cell_may_not_collide_with_a_surface_key():
    raw = {key: value for key, value in a_carrier().items() if key not in ("schema", "carrier_digest")}
    raw["cells"][0]["name"] = raw["surface"]["status_key"]
    with pytest.raises(host.CarrierError):
        host.validate_carrier(raw)


# ---------------------------------------------------------------- semantics are total


def test_no_request_can_make_the_host_raise():
    carrier = a_carrier()
    session = host.open_session(carrier, "opaque-0000000000000000", 40)
    for request in ("", "junk", "unlock", "unlock:x", "unlock:1:2", "\x00", "9" * 40, "{}"):
        assert isinstance(session.send(request), str)


def test_a_guard_refuses_and_leaves_the_state_alone():
    carrier = a_carrier()
    session = host.open_session(carrier, "opaque-0000000000000000", 10)
    refused = session.send("raise_it:2")
    assert refused == "nak:locked"
    assert session.send("unlock:0") == "ack:gate=1:level=0"


def test_an_effect_reads_the_state_as_it_was_before_the_action():
    carrier = a_carrier()
    state = (1, 0, 0)
    action = host.find_action(carrier, "raise_it")
    assert host.apply_effect(carrier, state, action, 3) == (1, 3, 1)


@pytest.mark.parametrize("kind", host.SURFACE_KINDS)
def test_every_surface_round_trips_a_request(kind):
    raw = {key: value for key, value in a_carrier().items() if key not in ("schema", "carrier_digest")}
    raw["surface"] = dict(raw["surface"], kind=kind)
    carrier = host.validate_carrier(raw)
    for name, argument in host.action_alphabet(carrier):
        encoded = host.encode_request(carrier, name, argument)
        assert host.decode_request(carrier, encoded) == (name, argument)


# ---------------------------------------------------------------- closure is a fixed point


def test_reachability_closes_by_emptying_the_frontier_not_by_a_bound():
    carrier = a_carrier()
    reachability = host.reachable_states(carrier)
    assert reachability["closed"] is True
    assert reachability["saturated_at_ceiling"] is False
    assert reachability["state_count"] > reachability["max_depth"]


def test_a_witness_sequence_actually_reaches_its_state():
    carrier = a_carrier()
    closure = host.observation_closure(carrier)
    for observed, state in closure["reachable_representatives"].items():
        sequence = host.witness_sequence(closure["reachability"], state)
        current = host.initial_state(carrier)
        for name, argument in sequence:
            outcome = host.step(carrier, current, name, argument)
            assert outcome["accepted"]
            current = outcome["state"]
        assert host.observation(carrier, current) == observed


def test_an_unreachable_observation_is_unreachable_by_exhaustion():
    carrier = a_carrier()
    closure = host.observation_closure(carrier)
    assert closure["unreachable_observations"]
    reachable = set(closure["reachable_observations"])
    for observed in closure["unreachable_observations"]:
        assert observed not in reachable
    assert len(reachable) + len(closure["unreachable_observations"]) == (
        closure["observation_space_size"]
    )


def test_the_ceiling_is_a_termination_guarantee_and_reports_saturation():
    carrier = a_carrier()
    starved = host.reachable_states(carrier, ceiling=2)
    assert starved["saturated_at_ceiling"] is True
    assert starved["closed"] is False


# ---------------------------------------------------------------- the session reveals nothing


def test_a_session_holds_no_attribute_that_is_a_carrier():
    """The honest form of the claim, and not a stronger one.

    Python closures are introspectable: `session._send.__closure__` does contain the carrier, and
    no amount of `__slots__` changes that. So this asserts what is actually true -- the session has
    no instance dictionary and no attribute, public or private, that *is* a carrier -- and the
    boundary that matters is enforced where it can be, by the source audit in
    `scripts/audit_m113_boundaries.py`.
    """
    carrier = a_carrier()
    session = host.open_session(carrier, "opaque-0000000000000000", 4)
    assert not hasattr(session, "__dict__")
    assert set(host.Session.__slots__) == {
        "_send",
        "_describe",
        "_budget",
        "_used",
        "_transcript",
        "carrier_ref",
    }
    for name in host.Session.__slots__:
        value = getattr(session, name)
        assert not (isinstance(value, dict) and value.get("schema") == host.SCHEMA)
    assert {
        name for name in dir(session) if not name.startswith("_")
    } == {
        "budget",
        "carrier_ref",
        "describe",
        "invocations_left",
        "invocations_used",
        "send",
        "transcript",
        "transcript_digest",
    }


def test_the_meta_channel_carries_the_wire_and_nothing_about_behaviour():
    carrier = a_carrier()
    meta = host.meta_channel(carrier)
    assert sorted(meta) == ["actions", "schema", "surface"]
    assert sorted(meta["actions"][0]) == ["arg_size", "arity", "name"]
    rendered = host.canonical_json(meta)
    for absent in ("gate", "level", "hidden", "locked", "range", "guard", "effect", "visible"):
        assert absent not in rendered


def test_a_session_refuses_one_invocation_past_its_budget():
    carrier = a_carrier()
    session = host.open_session(carrier, "opaque-0000000000000000", 2)
    session.send("unlock:0")
    session.send("unlock:0")
    with pytest.raises(host.BudgetExhausted):
        session.send("unlock:0")


def test_a_restart_costs_an_invocation_from_the_same_budget():
    carrier = a_carrier()
    channel = host.Channel(carrier, "opaque-0000000000000000", 6)
    session = channel.restart()
    session.send("unlock:0")
    assert channel.invocations_used == 2
    channel.restart()
    assert channel.invocations_used == 3
    assert channel.restarts == 2


def test_a_restart_returns_the_carrier_to_its_initial_configuration():
    carrier = a_carrier()
    channel = host.Channel(carrier, "opaque-0000000000000000", 20)
    session = channel.restart()
    session.send("unlock:0")
    assert session.send("raise_it:2") == "ack:gate=1:level=2"
    fresh = channel.restart()
    assert fresh.send("raise_it:2") == "nak:locked"


# ---------------------------------------------------------------- the host prefers no carrier


def test_the_structural_signature_ignores_names():
    carrier = a_carrier()
    raw = {key: value for key, value in carrier.items() if key not in ("schema", "carrier_digest")}
    renamed = {
        "surface": dict(raw["surface"], ok_token="yes", error_token="no1"),
        "cells": [dict(item, name="c%d" % index) for index, item in enumerate(raw["cells"])],
        "initial": raw["initial"],
        "visible": raw["visible"],
        "errors": ["e0", "e1"],
        "actions": [
            dict(item, name="a%d" % index, error="e%d" % raw["errors"].index(item["error"]))
            for index, item in enumerate(raw["actions"])
        ],
    }
    other = host.validate_carrier(renamed)
    assert other["carrier_digest"] != carrier["carrier_digest"]
    assert host.structural_signature(other) == host.structural_signature(carrier)


def test_the_devkit_emits_structurally_distinct_carriers():
    signatures = {
        host.structural_signature(devkit.development_carrier("host-distinct:%d" % index))
        for index in range(120)
    }
    assert len(signatures) == 120
