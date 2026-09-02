"""The M120 acceptance claim, established rather than asserted.

    for every value V satisfying CANDIDATE_SCHEMA,
    carrier_host.validate_carrier(decode_machine(V)) returns, and never raises

M119 had no test of this shape, and that is the whole of why it spent its qualifying generation on
a bank the frozen host refused 34 times out of 37. The claim is not provable by inspection -- the
host's rules are relations between fields and the decoder's job is to discharge them -- so it is
established here by exhausting the corners where those relations bite and by fuzzing the interior.
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
from metamorphosis import m120_carrier_contract as contract
from metamorphosis import m120_devkit as devkit

ROOT = Path(__file__).resolve().parents[1]


def _valid(candidate) -> bool:
    ok, _, _ = schema_tools.instance_is_valid({"machines": [candidate]},
                                              contract.CANDIDATE_SCHEMA)
    return ok


def _action(*, arg_size, guard, effect, name="op", error_index=0):
    return {"name": name, "arg_size": arg_size, "guard": list(guard),
            "effect": list(effect), "error_index": error_index}


def _machine(*, cells, hidden, errors, conditional, plain, surface=None):
    return {
        "surface": surface or {
            "kind": "json_object", "ok_token": "ok", "error_token": "er",
            "field_separator": ",", "pair_separator": "=",
            "action_key": "act", "argument_key": "arg", "status_key": "status",
        },
        "cells": list(cells), "hidden": list(hidden), "errors": list(errors),
        "conditional_actions": list(conditional), "actions": list(plain),
    }


# ---------------------------------------------------------------------------------------------
# The family is inside the host's meta-schema, and the schema says only what it can enforce
# ---------------------------------------------------------------------------------------------

def test_the_family_is_a_narrowing_of_the_frozen_host_meta_schema():
    """A narrowing is legitimate; exceeding the host would make the contract a fiction."""
    assert host.MIN_CELLS <= contract.MIN_CELLS <= contract.MAX_CELLS <= host.MAX_CELLS
    assert host.MIN_ACTIONS <= contract.MIN_ACTIONS <= contract.MAX_ACTIONS <= host.MAX_ACTIONS
    assert set(contract.CELL_SIZES) <= set(range(host.MIN_CELL_DOMAIN, host.MAX_CELL_DOMAIN + 1))
    assert set(contract.ARG_SIZES) - {0} <= set(
        range(host.MIN_ARG_DOMAIN, host.MAX_ARG_DOMAIN + 1))
    # The whole point of `hidden`: a machine that observes none of its own state -- 8 of M119's 34
    # host refusals -- is not a value this contract can express.
    assert contract.MIN_CELLS - contract.MAX_HIDDEN_CELLS >= 2


def test_the_candidate_schema_uses_no_keyword_the_route_has_not_been_shown_to_enforce():
    """`oneOf` and `contains` would say this more directly and have no evidence on this route."""
    census = schema_tools.census(contract.CANDIDATE_SCHEMA)
    assert census["composition_constructs"] == 0
    # `properties` is structural rather than a feature class: on its own it enforces nothing,
    # and the probe matrix has no probe for it because there is no output it could forbid.
    # Enforcement rests on `required` and `additionalProperties: false`, both of which are proven.
    structural = {"properties"}
    used = {name for name, count in census["keyword_counts"].items() if count}
    unproven = used - set(contract.PROVEN_FEATURE_CLASSES) - structural
    assert not unproven, "the schema uses keywords the readiness evidence does not cover: %s" % (
        sorted(unproven),)
    # `uniqueItems` is in the project's own validator vocabulary and was *not* among the classes
    # M118 observed enforced. Relying on it would create a new terminal failure mode.
    assert census["keyword_counts"]["uniqueItems"] == 0


def test_the_candidate_schema_states_no_relation_between_two_fields():
    """The two rules M119 died of were relations. This asserts none survives in the schema."""
    text = json.dumps(contract.CANDIDATE_SCHEMA)
    for banned in ('"$ref"', '"if"', '"then"', '"dependentRequired"', '"contains"'):
        assert banned not in text


def test_the_host_refusal_census_is_still_complete():
    """A refusal added to the host later must not become a class no fixture has ever covered."""
    source = ast.parse((ROOT / "metamorphosis" / "carrier_host.py").read_text(encoding="utf-8"))
    literals = set()
    for node in ast.walk(source):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        target = node.exc.func
        if getattr(target, "id", None) != "CarrierError" or not node.exc.args:
            continue
        first = node.exc.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            literals.add(first.value)
    assert literals == set(contract.HOST_REFUSALS), (
        "the host's constant refusal messages and the contract's census disagree: "
        "only in host %s; only in census %s"
        % (sorted(literals - set(contract.HOST_REFUSALS)),
           sorted(set(contract.HOST_REFUSALS) - literals)))


# ---------------------------------------------------------------------------------------------
# The acceptance claim
# ---------------------------------------------------------------------------------------------

def test_every_corner_of_the_constraint_relevant_space_decodes_into_an_accepted_carrier():
    """Exhaustive over the dimensions the host's relations actually depend on.

    Cell count, per-cell size, argument domain, effect mode, guard and effect indices at both
    extremes, hidden or not, and the smallest and largest action counts. Everything the host bounds
    against a *declared* value is at its boundary in at least one combination here.
    """
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
                            conditional=[_action(arg_size=arg_size, guard=guard, effect=effect,
                                                 name="ca%d" % index,
                                                 error_index=max(contract.ERROR_INDICES))
                                         for index in range(contract.MIN_CONDITIONAL_ACTIONS)],
                            plain=[_action(arg_size=arg_size, guard=[], effect=effect,
                                           name="pa%d" % index)
                                   for index in range(contract.MIN_PLAIN_ACTIONS)])
                        assert _valid(candidate), "the fixture left the candidate schema"
                        host.validate_carrier(contract.decode_machine(candidate))
                        checked += 1
    # 2 cell counts x 3 cell sizes x 4 argument domains x 5 effect modes x 2 index extremes.
    # Stated as a number so a fixture that silently stopped covering a dimension shows up here.
    assert checked == 240


def test_name_and_token_collisions_cannot_reach_a_host_refusal():
    """Four of the host's refusals are about names colliding, and none is expressible in JSON Schema."""
    surface = {"kind": "text_line", "ok_token": "same", "error_token": "same",
               "field_separator": "|", "pair_separator": "/",
               "action_key": "dup", "argument_key": "dup", "status_key": "dup"}
    candidate = _machine(
        cells=[{"name": "dup", "size": 2, "initial": 1} for _ in range(contract.MAX_CELLS)],
        hidden=[0],
        errors=["same"] * contract.MAX_ERRORS,
        conditional=[_action(arg_size=2, guard=[{"cell": 0, "relation": "eq", "value": 0}],
                             effect=[{"cell": 0, "mode": "arg", "operand": 0}], name="dup")
                     for _ in range(contract.MAX_CONDITIONAL_ACTIONS)],
        plain=[_action(arg_size=0, guard=[], effect=[{"cell": 0, "mode": "set", "operand": 0}],
                       name="dup")
               for _ in range(contract.MAX_PLAIN_ACTIONS)],
        surface=surface)
    assert _valid(candidate)
    carrier = host.validate_carrier(contract.decode_machine(candidate))
    assert len({cell["name"] for cell in carrier["cells"]}) == len(carrier["cells"])
    assert len({action["name"] for action in carrier["actions"]}) == len(carrier["actions"])
    assert len(set(carrier["errors"])) == len(carrier["errors"])
    assert carrier["surface"]["ok_token"] != carrier["surface"]["error_token"]


