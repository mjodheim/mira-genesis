"""The M122 acceptance claim, plus the guard M120 did not have.

Two claims, and the second is the one M120's closure bought:

    for every value V satisfying CANDIDATE_SCHEMA,
    carrier_host.validate_carrier(decode_machine(V)) returns, and never raises

    and the schema's own census stays inside what this route has been observed to enforce

M120 established the first and lost on the second. Its census drifted from five array-of-object
levels to eight as the representation changed, nothing in the apparatus said so, and a single-use
readiness gate spent sixteen requests discovering it.
"""

from __future__ import annotations

import ast
import itertools
import json
import random
from pathlib import Path

import pytest

from metamorphosis import carrier_host as host
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m116_schema as schema_tools
from metamorphosis import m122_carrier_contract as contract
from metamorphosis import m122_devkit as devkit

ROOT = Path(__file__).resolve().parents[1]


def _valid(candidate) -> bool:
    ok, _, _ = schema_tools.instance_is_valid({"machines": [candidate]},
                                              contract.CANDIDATE_SCHEMA)
    return ok


def _action(*, arg_size, guard, effect, name="op", error_index=0):
    return {"name": name, "arg_size": arg_size, "guard": list(guard),
            "effect": list(effect), "error_index": error_index}


def _machine(*, cells, hidden, errors, actions, surface=None):
    return {
        "surface": surface or {
            "kind": "json_object", "ok_token": "ok", "error_token": "er",
            "field_separator": ",", "pair_separator": "=",
            "action_key": "act", "argument_key": "arg", "status_key": "status",
        },
        "cells": list(cells), "hidden": list(hidden), "errors": list(errors),
        "actions": list(actions),
    }


# ---------------------------------------------------------------------------------------------
# The census guard: the thing M120 closed on
# ---------------------------------------------------------------------------------------------

def test_the_schema_stays_inside_the_nesting_this_route_enforces():
    """M120 asked for eight array-of-object levels and the route refused. Five is the evidence."""
    census = schema_tools.census(contract.candidate_schema())
    assert census["array_of_object_levels"] <= contract.CERTIFIED_ARRAY_OF_OBJECT_LEVELS
    assert contract.CERTIFIED_ARRAY_OF_OBJECT_LEVELS == 5


def test_the_flattened_schema_is_no_deeper_than_the_one_the_route_did_enforce():
    """M115's schema ran under M116 and M119 and was certified by M118's readiness gate."""
    m115 = json.loads((ROOT / "experiments" / "M115" / "OUTPUT_SCHEMA.json").read_text(
        encoding="utf-8"))
    inherited = schema_tools.census(m115)
    mine = schema_tools.census(contract.candidate_schema())
    assert mine["array_of_object_levels"] <= inherited["array_of_object_levels"]
    assert mine["max_nesting_depth"] <= inherited["max_nesting_depth"]


def test_the_census_guard_refuses_a_schema_that_outgrew_the_route(monkeypatch):
    """A guard that cannot fail is not a guard."""
    monkeypatch.setattr(contract, "CERTIFIED_ARRAY_OF_OBJECT_LEVELS", 4)
    with pytest.raises(contract.ContractError, match="array-of-object levels"):
        contract._assert_within_the_certified_census()


def test_the_m120_schema_would_be_refused_by_this_guard():
    """The concrete regression: the predecessor's own schema must not pass M122's check."""
    from metamorphosis import m120_carrier_contract as m120
    census = schema_tools.census(m120.candidate_schema())
    assert census["array_of_object_levels"] > contract.CERTIFIED_ARRAY_OF_OBJECT_LEVELS


def test_the_schema_uses_no_keyword_the_route_has_not_been_shown_to_enforce():
    census = schema_tools.census(contract.candidate_schema())
    assert census["composition_constructs"] == 0
    structural = {"properties"}
    used = {name for name, count in census["keyword_counts"].items() if count}
    unproven = used - set(contract.PROVEN_FEATURE_CLASSES) - structural
    assert not unproven, sorted(unproven)
    assert census["keyword_counts"]["uniqueItems"] == 0


def test_the_schema_states_no_relation_between_two_fields():
    text = json.dumps(contract.CANDIDATE_SCHEMA)
    for banned in ('"$ref"', '"if"', '"then"', '"dependentRequired"', '"contains"',
                   '"minContains"'):
        assert banned not in text


