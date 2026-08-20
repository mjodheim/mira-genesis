"""M095: the same operation, unreachable in one state and reachable in the next.

This is the mechanism M095 rests on, tested on its own before any lineage runs it. The claim
under test is narrow and checkable:

    an operation present in the set at both states applies at S1 and not at S0, and the only
    difference between the states is a repair the lineage adopted.

If that ever stopped holding — if the operation applied at S0, or if it needed to be *added*
between the states — M095 would be measuring something else, and the chain would prove nothing
about enabling.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis import m095_reach as reach  # noqa: E402
from metamorphosis.m094_composition import MethodDraft, render, unparse  # noqa: E402
from metamorphosis.m094_diagnosis import _encode_rendering  # noqa: E402
from metamorphosis.m095_reach import (  # noqa: E402,F401
    RENDER_PREFIX,
    IncludeRenderedField,
    NestedRendering,
    find_class,
    operations_for_nested,
    rendered_method,
    supplying_method,
    unreachable_operations,
)

#: S0. `Inner` renders nothing.
S0 = '''from dataclasses import dataclass


@dataclass(frozen=True)
class Inner:
    inner_id: str
    label: str
'''

#: S1. The same class, after a repair of exactly the shape M094 adopts.
S1 = S0 + '''
    def as_mapping(self):
        return {'inner_id': self.inner_id, 'label': self.label}
'''

INNER_REQUIREMENT = _encode_rendering(
    (("inner_id", "inner_id", None), ("label", "label", None))
)


def _inner(source: str) -> ast.ClassDef:
    node = find_class(ast.parse(source), "Inner")
    assert node is not None
    return node


def _operation(source: str) -> IncludeRenderedField:
    return IncludeRenderedField(
        key="inner",
        field="inner",
        inner_class=_inner(source),
        inner_requirement=INNER_REQUIREMENT,
    )


# ── the reachability difference ───────────────────────────────────────


def test_the_operation_cannot_apply_before_the_repair() -> None:
    """S0: no renderer on the inner class, so every composition through it dies."""

    operation = _operation(S0)
    assert operation.supplier() is None
    assert operation.is_reachable() is False
    assert operation.apply(MethodDraft(name="as_mapping")) is None


def test_the_same_operation_applies_after_the_repair() -> None:
    """S1: the inner class renders, so the operation contributes."""

    operation = _operation(S1)
    assert operation.supplier() == "as_mapping"
    assert operation.is_reachable() is True

    grown = operation.apply(MethodDraft(name="as_mapping"))
    assert grown is not None
    assert grown.items[0].key == "inner"
    assert rendered_method(grown.items[0].wrapper) == "as_mapping"


def test_the_operation_is_the_same_object_in_both_states() -> None:
    """Nothing is added between the states. The set is fixed; the code moved.

    If M095 worked by handing the lineage a new operation at S1, the chain would demonstrate
    a larger language rather than a larger reach, and the distinction is the whole milestone.
    """

    before, after = _operation(S0), _operation(S1)
    assert type(before) is type(after)
    assert (before.key, before.field, before.inner_requirement) == (
        after.key, after.field, after.inner_requirement
    )
    assert before.describe() == after.describe()
    # Only the state differs.
    assert before.inner_class is not after.inner_class


def test_the_repair_it_depends_on_is_read_from_the_code_not_recorded() -> None:
    """A renderer nobody adopted still counts: reach is a property of the state.

    The enabling relation must not be "the lineage remembers adopting something". A class that
    always had a renderer enables the operation just as well, which is what makes the S0
    control meaningful rather than bookkeeping.
    """

    always_had_one = S0.replace(
        "    label: str\n",
        "    label: str\n\n"
        "    def to_dict(self):\n"
        "        return {'inner_id': self.inner_id, 'label': self.label}\n",
    )
    operation = _operation(always_had_one)
    assert operation.supplier() == "to_dict"
    assert operation.is_reachable() is True


def test_a_renderer_that_does_not_cover_the_requirement_does_not_enable_it() -> None:
    """Half a repair is not a repair. The supplier must satisfy what the callers wrote."""

    partial = S0 + '''
    def as_mapping(self):
        return {'inner_id': self.inner_id}
'''
    operation = _operation(partial)
    assert operation.supplier() is None
    assert operation.apply(MethodDraft(name="as_mapping")) is None


def test_a_missing_inner_class_is_unreachable_rather_than_an_error() -> None:
    operation = IncludeRenderedField(
        key="inner", field="inner", inner_class=None, inner_requirement=INNER_REQUIREMENT,
    )
    assert operation.is_reachable() is False
    assert operation.apply(MethodDraft(name="as_mapping")) is None


def test_a_private_or_argument_taking_method_does_not_count() -> None:
    """A caller must be able to write `obj.method()`, or the renderer is not usable."""

    private = S0 + '''
    def _as_mapping(self):
        return {'inner_id': self.inner_id, 'label': self.label}
'''
    needs_args = S0 + '''
    def as_mapping(self, style):
        return {'inner_id': self.inner_id, 'label': self.label}
'''
    assert _operation(private).is_reachable() is False
    assert _operation(needs_args).is_reachable() is False


# ── what the enabled operation actually emits ─────────────────────────


def test_the_assembled_method_calls_the_inner_renderer(tmp_path: Path) -> None:
    draft = MethodDraft(name="as_mapping", returns="mapping")
    draft = _operation(S1).apply(draft)
    assert draft is not None
    source = unparse(render(draft))
    assert "self.inner.as_mapping()" in source, source

    # And it runs, producing the nested mapping rather than the object.
    module = S1 + '''

@dataclass(frozen=True)
class Outer:
    inner: Inner

''' + "\n".join("    " + line for line in source.splitlines()) + "\n"
    namespace: dict = {}
    exec(compile(module, "<m095>", "exec"), namespace)
    produced = namespace["Outer"](namespace["Inner"]("i-1", "L")).as_mapping()
    assert produced == {"inner": {"inner_id": "i-1", "label": "L"}}


def test_it_calls_whatever_the_inner_class_supplies_not_a_written_down_name() -> None:
    oddly_named = S0.replace(
        "    label: str\n",
        "    label: str\n\n"
        "    def zzz_render(self):\n"
        "        return {'inner_id': self.inner_id, 'label': self.label}\n",
    )
    draft = _operation(oddly_named).apply(MethodDraft(name="as_mapping", returns="mapping"))
    assert draft is not None
    assert "self.inner.zzz_render()" in unparse(render(draft))


# ── the census the S0 control reports ─────────────────────────────────


def test_the_unreachable_census_names_what_the_state_cannot_use() -> None:
    nested = (NestedRendering("inner", "inner", "Inner", INNER_REQUIREMENT),)
    at_s0 = operations_for_nested(nested, {"Inner": _inner(S0)})
    at_s1 = operations_for_nested(nested, {"Inner": _inner(S1)})

    assert unreachable_operations(at_s0) == ("include=inner<-render(inner)",)
    assert unreachable_operations(at_s1) == ()


def test_the_operation_set_offered_is_identical_in_both_states() -> None:
    """The census differs; the offer does not."""

    nested = (NestedRendering("inner", "inner", "Inner", INNER_REQUIREMENT),)
    at_s0 = operations_for_nested(nested, {"Inner": _inner(S0)})
    at_s1 = operations_for_nested(nested, {"Inner": _inner(S1)})
    assert [op.describe() for op in at_s0] == [op.describe() for op in at_s1]
    assert len(at_s0) == len(at_s1) == 1


# ── M094 is not disturbed ─────────────────────────────────────────────


def test_the_render_wrapper_is_additive_to_m094() -> None:
    """M094 produces no `render:` wrapper, so its adopted mechanism cannot have moved."""

    from metamorphosis.m094_composition import WRAPPERS

    assert all(
        wrapper is None or not wrapper.startswith(RENDER_PREFIX) for wrapper in WRAPPERS
    )