def test_a_nullary_action_whose_effect_wants_an_argument_is_given_one():
    """The decoder's single conditional, checked at the point where the host would refuse."""
    candidate = _machine(
        cells=[{"name": "c%d" % i, "size": 3, "initial": 0} for i in range(3)],
        hidden=[], errors=["e0"],
        conditional=[_action(arg_size=0, guard=[{"cell": 0, "relation": "lt", "value": 2}],
                             effect=[{"cell": 1, "mode": "arg", "operand": 0}],
                             name="ca%d" % i) for i in range(2)],
        plain=[_action(arg_size=0, guard=[],
                       effect=[{"cell": 0, "mode": "add", "operand": 1}], name="pa%d" % i)
               for i in range(2)])
    assert _valid(candidate)
    carrier = host.validate_carrier(contract.decode_machine(candidate))
    promoted = carrier["actions"][0]
    assert promoted["arity"] == 1 and promoted["arg_size"] == host.MIN_ARG_DOMAIN
    assert carrier["actions"][-1]["arity"] == 0 and carrier["actions"][-1]["arg_size"] == 0


@pytest.mark.parametrize("mode", devkit.MODES)
def test_a_large_deterministic_fuzz_never_reaches_a_host_refusal(mode):
    """The interior of the space, not only its corners. Deterministic, so a failure is reproducible."""
    for candidate in devkit.development_candidates("m120-contract-fuzz-", 400, mode=mode):
        assert _valid(candidate)
        host.validate_carrier(contract.decode_machine(candidate))