def test_there_is_exactly_one_actions_array():
    """The split into two was what took the census from five levels to eight."""
    machine = contract.CANDIDATE_SCHEMA["properties"]["machines"]["items"]["properties"]
    assert "actions" in machine
    assert "conditional_actions" not in machine
    # The family stays narrowed at four to six, as M120 narrowed it; the host permits two to
    # six, and M119's degenerate bank is why the floor is not the host's.
    assert machine["actions"]["minItems"] == contract.MIN_ACTIONS == 4
    assert machine["actions"]["maxItems"] == contract.MAX_ACTIONS == 6
    assert host.MIN_ACTIONS <= contract.MIN_ACTIONS
    assert contract.MAX_ACTIONS <= host.MAX_ACTIONS
    assert machine["actions"]["items"]["properties"]["guard"]["minItems"] == 0


# ---------------------------------------------------------------------------------------------
# The acceptance claim
# ---------------------------------------------------------------------------------------------

def test_the_family_is_a_narrowing_of_the_frozen_host_meta_schema():
    assert host.MIN_CELLS <= contract.MIN_CELLS <= contract.MAX_CELLS <= host.MAX_CELLS
    assert host.MIN_ACTIONS <= contract.MIN_ACTIONS <= contract.MAX_ACTIONS <= host.MAX_ACTIONS
    assert set(contract.CELL_SIZES) <= set(range(host.MIN_CELL_DOMAIN, host.MAX_CELL_DOMAIN + 1))
    assert set(contract.ARG_SIZES) - {0} <= set(
        range(host.MIN_ARG_DOMAIN, host.MAX_ARG_DOMAIN + 1))
    assert contract.MIN_CELLS - contract.MAX_HIDDEN_CELLS >= 2


def test_the_host_refusal_census_is_still_complete():
    source = ast.parse((ROOT / "metamorphosis" / "carrier_host.py").read_text(encoding="utf-8"))
    literals = set()
    for node in ast.walk(source):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        if getattr(node.exc.func, "id", None) != "CarrierError" or not node.exc.args:
            continue
        first = node.exc.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            literals.add(first.value)
    assert literals == set(contract.HOST_REFUSALS)


def test_every_corner_of_the_constraint_relevant_space_decodes_into_an_accepted_carrier():
    """Exhaustive over the dimensions the host's relations depend on."""
    checked = 0
    for cell_count in range(contract.MIN_CELLS, contract.MAX_CELLS + 1):
        for size in contract.CELL_SIZES:
            for arg_size in contract.ARG_SIZES:
                for mode in host.EFFECT_MODES:
                    for extreme in (0, max(contract.CELL_INDICES)):
                        cells = [{"name": "c%d" % i, "size": size,
                                  "initial": max(contract.CELL_VALUES)}
                                 for i in range(cell_count)]
                        guard = [{"cell": extreme, "relation": relation,
                                  "value": max(contract.CELL_VALUES)}
                                 for relation in host.GUARD_RELATIONS[:3]]
                        effect = [{"cell": extreme, "mode": mode,
                                   "operand": max(contract.CELL_VALUES)}]
                        candidate = _machine(
                            cells=cells,
                            hidden=[extreme] if extreme % 2 == 0 else [],
                            errors=["e0"],
                            actions=[_action(arg_size=arg_size,
                                             guard=guard if index % 2 else [],
                                             effect=effect, name="a%d" % index,
                                             error_index=max(contract.ERROR_INDICES))
                                     for index in range(contract.MIN_ACTIONS)])
                        assert _valid(candidate), "the fixture left the candidate schema"
                        host.validate_carrier(contract.decode_machine(candidate))
                        checked += 1
    # 2 cell counts x 3 sizes x 4 argument domains x 5 effect modes x 2 index extremes.
    assert checked == 240


def test_an_action_with_no_guard_at_all_is_accepted():
    """M120 could not express this without splitting the array. It is the whole point of M122."""
    candidate = _machine(
        cells=[{"name": "c%d" % i, "size": 3, "initial": 0} for i in range(3)],
        hidden=[], errors=["e0"],
        actions=[_action(arg_size=0, guard=[],
                         effect=[{"cell": 0, "mode": "add", "operand": 1}], name="a%d" % i)
                 for i in range(4)])
    assert _valid(candidate)
    carrier = host.validate_carrier(contract.decode_machine(candidate))
    assert all(action["guard"] == [] for action in carrier["actions"])


