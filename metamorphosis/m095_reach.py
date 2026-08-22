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
from metamorphosis.m094_diagnosis import _mapping_bindings, decode_rendering

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


def _plain_zero_argument_method(node: ast.AST) -> bool:
    """Can generated code safely invoke this as synchronous ``obj.method()``?

    The syntax M095 emits is deliberately narrow.  Async functions return a coroutine,
    argument-taking methods cannot be called that way, and a decorator can turn an otherwise
    ordinary function into a property, static method, class method, or an unknown wrapper.  A
    syntax-only check cannot prove those altered call contracts, so they do not count.
    """

    if not isinstance(node, ast.FunctionDef):
        return False
    if node.name.startswith("_") or node.decorator_list:
        return False
    positional = (*node.args.posonlyargs, *node.args.args)
    return bool(
        len(positional) == 1
        and not node.args.vararg
        and not node.args.kwonlyargs
        and not node.args.kwarg
    )


class _OwnReturns(ast.NodeVisitor):
    """Collect returns while refusing to descend into nested definitions."""

    def __init__(self) -> None:
        self.values: list[ast.expr] = []

    def visit_Return(self, node: ast.Return) -> None:  # noqa: N802 - ast visitor API
        if node.value is not None:
            self.values.append(node.value)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return


def _own_return_values(method: ast.FunctionDef) -> tuple[ast.expr, ...]:
    returned = _OwnReturns()
    for statement in method.body:
        returned.visit(statement)
    return tuple(returned.values)


def _method_supplies_mapping(method: ast.FunctionDef, requirement: str) -> bool:
    """Does this method's own control flow return the exact required mapping?"""

    wanted = decode_rendering(requirement)
    if not wanted:
        return False

    for value in _own_return_values(method):
        produced = _mapping_bindings(value)
        if produced is not None and all(
            produced.get(key) == (field, wrapper) for key, field, wrapper in wanted
        ):
            return True
    return False


def supplying_method(class_node: ast.ClassDef, requirement: str) -> str | None:
    """Which public zero-argument method of *class_node* supplies *requirement*, if any.

    Read from the syntax tree, so it measures the code rather than recalling what was adopted.
    A method counts whether the lineage wrote it, a person wrote it, or it was always there --
    which is what makes the enabling relation a property of the state and not of the history.

    Returning `None` is the whole of M095's reachability story: it is what makes a composition
    unbuildable at S0.
    """

    for node in class_node.body:
        if _plain_zero_argument_method(node) and _method_supplies_mapping(node, requirement):
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


# ── seeing the nested demand ──────────────────────────────────────────


def _attribute_chain(node: ast.expr) -> tuple[str, str, str] | None:
    """For `obj.field.sub`, return `(obj, field, sub)`. Anything else gives None."""

    if (isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)):
        return node.value.value.id, node.value.attr, node.attr
    return None