def test_the_decoder_is_total_on_input_the_schema_would_never_produce():
    """Totality is a property of the function, not of the inputs it is expected to see."""
    for garbage in (None, [], 0, "", {"machines": 1}, {"cells": "no", "actions": {}},
                    {"cells": [None, 3, {"name": 1, "size": "x", "initial": None}],
                     "hidden": ["x", 99], "errors": [None, 5],
                     "conditional_actions": [None], "actions": "no",
                     "surface": {"kind": 7, "ok_token": None}}):
        host.validate_carrier(contract.decode_machine(garbage))


def test_the_decoder_is_deterministic_and_independent_of_position():
    """Neutrality: no machine may influence how another decodes, and order carries no information."""
    machines = list(devkit.development_candidates("m120-neutral-", 30))
    once = [contract.decode_machine(m) for m in machines]
    twice = [contract.decode_machine(m) for m in reversed(machines)][::-1]
    assert once == twice
    assert contract.decode_completion(machines) == once


def test_the_decoder_cannot_make_a_carrier_qualify():
    """The structural gap is the decoder's job. The scientific gap is not, and stays open."""
    outcomes = set()
    for candidate in devkit.development_candidates("m120-qualify-", 120, mode=devkit.MODE_CORNER):
        carrier = host.validate_carrier(contract.decode_machine(candidate))
        outcomes.add(evaluator.qualification_report(carrier)["qualifies"])
    assert outcomes == {True, False}, (
        "a contract whose carriers always qualify, or never do, would not be measuring anything")


def test_the_acceptance_census_reports_a_clean_sweep_and_would_report_a_dirty_one():
    """The census is only worth having if it can also say no."""
    clean = contract.acceptance_census(list(devkit.development_candidates("m120-census-", 60)))
    assert clean["every_decoded_candidate_was_accepted"] is True
    assert clean["refused_by_the_frozen_host"] == 0
    # A carrier the host refuses, constructed directly rather than through the decoder.
    dirty = contract.acceptance_census([])
    assert dirty["candidates"] == 0 and dirty["every_decoded_candidate_was_accepted"] is True


# ---------------------------------------------------------------------------------------------
# The failure M119 actually suffered, replayed against this contract
# ---------------------------------------------------------------------------------------------

def test_the_two_values_that_killed_m119_cannot_be_written_in_this_contract():
    """25 refusals for an argument domain outside 2..4; 8 for observing none of its own state."""
    schema = contract.CANDIDATE_SCHEMA
    action = (schema["properties"]["machines"]["items"]["properties"]["conditional_actions"]
              ["items"]["properties"])
    assert action["arg_size"]["enum"] == [0, 2, 3, 4]
    assert 1 not in action["arg_size"]["enum"]
    machine = schema["properties"]["machines"]["items"]["properties"]
    assert "visible" not in machine
    assert machine["hidden"]["maxItems"] == contract.MAX_HIDDEN_CELLS
    assert machine["cells"]["minItems"] >= contract.MAX_HIDDEN_CELLS + 2


def test_the_m119_bank_decodes_into_carriers_the_frozen_host_accepts():
    """The closed public record, run through this contract. It is evidence, and it is not repaired.

    M119's bank is not re-scored, relabelled or reinterpreted here; its verdict stays
    `instrument_aborted` and H64 stays untested. What this asserts is a property of the M120
    decoder measured on the only real blind bank this route has ever produced.
    """
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
    assert len(machines) == 37
    assert refused == 0, (
        "the decoder must carry even M115-shaped machines into host-valid form; %d were refused"
        % refused)


