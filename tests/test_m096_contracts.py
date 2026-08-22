from __future__ import annotations

import ast
from pathlib import Path

from metamorphosis import m095_chain
from metamorphosis.m094_diagnosis import RenderAsMapping
from metamorphosis.m095_reach import RenderNestedValueObject, encode_nested
from metamorphosis.m096_contracts import (
    ContractExactRenderAsMapping,
    ContractExactRenderNestedValueObject,
    contract_safe_shapes,
)


def _class(source: str) -> ast.ClassDef:
    return next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef))


def test_exact_mapping_accepts_only_the_complete_observed_contract() -> None:
    detail = "x_axis=x|,y_axis=y|"
    exact = _class(
        "class Coordinate:\n"
        "    def render(self):\n"
        "        return {'x_axis': self.x, 'y_axis': self.y}\n"
    )
    superset = _class(
        "class Coordinate:\n"
        "    def render(self):\n"
        "        return {'x_axis': self.x, 'y_axis': self.y, 'x': self.x}\n"
    )

    assert RenderAsMapping().is_supplied_by(superset, "Coordinate", detail)
    assert ContractExactRenderAsMapping().is_supplied_by(exact, "Coordinate", detail)
    assert not ContractExactRenderAsMapping().is_supplied_by(
        superset, "Coordinate", detail
    )


def test_exact_mapping_rejects_open_or_duplicate_dict_literals() -> None:
    detail = "x=x|"
    duplicate = _class(
        "class Value:\n"
        "    def render(self):\n"
        "        return {'x': self.x, 'x': self.x}\n"
    )
    open_mapping = _class(
        "class Value:\n"
        "    def render(self):\n"
        "        return {**self.extra, 'x': self.x}\n"
    )

    shape = ContractExactRenderAsMapping()
    assert not shape.is_supplied_by(duplicate, "Value", detail)
    assert not shape.is_supplied_by(open_mapping, "Value", detail)


def test_exact_nested_mapping_requires_plain_and_nested_keys_without_extras() -> None:
    detail = encode_nested("coordinate", "coordinate", (("x", "x"),))
    exact = _class(
        "class Envelope:\n"
        "    def render(self):\n"
        "        return {'coordinate': self.coordinate.render()}\n"
    )
    superset = _class(
        "class Envelope:\n"
        "    def render(self):\n"
        "        return {'coordinate': self.coordinate.render(), "
        "'other': self.other}\n"
    )

    assert RenderNestedValueObject().is_supplied_by(exact, "Envelope", detail)
    assert RenderNestedValueObject().is_supplied_by(superset, "Envelope", detail)
    shape = ContractExactRenderNestedValueObject()
    assert shape.is_supplied_by(exact, "Envelope", detail)
    assert not shape.is_supplied_by(superset, "Envelope", detail)


def test_contract_binding_is_scoped_and_restored() -> None:
    inherited = m095_chain.SHAPES
    with contract_safe_shapes():
        assert m095_chain.SHAPES != inherited
        assert any(
            isinstance(shape, ContractExactRenderAsMapping)
            for shape in m095_chain.SHAPES
        )
    assert m095_chain.SHAPES is inherited


def test_contract_binding_restores_after_failure() -> None:
    inherited = m095_chain.SHAPES
    try:
        with contract_safe_shapes():
            raise RuntimeError("deliberate")
    except RuntimeError as error:
        assert str(error) == "deliberate"
    assert m095_chain.SHAPES is inherited


def test_module_import_does_not_modify_frozen_m095_source() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "metamorphosis" / "m095_chain.py").read_text(encoding="utf-8")
    assert "m096_contracts" not in source
