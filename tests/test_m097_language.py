from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

import pytest

from metamorphosis.m097_acquisition import acquire
from metamorphosis.m097_execution import confirm_search
from metamorphosis.m097_language import (
    DerivedRequirement,
    OperationLanguageState,
    evaluate_symbol,
    insufficiency_certificate,
    method_supplies_requirement,
    search,
    symbolic_expression,
)
from metamorphosis.m097_validator import validate
from scripts.author_m097_qualification_pool import COMPONENT, build_world, cases_for


DEVELOPMENT = {
    "id": "development_cycle",
    "class": "Cycle",
    "key": "width",
    "left_field": "upper",
    "right_field": "lower",
    "operator": "sub",
    "caller_count": 2,
    "fields": [
        {"name": "lower", "annotation": "int"},
        {"name": "upper", "annotation": "int"},
        {"name": "name", "annotation": "str"},
    ],
    "cases": [
        {"lower": 2, "upper": 8, "name": "a"},
        {"lower": -3, "upper": 5, "name": "b"},
        {"lower": 7, "upper": 1, "name": "c"},
        {"lower": 0, "upper": 0, "name": "d"},
    ],
}


def _public_cases():
    return [
        {"left": item["upper"], "right": item["lower"], "expected": item["upper"] - item["lower"]}
        for item in DEVELOPMENT["cases"]
    ]


def test_symbolic_substrate_builds_but_does_not_contain_finished_operation() -> None:
    acquisition = acquire(_public_cases())
    assert acquisition.candidates_assembled > 1_000
    assert acquisition.candidates_well_formed > 10
    assert acquisition.accepted_candidates >= 1
    assert acquisition.adopted is not None
    assert len(acquisition.adopted.body) == 3
    expression = symbolic_expression(acquisition.adopted.body)
    assert expression is not None
    assert evaluate_symbol(expression, 9, 4) == 5
    assert validate(acquisition.adopted, _public_cases()).accepted


def test_inherited_language_has_a_bound_independent_binary_gap() -> None:
    requirement = DerivedRequirement("Cycle", "width", "upper", "sub", "lower", 2)
    certificate = insufficiency_certificate(requirement)
    assert certificate["outside_constructive_image_at_any_bound"] is True
    assert certificate["same_language_more_budget_cannot_help"] is True
    assert certificate["required_ast_node"] == "BinOp"


def test_registration_changes_real_source_reach_and_execution() -> None:
    acquisition = acquire(_public_cases())
    assert acquisition.adopted is not None
    inherited = OperationLanguageState.inherited()
    extended = inherited.register(acquisition.adopted)
    requirement = DerivedRequirement("Cycle", "width", "upper", "sub", "lower", 2)
    with tempfile.TemporaryDirectory(prefix="m097-test-") as temporary:
        root = build_world(Path(temporary), DEVELOPMENT)
        source = (root / COMPONENT).read_text(encoding="utf-8")
        fields = [item["name"] for item in DEVELOPMENT["fields"]]
        before = search(source, requirement, fields, inherited)
        after = search(source, requirement, fields, extended)
        assert not before.reached_structurally
        assert after.reached_structurally
        executed, adopted_source, record = confirm_search(
            root, COMPONENT, after.sources, requirement, cases_for(DEVELOPMENT)
        )
    assert executed >= 1
    assert adopted_source is not None
    assert record is not None and record["confirmed"] is True


def test_registered_state_round_trips_without_definition_code() -> None:
    acquisition = acquire(_public_cases())
    assert acquisition.adopted is not None
    state = OperationLanguageState.inherited().register(acquisition.adopted)
    payload = json.loads(json.dumps(state.to_dict(), sort_keys=True))
    restored = OperationLanguageState.from_dict(payload)
    assert restored == state
    assert restored.to_dict()["state_digest"] == state.to_dict()["state_digest"]

    malformed = dict(payload)
    malformed["extensions"] = ["not a definition"]
    malformed_payload = {key: value for key, value in malformed.items() if key != "state_digest"}
    from metamorphosis.m097_language import digest
    malformed["state_digest"] = digest(malformed_payload)
    with pytest.raises(ValueError, match="closed definition records"):
        OperationLanguageState.from_dict(malformed)


def test_exact_derived_shape_rejects_extra_keys_and_wrong_operand_order() -> None:
    requirement = DerivedRequirement("Cycle", "width", "upper", "sub", "lower", 2)
    good = ast.parse(
        "def render(self):\n    return {'width': self.upper - self.lower}\n"
    ).body[0]
    extra = ast.parse(
        "def render(self):\n    return {'width': self.upper - self.lower, 'x': self.upper}\n"
    ).body[0]
    reversed_method = ast.parse(
        "def render(self):\n    return {'width': self.lower - self.upper}\n"
    ).body[0]
    assert isinstance(good, ast.FunctionDef)
    assert isinstance(extra, ast.FunctionDef)
    assert isinstance(reversed_method, ast.FunctionDef)
    assert method_supplies_requirement(good, requirement)
    assert not method_supplies_requirement(extra, requirement)
    assert not method_supplies_requirement(reversed_method, requirement)