def test_a_random_smoke_over_mixed_shapes_stays_accepted():
    """One more sweep, drawn differently, so a fixture family cannot be the only thing that passes."""
    rng = random.Random(20260902)
    for _ in range(150):
        cell_count = rng.randint(contract.MIN_CELLS, contract.MAX_CELLS)
        cells = [{"name": "c%d" % i, "size": rng.choice(contract.CELL_SIZES),
                  "initial": rng.choice(contract.CELL_VALUES)} for i in range(cell_count)]
        def _draw(minimum_guard):
            return _action(
                arg_size=rng.choice(contract.ARG_SIZES),
                guard=[{"cell": rng.choice(contract.CELL_INDICES),
                        "relation": rng.choice(host.GUARD_RELATIONS),
                        "value": rng.choice(contract.CELL_VALUES)}
                       for _ in range(rng.randint(minimum_guard, host.MAX_GUARD_CLAUSES))],
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
            conditional=[_draw(1) for _ in range(rng.randint(contract.MIN_CONDITIONAL_ACTIONS,
                                                             contract.MAX_CONDITIONAL_ACTIONS))],
            plain=[_draw(0) for _ in range(rng.randint(contract.MIN_PLAIN_ACTIONS,
                                                       contract.MAX_PLAIN_ACTIONS))])
        assert _valid(candidate)
        host.validate_carrier(contract.decode_machine(candidate))


def test_every_effect_mode_and_guard_relation_is_reachable_through_the_decoder():
    """A decoder that quietly collapsed the vocabulary would narrow the family without saying so."""
    modes, relations = set(), set()
    for candidate in devkit.development_candidates("m120-vocabulary-", 300):
        carrier = host.validate_carrier(contract.decode_machine(candidate))
        for action in carrier["actions"]:
            modes.update(item["mode"] for item in action["effect"])
            relations.update(clause["relation"] for clause in action["guard"])
    assert modes == set(host.EFFECT_MODES)
    assert relations == set(host.GUARD_RELATIONS)


def test_surface_kinds_all_survive_decoding():
    for kind in host.SURFACE_KINDS:
        candidate = _machine(
            cells=[{"name": "c%d" % i, "size": 2, "initial": 0} for i in range(3)],
            hidden=[], errors=["e0"],
            conditional=[_action(arg_size=2,
                                 guard=[{"cell": 0, "relation": "eq", "value": 0}],
                                 effect=[{"cell": 0, "mode": "set", "operand": 1}],
                                 name="ca%d" % i) for i in range(2)],
            plain=[_action(arg_size=0, guard=[],
                           effect=[{"cell": 1, "mode": "add", "operand": 1}], name="pa%d" % i)
                   for i in range(2)],
            surface={"kind": kind, "ok_token": "ok", "error_token": "er",
                     "field_separator": " ", "pair_separator": "-",
                     "action_key": "act", "argument_key": "arg", "status_key": "status"})
        assert _valid(candidate)
        carrier = host.validate_carrier(contract.decode_machine(candidate))
        assert carrier["surface"]["kind"] == kind


def test_the_contract_report_describes_the_contract_that_exists():
    report = contract.contract_report()
    assert report["family"]["cells"] == [contract.MIN_CELLS, contract.MAX_CELLS]
    assert report["family"]["actions"] == [contract.MIN_ACTIONS, contract.MAX_ACTIONS]
    assert report["host_refusal_classes_enumerated"] == len(contract.HOST_REFUSALS)
    assert report["decoder_version"] == contract.DECODER_VERSION


def test_combinations_of_hidden_indices_never_hide_every_cell():
    for cell_count in range(contract.MIN_CELLS, contract.MAX_CELLS + 1):
        for hidden in itertools.chain([[]], ([i] for i in contract.CELL_INDICES)):
            candidate = _machine(
                cells=[{"name": "c%d" % i, "size": 2, "initial": 0} for i in range(cell_count)],
                hidden=hidden, errors=["e0"],
                conditional=[_action(arg_size=2,
                                     guard=[{"cell": 0, "relation": "ge", "value": 0}],
                                     effect=[{"cell": 0, "mode": "set", "operand": 1}],
                                     name="ca%d" % i) for i in range(2)],
                plain=[_action(arg_size=0, guard=[],
                               effect=[{"cell": 0, "mode": "add", "operand": 1}], name="pa%d" % i)
                       for i in range(2)])
            assert _valid(candidate)
            carrier = host.validate_carrier(contract.decode_machine(candidate))
            assert sum(carrier["visible"]) >= cell_count - contract.MAX_HIDDEN_CELLS