def test_name_and_token_collisions_cannot_reach_a_host_refusal():
    surface = {"kind": "text_line", "ok_token": "same", "error_token": "same",
               "field_separator": "|", "pair_separator": "/",
               "action_key": "dup", "argument_key": "dup", "status_key": "dup"}
    candidate = _machine(
        cells=[{"name": "dup", "size": 2, "initial": 1} for _ in range(contract.MAX_CELLS)],
        hidden=[0],
        errors=["same"] * contract.MAX_ERRORS,
        actions=[_action(arg_size=2, guard=[{"cell": 0, "relation": "eq", "value": 0}],
                         effect=[{"cell": 0, "mode": "arg", "operand": 0}], name="dup")
                 for _ in range(contract.MAX_ACTIONS)],
        surface=surface)
    assert _valid(candidate)
    carrier = host.validate_carrier(contract.decode_machine(candidate))
    assert len({c["name"] for c in carrier["cells"]}) == len(carrier["cells"])
    assert len({a["name"] for a in carrier["actions"]}) == len(carrier["actions"])
    assert len(set(carrier["errors"])) == len(carrier["errors"])
    assert carrier["surface"]["ok_token"] != carrier["surface"]["error_token"]


def test_a_nullary_action_whose_effect_wants_an_argument_is_given_one():
    candidate = _machine(
        cells=[{"name": "c%d" % i, "size": 3, "initial": 0} for i in range(3)],
        hidden=[], errors=["e0"],
        actions=[_action(arg_size=0, guard=[],
                         effect=[{"cell": 1, "mode": "arg", "operand": 0}], name="a0")]
                + [_action(arg_size=0, guard=[],
                           effect=[{"cell": 0, "mode": "add", "operand": 1}], name="a%d" % i)
                   for i in range(1, 4)])
    assert _valid(candidate)
    carrier = host.validate_carrier(contract.decode_machine(candidate))
    assert carrier["actions"][0]["arity"] == 1
    assert carrier["actions"][0]["arg_size"] == host.MIN_ARG_DOMAIN
    assert carrier["actions"][-1]["arity"] == 0


@pytest.mark.parametrize("mode", devkit.MODES)
def test_a_large_deterministic_fuzz_never_reaches_a_host_refusal(mode):
    for candidate in devkit.development_candidates("m122-contract-fuzz-", 400, mode=mode):
        assert _valid(candidate)
        host.validate_carrier(contract.decode_machine(candidate))


def test_the_decoder_is_total_on_input_the_schema_would_never_produce():
    for garbage in (None, [], 0, "", {"machines": 1}, {"cells": "no", "actions": {}},
                    {"cells": [None, 3, {"name": 1, "size": "x", "initial": None}],
                     "hidden": ["x", 99], "errors": [None, 5], "actions": "no",
                     "surface": {"kind": 7, "ok_token": None}}):
        host.validate_carrier(contract.decode_machine(garbage))


def test_the_decoder_is_deterministic_and_independent_of_position():
    machines = list(devkit.development_candidates("m122-neutral-", 30))
    once = [contract.decode_machine(m) for m in machines]
    twice = [contract.decode_machine(m) for m in reversed(machines)][::-1]
    assert once == twice
    assert contract.decode_completion(machines) == once


def test_the_decoder_cannot_make_a_carrier_qualify():
    outcomes = set()
    for candidate in devkit.development_candidates("m122-qualify-", 120, mode=devkit.MODE_CORNER):
        carrier = host.validate_carrier(contract.decode_machine(candidate))
        outcomes.add(evaluator.qualification_report(carrier)["qualifies"])
    assert outcomes == {True, False}


def test_the_m119_bank_still_decodes_into_carriers_the_frozen_host_accepts():
    """The closed public record, run through the flattened decoder. Not repaired, not re-scored."""
    bank = json.loads((ROOT / "experiments" / "M119" / "CARRIER_BANK.json").read_text(
        encoding="utf-8"))
    machines = [{k: v for k, v in carrier.items() if k != "carrier_ref"}
                for carrier in bank["carriers"]]
    refused = 0
    for machine in machines:
        try:
            host.validate_carrier(contract.decode_machine(machine))
        except host.CarrierError:
            refused += 1
    assert len(machines) == 37 and refused == 0


def test_every_effect_mode_and_guard_relation_is_reachable_through_the_decoder():
    modes, relations = set(), set()
    for candidate in devkit.development_candidates("m122-vocabulary-", 300):
        carrier = host.validate_carrier(contract.decode_machine(candidate))
        for action in carrier["actions"]:
            modes.update(item["mode"] for item in action["effect"])
            relations.update(clause["relation"] for clause in action["guard"])
    assert modes == set(host.EFFECT_MODES)
    assert relations == set(host.GUARD_RELATIONS)