def nested_bindings(node: ast.expr) -> dict[str, tuple[str, tuple[tuple[str, str], ...]]]:
    """Keys of a dict literal whose value is itself a rendering of one nested field.

    `{"reading": {"reading_id": s.reading.reading_id, "unit": s.reading.unit}}` gives
    `{"reading": "reading"}`: the key `reading` holds a mapping built entirely out of
    attributes of `s.reading`, so the caller is rendering that field by hand and the field is
    what a renderer would have to render.

    A nested literal drawing on more than one field, or on anything that is not an attribute
    chain, binds nothing -- it is not a rendering of a single value object.
    """

    if not isinstance(node, ast.Dict):
        return {}

    found: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {}
    for key, value in zip(node.keys, node.values):
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        if not isinstance(value, ast.Dict) or not value.values:
            continue
        chains = [_attribute_chain(item) for item in value.values]
        if None in chains:
            continue
        # The base object matters as much as the field spelling.  Combining
        # ``sample.reading.id`` with ``other.reading.unit`` would otherwise manufacture a
        # renderer demand no single object can satisfy.
        sources = {(chain[0], chain[1]) for chain in chains if chain}
        if len(sources) != 1:
            continue
        inner_keys = [
            item.value for item in value.keys
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        if len(inner_keys) != len(chains):
            continue
        inner = tuple(sorted(
            (inner_key, chain[2]) for inner_key, chain in zip(inner_keys, chains) if chain
        ))
        _base, field = sources.pop()
        found[key.value] = (field, inner)
    return found


@dataclass(frozen=True)
class RenderNestedValueObject:
    """Rebuilding a *nested* value object's fields into a mapping, at the call site.

    M094's `RenderAsMapping` sees `{"k": obj.field}` and cannot see
    `{"k": {"a": obj.field.a, "b": obj.field.b}}`, which is what a caller writes when the field
    is itself a value object that renders nothing. This shape sees the second, and the whole of
    M095's chain depends on it being visible: without it the outer class's demand is invisible
    and there is no second repair to reach for.

    Defined here, in M095's namespace, and passed to the diagnosis explicitly. M094 measured
    with `CAPABILITY_SHAPES` and its result depends on that measurement; adding a shape to the
    shared tuple would have changed it.
    """

    name: str = "render_nested_value_object_as_mapping"
    merges_details: bool = True

    def applies_to(self, class_node: ast.ClassDef) -> bool:
        return any(
            isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            for item in class_node.body
        )

    def demand_sites(self, tree, class_node, rivals=()):
        """Call sites that render a nested field of this class by hand."""

        declared = {
            item.target.id for item in class_node.body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        }
        sites: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            for key, (field, inner) in nested_bindings(node).items():
                if field not in declared:
                    continue
                explainers = {
                    rival.identity for rival in rivals if field in rival.fields
                }
                if rivals and (
                    len(explainers) != 1
                    or not any(name == class_node.name for _, name in explainers)
                ):
                    continue
                sites.append((class_node.name, encode_nested(key, field, inner)))
        return sites

    def is_supplied_by(self, class_node: ast.ClassDef, target: str, detail: str) -> bool:
        """Does the class define a method rendering that field through a renderer?"""

        wanted = decode_rendering(detail)
        for node in class_node.body:
            if not _plain_zero_argument_method(node):
                continue
            for returned in _own_return_values(node):
                if not isinstance(returned, ast.Dict):
                    continue
                produced: dict[str, str] = {}
                for key, value in zip(returned.keys, returned.values):
                    if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                        continue
                    # `self.field.method()` -- a renderer called on the field.
                    if (isinstance(value, ast.Call)
                            and isinstance(value.func, ast.Attribute)
                            and isinstance(value.func.value, ast.Attribute)
                            and not value.args):
                        produced[key.value] = value.func.value.attr
                if all(produced.get(key) == field for key, field, _w in wanted):
                    return True
        return False


#: Wrapper prefix for a requirement key whose value is a nested mapping. What follows names
#: the inner key/field pairs the call sites wrote, so anything checking the requirement can
#: compute the expected value without discovering a method first.
NESTED_WRAPPER = "nested:"


def encode_nested(key: str, field: str, inner: tuple[tuple[str, str], ...]) -> str:
    """Encode `key -> field rendered as {k: f, ...}` the way the diagnosis encodes renderings.

    The inner pairs travel because the wrapper has to say *what the caller wrote*, not merely
    that something was nested. An audit of this module found the wrapper empty, so the probe
    expected the inner object where the call site had written a mapping and refused every
    correct candidate.
    """

    body = ";".join(f"{k}:{f}" for k, f in inner)
    return key + "=" + field + "|" + NESTED_WRAPPER + body


def decode_nested(wrapper: str | None) -> tuple[tuple[str, str], ...]:
    """Recover the inner key/field pairs from a `nested:` wrapper."""

    if not isinstance(wrapper, str) or not wrapper.startswith(NESTED_WRAPPER):
        return ()
    body = wrapper[len(NESTED_WRAPPER):]
    pairs = []
    for piece in body.split(";"):
        if not piece:
            continue
        key, _, field = piece.partition(":")
        pairs.append((key, field))
    return tuple(pairs)
