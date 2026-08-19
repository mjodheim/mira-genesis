"""M095: one repair changing what the next repair can reach.

M094 established that a lineage can locate the component limiting it and build the repair.
M095 asks the question one step along, which is the one the project actually cares about:

    does an adopted repair change what the lineage can *reach*?

The shape is a chain with a counterfactual:

    S0 --(repair A, chosen by the diagnosis)--> S1 --(repair B, chosen by the diagnosis)--> S2

    and: from S0, B is **unreachable** -- not merely unchosen. Same operation set, same budget,
    exhausted, nothing found.

One idea makes that possible without adding anything to the language. `IncludeRenderedField`
binds a key to a field that is itself a value object, by calling that object's own renderer.
Whether it *applies* is not a flag anyone sets: it is read from the inner class's syntax tree
at the moment the operation is asked. At S0 the inner class renders nothing, so the operation
returns `None` for every draft and no composition through it can be assembled. After repair A
adopts a renderer on the inner class, the same operation -- unchanged, and already in the set
at S0 -- begins to apply.

The operation set is identical in both states. The reach is not.

What this does **not** claim, and what M096/M097 are for: the lineage does not invent the
operation, extend its language, or acquire a capability it lacked. The language is authored and
fixed, and is disclosed here as the ceiling exactly as M094 disclosed its own. The claim is
narrower and, for a cumulative lineage, prior: **adoption moves the frontier of what a fixed
language can build.**
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, replace

from metamorphosis.m094_composition import MappingItem, MethodDraft, Operation
from metamorphosis.m094_diagnosis import RenderAsMapping, decode_rendering

REACH_SCHEMA = "m095-reach-v1"

#: Marks a mapping item whose value is produced by calling a renderer on the field, rather than
#: by reading the field. The method name travels in the wrapper so the assembled method calls
#: whatever the inner class actually supplies rather than a name written down here.
RENDER_PREFIX = "render:"


def find_class(tree: ast.AST, name: str) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def rendered_method(wrapper: str | None) -> str | None:
    """Recover the renderer name from a `render:<method>` wrapper, if that is what it is."""

    if isinstance(wrapper, str) and wrapper.startswith(RENDER_PREFIX):
        return wrapper[len(RENDER_PREFIX):]
    return None


def supplying_method(class_node: ast.ClassDef, requirement: str) -> str | None:
    """Which public zero-argument method of *class_node* supplies *requirement*, if any.

    Read from the syntax tree, so it measures the code rather than recalling what was adopted.
    A method counts whether the lineage wrote it, a person wrote it, or it was always there --
    which is what makes the enabling relation a property of the state and not of the history.

    Returning `None` is the whole of M095's reachability story: it is what makes a composition
    unbuildable at S0.
    """

    if not RenderAsMapping().is_supplied_by(class_node, class_node.name, requirement):
        return None

    wanted = decode_rendering(requirement)
    for node in class_node.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        if len(node.args.args) != 1 or node.args.vararg or node.args.kwonlyargs:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Return) or not isinstance(inner.value, ast.Dict):
                continue
            keys = {
                item.value for item in inner.value.keys
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
            if {key for key, _field, _wrapper in wanted} <= keys:
                return node.name
    return None


@dataclass(frozen=True)
class IncludeRenderedField(Operation):
    """Bind one key to a field rendered through that field's own renderer.

    Present in the operation set at every state; applicable only where the inner class supplies
    the rendering, which is read from its syntax tree when the operation is asked to apply.

    `apply` returning `None` is neither an error nor a matter of taste. It is the operation
    reporting that the code does not support what it would emit -- the same way `IncludeField`
    returns `None` for a key already bound. The search prunes the branch, and a composition
    that needed it cannot be assembled.
    """

    key: str
    field: str
    #: The inner class as it stands in the state being searched, or `None` if absent.
    inner_class: ast.ClassDef | None
    #: The rendering the inner class must supply, encoded as the diagnosis encodes it.
    inner_requirement: str

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        method = self.supplier()
        if method is None:
            return None
        if any(item.key == self.key for item in draft.items):
            return None
        item = MappingItem(key=self.key, field=self.field, wrapper=RENDER_PREFIX + method)
        return replace(draft, items=draft.items + (item,))

    def supplier(self) -> str | None:
        """The renderer this operation would call, or `None` if the state supplies none."""

        if self.inner_class is None:
            return None
        return supplying_method(self.inner_class, self.inner_requirement)

    def is_reachable(self) -> bool:
        """Can this operation contribute anything in the state it was built against?"""

        return self.supplier() is not None

    def describe(self) -> str:
        return "include=" + self.key + "<-render(" + self.field + ")"


@dataclass(frozen=True)
class NestedRendering:
    """One key of an outer requirement whose value is another value object.

    Recovered from the diagnosis and the outer class's annotations, not written down: `key` and
    `field` come from what the call sites wrote, `inner_class_name` from the field's annotation,
    and `inner_requirement` from what the call sites wrote about the inner object.
    """

    key: str
    field: str
    inner_class_name: str
    inner_requirement: str


def operations_for_nested(
    nested: tuple[NestedRendering, ...],
    inner_classes: dict[str, ast.ClassDef | None],
) -> tuple[IncludeRenderedField, ...]:
    """The nested-rendering operations available for one outer requirement.

    Identical in every state: one operation per nested key, always offered. Whether any of them
    can be used is settled by `apply`, against the code.
    """

    return tuple(
        IncludeRenderedField(
            key=item.key,
            field=item.field,
            inner_class=inner_classes.get(item.inner_class_name),
            inner_requirement=item.inner_requirement,
        )
        for item in nested
    )


def unreachable_operations(
    operations: tuple[IncludeRenderedField, ...]
) -> tuple[str, ...]:
    """Which of them the current state cannot use. The census S0's control reports."""

    return tuple(op.describe() for op in operations if not op.is_reachable())
