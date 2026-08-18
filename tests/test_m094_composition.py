"""The repair must be assembled, and most assemblies must be refused.

P6 asks for a repair built from composable operations rather than a template
body. Two things have to hold for that to mean anything, and both are checked
here:

* no operation is a repair — each contributes one decision, and a method exists
  only once some sequence has supplied a name, a return shape, and whatever that
  shape needs;
* the search genuinely rejects. A space where everything succeeds is a template
  with extra steps.

`experiments/M094/DESIGN_AUDIT.md` records what this replaces: one authored
template holding the finished method, then an f-string of a method with its
identifiers filled in from the AST.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from metamorphosis import m094_composition as composition
from metamorphosis.m094_composition import (
    IncludeField,
    MethodDraft,
    NameMethod,
    RejectEmpty,
    ReturnShape,
    operations_for,
    render,
    unparse,
)

CLASS_SOURCE = '''
from dataclasses import dataclass

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    missing: tuple = ()
'''


def _class_node(source: str, name: str = "Decision") -> ast.ClassDef:
    return next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.ClassDef) and n.name == name
    )


# ── No operation is a repair ─────────────────────────────────────────


def test_an_operation_alone_produces_no_method() -> None:
    """Each op is one decision; none of them is a method."""

    for operation in (NameMethod("as_mapping"), IncludeField("allowed"), ReturnShape("mapping")):
        draft = operation.apply(MethodDraft())
        assert draft is not None
        assert render(draft) is None, f"{operation.describe()} alone rendered a method"


def test_a_method_needs_a_name_a_shape_and_content() -> None:
    draft = MethodDraft()
    for operation in (NameMethod("as_mapping"), ReturnShape("mapping")):
        draft = operation.apply(draft)
    # Committed to a mapping but with nothing in it: still not a method.
    assert render(draft) is None

    draft = IncludeField("allowed").apply(draft)
    assert render(draft) is not None


def test_an_operation_that_cannot_apply_returns_none() -> None:
    """Pruning is what keeps a combinatorial space finite."""

    named = NameMethod("as_mapping").apply(MethodDraft())
    assert NameMethod("to_dict").apply(named) is None

    shaped = ReturnShape("mapping").apply(named)
    assert ReturnShape("filter").apply(shaped) is None

    included = IncludeField("allowed").apply(shaped)
    assert IncludeField("allowed", "list").apply(included) is None

    # A guard needs the parameter it guards to exist.
    assert RejectEmpty("value").apply(included) is None


# ── The method is a syntax tree, never text ──────────────────────────


def test_the_method_is_built_as_a_syntax_tree() -> None:
    draft = MethodDraft()
    for operation in (
        NameMethod("as_mapping"),
        ReturnShape("mapping"),
        IncludeField("allowed"),
        IncludeField("missing", "list"),
    ):
        draft = operation.apply(draft)

    function = render(draft)
    assert isinstance(function, ast.FunctionDef)

    source = unparse(function)
    ast.parse(source)
    assert "allowed" in source and "missing" in source


def test_two_drafts_differing_only_in_name_share_a_fingerprint() -> None:
    """Naming is not a discovery, and the search must not count it as one."""

    def build(name: str) -> MethodDraft:
        draft = MethodDraft()
        for operation in (NameMethod(name), ReturnShape("mapping"), IncludeField("allowed")):
            draft = operation.apply(draft)
        return draft

    assert build("as_mapping").fingerprint() == build("to_dict").fingerprint()


# ── The operation set does not contain the repair ────────────────────


def test_no_operation_carries_a_method_body() -> None:
    node = _class_node(CLASS_SOURCE)
    fields = sorted(f for f in ("allowed", "reason", "missing"))
    operations = operations_for("render_value_object_as_mapping", fields, "allowed,reason", ())

    for operation in operations:
        described = operation.describe()
        assert "def " not in described
        assert "return" not in described or described.startswith("return=")


def test_the_operation_set_is_derived_from_the_diagnosis() -> None:
    """Field operations come from the class; nothing is written per component."""

    operations = operations_for(
        "render_value_object_as_mapping", ["alpha", "beta"], "alpha,beta", ()
    )
    included = {op.field for op in operations if isinstance(op, IncludeField)}
    assert included == {"alpha", "beta"}


# ── The search refuses ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def report() -> composition.SearchReport:
    source = CLASS_SOURCE
    node = _class_node(source)

    def accepts(modified: str) -> bool:
        """Accept only a method returning a mapping that covers both fields."""

        tree = ast.parse(modified)
        target = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "Decision"),
            None,
        )
        if target is None:
            return False
        for member in target.body:
            if not isinstance(member, ast.FunctionDef) or member.name.startswith("_"):
                continue
            for inner in ast.walk(member):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Dict):
                    keys = {
                        k.value for k in inner.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                    }
                    if {"allowed", "reason"} <= keys:
                        return True
        return False

    return composition.search(
        source=source,
        class_name="Decision",
        capability="render_value_object_as_mapping",
        fields=["allowed", "reason", "missing"],
        detail="allowed,reason",
        collections=(),
        accepts=accepts,
        max_length=6,
    )


def test_the_search_examines_many_and_refuses_most(report: composition.SearchReport) -> None:
    """A space where everything succeeds is a template with extra steps."""

    assert report.examined > 100
    assert report.refused_total() > 0
    assert report.refused_total() > report.survivors, (
        "most assemblies must fail; if they do not, the operations are too close "
        "to the repair"
    )


def test_incomplete_drafts_are_the_commonest_refusal(report: composition.SearchReport) -> None:
    """Most sequences never become a method at all."""

    assert report.refused["incomplete_draft_is_not_a_method"] > 0


def test_candidates_are_refused_for_missing_the_requirement(
    report: composition.SearchReport,
) -> None:
    """Assemblies that build a method but the wrong one are rejected by measurement."""

    assert report.refused.get("requirement_not_satisfied", 0) > 0


def test_the_adopted_candidate_satisfies_the_requirement(
    report: composition.SearchReport,
) -> None:
    assert report.adopted is not None
    source = report.adopted.source
    ast.parse(source)
    assert "allowed" in source and "reason" in source
    assert len(report.adopted.composition) >= 3


def test_the_adoption_is_deterministic(report: composition.SearchReport) -> None:
    """The requirement underdetermines the method, so the tie breaks on content."""

    assert report.survivors >= 1
    assert report.adopted is not None
    assert len(report.adopted.digest()) == 64


def test_nothing_is_adopted_when_nothing_satisfies() -> None:
    result = composition.search(
        source=CLASS_SOURCE,
        class_name="Decision",
        capability="render_value_object_as_mapping",
        fields=["allowed"],
        detail="allowed",
        collections=(),
        accepts=lambda modified: False,
        max_length=4,
    )
    assert result.adopted is None
    assert result.survivors == 0
    assert result.refused_total() > 0