def test_combinations_of_hidden_indices_never_hide_every_cell():
    for cell_count in range(contract.MIN_CELLS, contract.MAX_CELLS + 1):
        for hidden in itertools.chain([[]], ([i] for i in contract.CELL_INDICES)):
            candidate = _machine(
                cells=[{"name": "c%d" % i, "size": 2, "initial": 0} for i in range(cell_count)],
                hidden=hidden, errors=["e0"],
                actions=[_action(arg_size=2, guard=[{"cell": 0, "relation": "ge", "value": 0}],
                                 effect=[{"cell": 0, "mode": "set", "operand": 1}],
                                 name="a%d" % i) for i in range(4)])
            assert _valid(candidate)
            carrier = host.validate_carrier(contract.decode_machine(candidate))
            assert sum(carrier["visible"]) >= cell_count - contract.MAX_HIDDEN_CELLS


def test_a_random_smoke_over_mixed_shapes_stays_accepted():
    rng = random.Random(20260903)
    for _ in range(150):
        cell_count = rng.randint(contract.MIN_CELLS, contract.MAX_CELLS)
        cells = [{"name": "c%d" % i, "size": rng.choice(contract.CELL_SIZES),
                  "initial": rng.choice(contract.CELL_VALUES)} for i in range(cell_count)]

        def _draw():
            return _action(
                arg_size=rng.choice(contract.ARG_SIZES),
                guard=[{"cell": rng.choice(contract.CELL_INDICES),
                        "relation": rng.choice(host.GUARD_RELATIONS),
                        "value": rng.choice(contract.CELL_VALUES)}
                       for _ in range(rng.randint(0, host.MAX_GUARD_CLAUSES))],
                effect=[{"cell": rng.choice(contract.CELL_INDICES),
                         "mode": rng.choice(host.EFFECT_MODES),
                         "operand": rng.choice(contract.CELL_VALUES)}
                        for _ in range(rng.randint(1, host.MAX_EFFECT_ASSIGNMENTS))],
                name="a%d" % rng.randrange(4), error_index=rng.choice(contract.ERROR_INDICES))

        candidate = _machine(
            cells=cells,
            hidden=[rng.choice(contract.CELL_INDICES)] if rng.random() < 0.5 else [],
            errors=["e%d" % i for i in range(rng.randint(contract.MIN_ERRORS,
                                                         contract.MAX_ERRORS))],
            actions=[_draw() for _ in range(rng.randint(contract.MIN_ACTIONS,
                                                        contract.MAX_ACTIONS))])
        assert _valid(candidate)
        host.validate_carrier(contract.decode_machine(candidate))


# ---------------------------------------------------------------------------------------------
# The yield, and the measurement that justified dropping M120's guarantee
# ---------------------------------------------------------------------------------------------

def test_the_development_emitter_only_draws_schema_valid_candidates():
    for mode in devkit.MODES:
        for candidate in devkit.development_candidates("m122-devkit-", 40, mode=mode):
            ok, location, keyword = schema_tools.instance_is_valid(
                {"machines": [candidate]}, contract.candidate_schema())
            assert ok, "%s draw left the schema at %s (%s)" % (mode, location, keyword)


def test_the_flattened_family_yields_at_least_as_well_as_m120s():
    """Flattening was forced. Improving the yield was not, and is measured rather than claimed."""
    corner = devkit.qualification_rate("m122-yield-", 400, mode=devkit.MODE_CORNER)
    uniform = devkit.qualification_rate("m122-yield-", 400, mode=devkit.MODE_UNIFORM)
    assert corner["every_decoded_candidate_was_accepted"]
    assert uniform["every_decoded_candidate_was_accepted"]
    # M120's committed derivation recorded 0.2875 at the corner and 0.4175 uniform.
    assert corner["qualification_rate"] >= 0.2875
    assert uniform["qualification_rate"] >= 0.4175


def test_carriers_with_no_guarded_action_are_rare_enough_that_the_clause_can_carry_it():
    """The guarantee M120 paid three nesting levels for, measured instead of assumed."""
    unprotocol = 0
    total = 600
    for candidate in devkit.development_candidates("m122-protocol-", total,
                                                   mode=devkit.MODE_CORNER):
        carrier = host.validate_carrier(contract.decode_machine(candidate))
        report = evaluator.qualification_report(carrier)
        if "the_carrier_imposes_a_protocol" in report["blocking_clauses"]:
            unprotocol += 1
    assert unprotocol / total < 0.05, (
        "%d of %d carriers impose no protocol; the schema guarantee M120 paid for would be "
        "earning its price after all" % (unprotocol, total))


def test_the_contract_report_describes_the_contract_that_exists():
    report = contract.contract_report()
    assert report["array_of_object_levels"] == 5
    assert report["census_is_within_what_the_route_enforces"] is True
    assert report["family"]["actions"] == [contract.MIN_ACTIONS, contract.MAX_ACTIONS]
    assert report["family"]["guard_clauses_per_action"][0] == 0
    assert report["host_refusal_classes_enumerated"] == len(contract.HOST_REFUSALS)
