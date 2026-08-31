"""Adversarial tests for the M116 schema-complexity census and the DEVELOPMENT stress gate.

The census exists so nobody chooses the gate's structural thresholds. They are recomputed from the
frozen M115 carrier output schema on every run. These tests prove the derivation is mechanical,
that a structurally weaker stress schema fails, and that no qualifying input can travel with the
DEVELOPMENT probe.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m116_schema as schema_tools
from metamorphosis import m116_stress_schema as stress
from scripts import audit_m116_capacity as capacity
from scripts import derive_carrier_schema_census as derive

ROOT = Path(__file__).resolve().parents[1]
CARRIER_VOCABULARY = ("machines", "surface", "cells", "initial", "visible", "errors", "actions")


def _frozen_schema():
    return json.loads((ROOT / "experiments" / "M115" / "OUTPUT_SCHEMA.json").read_text("utf-8"))


# ---------------------------------------------------------------------------------------------
# Derivation is mechanical
# ---------------------------------------------------------------------------------------------

def test_the_census_is_derived_from_the_frozen_schema_not_hard_coded():
    frozen = schema_tools.census(_frozen_schema())
    committed = json.loads((ROOT / "experiments" / "M116" / "CARRIER_SCHEMA_CENSUS.json")
                           .read_text("utf-8"))
    assert committed["frozen_carrier_census"] == frozen
    assert committed["derived_from"] == "experiments/M115/OUTPUT_SCHEMA.json"
    assert committed["thresholds_are_derived_not_chosen"] is True


def test_the_committed_census_matches_a_fresh_derivation():
    committed = json.loads((ROOT / "experiments" / "M116" / "CARRIER_SCHEMA_CENSUS.json")
                           .read_text("utf-8"))
    assert committed == derive.build()


def test_the_census_is_a_pure_function_of_the_schema():
    schema = _frozen_schema()
    assert schema_tools.census(schema) == schema_tools.census(copy.deepcopy(schema))


def test_the_frozen_carrier_schema_is_not_modified_by_censusing_it():
    before = (ROOT / "experiments" / "M115" / "OUTPUT_SCHEMA.json").read_bytes()
    schema_tools.census(json.loads(before.decode("utf-8")))
    assert (ROOT / "experiments" / "M115" / "OUTPUT_SCHEMA.json").read_bytes() == before


# ---------------------------------------------------------------------------------------------
# Dominance
# ---------------------------------------------------------------------------------------------

def test_the_stress_schema_dominates_the_frozen_carrier_schema():
    holds, failures = schema_tools.census_dominates(
        schema_tools.census(stress.build_stress_schema()), schema_tools.census(_frozen_schema())
    )
    assert holds is True, failures


def test_the_old_flat_stress_schema_would_now_fail_the_gate():
    """The schema M116 shipped with -- 1,536 rows of eight integers -- is structurally weaker."""
    flat = {
        "type": "object", "additionalProperties": False, "required": ["rows"],
        "properties": {"rows": {
            "type": "array", "minItems": 1536, "maxItems": 1536,
            "items": {"type": "object", "additionalProperties": False,
                      "required": list("abcdefgh"),
                      "properties": {k: {"type": "integer", "minimum": 10000000,
                                         "maximum": 99999999} for k in "abcdefgh"}}}},
    }
    holds, failures = schema_tools.census_dominates(
        schema_tools.census(flat), schema_tools.census(_frozen_schema())
    )
    assert holds is False
    assert any("pattern" in failure for failure in failures)
    assert any("enum" in failure for failure in failures)


@pytest.mark.parametrize("weakening", ["drop_pattern", "drop_enum", "flatten", "drop_type"])
def test_a_weakened_stress_schema_fails_dominance(weakening: str):
    weakened = copy.deepcopy(stress.build_stress_schema())
    item = weakened["properties"]["consignments"]["items"]
    if weakening == "drop_pattern":
        del item["properties"]["docket"]["pattern"]
        del item["properties"]["assayer"]["pattern"]
        del item["properties"]["tariff_codes"]["items"]["pattern"]
    elif weakening == "drop_enum":
        del item["properties"]["status"]["enum"]
        del item["properties"]["priority"]["enum"]
    elif weakening == "flatten":
        item["properties"]["parcels"] = {"type": "array", "items": {"type": "integer"}}
    elif weakening == "drop_type":
        # Remove every boolean the stress schema declares; the frozen carrier schema needs one.
        item["properties"]["insured"] = {}
        item["properties"]["routing"]["properties"]["bonded"] = {}
        sample = item["properties"]["parcels"]["items"]["properties"]["samples"]["items"]
        sample["properties"]["retained"] = {}
        sample["properties"]["assays"]["items"]["properties"]["certified"] = {}
    holds, failures = schema_tools.census_dominates(
        schema_tools.census(weakened), schema_tools.census(_frozen_schema())
    )
    assert holds is False, "weakening %s should not dominate" % weakening
    assert failures


def test_the_audit_refuses_to_build_a_request_from_a_weaker_schema(monkeypatch):
    monkeypatch.setattr(capacity, "STRESS_SCHEMA", {"type": "object"})
    with pytest.raises(capacity.CapacityAuditError, match="structurally weaker"):
        capacity.request_body_digest()


def test_the_audit_gate_requires_dominance_before_any_network_call():
    # `request_body_digest` is the only path to a request body, and it asserts dominance first.
    assert capacity.request_body_digest()
    census = capacity._assert_structurally_dominating()
    assert census["candidate"]["max_nesting_depth"] >= census["frozen"]["max_nesting_depth"]


# ---------------------------------------------------------------------------------------------
# Blindness of the DEVELOPMENT probe
# ---------------------------------------------------------------------------------------------

def test_the_stress_schema_carries_no_carrier_vocabulary():
    blob = json.dumps(stress.build_stress_schema()) + stress.STRESS_PROMPT
    for word in CARRIER_VOCABULARY:
        assert word not in blob


def test_no_qualifying_input_can_be_used_by_development():
    body = json.dumps(capacity.REQUEST_BODY)
    for milestone in ("M113", "M114", "M115"):
        path = ROOT / "experiments" / milestone / "QUALIFYING_INPUT.txt"
        if not path.is_file():
            continue
        qualifying = path.read_text("utf-8", errors="replace")
        assert qualifying.strip() not in body
        assert stress.STRESS_PROMPT.strip() not in qualifying


def test_the_development_request_never_carries_the_carrier_schema():
    body = json.dumps(capacity.REQUEST_BODY)
    assert json.dumps(_frozen_schema()) not in body
    sent = capacity.REQUEST_BODY["response_format"]["json_schema"]["schema"]
    assert sent == stress.build_stress_schema()


def test_the_capacity_requirement_survives_the_structural_extension():
    assert capacity.OLD_M115_MAX_TOKENS == 32000
    assert capacity.MAX_TOKENS == 131072
    assert capacity.REQUEST_BODY["reasoning"] == {"effort": "none"}


def test_development_retry_semantics_are_unchanged():
    assert capacity.MAX_PHYSICAL_ATTEMPTS == 3
    assert capacity.RETRY_WAIT_SECONDS == 60


# ---------------------------------------------------------------------------------------------
# The validator the census shares
# ---------------------------------------------------------------------------------------------

def test_the_validator_refuses_composition_keywords_rather_than_guessing():
    with pytest.raises(schema_tools.SchemaError, match="composition keyword"):
        schema_tools.validate_instance({}, {"type": "object", "anyOf": [{}]})


def test_the_validator_reports_a_location_and_keyword_never_a_value():
    schema = {"type": "object", "properties": {"token": {"type": "string", "pattern": "^[a-z]+$"}}}
    ok, location, keyword = schema_tools.instance_is_valid({"token": "SECRET-VALUE"}, schema)
    assert ok is False
    assert keyword == "pattern"
    assert "SECRET" not in location
