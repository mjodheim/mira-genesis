"""M096 contract-safe composition over the frozen M095 lineage.

M095 accepted a renderer when it covered every demanded binding, even if it also
returned unrelated keys.  That local subset contract was not safe to embed in the
strict nested mapping demanded by the next repair.  M096 changes one thing: mapping
repairs are accepted only when their complete top-level output contract is the one
observed at the call sites.

The M094 and M095 sources are frozen evidence and are intentionally not edited.  This
module supplies stricter capability shapes to the inherited M095 lineage for the
duration of an M096 run, then restores the original shapes even when the run fails.
The operation language, search order and composition bound remain inherited.
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Iterator

from metamorphosis import m095_chain as inherited
from metamorphosis import m095_reach as reach
from metamorphosis.m094_diagnosis import (
    RenderAsMapping,
    _mapping_bindings,
    decode_rendering,
)

CONTRACT_SCHEMA = "m096-contract-safe-composition-v1"


def _literal_mapping_bindings(node: ast.expr) -> dict[str, tuple[str, str | None]] | None:
    """Return all bindings only when *node* is a closed, duplicate-free dict literal."""

    if not isinstance(node, ast.Dict) or len(node.keys) != len(node.values):
        return None
    keys = [
        key.value
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    ]
    if len(keys) != len(node.keys) or len(set(keys)) != len(keys):
        return None
    bindings = _mapping_bindings(node)
    if bindings is None or len(bindings) != len(keys):
        return None
    return bindings


def _own_returns(method: ast.FunctionDef) -> tuple[ast.expr, ...]:
    """Collect return values without accepting returns from nested definitions."""

    class Returns(ast.NodeVisitor):
        def __init__(self) -> None:
            self.values: list[ast.expr] = []

        def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
            if node.value is not None:
                self.values.append(node.value)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            return

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            return

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
            return

    found = Returns()
    for statement in method.body:
        found.visit(statement)
    return tuple(found.values)


def _plain_method(node: ast.AST) -> bool:
    if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
        return False
    positional = (*node.args.posonlyargs, *node.args.args)
    return bool(
        len(positional) == 1
        and not node.decorator_list
        and not node.args.vararg
        and not node.args.kwonlyargs
        and not node.args.kwarg
    )


@dataclass(frozen=True)
class ContractExactRenderAsMapping(RenderAsMapping):
    """The M094 mapping demand with equality, rather than subset, acceptance."""

    def is_supplied_by(self, class_node: ast.ClassDef, target: str, detail: str) -> bool:
        wanted = {
            key: (field, wrapper)
            for key, field, wrapper in decode_rendering(detail)
        }
        if not wanted:
            return False
        for method in class_node.body:
            if not _plain_method(method):
                continue
            for returned in _own_returns(method):
                if _literal_mapping_bindings(returned) == wanted:
                    return True
        return False


def _plain_binding(node: ast.expr) -> tuple[str, str | None] | None:
    wrapper: str | None = None
    value = node
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in {"list", "tuple", "set", "dict", "sorted"}
        and len(value.args) == 1
        and not value.keywords
    ):
        wrapper = value.func.id
        value = value.args[0]
    if (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id == "self"
    ):
        return value.attr, wrapper
    return None


def _nested_binding(node: ast.expr) -> str | None:
    if not (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "self"
    ):
        return None
    return node.func.value.attr


@dataclass(frozen=True)
class ContractExactRenderNestedValueObject(reach.RenderNestedValueObject):
    """Accept an outer renderer only when every and only demanded key is returned."""

    def is_supplied_by(self, class_node: ast.ClassDef, target: str, detail: str) -> bool:
        wanted = {
            key: (field, wrapper)
            for key, field, wrapper in decode_rendering(detail)
        }
        if not wanted:
            return False
        for method in class_node.body:
            if not _plain_method(method):
                continue
            for returned in _own_returns(method):
                if not isinstance(returned, ast.Dict):
                    continue
                keys = [
                    key.value
                    for key in returned.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                ]
                if len(keys) != len(returned.keys) or set(keys) != set(wanted):
                    continue
                if len(set(keys)) != len(keys):
                    continue
                produced: dict[str, tuple[str, str | None]] = {}
                valid = True
                for key, value in zip(keys, returned.values):
                    field, wrapper = wanted[key]
                    if isinstance(wrapper, str) and wrapper.startswith(reach.NESTED_WRAPPER):
                        nested_field = _nested_binding(value)
                        if nested_field != field:
                            valid = False
                            break
                        produced[key] = (field, wrapper)
                    else:
                        binding = _plain_binding(value)
                        if binding != (field, wrapper):
                            valid = False
                            break
                        produced[key] = binding
                if valid and produced == wanted:
                    return True
        return False


_INHERITED_SHAPES = inherited.SHAPES
EXACT_SHAPES = tuple(
    ContractExactRenderAsMapping()
    if shape.name == "render_value_object_as_mapping"
    else ContractExactRenderNestedValueObject()
    if shape.name == inherited.NESTED
    else shape
    for shape in _INHERITED_SHAPES
)
_PATCH_LOCK = RLock()


@contextmanager
def contract_safe_shapes() -> Iterator[None]:
    """Bind the additive M096 contract for one inherited lineage operation."""

    with _PATCH_LOCK:
        if inherited.SHAPES != _INHERITED_SHAPES:
            raise RuntimeError("the inherited M095 capability-shape binding has drifted")
        inherited.SHAPES = EXACT_SHAPES
        inherited.clear_caches()
        try:
            yield
        finally:
            inherited.SHAPES = _INHERITED_SHAPES
            inherited.clear_caches()


def measure(root: Path):
    with contract_safe_shapes():
        return inherited.measure(root)


def control_from_s0(root: Path):
    with contract_safe_shapes():
        return inherited.control_from_s0(root)


def run_existing(root: Path, counterfactual_root: Path):
    with contract_safe_shapes():
        return inherited.run_existing(root, counterfactual_root)


def run(root: Path, counterfactual_root: Path, **arrangement: int | None):
    with contract_safe_shapes():
        return inherited.run(root, counterfactual_root, **arrangement)


__all__ = [
    "CONTRACT_SCHEMA",
    "ContractExactRenderAsMapping",
    "ContractExactRenderNestedValueObject",
    "EXACT_SHAPES",
    "contract_safe_shapes",
    "control_from_s0",
    "measure",
    "run",
    "run_existing",
]
